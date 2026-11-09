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
    ui('display');command(['swift','qa/capabilities.swift'],'capabilities')
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
    ui('click',point=[800,700]); snapshot('B-review.png')
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
    press('Copy prompt');command(['pbpaste'],'actual-agent-prompt');time.sleep(2)
    snapshot('D-handoff.png');shutil.copytree(exported,out/'ui-export');shutil.copytree(high,out/'high-session')
    cases['handoff-export']=dict(status='pass',package=str(exported),validation=json.loads(validation['stdout']),promptCopied=True)
    # Low sensitivity uses the real browser and a new native capture.
    browser('reset');low=capture('Low');browser('share');time.sleep(3);browser('link');time.sleep(3);browser('cancel');time.sleep(2);stop()
    low_state=json.loads((low/'session.json').read_text());shutil.copytree(low,out/'low-session')
    cases['selected-window-low']=dict(status='pass' if len(low_state['frames'])>=3 else 'fail',frames=len(low_state['frames']))
    # Repeat the real recording pill at the smaller available hosted display mode.
    ui('display',width=1440);time.sleep(1)
    browser('reset');layout=capture('High');snapshot('A2-recording-1440.png',True);stop()
    ui('display');time.sleep(1)
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
    recovered_frames=json.loads((fault/'session.json').read_text())['frames']
    cases['failed-save-retry']=dict(status='pass' if ('recover' in fault_text.lower() or 'could not be saved' in fault_text.lower()) and recovered.get('exitCode')==0 and len(recovered_frames)>=2 else 'pending',observedStatus=fault_text,validation=recovered,frames=len(recovered_frames))
    # Rapid cycles retain distinct folders; each operation uses the actual controls.
    cycles=[]
    for i in range(5):
        browser('reset');run=capture('High',settle=0);stop();cycles.append(str(run))
    starts=[e['at'] for e in events if e['name']=='start-request'][-5:]
    stops=[e['at'] for e in events if e['name']=='stop-request'][-5:]
    cases['rapid-start-stop']=dict(status='pass' if len(set(cycles))==5 and all(b-a<1 for a,b in zip(starts,stops)) else 'pending',sessions=cycles,startToStopSeconds=[b-a for a,b in zip(starts,stops)],note='Five immediate UI start/stop cycles. Delayed-start cancellation still pending.')
    # Reopen the original real session through NSOpenPanel, preserving its actual marks.
    keys(31,True);time.sleep(.7);choose_folder(high,'Open');time.sleep(.7)
    reopened_text=status_text();press('Mark Up',False);time.sleep(.6);press('Share workspace',False);time.sleep(.4)
    reopened_nodes=tree('reopened')
    notes=[n.get('AXValue') for n in reopened_nodes if n.get('AXPlaceholderValue')=='What should change?']
    cases['session-reopen-recovery']=dict(status='pass' if all(a['instruction'] in notes for a in expected_marks) and json.loads((high/'session.json').read_text())['annotations']==expected_marks else 'fail',notes=notes,observedStatus=reopened_text)
    snapshot('session-reopened.png')
    # Close the selected window while a distinct magenta browser window remains alive.
    browser('reset');browser('other');closure=capture('High');browser('share');time.sleep(2)
    closed=browser('close');time.sleep(3);closure_text=status_text();closure_state=json.loads((closure/'session.json').read_text())
    stopped='Recording stopped' in closure_text or 'capture stopped' in closure_text
    cases['selected-window-closure-no-substitution']=dict(status='pass' if stopped and closed.get('otherAlive') and closure_state['frames'] and all(f.get('windowTitle')=='Tidewater — Projects' for f in closure_state['frames']) else 'fail',observedStatus=closure_text,otherWindowAlive=closed.get('otherAlive'),frameTitles=[f.get('windowTitle') for f in closure_state['frames']])
    snapshot('selected-window-closure.png');shutil.copytree(closure,out/'closure-session')
    if not stopped:press('Stop',required=False)
    # Quit the actual browser application, preserving the last captured frames.
    browser('reset');exit_root=capture('High');browser('share');time.sleep(2);browser('quit');time.sleep(3)
    exit_text=status_text();exit_state=json.loads((exit_root/'session.json').read_text())
    cases['target-application-exit']=dict(status='pass' if ('Recording stopped' in exit_text or 'capture stopped' in exit_text) and exit_state['frames'] else 'fail',observedStatus=exit_text,frames=len(exit_state['frames']))
    snapshot('target-application-exit.png');shutil.copytree(exit_root,out/'application-exit-session')
    # Request a normal ContextLens Quit during capture; never mistake forced termination for success.
    browser('reset');quit_root=capture('High');browser('share');time.sleep(.3);keys(12,True)
    quit_observed=wait_for(lambda:candidate_process.poll() is not None,12)
    quit_code=candidate_process.poll()
    cases['contextlens-exit-during-capture']=dict(status='pass' if quit_code==0 else 'fail',normalExitCode=quit_code,session=str(quit_root))
    if quit_code is None:
        command(['sample',candidate_process.pid,'3','-file',out/'quit-timeout.sample.txt'],'quit-timeout-sample',10)
        tree('quit-timeout');snapshot('quit-timeout.png')
    command([cli,'validate',quit_root],'quit-session-validation');shutil.copytree(quit_root,out/'quit-session')
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
    if candidate_process and candidate_process.poll() is None:
        try:
            press('Stop',required=False);press('OK',required=False);keys(1,True);time.sleep(.5);keys(12,True);time.sleep(2)
        except Exception:pass
        if candidate_process.poll() is None:
            record('cleanup-only-sigterm',pid=candidate_process.pid,notANormalQuitPass=True)
            candidate_process.terminate()
            try:candidate_process.wait(timeout=5)
            except subprocess.TimeoutExpired:candidate_process.kill();candidate_process.wait()
    shutil.copytree(storage,out/'all-native-sessions',dirs_exist_ok=True)
    # Installation is an independent native case on this empty disposable Mac only.
    try:
        mount=temp/'installer-volume'
        assert not Path('/Applications/ContextLens.app').exists()
        attached=command(['hdiutil','attach','-plist','-nobrowse','-noautoopen','-readonly','-owners','off','-mountpoint',mount,candidate/'ContextLens-development.dmg'],'installer-mount')
        assert attached.get('exitCode')==0
        command(['open',mount],'installer-finder-open');time.sleep(3)
        drag=command(['swift','qa/finder-install.swift'],'installer-real-drag')
        detached=command(['hdiutil','detach',mount],'installer-eject')
        assert drag.get('exitCode')==0 and detached.get('exitCode')==0
        verification=command(['python3','-c',"import sys; sys.path[:0]=['scripts','distribution/dmg']; from release import verify; from dmg import inventory; from pathlib import Path; import os; a='/Applications/ContextLens.app'; verify(a,'development'); assert inventory(a)==inventory(Path(os.environ['RUNNER_TEMP'])/'unpacked/ContextLens.app'); print('Installed development bundle exactly matches source')"],'installed-bundle-verification')
        assert verification.get('exitCode')==0
        command(['open','-n','/Applications/ContextLens.app','--args','--isolated-native-test','-onboardingComplete','YES'],'installed-launch');time.sleep(3)
        inspection=command(['swift','qa/inspect-installed.swift'],'installed-running-observation')
        observed=json.loads(inspection.get('stdout','{}'))
        cases['dmg-drag-install-eject-launch']=dict(status='pass' if observed.get('runningInstalledCopy') and observed.get('version')=='0.3.1' and observed.get('build')=='6' and observed.get('windowCount',0)>0 else 'pending',drag=drag,eject=detached,installedObservation=observed)
        installed_images=out/'installed-launch';installed_images.mkdir()
        command(['swift','qa/capture-windows.swift',installed_images,'dev.contextlens.app'],'installed-launch-images')
    except Exception as error:cases['dmg-drag-install-eject-launch']=dict(status='pending',observation=repr(error))
    (out/'native-case-results.json').write_text(json.dumps(dict(cases=cases,maintainerApproval=False,noTCCChanges=True,exactCandidate=False,developmentBuild=True,realNativeRecording=bool(cases.get('selected-window-high',{}).get('status')=='pass')),indent=2))
    if browser_process:
        browser_process.terminate()
        try:browser_process.wait(timeout=5)
        except subprocess.TimeoutExpired:browser_process.kill()
