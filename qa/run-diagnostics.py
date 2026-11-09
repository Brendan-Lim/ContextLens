"""Disposable hosted Mac only. No trust approval, privacy changes, or app rebuilds."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path.cwd()
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'
out.mkdir()
candidate = temp / 'exact-candidate'
def run(args, name, timeout=300):
    started = time.time()
    try:
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout)
        result = dict(exitCode=p.returncode, seconds=time.time()-started, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired:
        result = dict(status='timeout', seconds=time.time()-started)
    (out / (name+'.json')).write_text(json.dumps(result, indent=2))
    return result
run(['gh','run','download','42557369631','--repo','Brendan-Lim/ContextLens','--name','official-candidate-0.3.1','--dir',candidate], 'download')
expected = {'ContextLens-0.3.1-arm64.zip':'f4ac0a2cc3dc5fd6f120a21e3f7152f86351b7f8bf93e3908f57bc5a9ad3425e',
            'ContextLens-0.3.1-arm64.dmg':'52872a5e0221fac2960fb8d5c349743201bbb5800a914eb77b1b48416473b37d'}
for name, digest in expected.items():
    assert hashlib.sha256((candidate/name).read_bytes()).hexdigest() == digest
(out/'candidate-provenance.json').write_bytes((candidate/'provenance.json').read_bytes())
run(['python3','scripts/unnotarized-release.py','verify-assets',candidate], 'verify-assets')
run(['ditto','-x','-k',candidate/'ContextLens-0.3.1-arm64.zip',temp/'unpacked'], 'unpack')
app = temp/'unpacked/ContextLens.app'
cli = app/'Contents/MacOS/contextlens-cli'
run(['sw_vers'], 'macos')
run(['sysctl','hw.model','hw.memsize','kern.hv_support'], 'hardware')
run(['df','-h',temp], 'disk')
run(['swift','qa/capabilities.swift'], 'capabilities')
run(['spctl','--assess','--type','execute','-vv',app], 'read-only-gatekeeper-assessment')
run(['xattr','-p','com.apple.quarantine',app], 'quarantine-read-only')
run(['python3','scripts/verify-native.py','--isolated-environment','--app',app,'--output',out/'own-window'], 'native-self-window', timeout=420)
run([cli,'demo',out/'synthetic-cli-session'], 'synthetic-demo')
run([cli,'validate',out/'synthetic-cli-session'], 'synthetic-session-validation')
run([cli,'export',out/'synthetic-cli-session',out/'synthetic-cli-package','--all-frames','--keep-duplicates'], 'synthetic-export')
run(['python3','scripts/validate_package.py',out/'synthetic-cli-package'], 'synthetic-package-validation')
run([cli,'profile'], 'comparator-profile')
# Real Finder rendering in the disposable guest; original candidate remains read-only.
mount = temp/'installer-volume'
attached = run(['hdiutil','attach','-plist','-nobrowse','-noautoopen','-readonly','-mountpoint',mount,candidate/'ContextLens-0.3.1-arm64.dmg'], 'finder-mount')
if attached.get('exitCode') == 0:
    run(['open',mount], 'finder-open')
    time.sleep(4)
    folder = out/'finder'; folder.mkdir()
    run(['swift','qa/capture-windows.swift',folder,'com.apple.finder'], 'finder-capture')
    run(['hdiutil','detach',mount], 'finder-detach')
# A real capture panel is diagnostic only; not claimed as a selected Tidewater recording.
process = subprocess.Popen([str(app/'Contents/MacOS/ContextLens'),'--isolated-native-test','--capture-preview'])
try:
    time.sleep(7)
    folder = out/'capture-panel'; folder.mkdir()
    run(['swift','qa/capture-windows.swift',folder,'dev.contextlens.app'], 'capture-panel')
finally:
    process.terminate()
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired: process.kill(); process.wait()
(out/'scope.json').write_text(json.dumps(dict(isolatedEnvironment=True, exactCandidate=True,
    nativeRecordingAccepted=False, humanAcceptance=False, sessionProvenance='CLI-generated synthetic fixture',
    noSecurityOrPrivacyApprovalsAutomated=True, noApplicationRebuild=True), indent=2))
