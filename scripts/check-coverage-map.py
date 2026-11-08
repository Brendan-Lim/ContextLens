#!/usr/bin/env python3
"""Fail if a new public type has no audit row; rows are a manual behavior audit, not line coverage."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
report = (root/'docs/testing-coverage.md').read_text()
types = []
for target in ['ContextLensCore', 'ContextLensImaging', 'ContextLensCapture']:
    for path in (root/'Sources'/target).glob('*.swift'):
        for name in re.findall(r'public\s+(?:(?:final|indirect)\s+)?(?:struct|enum|actor|class)\s+(\w+)', path.read_text()):
            types.append((target, name))
missing = [f'{target}.{name}' for target, name in types if f'| `{name}` |' not in report]
if missing: raise SystemExit('Missing coverage audit rows: ' + ', '.join(missing))
print(f'Coverage audit includes all {len(types)} public types. Behavioral completeness still requires review.')
