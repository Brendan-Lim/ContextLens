import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
strip = load('strip_png_metadata', 'strip-png-metadata.py')
audit = load('audit_public_files', 'audit-public-files.py')


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))


def png(*extra):
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(b'\x00' + b'\x10\x20\x30\xff' * 2))
    return b'\x89PNG\r\n\x1a\n' + ihdr + b''.join(extra) + idat + chunk(b'IEND', b'')


class StripPNGMetadataTests(unittest.TestCase):
    def test_screenshot_metadata_is_removed_and_pixels_kept(self):
        # What macOS screenshots add: XMP (iTXt), Apple's iDOT, a timestamp and EXIF.
        source = png(chunk(b'sRGB', b'\x00'), chunk(b'pHYs', struct.pack('>IIB', 5669, 5669, 1)),
                     chunk(b'iTXt', b'XML:com.adobe.xmp\x00\x00\x00\x00\x00<x:xmpmeta>Screenshot</x:xmpmeta>'),
                     chunk(b'iDOT', b'\x00' * 28), chunk(b'tIME', b'\x07\xea\x0b\x09\x01\x02\x03'),
                     chunk(b'eXIf', b'MM\x00*'))
        self.assertIsNotNone(audit.png_issue(source))
        cleaned, removed = strip.strip(source)
        self.assertEqual(removed, ['iTXt', 'iDOT', 'tIME', 'eXIf'])
        self.assertIsNone(audit.png_issue(cleaned))
        self.assertEqual([k for k, _ in strip.chunks(cleaned)], [b'IHDR', b'sRGB', b'pHYs', b'IDAT', b'IEND'])
        self.assertEqual([p for k, p in strip.chunks(cleaned) if k == b'IDAT'],
                         [p for k, p in strip.chunks(source) if k == b'IDAT'])

    def test_rejects_non_png_and_corrupt_chunks(self):
        with self.assertRaises(ValueError): strip.strip(b'GIF89a')
        broken = bytearray(png()); broken[-5] ^= 1
        with self.assertRaises(ValueError): strip.strip(bytes(broken))

    def test_cli_writes_a_new_file_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, 'in.png'), Path(tmp, 'out.png')
            src.write_bytes(png(chunk(b'tEXt', b'Software\x00Screenshot')))
            self.assertEqual(strip.main([str(src), str(dst)]), 0)
            self.assertIsNone(audit.png_issue(dst.read_bytes()))
            self.assertEqual(strip.main([str(src), str(dst)]), 2)
            self.assertEqual(strip.main([str(src), str(src)]), 2)


if __name__ == '__main__':
    unittest.main()
