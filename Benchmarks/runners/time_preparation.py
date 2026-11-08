#!/usr/bin/env python3
"""Observe human preparation time; timestamps are never synthesized."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('key',help='TASK/CONDITION/TRIAL, e.g. 01/manual/1')
p.add_argument('folder',type=Path,help='Operator-created evidence folder containing task.md')
p.add_argument('--ledger',type=Path,default=Path('Benchmarks/preparations.json'))
a = p.parse_args()
input('Press Enter when you BEGIN preparing the report. ')
start = dt.datetime.now(dt.timezone.utc); clock = time.monotonic()
input('Prepare the report in the chosen workflow. Press Enter when the agent-ready task.md and evidence are COMPLETE. ')
end = dt.datetime.now(dt.timezone.utc)
if not (a.folder/'task.md').is_file(): raise SystemExit('Missing task.md; timing not recorded as a complete preparation.')
ledger = json.loads(a.ledger.read_text()) if a.ledger.exists() else {}
if a.key in ledger: raise SystemExit('This ledger key exists; choose a new trial number.')
ledger[a.key] = {'path':str(a.folder.resolve()),'T0':start.isoformat(),'T1':end.isoformat(),'active_human_seconds':None,'elapsed_seconds':time.monotonic()-clock,'operator_observed':True}
a.ledger.parent.mkdir(parents=True,exist_ok=True); a.ledger.write_text(json.dumps(ledger,indent=2)+'\n')
print('Recorded observed elapsed preparation. Active human effort remains unavailable unless independently measured.')
