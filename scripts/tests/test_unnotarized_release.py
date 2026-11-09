import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import platform
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SPEC = importlib.util.spec_from_file_location('official', Path(__file__).resolve().parents[1] / 'unnotarized-release.py')
official = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(official)


class OfficialGateTests(unittest.TestCase):
    def candidate_files(self, root):
        receipt = self.receipt()
        receipt['assets'] = {}
        for name in official.asset_names(receipt['version']):
            (root / name).write_bytes(b'Synthetic container bytes for checksum rejection only')
            receipt['assets'][name] = official.sha256(root / name)
        (root / 'provenance.json').write_text(json.dumps(receipt))
        (root / 'SHA256SUMS').write_text(''.join(
            f'{official.sha256(root / name)}  {name}\n' for name in [*receipt['assets'], 'provenance.json']))
        return receipt

    def test_zip_and_dmg_each_reject_tampering_before_extraction(self):
        for name in official.asset_names(official.metadata()['version']):
            with self.subTest(asset=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); self.candidate_files(root)
                (root / name).write_bytes(b'Tampered synthetic container')
                with patch.object(official, 'run') as execute, patch.object(official, 'verify_dmg') as mount:
                    with self.assertRaisesRegex(ValueError, 'checksum mismatch'): official.verify_assets(root)
                    execute.assert_not_called(); mount.assert_not_called()

    def test_embedded_provenance_mismatch_is_rejected_before_dmg_mount(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); receipt = self.candidate_files(root)
            with patch.object(official, 'run'), patch.object(official, 'archive_members'), \
                 patch.object(official, 'bundle_hash', return_value=receipt['bundleInventorySHA256']), \
                 patch.object(official, 'verify_bundle', return_value=dict(receipt, sourceCommit='d' * 40)), \
                 patch.object(official, 'verify_dmg') as mount:
                with self.assertRaisesRegex(ValueError, 'provenance differs'): official.verify_assets(root)
                mount.assert_not_called()

    def test_publish_checks_freshness_before_assets_and_before_remote_writes(self):
        for outcomes, asset_calls in [([ValueError('stale release inputs')], 0),
                                       ([None, ValueError('stale release inputs')], 1)]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'provenance.json').write_text(json.dumps(self.receipt()))
                evidence = root / 'acceptance.json'
                evidence.write_text(json.dumps(self.evidence()))
                with patch.object(official, 'assert_fresh_candidate', create=True, side_effect=outcomes) as fresh, \
                     patch.object(official, 'unused_version'), patch.object(official, 'candidate_run'), \
                     patch.object(official, 'verify_assets', return_value=self.receipt()) as verify, \
                     patch.object(official, 'run', return_value='{}') as execute:
                    with self.assertRaisesRegex(ValueError, 'stale release inputs'):
                        official.publish(root, evidence, '42')
                    self.assertEqual(verify.call_count, asset_calls)
                    self.assertEqual(fresh.call_count, len(outcomes))
                    for call in execute.call_args_list:
                        self.assertNotIn('create', call.args)
                        self.assertNotIn('-f', call.args)

    @unittest.skipUnless(platform.system() == 'Darwin', 'macOS build entry point')
    def test_build_cannot_silently_change_a_requested_signing_channel(self):
        for arguments in [ ['--distribution', '--unnotarized-stable'],
                           ['--unnotarized-stable', '--distribution'],
                           ['--preview', '0.3.1-preview.1', '--unnotarized-stable'] ]:
            result = subprocess.run(['zsh', str(official.ROOT / 'scripts/build-app.sh'), *arguments], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Choose exactly one signing channel', result.stderr)

    def receipt(self):
        return dict(version=official.metadata()['version'], build=official.metadata()['build'],
                    sourceCommit='a' * 40, bundleInventorySHA256='b' * 64,
                    assets={'sample.zip': 'c' * 64}, trust=official.TRUST)

    def evidence(self):
        return dict(schemaVersion=1, version=official.metadata()['version'],
                    build=official.metadata()['build'], sourceCommit='a' * 40,
                    bundleInventorySHA256='b' * 64, assets={'sample.zip': 'c' * 64},
                    isolatedEnvironment=True, testedBy='release-maintainer',
                    testedAt=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), macOS='15.8.2', architecture='arm64',
                    blockers=[], cases={case: dict(status='pass', observation='Observed on disposable Mac; retained synthetic evidence.',
                                                 evidence='isolated-run/case-01') for case in official.CASES})

    def test_missing_acceptance_cannot_publish_or_create_tag(self):
        with patch.object(official, 'run') as execute:
            with self.assertRaises((ValueError, FileNotFoundError)):
                official.publish('/tmp/no-official-assets', '/tmp/no-acceptance-evidence', '42')
            execute.assert_not_called()

    def test_gate_binds_exact_candidate_and_every_manual_case(self):
        receipt, evidence = self.receipt(), self.evidence()
        official.acceptance(evidence, receipt)
        changes = [dict(isolatedEnvironment=False), dict(blockers=['unresolved closure']),
                   dict(sourceCommit='d' * 40), dict(bundleInventorySHA256='e' * 64),
                   dict(assets={'sample.zip': 'f' * 64}), dict(build=999), dict(testedBy='pending'),
                   dict(testedAt='yesterday'), dict(architecture='x86_64'), dict(macOS='13.0'), dict(cases={})]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                official.acceptance(dict(evidence, **change), receipt)
        for case in official.CASES:
            for status in ['pending', 'fail', True, 'PASS']:
                changed = copy.deepcopy(evidence)
                changed['cases'][case]['status'] = status
                with self.subTest(case=case, status=status), self.assertRaises(ValueError):
                    official.acceptance(changed, receipt)
        for field in ['observation', 'evidence']:
            changed = copy.deepcopy(evidence)
            changed['cases'][official.CASES[0]][field] = 'TODO'
            with self.assertRaises(ValueError): official.acceptance(changed, receipt)

    def test_download_tampering_fails_before_mounting_or_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            receipt = self.receipt()
            receipt['assets'] = {name: 'c' * 64 for name in official.asset_names(receipt['version'])}
            (path / 'provenance.json').write_text(json.dumps(receipt))
            for name in receipt['assets']: (path / name).write_bytes(b'tampered')
            with patch.object(official, 'run') as execute, patch.object(official, 'verify_dmg') as mount:
                with self.assertRaises(ValueError): official.verify_assets(path)
                execute.assert_not_called(); mount.assert_not_called()

    def test_only_exact_successful_manual_candidate_workflow_can_promote(self):
        receipt = self.receipt()
        good = dict(conclusion='success', event='workflow_dispatch', head_sha=receipt['sourceCommit'],
                    path='.github/workflows/unnotarized-stable.yml', head_branch='main',
                    repository={'full_name': official.REPO})
        official.candidate_run(good, receipt)
        for change in [dict(conclusion='failure'), dict(event='pull_request'), dict(head_sha='c' * 40),
                       dict(path='.github/workflows/ci.yml'), dict(repository={'full_name': 'someone/fork'}),
                       dict(head_branch='another-branch')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                official.candidate_run(dict(good, **change), receipt)

    def test_cask_requires_real_asset_and_discloses_unnotarized_trust(self):
        spec = importlib.util.spec_from_file_location('update_homebrew', Path(__file__).resolve().parents[1] / 'update-homebrew.py')
        updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)
        version = official.metadata()['version']
        for asset in [None, True, 0, -1, '123/../x']:
            with self.subTest(asset=asset), self.assertRaises(ValueError):
                updater.render_official(version, 'a' * 64, asset)
        with self.assertRaises(ValueError): updater.render_official(version, 'placeholder', 123)
        text = updater.render_official(version, 'a' * 64, 123)
        for expected in ['cask "contextlens"', 'Unnotarized official', 'Open Anyway',
                         'conflicts_with cask: "contextlens-preview"', 'container type: :zip']:
            self.assertIn(expected, text)
        for forbidden in ['zap ', 'xattr ', 'spctl ', ':no_check', '--no-quarantine']:
            self.assertNotIn(forbidden, text)

    def test_acceptance_uses_instants_across_tester_and_runner_timezones(self):
        evidence, receipt = self.evidence(), self.receipt()
        tested_at = datetime.fromisoformat(evidence['testedAt'])
        for offset in [-12, 0, 8, 14]:
            evidence['testedAt'] = tested_at.astimezone(timezone(timedelta(hours=offset))).isoformat()
            official.acceptance(evidence, receipt)
        for value in [tested_at.replace(tzinfo=None).isoformat(), tested_at.date().isoformat(),
                      (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()]:
            evidence['testedAt'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                official.acceptance(evidence, receipt)


class ReleaseInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='release-input-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture Maintainer')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('config/version.json', (official.ROOT / 'config/version.json').read_text())
        self.write('config/release-input-policy.json', json.dumps(dict(schemaVersion=1,
                   nonArtifactDocumentation=['README.md', 'docs/guide.md', 'docs/final-candidate.md'])))
        for name in ['Sources/App/main.swift', 'Package.swift', 'Package.resolved',
                     'scripts/build-app.sh', 'scripts/release.py', 'scripts/preview-release.py',
                     'scripts/swift.sh', 'scripts/unnotarized-release.py',
                     'Brand/AppIcon.icns', 'LICENSE', 'config/signing.json',
                     'distribution/dmg/dmg.py', 'distribution/dmg/assets/background.png',
                     'distribution/dmg/requirements.txt', '.github/workflows/unnotarized-stable.yml',
                     'README.md', 'docs/guide.md']:
            self.write(name, 'synthetic original\n')
        self.commit()
        patcher = patch.object(official, 'ROOT', self.root)
        patcher.start(); self.addCleanup(patcher.stop)
        self.source = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.PIPE).strip()

    def write(self, name, contents):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(contents)

    def commit(self):
        self.git('add', '-A'); self.git('commit', '-qm', 'Synthetic release input fixture')

    def receipt(self):
        return dict(sourceCommit=self.source, releaseInputs=official.release_input_identity(self.source))

    def test_each_production_dependency_and_packaging_input_invalidates_candidate(self):
        receipt = self.receipt()
        paths = ['Sources/App/main.swift', 'Package.swift', 'Package.resolved',
                 'scripts/build-app.sh', 'scripts/release.py', 'scripts/preview-release.py',
                 'scripts/swift.sh', 'scripts/unnotarized-release.py', 'Brand/AppIcon.icns',
                 'LICENSE', 'config/signing.json', 'distribution/dmg/dmg.py',
                 'distribution/dmg/assets/background.png', 'distribution/dmg/requirements.txt',
                 '.github/workflows/unnotarized-stable.yml', 'new-build-input.dat',
                 'docs/new-runtime-resource.json', 'docs/new-build-helper.swift']
        paths += ['docs/unreviewed-build-input.md']
        for name in paths:
            with self.subTest(path=name):
                # Independent descendant for each type of input, never shared cumulative changes.
                self.git('checkout', '-q', '--detach', self.source)
                self.write(name, 'synthetic changed\n'); self.commit()
                with self.assertRaisesRegex(ValueError, 'Release inputs changed'):
                    official.assert_fresh_candidate(receipt, 'HEAD')

    def test_readme_documentation_and_exact_acceptance_record_allow_same_candidate(self):
        receipt = self.receipt()
        self.write('README.md', 'New user-facing copy\n')
        self.write('docs/final-candidate.md', 'New engineering report\n')
        self.write('docs/release-acceptance/0.3.1.json', '{"synthetic": true}\n')
        self.commit()
        official.assert_fresh_candidate(receipt, 'HEAD')
        self.assertEqual(official.release_input_identity('HEAD'), receipt['releaseInputs'])

    def test_mode_symlink_deletion_and_reverted_input_changes_are_not_exempt(self):
        receipt = self.receipt()
        for change in ['mode', 'symlink', 'delete', 'revert']:
            with self.subTest(change=change):
                self.git('checkout', '-q', '--detach', self.source)
                if change == 'mode':
                    (self.root / 'scripts/build-app.sh').chmod(0o755)
                elif change == 'symlink':
                    (self.root / 'docs/guide.md').unlink()
                    (self.root / 'docs/guide.md').symlink_to('../Package.swift')
                elif change == 'delete':
                    (self.root / 'Brand/AppIcon.icns').unlink()
                else:
                    self.write('Package.swift', 'synthetic changed\n')
                self.commit()
                if change == 'revert':
                    self.write('Package.swift', 'synthetic original\n'); self.commit()
                with self.assertRaisesRegex(ValueError, 'Release inputs changed'):
                    official.assert_fresh_candidate(receipt, 'HEAD')

    def test_missing_or_forged_inventory_receipt_cannot_promote(self):
        receipt = self.receipt()
        for changed in [dict(sourceCommit=self.source),
                        dict(receipt, releaseInputs=dict(schemaVersion=1, sha256='0' * 64, files=1))]:
            with self.subTest(receipt=changed), self.assertRaisesRegex(ValueError, 'input inventory'):
                official.assert_fresh_candidate(changed, 'HEAD')


if __name__ == '__main__': unittest.main()
