"""Normal installed launch before/after real onboarding. No privacy/security approval actions."""
import json
import os
from pathlib import Path
import subprocess
import time

assert os.environ.get('GITHUB_ACTIONS') == 'true'
temp = Path(os.environ['RUNNER_TEMP']); out = temp/'native-evidence'; out.mkdir(exist_ok=True)
source = temp/'unpacked/ContextLens.app'; installed = Path('/Applications/ContextLens.app')
assert not installed.exists(), 'Never replace an existing installation'
subprocess.run(['ditto', source, installed], check=True)
helper = temp/'installed-helper'
subprocess.run(['swiftc', 'qa/inspect-installed.swift', '-o', helper], check=True)
def command(args, name, timeout=30):
    try:
        p = subprocess.run(list(map(str,args)), capture_output=True, text=True, timeout=timeout)
        r = dict(exitCode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired: r = dict(status='timeout')
    (out/(name+'.json')).write_text(json.dumps(r,indent=2)); return r
def observe(name):
    result=command([helper], name)
    value=json.loads(result.get('stdout','{}'))
    folder=out/name;folder.mkdir()
    command(['swift','qa/capture-windows.swift',folder,'dev.contextlens.app'],name+'-images')
    if value.get('runningInstalledCopy') and value.get('windowCount',0)==0:
        command(['sample',value['pid'],'3','-file',out/(name+'.sample.txt')],name+'-sample')
    return value
results={}
try:
    command(['open','-n',installed], 'normal-fresh-open');time.sleep(5)
    results['normalFresh']=observe('normal-fresh')
    command([helper,'--finish-onboarding'],'finish-onboarding');time.sleep(2)
    command(['defaults','read','dev.contextlens.app','onboardingComplete'],'persisted-onboarding')
    command([helper,'--terminate'],'first-quit');time.sleep(4)
    command(['open','-n',installed],'normal-onboarded-open');time.sleep(5)
    results['normalOnboarded']=observe('normal-onboarded')
    command([helper,'--terminate'],'second-quit');time.sleep(4)
    command(['open','-n',installed,'--args','--isolated-native-test','-onboardingComplete','YES'],'with-fixture-arguments-open');time.sleep(5)
    results['withFixtureArguments']=observe('with-fixture-arguments')
    command([helper,'--terminate'],'third-quit');time.sleep(4)
    command(['open','-n',installed],'normal-repeat-open');time.sleep(5)
    results['normalRepeat']=observe('normal-repeat')
finally:
    command([helper,'--terminate'],'cleanup')
    (out/'launch-comparison.json').write_text(json.dumps(dict(results=results,noSecurityOrPrivacyApprovals=True,maintainerAcceptance=False),indent=2))
