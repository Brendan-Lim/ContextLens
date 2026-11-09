"""Transfer only an explicit fictional-screenshot allowlist and sanitized results.

Raw receipts, sessions, exports, logs, UI trees and keys stay on the disposable
runner. No recursive copy of the evidence directory is permitted.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

assert os.environ.get('GITHUB_ACTIONS')=='true'
temp=Path(os.environ['RUNNER_TEMP']);raw=temp/'native-evidence';safe=temp/'safe-native-evidence';safe.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('strip_png',Path.cwd()/'scripts/strip-png-metadata.py')
strip=importlib.util.module_from_spec(spec);spec.loader.exec_module(strip)
cases={};value={}
casefile=raw/'native-case-results.json'
if casefile.exists():value=json.loads(casefile.read_text())
scalar_fields={'frames','undoChanged','redoRestored','normalExitCode','otherWindowAlive','promptCopied'}
for name,item in value.get('cases',{}).items():
    clean={'status':item.get('status','pending')}
    for field in scalar_fields:
        v=item.get(field)
        if isinstance(v,(int,bool)) and not isinstance(v,str):clean[field]=v
    for field in ['startToStopSeconds']:
        if field in item:clean[field]=item[field]
    if name=='dmg-drag-install-eject-launch':
        obs=item.get('installedObservation',{})
        clean['installedCopyRunning']=obs.get('runningInstalledCopy',False)
        clean['visibleWindowCount']=obs.get('windowCount',0)
        clean['version']=obs.get('version');clean['build']=obs.get('build')
    cases[name]=clean
pill=raw/'pill-ocr.json'
if pill.exists():
    try:
        checks=json.loads(pill.read_text())
        cases['recording-stop-label']=dict(status='pass' if checks and all(c.get('fullStopLabelDetected') for c in checks) else 'pending',capturesChecked=len(checks),allShowCompleteStop=bool(checks) and all(c.get('fullStopLabelDetected') for c in checks))
    except json.JSONDecodeError:cases['recording-stop-label']=dict(status='pending')
finder=raw/'finder-cases.json'
if finder.exists():cases.update(json.loads(finder.read_text()))
# Independently validate actual native sessions/export on this runner, then keep
# only aggregate counts and boolean/string-equality results, never session data.
session_results=[]
cli=temp/'unpacked/ContextLens.app/Contents/MacOS/contextlens-cli'
for p in sorted((raw/'all-native-sessions').glob('*/session.json')):
    result=subprocess.run([str(cli),'validate',str(p.parent)],capture_output=True,text=True,timeout=60)
    state=json.loads(p.read_text())
    session_results.append(dict(valid=result.returncode==0,frameCount=len(state['frames']),annotationCount=len(state['annotations'])))
export_checks={}
export=raw/'ui-export'
if (export/'manifest.json').exists():
    m=json.loads((export/'manifest.json').read_text());s=json.loads((raw/'high-session/session.json').read_text())
    expected=['Align the action buttons with the right edge of the email field.','Center this avatar vertically in its row, like the one above.']
    validation=subprocess.run([sys.executable,'scripts/validate_package.py',str(export)],capture_output=True,text=True,timeout=60)
    prompt=json.loads((raw/'actual-agent-prompt.json').read_text()).get('stdout','')
    export_checks=dict(validPackage=validation.returncode==0,frames=len(m['frames']),issues=len(m['issues']),
        exactTask=m['task']==s['task']=='Polish the Share workspace dialog.',
        exactInstructions=[i['annotation']['instruction'] for i in m['issues']]==expected==[a['instruction'] for a in s['annotations']],
        stableIssueIDs=[i['annotation']['id'] for i in m['issues']]==['CL-001','CL-002'],
        canonicalSavedPromptVerified='Polish the Share workspace dialog.' in prompt and '/private/tmp/share-dialog-feedback/' in prompt and '/context.md' in prompt)
allow=['product-originals/'+n for n in [
    'A-capture.png','A2-recording.png','A2-recording-three-states.png','A2-recording-1600.png',
    'B-review.png','C-markup.png','D-handoff.png','capture-save-failure.png','session-reopened.png',
    'selected-window-closure.png','target-application-exit.png','quit-timeout.png','workflow-failure.png']]
allow+=['finder-light/Finder.png','finder-dark/Finder.png']
for folder in ['installed-launch','installed-direct']:
    for p in (raw/folder).glob('dev.contextlens.app-*.png'):
        if re.fullmatch(r'dev\.contextlens\.app-\d+\.png',p.name):allow.append(folder+'/'+p.name)
images=[]
for relative in allow:
    source=raw/relative
    if not source.is_file():continue
    target=safe/relative;target.parent.mkdir(exist_ok=True)
    original=source.read_bytes();cleaned,removed=strip.strip(original)
    assert b''.join(v for k,v in strip.chunks(original) if k==b'IDAT')==b''.join(v for k,v in strip.chunks(cleaned) if k==b'IDAT')
    target.write_bytes(cleaned)
    images.append(dict(path=relative,sha256=hashlib.sha256(cleaned).hexdigest(),originalSHA256=hashlib.sha256(original).hexdigest(),removedChunks=removed,pixelsUnchanged=True))
summary=dict(exactOfficialCandidate=(raw/'candidate-verified.json').exists(),developmentRebuild=False,maintainerAttestation=False,
    cases=cases,sessionValidation=session_results,exportChecks=export_checks,images=images,
    privateReceiptsTransferred=False,sessionDataTransferred=False,decryptionKeysTransferred=False,
    existingRunnerAccessOnly=True,noTCCChanges=True,noHumanSecurityApprovalAutomated=True,
    originalBundleIdentityUnchanged=json.loads((raw/'bundle-after.json').read_text()).get('unchanged',False) if (raw/'bundle-after.json').exists() else False)
summary['candidateRunID']=42601149595
summary['candidateSourceSHA']='d0323bb84c08d5f42c29cae5635931bf2d825d98'
summary['candidateAssetSHA256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (temp/'official-candidate').glob('ContextLens-0.3.1-arm64.*') if p.suffix in {'.zip','.dmg'}}
human=['gatekeeper-first-launch','open-anyway','screen-recording-denied','fresh-screen-recording-grant-relaunch','permission-revocation-recovery']
summary['humanSecurityCases']={name:dict(status='pending',reason='Requires a genuine quarantined first launch or explicit user decision on a disposable interactive Mac') for name in human}
(safe/'engineering-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
assert not any(p.suffix in {'.key','.pem','.log','.tar','.cms'} or p.name in {'session.json','manifest.json','provenance.json','official.json'} for p in safe.rglob('*'))
print('Prepared fictional window screenshots and sanitized observations only; no raw sessions, receipts, logs or keys.')
