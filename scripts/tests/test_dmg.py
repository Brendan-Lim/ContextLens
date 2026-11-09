import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'distribution/dmg'))
from dmg import inventory, mounted, build, configure, verify_layout


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

    def test_forced_cleanup_is_not_reported_as_a_clean_detach(self):
        calls = []
        def execute(*args):
            calls.append(args)
            if args[:2] == ('hdiutil', 'detach') and '-force' not in args:
                raise subprocess.CalledProcessError(1, args)
            return ''
        with patch('dmg.run', side_effect=execute), patch('dmg.os.path.ismount', return_value=True):
            with self.assertRaises(subprocess.CalledProcessError):
                with mounted('/tmp/synthetic.dmg'):
                    pass
        self.assertEqual(calls[-1][:3], ('hdiutil', 'detach', '-force'))
        self.assertEqual(calls[-1][-1], calls[-2][-1])

    def test_existing_image_is_not_touched_even_before_app_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'published.dmg'; target.write_bytes(b'immutable')
            with patch('dmg.verify') as verify:
                with self.assertRaisesRegex(ValueError, 'replacement'): build('ContextLens.app', target)
                verify.assert_not_called()
            self.assertEqual(target.read_bytes(), b'immutable')


class FinderIconSettingsTests(unittest.TestCase):
    """Finder rejects picture settings without its fallback RGB color components."""
    def setUp(self):
        from unittest.mock import MagicMock
        self.records = {'.': {}, 'ContextLens.app': {}, 'Applications': {}}
        store = MagicMock()
        store.__enter__.return_value = self.records
        alias = SimpleNamespace(target=SimpleNamespace(posix_path='/.background/background.tiff'),
                                volume=SimpleNamespace(name='ContextLens'), to_bytes=lambda: b'alias')
        modules = {
            'ds_store': SimpleNamespace(DSStore=SimpleNamespace(open=lambda *args: store)),
            'mac_alias': SimpleNamespace(Alias=SimpleNamespace(for_file=lambda path: alias,
                                                               from_bytes=lambda value: alias)),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        configure(Path('/tmp/synthetic-volume'))
        self.records['.']['icvl'] = (b'type', b'icnv')

    def test_picture_requires_every_fallback_color_component(self):
        options = self.records['.']['icvp']
        # This is the original blank-background layout despite a valid alias and artwork.
        for channel in ['backgroundColorRed', 'backgroundColorGreen', 'backgroundColorBlue']:
            options.pop(channel, None)
        with self.assertRaisesRegex(ValueError, 'color'):
            verify_layout(Path('/tmp/synthetic-volume'))

    def test_complete_picture_settings_and_each_missing_or_malformed_component(self):
        options = self.records['.']['icvp']
        verify_layout(Path('/tmp/synthetic-volume'))
        for channel in ['backgroundColorRed', 'backgroundColorGreen', 'backgroundColorBlue']:
            self.assertEqual(options[channel], 1.0)
            for value in [None, '1.0', True, 0.5]:
                with self.subTest(channel=channel, value=value):
                    if value is None: options.pop(channel)
                    else: options[channel] = value
                    with self.assertRaisesRegex(ValueError, 'color'):
                        verify_layout(Path('/tmp/synthetic-volume'))
                    options[channel] = 1.0


if __name__ == '__main__': unittest.main()
