import json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import compare_handoffs as study

class HandoffComparisonTests(unittest.TestCase):
    def test_schedule_is_seeded_paired_and_keeps_repeats(self):
        rows=study.plan(['01','03','05'],2)
        self.assertEqual(rows,study.plan(['01','03','05'],2))
        self.assertEqual(len(rows),12)
        self.assertEqual(len({(r['task'],r['trial'],r['condition']) for r in rows}),12)
    def test_visual_quality_control_rejects_changed_or_missing_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for condition in ['baseline','lean']:
                folder=root/'packages/01'/condition
                (folder/'crops').mkdir(parents=True);(folder/'annotated/states').mkdir(parents=True);(folder/'metadata').mkdir()
                (folder/'crops/CL-001.png').write_bytes(b'identical fixture bytes')
                for name in ['manifest.json','metadata/session.json']:(folder/name).write_text('{}')
            self.assertEqual(study.verify_pair(root,'01'),['crops/CL-001.png'])
            (root/'packages/01/lean/crops/CL-001.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):study.verify_pair(root,'01')

    def test_pending_run_has_no_invented_savings(self):
        with tempfile.TemporaryDirectory() as temp:
            result=study.summarize(Path(temp))
            self.assertEqual(result['status'],'live-validation-pending')
            self.assertEqual(result['trial_count'],0)
            self.assertIsNone(result['mean_tokens_saved_all_observed'])
            self.assertIsNone(result['exact_per_trial_allowance'])
    def test_failed_lean_attempt_cannot_be_a_successful_speedup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for condition,tokens,passed,seconds in [('baseline',100,True,20),('lean',50,False,None)]:
                folder=root/condition;folder.mkdir()
                (folder/'result.json').write_text(json.dumps(dict(task='01',trial=1,condition=condition,usage={'total_tokens':tokens},success=passed,agent_to_acceptance_seconds=seconds,attached_images={'same.png':'digest'})))
            result=study.summarize(root)
            self.assertEqual(result['mean_tokens_saved_all_observed'],50)
            self.assertEqual(result['both_passed_pairs'],0)
            self.assertIsNone(result['mean_agent_to_acceptance_seconds_saved_successful_pairs'])
