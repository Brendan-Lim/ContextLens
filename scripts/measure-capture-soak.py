#!/usr/bin/env python3
"""Two sequential self-window capture runs. Never enumerates a target chosen from another app."""
import argparse
import datetime
import hashlib
import json
import os
import signal
from pathlib import Path
import platform
import re
import subprocess
import time
from source_state import ROOT, source_state

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--seconds', type=int, default=600)
p.add_argument('--output', type=Path, default=ROOT/'Benchmarks/reports/rigorous-testing/soak')
a = p.parse_args()
if not 1 <= a.seconds <= 600: p.error('Duration must be 1–600 seconds')
a.output.mkdir(parents=True, exist_ok=True)
app = ROOT/'dist/ContextLens.app/Contents/MacOS/ContextLens'
report = dict(kind='self-hosted-generated-capture-measurements', source=source_state(),
              binary_sha256=hashlib.sha256(app.read_bytes()).hexdigest(), machine=platform.platform(),
              measured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), runs=[])
for sensitivity in ['low', 'high']:
    output = a.output/f'{sensitivity}.json'
    command = [str(app), '--capture-soak', str(output), '--soak-seconds', str(a.seconds)]
    if sensitivity == 'low': command += ['--low-sensitivity']
    stdout = a.output/f'{sensitivity}.stdout.log'; stderr = a.output/f'{sensitivity}.resources.log'
    samples = []; start = time.monotonic()
    with stdout.open('w') as out, stderr.open('w') as err:
        proc = subprocess.Popen(['/usr/bin/time', '-l', *command], cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
        while proc.poll() is None and time.monotonic()-start < a.seconds+45:
            # The parent is /usr/bin/time; sample its direct child, the app instance launched here.
            child = subprocess.run(['pgrep', '-P', str(proc.pid)], capture_output=True, text=True).stdout.split()
            if child:
                ps = subprocess.run(['ps', '-p', child[0], '-o', '%cpu=,rss='], capture_output=True, text=True)
                numbers = ps.stdout.split()
                if len(numbers) == 2:
                    samples.append(dict(elapsed_seconds=time.monotonic()-start, cpu_percent=float(numbers[0]), rss_bytes=int(numbers[1])*1024))
            time.sleep(1)
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
    resources = stderr.read_text(); rss = re.search(r'(\d+)\s+maximum resident set size', resources)
    times = re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', resources)
    run = dict(sensitivity=sensitivity, command=command, exit_code=proc.returncode,
               wall_seconds=time.monotonic()-start, peak_rss_bytes=int(rss[1]) if rss else None, samples=samples,
               process_cpu_percent=(float(times[2])+float(times[3]))/float(times[1])*100 if times else None)
    if output.exists(): run['measurement'] = json.loads(output.read_text())
    report['runs'].append(run)
    (a.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'{sensitivity}: {run["wall_seconds"]:.1f}s, exit {proc.returncode}', flush=True)
print(a.output/'results.json')
