from pathlib import Path
import importlib.util
import tempfile
import json
import unittest

file=Path(__file__).resolve().parents[1]/'live_pilot.py'
spec=importlib.util.spec_from_file_location('code_pilot',file)
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)


class PilotGateTests(unittest.TestCase):
    def test_previous_manual_study_authorization_is_not_inherited(self):
        previous=file.parents[2]/'Benchmarks/reports/manual-vs-contextlens/authorization.json'
        with self.assertRaisesRegex(ValueError,'does not explicitly cover'):pilot.require_authorization(previous)

    def test_missing_authorization_does_not_start_an_attempt(self):
        with self.assertRaisesRegex(ValueError,'New authorization'):pilot.require_authorization(None)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'no.json'
            with self.assertRaises(ValueError):pilot.require_authorization(p)

    def test_scope_and_cap_are_required_even_for_true_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'auth.json';p.write_text(json.dumps({'authorized':True,'study':'visual-to-code','max_invocations':999}))
            with self.assertRaises(ValueError):pilot.require_authorization(p)

    def test_seeded_schedule_is_four_matched_triplets_with_primary_AB(self):
        rows=pilot.schedule();self.assertEqual(rows,pilot.schedule());self.assertEqual(len(rows),12)
        for task in ['01','04','08','10']:
            self.assertEqual({r['condition'] for r in rows if r['task']==task},{'current','code-aware','minimal-code-aware'})
