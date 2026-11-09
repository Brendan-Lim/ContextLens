#!/usr/bin/env python3
"""Explicit official ad-hoc channel. Candidate packaging never authorizes stable publication."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from release import ROOT, archive_members, metadata, require, run, verify
sys.path.insert(0, str(ROOT / 'distribution/dmg'))
from dmg import build as build_dmg, inventory, sha256, verify_dmg

SPEC = importlib.util.spec_from_file_location('preview_helpers', ROOT / 'scripts/preview-release.py')
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
REPO = preview.REPO
TRUST = 'official-unnotarized-adhoc'
CASES = ('gatekeeper-first-launch', 'open-anyway', 'screen-recording-denied',
         'fresh-screen-recording-grant-relaunch', 'selected-window-low', 'selected-window-high',
         'review-annotation-undo-redo', 'handoff-export', 'session-reopen-recovery',
         'selected-window-closure-no-substitution', 'target-application-exit',
         'contextlens-exit-during-capture', 'pending-frame-persistence', 'failed-save-retry',
         'rapid-start-stop', 'permission-revocation-recovery', 'dmg-finder-light',
         'dmg-finder-dark', 'dmg-drag-install-eject-launch')


def release_input_identity(revision):
    """Inventory the tracked dependency closure; unknown inputs are protected.

    The actual build reads SwiftPM source/dependencies, scripts and their imports,
    version/signing metadata, icon/license, DMG assets/layout/dependencies and the
    pinned workflow/toolchain. Protect the entire tree, including new files,
    except regular documentation and this version's separately verified evidence.
    Symlinks, executable documentation and all non-Markdown docs stay protected.
    """
    acceptance_path = 'docs/release-acceptance/' + metadata()['version'] + '.json'
    policy = json.loads(run('git', '-C', ROOT, 'show', revision + ':config/release-input-policy.json'))
    require(set(policy) == {'schemaVersion', 'nonArtifactDocumentation'} and policy['schemaVersion'] == 1,
            'Unsupported release input policy')
    docs = policy['nonArtifactDocumentation']
    require(isinstance(docs, list) and all(isinstance(path, str) for path in docs), 'Invalid documentation inventory')
    require(len(set(docs)) == len(docs) and all(
        (path == 'README.md' or path.startswith('docs/') and path.endswith('.md'))
        and '\\' not in path and all(part not in ('', '.', '..') for part in path.split('/'))
        for path in docs), 'Invalid documentation exemption')
    entries = []
    for record in run('git', '-C', ROOT, 'ls-tree', '-r', '-z', '--full-tree', revision).split('\0'):
        if not record: continue
        header, path = record.split('\t', 1)
        mode, kind, oid = header.split()
        if mode == '100644' and (path in docs or path == acceptance_path): continue
        require(kind == 'blob' and mode in ('100644', '100755', '120000'),
                'Unsupported release input: ' + path)
        entries.append([path, mode, oid])
    encoded = json.dumps(sorted(entries), separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return dict(schemaVersion=1, sha256=hashlib.sha256(encoded).hexdigest(), files=len(entries))


def assert_fresh_candidate(receipt, current='origin/main'):
    source = receipt.get('sourceCommit', '')
    require(isinstance(source, str) and re.fullmatch(r'[0-9a-f]{40}', source), 'Invalid candidate source')
    identity = receipt.get('releaseInputs')
    require(isinstance(identity, dict) and set(identity) == {'schemaVersion', 'sha256', 'files'},
            'Candidate release input inventory missing or mismatched')
    expected = release_input_identity(source)
    require(identity == expected, 'Candidate release input inventory missing or mismatched')
    run('git', '-C', ROOT, 'merge-base', '--is-ancestor', source, current)
    # Inspect every intervening tree as well, so a changed-then-reverted input
    # cannot reuse acceptance for a candidate from before that change.
    revisions = [current] + run('git', '-C', ROOT, 'rev-list', '--ancestry-path', source + '..' + current).splitlines()
    for revision in dict.fromkeys(revisions):
        require(release_input_identity(revision) == expected,
                'Release inputs changed after candidate preparation; prepare and test a new candidate')


def asset_names(version):
    require(isinstance(version, str), 'Exact release version required')
    metadata(version)
    return [f'ContextLens-{version}-arm64.{extension}' for extension in ['zip', 'dmg']]


def bundle_hash(app):
    return hashlib.sha256(json.dumps(inventory(app), sort_keys=True).encode()).hexdigest()


def write_provenance(app):
    data = metadata()
    receipt = dict(preview.source(), version=data['version'], build=data['build'],
                   releaseInputs=release_input_identity('HEAD'),
                   architecture='arm64', minimumMacOS=data['minimumMacOS'], trust=TRUST,
                   notarized=False, developerIDSigned=False,
                   xcode=run('xcodebuild', '-version').strip(), swift=run('swift', '--version').strip(),
                   buildOS=run('sw_vers', '-productVersion').strip())
    with (Path(app) / 'Contents/Resources/official.json').open('x') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')


def verify_bundle(app):
    app = Path(app)
    verify(app, 'development')
    for binary in [app, app / 'Contents/MacOS/ContextLens', app / 'Contents/MacOS/contextlens-cli']:
        preview.adhoc_signature(run('codesign', '-d', '--verbose=4', binary))
    receipt = json.loads((app / 'Contents/Resources/official.json').read_text())
    data = metadata()
    require(all(receipt.get(k) == data[k] for k in ['version', 'build', 'minimumMacOS']), 'Official bundle metadata mismatch')
    require(receipt.get('architecture') == 'arm64' and receipt.get('trust') == TRUST
            and receipt.get('sourceDirty') is False and receipt.get('notarized') is False
            and receipt.get('developerIDSigned') is False, 'Official bundle trust mismatch')
    require(receipt.get('sourceRepository') == f'https://github.com/{REPO}', 'Unexpected source repository')
    for key in ['sourceCommit', 'sourceTree']:
        require(re.fullmatch(r'[0-9a-f]{40}', receipt.get(key, '')), 'Invalid source identity')
    require(run('git', '-C', ROOT, 'rev-parse', receipt['sourceCommit'] + '^{tree}').strip()
            == receipt['sourceTree'], 'Embedded tree differs from source commit')
    require(receipt.get('releaseInputs') == release_input_identity(receipt['sourceCommit']),
            'Embedded release input inventory differs from source commit')
    return receipt


def package(app, output):
    expected = preview.source()
    receipt = verify_bundle(app)
    require(all(receipt.get(k) == v for k, v in expected.items()), 'App differs from packaging source')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    require(not list(output.iterdir()), 'Candidate output must be empty; never replace assets')
    names = asset_names(receipt['version'])
    original = bundle_hash(app)
    with tempfile.TemporaryDirectory(prefix='contextlens-candidate-') as temporary:
        stage = Path(temporary)
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, stage / names[0])
        archive_members(stage / names[0])
        build_dmg(app, stage / names[1])
        require(bundle_hash(app) == original, 'Packaging changed the signed source bundle')
        provenance = dict(receipt, bundleInventorySHA256=original,
                          assets={name: sha256(stage / name) for name in names})
        (stage / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        (stage / 'SHA256SUMS').write_text(''.join(f'{sha256(stage / name)}  {name}\n'
                                               for name in names + ['provenance.json']))
        verify_assets(stage)
        for path in stage.iterdir():
            # Copy through a same-filesystem temporary, then exclusive link.
            with tempfile.TemporaryDirectory(prefix='.asset-', dir=output) as local:
                copied = Path(local) / path.name
                run('ditto', path, copied)
                os.link(copied, output / path.name)
    return provenance


def verify_assets(output):
    output = Path(output)
    receipt = json.loads((output / 'provenance.json').read_text())
    names = asset_names(receipt.get('version'))
    require(receipt.get('trust') == TRUST and set(receipt.get('assets', {})) == set(names), 'Candidate asset/trust mismatch')
    for name in names:
        require(receipt['assets'][name] == sha256(output / name), 'Candidate checksum mismatch')
    expected = ''.join(f'{sha256(output / name)}  {name}\n' for name in names + ['provenance.json'])
    require((output / 'SHA256SUMS').read_text() == expected, 'Final asset checksum list differs')
    archive_members(output / names[0])
    with tempfile.TemporaryDirectory(prefix='contextlens-official-verify-') as temporary:
        run('ditto', '-x', '-k', output / names[0], temporary)
        app = Path(temporary) / 'ContextLens.app'
        embedded = verify_bundle(app)
        require(receipt == dict(embedded, assets=receipt['assets'], bundleInventorySHA256=bundle_hash(app)),
                'ZIP content/provenance differs from receipt')
        result = verify_dmg(output / names[1], app, install_copy=True)
        require(result['bundleInventorySHA256'] == receipt['bundleInventorySHA256'], 'DMG and ZIP bundles differ')
    return receipt


def descriptive(value, minimum=4):
    return isinstance(value, str) and len(value.strip()) >= minimum and value.strip().lower() not in {
        'pending', 'todo', 'unknown', 'not run', 'n/a', 'example', 'placeholder'}


def acceptance(evidence, receipt):
    require(evidence.get('schemaVersion') == 1 and evidence.get('isolatedEnvironment') is True,
            'Verified isolated interactive acceptance is required')
    for key in ['version', 'build', 'sourceCommit', 'bundleInventorySHA256', 'assets']:
        require(evidence.get(key) == receipt.get(key), 'Acceptance differs from candidate: ' + key)
    require(evidence.get('blockers') == [], 'All release-blocking findings must be resolved')
    require(descriptive(evidence.get('testedBy')), 'A real tester attestation is required')
    require(isinstance(evidence.get('testedAt'), str) and 'T' in evidence['testedAt'], 'ISO test timestamp with timezone required')
    tested_at = datetime.fromisoformat(evidence['testedAt'].replace('Z', '+00:00'))
    require(tested_at.tzinfo is not None, 'Acceptance timestamp must identify its timezone')
    require(datetime(2026, 1, 1, tzinfo=timezone.utc) <= tested_at <= datetime.now(timezone.utc), 'Invalid/future acceptance timestamp')
    require(evidence.get('architecture') == 'arm64' and isinstance(evidence.get('macOS'), str)
            and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', evidence['macOS'])
            and int(evidence['macOS'].split('.')[0]) >= 14, 'Supported test machine required')
    cases = evidence.get('cases', {})
    require(isinstance(cases, dict) and set(cases) == set(CASES), 'Every required manual case must be observed')
    for name in CASES:
        case = cases[name]
        require(isinstance(case, dict) and case.get('status') == 'pass' and
                descriptive(case.get('observation'), 16) and descriptive(case.get('evidence')),
                'Missing verified manual result: ' + name)
    # These attestations are maintainer-reviewed observations, not machine proof of a GUI interaction.
    return evidence


def candidate_run(info, receipt):
    require(info.get('conclusion') == 'success' and info.get('event') == 'workflow_dispatch'
            and info.get('path') == '.github/workflows/unnotarized-stable.yml'
            and info.get('head_branch') == 'main' and info.get('head_sha') == receipt['sourceCommit']
            and info.get('repository', {}).get('full_name') == REPO, 'Candidate must come from the successful official manual workflow')


def unused_version(version):
    metadata(version)
    require(not run('git', '-C', ROOT, 'status', '--porcelain').strip(), 'Clean checkout required')
    require(run('git', '-C', ROOT, 'branch', '--show-current').strip() == 'main', 'Release must run on main')
    run('git', '-C', ROOT, 'fetch', 'origin', 'main', '--tags')
    require(run('git', '-C', ROOT, 'rev-parse', 'HEAD') == run('git', '-C', ROOT, 'rev-parse', 'origin/main'), 'Use current origin/main')
    require(not run('git', '-C', ROOT, 'tag', '--list', 'v' + version).strip(), 'Version tag already exists')
    pages = json.loads(run('gh', 'api', f'repos/{REPO}/releases', '--paginate', '--slurp'))
    require(not any(r['tag_name'] == 'v' + version for page in pages for r in page), 'Release/draft already exists')


def publish(output, evidence_path, run_id):
    # No remote mutation or archive execution occurs when evidence is absent/pending.
    evidence = json.loads(Path(evidence_path).read_text())
    output = Path(output)
    receipt = json.loads((output / 'provenance.json').read_text())
    acceptance(evidence, receipt)
    require(re.fullmatch(r'[1-9][0-9]*', run_id), 'Actual candidate workflow run ID required')
    candidate_run(json.loads(run('gh', 'api', f'repos/{REPO}/actions/runs/{run_id}')), receipt)
    unused_version(receipt['version'])
    run('git', '-C', ROOT, 'merge-base', '--is-ancestor', receipt['sourceCommit'], 'origin/main')
    assert_fresh_candidate(receipt)
    verify_assets(output)
    notes = f'''ContextLens v{receipt['version']}

Official project release · Apple Silicon · macOS 14+

UNNOTARIZED: ad-hoc signed for integrity. No Developer ID signature or Apple notarization.
Apple has not verified this app. Verify SHA256SUMS and provenance before authorizing.
If macOS blocks launch, use Apple's user-controlled Open Anyway procedure:
https://support.apple.com/en-us/102445
Keep quarantine and Gatekeeper enabled. Managed Macs may prohibit authorization.

DMG: open, drag ContextLens onto Applications, eject, then open from Applications.
ZIP: the same verified app bundle, used by Homebrew after the stable cask is published.
Preview users: back up sessions and quit; uninstall only the preview cask before switching.
https://github.com/{REPO}/blob/main/docs/homebrew.md

Source: https://github.com/{REPO}/commit/{receipt['sourceCommit']}
Candidate run: https://github.com/{REPO}/actions/runs/{run_id}
All required isolated interactive cases are attested in acceptance.json.
This is project stability acceptance; it is not Apple trust or measured agent-efficiency evidence.
'''
    with tempfile.TemporaryDirectory(prefix='contextlens-release-notes-') as temporary:
        path = Path(temporary)
        (path / 'notes.md').write_text(notes)
        (path / 'acceptance.json').write_text(json.dumps(evidence, indent=2) + '\n')
        # Mount/copy verification can take time. Recheck current main and inputs
        # immediately before the first remote mutation, retaining all old gates.
        unused_version(receipt['version'])
        assert_fresh_candidate(receipt)
        run('gh', 'api', f'repos/{REPO}/git/refs', '-f', 'ref=refs/tags/v' + receipt['version'], '-f', 'sha=' + receipt['sourceCommit'])
        run('gh', 'release', 'create', 'v' + receipt['version'], '--repo', REPO, '--verify-tag', '--draft',
            '--title', 'ContextLens v' + receipt['version'], '--notes-file', path / 'notes.md',
            *[output / name for name in asset_names(receipt['version']) + ['SHA256SUMS', 'provenance.json']], path / 'acceptance.json')
        # Verify GitHub's uploaded bytes before flipping the draft public. No clobber/retry path.
        download = path / 'download'; download.mkdir()
        run('gh', 'release', 'download', 'v' + receipt['version'], '--repo', REPO, '--dir', download)
        require(json.loads((download / 'acceptance.json').read_text()) == evidence, 'Uploaded acceptance changed')
        require(verify_assets(download) == receipt, 'Uploaded assets changed')
        run('gh', 'release', 'edit', 'v' + receipt['version'], '--repo', REPO, '--draft=false', '--prerelease=false', '--latest')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    provenance = commands.add_parser('provenance'); provenance.add_argument('app')
    packaging = commands.add_parser('package'); packaging.add_argument('app'); packaging.add_argument('output')
    check = commands.add_parser('verify-assets'); check.add_argument('output')
    inputs = commands.add_parser('input-identity'); inputs.add_argument('revision', nargs='?', default='HEAD')
    preflight = commands.add_parser('preflight'); preflight.add_argument('version')
    promote = commands.add_parser('publish'); promote.add_argument('output'); promote.add_argument('evidence'); promote.add_argument('candidate_run_id')
    args = parser.parse_args()
    if args.command == 'provenance': write_provenance(args.app)
    elif args.command == 'package': print(json.dumps(package(args.app, args.output), indent=2))
    elif args.command == 'verify-assets': print(json.dumps(verify_assets(args.output), indent=2))
    elif args.command == 'preflight': unused_version(args.version)
    elif args.command == 'input-identity': print(json.dumps(release_input_identity(args.revision), indent=2))
    elif args.command == 'publish': publish(args.output, args.evidence, args.candidate_run_id)


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Official unnotarized gate failed: {error}')
