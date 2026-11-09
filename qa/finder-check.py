"""Disposable hosted Mac: compare alias-only and bookmark layouts with identical app/artwork."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Disposable hosted runner required'
root = Path.cwd()
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'
out.mkdir(exist_ok=True)
candidate = temp / 'development-candidate'
candidate.mkdir()
app = temp / 'unpacked/ContextLens.app'
sys.path[:0] = [str(root / 'distribution/dmg'), str(root / 'scripts')]
import dmg
from release import package

def command(args, name, timeout=120):
    try:
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout)
        result = dict(exitCode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired:
        result = dict(status='timeout')
    (out / (name + '.json')).write_text(json.dumps(result, indent=2))
    return result

command(['sw_vers'], 'macos')
command(['sysctl', 'hw.model', 'hw.memsize'], 'machine')
command(['swift', 'qa/capabilities.swift'], 'capabilities')
source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
production = '28b836e'
differences = subprocess.check_output(['git', 'diff', '--name-only', production, 'HEAD', '--', 'Sources', 'Package.swift', 'Brand', 'distribution/dmg', 'scripts', 'config'], text=True).splitlines()
assert not differences, 'Production inputs differ from reviewed fix source'
(out / 'production-input-comparison.json').write_text(json.dumps(dict(productionSource=subprocess.check_output(['git','rev-parse',production],text=True).strip(), diagnosticSource=source, matchingProductionPaths=True), indent=2))
(out / 'development-source.json').write_text(json.dumps(dict(source=source, officialCandidate=False,
    maintainerAcceptance=False, noSecurityOrPrivacyApprovalsAutomated=True), indent=2))
# Build the control using the exact pre-fix builder; the bundle and image assets are shared.
baseline = subprocess.check_output(['git', 'show', 'e782f4e:distribution/dmg/dmg.py'], text=True)
scope = {'__file__': str(root / 'distribution/dmg/dmg.py'), '__name__': 'baseline_dmg'}
exec(compile(baseline, '<pre-fix-dmg-builder>', 'exec'), scope)
control = candidate / 'ContextLens-alias-only-control.dmg'
(out / 'control-structural-verification.json').write_text(json.dumps(scope['build'](app, control), indent=2))
patched = candidate / 'ContextLens-development.dmg'
(out / 'patched-structural-verification.json').write_text(json.dumps(dmg.build(app, patched), indent=2))
(out / 'development-zip-verification.json').write_text(json.dumps(package(app, candidate, development=True), indent=2, default=str))
# Keep only public-source provenance and final-byte hashes here; all evidence is encrypted.
(out / 'development-hashes.json').write_text(json.dumps({p.name: dmg.sha256(p) for p in candidate.iterdir() if p.is_file()}, indent=2))
for label, image in [('alias-only-control', control), ('patched', patched)]:
    for appearance in ['Light', 'Dark']:
        # Ordinary appearance preference only. No trust, TCC, or security dialogs are approved.
        setting = command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to ' + ('true' if appearance == 'Dark' else 'false')], label + '-' + appearance + '-appearance', 15)
        command(['defaults', 'read', '-g', 'AppleInterfaceStyle'], label + '-' + appearance + '-appearance-readback')
        with dmg.mounted(image) as mount:
            command(['open', mount], label + '-' + appearance + '-finder-open')
            time.sleep(4)
            folder = out / ('finder-' + label + '-' + appearance.lower())
            folder.mkdir()
            shot = command(['swift', 'qa/finder-snapshot.swift', mount, folder], label + '-' + appearance + '-snapshot')
            if shot.get('exitCode') == 0:
                command(['swift', 'distribution/dmg/verify-finder-background.swift', folder/'Finder.png', 'distribution/dmg/assets/background@1x.png'], label + '-' + appearance + '-rendered-pixels')
        time.sleep(1)

command(['osascript', '-e', 'tell application "System Events" to tell appearance preferences to set dark mode to false'], 'restore-light-for-product-media', 15)
