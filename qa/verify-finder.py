"""Real Finder only, on an ephemeral GitHub-hosted Mac. Never use on an owner's Mac."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true'
assert os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'; out.mkdir()
sys.path[:0] = ['distribution/dmg', 'scripts']
import dmg
from release import package

def command(args, name, check=True, timeout=90):
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout)
    (out / (name + '.json')).write_text(json.dumps(dict(exitCode=p.returncode, stdout=p.stdout, stderr=p.stderr), indent=2))
    if check and p.returncode: raise RuntimeError(name + ' failed')
    return p

command(['sw_vers'], 'macos')
command(['git', 'rev-parse', 'HEAD'], 'prototype-source')
app = temp / 'unpacked/ContextLens.app'
image = temp / 'ContextLens-prototype.dmg'
result = dmg.build(app, image)
(out / 'structural.json').write_text(json.dumps(result, indent=2))
archive = package(app, temp / 'archive', development=True)
with tempfile.TemporaryDirectory(dir=temp) as destination:
    command(['ditto', '-x', '-k', archive, destination], 'extract-zip')
    assert dmg.inventory(Path(destination) / 'ContextLens.app') == dmg.inventory(app)
(out / 'zip-dmg-equality.json').write_text(json.dumps(dict(equal=True, dmgSHA256=dmg.sha256(image), zipSHA256=dmg.sha256(archive)), indent=2))
old_hidden = subprocess.run(['defaults', 'read', 'com.apple.finder', 'AppleShowAllFiles'], capture_output=True, text=True)
old_dark = subprocess.check_output(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to get dark mode'], text=True).strip()
results = {}
try:
    for hidden in [False, True]:
        command(['defaults', 'write', 'com.apple.finder', 'AppleShowAllFiles', '-bool', str(hidden).lower()], 'set-hidden-' + str(hidden))
        command(['killall', 'Finder'], 'restart-finder-' + str(hidden), check=False)
        time.sleep(3)
        for dark in [False, True]:
            label = ('hidden-on' if hidden else 'hidden-off') + ('-dark' if dark else '-light')
            command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to ' + str(dark).lower()], label + '-appearance')
            command(['defaults', 'read', 'com.apple.finder', 'AppleShowAllFiles'], label + '-hidden-readback')
            command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to get dark mode'], label + '-appearance-readback')
            with dmg.mounted(image) as mount:
                (out / (label + '-root.json')).write_text(json.dumps(sorted(p.name for p in mount.iterdir())))
                command(['open', mount], label + '-open'); time.sleep(4)
                folder = out / label; folder.mkdir()
                command(['swift', 'qa/finder-snapshot.swift', mount, folder], label + '-snapshot')
                pixels = command(['swift', 'distribution/dmg/verify-finder-background.swift', folder / 'Finder.png', 'distribution/dmg/assets/background@1x.png'], label + '-pixels')
                results[label] = json.loads(pixels.stdout)
                if hidden and dark:
                    command(['swift', 'qa/finder-install.swift'], 'actual-finder-drag')
                    installed = Path('/Applications/ContextLens.app')
                    assert dmg.inventory(installed) == dmg.inventory(app)
                    command(['codesign', '--verify', '--deep', '--strict', installed], 'installed-signature')
    # Launch only after the last mount context has completed a clean detach.
    command(['hdiutil', 'info', '-plist'], 'images-after-eject')
    assert str(image) not in (out / 'images-after-eject.json').read_text()
    command(['open', '/Applications/ContextLens.app'], 'installed-launch-after-eject'); time.sleep(5)
    state = json.loads(command(['swift', 'qa/inspect-installed.swift'], 'installed-state-after-eject').stdout)
    assert state.get('runningInstalledCopy') and state.get('finishedLaunching') and state.get('version') == '0.3.1' and state.get('build') == '6'
    command(['swift', 'qa/inspect-installed.swift', '--terminate'], 'terminate-installed')
    (out / 'matrix-results.json').write_text(json.dumps(results, indent=2))
finally:
    command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to ' + old_dark], 'restore-appearance', check=False)
    if old_hidden.returncode == 0:
        command(['defaults', 'write', 'com.apple.finder', 'AppleShowAllFiles', old_hidden.stdout.strip()], 'restore-hidden', check=False)
    else:
        command(['defaults', 'delete', 'com.apple.finder', 'AppleShowAllFiles'], 'restore-hidden', check=False)
    command(['killall', 'Finder'], 'restore-finder', check=False)
