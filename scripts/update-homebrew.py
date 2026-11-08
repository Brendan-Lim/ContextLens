#!/usr/bin/env python3
"""Generate a cask only from a published, verified ContextLens release download."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from release import metadata, require, verify_archive, ROOT


def render(version, checksum):
    require(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version), 'Invalid version')
    require(re.fullmatch(r'[0-9a-f]{64}', checksum), 'Exact SHA-256 required')
    template = (ROOT / 'distribution/homebrew/Casks/contextlens.rb.in').read_text()
    return template.replace('__VERSION__', version).replace('__SHA256__', checksum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version'); parser.add_argument('tap', type=Path)
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
    for asset in [name, name + '.sha256', name + '.json']:
        matching = [a for a in info['assets'] if a['name'] == asset]
        require(len(matching) == 1 and matching[0]['state'] == 'uploaded', 'Missing or ambiguous release asset')
        require(matching[0]['browser_download_url'] == f'https://github.com/Brendan-Lim/ContextLens/releases/download/{tag}/{asset}', 'Unexpected release download URL')
    with tempfile.TemporaryDirectory(prefix='contextlens-tap-update-') as temporary:
        subprocess.run(['gh', 'release', 'download', tag, '--repo', 'Brendan-Lim/ContextLens', '--dir', temporary,
                        '--pattern', name, '--pattern', name + '.sha256', '--pattern', name + '.json'], check=True)
        receipt = verify_archive(Path(temporary) / name)
        commit = json.loads(subprocess.check_output(['gh', 'api', f'repos/Brendan-Lim/ContextLens/commits/{tag}'], text=True))
        require(receipt.get('sourceCommit') == commit['sha'], 'Receipt source commit differs from the published tag')
        # Trust the expected signing team, not a receipt's self-asserted trust field.
        contents = render(args.version, receipt['sha256'])
    casks = tap / 'Casks'; casks.mkdir(exist_ok=True)
    target = casks / 'contextlens.rb'
    if target.exists():
        old = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+)"$', target.read_text(), re.M)
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
