"""Observe the exact candidate DMG in real Finder; never build a replacement."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

assert os.environ.get('GITHUB_ACTIONS')=='true'
temp=Path(os.environ['RUNNER_TEMP']);out=temp/'native-evidence';out.mkdir(exist_ok=True)
sys.path.insert(0,str(Path.cwd()/'distribution/dmg'))
import dmg
image=temp/'official-candidate/ContextLens-0.3.1-arm64.dmg'
assert image.is_file()
def command(args,name):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=90)
    (out/(name+'.json')).write_text(json.dumps(dict(exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2))
    assert p.returncode==0,name
    return p.stdout
old=subprocess.check_output(['osascript','-e','tell application "System Events" to tell appearance preferences to get dark mode'],text=True).strip()
results={}
try:
    with dmg.mounted(image) as mount:
        command(['open',mount],'finder-open');time.sleep(4)
        for mode in ['Light','Dark']:
            command(['osascript','-e','tell application "System Events" to tell appearance preferences to set dark mode to '+('true' if mode=='Dark' else 'false')],'appearance-'+mode);time.sleep(2)
            folder=out/('finder-'+mode.lower());folder.mkdir()
            command(['swift','qa/finder-snapshot.swift',mount,folder],'finder-'+mode+'-snapshot')
            pixels=json.loads(command(['swift','distribution/dmg/verify-finder-background.swift',folder/'Finder.png','distribution/dmg/assets/background@1x.png'],'finder-'+mode+'-pixels'))
            results['dmg-finder-'+mode.lower()]=dict(status='pass' if pixels['renderedArtwork'] else 'fail',pixelCheck=pixels)
finally:
    command(['osascript','-e','tell application "System Events" to tell appearance preferences to set dark mode to '+old],'restore-runner-appearance')
    (out/'finder-cases.json').write_text(json.dumps(results,indent=2))
