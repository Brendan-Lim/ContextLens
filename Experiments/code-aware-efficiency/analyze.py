"""Matched study analysis. Synthetic checks and incomplete telemetry never become live effects."""
import argparse
import json
from pathlib import Path
import statistics

def analyze(folder):
    plan=json.loads((folder/'plan.json').read_text());trials=[]
    for p in sorted((folder/'trials').glob('*/result.json')):
        r=json.loads(p.read_text())
        if r['kind']!='code-aware-efficiency-live-trial':raise ValueError('Synthetic records cannot be live performance')
        trials.append(r)
    allowed={(r['task'],r['condition'],r['repeat']) for r in plan['rows']}
    keys=[(r['task'],r['condition'],r['repeat']) for r in trials]
    if len(set(keys))!=len(keys) or any(k not in allowed for k in keys):raise ValueError('Unplanned or duplicate attempt')
    pairs=[]
    for task,repeat in sorted({(r['task'],r['repeat']) for r in plan['rows']}):
        arms={r['condition']:r for r in trials if (r['task'],r['repeat'])==(task,repeat)}
        row=dict(task=task,repeat=repeat,status='pending' if len(arms)<2 else 'matched',conditions={k:{'status':v['status'],'accepted':v['success'],'usage':v['usage']} for k,v in arms.items()},deltasBMinusA={})
        if len(arms)==2:
            a,b=arms['current'],arms['code-aware']
            for key in ['baselineCommit','sourceBefore','promptSHA256','imageSHA256']:
                if a.get(key) is None or a[key]!=b.get(key):raise ValueError('Nonequivalent matched pair: '+key)
            for metric in ['total_tokens','cached_input_tokens','uncached_input_tokens','input_tokens','output_tokens']:
                av,bv=a['usage'].get(metric),b['usage'].get(metric)
                row['deltasBMinusA'][metric]=bv-av if av is not None and bv is not None else None
            for metric in ['sourceDiscoveryCommands','filesInspectedRecognizedLowerBound','repeatedReadOccurrences','testExecutionsRecognized','commandOutputUTF8Bytes']:
                av,bv=a.get('activity',{}).get(metric),b.get('activity',{}).get(metric)
                row['deltasBMinusA'][metric]=bv-av if av is not None and bv is not None else None
            clocks=not(a.get('clockDiscrepancy',True) or b.get('clockDiscrepancy',True))
            row['deltasBMinusA']['executionSeconds']=b['duration_seconds']-a['duration_seconds'] if clocks and 'duration_seconds' in a and 'duration_seconds' in b else None
            row['deltasBMinusA']['acceptedSeconds']=b['timeToIndependentlyAcceptedSeconds']-a['timeToIndependentlyAcceptedSeconds'] if clocks and a['success'] and b['success'] else None
        pairs.append(row)
    metrics=sorted({m for r in pairs for m in r['deltasBMinusA']})
    means={m:{'completePairs':len(v:=[r['deltasBMinusA'].get(m) for r in pairs if r['deltasBMinusA'].get(m) is not None]),'meanBMinusA':statistics.mean(v) if v else None} for m in metrics}
    return dict(kind='matched-code-aware-efficiency-analysis',planned=8,executed=len(trials),newLiveResultsAvailable=bool(trials),pairs=pairs,descriptivePairedMeans=means,
        correctness={c:{'attempts':len(rs:=[r for r in trials if r['condition']==c]),'accepted':sum(r['success'] for r in rs),'failedOrInterrupted':sum(not r['success'] for r in rs),
          'regressionFailures':[dict(task=r['task'],failures=r.get('regressionFailures')) for r in rs if r.get('regressionFailures')],
          'incorrectHintReliance':[dict(task=r['task'],value=r.get('incorrectHintReliance'),status=r.get('incorrectHintRelianceStatus')) for r in rs]} for c in ['current','code-aware']},
        limitations=['Missing telemetry stays null; no synthetic/model usage conflation. Total is provider completed-turn input plus output, cached input a subset.',
          'All matched outcomes retained, including failure/timeouts. Token deltas require complete equivalent pairs; accepted-time deltas additionally require both accepted and valid clocks.',
          'Four pairs support descriptive pilot findings, not established population effects. Do not select only successful tasks for token claims.',
          'No token allocation to commands, files or output bytes. Mental reliance requires explicit transcript adjudication.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();report=analyze(a.folder)
    text=json.dumps(report,indent=2)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')

if __name__=='__main__':main()
