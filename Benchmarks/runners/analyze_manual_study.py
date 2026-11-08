#!/usr/bin/env python3
"""Analyze only actual trials from the frozen manual-equivalent study; missing stays null."""
import argparse
import json
from pathlib import Path
import random
import statistics as stats
import manual_study as study

METRICS = ['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens',
           'reasoning_output_tokens','total_tokens','agent_execution_seconds','evaluation_seconds',
           'time_to_accepted_solution_seconds','turns','completed_shell_calls','failed_shell_calls','cost_usd']


def distribution(values):
    values=sorted(v for v in values if v is not None)
    return {'n':len(values),'mean':stats.mean(values) if values else None,
            'median':stats.median(values) if values else None,
            'sd':stats.stdev(values) if len(values)>1 else None,
            'min':min(values) if values else None,'max':max(values) if values else None}


def value(row, metric):
    if metric in ['completed_shell_calls','failed_shell_calls']:return row.get('activity',{}).get(metric)
    if metric.endswith('tokens') or metric in ['turns','cost_usd']:return row.get('usage',{}).get(metric)
    if metric=='time_to_accepted_solution_seconds' and not row.get('success'):return None
    return row.get(metric)


def cluster_interval(pairs, metric, percent=False):
    clusters={}
    for pair in pairs:
        r=pair['metrics'][metric]
        if r['difference_manual_minus_contextlens'] is not None:clusters.setdefault(pair['task'],[]).append(r)
    if len(clusters)<3:return None
    clusters=list(clusters.values());rng=random.Random(93218);samples=[]
    for _ in range(10000):
        selected=[r for _ in clusters for r in rng.choice(clusters)]
        a=stats.mean(r['manual'] for r in selected);b=stats.mean(r['contextlens'] for r in selected)
        if percent and not a:continue
        samples.append((a-b)/a*100 if percent else a-b)
    if not samples:return None
    samples.sort()
    return {'low':samples[int(.025*(len(samples)-1))],'high':samples[int(.975*(len(samples)-1))],
            'task_clusters':len(clusters),'bootstrap_draws':10000,'seed':93218,
            'scope':'Exploratory percentile interval; repetitions retained within sampled tasks; six selected tasks cannot establish population effects.'}


def analyze(root):
    rows=[];keys=set();identities=set()
    for file in sorted((root/'trials').glob('*/result.json')):
        row=json.loads(file.read_text())
        if row.get('kind')!='manual-equivalent-contextlens-agent-trial':raise ValueError('Unexpected study kind')
        key=(row['task'],row['trial'],row['condition'])
        if key in keys:raise ValueError('Duplicate trial key')
        keys.add(key)
        identities.add(tuple(json.dumps(row.get(k),sort_keys=True) for k in ['protocol_sha256','model','effort','identity','source_sha256']))
        row['artifact']=str(file.relative_to(root));rows.append(row)
    if len(identities)>1:raise ValueError('Do not pool different source/model/CLI/protocol settings')
    groups={}
    for condition in study.CONDITIONS:
        selected=[r for r in rows if r['condition']==condition]
        groups[condition]={'attempts':len(selected),'accepted':sum(bool(r.get('success')) for r in selected),
                           'failed_or_incomplete':sum(not r.get('success') for r in selected),
                           'metrics':{metric:distribution(value(r,metric) for r in selected) for metric in METRICS}}
    pairs=[]
    for task,trial in sorted({(r['task'],r['trial']) for r in rows}):
        selected={r['condition']:r for r in rows if (r['task'],r['trial'])==(task,trial)}
        if set(selected)!=set(study.CONDITIONS):continue
        a,b=selected['manual-equivalent'],selected['contextlens'];metrics={}
        for metric in METRICS:
            x,y=value(a,metric),value(b,metric)
            if metric=='time_to_accepted_solution_seconds' and not(a.get('success') and b.get('success')):x=y=None
            diff=x-y if x is not None and y is not None else None
            metrics[metric]={'manual':x,'contextlens':y,'difference_manual_minus_contextlens':diff,
                             'reduction_percent':100*diff/x if diff is not None and x else None}
        pairs.append({'task':task,'trial':trial,'both_accepted':bool(a.get('success') and b.get('success')),'metrics':metrics})
    comparisons={}
    for metric in METRICS:
        data=[p['metrics'][metric] for p in pairs if p['metrics'][metric]['difference_manual_minus_contextlens'] is not None]
        a=stats.mean(p['manual'] for p in data) if data else None
        b=stats.mean(p['contextlens'] for p in data) if data else None
        comparisons[metric]={'paired_differences':distribution(p['difference_manual_minus_contextlens'] for p in data),
            'mean_pair_reduction_percent':distribution(p['reduction_percent'] for p in data),
            'reduction_of_paired_means_percent':100*(a-b)/a if a else None,
            'task_cluster_95pct_difference':cluster_interval(pairs,metric),
            'task_cluster_95pct_percent':cluster_interval(pairs,metric,True)}
    categories={t['id']:t['category'] for t in json.loads(study.SPEC.read_text())['tasks']}
    strata={}
    for category in ['visual','interactive']:
        subset=[p for p in pairs if categories[p['task']]==category]
        strata[category]={metric:{'paired_savings':distribution(p['metrics'][metric]['difference_manual_minus_contextlens'] for p in subset),
                                   'interval':cluster_interval(subset,metric)}
                          for metric in ['total_tokens','uncached_input_tokens','time_to_accepted_solution_seconds']}
    result={'kind':'manual-equivalent-vs-contextlens-analysis',
        'status':'measured-exploratory' if rows else 'no-live-agent-data',
        'actual_attempt_records':len(rows),'model_invocations_started':sum(bool(r.get('T2')) for r in rows),
        'completed_agent_attempts':sum(r.get('status')=='completed' for r in rows),
        'planned_attempts':24,'matched_pairs':len(pairs),'both_accepted_pairs':sum(p['both_accepted'] for p in pairs),
        'groups':groups,'paired_comparisons':comparisons,'pairs':pairs,'strata':strata,'individual_trials':rows,
        'human_preparation_seconds':None,'human_workflow_seconds':None,'human_effort':None,
        'cost_usd':None,'exact_per_trial_allowance':None,
        'policy':'All attempts with observed usage retained, including failures/timeouts. Accepted-solution timing pairs require both arms accepted. Missing values are never zero. No human or cost inference from automated fixture preparation or token/file sizes.'}
    study.write(root/'analysis.json',result);study.write(root/'results.json',{'kind':result['kind'],'individual_trials':rows,'trial_count':len(rows)})
    return result


def charts(root,data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    folder=root/'charts';folder.mkdir(exist_ok=True)
    charts=[('total-tokens','Total provider-accounted tokens','total_tokens','Tokens'),
            ('uncached-input','Uncached input tokens','uncached_input_tokens','Tokens'),
            ('execution-time','CLI startup + agent execution','agent_execution_seconds','Seconds'),
            ('correctness','Independent acceptance rate',None,'Accepted attempts'),
            ('per-task-savings','Per-task paired token savings','paired','Manual-equivalent − ContextLens tokens')]
    for name,title,metric,label in charts:
        fig,ax=plt.subplots(figsize=(8,4.6));fig.patch.set_facecolor('white')
        if not data['actual_attempt_records']:
            ax.axis('off');ax.text(.5,.56,'UNMEASURED',ha='center',fontsize=22,fontweight='bold',transform=ax.transAxes)
            ax.text(.5,.38,'0 live agent trials\nNew-study usage authorization pending',ha='center',linespacing=1.6,color='#555',transform=ax.transAxes)
        elif metric=='paired':
            tasks=sorted({p['task'] for p in data['pairs']});labels=[];vals=[]
            for task in tasks:
                values=[p['metrics']['total_tokens']['difference_manual_minus_contextlens'] for p in data['pairs'] if p['task']==task]
                values=[v for v in values if v is not None]
                if values:labels.append(task);vals.append(stats.mean(values))
            ax.bar(labels,vals,color=['#227f78' if v>=0 else '#b35c48' for v in vals]);ax.axhline(0,color='#333',lw=.8);ax.set_xlabel('Fixture task (mean of retained paired repetitions)');ax.set_ylabel(label)
        elif metric is None:
            groups=[data['groups'][c] for c in study.CONDITIONS]
            vals=[g['accepted']/g['attempts']*100 if g['attempts'] else None for g in groups]
            for i,v in enumerate(vals):
                if v is not None:ax.bar(i,v,color=['#607f99','#227f78'][i]);ax.text(i,v+2,f"{groups[i]['accepted']}/{groups[i]['attempts']}",ha='center')
            ax.set_xticks([0,1],['Manual-equivalent','ContextLens']);ax.set_ylim(0,110);ax.set_ylabel('Accepted (%)');ax.text(.01,-.22,'Small selected sample; no general non-inferiority claim.',transform=ax.transAxes,fontsize=9)
        else:
            groups=[data['groups'][c]['metrics'][metric] for c in study.CONDITIONS]
            for i,g in enumerate(groups):
                if g['mean'] is not None:ax.bar(i,g['mean'],color=['#607f99','#227f78'][i]);ax.text(i,g['mean'],f"  n={g['n']}",ha='center',va='bottom')
                else:ax.text(i,0,'Unavailable',ha='center')
            ax.set_xticks([0,1],['Manual-equivalent','ContextLens']);ax.set_ylabel(label)
            ci=data['paired_comparisons'][metric]['task_cluster_95pct_difference']
            if ci:ax.text(.01,-.22,f"95% task-cluster interval for saving: {ci['low']:,.1f} to {ci['high']:,.1f}",transform=ax.transAxes,fontsize=9)
        ax.set_title(title,loc='left',fontweight='bold',pad=18)
        fig.tight_layout();fig.savefig(folder/f'{name}.png',dpi=220);fig.savefig(folder/f'{name}.svg');plt.close(fig)
    study.write(folder/'provenance.json',{'source':'../analysis.json','live_attempts':data['actual_attempt_records'],
          'human_preparation_chart':None,'reason':'No observed human timing; no zero-valued preparation bars',
          'unavailable_panels':'Status-only placeholders contain no fabricated measurements'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=study.DEFAULT);p.add_argument('--charts',action='store_true');a=p.parse_args()
    data=analyze(a.output)
    if a.charts:charts(a.output,data)
    print(json.dumps({k:data[k] for k in ['status','actual_attempt_records','matched_pairs']}))
