import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'distribution/dmg'))
from dmg import inventory, mounted, build


class DiskImageSafetyTests(unittest.TestCase):
    def test_failed_verification_detaches_only_its_private_mount(self):
        calls = []
        def execute(*args):
            calls.append(args)
            return ''
        with patch('dmg.run', side_effect=execute), patch('dmg.os.path.ismount', return_value=True):
            with self.assertRaisesRegex(ValueError, 'verify failed'):
                with mounted('/tmp/synthetic.dmg'):
                    raise ValueError('verify failed')
        self.assertEqual(calls[-1][0:2], ('hdiutil', 'detach'))
        self.assertEqual(str(calls[-1][2]), str(calls[0][-2]))
        self.assertTrue(str(calls[-1][2]).startswith(('/private/tmp/contextlens-mount-', '/tmp/contextlens-mount-')))

    def test_inventory_detects_changed_content_mode_and_escaping_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            binary = app / 'binary'; binary.write_bytes(b'original'); binary.chmod(0o644)
            first = inventory(app)
            binary.write_bytes(b'changed')
            self.assertNotEqual(inventory(app), first)
            first = inventory(app); binary.chmod(0o755)
            self.assertNotEqual(inventory(app), first)
            (app / 'escape').symlink_to('/Applications')
            with self.assertRaisesRegex(ValueError, 'symlink'): inventory(app)

    def test_existing_image_is_not_touched_even_before_app_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'published.dmg'; target.write_bytes(b'immutable')
            with patch('dmg.verify') as verify:
                with self.assertRaisesRegex(ValueError, 'replacement'): build('ContextLens.app', target)
                verify.assert_not_called()
            self.assertEqual(target.read_bytes(), b'immutable')


if __name__ == '__main__': unittest.main()
