"""Controlled Finder-only investigation. Development images, disposable hosted Mac only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true'
root = Path.cwd()
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'; out.mkdir(exist_ok=True)
sys.path[:0] = ['distribution/dmg', 'scripts']
import dmg
app = temp / 'unpacked/ContextLens.app'
baseline = subprocess.check_output(['git', 'show', 'e782f4e:distribution/dmg/dmg.py'], text=True)

def command(args, name):
    try:
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=30)
        value = dict(exitCode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired:
        value = dict(status='timeout')
    (out / (name + '.json')).write_text(json.dumps(value, indent=2))
    return value

rgb = baseline.replace('viewOptionsVersion=1, backgroundType=2,',
    'viewOptionsVersion=1, backgroundColorRed=1.0, backgroundColorGreen=1.0, backgroundColorBlue=1.0, backgroundType=2,')
one = baseline.replace("run('tiffutil', '-cathidpicheck', work / '1x.tiff', work / '2x.tiff',\n            '-out', stage / '.background/background.tiff')",
    "__import__('shutil').copyfile(work / '1x.tiff', stage / '.background/background.tiff')")
for label, source in [('rgb-defaults', rgb), ('single-resolution-tiff', one), ('finder-authored', baseline)]:
    scope = {'__file__': str(root / 'distribution/dmg/dmg.py'), '__name__': 'controlled_dmg'}
    exec(compile(source, '<controlled-dmg-builder>', 'exec'), scope)
    if label == 'finder-authored':
        original = scope['configure']
        def authored(mount):
            original(mount)
            script = '''on run argv
                tell application "Finder"
                    set folderAlias to POSIX file (item 1 of argv) as alias
                    open folderAlias
                    set w to front window
                    set current view of w to icon view
                    set opts to icon view options of w
                    set background picture of opts to POSIX file (item 2 of argv) as alias
                    set icon size of opts to 104
                    delay 2
                    close w
                end tell
            end run'''
            command(['osascript', '-e', script, mount, mount / '.background/background.tiff'], 'finder-authoring')
            time.sleep(3)
            from ds_store import DSStore
            with DSStore.open(str(mount / '.DS_Store'), 'r') as store:
                options = store['.']['icvp']
                (out / 'finder-authored-options.json').write_text(json.dumps(options, default=lambda x: '<binary>', indent=2))
        scope['configure'] = authored
    image = temp / (label + '.dmg')
    try:
        result = scope['build'](app, image)
        (out / (label + '-structure.json')).write_text(json.dumps(result, indent=2))
        for appearance in ['Light', 'Dark']:
            command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to ' + ('true' if appearance == 'Dark' else 'false')], label + '-' + appearance + '-appearance')
            with dmg.mounted(image) as mount:
                command(['open', mount], label + '-' + appearance + '-open')
                time.sleep(4)
                folder = out / (label + '-' + appearance.lower()); folder.mkdir()
                command(['swift', 'qa/finder-snapshot.swift', mount, folder], label + '-' + appearance + '-snapshot')
    except Exception as error:
        (out / (label + '-error.txt')).write_text(repr(error))
