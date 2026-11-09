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
source='b4453baa79ffe7280ae8af04da13a99ab4b29656'
expected={
 'ContextLens-0.3.1-arm64.zip':'9178e8d2eb2ec273a1222103d757087f68f0d92e8f50cfde6e0a633fc4bd0e9b',
 'ContextLens-0.3.1-arm64.dmg':'e8e7d63c5d604a14f24cffe9596f32fbdcc6eb5d9f4cddfe0643316e039c7cc2'}
for name,digest in expected.items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
spec=importlib.util.spec_from_file_location('official',Path.cwd()/'scripts/unnotarized-release.py')
sys.path.insert(0,str(Path.cwd()/'scripts'));official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
receipt=official.verify_assets(folder)
assert receipt['sourceCommit']==source and receipt['version']=='0.3.1' and receipt['build']==6
assert receipt['releaseInputs']['sha256']=='fbf71d64f4011677bb684f99678801832587631443ba639068f5f3bbd4093db5'
assert receipt['bundleInventorySHA256']=='1f2e93d90c3d7761a4ad85ff14fc6c102d9f13d6d599694749e739c53b8fd296'
assert not subprocess.check_output(['git','diff','--name-only',source,'HEAD','--','Sources','Package.swift','Brand','distribution','scripts','config','docs/screenshot-kit/demo-site'],text=True).strip()
subprocess.run(['ditto','-x','-k',str(folder/'ContextLens-0.3.1-arm64.zip'),str(temp/'unpacked')],check=True)
app=temp/'unpacked/ContextLens.app'
assert official.verify_bundle(app)['sourceCommit']==source
assert official.bundle_hash(app)==receipt['bundleInventorySHA256']
(out/'candidate-verified.json').write_text(json.dumps(dict(source=source,assetHashes=expected,bundleInventory=official.bundle_hash(app),officialPrepareRun=42614894584),indent=2))
print('Exact official candidate hashes, protected inputs, signatures and both containers verified. Original app extracted without modifications.')
