#!/usr/bin/env python3
"""Validate the published schema subset and cross-file image/path invariants, offline."""
import json
import math
from pathlib import Path
import re
import struct
import sys
import zlib
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
    """Check CRCs, complete DEFLATE scanlines and PNG structure with bounded buffers.

    Covers grayscale/palette/RGB/alpha, all PNG bit depths and Adam7. It is a
    structural validator, not an image renderer or a redaction pixel auditor.
    """
    def rows(width, height, depth, channels, interlaced):
        passes = [(0, 0, 1, 1)] if not interlaced else [
            (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
            (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
        for x, y, dx, dy in passes:
            w, h = max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy)
            if w:
                for _ in range(h): yield (w * depth * channels + 7) // 8

    with path.open('rb') as stream:
        assert stream.read(8) == b'\x89PNG\r\n\x1a\n', 'Expected PNG '+str(path)
        width = height = color = None
        palette = idat = idat_ended = False
        decoder = zlib.decompressobj()
        row_lengths = iter(())
        row_width = remaining = None

        def pixels(block):
            nonlocal row_width, remaining
            pending = block
            while True:
                try: decoded = decoder.decompress(pending, 65536)
                except zlib.error as error: raise ValueError('Invalid PNG compressed stream') from error
                assert not decoder.unused_data, 'Extra PNG compressed stream'
                offset = 0
                while offset < len(decoded):
                    assert row_width is not None, 'Extra PNG scanline data'
                    if remaining == row_width + 1:
                        assert decoded[offset] <= 4, 'Invalid PNG scanline filter'
                    count = min(remaining, len(decoded) - offset)
                    offset += count; remaining -= count
                    if remaining == 0:
                        row_width = next(row_lengths, None)
                        remaining = None if row_width is None else row_width + 1
                pending = decoder.unconsumed_tail
                if not pending and len(decoded) < 65536: break

        while True:
            header = stream.read(8)
            assert len(header) == 8, 'Truncated PNG chunk'
            size, kind = struct.unpack('>I4s', header)
            assert size <= 0x7fffffff and all(65 <= c <= 90 or 97 <= c <= 122 for c in kind), 'Invalid PNG chunk'
            assert width is not None or kind == b'IHDR', 'PNG must begin with IHDR'
            assert kind in (b'IHDR', b'PLTE', b'IDAT', b'IEND') or kind[0] & 32, 'Unknown critical PNG chunk'
            if kind == b'IHDR': assert width is None and size == 13, 'Invalid PNG header'
            if kind == b'PLTE':
                assert not palette and not idat and 0 < size <= 768 and size % 3 == 0 and color not in (0, 4), 'Invalid PNG palette'
                palette = True
            if kind == b'IDAT':
                assert not idat_ended and (color != 3 or palette), 'Invalid PNG image data order'
                idat = True
            elif idat: idat_ended = True
            if kind == b'IEND': assert size == 0 and idat, 'Invalid PNG end'
            checksum = zlib.crc32(kind)
            left = size
            while left:
                block = stream.read(min(left, 65536))
                assert block, 'Truncated PNG data'
                left -= len(block); checksum = zlib.crc32(block, checksum)
                if kind == b'IHDR':
                    assert len(block) == 13, 'Truncated PNG header'
                    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', block)
                    depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
                    assert 0 < width <= 32768 and 0 < height <= 32768, 'Invalid PNG dimensions'
                    assert color in depths and depth in depths[color] and compression == filtering == 0 and interlace in (0, 1), 'Unsupported PNG header'
                    row_lengths = iter(rows(width, height, depth, {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color], interlace))
                    row_width = next(row_lengths, None); remaining = row_width + 1
                elif kind == b'IDAT': pixels(block)
            crc = stream.read(4)
            assert len(crc) == 4 and struct.unpack('>I', crc)[0] == checksum, 'PNG CRC mismatch'
            if kind == b'IEND':
                assert decoder.eof and row_width is None, 'Incomplete PNG image data'
                assert not stream.read(1), 'Trailing PNG data'
                return width, height

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
        if a['kind'] == 'redaction': assert a['instruction'] == '', 'Redaction note must not be exported'
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
    brief = (root/'context.md').read_text()
    if brief.startswith('# ContextLens feedback\n'):
        # Earlier v1/v2 packages predate state overviews and the separate timeline.
        # The current brief explicitly promises both, so validate those promises.
        marked = {a['frameID'] for a in annotations.values() if a['kind'] != 'redaction'}
        initial = [f for f in m['frames'] if f['id'] in marked] if marked else m['frames'][:3]
        assert '\n## Visual evidence\n' in brief, 'Missing visual evidence section'
        evidence = brief.split('\n## Visual evidence\n', 1)[1].split('\nMore context, only if needed:', 1)[0]
        links = re.findall(r'\[([A-Za-z0-9_-]+)\]: ([^\r\n]+\.png)(?=\r?\n|$)', evidence)
        expected = [(f['id'], 'annotated/states/'+f['id']+'.png' if f['id'] in marked else f['imagePath']) for f in initial]
        assert links == expected, 'Brief image references disagree with manifest'
        for frame_id, path in links:
            assert png_size(safe_path(root,path)) == (frames[frame_id]['width'],frames[frame_id]['height'])
        timeline = safe_path(root,'metadata/timeline.md').read_text()
        for f in m['frames']:
            assert 'Frame: '+f['imagePath'] in timeline, 'Timeline is missing a frame reference'
    return {'frames':len(frames),'issues':len(ids),'status':'valid'}
if __name__ == '__main__':
    try: print(json.dumps(validate(Path(sys.argv[1]))))
    except (AssertionError,ValueError,KeyError,IndexError,OSError) as e: print('Invalid package: '+str(e),file=sys.stderr); sys.exit(1)
