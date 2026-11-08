#!/usr/bin/env python3
"""Targeted publication scan. Reports filenames/line numbers, never matching values."""
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
args = ['git', '-C', str(root), 'ls-files', '-z']
if '--staged' in sys.argv:
    paths = subprocess.check_output(['git', '-C', str(root), 'diff', '--cached', '--name-only', '--diff-filter=ACM', '-z']).decode().split('\0')
else:
    paths = subprocess.check_output(args).decode().split('\0')
secret = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
errors = []
for name in filter(None, paths):
    path = root / name
    if not path.is_file(): continue
    if any(part in path.parts for part in ['node_modules', '.build', 'dist', '__pycache__']) or path.suffix in ['.p12', '.p8', '.mobileprovision'] or path.name.startswith('.env') and path.name != '.env.example':
        errors.append((name, 'generated/credential filename'))
    if name.startswith('Benchmarks/reports/') and not name.startswith('Benchmarks/reports/browser-evidence/'):
        errors.append((name, 'private benchmark output'))
    if re.match(r'Experiments/[^/]+/reports/', name): errors.append((name, 'private experiment output'))
    contents = subprocess.check_output(['git', '-C', str(root), 'show', ':' + name])
    if b'\0' in contents: continue
    for number, line in enumerate(contents.splitlines(), 1):
        if secret.search(line): errors.append((name, 'credential pattern at line ' + str(number)))
        if b'/private/var/folders/' in line and not name.startswith(('Tests/', 'scripts/')):
            errors.append((name, 'private temporary path at line ' + str(number)))
for name, reason in errors: print(name + ': ' + reason)
if errors: raise SystemExit('Publication scan failed; inspect findings without printing secret values.')
print('Targeted publication scan passed for ' + str(len([p for p in paths if p])) + ' indexed files. Manual metadata/image review is still required.')
