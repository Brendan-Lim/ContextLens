#!/usr/bin/env python3
"""Background self-window checks only; no activation or external window capture."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from source_state import ROOT, source_state

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/rigorous-testing/native')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
app = ROOT/'dist/ContextLens.app/Contents/MacOS/ContextLens'
cli = ROOT/'dist/contextlens-cli'
report = {'kind':'native-self-window-checks','source':source_state(),'binary_sha256':hashlib.sha256(app.read_bytes()).hexdigest(),'runs':[]}
with tempfile.TemporaryDirectory(prefix='contextlens-native-') as temp:
    root = Path(temp); demo = root/'demo'; gradient = root/'gradient'
    subprocess.run([str(cli), 'demo', str(demo)], check=True)
    subprocess.run([str(cli), 'stress-fixture', str(gradient), '3', '--gradient'], check=True)
    for mode in ['dark', 'light']:
        appearance = ['-NSRequiresAquaSystemAppearance', 'YES' if mode == 'light' else 'NO']
        for tab in ['review', 'mark-up', 'hand-off']:
            folder = a.output/f'{mode}-{tab}'; folder.mkdir(exist_ok=True)
            command = [str(app), '--session', str(demo), '--tab', tab, '--frame', 'frame-002', '--snapshot-scale', '2',
                       '--smoke-snapshot', str(folder/'window.png'), '--native-capture-test', *appearance]
            if tab == 'mark-up': command += ['--zoom', '2']
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=40)
                item = dict(command=command, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr,
                            screenshot_exists=(folder/'window.png').is_file())
                probe = folder/'native-capture-verification.json'
                if probe.exists(): item['capture_verification'] = json.loads(probe.read_text())
            except subprocess.TimeoutExpired as error:
                item = dict(command=command, status='timeout', stdout=str(error.stdout), stderr=str(error.stderr))
            report['runs'].append(item)
        path = a.output/f'{mode}-zoom.json'
        command = [str(app), '--session', str(gradient), '--tab', 'mark-up', '--frame', 'frame-002', '--snapshot-scale', '2', '--exercise-zoom', str(path), *appearance]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=40)
            item = dict(command=command, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            if path.exists(): item['zoom_verification'] = json.loads(path.read_text())
        except subprocess.TimeoutExpired as error:
            item = dict(command=command, status='timeout', stdout=str(error.stdout), stderr=str(error.stderr))
        report['runs'].append(item)
(a.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
print(a.output/'results.json')
