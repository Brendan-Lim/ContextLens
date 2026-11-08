#!/usr/bin/env python3
"""Publication plots with explicit cohorts, missing usage and clock-interruption warnings."""
import json
from pathlib import Path
import statistics as stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]/'Benchmarks/reports/manual-vs-contextlens/study-v2'
a=json.loads((ROOT/'analysis.json').read_text());t=json.loads((ROOT/'timing-audit.json').read_text())
out=ROOT/'charts';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
COLORS=['#637f95','#227f78'];LABELS=['Manual-equivalent','ContextLens']


def save(fig,name):
    fig.savefig(out/f'{name}.png',dpi=240,facecolor='white');fig.savefig(out/f'{name}.svg',facecolor='white');plt.close(fig)


def bars(ax,values,title,ylabel):
    ax.bar([0,1],values,color=COLORS,width=.58)
    ax.set_xticks([0,1],LABELS);ax.set_title(title,loc='left',fontsize=12,fontweight='bold',pad=14);ax.set_ylabel(ylabel)
    ax.set_ylim(0,max(values)*1.19);ax.yaxis.grid(True,alpha=.16);ax.set_axisbelow(True)
    for i,v in enumerate(values):ax.text(i,v+max(values)*.025,f'{v:,.1f}',ha='center',fontsize=11)


for metric,name,title in [('total_tokens','total-tokens','Total provider-accounted tokens'),('uncached_input_tokens','uncached-input','Uncached input tokens')]:
    pairs=[p['metrics'][metric] for p in a['pairs'] if p['metrics'][metric]['difference_manual_minus_contextlens'] is not None]
    values=[stats.mean(p[k] for p in pairs) for k in ['manual','contextlens']]
    fig,ax=plt.subplots(figsize=(8,5));bars(ax,values,title,'Mean tokens per attempt in matched pairs')
    ci=a['paired_comparisons'][metric]['task_cluster_95pct_difference']
    fig.text(.12,.105,f"{len(pairs)} matched pairs with observed usage. One timed-out pair has unknown usage.",fontsize=9,color='#444')
    fig.text(.12,.065,f"95% task-cluster interval, Manual − ContextLens: {ci['low']:,.0f} to {ci['high']:,.0f} tokens.",fontsize=9,color='#444')
    fig.subplots_adjust(bottom=.24,top=.88,left=.13,right=.96);save(fig,name)

fig,axes=plt.subplots(1,3,figsize=(13,5.3))
raw=t['sensitivity']['all_matched']['recorded_monotonic_execution_seconds']
stable=t['sensitivity']['posthoc_non_anomalous_pairs']['recorded_monotonic_execution_seconds']
accepted=[p['metrics']['time_to_accepted_solution_seconds'] for p in a['pairs'] if p['both_accepted']]
bars(axes[0],[raw['manual_mean'],raw['contextlens_mean']],f"Raw execution · {raw['pairs']} pairs",'Recorded monotonic seconds')
bars(axes[1],[stable['manual_mean'],stable['contextlens_mean']],f"Clock-stable sensitivity · {stable['pairs']} pairs",'Recorded monotonic seconds')
bars(axes[2],[stats.mean(p[k] for p in accepted) for k in ['manual','contextlens']],f"Both accepted · {len(accepted)} pairs",'Invocation through evaluator (s)')
for ax in axes:ax.set_xticklabels(['Manual-equiv.','ContextLens'],fontsize=9)
fig.suptitle('Agent timing: interrupted attempts change the apparent result',x=.065,ha='left',fontsize=15,fontweight='bold')
fig.text(.065,.115,'Raw data include an interrupted manual timeout: 300 s monotonic versus 18,264 s between UTC timestamps.',fontsize=10,color='#973e30')
fig.text(.065,.073,'Middle panel is post hoc diagnostic sensitivity, not a replacement score. Right panel excludes both failed pairs.',fontsize=9,color='#444')
ci=a['paired_comparisons']['time_to_accepted_solution_seconds']['task_cluster_95pct_difference']
fig.text(.065,.033,f"Accepted-pair saving 95% task-cluster interval: {ci['low']:.2f} to {ci['high']:.2f} s. Human preparation is unmeasured.",fontsize=9,color='#444')
fig.subplots_adjust(bottom=.29,top=.78,left=.065,right=.98,wspace=.43);save(fig,'execution-time')

fig,ax=plt.subplots(figsize=(8,5))
groups=[a['groups'][c] for c in ['manual-equivalent','contextlens']]
rates=[100*g['accepted']/g['attempts'] for g in groups]
bars(ax,rates,'Frozen independent acceptance','Accepted attempts (%)');ax.set_ylim(0,115)
for i,g in enumerate(groups):ax.text(i,20,f"{g['accepted']} / {g['attempts']} attempts",ha='center',color='white',fontweight='bold')
fig.text(.12,.105,'Manual failures: one border-box contract failure; one interrupted timeout.',fontsize=9,color='#444')
fig.text(.12,.065,'Selected tasks, repeated attempts, no general quality non-inferiority conclusion.',fontsize=9,color='#444')
fig.subplots_adjust(bottom=.24,top=.88,left=.13,right=.96);save(fig,'correctness')

tasks=sorted({p['task'] for p in a['pairs']});values=[];labels=[]
for task in tasks:
    xs=[p['metrics']['total_tokens']['difference_manual_minus_contextlens'] for p in a['pairs'] if p['task']==task]
    xs=[x for x in xs if x is not None];values.append(stats.mean(xs));labels.append(f'{task}\n(n={len(xs)})')
fig,ax=plt.subplots(figsize=(8,5));ax.barh(labels,values,color=['#227f78' if v>=0 else '#b25e49' for v in values]);ax.axvline(0,color='#444',lw=.8)
ax.invert_yaxis();ax.set_xlabel('Mean paired token saving: Manual-equivalent − ContextLens');ax.set_title('Per-task outcomes vary',loc='left',fontweight='bold',pad=16)
fig.text(.13,.075,'Positive favours ContextLens; negative favours manual-equivalent. Missing usage is not zero.',fontsize=9,color='#444')
fig.subplots_adjust(bottom=.2,top=.88,left=.13,right=.96);save(fig,'per-task-savings')
(out/'provenance.json').write_text(json.dumps({'kind':'actual-data-publication-plots','sources':['../analysis.json','../timing-audit.json'],
    'token_chart_matched_pairs':len([p for p in a['pairs'] if p['metrics']['total_tokens']['difference_manual_minus_contextlens'] is not None]),
    'raw_time_pairs':11,'accepted_time_pairs':len(accepted),'timing_sensitivity':'Post hoc clock-diagnostic exclusion, explicitly labelled',
    'human_preparation_chart':None,'reason':'No observed human preparation','bootstrap':'10000 task-cluster resamples, seed 93218; repetitions retained'},indent=2)+'\n')
print(out)
