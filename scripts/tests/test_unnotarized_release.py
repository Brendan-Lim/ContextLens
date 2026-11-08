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


if __name__ == '__main__': unittest.main()
