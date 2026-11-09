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
expected='1f2e93d90c3d7761a4ad85ff14fc6c102d9f13d6d599694749e739c53b8fd296'
verified=official.verify_bundle(app);unchanged=official.bundle_hash(app)==expected
(out/'bundle-after.json').write_text(json.dumps(dict(unchanged=unchanged,sourceCommit=verified['sourceCommit']),indent=2))
assert unchanged,'Native testing changed the original app bundle'
