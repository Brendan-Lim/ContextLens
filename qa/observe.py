"""Disposable native observations; human permission cases always remain pending.

The UI phase injects synthetic errors into a separate fresh development build.
It never represents an OS denial, grant, revocation, or recovery observation.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true'
assert os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
temp = Path(os.environ['RUNNER_TEMP'])
out = temp / 'native-evidence'; out.mkdir(exist_ok=True)

def command(args, name, check=True, timeout=90, env=None):
    try:
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout, env=env)
        result = dict(exitCode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired:
        result = dict(status='timeout')
    (out / (name + '.json')).write_text(json.dumps(result, indent=2))
    if check and result.get('exitCode') != 0: raise RuntimeError(name + ' failed')
    return result

def native():
    command(['sw_vers'], 'macos')
    command(['git', 'rev-parse', 'HEAD'], 'diagnostic-source')
    command(['git', 'diff', '--exit-code', '0b2c9a95927175d05222aa79aa9cc33ac2c8a38e', '--', 'Sources', 'scripts', 'distribution', 'config'], 'production-input-equality')
    command(['swiftc', 'qa/ui.swift', '-o', temp / 'ui-helper'], 'native-compile-ui-helper')
    install = temp / 'same-path-install/ContextLens.app'
    install.parent.mkdir()
    results = {'humanDenial': 'pending', 'humanGrant': 'pending', 'humanRevocationRecovery': 'pending',
               'freshUserConsentVerified': False, 'permissionSettingsChanged': False, 'runs': {}}
    for label, source in [('control', temp / 'control-unpacked/ContextLens.app'), ('updated', temp / 'unpacked/ContextLens.app')]:
        if install.exists(): shutil.rmtree(install)
        command(['ditto', source, install], label + '-copy')
        command(['codesign', '--verify', '--deep', '--strict', install], label + '-strict-signature')
        signature = command(['codesign', '-d', '-r-', '--verbose=4', install], label + '-identity')
        text = signature['stdout'] + signature['stderr']
        assert 'Signature=adhoc' in text
        info = plistlib.loads((install / 'Contents/Info.plist').read_bytes())
        assert info['CFBundleIdentifier'] == 'dev.contextlens.app'
        result = command(['python3', 'scripts/verify-native.py', '--isolated-environment', '--closure-only', '--app', install,
                          '--output', out / (label + '-native')], label + '-native-launcher', check=False, timeout=90)
        report = out / (label + '-native/dark-review/native-capture-verification.json')
        value = json.loads(report.read_text()) if report.exists() else {}
        results['runs'][label] = dict(cdhash=re.search(r'^CDHash=(.+)$', text, re.M).group(1),
                                     version=info['CFBundleShortVersionString'], build=info['CFBundleVersion'],
                                     launcherExit=result.get('exitCode'), nativeReport=value,
                                     nativeScreenshotPresent=(out / (label + '-native/dark-review/window.png')).exists())
        if label == 'updated':
            env = dict(os.environ, CONTEXTLENS_EXPECTED_APP=str(install))
            process = subprocess.Popen([str(install / 'Contents/MacOS/ContextLens'), '--isolated-native-test',
                                        '--capture-preview', '-onboardingComplete', 'YES'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            try:
                time.sleep(4)
                tree = command([temp / 'ui-helper', 'tree'], 'real-api-ui-before', check=False, env=env)
                if tree.get('exitCode') == 0:
                    button = 'Check Access' if 'Check Access' in tree['stdout'] else 'Refresh windows'
                    # Request verification only; never press any system consent control.
                    command([temp / 'ui-helper', 'press', json.dumps(dict(text=button))], 'real-api-check-action', check=False, env=env)
                    time.sleep(4)
                    command([temp / 'ui-helper', 'tree'], 'real-api-ui-after', check=False, env=env)
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
        # Preserve failed/blocked native results; do not infer approval from preflight.
    assert results['runs']['control']['cdhash'] != results['runs']['updated']['cdhash']
    results['sameBundleIdentifierDifferentCodeHashes'] = True
    results['sameInstallPath'] = True
    results['upgradePermissionRetention'] = 'not-established-without-human-controlled-initial-grant'
    (out / 'native-comparison.json').write_text(json.dumps(results, indent=2))

def inject_ui():
    path = Path('Sources/ContextLensApp/AppModel.swift')
    source = path.read_text()
    needle = '    func refresh(userInitiated: Bool = false) async {\n'
    assert source.count(needle) == 1
    injection = '''        // Diagnostic branch only: synthetic presentation fixture, never a TCC result.
        if ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true",
           let index = CommandLine.arguments.firstIndex(of: "--qa-access-state"), CommandLine.arguments.indices.contains(index + 1) {
            let name = CommandLine.arguments[index + 1]
            let failure = NSError(domain: "SyntheticCaptureService", code: -999,
                                  userInfo: [NSLocalizedDescriptionKey: "Synthetic enumeration error for UI inspection"])
            screenAccess = name == "unverified" ? .unverified : ScreenAccessState(error: failure, permissionDenied: name == "denied")
            windows = []; windowID = nil; preview = nil
            return
        }
'''
    path.write_text(source.replace(needle, needle + injection))
    path = Path('Sources/ContextLensApp/ScreenAccessDetails.swift')
    source = path.read_text().replace('@State private var showIdentity = false', '@State private var showIdentity = true')
    path.write_text(source)
    (out / 'synthetic-ui-limit.json').write_text(json.dumps(dict(syntheticErrors=True, humanConsentObserved=False,
        productionCodeUntouchedByNativePhase=True, noSecurityOrPrivacyApprovalsAutomated=True), indent=2))

def ui():
    # The helper only finds this exact disposable app. It cannot target a Settings window.
    app = temp / 'ui-unpacked/ContextLens.app'
    env = dict(os.environ, CONTEXTLENS_EXPECTED_APP=str(app))
    command(['swiftc', 'qa/ui.swift', '-o', temp / 'ui-helper'], 'compile-ui-helper')
    # Compile the capture helper once; it captures only the allowed app bundle's windows.
    command(['swiftc', 'qa/capture-windows.swift', '-o', temp / 'capture-helper'], 'compile-capture-helper')
    results = {}
    for state in ['unverified', 'denied', 'failed']:
        folder = out / ('synthetic-' + state); folder.mkdir()
        process = subprocess.Popen([str(app / 'Contents/MacOS/ContextLens'), '--isolated-native-test', '--capture-preview',
                                    '--qa-access-state', state, '-onboardingComplete', 'YES'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            time.sleep(4)
            tree = command([temp / 'ui-helper', 'tree'], state + '-ui-tree', check=False, env=env)
            capture = command([temp / 'capture-helper', folder, 'dev.contextlens.app'], state + '-capture', check=False, env=env)
            results[state] = dict(treeExit=tree.get('exitCode'), captureExit=capture.get('exitCode'), screenshots=len(list(folder.glob('*.png'))))
            if tree.get('exitCode') == 0:
                expected = {'unverified': 'access unverified', 'denied': 'access denied', 'failed': 'verification failed'}[state]
                assert expected in tree['stdout'], 'Distinct access state missing from native UI'
                assert 'Running copy:' in tree['stdout'], 'Running copy missing'
                assert 'Ad-hoc signature' in tree['stdout'], 'Real running-process signing details missing'
                assert 'Code hash:' in tree['stdout'], 'Code hash missing'
                if state != 'unverified': assert 'SyntheticCaptureService' in tree['stdout'] and '-999' in tree['stdout']
        finally:
            # Stop only the exact process created above; no app-ID or global kill.
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
    (out / 'synthetic-ui-results.json').write_text(json.dumps(results, indent=2))

{'native': native, 'inject-ui': inject_ui, 'ui': ui}[sys.argv[1]]()
