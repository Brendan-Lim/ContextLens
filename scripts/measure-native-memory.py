#!/usr/bin/env python3
"""Actual app startup/snapshot resource use for generated 500-state sessions."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time
from source_state import ROOT, source_state

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline-app', type=Path, required=True)
p.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/rigorous-testing/native-memory')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
apps = {'before': a.baseline_app.resolve()/'Contents/MacOS/ContextLens', 'after': ROOT/'dist/ContextLens.app/Contents/MacOS/ContextLens'}
report = dict(kind='native-generated-500-state-startup', source=source_state(), machine=platform.platform(),
              binary_sha256={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in apps.items()},
              limitations='Wall time includes the fixed 3-second smoke delay and snapshot rendering; not typing latency or FPS. Generated compressible 1920x1200 images. Before/after launch order alternates; three Mark Up repetitions.', runs=[])
with tempfile.TemporaryDirectory(prefix='contextlens-native-memory-') as temp:
    session = Path(temp)/'session'
    subprocess.run([str(ROOT/'dist/contextlens-cli'), 'stress-fixture', str(session), '500'], check=True)
    for tab in ['mark-up', 'review']:
        for repetition in range(3 if tab == 'mark-up' else 1):
            for name in (['before', 'after'] if repetition % 2 == 0 else ['after', 'before']):
                output = a.output/f'{name}-{tab}-{repetition+1}.png'
                command = [str(apps[name]), '--session', str(session), '--tab', tab, '--frame', 'frame-002', '--snapshot-scale', '2', '--smoke-snapshot', str(output)]
                start = time.perf_counter()
                try:
                    result = subprocess.run(['/usr/bin/time', '-l', *command], capture_output=True, text=True, timeout=90)
                    memory = re.search(r'(\d+)\s+maximum resident set size', result.stderr)
                    item = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr, peak_rss_bytes=int(memory[1]) if memory else None)
                except subprocess.TimeoutExpired as error:
                    item = dict(status='timeout', stdout=str(error.stdout), stderr=str(error.stderr))
                report['runs'].append(dict(build=name, tab=tab, repetition=repetition+1, command=command, elapsed_seconds=time.perf_counter()-start, **item))
                (a.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
print(a.output/'results.json')
