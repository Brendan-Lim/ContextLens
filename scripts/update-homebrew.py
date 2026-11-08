#!/usr/bin/env python3
"""Generate a cask only from a published, verified ContextLens release download."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import importlib.util
from release import metadata, require, verify_archive, ROOT


def render(version, checksum):
    require(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version), 'Invalid version')
    require(re.fullmatch(r'[0-9a-f]{64}', checksum), 'Exact SHA-256 required')
    template = (ROOT / 'distribution/homebrew/Casks/contextlens.rb.in').read_text()
    return template.replace('__VERSION__', version).replace('__SHA256__', checksum)


def official_helpers():
    spec = importlib.util.spec_from_file_location('official_release', ROOT / 'scripts/unnotarized-release.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_official(version, checksum, asset_id):
    # Keep the trusted rendering/verification path separate and unchanged.
    metadata(version)
    require(re.fullmatch(r'[0-9a-f]{64}', checksum), 'Actual checksum required')
    require(type(asset_id) is int and asset_id > 0, 'Actual official ZIP asset ID required')
    return (ROOT / 'distribution/homebrew/Casks/contextlens-unnotarized.rb.in').read_text().replace(
        '__VERSION__', version).replace('__SHA256__', checksum).replace('__ASSET_ID__', str(asset_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version'); parser.add_argument('tap', type=Path)
    parser.add_argument('--unnotarized-official', action='store_true', help='Explicitly verify the separate official ad-hoc channel and its acceptance')
    args = parser.parse_args()
    metadata(args.version)
    tap = args.tap.resolve()
    require((tap / '.git').is_dir(), 'Use an inspected, separate tap checkout')
    require(subprocess.check_output(['git', '-C', str(tap), 'remote', 'get-url', 'origin'], text=True).strip() in ['https://github.com/Brendan-Lim/homebrew-tap.git', 'https://github.com/Brendan-Lim/homebrew-tap', 'git@github.com:Brendan-Lim/homebrew-tap.git'], 'Unexpected tap remote')
    require(not subprocess.check_output(['git', '-C', str(tap), 'status', '--porcelain'], text=True).strip(), 'Tap must be clean before updating')
    tag = 'v' + args.version
    info = json.loads(subprocess.check_output(['gh', 'api', f'repos/Brendan-Lim/ContextLens/releases/tags/{tag}'], text=True))
    require(info['tag_name'] == tag and not info['draft'] and not info['prerelease'] and info['published_at'], 'A published stable release is required')
    name = f'ContextLens-{args.version}-arm64.zip'
    official = official_helpers() if args.unnotarized_official else None
    assets = official.asset_names(args.version) + ['provenance.json', 'SHA256SUMS', 'acceptance.json'] if official else [name, name + '.sha256', name + '.json']
    for asset in assets:
        matching = [a for a in info['assets'] if a['name'] == asset]
        require(len(matching) == 1 and matching[0]['state'] == 'uploaded', 'Missing or ambiguous release asset')
        require(matching[0]['browser_download_url'] == f'https://github.com/Brendan-Lim/ContextLens/releases/download/{tag}/{asset}', 'Unexpected release download URL')
    with tempfile.TemporaryDirectory(prefix='contextlens-tap-update-') as temporary:
        patterns = [item for asset in assets for item in ['--pattern', asset]]
        subprocess.run(['gh', 'release', 'download', tag, '--repo', 'Brendan-Lim/ContextLens', '--dir', temporary, *patterns], check=True)
        receipt = official.verify_assets(temporary) if official else verify_archive(Path(temporary) / name)
        if official:
            official.acceptance(json.loads((Path(temporary) / 'acceptance.json').read_text()), receipt)
        commit = json.loads(subprocess.check_output(['gh', 'api', f'repos/Brendan-Lim/ContextLens/commits/{tag}'], text=True))
        require(receipt.get('sourceCommit') == commit['sha'], 'Receipt source commit differs from the published tag')
        # Trust the expected signing team, not a receipt's self-asserted trust field.
        asset_id = next(a['id'] for a in info['assets'] if a['name'] == name)
        contents = render_official(args.version, receipt['assets'][name], asset_id) if official else render(args.version, receipt['sha256'])
    casks = tap / 'Casks'; casks.mkdir(exist_ok=True)
    target = casks / 'contextlens.rb'
    if target.exists():
        old = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+)(?:,[1-9][0-9]*)?"$', target.read_text(), re.M)
        require(old and tuple(map(int, args.version.split('.'))) > tuple(map(int, old[1].split('.'))), 'Only forward version updates are allowed')
    temporary = casks / '.contextlens.rb.tmp'
    try:
        with temporary.open('x') as file: file.write(contents)
        subprocess.run(['ruby', '-c', str(temporary)], check=True)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    print('Generated ' + str(target) + '; run tap validation and Homebrew audit, then review/commit/push.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Tap update failed: {error}')
