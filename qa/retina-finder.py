"""Real current development DMG, real Finder, disposable Retina display only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true'
root = Path.cwd(); temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'; out.mkdir(exist_ok=True)
sys.path.insert(0, str(root / 'distribution/dmg'))
import dmg
candidate = temp / 'development-candidate'; candidate.mkdir(exist_ok=True)
image = candidate / 'ContextLens-development.dmg'
app = temp / 'unpacked/ContextLens.app'
source = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
main = '40ad911d5c5fa68f4325e5ae0afc41da1de158ad'
paths = ['Sources','Package.swift','Brand','distribution/dmg','scripts','config','docs/screenshot-kit/demo-site']
assert not subprocess.check_output(['git','diff','--name-only',main,'HEAD','--',*paths],text=True).strip()
(out/'production-input-comparison.json').write_text(json.dumps(dict(source=source,productionSource=main,matchingProductionPaths=paths,officialCandidate=False),indent=2))
for attempt in range(1,4):
    try:
        verification=dmg.build(app,image)
        (out/'dmg-verification.json').write_text(json.dumps(verification,indent=2))
        break
    except subprocess.CalledProcessError as error:
        (out/('dmg-build-failed-attempt-'+str(attempt)+'.json')).write_text(json.dumps(dict(command=error.cmd,exitCode=error.returncode,stdout=error.stdout,stderr=error.stderr),indent=2))
        if attempt==3:raise
        time.sleep(5)
def command(args,name):
    p = subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=90)
    (out/(name+'.json')).write_text(json.dumps(dict(exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2))
    assert p.returncode == 0,name
    return p.stdout
old = subprocess.run(['osascript','-e','tell application "System Events" to tell appearance preferences to get dark mode'],capture_output=True,text=True,check=True).stdout.strip()
try:
    with dmg.mounted(image) as mount:
        command(['open',mount],'finder-open');time.sleep(4)
        for appearance in ['Light','Dark']:
            command(['osascript','-e','tell application "System Events" to tell appearance preferences to set dark mode to '+('true' if appearance=='Dark' else 'false')],'appearance-'+appearance)
            time.sleep(2)
            folder=out/('finder-'+appearance.lower());folder.mkdir(exist_ok=True)
            raw=command(['swift','qa/finder-snapshot.swift',mount,folder],'finder-'+appearance+'-snapshot')
            shot=json.loads(raw)
            command([temp/'window-proof',str(shot['windowID']),folder/'Finder.png'],'finder-'+appearance+'-retina-proof')
            command(['swift','distribution/dmg/verify-finder-background.swift',folder/'Finder.png','distribution/dmg/assets/background@1x.png'],'finder-'+appearance+'-pixels')
finally:
    command(['osascript','-e','tell application "System Events" to tell appearance preferences to set dark mode to '+old],'restore-runner-appearance')
