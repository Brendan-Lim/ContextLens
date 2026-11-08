#!/usr/bin/env python3
"""Descriptive paired results; failures, cached input and account-wide quota remain explicit."""
import argparse
import json
from pathlib import Path
import random
import statistics as stats
import compare_handoffs
import allowance_observation


def distribution(values):
    values=sorted(v for v in values if v is not None)
    if not values:return {'observations':0,'mean':None,'median':None,'range':None}
    return {'observations':len(values),'mean':stats.mean(values),'median':stats.median(values),'range':[values[0],values[-1]]}


def task_cluster_interval(pairs, metric):
    clusters={}
    for pair in pairs:
        value=pair['accepted_result_seconds_saved'] if metric=='seconds' else pair['tokens_saved_baseline_minus_lean'][metric]
        if value is not None:clusters.setdefault(pair['task'],[]).append(value)
    if len(clusters)<3:return None
    values=list(clusters.values());rng=random.Random(1729);samples=[]
    for _ in range(10000):
        selected=[rng.choice(values) for _ in values]
        samples.append(stats.mean(v for cluster in selected for v in cluster))
    samples.sort()
    return {'lower':samples[249],'upper':samples[9749],'tasks':len(values),'resamples':10000,'seed':1729,
            'method':'Exploratory percentile interval for mean paired saving, resampling tasks and retaining their repetitions together. Selected synthetic tasks do not establish population generalization.'}


def analyze(root):
    summary=compare_handoffs.summarize(root);rows=summary['individual_trials']
    folders={}
    for path in root.glob('*/result.json'):
        row=json.loads(path.read_text());folders[(row['task'],row['trial'],row['condition'])]=path.parent
    metrics=['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens','total_tokens']
    for row in rows:
        folder=folders[(row['task'],row['trial'],row['condition'])]
        events=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines() if line.strip()]
        commands=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
        row['completed_shell_calls']=len(commands)
        row['nonzero_shell_calls']=sum(c.get('exit_code') not in [None,0] for c in commands)
    groups={}
    for condition in ['baseline','lean']:
        selected=[r for r in rows if r['condition']==condition]
        groups[condition]={'attempts':len(selected),'accepted':sum(r.get('success',False) for r in selected),
            'usage_all_observed':{key:distribution([r.get('usage',{}).get(key) for r in selected]) for key in metrics},
            'execution_seconds_all_attempts':distribution([r.get('agent_execution_seconds') for r in selected]),
            'accepted_result_seconds_successes_only':distribution([r.get('agent_to_acceptance_seconds') for r in selected if r.get('success')]),
            'completed_shell_calls':distribution([r['completed_shell_calls'] for r in selected]),
            'nonzero_shell_calls':distribution([r['nonzero_shell_calls'] for r in selected])}
    pairs=[]
    for task,trial in sorted({(r['task'],r['trial']) for r in rows}):
        selected={r['condition']:r for r in rows if (r['task'],r['trial'])==(task,trial)}
        if len(selected)!=2:continue
        a,b=selected['baseline'],selected['lean'];both=a.get('success') and b.get('success')
        differences={}
        for key in metrics:
            x,y=a.get('usage',{}).get(key),b.get('usage',{}).get(key)
            differences[key]=x-y if x is not None and y is not None else None
        x,y=a.get('agent_to_acceptance_seconds'),b.get('agent_to_acceptance_seconds')
        pairs.append({'task':task,'trial':trial,'both_accepted':bool(both),'tokens_saved_baseline_minus_lean':differences,
                      'accepted_result_seconds_saved':x-y if both and x is not None and y is not None else None,
                      'shell_calls_saved':a['completed_shell_calls']-b['completed_shell_calls']})
    task_results=[]
    for task in sorted({p['task'] for p in pairs}):
        selected=[p for p in pairs if p['task']==task]
        task_results.append({'task':task,'pairs':len(selected),'both_accepted':sum(p['both_accepted'] for p in selected),
            'total_tokens_saved':distribution([p['tokens_saved_baseline_minus_lean']['total_tokens'] for p in selected]),
            'uncached_input_tokens_saved':distribution([p['tokens_saved_baseline_minus_lean']['uncached_input_tokens'] for p in selected]),
            'accepted_result_seconds_saved':distribution([p['accepted_result_seconds_saved'] for p in selected])})
    ordered=sorted(rows,key=lambda r:r.get('T2',''))
    quota=allowance_observation.compare(ordered[0]['allowance_before'],ordered[-1].get('allowance_after',{})) if ordered else None
    planned=len(json.loads((root/'plan.json').read_text())['rows'])
    result={'kind':'exploratory-handoff-comparison-analysis','trial_count':len(rows),'planned_trials':planned,
            'schedule_complete':len(rows)==planned,'groups':groups,'paired_results':pairs,'per_task_results':task_results,
            'paired_token_savings_all_observed':{key:distribution([p['tokens_saved_baseline_minus_lean'][key] for p in pairs]) for key in metrics},
            'paired_accepted_result_seconds_saved_successful_pairs':distribution([p['accepted_result_seconds_saved'] for p in pairs]),
            'exploratory_95pct_task_cluster_bootstrap':{key:task_cluster_interval(pairs,key) for key in ['total_tokens','uncached_input_tokens','seconds']},
            'allowance_observation':quota,'exact_per_trial_allowance':None,'human_preparation_time':None,'workspace_credit_cost':None,
            'limitations':['Six synthetic tasks with two repetitions are exploratory, not population evidence.',
                'Identical attached images control initial image exposure; combined overview viewing is not tested.',
                'Cache state, task order, machine load and provider latency can affect results.',
                'Account allowance readings are shared with this active conversation; no causal quota attribution.',
                'Target/regression acceptance is not general quality non-inferiority or independent visual review.',
                'No credit purchases/API billing; underlying Education workspace credit consumption/cost is unknown.']}
    (root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=compare_handoffs.BASE/'reports/lean-handoff/comparison')
    args=parser.parse_args();analyze(args.results);print(args.results/'analysis.json')
