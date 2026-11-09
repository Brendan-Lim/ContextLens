"""Fresh guest, genuine browser download, read-only trust observation. Never approves a warning."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PurePosixPath
import plistlib
import subprocess
import time
import zipfile

temp=Path(os.environ['RUNNER_TEMP']);out=temp/'native-evidence';out.mkdir(exist_ok=True)
def command(args,name,timeout=60):
    try:
        p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
        result=dict(exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired:result=dict(status='timeout')
    (out/(name+'.json')).write_text(json.dumps(result,indent=2));return result
def wait_file(find):
    end=time.time()+25
    while time.time()<end:
        files=list(find())
        if files:return files[0]
        time.sleep(.4)
    return None
def safe_zip(path,app=False):
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            name=PurePosixPath(item.filename)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename
            assert (item.external_attr>>16)&0o170000 !=0o120000
            if app:assert name.parts[0] in ['ContextLens.app','__MACOSX']
        assert archive.testzip() is None
summary=dict(kind='fresh-browser-download-policy-observation',maintainerApproval=False,noSecurityApprovalsAutomated=True,noTCCChanges=True,cases={})
try:
    command(['sw_vers'],'macos')
    assert command(['node','qa/trust-download.cjs'],'browser-download')['exitCode']==0
    receipt=json.loads((out/'genuine-browser-download.json').read_text())
    assert receipt.get('apiDigestMatched',True),'Authenticated artifact digest mismatch'
    if not receipt['savedQuarantine']['present']:
        summary['cases']['gatekeeper-first-launch']=dict(status='pending',observation='Actual Chromium download completed without quarantine metadata; no metadata fabricated and no first-launch claim.')
    else:
        archive=Path(receipt['localFile']);safe_zip(archive)
        command(['open',archive],'archive-utility-outer')
        candidate_zip=wait_file(lambda:archive.parent.rglob('ContextLens-0.3.1-arm64.zip'))
        assert candidate_zip,'Archive Utility did not extract exact candidate ZIP'
        assert hashlib.sha256(candidate_zip.read_bytes()).hexdigest()=='f4ac0a2cc3dc5fd6f120a21e3f7152f86351b7f8bf93e3908f57bc5a9ad3425e'
        dmg=candidate_zip.with_suffix('.dmg');assert hashlib.sha256(dmg.read_bytes()).hexdigest()=='52872a5e0221fac2960fb8d5c349743201bbb5800a914eb77b1b48416473b37d'
        safe_zip(candidate_zip,True);command(['open',candidate_zip],'archive-utility-candidate')
        info=wait_file(lambda:candidate_zip.parent.rglob('ContextLens.app/Contents/Info.plist'))
        assert info,'Archive Utility did not extract application'
        app=info.parents[1];metadata=plistlib.loads(info.read_bytes())
        assert (metadata['CFBundleShortVersionString'],metadata['CFBundleVersion'],metadata['CFBundleIdentifier'])==('0.3.1','6','dev.contextlens.app')
        assert command(['codesign','--verify','--deep','--strict',app],'strict-signature')['exitCode']==0
        spec=importlib.util.spec_from_file_location('official','scripts/unnotarized-release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        inventory=module.bundle_hash(app);assert inventory=='9e689eba51491066164b315dd2ac94d525154d4d7c8dadd1ea5124ed5775e1db'
        attribute=command(['xattr','-p','com.apple.quarantine',app],'genuine-app-quarantine')
        summary['bundleInventorySHA256']=inventory;summary['appQuarantinePresent']=attribute.get('exitCode')==0
        if attribute.get('exitCode')!=0:
            summary['cases']['gatekeeper-first-launch']=dict(status='pending',observation='Browser container genuinely quarantined, but Archive Utility app inheritance not present; no first-launch pass claimed.')
        else:
            # This is the first candidate code launch in this fresh job. No CLI help execution preceded it.
            command(['open','-n',app],'genuine-quarantined-launch');time.sleep(4)
            observation=command(['swift','qa/security-observation.swift'],'actual-security-ui')
            windows=out/'security-originals';windows.mkdir()
            command(['swift','qa/capture-windows.swift',windows,'com.apple.CoreServicesUIAgent','com.apple.SecurityAgent','dev.contextlens.app'],'security-window-captures')
            raw=observation.get('stdout','').lower()
            warning=any(text in raw for text in ['could not verify','cannot verify','unidentified developer','couldn’t be opened','cannot be opened'])
            summary['cases']['gatekeeper-first-launch']=dict(status='pass' if warning else 'pending',observation='Genuine quarantined app opened normally; security UI retained without clicking any approval.',warningObserved=warning)
except Exception as error:summary['error']=str(error)
summary['cases']['open-anyway']=dict(status='pending',observation='Human trust authorization was not automated. No Open Anyway/Open confirmation approved.')
(out/'trust-case-results.json').write_text(json.dumps(summary,indent=2))
