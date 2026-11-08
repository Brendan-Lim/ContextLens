#!/usr/bin/env python3
"""Explicitly isolated own-window checks. This flag acknowledges isolation; it does not create it."""
import argparse
import hashlib
import json
import plistlib
from pathlib import Path
import subprocess
import tempfile
from source_state import ROOT, source_state


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--isolated-environment', action='store_true', help='Required: a disposable interactive macOS VM/test machine with no owner installation/TCC identity')
    result.add_argument('--app', type=Path, default=ROOT/'dist/ContextLens.app')
    result.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/rigorous-testing/native')
    result.add_argument('--closure-only', action='store_true', help='Run one Review/closure diagnostic, without zoom/input exercises')
    result.add_argument('--probe-style', choices=['original', 'closable'], default='original')
    result.add_argument('--key-probe', action='store_true', help='Opt-in comparison with the old key-window ordering; isolated environment only')
    return result


def main(argv=None):
    p = parser(); args = p.parse_args(argv)
    if not args.isolated_environment:
        p.error('No app launched: --isolated-environment requires a genuine disposable interactive macOS VM/test machine. Do not run against the owner desktop or TCC permissions.')
    app = args.app/'Contents/MacOS/ContextLens'
    cli = args.app/'Contents/MacOS/contextlens-cli'
    if not app.is_file() or not cli.is_file(): p.error('Use a built app bundle with its embedded CLI')
    version = json.loads((ROOT/'config/version.json').read_text())
    try: info = plistlib.loads((args.app/'Contents/Info.plist').read_bytes())
    except (OSError, ValueError): p.error('Candidate bundle Info.plist is missing or invalid')
    if (info.get('CFBundleShortVersionString'), info.get('CFBundleVersion'), info.get('CFBundleIdentifier')) != (version['version'], str(version['build']), version['bundleID']):
        p.error('Candidate bundle version/build/identity differs from this source. Build the candidate in isolation; do not test the owner installation.')
    if args.output.exists() and any(args.output.iterdir()): p.error('Choose a new output directory; preserve previous test evidence')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'kind': 'isolated-native-self-window-checks', 'source': source_state(),
              'binary_sha256': hashlib.sha256(app.read_bytes()).hexdigest(), 'runs': [],
              'bundle_version': info['CFBundleShortVersionString'], 'bundle_build': info['CFBundleVersion'],
              'fresh_user_permission_verified': False, 'probe_style': args.probe_style,
              'key_probe_requested': args.key_probe, 'observation_deadline_ms': 2000,
              'deadline_note': 'Polling stops scheduling at 2 s; an in-flight OS query can exceed that budget. Whole-process timeout is 40 s.'}
    with tempfile.TemporaryDirectory(prefix='contextlens-native-') as temp:
        root = Path(temp); demo = root/'demo'; gradient = root/'gradient'
        subprocess.run([str(cli), 'demo', str(demo)], check=True)
        if not args.closure_only: subprocess.run([str(cli), 'stress-fixture', str(gradient), '3', '--gradient'], check=True)
        for mode in ['dark'] if args.closure_only else ['dark', 'light']:
            appearance = ['-NSRequiresAquaSystemAppearance', 'YES' if mode == 'light' else 'NO']
            for tab in ['review'] if args.closure_only else ['review', 'mark-up', 'hand-off']:
                folder = args.output/f'{mode}-{tab}'; folder.mkdir(exist_ok=True)
                command = [str(app), '--isolated-native-test', '--session', str(demo), '--tab', tab, '--frame', 'frame-002',
                           '--snapshot-scale', '2', '--smoke-snapshot', str(folder/'window.png'), '--native-capture-test',
                           '--native-probe-style', args.probe_style, *appearance]
                if args.key_probe: command += ['--native-probe-key-window']
                if tab == 'mark-up': command += ['--zoom', '2']
                item = invoke(command)
                item['screenshot_exists'] = (folder/'window.png').is_file()
                probe = folder/'native-capture-verification.json'
                if probe.exists(): item['capture_verification'] = json.loads(probe.read_text())
                report['runs'].append(item)
            if not args.closure_only:
                path = args.output/f'{mode}-zoom.json'
                command = [str(app), '--isolated-native-test', '--session', str(gradient), '--tab', 'mark-up', '--frame', 'frame-002',
                           '--snapshot-scale', '2', '--exercise-zoom', str(path), *appearance]
                item = invoke(command)
                if path.exists(): item['zoom_verification'] = json.loads(path.read_text())
                report['runs'].append(item)
    results = [r.get('capture_verification', r.get('zoom_verification', {})).get('status') for r in report['runs']]
    report['status'] = 'passed' if all(r.get('exit_code') == 0 for r in report['runs']) and results and all(s == 'passed' for s in results) else 'incomplete-or-failed'
    (args.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(args.output/'results.json')
    return 0 if report['status'] == 'passed' else 1


def invoke(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=40)
        return dict(command=command, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired:
        return dict(command=command, status='timeout', reason='Native process exceeded 40 seconds; no integration pass claimed')


if __name__ == '__main__':
    raise SystemExit(main())
