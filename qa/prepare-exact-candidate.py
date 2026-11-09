"""Verify and extract immutable official assets; never build or re-sign an app."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

assert os.environ.get('GITHUB_ACTIONS')=='true'
temp=Path(os.environ['RUNNER_TEMP']);folder=temp/'official-candidate';out=temp/'native-evidence';out.mkdir(exist_ok=True)
source='d0323bb84c08d5f42c29cae5635931bf2d825d98'
expected={
 'ContextLens-0.3.1-arm64.zip':'78692e2ec6997dbcdbfaf17021f43347aec5938eca8e29f25c22b79b11c94c70',
 'ContextLens-0.3.1-arm64.dmg':'32b3b53b0576a3fe8d2e8c3bf6700de9e0d6b5bdd4066c8657975229c920407c'}
for name,digest in expected.items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
spec=importlib.util.spec_from_file_location('official',Path.cwd()/'scripts/unnotarized-release.py')
sys.path.insert(0,str(Path.cwd()/'scripts'));official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
receipt=official.verify_assets(folder)
assert receipt['sourceCommit']==source and receipt['version']=='0.3.1' and receipt['build']==6
assert receipt['releaseInputs']['sha256']=='b82101587ee58ee3369720fcd621dc824f51c6aeab53add29e934f6a4843ecc2'
assert receipt['bundleInventorySHA256']=='ee4613c20e6d9b2eb4c476b860709f4e97f87e09bbed9259330fb9b88bb662ed'
assert not subprocess.check_output(['git','diff','--name-only',source,'HEAD','--','Sources','Package.swift','Brand','distribution','scripts','config','docs/screenshot-kit/demo-site'],text=True).strip()
subprocess.run(['ditto','-x','-k',str(folder/'ContextLens-0.3.1-arm64.zip'),str(temp/'unpacked')],check=True)
app=temp/'unpacked/ContextLens.app'
assert official.verify_bundle(app)['sourceCommit']==source
assert official.bundle_hash(app)==receipt['bundleInventorySHA256']
(out/'candidate-verified.json').write_text(json.dumps(dict(source=source,assetHashes=expected,bundleInventory=official.bundle_hash(app),officialPrepareRun=42601149595),indent=2))
print('Exact official candidate hashes, protected inputs, signatures and both containers verified. Original app extracted without modifications.')
