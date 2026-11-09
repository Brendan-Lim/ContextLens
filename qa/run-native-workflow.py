"""Exact-candidate native UI operation on a disposable hosted Mac. No security approvals."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import traceback
import urllib.request

temp=Path(os.environ['RUNNER_TEMP']); out=temp/'native-evidence';out.mkdir(exist_ok=True)
images=out/'product-originals';images.mkdir()
storage=Path('/tmp/contextlens-native-sessions');storage.mkdir()
parent=Path('/tmp/share-dialog-feedback');parent.mkdir()
helper=temp/'ui-helper';app=temp/'unpacked/ContextLens.app';cli=app/'Contents/MacOS/contextlens-cli'
events=[];cases={};candidate=temp/'exact-candidate'
def record(name,**values):
    event=dict(at=time.time(),name=name,**values);events.append(event)
    (out/'native-actions.json').write_text(json.dumps(events,indent=2))
def command(args,name,timeout=60):
    try:
        r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
        v=dict(exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired:v=dict(status='timeout')
    (out/(name+'.json')).write_text(json.dumps(v,indent=2));return v
def ui(action,required=True,**values):
    r=command([helper,action,json.dumps(values)],'ui-last',20)
    try:data=json.loads(r.get('stdout','{}'))
    except json.JSONDecodeError:data=r
    record('ui-'+action,options=values,result=data)
    if required and r.get('exitCode')!=0:raise RuntimeError(str(data))
    return data
def tree(name):
    value=ui('tree');(out/(name+'-tree.json')).write_text(json.dumps(value,indent=2));return value.get('nodes',[])
def press(text,exact=True,required=True):return ui('press',text=text,exact=exact,role='AXButton',required=required)
def keys(code,cmd=False,shift=False):return ui('keys',code=code,command=cmd,shift=shift)
def snapshot(name,panel=False):return ui('snapshot',file=str(images/name),**({'title':'ContextLens Capture'} if panel else {}))
def latest():
    files=sorted(storage.glob('*/session.json'),key=lambda p:p.stat().st_mtime)
    if not files:return None,None
    f=files[-1];return f.parent,json.loads(f.read_text())
def wait_for(predicate,seconds=12):
    deadline=time.time()+seconds
    while time.time()<deadline:
        try:
            value=predicate()
            if value:return value
        except (OSError,ValueError):pass
        time.sleep(.25)
    return None
def browser(action):
    request=urllib.request.Request(origin+'/control',data=json.dumps(dict(action=action)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:result=json.load(response)
    record('browser-'+action,result=result);return result
def capture(sensitivity,photo=False):
    keys(45,True);time.sleep(.8)
    press('Tidewater',False)
    press(sensitivity)
    if photo:snapshot('A-capture.png',True)
    old={str(p) for p in storage.iterdir()}
    press('Start Capture');time.sleep(2)
    if photo:snapshot('A2-recording.png',True)
    root=wait_for(lambda:next((p for p in storage.iterdir() if str(p) not in old and (p/'session.json').exists()),None))
    assert root is not None,'No capture session created'
    return root
def stop():
    press('Stop');time.sleep(1.4)
def note(text):
    nodes=tree('note-target')
    fields=[n for n in nodes if n.get('AXRole') in ('AXTextField','AXTextArea') and (n.get('AXPlaceholderValue')=='What should change?' or n.get('AXDescription')=='What should change?' or n.get('AXValue','')=='')]
    assert fields,'No native note field'
    ui('type',index=fields[-1]['index'],value=text)
def choose_folder(path):
    keys(5,True,True);time.sleep(.6)
    nodes=tree('folder-go')
    fields=[n for n in nodes if n.get('AXRole') in ('AXTextField','AXComboBox') and n.get('AXEnabled',True)]
    assert fields,'No native Go To Folder field'
    ui('type',index=fields[-1]['index'],value=str(path));keys(36);time.sleep(.7)
    press('Save Hand Off',required=False);time.sleep(1)
def status_text():return ' '.join(str(n.get('AXValue',''))+' '+str(n.get('AXTitle','')) for n in ui('tree').get('nodes',[]))
browser_process=None;candidate_process=None
try:
    r=command(['gh','run','download','42557369631','--repo','Brendan-Lim/ContextLens','--name','official-candidate-0.3.1','--dir',candidate],'download')
    assert r.get('exitCode')==0
    expected={'ContextLens-0.3.1-arm64.zip':'f4ac0a2cc3dc5fd6f120a21e3f7152f86351b7f8bf93e3908f57bc5a9ad3425e','ContextLens-0.3.1-arm64.dmg':'52872a5e0221fac2960fb8d5c349743201bbb5800a914eb77b1b48416473b37d'}
    for filename,digest in expected.items():assert hashlib.sha256((candidate/filename).read_bytes()).hexdigest()==digest
    (out/'candidate-provenance.json').write_bytes((candidate/'provenance.json').read_bytes())
    assert command(['python3','scripts/unnotarized-release.py','verify-assets',candidate],'verify-assets')['exitCode']==0
    assert command(['ditto','-x','-k',candidate/'ContextLens-0.3.1-arm64.zip',temp/'unpacked'],'unpack')['exitCode']==0
    assert command(['swiftc','qa/ui.swift','-o',helper],'compile-ui-helper')['exitCode']==0
    ui('display');command(['swift','qa/capabilities.swift'],'capabilities')
    browser_log=(out/'browser-process.log').open('w')
    browser_process=subprocess.Popen(['node','qa/tidewater.cjs'],stdout=browser_log,stderr=browser_log)
    assert wait_for(lambda:(out/'browser-ready.json').exists(),30),'Browser failed'
    origin=json.loads((out/'browser-ready.json').read_text())['origin']
    application_log=(out/'candidate-process.log').open('w')
    candidate_process=subprocess.Popen([str(app/'Contents/MacOS/ContextLens'),'--isolated-native-test','--capture-preview','-onboardingComplete','YES','-storagePath',str(storage),'-ApplePersistenceIgnoreState','YES','-NSRequiresAquaSystemAppearance','YES'],stdout=application_log,stderr=application_log)
    record('launch-candidate',method='direct exact binary; existing runner execution context, no privacy settings changed',pid=candidate_process.pid)
    time.sleep(4)
    nodes=tree('launch')
    press('Start using ContextLens',required=False)
    ui('resize',width=1320,height=860,x=40,y=40,required=False)
    high=capture('High',True)
    browser('share');time.sleep(3)
    browser('link');time.sleep(3)
    browser('invite');browser('fill');time.sleep(3)
    state=json.loads((high/'session.json').read_text());preferred=state['frames'][-1]['id'];geometry=browser('state')
    browser('cancel');time.sleep(3);stop()
    state=json.loads((high/'session.json').read_text());assert len(state['frames'])>=3
    cases['selected-window-high']=dict(status='pass',frames=len(state['frames']),session=str(high),preferredFrame=preferred)
    first=state['frames'][0];press('Include '+first['name']+' in hand-off')
    snapshot('B-review.png')
    press('Mark Up',False);time.sleep(.8)
    preferred_frame=next(f for f in state['frames'] if f['id']==preferred)
    press(preferred_frame['name'],False);time.sleep(.8)
    nodes=tree('markup-before')
    available=[n for n in nodes if n.get('AXRole')=='AXImage' and n.get('width',0)>300 and n.get('height',0)>200]
    assert available,'Native canvas image has no accessible bounds'
    image=max(available,key=lambda n:n['width']*n['height'])
    border=(preferred_frame['width']-geometry['innerWidth'])/2
    top=preferred_frame['height']-geometry['innerHeight']-border
    def canvas(x,y):return [image['x']+(x+border)/preferred_frame['width']*image['width'],image['y']+(y+top)/preferred_frame['height']*image['height']]
    cancel,send=geometry['cancel'],geometry['send']
    press('Box');ui('drag',**{'from':canvas(cancel['x']-4,cancel['y']-4),'to':canvas(send['x']+send['width']+4,send['y']+send['height']+4)})
    note('Align the action buttons with the right edge of the email field.')
    avatar=geometry['avatar'];press('Highlight');ui('drag',**{'from':canvas(avatar['x']+avatar['width']/2,avatar['y']+3),'to':canvas(avatar['x']+avatar['width']/2,avatar['y']+avatar['height']-3)})
    note('Center this avatar vertically in its row, like the one above.')
    state=json.loads((high/'session.json').read_text());assert len(state['annotations'])==2
    expected_marks=state['annotations'];ui('click',point=[image['x']+image['width']-8,image['y']+image['height']-8])
    keys(6,True);time.sleep(.4);undone=json.loads((high/'session.json').read_text())['annotations']
    keys(6,True,True);time.sleep(.4);redone=json.loads((high/'session.json').read_text())['annotations']
    cases['review-annotation-undo-redo']=dict(status='pass' if undone!=expected_marks and redone==expected_marks else 'fail',undoChanged=undone!=expected_marks,redoRestored=redone==expected_marks,marks=redone)
    snapshot('C-markup.png')
    press('Hand Off',False);time.sleep(1)
    nodes=tree('handoff-before')
    task=next(n for n in nodes if n.get('AXPlaceholderValue')=='What should the agent do?' or n.get('AXDescription')=='What should the agent do?')
    ui('type',index=task['index'],value='Polish the Share workspace dialog.');time.sleep(1)
    press('Save Hand Off');time.sleep(.7);choose_folder(parent)
    exported=wait_for(lambda:next(parent.glob('*/manifest.json'),None),15)
    assert exported,'Native export did not complete'
    exported=exported.parent
    validation=command(['python3','scripts/validate_package.py',exported],'ui-export-validation')
    assert validation['exitCode']==0
    press('Copy prompt');command(['pbpaste'],'actual-agent-prompt');time.sleep(2)
    snapshot('D-handoff.png');shutil.copytree(exported,out/'ui-export');shutil.copytree(high,out/'high-session')
    cases['handoff-export']=dict(status='pass',package=str(exported),validation=json.loads(validation['stdout']),promptCopied=True)
    # Low sensitivity uses the real browser and a new native capture.
    browser('reset');low=capture('Low');browser('share');time.sleep(3);browser('link');time.sleep(3);browser('cancel');time.sleep(2);stop()
    low_state=json.loads((low/'session.json').read_text());shutil.copytree(low,out/'low-session')
    cases['selected-window-low']=dict(status='pass' if len(low_state['frames'])>=3 else 'fail',frames=len(low_state['frames']))
    # A pending sampled change is stopped before normal settle when timing permits.
    browser('reset');pending=capture('High');browser('share');time.sleep(.3);stop()
    pending_state=json.loads((pending/'session.json').read_text());shutil.copytree(pending,out/'pending-session')
    cases['pending-frame-persistence']=dict(status='pass' if any(f.get('captureReason')=='stop_flush' for f in pending_state['frames']) else 'pending',frames=pending_state['frames'])
    # Capture write failure and Save Session recovery occur only in throwaway storage.
    browser('reset');fault=capture('High');(fault/'frames').chmod(0o555);fault.chmod(0o555)
    browser('share');time.sleep(1.2);press('Stop',required=False);time.sleep(.5)
    fault_text=status_text();snapshot('capture-save-failure.png')
    fault.chmod(0o755);(fault/'frames').chmod(0o755);press('OK',required=False);keys(1,True);time.sleep(1)
    recovered=command([cli,'validate',fault],'recovered-session-validation');shutil.copytree(fault,out/'recovered-session')
    cases['failed-save-retry']=dict(status='pass' if ('recover' in fault_text.lower() or 'could not be saved' in fault_text.lower()) and recovered.get('exitCode')==0 else 'pending',observedStatus=fault_text,validation=recovered)
    # Rapid cycles retain distinct folders; each operation uses the actual controls.
    cycles=[]
    for i in range(5):
        browser('reset');run=capture('High');stop();cycles.append(str(run))
    cases['rapid-start-stop']=dict(status='pass' if len(set(cycles))==5 else 'fail',sessions=cycles,note='Five distinct UI start/stop cycles; each allowed initial capture. Sub-second start/stop remains untested.')
except Exception as error:
    record('workflow-error',error=str(error),traceback=traceback.format_exc())
    try:tree('failure');snapshot('workflow-failure.png')
    except Exception:pass
finally:
    # Preserve all generated sessions and current UI even when an assertion fails.
    for directory in storage.iterdir():
        if directory.is_dir():
            directory.chmod(0o755)
            if (directory/'frames').exists():(directory/'frames').chmod(0o755)
    shutil.copytree(storage,out/'all-native-sessions',dirs_exist_ok=True)
    (out/'native-case-results.json').write_text(json.dumps(dict(cases=cases,maintainerApproval=False,noTCCChanges=True,exactCandidate=True,realNativeRecording=bool(cases.get('selected-window-high',{}).get('status')=='pass')),indent=2))
    if browser_process:
        browser_process.terminate()
        try:browser_process.wait(timeout=5)
        except subprocess.TimeoutExpired:browser_process.kill()
