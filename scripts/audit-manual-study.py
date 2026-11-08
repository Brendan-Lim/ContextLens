#!/usr/bin/env python3
"""Post-study integrity/activity inventory. Does not edit attempts or rescore acceptance."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import statistics as stats
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Benchmarks/runners'))
import manual_study as study

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,default=study.DEFAULT/'study-v2')
a=p.parse_args();root=a.output;rows=[];timing=[]
for file in sorted((root/'trials').glob('*/result.json')):
    r=json.loads(file.read_text());folder=file.parent
    trace=(folder/'trace.jsonl').read_text()
    events=[json.loads(line) for line in trace.splitlines() if line.strip()]
    usage=study.telemetry.codex(trace)
    commands=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
    tests=[]
    # These are explicit recognizable source-validation commands, not inferred reasoning turns.
    for item in commands:
        command=item['command']
        for pattern in [r'git diff --check',r'node --check\s+[\w./-]+',r'python3? -m unittest[^;\n]*',r'npm test[^;\n]*']:
            tests.extend(re.findall(pattern,command))
    counts=Counter(tests)
    image=folder/'project'/r['attached_image']['path']
    expected=json.loads((folder/'evidence-manifest.json').read_text())
    actual=study.fingerprint(folder/'project/evidence')
    wall=(dt.datetime.fromisoformat(r['T3'])-dt.datetime.fromisoformat(r['T2'])).total_seconds() if r.get('T3') else None
    mono=r.get('agent_execution_seconds')
    difference=wall-mono if wall is not None and mono is not None else None
    timing.append({'trial':folder.name,'task':r['task'],'condition':r['condition'],'trial_number':r['trial'],
        'utc_wall_execution_seconds':wall,'recorded_monotonic_execution_seconds':mono,
        'wall_minus_monotonic_seconds':difference,'clock_discrepancy_over_1_second':abs(difference)>1 if difference is not None else None,
        'utc_wall_to_acceptance_seconds':(dt.datetime.fromisoformat(r['T4'])-dt.datetime.fromisoformat(r['T2'])).total_seconds() if r.get('T4') else None,
        'accepted':r['success'],'timed_out':r.get('timed_out',False)})
    rows.append({'trial':folder.name,'task':r['task'],'condition':r['condition'],'trial_number':r['trial'],
        'baseline_commit':r['baseline_commit'],'usage_reparse_matches':usage==r['usage'],
        'primary_image_hash_matches':hashlib.sha256(image.read_bytes()).hexdigest()==r['attached_image']['sha256'],
        'evidence_unmodified':expected==actual,'files_changed':r['files_changed'],
        'commands':[{'command':c['command'],'exit_code':c.get('exit_code'),'status':c.get('status')} for c in commands],
        'recognizable_validation_commands':dict(counts),
        'literal_recognizable_validation_reruns':sum(max(n-1,0) for n in counts.values()),
        'test_rerun_scope':'Exact recognizable command repetitions only. Inline test programs and semantic equivalence of different commands are not inferred. Independent evaluator runs once per attempt.',
        'completed_file_change_items':sum(e.get('type')=='item.completed' and e.get('item',{}).get('type')=='file_change' for e in events),
        'human_corrective_prompts':0,'internal_reasoning_iterations':None,'primary_accepted':r['success']})
result={'kind':'post-study-integrity-and-trace-activity-audit','rows':rows,
    'all_usage_reparse_matches':all(r['usage_reparse_matches'] for r in rows),
    'all_primary_image_hashes_match':all(r['primary_image_hash_matches'] for r in rows),
    'all_evidence_unmodified':all(r['evidence_unmodified'] for r in rows),
    'same_initial_fixture_commit':len({r['baseline_commit'] for r in rows})==1,
    'primary_results_unchanged':True,
    'review_limit':'Inventory supports unblinded patch/trace review; it is not human visual acceptance or an extra corrective trial.'}
study.write(root/'trace-activity-audit.json',result)
by_pair={}
for row in timing:by_pair.setdefault((row['task'],row['trial_number']),{})[row['condition']]=row
sensitivities={}
for name,exclude_anomalies in [('all_matched',False),('posthoc_non_anomalous_pairs',True)]:
    selected=[]
    for pair in by_pair.values():
        if set(pair)!=set(study.CONDITIONS):continue
        if exclude_anomalies and any(r['clock_discrepancy_over_1_second'] for r in pair.values()):continue
        selected.append(pair)
    sensitivities[name]={}
    for field in ['utc_wall_execution_seconds','recorded_monotonic_execution_seconds']:
        x=[p['manual-equivalent'][field] for p in selected];y=[p['contextlens'][field] for p in selected]
        m,n=(stats.mean(x),stats.mean(y)) if x else (None,None)
        sensitivities[name][field]={'pairs':len(selected),'manual_mean':m,'contextlens_mean':n,
             'mean_saving':m-n if m is not None else None,'percent_reduction':100*(m-n)/m if m else None}
study.write(root/'timing-audit.json',{'kind':'post-study-clock-reconciliation','rows':timing,'sensitivity':sensitivities,
    'anomalies':[r for r in timing if r['clock_discrepancy_over_1_second']],
    'scope':'Derived from immutable UTC T2/T3/T4 and stored monotonic durations. The >1s diagnostic and exclusion sensitivity are post hoc. Sleep/suspension or wall-clock adjustment are possible, not established causes. Preserve all failures and raw fields; do not attribute gaps to the product or provider.'})
assert all(result[k] for k in ['all_usage_reparse_matches','all_primary_image_hashes_match','all_evidence_unmodified','same_initial_fixture_commit'])
print(f'Checked integrity and recorded commands for {len(rows)} revised trials.')
