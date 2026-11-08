#!/usr/bin/env python3
"""Replay recorded browser samples through production selection and compare saved states."""
import json
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
results=[]
for fixture in sorted((root/'Benchmarks/reports/browser-evidence').glob('*/events.json')):
    expected=json.loads((fixture.parent/'source-session/session.json').read_text())['frames']
    with tempfile.TemporaryDirectory(prefix='contextlens-replay-') as d:
        dest=Path(d)/'session'
        subprocess.run([str(root/'dist/contextlens-cli'),'replay',str(fixture),str(dest)],capture_output=True,check=True)
        actual=json.loads((dest/'session.json').read_text())['frames']
        if expected!=actual: raise SystemExit('Non-deterministic frame selection: '+str(fixture))
        for frame in actual:
            if (dest/frame['imagePath']).read_bytes() != (fixture.parent/'source-session'/frame['imagePath']).read_bytes():
                raise SystemExit('Image replay mismatch: '+str(fixture))
    results.append({'task':fixture.parent.name,'samples':len(json.loads(fixture.read_text())),'committed_states':len(actual),'passed':True})
(root/'Benchmarks/reports/replay-validation.json').write_text(json.dumps({'kind':'deterministic-replay-validation','fixtures':results},indent=2)+'\n')
print('Deterministic production replay passed for',len(results),'recorded fixtures')
