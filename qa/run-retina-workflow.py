"""Development-build native UI operation on a disposable hosted Mac. No security approvals."""
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
def snapshot(name,panel=False):
    result=ui('snapshot',file=str(images/name),**({'title':'ContextLens Capture'} if panel else {}))
    proof=command([temp/'window-proof',str(result['id']),images/name],name+'-retina-proof')
    assert proof['exitCode']==0,'Window not proven Retina: '+name
    return result
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
def capture(sensitivity,photo=False,settle=2):
    keys(45,True);time.sleep(.8)
    press('Tidewater',False)
    press(sensitivity)
    if photo:snapshot('A-capture.png',True)
    old={str(p) for p in storage.iterdir()}
    record('start-request',sensitivity=sensitivity)
    press('Start Capture');time.sleep(settle)
    if photo:snapshot('A2-recording.png',True)
    root=wait_for(lambda:next((p for p in storage.iterdir() if str(p) not in old and (p/'session.json').exists()),None))
    assert root is not None,'No capture session created'
    return root
def stop():
    record('stop-request')
    press('Stop');time.sleep(1.4)
def note(text):
    nodes=tree('note-target')
    fields=[n for n in nodes if n.get('AXRole') in ('AXTextField','AXTextArea') and (n.get('AXPlaceholderValue')=='What should change?' or n.get('AXDescription')=='What should change?' or n.get('AXValue','')=='')]
    assert fields,'No native note field'
    ui('type',index=fields[-1]['index'],value=text)
def choose_folder(path,prompt='Save Hand Off'):
    keys(5,True,True);time.sleep(.6)
    nodes=tree('folder-go')
    fields=[n for n in nodes if n.get('AXRole') in ('AXTextField','AXComboBox') and n.get('AXEnabled',True) and n.get('AXIdentifier')!='Search' and (n.get('AXFocused') or n.get('AXRole')=='AXComboBox')]
    assert fields,'No native Go To Folder field'
    ui('type',index=fields[-1]['index'],value=str(path));keys(36);time.sleep(.7)
    press(prompt,required=False);time.sleep(1)
def status_text():return ' '.join(str(n.get('AXValue',''))+' '+str(n.get('AXTitle','')) for n in ui('tree').get('nodes',[]))
browser_process=None;candidate_process=None
try:
    assert os.environ.get('GITHUB_ACTIONS')=='true', 'Disposable hosted runner required'
    candidate=temp/'development-candidate'
    assert app.exists()
    assert command(['swiftc','qa/ui.swift','-o',helper],'compile-ui-helper')['exitCode']==0
    ui('display');command([temp/'display-proof'],'capture-display-state')
    browser_log=(out/'browser-process.log').open('w')
    browser_process=subprocess.Popen(['node','qa/tidewater.cjs'],stdout=browser_log,stderr=browser_log)
    assert wait_for(lambda:(out/'browser-ready.json').exists(),30),'Browser failed'
    origin=json.loads((out/'browser-ready.json').read_text())['origin']
    application_log=(out/'candidate-process.log').open('w')
    candidate_process=subprocess.Popen([str(app/'Contents/MacOS/ContextLens'),'--isolated-native-test','--capture-preview','-onboardingComplete','YES','-storagePath',str(storage),'-ApplePersistenceIgnoreState','YES','-NSRequiresAquaSystemAppearance','YES'],stdout=application_log,stderr=application_log)
    record('launch-candidate',method='direct development binary; existing runner access; no privacy settings changed',pid=candidate_process.pid)
    time.sleep(4)
    nodes=tree('launch')
    press('Start using ContextLens',required=False)
    ui('resize',width=1320,height=860,x=40,y=40,required=False)
    high=capture('High',True)
    browser('share');time.sleep(3)
    browser('link');time.sleep(3)
    browser('invite');browser('fill');time.sleep(3)
    state=json.loads((high/'session.json').read_text());preferred=state['frames'][-1]['id'];geometry=browser('state')
    snapshot('A2-recording-three-states.png',True)
    browser('cancel');time.sleep(3);stop()
    state=json.loads((high/'session.json').read_text());assert len(state['frames'])>=3
    cases['selected-window-high']=dict(status='pass',frames=len(state['frames']),session=str(high),preferredFrame=preferred)
    first=state['frames'][0];press('Include '+first['name']+' in hand-off')
    rename=next(n for n in tree('review-before-rename') if n.get('AXPlaceholderValue')=='State name' and n.get('AXValue')==next(f for f in state['frames'] if f['id']==preferred)['name'])
    ui('type',index=rename['index'],value='Share workspace')
    state=json.loads((high/'session.json').read_text())
    assert next(f for f in state['frames'] if f['id']==preferred)['name']=='Share workspace'
    keys(53); snapshot('B-review.png')
    press('Mark Up',False);time.sleep(.8)
    preferred_frame=next(f for f in state['frames'] if f['id']==preferred)
    press(preferred_frame['name'],False);time.sleep(.8)
    nodes=tree('markup-before')
    available=[n for n in nodes if n.get('AXRole')=='AXImage' and n.get('width',0)>300 and n.get('height',0)>200]
    assert available,'Native canvas image has no accessible bounds'
    image=max(available,key=lambda n:n['width']*n['height'])
    scale=preferred_frame['displayScale'];assert scale==2,'Tidewater was not rendered on Retina display'
    logical_width=preferred_frame['width']/scale;logical_height=preferred_frame['height']/scale
    border=(logical_width-geometry['innerWidth'])/2
    top=logical_height-geometry['innerHeight']-border
    def canvas(x,y):return [image['x']+(x+border)/logical_width*image['width'],image['y']+(y+top)/logical_height*image['height']]
    cancel,send=geometry['cancel'],geometry['send']
    press('Box');ui('drag',**{'from':canvas(cancel['x']-4,cancel['y']-4),'to':canvas(send['x']+send['width']+4,send['y']+send['height']+4)})
    note('Align the action buttons with the right edge of the email field.')
    avatar=geometry['avatar'];press('Highlight');ui('drag',**{'from':canvas(avatar['x']+avatar['width']/2,avatar['y']+3),'to':canvas(avatar['x']+avatar['width']/2,avatar['y']+avatar['height']-3)})
    note('Center this avatar vertically in its row, like the one above.')
    state=json.loads((high/'session.json').read_text());assert len(state['annotations'])==2
    assert [a['instruction'] for a in state['annotations']]==['Align the action buttons with the right edge of the email field.','Center this avatar vertically in its row, like the one above.'],'Native notes did not match requested instructions'
    expected_marks=state['annotations'];ui('click',point=[image['x']+image['width']-8,image['y']+image['height']-8])
    keys(6,True);time.sleep(.4);undone=json.loads((high/'session.json').read_text())['annotations']
    keys(6,True,True);time.sleep(.4);redone=json.loads((high/'session.json').read_text())['annotations']
    cases['review-annotation-undo-redo']=dict(status='pass' if undone!=expected_marks and redone==expected_marks else 'fail',undoChanged=undone!=expected_marks,redoRestored=redone==expected_marks,marks=redone)
    snapshot('C-markup.png')
    press('Hand Off',False);time.sleep(1)
    nodes=tree('handoff-before')
    task=next(n for n in nodes if n.get('AXPlaceholderValue')=='What should the agent do?' or n.get('AXDescription')=='What should the agent do?')
    ui('type',index=task['index'],value='Polish the Share workspace dialog.');time.sleep(1)
    assert json.loads((high/'session.json').read_text()).get('task')=='Polish the Share workspace dialog.'
    press('Save Hand Off');time.sleep(.7);choose_folder(parent)
    exported=wait_for(lambda:next(parent.glob('*/manifest.json'),None),15)
    assert exported,'Native export did not complete'
    exported=exported.parent
    validation=command(['python3','scripts/validate_package.py',exported],'ui-export-validation')
    assert validation['exitCode']==0
    press('Copy prompt');copied=command(['pbpaste'],'actual-agent-prompt');assert str((exported/'context.md').resolve()) in copied['stdout'];assert 'Polish the Share workspace dialog.' in copied['stdout'];time.sleep(2)
    snapshot('D-handoff.png');shutil.copytree(exported,out/'ui-export');shutil.copytree(high,out/'high-session')
    cases['handoff-export']=dict(status='pass',package=str(exported),validation=json.loads(validation['stdout']),promptCopied=True)
    # Reproduce the approved reopened Mark Up state through the real file picker.
    keys(31,True);time.sleep(.7);choose_folder(high,'Open');time.sleep(.7)
    press('Mark Up',False);time.sleep(.6);press('Share workspace',False);time.sleep(.5)
    reopened=tree('reopened')
    assert all(a['instruction'] in [n.get('AXValue') for n in reopened] for a in expected_marks)
    snapshot('C-markup.png')
    for frame in json.loads((high/'session.json').read_text())['frames']:
        assert frame['displayScale']==2
    cases['retina-session']=dict(status='pass',scale=2,states=len(state['frames']),annotationIDs=[a['id'] for a in expected_marks])
    (out/'screenshot-results.json').write_text(json.dumps(cases,indent=2))
    keys(12,True);candidate_process.wait(timeout=12)
except Exception as error:
    record('workflow-error',error=str(error),traceback=traceback.format_exc())
    try:tree('failure');snapshot('workflow-failure.png')
    except Exception:pass
    raise
finally:
    # Retain the real sessions/export even if a later capture or assertion fails.
    shutil.copytree(storage,out/'all-native-sessions',dirs_exist_ok=True)
    shutil.copytree(parent,out/'all-native-exports',dirs_exist_ok=True)
    if candidate_process and candidate_process.poll() is None:
        candidate_process.terminate()
        try:candidate_process.wait(timeout=5)
        except subprocess.TimeoutExpired:candidate_process.kill();candidate_process.wait()
    if browser_process:
        browser_process.terminate()
        try:browser_process.wait(timeout=5)
        except subprocess.TimeoutExpired:browser_process.kill();browser_process.wait()
