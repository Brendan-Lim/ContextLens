#!/usr/bin/env python3
import json
from pathlib import Path
from validate_package import validate
root=Path(__file__).resolve().parents[1]
packages=sorted(p for p in (root/'docs/examples').iterdir() if p.is_dir() and (p/'manifest.json').is_file())+sorted((root/'Benchmarks/reports/browser-evidence').glob('*/contextlens'))
try: import jsonschema
except ImportError: jsonschema=None
for folder in packages:
    validate(folder)
    if jsonschema:
        for file,schema in [('manifest.json','manifest'),('metadata/session.json','session')]:
            version = json.loads((folder/file).read_text()).get('schemaVersion')
            schema_name = 'manifest-v1' if schema == 'manifest' and version == 1 else schema
            jsonschema.Draft202012Validator(json.loads((root/'schemas'/(schema_name+'.schema.json')).read_text()),format_checker=jsonschema.FormatChecker()).validate(json.loads((folder/file).read_text()))
print('Validated',len(packages),'packages;', 'independent Draft 2020-12 validation included' if jsonschema else 'install jsonschema for independent schema cross-check')
