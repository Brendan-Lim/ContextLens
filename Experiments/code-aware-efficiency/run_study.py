#!/usr/bin/env python3
"""Prepare eight trials without inference. --run requires fresh, study-specific authorization."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'Benchmarks/runners'))
import harness
import subscription_guard as guard
import telemetry
import profile_agent_exploration as exploration

STUDY='code-aware-agent-efficiency'
TASKS=['publish-actions','project-filter','seat-allocation','contact-validation']
SECRET_KEYS=['OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL','CODEX_ACCESS_TOKEN']

def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fingerprint(root):
    return {str(p.relative_to(root)):('symlink:'+os.readlink(p) if p.is_symlink() else digest(p)) for p in sorted(root.rglob('*')) if p.is_file() or p.is_symlink()}

def copy_dependencies(source,destination):
    # npm's relative .bin links must retain their resolution inside each private copy.
    # Reject escaping/absolute links before preserving them; never link back to a trial.
    for p in source.rglob('*'):
        if p.is_symlink():
            if Path(os.readlink(p)).is_absolute() or source.resolve() not in p.resolve().parents:
                raise ValueError('Dependency link escapes the selected dependency tree')
    shutil.copytree(source,destination,symlinks=True)

def schedule(repeat=1):
    rng=random.Random(8301);tasks=TASKS.copy();rng.shuffle(tasks);rows=[]
    for task in tasks:
        conditions=['current','code-aware'];rng.shuffle(conditions)
        if repeat%2==0:conditions.reverse()
        rows.extend(dict(task=task,condition=c,repeat=repeat) for c in conditions)
    return rows

def identities():
    truth=json.loads((BASE/'reports/ground-truth.json').read_text())
    for file,hash in truth['publicSourceFiles'].items():
        if digest(BASE/'fixture'/file)!=hash:raise ValueError('Frozen fixture drift: '+file)
    if digest(BASE/'evaluate.mjs')!=truth['independentEvaluatorSHA256']:raise ValueError('Frozen evaluator drift')
    if digest(BASE/'tasks.json')!=truth['taskSpecSHA256']:raise ValueError('Task drift')
    return dict(groundTruth=digest(BASE/'reports/ground-truth.json'),source=truth['publicSourceFiles'],
        dependencies=fingerprint(BASE/'fixture/node_modules'),built=fingerprint(BASE/'fixture/dist'),
        evidence=fingerprint(BASE/'reports/packages'),runner=digest(Path(__file__)),
        localHelpers={str(p.relative_to(BASE)):digest(p) for p in sorted((BASE/'lib').glob('*.mjs'))},
        browserAdapter=fingerprint(ROOT/'Experiments/visual-to-code/src'),
        sharedHelpers={f:digest(ROOT/'Benchmarks/runners'/f) for f in ['harness.py','subscription_guard.py','telemetry.py','profile_agent_exploration.py']},
        cli=subprocess.check_output(['codex','--version'],text=True).strip(),node=subprocess.check_output(['node','--version'],text=True).strip())

def prepare(output):
    output.mkdir(parents=True,exist_ok=True)
    plan=dict(kind='prepared-code-aware-efficiency-plan-not-live-results',study=STUDY,seed=8301,rows=schedule(),preparedInvocations=8,
        model='gpt-6.1-sol',reasoningEffort='high',serviceTier='default',permissionPolicy='workspace-write; strict user-config isolation; no web; workspace-only instructions',
        timeoutSeconds=600,identities=identities(),freshAuthorizationRequired=True,previousAuthorizationInherited=False,
        repetitions='Initial four matched pairs only. schedule(2) reverses each pair for a later separately authorized eight-attempt replication.',
        guidance='Same prompt, instruction, images and available visual evidence; B adds data-only DOM/source hints. No third condition.',
        acceptance='First frozen independent target check plus all shared regression groups, source typecheck/build and unchanged tooling. Preserve failures/timeouts. No corrective retries.',
        analysis='Report four task-paired deltas individually; complete matched usage only for token differences. Preserve incomplete pairs and correctness outcomes; no missing=zero. Execution-to-independent-acceptance includes evaluation, failed acceptance time is unavailable/censored. Descriptive only; no population claim.')
    p=output/'plan.json'
    if p.exists():
        if json.loads(p.read_text())!=plan:raise ValueError('Frozen plan input drift')
    else:write(p,plan)
    return plan

def require_authorization(file):
    if not file or not file.is_file():raise ValueError('Fresh authorization for this new eight-attempt study is required; no model call started')
    auth=json.loads(file.read_text())
    if not(auth.get('study')==STUDY and auth.get('authorized') is True and auth.get('max_invocations')==8
        and auth.get('user_instruction') and auth.get('billing_scope')=='existing-allocation-no-purchases-no-api'):
        raise ValueError('Authorization does not cover this study and exact eight-invocation cap')
    return auth

def activity(raw,workspace):
    commands=[];counts=Counter();unparsed=0;noncommand=[]
    for index,line in enumerate(raw.splitlines()):
        try:e=json.loads(line)
        except json.JSONDecodeError:unparsed+=1;continue
        if e.get('type')!='item.completed':continue
        item=e.get('item',{})
        if item.get('type')!='command_execution':
            noncommand.append({'eventIndex':index,'type':item.get('type')});continue
        command=item.get('command','');c=exploration.classify(command.replace(str(workspace)+'/', ''))
        # Existing conservative parser plus the explicit local typecheck/build scripts.
        if 'npm run check' in command or 'npm run build' in command:c['test_or_assertion_command']=True
        counts.update(c['recognized_source_reads']);output=item.get('aggregated_output','')
        commands.append(dict(c,eventIndex=index,command=command,exitCode=item.get('exit_code'),outputUTF8Bytes=len(output.encode()),outputCharacters=len(output),tokens=None))
    return dict(commands=commands,nonCommandToolItems=noncommand,unparsedLines=unparsed,sourceDiscoveryCommands=sum(c['source_search_or_listing'] for c in commands),
        recognizedSourceFilesRead=dict(counts),filesInspectedRecognizedLowerBound=len(counts),repeatedReadOccurrences=sum(max(0,n-1) for n in counts.values()),
        testExecutionsRecognized=sum(c['test_or_assertion_command'] for c in commands),commandOutputUTF8Bytes=sum(c['outputUTF8Bytes'] for c in commands),
        limits='Conservative command recognizer, not filesystem access tracing. Batched categories overlap. No command token attribution or mental reliance inferred.')

REPAIRS={
 'publish-actions':('src/ui/dialogs/ActionCluster.module.css','justify-content: flex-start;','justify-content: flex-end;'),
 'project-filter':('src/interaction/useLayerDismissal.ts','      onDismiss();','      const target=event.target as Node;\n      if(!anchor.current?.contains(target)&&!layer.current?.contains(target))onDismiss();'),
 'seat-allocation':('src/state/useSeatAllocation.ts','setSeats(seats+1)','setSeats(value=>value+1)'),
 'contact-validation':('src/domain/validation/contactPolicy.ts',"return address.includes('@');",r"return /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(address);")}

def attempt(row,output,plan,auth=None,synthetic=None):
    if synthetic is None:
        if auth is None:raise ValueError('No authorization')
        before=guard.check(allow_edu_allocation=auth.get('education_allocation_authorized') is True)
    else:before=None
    uid=f"{row['task']}-{row['condition']}-{row['repeat']}";dest=output/'trials'/uid;dest.mkdir(parents=True,exist_ok=False)
    work=Path(tempfile.mkdtemp(prefix='contextlens-efficiency-'))
    record=dict(row,trial=row['repeat'],kind='synthetic-local-runner-check' if synthetic else 'code-aware-efficiency-live-trial',status='reserved',success=False,
        allowanceBefore=before,usage=telemetry.blank(),incorrectHintReliance=None,incorrectHintRelianceStatus='Requires transcript adjudication; source reads alone do not prove reliance.',humanPreparationSeconds=None)
    write(dest/'result.json',record)
    try:
        for name in ['src','tools','dist']:
            shutil.copytree(BASE/'fixture'/name,work/name)
        copy_dependencies(BASE/'fixture/node_modules',work/'node_modules')
        for name in ['package.json','package-lock.json','tsconfig.json','index.html']:
            shutil.copyfile(BASE/'fixture'/name,work/name)
        (work/'.gitignore').write_text('node_modules/\ndist/\nevidence/\n')
        record['baselineCommit']=harness.baseline_commit(work)
        folder=BASE/'reports/packages'/row['task'];shutil.copytree(folder/row['condition'],work/'evidence')
        prompt=(folder/'prompt.txt').read_text();(dest/'prompt.txt').write_text(prompt)
        image=work/'evidence/annotated/states/frame-001.png'
        record.update(promptSHA256=digest(folder/'prompt.txt'),imageSHA256=digest(image),evidence=fingerprint(work/'evidence'),sourceBefore=fingerprint(work/'src'))
        command=guard.command()[:-1]+['--image',str(image),'-']
        if synthetic:
            if synthetic=='repair':
                f,old,new=REPAIRS[row['task']]
                code=f"from pathlib import Path\np=Path({f!r})\np.write_text(p.read_text().replace({old!r},{new!r},1))\n"
                # Deliberately no usage event: a local program must never masquerade as provider usage.
                command=['python3','-c',code]
            elif synthetic=='timeout':command=['python3','-c','import time; time.sleep(10)']
            elif synthetic=='failure':command=['python3','-c','raise SystemExit(7)']
            else:raise ValueError('Invalid synthetic mode')
        record.update(command=command,T2=harness.iso());write(dest/'result.json',record);start=time.monotonic()
        saved={k:os.environ.get(k) for k in SECRET_KEYS}
        for k in SECRET_KEYS:os.environ.pop(k,None)
        try:execution=harness.run_process(command,work,prompt,plan['timeoutSeconds'],dest/'trace.jsonl',dest/'stderr.txt')
        finally:
            for k,v in saved.items():
                if v is not None:os.environ[k]=v
        record.update(execution,T3=harness.iso());write(dest/'execution.json',record)
        record['utcExecutionSeconds']=(dt.datetime.fromisoformat(record['T3'])-dt.datetime.fromisoformat(record['T2'])).total_seconds()
        record['clockDiscrepancy']=abs(record['utcExecutionSeconds']-execution['duration_seconds'])>1
        raw=(dest/'trace.jsonl').read_text()
        try:record['usage']=telemetry.codex(raw)
        except (ValueError,json.JSONDecodeError) as e:record['telemetryError']=str(e)
        record['activity']=activity(raw,work)
        record['toolingUnchanged']=all(digest(work/p)==h for p,h in plan.get('source',plan.get('identities',{}).get('source',{})).items() if not p.startswith('src/'))
        checks=[];evaluated=time.monotonic()
        for name,args in [('typecheck',['npm','run','check']),('build',['npm','run','build'])]:
            p=subprocess.run(args,cwd=work,text=True,capture_output=True,timeout=60)
            (dest/(name+'.stdout.txt')).write_text(p.stdout);(dest/(name+'.stderr.txt')).write_text(p.stderr);checks.append({'check':name,'passed':p.returncode==0})
        p=subprocess.run(['node',str(BASE/'evaluate.mjs'),str(work),row['task']],text=True,capture_output=True,timeout=150)
        (dest/'evaluation.json').write_text(p.stdout);(dest/'evaluation.stderr.txt').write_text(p.stderr)
        record['checks']=json.loads(p.stdout);record['buildChecks']=checks;record['evaluationSeconds']=time.monotonic()-evaluated
        record['targetAccepted']=all(c['passed'] for c in record['checks']['targets'])
        record['regressionFailures']=[r for r in record['checks']['regressions'] if not r['passed']]
        record['success']=bool(p.returncode==0 and all(c['passed'] for c in checks) and record['toolingUnchanged'] and execution['returncode']==0 and not execution['timed_out'])
        record['firstAttemptAccepted']=record['success'];record['T4']=harness.iso() if record['success'] else None
        record['timeToIndependentlyAcceptedSeconds']=time.monotonic()-start if record['success'] else None
        record['status']='timed-out' if execution['timed_out'] else ('accepted' if record['success'] else 'failed')
        if not synthetic:record['allowanceAfter']=guard.read_status()
    except Exception as e:record.update(runnerError=str(e),status='interrupted')
    finally:
        try:
            record['sourceAfter']=fingerprint(work/'src') if (work/'src').exists() else {}
            patch=subprocess.run(['git','diff','--binary','HEAD'],cwd=work,text=True,capture_output=True);(dest/'diff.patch').write_text(patch.stdout)
            shutil.copytree(work,dest/'project',ignore=shutil.ignore_patterns('.git','node_modules'))
            (dest/'reliance-review.json').write_text(json.dumps({'kind':'pending-human-or-transcript-adjudication','incorrectSourceHintReliance':None,'evidenceEventIndices':[],
              'rule':'A wrong-hint-caused edit or explicit acceptance of an incorrect pointer needs transcript evidence; reading a hinted file is insufficient.'},indent=2)+'\n')
        finally:write(dest/'result.json',record);shutil.rmtree(work)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=BASE/'reports/study');p.add_argument('--run',action='store_true')
    p.add_argument('--authorization',type=Path);p.add_argument('--self-test',type=Path);a=p.parse_args()
    if a.self_test:
        if a.run:raise ValueError('Synthetic checks cannot be a live run')
        a.self_test.mkdir(exist_ok=False);plan={'timeoutSeconds':30,'source':json.loads((BASE/'reports/ground-truth.json').read_text())['publicSourceFiles']};results=[]
        for task in TASKS:
            results.append(attempt(dict(task=task,condition='code-aware' if len(results)%2 else 'current',repeat=1),a.self_test,plan,synthetic='repair'))
        for mode in ['failure','timeout']:
            results.append(attempt(dict(task='seat-allocation',condition='current',repeat=2 if mode=='failure' else 3),a.self_test,{**plan,'timeoutSeconds':.05 if mode=='timeout' else 30},synthetic=mode))
        assert all(r['success'] for r in results[:4]),[(r['task'],r['status']) for r in results[:4]]
        assert all(not r['success'] for r in results[4:]);assert results[-1]['timed_out'];assert results[-2]['returncode']==7
        assert all(r['usage']['total_tokens'] is None for r in results)
        assert len({r['baselineCommit'] for r in results})==1
        write(a.self_test/'summary.json',dict(kind='synthetic-local-checks-not-agent-performance',newModelCalls=0,repairChecks=4,retainedFailure=1,retainedTimeout=1,usageUnavailableNotZero=True,success=True))
        print('Six local runner checks passed; no model calls.');return
    plan=prepare(a.output)
    if not a.run:print('Eight trials prepared; zero model calls. Fresh study-specific authorization required.');return
    auth=require_authorization(a.authorization)
    for row in plan['rows']:
        dest=a.output/'trials'/f"{row['task']}-{row['condition']}-{row['repeat']}"
        if dest.exists():continue  # Reserved, failed and partial attempts are never repeated.
        if len(list((a.output/'trials').glob('*')))>=auth['max_invocations']:raise ValueError('Invocation cap reached')
        if identities()!=plan['identities']:raise ValueError('Frozen inputs drift')
        result=attempt(row,a.output,plan,auth=auth);print(json.dumps({k:result.get(k) for k in ['task','condition','status','success']}),flush=True)
        if result.get('runnerError') or result.get('timed_out') or result.get('clockDiscrepancy'):break

if __name__=='__main__':main()
