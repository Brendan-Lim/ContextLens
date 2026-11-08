#!/usr/bin/env python3
"""Separate, explicitly unnotarized preview channel. No Apple credentials or security exceptions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from release import ROOT, archive_members, metadata, require, run, verify

REPO = 'Brendan-Lim/ContextLens'
TRUST = 'unnotarized-adhoc-preview'


def preview_version(version):
    require(re.fullmatch(re.escape(metadata()['version']) + r'-preview\.[1-9][0-9]*', version),
            'Preview must be the current base version plus -preview.N (N > 0)')
    return version


def source():
    require(not run('git', '-C', ROOT, 'status', '--porcelain').strip(), 'Preview requires a clean source checkout')
    return dict(sourceRepository='https://github.com/' + REPO,
                sourceCommit=run('git', '-C', ROOT, 'rev-parse', 'HEAD').strip(),
                sourceTree=run('git', '-C', ROOT, 'rev-parse', 'HEAD^{tree}').strip(), sourceDirty=False)


def write_provenance(app, version):
    preview_version(version)
    receipt = dict(source(), version=version, baseVersion=metadata()['version'], architecture='arm64',
                   trust=TRUST, notarized=False, developerIDSigned=False,
                   xcode=run('xcodebuild', '-version').strip(), swift=run('swift', '--version').strip(),
                   buildOS=run('sw_vers', '-productVersion').strip())
    (Path(app) / 'Contents/Resources/preview.json').write_text(json.dumps(receipt, indent=2) + '\n')


def adhoc_signature(signature):
    require('Signature=adhoc\n' in signature and 'Authority=' not in signature
            and 'TeamIdentifier=not set\n' in signature, 'Preview requires ad-hoc signing without an Apple authority or team')


def verify_bundle(app, version):
    preview_version(version)
    app = Path(app).resolve()
    for binary in [app, app / 'Contents/MacOS/ContextLens', app / 'Contents/MacOS/contextlens-cli']:
        adhoc_signature(run('codesign', '-d', '--verbose=4', binary))
    verify(app, 'development')
    receipt = json.loads((app / 'Contents/Resources/preview.json').read_text())
    require(receipt.get('version') == version and receipt.get('baseVersion') == metadata()['version']
            and receipt.get('trust') == TRUST and receipt.get('architecture') == 'arm64'
            and receipt.get('sourceDirty') is False and receipt.get('notarized') is False
            and receipt.get('developerIDSigned') is False, 'Preview bundle provenance mismatch')
    require(receipt.get('sourceRepository') == 'https://github.com/' + REPO, 'Unexpected source repository')
    require(re.fullmatch(r'[0-9a-f]{40}', receipt.get('sourceCommit', ''))
            and re.fullmatch(r'[0-9a-f]{40}', receipt.get('sourceTree', '')), 'Invalid source commit/tree')
    require(run('git', '-C', ROOT, 'rev-parse', receipt['sourceCommit'] + '^{tree}').strip()
            == receipt['sourceTree'], 'Source tree differs from commit')
    return receipt


def package(app, output, version):
    preview_version(version)
    expected_source = source()
    receipt = verify_bundle(app, version)
    require(all(receipt.get(k) == v for k, v in expected_source.items()), 'Bundle was built from different source')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = f'ContextLens-{version}-arm64.zip'
    target = output / name
    require(not any((output / (name + suffix)).exists() for suffix in ['', '.sha256', '.json']),
            'Preview archive or sidecar exists; never overwrite')
    with tempfile.TemporaryDirectory(prefix='.preview-', dir=output) as temporary:
        staged = Path(temporary) / name
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', Path(app).resolve(), staged)
        archive_members(staged)
        unpacked = Path(temporary) / 'unpacked'
        run('ditto', '-x', '-k', staged, unpacked)
        require(verify_bundle(unpacked / 'ContextLens.app', version) == receipt, 'Archive round-trip changed provenance')
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        # Hard links and exclusive sidecar creation fail rather than replace bytes.
        os.link(staged, target)
    receipt = dict(receipt, archive=name, sha256=digest)
    with target.with_suffix('.zip.sha256').open('x') as checksum:
        checksum.write(f'{digest}  {name}\n')
    with target.with_suffix('.zip.json').open('x') as sidecar:
        sidecar.write(json.dumps(receipt, indent=2) + '\n')
    verify_archive(target, version)
    print(json.dumps(receipt, indent=2))
    return target


def verify_archive(path, version):
    preview_version(version)
    path = Path(path).resolve()
    require(path.name == f'ContextLens-{version}-arm64.zip', 'Unexpected preview asset name')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(path.with_suffix('.zip.sha256').read_text().strip() == f'{digest}  {path.name}', 'Preview checksum mismatch')
    receipt = json.loads(path.with_suffix('.zip.json').read_text())
    require(receipt.get('sha256') == digest and receipt.get('archive') == path.name
            and receipt.get('trust') == TRUST and receipt.get('notarized') is False
            and receipt.get('developerIDSigned') is False, 'Preview receipt mismatch')
    archive_members(path)
    with tempfile.TemporaryDirectory(prefix='contextlens-preview-verify-') as temporary:
        run('ditto', '-x', '-k', path, temporary)
        embedded = verify_bundle(Path(temporary) / 'ContextLens.app', version)
        require(receipt == dict(embedded, archive=path.name, sha256=digest), 'Embedded provenance differs from receipt')
    return receipt


def preflight(version):
    preview_version(version)
    source()
    require(run('git', '-C', ROOT, 'branch', '--show-current').strip() == 'main', 'Preview must run from main')
    run('git', '-C', ROOT, 'fetch', 'origin', 'main', '--tags')
    require(run('git', '-C', ROOT, 'rev-parse', 'HEAD') == run('git', '-C', ROOT, 'rev-parse', 'origin/main'),
            'Preview must use current origin/main')
    require(not run('git', '-C', ROOT, 'tag', '--list', 'v' + version).strip(), 'Preview tag already exists')
    pages = json.loads(run('gh', 'api', f'repos/{REPO}/releases', '--paginate', '--slurp'))
    require(not any(r['tag_name'] == 'v' + version for page in pages for r in page), 'Preview release already exists')


def publish(output, version):
    preflight(version)
    output = Path(output).resolve()
    name = f'ContextLens-{version}-arm64.zip'
    receipt = verify_archive(output / name, version)
    require(all(receipt.get(k) == v for k, v in source().items()), 'Archive source differs from publication source')
    notes = f'''ContextLens {version} — UNNOTARIZED PREVIEW

Apple Silicon (arm64), macOS 14+. Optimized app with embedded contextlens-cli.
Ad-hoc signed for code integrity only. No Developer ID signature, Apple notarization,
or Gatekeeper acceptance is claimed. Apple has not verified this preview.

Verify the release origin, source commit and SHA-256 before authorizing this app.
The checksum detects changed bytes; it does not establish Apple trust.
If macOS blocks launch, follow Apple's user-controlled Open Anyway process:
https://support.apple.com/en-us/102445
Do not remove quarantine or disable Gatekeeper. Managed Macs may prohibit authorization.

Source: https://github.com/{REPO}/commit/{receipt['sourceCommit']}
ZIP: {name}
SHA-256: {receipt['sha256']}

Automated regression, bundle, architecture, portability and archive checks passed.
Fresh-user Gatekeeper authorization, Screen Recording and interactive capture/Hand Off
remain pending. macOS 14 runtime has not been tested; hosted checks use macOS 15.
Homebrew availability and installation results: https://github.com/{REPO}/blob/main/docs/preview-releases.md
'''
    with tempfile.TemporaryDirectory(prefix='contextlens-preview-notes-') as temporary:
        notes_file = Path(temporary) / 'notes.txt'
        notes_file.write_text(notes)
        # Atomic create-ref rejects even a racing existing tag. Never move a tag.
        run('gh', 'api', f'repos/{REPO}/git/refs', '-f', 'ref=refs/tags/v' + version,
            '-f', 'sha=' + receipt['sourceCommit'])
        run('gh', 'release', 'create', 'v' + version, '--repo', REPO, '--verify-tag', '--draft',
            '--prerelease', '--latest=false', '--title', f'ContextLens {version} — Unnotarized Preview',
            '--notes-file', notes_file, *[output / (name + suffix) for suffix in ['', '.sha256', '.json']])
        run('gh', 'release', 'edit', 'v' + version, '--repo', REPO, '--draft=false', '--prerelease', '--latest=false')


def published_assets(info, version):
    require(info['tag_name'] == 'v' + version and info['prerelease'] and not info['draft'] and info['published_at'],
            'A published prerelease is required')
    name = f'ContextLens-{version}-arm64.zip'
    for suffix in ['', '.sha256', '.json']:
        matches = [a for a in info['assets'] if a['name'] == name + suffix]
        require(len(matches) == 1 and matches[0]['state'] == 'uploaded', 'Missing or ambiguous preview asset')
        require(matches[0]['browser_download_url'] == f'https://github.com/{REPO}/releases/download/v{version}/{name}{suffix}',
                'Unexpected preview asset URL')
        asset_id = matches[0].get('id')
        require(type(asset_id) is int and asset_id > 0 and matches[0].get('url') ==
                f'https://api.github.com/repos/{REPO}/releases/assets/{asset_id}', 'Unexpected preview API asset URL')


def render_cask(version, checksum, asset_id):
    preview_version(version)
    require(re.fullmatch(r'[0-9a-f]{64}', checksum), 'Actual SHA-256 required')
    require(type(asset_id) is int and asset_id > 0, 'Actual positive GitHub asset ID required')
    return (ROOT / 'distribution/homebrew/Casks/contextlens-preview.rb.in').read_text().replace(
        '__VERSION__', version).replace('__SHA256__', checksum).replace('__ASSET_ID__', str(asset_id))


def update_tap(tap, version):
    preview_version(version)
    tap = Path(tap).resolve()
    require(run('git', '-C', tap, 'remote', 'get-url', 'origin').strip() in [
        'https://github.com/Brendan-Lim/homebrew-tap.git', 'https://github.com/Brendan-Lim/homebrew-tap',
        'git@github.com:Brendan-Lim/homebrew-tap.git'], 'Unexpected tap origin')
    require(not run('git', '-C', tap, 'status', '--porcelain').strip(), 'Tap must be clean')
    info = json.loads(run('gh', 'api', f'repos/{REPO}/releases/tags/v{version}'))
    published_assets(info, version)
    name = f'ContextLens-{version}-arm64.zip'
    with tempfile.TemporaryDirectory(prefix='contextlens-preview-download-') as temporary:
        run('gh', 'release', 'download', 'v' + version, '--repo', REPO, '--dir', temporary,
            '--pattern', name, '--pattern', name + '.sha256', '--pattern', name + '.json')
        receipt = verify_archive(Path(temporary) / name, version)
        commit = json.loads(run('gh', 'api', f'repos/{REPO}/commits/v{version}'))
        require(receipt['sourceCommit'] == commit['sha'], 'Preview tag differs from archive source')
        asset = next(a for a in info['assets'] if a['name'] == name)
        contents = render_cask(version, receipt['sha256'], asset['id'])
    target = tap / 'Casks/contextlens-preview.rb'
    if target.exists():
        old = re.search(r'^  version "(.+)"$', target.read_text(), re.M)
        old_version = old[1].split(',')[0] if old else None
        require(old_version and old_version != version, 'Never replace a published cask version')
        def ordering(value):
            return tuple(map(int, re.fullmatch(r'(\d+)\.(\d+)\.(\d+)-preview\.(\d+)', value).groups()))
        require(ordering(version) > ordering(old_version), 'Only forward preview updates are allowed')
    with tempfile.TemporaryDirectory(prefix='.preview-cask-', dir=tap) as temporary:
        staged = Path(temporary) / target.name
        staged.write_text(contents)
        run('ruby', '-c', staged)
        os.replace(staged, target)
    print('Generated preview cask from verified published bytes; audit/install on a disposable Mac before publishing the tap.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['preflight', 'provenance', 'package', 'verify-archive', 'publish', 'update-tap']:
        command = commands.add_parser(name)
        command.add_argument('version')
        if name in ['provenance', 'package']: command.add_argument('app')
        if name in ['package', 'publish']: command.add_argument('output')
        if name == 'verify-archive': command.add_argument('path')
        if name == 'update-tap': command.add_argument('tap')
    args = parser.parse_args()
    if args.command == 'preflight': preflight(args.version)
    elif args.command == 'provenance': write_provenance(args.app, args.version)
    elif args.command == 'package': package(args.app, args.output, args.version)
    elif args.command == 'verify-archive': print(json.dumps(verify_archive(args.path, args.version), indent=2))
    elif args.command == 'publish': publish(args.output, args.version)
    elif args.command == 'update-tap': update_tap(args.tap, args.version)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as error:
        raise SystemExit(f'Preview gate failed: {error}')
