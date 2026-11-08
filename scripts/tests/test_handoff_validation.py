import importlib.util
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('package_validator', ROOT / 'scripts/validate_package.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class HandoffValidationTests(unittest.TestCase):
    def package(self, directory):
        root = Path(directory) / 'Hand off 画面'
        shutil.copytree(ROOT / 'docs/examples/agent-session-v2', root)
        return root

    def test_png_header_alone_is_not_a_valid_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            path = root / 'frames/frame-003.png'
            path.write_bytes(path.read_bytes()[:24])
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)

    def test_changed_png_data_crc_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            path = root / 'frames/frame-003.png'
            contents = bytearray(path.read_bytes()); contents[-16] ^= 1
            path.write_bytes(contents)
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)

    def test_context_cannot_reference_a_missing_state_overview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            (root / 'context.md').write_text('# ContextLens feedback\n\n## Visual evidence\n\n- Confirmation [frame-003]: annotated/states/frame-003.png\n')
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)

    def test_redaction_notes_cannot_survive_in_exported_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            path = root / 'metadata/session.json'
            session = json.loads(path.read_text())
            mark = next(a for a in session['annotations'] if a['kind'] == 'redaction')
            mark['instruction'] = 'Synthetic private redaction note'
            path.write_text(json.dumps(session))
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)

    @staticmethod
    def png(width=2, height=2, color=6, depth=8, interlace=0, raw=None):
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        header = struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, interlace)
        if raw is None: raw = (b'\0' + b'\xff\0\0\xff' * width) * height
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

    def test_scanline_corruption_with_valid_chunk_crcs_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.png'
            for raw in [b'', b'\0' + b'\xff' * 8, (b'\5' + b'\xff' * 8) * 2,
                        (b'\0' + b'\xff' * 8) * 3]:
                with self.subTest(raw_length=len(raw)):
                    path.write_bytes(self.png(raw=raw))
                    with self.assertRaises((AssertionError, ValueError)): validator.png_size(path)

    def test_supported_bit_depths_interlace_and_large_streaming_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.png'
            for kwargs, expected in [({}, (2, 2)),
                                     (dict(color=0, depth=1, raw=b'\0\x80\0\x40'), (2, 2)),
                                     (dict(width=1, height=1, depth=16, interlace=1, raw=b'\0' + b'\xff' * 8), (1, 1)),
                                     (dict(width=8, height=8, interlace=1,
                                           raw=b''.join(b'\0' + b'\xff\0\0\xff' * n for n in [1,1,2,2,2,4,4,4,4,4,4,8,8,8,8])), (8, 8)),
                                     (dict(width=20000, height=2), (20000, 2))]:
                with self.subTest(kwargs=kwargs):
                    path.write_bytes(self.png(**kwargs))
                    self.assertEqual(validator.png_size(path), expected)

    def test_legacy_v1_and_v2_packages_remain_valid(self):
        for name in ['agent-session', 'agent-session-v2']:
            self.assertEqual(validator.validate(ROOT / 'docs/examples' / name)['status'], 'valid')

    def test_manifest_path_traversal_and_escaping_output_symlinks_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            frame = root / 'frames/frame-003.png'
            outside = Path(directory) / 'outside.png'; outside.write_bytes(frame.read_bytes())
            frame.unlink(); frame.symlink_to(outside)
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)
        with tempfile.TemporaryDirectory() as directory:
            root = self.package(directory)
            path = root / 'manifest.json'; manifest = json.loads(path.read_text())
            manifest['issues'][0]['cropPath'] = '../outside.png'; path.write_text(json.dumps(manifest))
            with self.assertRaises((AssertionError, ValueError)): validator.validate(root)
