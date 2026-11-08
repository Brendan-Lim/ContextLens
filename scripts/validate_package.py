#!/usr/bin/env python3
"""Validate the published schema subset and cross-file image/path invariants, offline."""
import json
import math
from pathlib import Path
import re
import struct
import sys
if not __debug__: raise RuntimeError("Validation requires assertions enabled; do not use Python -O.")

def schema_check(value, schema, at='$'):
    # All keywords emitted by make-schemas.py are checked; unsupported keywords fail closed.
    supported = {'$schema','title','type','properties','required','additionalProperties','items','enum','const','minimum','maximum','exclusiveMinimum','pattern','format'}
    assert not (set(schema)-supported), 'Unsupported schema keyword at '+at
    if 'const' in schema: assert value == schema['const'] and type(value) is type(schema['const']), 'Wrong constant '+at
    if 'enum' in schema: assert value in schema['enum'], 'Unknown enum '+at
    kind = schema.get('type')
    types = {'object':dict,'array':list,'string':str,'integer':int,'number':(int,float),'boolean':bool}
    if kind:
        assert isinstance(value,types[kind]) and not (kind in ('integer','number') and isinstance(value,bool)), 'Wrong type '+at
    if kind == 'object':
        assert set(schema['required']) <= set(value), 'Missing required fields '+at
        if schema.get('additionalProperties') is False: assert set(value) <= set(schema['properties']), 'Unknown fields '+at
        for k,v in value.items(): schema_check(v,schema['properties'][k],at+'.'+k)
    if kind == 'array':
        for i,v in enumerate(value): schema_check(v,schema['items'],at+'[%d]'%i)
    if kind in ('integer','number'):
        assert math.isfinite(value), 'Non-finite number '+at
        for key,comparison in [('minimum',lambda a,b:a>=b),('maximum',lambda a,b:a<=b),('exclusiveMinimum',lambda a,b:a>b)]:
            if key in schema: assert comparison(value,schema[key]), 'Out of range '+at
    if 'pattern' in schema: assert re.search(schema['pattern'],value), 'Invalid string '+at
    if schema.get('format') == 'date-time':
        from datetime import datetime
        assert datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo, 'Missing timezone '+at

def safe_path(root, path):
    assert path and not path.startswith('/') and '\\' not in path and ':' not in path
    assert all(p not in ('','.','..') for p in path.split('/')), 'Unsafe path'
    target = (root/path).resolve()
    assert root.resolve() in target.parents and target.is_file(), 'Missing or escaping file '+path
    return target

def png_size(path):
    b = path.read_bytes()[:24]
    assert b[:8] == b'\x89PNG\r\n\x1a\n', 'Expected PNG '+str(path)
    return struct.unpack('>II',b[16:24])

def validate(root):
    schemas = Path(__file__).resolve().parents[1]/'schemas'
    m = json.loads((root/'manifest.json').read_text())
    manifest_schema = 'manifest-v1.schema.json' if m.get('schemaVersion') == 1 else 'manifest.schema.json'
    schema_check(m,json.loads((schemas/manifest_schema).read_text()))
    s = json.loads((root/'metadata/session.json').read_text()); schema_check(s,json.loads((schemas/'session.schema.json').read_text()))
    assert m['sessionID'] == s['id'] and m['frames'] == s['frames'] and m['mode'] == s['mode']
    frames = {f['id']:f for f in m['frames']}; assert len(frames) == len(m['frames']) and frames
    for f in frames.values(): assert png_size(safe_path(root,f['imagePath'])) == (f['width'],f['height'])
    annotations = {a['id']:a for a in s['annotations']}; assert len(annotations) == len(s['annotations'])
    for a in annotations.values():
        assert a['frameID'] in frames; r=a['region']; assert r['x']+r['width'] <= 1.0000001 and r['y']+r['height'] <= 1.0000001
    ids = set()
    for issue in m['issues']:
        a = issue['annotation']; assert a['id'] not in ids; ids.add(a['id'])
        assert a['kind'] != 'redaction'
        assert a == {k:v for k,v in annotations[a['id']].items() if k in a}
        frame=frames[a['frameID']]
        assert png_size(safe_path(root,issue['annotatedPath'])) == (frame['width'],frame['height'])
        width,height=png_size(safe_path(root,issue['cropPath'])); assert 0 < width <= frame['width'] and 0 < height <= frame['height']
    assert ids == {a['id'] for a in annotations.values() if a['kind'] != 'redaction'}
    assert s['nextIssueNumber'] > max([int(a[3:]) for a in annotations if a.startswith('CL-')] or [0])
    assert m.get('task') == s.get('task')
    if m['schemaVersion'] == 2:
        summary = m['summary']
        assert summary['includedFrames'] == len(frames) and summary['includedAnnotations'] == len(ids)
        assert summary['selectedFrames'] == len(frames) + summary['excludedUnannotated'] + summary['excludedDuplicates']
        assert summary['unlabelledAnnotations'] == sum(not a['instruction'].strip() for a in annotations.values() if a['kind'] != 'redaction')
        if m['exportOptions']['annotatedOnly']: assert set(frames) <= {a['frameID'] for a in annotations.values()}
    for p in ['README.md','context.md']: safe_path(root,p)
    return {'frames':len(frames),'issues':len(ids),'status':'valid'}
if __name__ == '__main__':
    try: print(json.dumps(validate(Path(sys.argv[1]))))
    except (AssertionError,ValueError,KeyError,IndexError,OSError) as e: print('Invalid package: '+str(e),file=sys.stderr); sys.exit(1)
