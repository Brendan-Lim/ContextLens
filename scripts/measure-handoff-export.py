#!/usr/bin/env python3
"""Counterbalanced export-only timing; synthetic local frames, no models or external captures."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import tempfile
import time
from source_state import ROOT, source_state


def run(command):
    started = time.perf_counter()
    result = subprocess.run(['/usr/bin/time', '-l', *command], cwd=ROOT,
                            capture_output=True, text=True, timeout=180)
    memory = re.search(r'(\d+)\s+maximum resident set size', result.stderr)
    return {'command': command, 'elapsed_seconds': time.perf_counter()-started,
            'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
            'peak_rss_bytes': int(memory[1]) if memory else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-cli', type=Path, default=ROOT/'.build/contextlens-cli-before-lean')
    parser.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/lean-handoff/export-performance-controlled.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output path; previous observations must be retained')
    executables = {'baseline': args.baseline_cli.resolve(), 'lean': ROOT/'dist/contextlens-cli'}
    report = {'kind': 'measured-handoff-export-only', 'source': source_state(),
              'measured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'machine': {'architecture': platform.machine(), 'macos': platform.mac_ver()[0],
                          'hardware_and_memory': subprocess.check_output(['sysctl', '-n', 'hw.model', 'hw.memsize'], text=True).strip()},
              'binary_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in executables.items()},
              'seed': 1729, 'runs': [], 'status': 'incomplete',
              'limitations': ['Synthetic compressible 1920x1200 images, one mark per state; not a real session.',
                             'Elapsed time includes CLI launch, export planning and /usr/bin/time overhead.',
                             'Three repetitions per condition are descriptive; cache/load variance remains possible.',
                             'Run after native checks/model trials have finished; no human/agent savings are inferred.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='contextlens-export-only-') as temp:
            root = Path(temp); fixture = root/'session'
            report['fixture'] = run([str(executables['lean']), 'stress-fixture', str(fixture), '100'])
            if report['fixture'].get('exit_code') != 0:
                raise RuntimeError('Fixture generation failed; inspect the retained command/output')
            rng = random.Random(1729)
            for repetition in range(1, 4):
                order = ['baseline', 'lean']; rng.shuffle(order)
                for name in order:
                    dest = root/f'{name}-{repetition}'
                    row = dict(condition=name, repetition=repetition,
                               **run([str(executables[name]), 'export', str(fixture), str(dest), '--all-frames', '--keep-duplicates']))
                    report['runs'].append(row)
                    if row.get('exit_code') != 0:
                        raise RuntimeError('Export failed; inspect the retained command/output')
                    row['package_bytes'] = sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())
            report['summary'] = {name: {
                'mean_elapsed_seconds': statistics.mean(r['elapsed_seconds'] for r in report['runs'] if r['condition'] == name),
                'mean_package_bytes': statistics.mean(r['package_bytes'] for r in report['runs'] if r['condition'] == name)
            } for name in executables}
            report['status'] = 'measured'
    finally:
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()
