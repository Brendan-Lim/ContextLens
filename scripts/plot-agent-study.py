#!/usr/bin/env python3
"""Plot actual scripted-agent observations; never combine them with human-study placeholders."""
import json
import os
from pathlib import Path
import statistics as stats

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.build/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base=ROOT/'Benchmarks/reports/rigorous-testing/scripted-agent'
data=json.loads((base/'results.json').read_text())
conditions=['plain-screenshots','auto-only','contextlens']
rows=data['individual_trials']
for filename,key,title,ylabel in [
    ('tokens','usage.total_tokens','Actual agent tokens — eager image attachments','Provider-accounted total tokens (includes cached input)'),
    ('agent-time','agent_to_acceptance_seconds','Agent to accepted result — successes only','Seconds; human preparation excluded')]:
    fig,ax=plt.subplots(figsize=(9,5.8))
    fig.subplots_adjust(left=.12,right=.98,bottom=.18,top=.85)
    for index,condition in enumerate(conditions):
        values=[]
        for row in rows:
            if row['condition']!=condition:continue
            value=row.get('usage',{}).get('total_tokens') if key.startswith('usage.') else row.get(key)
            if value is not None:values.append(value)
        if not values:continue
        ax.bar(index,stats.mean(values),color=['#9ba8b6','#5d9eb7','#df965a'][index],width=.65,zorder=2)
        offsets=[(i-(len(values)-1)/2)*.045 for i in range(len(values))]
        ax.scatter([index+x for x in offsets],values,s=20,color='#263445',alpha=.7,zorder=3)
        ax.annotate(f'n={len(values)}',(index,0),xytext=(0,7),textcoords='offset points',ha='center',fontsize=10)
    ax.set_xticks(range(3),['Plain screenshots','Auto-only','ContextLens package'])
    ax.set_ylabel(ylabel);ax.set_title(title+'\nGPT-6.1 Sol / high; three generated task scopes',loc='left',fontsize=12)
    ax.grid(axis='y',alpha=.2,zorder=0);ax.spines[['top','right']].set_visible(False)
    fig.text(.01,.025,'Bars: arithmetic means. Points: individual attempts. Exploratory fixture study; no human-time claim.',fontsize=8,color='#555')
    fig.savefig(base/f'{filename}.svg');fig.savefig(base/f'{filename}.png',dpi=150);plt.close(fig)
print(base)
