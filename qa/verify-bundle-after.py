import importlib.util
import json
import os
from pathlib import Path
import sys

assert os.environ.get('GITHUB_ACTIONS')=='true'
temp=Path(os.environ['RUNNER_TEMP']);out=temp/'native-evidence'
sys.path.insert(0,str(Path.cwd()/'scripts'))
spec=importlib.util.spec_from_file_location('official',Path.cwd()/'scripts/unnotarized-release.py')
official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
app=temp/'unpacked/ContextLens.app'
expected='ee4613c20e6d9b2eb4c476b860709f4e97f87e09bbed9259330fb9b88bb662ed'
verified=official.verify_bundle(app);unchanged=official.bundle_hash(app)==expected
(out/'bundle-after.json').write_text(json.dumps(dict(unchanged=unchanged,sourceCommit=verified['sourceCommit']),indent=2))
assert unchanged,'Native testing changed the original app bundle'
