#!/usr/bin/env python3
"""Identify the actual source tree even in an uncommitted/new repository."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def source_state():
    files = [ROOT / 'Package.swift']
    for folder in ['Sources', 'Tests', 'scripts', 'Benchmarks/runners', 'Benchmarks/tests']:
        files += [p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    build_digest = hashlib.sha256()
    for path in sorted([ROOT/'Package.swift', *(ROOT/'Sources').rglob('*.swift')]):
        build_digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    commit = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    return {'git_commit': commit.stdout.strip() if commit.returncode == 0 else None,
            'source_sha256': digest.hexdigest(), 'build_source_sha256': build_digest.hexdigest(),
            'source_scope': 'Package.swift, Sources, Tests, scripts, Benchmarks/runners, Benchmarks/tests; excludes caches',
            'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()}

if __name__ == '__main__':
    import json
    print(json.dumps(source_state(), indent=2))
