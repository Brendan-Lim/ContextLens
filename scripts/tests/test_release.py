import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
CURRENT_VERSION = release.metadata()['version']


class ReleaseSafetyTests(unittest.TestCase):
    def test_version_input_cannot_change_tag_or_shell_syntax(self):
        for version in ['v0.3.0', '../0.3.0', '0.3.0\n', '0.3.0;echo x', '00.3.0', '0.3.0-beta']:
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.metadata(version)

    def test_bump_must_match_checked_in_metadata(self):
        self.assertEqual(release.metadata(CURRENT_VERSION)['bundleID'], 'dev.contextlens.app')
        with self.assertRaises(ValueError): release.metadata('9.9.9')

    def test_archive_rejects_traversal_absolute_paths_foreign_roots_and_missing_cli(self):
        for name in ['../secret', '/tmp/secret', 'ContextLens.app/../../secret', 'unexpected.txt', 'ContextLens.app\\escape']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'bad.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('ContextLens.app/Contents/MacOS/contextlens-cli', 'binary')
                    archive.writestr(name, 'bad')
                with self.assertRaises(ValueError): release.archive_members(path)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'no-cli.zip'
            with zipfile.ZipFile(path, 'w') as archive: archive.writestr('ContextLens.app/Contents/Info.plist', 'plist')
            with self.assertRaises(ValueError): release.archive_members(path)

    def test_archive_rejects_symbolic_link_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'link.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('ContextLens.app/Contents/MacOS/contextlens-cli', 'binary')
                link = zipfile.ZipInfo('ContextLens.app/link')
                link.create_system = 3
                link.external_attr = 0o120777 << 16
                archive.writestr(link, '/etc/passwd')
            with self.assertRaises(ValueError): release.archive_members(path)

    def test_valid_archive_with_macos_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'valid.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('ContextLens.app/Contents/MacOS/contextlens-cli', 'binary')
                archive.writestr('__MACOSX/._ContextLens.app', 'metadata')
            release.archive_members(path)

    def test_public_packaging_demands_notarized_distribution_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(release, 'verify', side_effect=ValueError('untrusted')) as verify:
                with self.assertRaises(ValueError): release.package('ContextLens.app', temporary)
                verify.assert_called_once_with('ContextLens.app', 'distribution', notarized=True)
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_existing_archive_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            existing = Path(temporary) / f'ContextLens-{CURRENT_VERSION}-arm64.zip'
            existing.write_bytes(b'published bytes')
            with patch.object(release, 'verify', return_value=release.metadata()), patch.object(release, 'run', return_value=''):
                with self.assertRaisesRegex(ValueError, 'already exists'): release.package('ContextLens.app', temporary)
            self.assertEqual(existing.read_bytes(), b'published bytes')



class DownloadVerificationTests(unittest.TestCase):
    def test_changed_download_is_rejected_before_extracting_or_executing(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f'ContextLens-{CURRENT_VERSION}-arm64.zip'
            path.write_bytes(b'changed download')
            path.with_suffix('.zip.sha256').write_text('old hash  ' + path.name)
            with patch.object(release, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'checksum'): release.verify_archive(path)
                execute.assert_not_called()

    def test_checksum_matching_a_development_receipt_cannot_establish_trust(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f'ContextLens-{CURRENT_VERSION}-arm64.zip'
            path.write_bytes(b'development bytes')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix('.zip.sha256').write_text(f'{digest}  {path.name}\n')
            path.with_suffix('.zip.json').write_text(json.dumps({'sha256':digest,'trust':'development-only'}))
            with patch.object(release, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'receipt'): release.verify_archive(path)
                execute.assert_not_called()

if __name__ == '__main__': unittest.main()
