"""Repeat frozen checks on retained snapshots, without model calls or altered outcomes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import run_study as runner

BASE=runner.BASE

def recheck():
    rows=[];truth=json.loads((BASE/'reports/ground-truth.json').read_text())
    for file in sorted((BASE/'reports/study/trials').glob('*/result.json')):
        original=json.loads(file.read_text())
        if original['kind']!='code-aware-efficiency-live-trial':raise ValueError('Only retained live snapshots are eligible')
        if original['status']=='reserved':raise ValueError('Wait until execution completes')
        start=time.monotonic()
        with tempfile.TemporaryDirectory(prefix='contextlens-independent-recheck-') as temp:
            work=Path(temp)/'project';shutil.copytree(file.parent/'project',work)
            runner.copy_dependencies(BASE/'fixture/node_modules',work/'node_modules')
            build=[]
            for name,args in [('typecheck',['npm','run','check']),('build',['npm','run','build'])]:
                p=subprocess.run(args,cwd=work,text=True,capture_output=True,timeout=60)
                build.append({'check':name,'passed':p.returncode==0})
                if p.returncode:raise ValueError(name+' failed during recheck: '+p.stderr)
            p=subprocess.run(['node',str(BASE/'evaluate.mjs'),str(work),original['task']],text=True,capture_output=True,timeout=150)
            checks=json.loads(p.stdout)
            tooling=all(runner.digest(work/f)==h for f,h in truth['publicSourceFiles'].items() if not f.startswith('src/'))
            repeated_acceptance=bool(p.returncode==0 and all(c['passed'] for c in build) and tooling and original['returncode']==0 and not original['timed_out'])
            row={'trial':file.parent.name,'buildChecks':build,'checks':checks,'toolingUnchanged':tooling,'matchesRecordedChecks':checks==original.get('checks'),
              'matchesRecordedBuildChecks':build==original.get('buildChecks'),'repeatedFrozenAcceptance':repeated_acceptance,'matchesRecordedAcceptance':repeated_acceptance==original['success'],
              'recheckSecondsNotAgentPerformance':time.monotonic()-start}
            rows.append(row)
            if not(row['matchesRecordedChecks'] and row['matchesRecordedBuildChecks'] and row['matchesRecordedAcceptance']):raise ValueError('Stored snapshot outcome did not reproduce: '+file.parent.name)
    return {'kind':'post-execution-frozen-check-reproduction','newModelCalls':0,'snapshotsChecked':len(rows),'allRecordedOutcomesReproduced':True,'rows':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=recheck()
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Stored snapshot checks reproduced; no model calls.')
