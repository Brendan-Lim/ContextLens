"""Short genuine capture at a supported smaller display mode; no TCC changes."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

assert os.environ.get('GITHUB_ACTIONS') == 'true'
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'
helper = temp / 'ui-helper'
app = temp / 'unpacked/ContextLens.app'
subprocess.run(['swiftc', 'qa/ui.swift', '-o', helper], check=True)
subprocess.run(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to false'], check=True)
def ui(action, **options):
    p = subprocess.run([helper, action, json.dumps(options)], capture_output=True, text=True, timeout=20)
    result = json.loads(p.stdout)
    (out / ('pill-' + action + '-last.json')).write_text(json.dumps(result, indent=2))
    assert p.returncode == 0, action
    return result

display = ui('display', width=1600)
(out / 'pill-display-1600.json').write_text(json.dumps(display, indent=2))
assert display['setStatus'] == 0 and display['screens'][0]['width'] == 1600
browser = subprocess.Popen(['node', 'qa/tidewater.cjs'], stdout=(out / 'pill-browser.log').open('w'), stderr=subprocess.STDOUT)
app_process = None
try:
    for _ in range(120):
        if (out / 'browser-ready.json').exists(): break
        time.sleep(.25)
    origin = json.loads((out / 'browser-ready.json').read_text())['origin']
    storage = temp / 'pill-sessions'
    app_process = subprocess.Popen([str(app / 'Contents/MacOS/ContextLens'), '--isolated-native-test', '--capture-preview', '-onboardingComplete', 'YES', '-storagePath', str(storage), '-ApplePersistenceIgnoreState', 'YES', '-NSRequiresAquaSystemAppearance', 'YES'], stdout=(out / 'pill-app.log').open('w'), stderr=subprocess.STDOUT)
    time.sleep(4)
    ui('press', text='Tidewater', exact=False, role='AXButton')
    ui('press', text='High', role='AXButton')
    ui('press', text='Start Capture', role='AXButton')
    time.sleep(2)
    ui('snapshot', title='ContextLens Capture', file=str(out / 'A2-recording-1600.png'))
    for action in ['share', 'link', 'invite']:
        request = urllib.request.Request(origin + '/control', data=json.dumps(dict(action=action)).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=15) as response: response.read()
        time.sleep(3)
    ui('snapshot', title='ContextLens Capture', file=str(out / 'A2-recording-1600-four-states.png'))
    ui('press', text='Stop', role='AXButton')
    time.sleep(2)
    sessions = list(storage.glob('*/session.json'))
    assert len(sessions) == 1
    state = json.loads(sessions[0].read_text())
    (out / 'pill-capture-1600.json').write_text(json.dumps(dict(states=len(state['frames']), frameTitles=[f.get('windowTitle') for f in state['frames']], realRecording=True, maintainerAcceptance=False), indent=2))
    ui('keys', code=12, command=True)
    app_process.wait(timeout=10)
finally:
    if app_process and app_process.poll() is None: app_process.terminate()
    browser.terminate()
