"""Read-only reproducibility, package, isolation and prior-artifact gates. No inference."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import run_study

BASE=run_study.BASE;ROOT=run_study.ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from validate_package import validate
from source_state import source_state

def preflight():
    plan=json.loads((BASE/'reports/study/plan.json').read_text())
    assert run_study.identities()==plan['identities'],'Frozen execution inputs drifted'
    packages=[];comparison=json.loads((BASE/'reports/packages/comparison.json').read_text())
    truth=json.loads((BASE/'reports/ground-truth.json').read_text())
    for row in comparison['rows']:
        task=row['task'];expected=next(r for r in truth['responsibility'] if r['task']==task)
        s=row['source'];assert s['file']==expected['file'] and s['symbol']==expected['symbol'] and s['start']<=expected['blameStart'] and s['end']>=expected['blameEnd']
        for condition in ['current','code-aware']:
            folder=BASE/'reports/packages'/task/condition;packages.append(dict(task=task,condition=condition,**validate(folder)))
    mapping=json.loads((BASE/'reports/mapping/results.json').read_text())
    assert not mapping['infrastructureErrors']
    for key in ['sourceFileTop1','responsibleSpanTop1','correctAbstentions']:
        assert mapping['metrics'][key]['correct']==mapping['metrics'][key]['total']==6
    assert mapping['metrics']['incorrectHighConfidenceHints']==0
    controls=json.loads((BASE/'reports/fixture-validation/results.json').read_text())
    assert all(not t['passed'] for t in controls['baseline']['targets'])
    assert all(t['passed'] for t in controls['combined']['targets']+controls['combined']['regressions'])
    assert len(controls['controls'])==4
    dry=json.loads((BASE/'reports/runner-self-test-v2/summary.json').read_text());assert dry['success'] and dry['newModelCalls']==0
    assert len(list((BASE/'reports/runner-self-test-v2/trials').glob('*/result.json')))==6
    # The evaluator, ground truth, controls, runner and other trials are absent from source copies.
    for p in (BASE/'reports/runner-self-test-v2/trials').glob('*/project'):
        assert not any((p/name).exists() for name in ['tasks.json','evaluate.mjs','validate-fixture.mjs','run_study.py','reports'])
    preservation=[]
    for folder in [ROOT/'Experiments/visual-to-code',ROOT/'Benchmarks/reports/manual-vs-contextlens']:
        hashes=json.loads((folder/'reports/artifact-sha256.json' if folder.name=='visual-to-code' else folder/'artifact-sha256.json').read_text())
        changed=[f for f,h in hashes.items() if not (folder/f).is_file() or run_study.digest(folder/f)!=h]
        assert not changed,changed
        preservation.append(dict(folder=str(folder.relative_to(ROOT)),filesChecked=len(hashes),changed=changed))
    production=source_state();prior=json.loads((ROOT/'Benchmarks/reports/manual-vs-contextlens/environment.json').read_text())
    assert production['build_source_sha256']==prior['build_source_sha256']
    packages_metadata={}
    for name in ['react','react-dom','typescript','esbuild','@jridgewell/trace-mapping','@types/react','@types/react-dom']:
        pkg=json.loads((BASE/'fixture/node_modules'/name/'package.json').read_text());packages_metadata[name]={k:pkg.get(k) for k in ['version','license']}
    environment=dict(machine=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
        macOS=subprocess.check_output(['sw_vers'],text=True).strip(),python=platform.python_version(),node=plan['identities']['node'],codexCLI=plan['identities']['cli'],
        chrome=subprocess.check_output(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--version'],text=True).strip(),
        packages=packages_metadata,gitCommit=production['git_commit'],productionBuildSourceSHA256=production['build_source_sha256'])
    return dict(kind='no-inference-code-aware-preflight',ready=True,newModelCalls=0,preparedTrials=8,executedLiveTrials=len(list((BASE/'reports/study/trials').glob('*/result.json'))),
        packages=packages,mapping=mapping['metrics'],syntheticRunner=dry,priorPreservation=preservation,productionUnchanged=True,environment=environment,
        authorization='Absent for this study. Prior studies are rejected. Live run remains gated.',
        readinessScope='Local synthetic verification and frozen input checks. Actual subscription allowance/model reachability and agent behavior are untested; guard runs before each authorized invocation.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();result=preflight();text=json.dumps(result,indent=2)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
