"""Reproduce descriptive matched metrics from retained live records only.

Complements the frozen analyzer; it never invokes an agent or changes a trial.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics as stats

BASE=Path(__file__).resolve().parent
import analyze

USAGE=['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens','total_tokens','cost_usd']
ACTIVITY=['sourceDiscoveryCommands','filesInspectedRecognizedLowerBound','sourceReadOccurrences','repeatedReadOccurrences',
          'completedShellCommands','failedShellCommands','testExecutionsRecognized','commandOutputUTF8Bytes','sourceFilesModified',
          'applicationSourceFilesRead','applicationSourceReadOccurrences']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def distribution(values):
    values=[v for v in values if v is not None]
    return {'n':len(values),'mean':stats.mean(values) if values else None,'median':stats.median(values) if values else None,'min':min(values) if values else None,'max':max(values) if values else None}
def reduction(a,b):return (a-b)/a*100 if a is not None and b is not None and a!=0 else None

def summarize(folder):
    folder=folder.resolve()
    primary=analyze.analyze(folder);plan=json.loads((folder/'plan.json').read_text())
    comparison=json.loads((BASE/'reports/packages/comparison.json').read_text())
    hints={r['task']:r['source']['file'] for r in comparison['rows']}
    truth=json.loads((BASE/'reports/ground-truth.json').read_text())['publicSourceFiles']
    rows=[]
    for scheduled in plan['rows']:
        uid=f"{scheduled['task']}-{scheduled['condition']}-{scheduled['repeat']}";file=folder/'trials'/uid/'result.json'
        if not file.exists():
            rows.append(dict(scheduled,uid=uid,status='not-executed',success=None,metrics={},evidence=None));continue
        r=json.loads(file.read_text());activity=r.get('activity',{});commands=activity.get('commands',[])
        source=r.get('sourceBefore',{});after=r.get('sourceAfter',{})
        changed=sorted('src/'+f for f in source.keys()|after.keys() if source.get(f)!=after.get(f))
        files=activity.get('recognizedSourceFilesRead',{})
        reads=[{'eventIndex':c['eventIndex'],'files':c['recognized_source_reads']} for c in commands if c['recognized_source_reads']]
        metrics={k:r.get('usage',{}).get(k) for k in USAGE}
        metrics.update({k:activity.get(k) for k in ACTIVITY})
        observed='activity' in r
        metrics.update(sourceReadOccurrences=sum(files.values()) if observed else None,completedShellCommands=len(commands) if observed else None,
          failedShellCommands=sum(c.get('exitCode') not in (None,0) for c in commands) if observed else None,sourceFilesModified=len(changed) if 'sourceBefore' in r and 'sourceAfter' in r else None,
          applicationSourceFilesRead=sum(f.startswith('src/') for f in files) if observed else None,
          applicationSourceReadOccurrences=sum(n for f,n in files.items() if f.startswith('src/')) if observed else None,
          executionSeconds=r.get('duration_seconds'),evaluationSeconds=r.get('evaluationSeconds'),acceptedSeconds=r.get('timeToIndependentlyAcceptedSeconds'))
        snapshot=file.parent/'project'
        delivered={str(p.relative_to(snapshot)):digest(p) for p in sorted(snapshot.rglob('*')) if p.is_file() and p.relative_to(snapshot).parts[0] not in ['dist','dist-plain','node_modules','evidence','.git']}
        changes=[{'file':f,'kind':'modified' if f in delivered else 'deleted'} for f,h in truth.items() if delivered.get(f)!=h] if snapshot.exists() else []
        changes += [{'file':f,'kind':'added'} for f in delivered.keys()-truth.keys()-{'.gitignore'}]
        hint=hints[r['task']];hint_events=[c['eventIndex'] for c in commands if hint in c['recognized_source_reads']]
        raw=(file.parent/'trace.jsonl').read_text() if (file.parent/'trace.jsonl').exists() else ''
        events=[]
        for line in raw.splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:continue
        rows.append(dict(scheduled,uid=uid,status=r['status'],success=r['success'],metrics=metrics,
          clocksValid=not r.get('clockDiscrepancy',True),utcExecutionSeconds=r.get('utcExecutionSeconds'),T2=r.get('T2'),T3=r.get('T3'),T4=r.get('T4'),
          buildChecks=r.get('buildChecks'),acceptance=r.get('checks'),toolingUnchanged=r.get('toolingUnchanged'),runnerError=r.get('runnerError'),
          sourceFilesModified=changed,deliveredNonGeneratedChanges=sorted(changes,key=lambda c:c['file']),responsibleFile=hint,responsibleFileModified=hint in changed,recognizedFiles=files,readOrder=reads,
          hintInspection={'applicable':r['condition']=='code-aware','file':hint,'recognizedReadEvents':hint_events,
            'firstRecognizedSourceReadIncludesHint':bool(reads and hint in reads[0]['files']),
            'firstRecognizedSourceFileIsHint':bool(reads and reads[0]['files'][0]==hint),
            'otherSourceFilesRead':[f for f in files if f!=hint],
            'mentalReliance':None,'interpretation':'Ordered recognized command reads only; neither a read nor an edit alone establishes reliance.'},
          completedCLITurns=r.get('usage',{}).get('turns'),threadStartedEvents=sum(e.get('type')=='thread.started' for e in events),
          evidence={'result':str(file.relative_to(folder)),'resultSHA256':digest(file),'traceSHA256':digest(file.parent/'trace.jsonl') if (file.parent/'trace.jsonl').exists() else None,
            'patchSHA256':digest(file.parent/'diff.patch') if (file.parent/'diff.patch').exists() else None}))
    pairs=[]
    for task in sorted({r['task'] for r in plan['rows']}):
        arms={r['condition']:r for r in rows if r['task']==task};a,b=arms['current'],arms['code-aware']
        pair=dict(task=task,current=a['uid'],codeAware=b['uid'],bothAccepted=a['success'] is True and b['success'] is True,
          validClocks=a.get('clocksValid',False) and b.get('clocksValid',False),metrics={})
        for k in USAGE+ACTIVITY+['executionSeconds','evaluationSeconds','acceptedSeconds']:
            av,bv=a['metrics'].get(k),b['metrics'].get(k)
            eligible=av is not None and bv is not None
            if k in ['executionSeconds','acceptedSeconds']:eligible &= pair['validClocks']
            if k=='acceptedSeconds':eligible &= pair['bothAccepted']
            pair['metrics'][k]=dict(current=av,codeAware=bv,eligible=eligible,BMinusA=bv-av if eligible else None,reductionPercent=reduction(av,bv) if eligible else None)
        pairs.append(pair)
    aggregates={}
    for k in USAGE+ACTIVITY+['executionSeconds','evaluationSeconds','acceptedSeconds']:
        eligible=[p['metrics'][k] for p in pairs if p['metrics'][k]['eligible']]
        av=[p['current'] for p in eligible];bv=[p['codeAware'] for p in eligible]
        aa,bb=distribution(av),distribution(bv)
        aggregates[k]=dict(completePairs=len(eligible),current=aa,codeAware=bb,BMinusA=distribution([b-a for a,b in zip(av,bv)]),
          pairedReductionPercent=distribution([p['reductionPercent'] for p in eligible]),reductionOfMeansPercent=reduction(aa['mean'],bb['mean']))
    accepted_pairs=[p for p in pairs if p['bothAccepted'] and p['validClocks']]
    accepted_execution={}
    for condition in ['current','code-aware']:
        accepted_execution[condition]=distribution([r['metrics']['executionSeconds'] for r in rows if r['condition']==condition and any(p['task']==r['task'] for p in accepted_pairs)])
    return dict(kind='retained-live-records-descriptive-analysis',newModelCalls=0,primaryAnalyzer=primary,plannedAttempts=8,
      retainedAttempts=sum(r['status']!='not-executed' for r in rows),CLIThreadsObserved=sum(r.get('threadStartedEvents',0) for r in rows),
      completedCLITurns=sum(r.get('completedCLITurns') or 0 for r in rows),rows=rows,pairs=pairs,aggregates=aggregates,
      bothAcceptedValidClockPairs=len(accepted_pairs),acceptedPairAgentExecutionSeconds=accepted_execution,
      correctness={c:{'attempts':sum(r['condition']==c and r['status']!='not-executed' for r in rows),'accepted':sum(r['condition']==c and r['success'] is True for r in rows),
        'failedOrInterrupted':[r['uid'] for r in rows if r['condition']==c and r['success'] is False]} for c in ['current','code-aware']},
      limitations=['Four different authored tasks, one matched pair each. No significance or population claims.',
       'Complete matched usage includes failed attempts; missing never becomes zero. Valid-clock both-accepted pairs alone inform accepted-time comparisons.',
       'Recognized source reads include dependency/tool source and are a lower bound. Other files read are not automatically unrelated or unnecessary.',
       'Recorded command output bytes are not tokens. Completed CLI turns are not shell calls or a count of internal provider requests.',
       'Cache state, model/provider latency and human preparation time are uncontrolled/unobserved. Cost is unavailable unless provider-exposed.'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,default=BASE/'reports/study');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as f:json.dump(summarize(a.study),f,indent=2);f.write('\n')
