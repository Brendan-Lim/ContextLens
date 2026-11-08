#!/bin/bash
set -euo pipefail
: "${RUNNER_TEMP:?}"
# Parse security's quoted paths without eval, preserving paths containing spaces.
python3 - <<'PY'
import os
from pathlib import Path
import shlex
import subprocess
root = Path(os.environ['RUNNER_TEMP'])
saved = root / 'contextlens-original-keychains.txt'
if saved.exists():
    subprocess.run(['security', 'list-keychains', '-d', 'user', '-s', *shlex.split(saved.read_text())], check=True)
keychain = root / 'contextlens-signing.keychain-db'
if keychain.exists(): subprocess.run(['security', 'delete-keychain', str(keychain)], check=True)
PY
