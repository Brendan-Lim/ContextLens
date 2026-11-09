"""Synthetic export round trips through the actual CLI; no GUI, capture or model calls."""
import importlib.util
import json
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
CLI = Path(os.environ.get('CONTEXTLENS_TEST_CLI', str(ROOT / 'dist/contextlens-cli')))
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_package import validate


def png(width, height, raw=None):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    pixels = (b'\0' + b'\xff\0\0\xff' * width) * height if raw is None else raw
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


def decode(path):
    """Independent top-left pixel reader for the native export's 8-bit RGB(A) PNGs."""
    data = path.read_bytes(); offset = 8; compressed = bytearray()
    while offset < len(data):
        size, kind = struct.unpack('>I4s', data[offset:offset + 8]); block = data[offset + 8:offset + 8 + size]
        if kind == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', block)
            assert depth == 8 and color in (2, 6) and interlace == 0
            channels = 3 if color == 2 else 4
        if kind == b'IDAT': compressed.extend(block)
        offset += size + 12
    raw = zlib.decompress(compressed); stride = width * channels; pixels = bytearray(stride * height)
    def paeth(a, b, c):
        p = a + b - c; distances = (abs(p - a), abs(p - b), abs(p - c))
        return (a, b, c)[distances.index(min(distances))]
    for y in range(height):
        filtering = raw[y * (stride + 1)]
        for x in range(stride):
            left = pixels[y * stride + x - channels] if x >= channels else 0
            up = pixels[(y - 1) * stride + x] if y else 0
            corner = pixels[(y - 1) * stride + x - channels] if y and x >= channels else 0
            predictor = (0, left, up, (left + up) // 2, paeth(left, up, corner))[filtering]
            pixels[y * stride + x] = (raw[y * (stride + 1) + 1 + x] + predictor) & 255
    def at(x, y): return tuple(pixels[(y * width + x) * channels:(y * width + x) * channels + 3])
    return width, height, at


@unittest.skipUnless(CLI.is_file(), 'Build the native CLI first; never substitute a different checkout binary')
class HandoffCLITests(unittest.TestCase):
    def run_cli(self, *arguments, success=True):
        result = subprocess.run([str(CLI), *map(str, arguments)], capture_output=True, text=True, timeout=60)
        if success: self.assertEqual(result.returncode, 0, result.stderr)
        else: self.assertNotEqual(result.returncode, 0)
        return result

    def test_real_cli_exports_redacted_retina_reordered_unicode_session_and_retries(self):
        with tempfile.TemporaryDirectory(prefix='contextlens-cli-handoff-') as directory:
            source = Path(directory) / 'Project space 画面'
            self.run_cli('demo', source)
            session = json.loads((source / 'session.json').read_text())
            dimensions = [(128, 80), (256, 160), (180, 120)]
            for index, (frame, size) in enumerate(zip(session['frames'], dimensions), 1):
                frame.update(width=size[0], height=size[1], displayScale=2 if index == 2 else 1,
                             name='Renamed 画面 '+str(index), selected=index != 3,
                             imagePath=f'frames/entrée 画面 {index}.png')
                (source / frame['imagePath']).write_bytes(png(*size))
            def mark(number, index, kind, region, instruction='', points=None):
                return dict(id=f'CL-{number:03}', frameID=session['frames'][index]['id'], kind=kind,
                            region=dict(zip(['x', 'y', 'width', 'height'], region)), instruction=instruction,
                            points=points or [], severity='normal')
            session['annotations'] = [
                mark(1, 0, 'rectangle', (.2, .2, .2, .2), 'Align this button.\rKeep the note quoted.'),
                mark(2, 0, 'redaction', (.4, .4, .2, .2), 'Synthetic redaction note must stay local'),
                mark(5, 1, 'highlight', (.17, .16, .56, .58), 'Align this L-shaped region 画面',
                     [dict(x=.2, y=.2), dict(x=.2, y=.7), dict(x=.7, y=.7)]),
                mark(7, 2, 'rectangle', (.2, .2, .2, .2), 'Deselected note must stay local')]
            session['nextIssueNumber'] = 8
            session['frames'] = [session['frames'][1], session['frames'][0], session['frames'][2]]
            (source / 'session.json').write_text(json.dumps(session, ensure_ascii=False, indent=2))
            original = (source / 'session.json').read_bytes()
            self.run_cli('validate', source)

            first, second = Path(directory) / 'Hand off 画面', Path(directory) / 'Second hand off'
            self.run_cli('export', source, first)
            self.run_cli('export', source, second)
            self.assertEqual(validate(first), dict(frames=2, issues=2, status='valid'))
            self.assertEqual(validate(second), dict(frames=2, issues=2, status='valid'))
            def files(folder): return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            first_bytes = files(first)
            self.assertEqual(first_bytes, files(second))
            self.run_cli('export', source, first, success=False)
            self.assertEqual(files(first), first_bytes)
            manifest = json.loads(first_bytes['manifest.json'])
            self.assertEqual([f['id'] for f in manifest['frames']], ['frame-002', 'frame-001'])
            self.assertEqual([i['annotation']['id'] for i in manifest['issues']], ['CL-005', 'CL-001'])
            metadata = json.loads(first_bytes['metadata/session.json'])
            self.assertEqual(metadata['nextIssueNumber'], 8)
            self.assertEqual(next(a for a in metadata['annotations'] if a['kind'] == 'redaction')['instruction'], '')
            for name in ['context.md', 'manifest.json', 'metadata/session.json']:
                text = first_bytes[name].decode()
                self.assertNotIn('Synthetic redaction note', text); self.assertNotIn('Deselected note', text)
                self.assertNotIn(str(source), text)
            self.assertIn('> Align this button.\n> Keep the note quoted.', first_bytes['context.md'].decode())
            for path in ['frames/frame-001.png', 'annotated/CL-001.png', 'annotated/states/frame-001.png']:
                width, height, at = decode(first / path)
                self.assertEqual((width, height), (128, 80)); self.assertEqual(at(65, 40), (0, 0, 0))
            self.assertEqual(decode(first / 'crops/CL-001.png')[2](64, 40), (0, 0, 0))
            self.assertNotEqual(decode(source / 'frames/entrée 画面 1.png')[2](65, 40), (0, 0, 0))
            self.assertGreater(decode(first / 'annotated/CL-001.png')[2](26, 25)[1], 20)
            width, height, at = decode(first / 'annotated/CL-005.png')
            self.assertEqual((width, height), (256, 160)); self.assertGreater(at(51, 72)[1], at(115, 72)[1] + 20)
            self.assertEqual(decode(first / 'crops/CL-005.png')[:2], (189, 140))
            if importlib.util.find_spec('jsonschema'):
                import jsonschema
                for value, schema in [(manifest, 'manifest'), (metadata, 'session')]:
                    jsonschema.Draft202012Validator(json.loads((ROOT / f'schemas/{schema}.schema.json').read_text()),
                                                   format_checker=jsonschema.FormatChecker()).validate(value)
            self.assertEqual((source / 'session.json').read_bytes(), original)
            self.run_cli('validate', source)

    def test_incomplete_image_stream_is_not_exported_as_a_success(self):
        with tempfile.TemporaryDirectory(prefix='contextlens-incomplete-image-') as directory:
            source, destination = Path(directory) / 'session', Path(directory) / 'handoff'
            self.run_cli('demo', source)
            session = json.loads((source / 'session.json').read_text())
            frame = session['frames'][2]
            # Complete PNG framing and CRCs, but only one row for a 600-row image.
            image = png(frame['width'], frame['height'], raw=b'\0' + b'\xff\0\0\xff' * frame['width'])
            (source / frame['imagePath']).write_bytes(image)
            self.run_cli('export', source, destination, success=False)
            self.assertFalse(destination.exists())
            self.assertFalse(list(Path(directory).glob('.contextlens-*')))
