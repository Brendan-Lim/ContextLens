#!/usr/bin/env python3
"""Repeatable generated workloads; no external window capture or agent execution."""
import argparse
import datetime
import json
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time
from source_state import ROOT, source_state


def run(command, timeout=180):
    start = time.perf_counter()
    try:
        result = subprocess.run(['/usr/bin/time', '-l', *command], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        memory = re.search(r'(\d+)\s+maximum resident set size', result.stderr)
        return dict(command=command, elapsed_seconds=time.perf_counter()-start, exit_code=result.returncode,
                    peak_rss_bytes=int(memory[1]) if memory else None, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as error:
        return dict(command=command, elapsed_seconds=time.perf_counter()-start, status='timeout',
                    stdout=(error.stdout or b'').decode(), stderr=(error.stderr or b'').decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/rigorous-testing/performance.json')
    parser.add_argument('--baseline-cli', type=Path)
    args = parser.parse_args()
    cli = str(ROOT/'dist/contextlens-cli')
    sysctl = subprocess.run(['sysctl', '-n', 'hw.model', 'hw.memsize'], capture_output=True, text=True)
    report = dict(kind='measured-generated-workloads', measured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  source=source_state(), machine={'architecture':platform.machine(), 'macos':platform.mac_ver()[0],
                    'hardware_and_memory':sysctl.stdout.strip() or None, 'hardware_probe_error':sysctl.stderr.strip() or None},
                  limitations=['Generated, compressible 1920x1200 fixtures; not a human workflow.',
                    'Image work excludes typing-to-display latency and SwiftUI layout.',
                    'No human preparation or provider tokens are estimated.',
                    'No committed HEAD exists when git_commit is null; source_sha256 identifies the measured tree.'], runs=[])
    with tempfile.TemporaryDirectory(prefix='contextlens-performance-') as temp:
        root = Path(temp)
        for count in [100, 500]:
            fixture = root/f'session-{count}'
            generation = run([cli, 'stress-fixture', str(fixture), str(count)])
            report['runs'].append(dict(workload=f'generate-{count}', **generation))
            if generation.get('exit_code') != 0: continue
            for repetition in range(3):
                result = run([cli, 'profile-images', str(fixture)])
                if result.get('exit_code') == 0: result['measurement'] = json.loads(result['stdout'])
                report['runs'].append(dict(workload=f'images-{count}', repetition=repetition+1, **result))
            if count == 100:
                for name, executable in [('before', args.baseline_cli), ('after', Path(cli))]:
                    if executable is None: continue
                    for repetition in range(3):
                        destination = root/f'export-{name}-{repetition}'
                        result = run([str(executable.resolve()), 'export', str(fixture), str(destination), '--all-frames', '--keep-duplicates'])
                        result['package_bytes'] = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
                        report['runs'].append(dict(workload=f'export-100-{name}', repetition=repetition+1, **result))
        result = run([cli, 'profile'])
        if result.get('exit_code') == 0: result['measurement'] = json.loads(result['stdout'])
        report['runs'].append(dict(workload='comparator', **result))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(args.output)

if __name__ == '__main__': main()
