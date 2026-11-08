#!/usr/bin/env python3
"""Compare frozen/current exporters without model calls; preserve every existing evidence pixel and request."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_state import ROOT, source_state

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline-cli',type=Path,default=ROOT/'.build/contextlens-cli-before-lean')
p.add_argument('--output',type=Path,default=ROOT/'Benchmarks/reports/lean-handoff')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
cli=ROOT/'dist/contextlens-cli'
report={'kind':'deterministic-handoff-preservation','source':source_state(),
        'baseline_cli_sha256':hashlib.sha256(a.baseline_cli.read_bytes()).hexdigest(),
        'candidate_cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'fixtures':[],
        'scope':'Exact existing manifest, metadata and PNG-byte preservation. This is not agent quality, speed, token or allowance measurement.'}
with tempfile.TemporaryDirectory(prefix='contextlens-lean-preservation-') as temp:
    for fixture in sorted((ROOT/'Benchmarks/reports/browser-evidence').glob('*/source-session')):
        target=a.output/'packages'/fixture.parent.name
        target.mkdir(parents=True,exist_ok=True)
        # Dedicated output roots must not overwrite a previous export.
        old,new=target/'baseline',target/'lean'
        if old.exists() or new.exists():raise SystemExit('Evidence destination exists: choose a new --output')
        subprocess.run([str(a.baseline_cli),'export',str(fixture),str(old)],check=True,capture_output=True)
        subprocess.run([str(cli),'export',str(fixture),str(new)],check=True,capture_output=True)
        for metadata in ['manifest.json','metadata/session.json']:
            assert json.loads((old/metadata).read_text())==json.loads((new/metadata).read_text()),metadata
        preserved=[]
        for image in sorted(old.rglob('*.png')):
            relative=image.relative_to(old)
            assert image.read_bytes()==(new/relative).read_bytes(),str(relative)
            preserved.append(str(relative))
        source=json.loads((new/'metadata/session.json').read_text())
        brief=(new/'context.md').read_text();timeline=(new/'metadata/timeline.md').read_text()
        for mark in source['annotations']:
            if mark['kind']=='redaction':continue
            assert mark['id'] in brief
            assert mark['instruction'].replace('\n','\n> ') in brief
        for frame in source['frames']:assert f"frames/{frame['id']}.png" in timeline
        for line in brief.splitlines():
            if line.startswith('- ') and 'annotated/states/' in line:
                relative=line.rsplit(': ',1)[1]
                assert (new/relative).is_file(),relative
        for folder in [old,new]:
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_package.py'),str(folder)],check=True,capture_output=True)
        report['fixtures'].append({'task':fixture.parent.name,'status':'passed','preserved_existing_pngs':preserved,
            'baseline_required_text_bytes':sum((old/name).stat().st_size for name in ['context.md','manifest.json']),'baseline_context_bytes':(old/'context.md').stat().st_size,'lean_context_bytes':(new/'context.md').stat().st_size,
            'baseline_required_entry_reads':['context.md','manifest.json'],'lean_required_entry_reads':['context.md'],
            'overview_count':len(list((new/'annotated/states').glob('*.png'))),'explicit_instruction_count':sum(m['kind']!='redaction' for m in source['annotations'])})
report['status']='passed'
(a.output/'preservation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Preserved all legacy images/metadata/instructions in {len(report["fixtures"])} paired exports; no agents started.')
