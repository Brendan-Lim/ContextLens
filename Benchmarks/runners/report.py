#!/usr/bin/env python3
"""Report actual live measurements; never substitute synthetic telemetry as results."""
import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import random
import statistics as stats

BASE=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(BASE.parent/'.build/matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME',str(BASE.parent/'.build/xdg-cache'))

CONDITIONS=['manual','auto-only','contextlens']
METRICS=[('Preparation time (s)','preparation_seconds'),('Input tokens','usage.input_tokens'),('Cached input tokens','usage.cached_input_tokens'),('Uncached input tokens','usage.uncached_input_tokens'),('Output tokens','usage.output_tokens'),('Total tokens','usage.total_tokens'),('Agent execution time (s)','agent_execution_seconds'),('End-to-end time (s)','end_to_end_seconds'),('Agent cost (USD)','usage.cost_usd'),('Success rate','success'),('Corrective iterations','corrective_iterations')]

def value(row,key):
    v=row
    for k in key.split('.'):
        if not isinstance(v,dict): return None
        v=v.get(k)
    return v if isinstance(v,(int,float,bool)) and math.isfinite(v) else None

def summary(values):
    if not values: return {'n':0,'mean':None,'median':None,'iqr':None}
    q=stats.quantiles(values,n=4,method='inclusive') if len(values)>1 else [values[0]]*3
    return {'n':len(values),'mean':stats.mean(values),'median':stats.median(values),'iqr':q[2]-q[0]}

def bootstrap(values, estimator=stats.median):
    if len(values)<10: return None
    rng=random.Random(1729)
    samples=sorted(estimator(rng.choices(values,k=len(values))) for _ in range(2000))
    return [samples[49],samples[1949]]

def aggregate(rows):
    # Never merge providers/models/reasoning settings into a same-agent conclusion.
    groups=defaultdict(list)
    fields = ('agent', 'model', 'effort', 'cli_version', 'source_sha256', 'timeout_seconds', 'node_version', 'command', 'platform')
    for r in rows: groups[tuple(str(r.get(k, 'unrecorded')) for k in fields)].append(r)
    result=[]
    for group,runs in sorted(groups.items()):
        block=dict(zip(fields, group), conditions={}, paired={})
        for c in sorted(set(r['condition'] for r in runs)):
            chosen=[r for r in runs if r['condition']==c]
            metrics={k:summary([value(r,k) for r in chosen if value(r,k) is not None]) for _,k in METRICS if k!='success'}
            metrics['success']={'attempted':len(chosen),'passed':sum(r['success'] for r in chosen),'rate':sum(r['success'] for r in chosen)/len(chosen)}
            metrics['failures_or_censored']=sum(not r['success'] for r in chosen)
            block['conditions'][c]=metrics
        paired=defaultdict(dict)
        for r in runs:
            key=(r['task'],r['trial']); condition=r['condition']
            if condition in paired[key]: raise ValueError('Duplicate live trial key; use distinct trial numbers')
            paired[key][condition]=r
        for _,metric in METRICS:
            if metric=='success': continue
            differences=[]; successful_differences=[]; ratios=[]; speedups=[]; paired_attempts=0; missing_pairs=0
            for pair in paired.values():
                a,b=pair.get('manual'),pair.get('contextlens')
                if not a or not b: continue
                paired_attempts += 1
                av,bv=value(a,metric),value(b,metric)
                if av is None or bv is None:
                    missing_pairs += 1; continue
                differences.append(bv-av)
                if a['success'] and b['success']:
                    successful_differences.append(bv-av)
                    if av>0: ratios.append((av-bv)/av*100)
                    if metric=='end_to_end_seconds' and bv>0: speedups.append(av/bv)
            block['paired'][metric]={'paired_attempts':paired_attempts,'missing_measurement_pairs':missing_pairs,
                'all_observed_savings_manual_minus_contextlens':summary([-x for x in differences]),
                'successful_pair_savings_manual_minus_contextlens':summary([-x for x in successful_differences]),
                'mean_savings_95pct_paired_bootstrap':bootstrap([-x for x in successful_differences], stats.mean),
                'all_observed_differences_contextlens_minus_manual':summary(differences),'successful_pair_differences':summary(successful_differences),'successful_pair_reduction_percent':summary(ratios),'end_to_end_speedup_manual_over_contextlens':summary(speedups) if metric=='end_to_end_seconds' else None,'median_difference_95pct_paired_bootstrap':bootstrap(successful_differences)}
        result.append(block)
    return result

def chart(output,filename,title,groups,key,ylabel):
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    if not groups:
        ax.axis('off'); ax.text(.5,.55,'Live benchmark pending',ha='center',va='center',fontsize=20)
        ax.text(.5,.38,'No measured agent trials. No values estimated.',ha='center',va='center',color='#555')
    else:
        width=.24; x=list(range(len(groups)))
        conditions = sorted({c for g in groups for c in g['conditions']})
        width = min(.24, .8/max(1,len(conditions)))
        for i,c in enumerate(conditions):
            values=[]
            for g in groups:
                m=g['conditions'].get(c,{}).get(key,{})
                values.append(m.get('rate') if key=='success' else m.get('median'))
            # NaN preserves missing data without making it look like a zero.
            ax.bar([p+(i-(len(conditions)-1)/2)*width for p in x],[v if v is not None else float('nan') for v in values],width,label=c)
        ax.set_xticks(x,['%s\n%s\n%s'%(g['agent'],g['model'],g['effort']) for g in groups]); ax.legend(); ax.set_ylabel(ylabel)
    ax.set_title(title); fig.savefig(output/(filename+'.svg')); fig.savefig(output/(filename+'.png'),dpi=160); plt.close(fig)

def main():
    import matplotlib
    matplotlib.use('Agg')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,default=BASE/'runs');p.add_argument('--output',type=Path,default=BASE/'reports');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for f in sorted(a.runs.glob('*/result.json')):
        r=json.loads(f.read_text())
        if r.get('kind')=='live-agent-trial': rows.append(r)
    groups=aggregate(rows)
    data={'kind':'actual-benchmark-results','status':'measured' if rows else 'live-trials-pending','trial_count':len(rows),'groups':groups,'individual_tasks':rows,'synthetic_telemetry_included':False}
    (a.output/'results.json').write_text(json.dumps(data,indent=2)+'\n')
    lines=['# ContextLens operator-timed workflow benchmark report','','## Evidence status','',f'Live agent trials: **{len(rows)}**. Synthetic parser fixtures are excluded from all comparisons.','Human preparation, provider tokens, agent cost and fix accuracy are unavailable until operator-timed live trials are recorded. No savings are established.' if not rows else 'All attempts, including failures and timeouts, are retained. Failed time-to-success observations are censored, not assigned zero.','', '## Workflow comparison','', 'Values are medians [IQR] across available measurements, except success rates. Missing values are N/A, not zero. End-to-end medians describe successes only; always read them beside failure counts.','']
    blocks=groups or [{'agent':'pending','model':'pending','effort':'pending','conditions':{}}]
    for g in blocks:
        lines += [f"### {g['agent']} / {g['model']} / {g['effort']}",'','| Metric | Manual | Auto-only | ContextLens | Difference |','|---|---:|---:|---:|---:|']
        for label,key in METRICS:
            cells=[]
            for c in CONDITIONS:
                v=g['conditions'].get(c,{}).get(key,{})
                if key=='success': cells.append(f"{v['passed']}/{v['attempted']} ({v['rate']:.1%})" if v else 'N/A')
                else: cells.append(f"{v['median']:.3f} [{v['iqr']:.3f}] n={v['n']}" if v.get('median') is not None else 'N/A')
            d=g.get('paired',{}).get(key,{}).get('all_observed_differences_contextlens_minus_manual',{})
            difference=f"{d['median']:+.3f} (paired median)" if d.get('median') is not None else 'N/A'
            lines.append('| '+label+' | '+' | '.join(cells)+' | '+difference+' |')
        lines += ['', '| Paired savings (Manual − ContextLens) | Mean, all observed | Mean, both successful | Observed / attempted pairs |', '|---|---:|---:|---:|']
        for label, key in [('Total tokens', 'usage.total_tokens'), ('Preparation seconds', 'preparation_seconds'), ('End-to-end seconds', 'end_to_end_seconds')]:
            paired = g.get('paired', {}).get(key, {})
            all_obs = paired.get('all_observed_savings_manual_minus_contextlens', {})
            successful = paired.get('successful_pair_savings_manual_minus_contextlens', {})
            fmt = lambda v: 'N/A' if v is None else f'{v:+.3f}'
            lines.append(f"| {label} | {fmt(all_obs.get('mean'))} | {fmt(successful.get('mean'))} | {all_obs.get('n',0)} / {paired.get('paired_attempts',0)} |")
        lines += ['', 'Positive savings favor ContextLens; negative values mean it used more. Failed attempts remain in all-observed token accounting. Missing usage is excluded with its count shown. Means and medians answer different questions; no savings are inferred from bytes.', '']
    lines += ['## Individual task results','','| Task | Agent / model | Trial | Workflow | Success | Tokens | Prep (s) | Agent (s) | End-to-end (s) |','|---|---|---:|---|---|---:|---:|---:|---:|']
    if not rows: lines.append('| Live trials pending | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |')
    for r in rows:
        vals=[r['task'],r['agent']+' / '+r['model'],r['trial'],r['condition'],r['success'],value(r,'usage.total_tokens'),value(r,'preparation_seconds'),value(r,'agent_execution_seconds'),value(r,'end_to_end_seconds')]
        lines.append('| '+' | '.join('N/A' if v is None else str(v) for v in vals)+' |')
    lines += ['','## No-cost validation','','These are fixture/evaluator checks, not coding-agent successes.']
    fixture=BASE/'reports/fixture-validation.json'
    if fixture.exists():
        f=json.loads(fixture.read_text());lines += [f"- Broken controls rejected: {sum(not x['passed'] for x in f['broken'])}/{len(f['broken'])}.",f"- Known-good controls accepted: {sum(x['passed'] for x in f['fixed'])}/{len(f['fixed'])}."]
    perf=BASE/'reports/frame-comparison.json'
    if perf.exists():
        f=json.loads(perf.read_text()); lines += [f"- Regional comparison microbenchmark: {f['samples']} comparisons at {f['width']}×{f['height']}, {f['mean_ms']:.4f} ms mean on this machine. This excludes screen capture, decoding, encoding, UI work and peak memory."]
    strategy=BASE/'reports/strategy-measurements.json'
    if strategy.exists():
        payload=json.loads(strategy.read_text());lines += ['','## Export strategies: measured initial filesystem payload','','| Strategy | Images initially offered | Initial bytes | Actual input/output tokens | Agent time | Success |','|---|---:|---:|---|---|---|']
        names=['all-frames','deduplicated','annotated','manifest-first'];totals=[]
        for name in names:
            subset=[r for r in payload if r['strategy']==name];n=sum(r['initial_image_count'] for r in subset);size=sum(r['initial_payload_bytes'] for r in subset);totals.append(size)
            lines.append(f'| {name} | {n} | {size:,} | N/A | N/A | N/A |')
        lines += ['','Measured over ten scripted browser fixtures from the same capture events. All-frames includes repeated samples. Deduplicated uses the production selector. Annotated offers one relevant overlay per issue. Manifest-first measures the initial text only; subsequent image reads are not counted in its initial payload. This is not a token or runtime comparison, and no best agent strategy can be identified.']
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained');ax.bar(names,totals,color=['#a8b4c4','#82b7cb','#59bda5','#426885']);ax.set_ylabel('Initial filesystem bytes (10 fixtures)');ax.set_title('Measured payload, not model tokens');fig.savefig(a.output/'strategy-payload.svg');fig.savefig(a.output/'strategy-payload.png',dpi=160);plt.close(fig)
    for name,title,key,label in [('tokens','Agent token consumption','usage.total_tokens','Tokens'),('completion-time','End-to-end time (successful trials)','end_to_end_seconds','Seconds'),('preparation-time','Observed human preparation time','preparation_seconds','Seconds'),('success-rate','Agent acceptance success rate','success','Fraction')]: chart(a.output,name,title,groups,key,label)
    valid=[r for r in rows if value(r,'usage.total_tokens') is not None and value(r,'end_to_end_seconds') is not None]
    if len(valid)>=6:
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
        for c in CONDITIONS:
            chosen=[r for r in valid if r['condition']==c]; ax.scatter([value(r,'usage.total_tokens') for r in chosen],[r['end_to_end_seconds'] for r in chosen],label=c)
        ax.set_xlabel('Tokens');ax.set_ylabel('End-to-end seconds');ax.legend();fig.savefig(a.output/'tokens-vs-time.svg');plt.close(fig)
    lines += ['','## Interpretation and limits','','No human-preparation savings, token savings, end-to-end speedup, first-attempt accuracy improvement, or best export strategy is established without paired live trials. Payload size does not estimate image-token usage. Compare within the same agent, model and effort before considering cross-provider results.','', 'Live results must record the CLI versions, fixed source hash/commit, complete stdout/stderr traces, invocation, timings, acceptance results and patch. Report T1–T2 queue delay separately; do not compare stale prepared tasks with immediate handoffs. Twelve baseline-passing structural and interaction guards provide partial regression checks. Unrelated tasks also contain deliberate defects, so full regression assurance still needs human review.','', 'Paired differences (ContextLens − Manual), successful-pair reduction percentages and median/IQR are in results.json. Bootstrap intervals appear only at ≥10 paired successes; smaller samples are exploratory. Failures remain in overall token and cost summaries.','', '## Reproduction','','See [benchmark protocol](../README.md). The default harness emits a seeded plan without starting an agent. Explicit operator timing, model selection and --live --allow-paid are required for paid trials.','']
    (a.output/'benchmark-report.md').write_text('\n'.join(lines))
    print('Reported %d actual live trials; synthetic usage excluded.'%len(rows))
if __name__=='__main__': main()
