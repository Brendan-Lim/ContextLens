import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SPEC = importlib.util.spec_from_file_location('preview_release', Path(__file__).resolve().parents[1] / 'preview-release.py')
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
BASE = preview.metadata()['version']
VERSION = BASE + '-preview.1'


class PreviewSafetyTests(unittest.TestCase):
    def test_existing_tag_or_draft_release_prevents_publication(self):
        for tag, pages in [('v' + VERSION + '\n', [[]]), ('', [[{'tag_name': 'v' + VERSION, 'draft': True}]])]:
            def command(*args):
                if 'branch' in args: return 'main\n'
                if 'rev-parse' in args: return 'a' * 40 + '\n'
                if 'tag' in args: return tag
                if args[0] == 'gh': return json.dumps(pages)
                return ''
            with self.subTest(tag=tag), patch.object(preview, 'source', return_value={}), patch.object(preview, 'run', side_effect=command) as execute:
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    preview.publish('/tmp/nonexistent-preview-assets', VERSION)
                self.assertFalse(any('create' in call.args or 'edit' in call.args for call in execute.call_args_list))

    def test_only_numbered_previews_of_current_base_are_allowed(self):
        self.assertEqual(preview.preview_version(VERSION), VERSION)
        other_base = str(int(BASE.split('.')[0]) + 1) + '.0.0-preview.1'
        for value in [BASE, 'v' + VERSION, BASE + '-preview.0', BASE + '-preview.01',
                      other_base, VERSION + '\n', VERSION + ';echo x']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                preview.preview_version(value)

    def test_no_apple_authority_or_team_allowed(self):
        preview.adhoc_signature('Signature=adhoc\nTeamIdentifier=not set\n')
        for signature in ['Signature=adhoc\nAuthority=Apple Development: Someone\n',
                          'Signature=adhoc\nTeamIdentifier=ABCDEFGHIJ\n', 'Signature=regular\n']:
            with self.subTest(signature=signature), self.assertRaises(ValueError):
                preview.adhoc_signature(signature)

    def test_dirty_source_and_existing_sidecars_fail_before_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(preview, 'source', side_effect=ValueError('clean source')):
                with self.assertRaisesRegex(ValueError, 'clean source'):
                    preview.package('ContextLens.app', temporary, VERSION)
            sidecar = Path(temporary) / f'ContextLens-{VERSION}-arm64.zip.json'
            sidecar.write_text('published')
            with patch.object(preview, 'source', return_value={}), patch.object(preview, 'verify_bundle', return_value={}):
                with self.assertRaisesRegex(ValueError, 'exists'):
                    preview.package('ContextLens.app', temporary, VERSION)
            self.assertEqual(sidecar.read_text(), 'published')

    def test_tampered_archive_rejected_before_extract_or_execute(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f'ContextLens-{VERSION}-arm64.zip'
            path.write_bytes(b'changed')
            path.with_suffix('.zip.sha256').write_text('old checksum')
            with patch.object(preview, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    preview.verify_archive(path, VERSION)
                execute.assert_not_called()

    def test_preview_receipt_cannot_claim_stable_trust(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f'ContextLens-{VERSION}-arm64.zip'
            path.write_bytes(b'archive')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix('.zip.sha256').write_text(f'{digest}  {path.name}\n')
            path.with_suffix('.zip.json').write_text(json.dumps({'sha256': digest, 'trust': 'developer-id-notarized'}))
            with patch.object(preview, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'receipt'):
                    preview.verify_archive(path, VERSION)
                execute.assert_not_called()

    def test_cask_requires_actual_sha_and_discloses_trust(self):
        with self.assertRaises(ValueError): preview.render_cask(VERSION, 'fake', 123)
        for asset_id in [0, -1, True, '123/../456', '123;echo x']:
            with self.subTest(asset_id=asset_id), self.assertRaises(ValueError):
                preview.render_cask(VERSION, 'a' * 64, asset_id)
        text = preview.render_cask(VERSION, 'a' * 64, 123)
        self.assertIn('cask "contextlens-preview"', text)
        self.assertIn(f'version "{VERSION},123"', text)
        self.assertIn('https://api.github.com/repos/Brendan-Lim/ContextLens/releases/assets/#{version.csv.second}', text)
        self.assertIn('Accept: application/octet-stream', text)
        self.assertIn('conflicts_with cask: "contextlens"', text)
        self.assertIn('Unnotarized', text)
        self.assertIn('Open Anyway', text)
        for forbidden in ['zap ', '--no-quarantine', 'xattr ', 'spctl ', ':no_check']:
            self.assertNotIn(forbidden, text)

    def test_published_preview_and_exact_uploaded_assets_are_required(self):
        version = VERSION
        name = f'ContextLens-{version}-arm64.zip'
        info = dict(tag_name='v' + version, draft=False, prerelease=True, published_at='now',
                    assets=[dict(id=i, url=f'https://api.github.com/repos/Brendan-Lim/ContextLens/releases/assets/{i}',
                                 name=n, state='uploaded', browser_download_url=
                                 f'https://github.com/Brendan-Lim/ContextLens/releases/download/v{version}/{n}')
                            for i, n in enumerate([name, name + '.sha256', name + '.json'], 123)])
        preview.published_assets(info, version)
        for change in [dict(draft=True), dict(prerelease=False), dict(assets=[]), dict(tag_name='v' + BASE)]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                preview.published_assets(dict(info, **change), version)
        with self.assertRaises(ValueError):
            preview.published_assets(dict(info, assets=[dict(a, url='https://example.com/foreign') for a in info['assets']]), version)


if __name__ == '__main__':
    unittest.main()
