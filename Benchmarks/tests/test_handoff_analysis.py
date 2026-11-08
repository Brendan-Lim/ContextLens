import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import analyze_handoff_comparison as analysis


class HandoffAnalysisTests(unittest.TestCase):
    def fixture(self, root, lean_success=True):
        (root/'plan.json').write_text(json.dumps({'rows':[{},{}]}))
        for condition,usage,seconds in [
            ('baseline',{'input_tokens':100,'cached_input_tokens':70,'uncached_input_tokens':30,'output_tokens':20,'total_tokens':120},20),
            ('lean',{'input_tokens':90,'cached_input_tokens':50,'uncached_input_tokens':40,'output_tokens':10,'total_tokens':100},10)]:
            folder=root/condition;folder.mkdir()
            row={'task':'01','trial':1,'condition':condition,'usage':usage,
                 'success':condition=='baseline' or lean_success,'attached_images':{'same.png':'hash'},
                 'agent_to_acceptance_seconds':seconds,'allowance_before':{},'allowance_after':{}}
            (folder/'result.json').write_text(json.dumps(row))
            (folder/'trace.jsonl').write_text('')

    def test_total_token_savings_cannot_be_mistaken_for_uncached_savings(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            result=analysis.analyze(root)
            self.assertTrue(result['schedule_complete'])
            self.assertEqual(result['paired_token_savings_all_observed']['total_tokens']['mean'],20)
            self.assertEqual(result['paired_token_savings_all_observed']['uncached_input_tokens']['mean'],-10)
            self.assertIsNone(result['exact_per_trial_allowance'])
            self.assertIsNone(result['workspace_credit_cost'])

    def test_faster_failed_attempt_is_retained_without_claiming_accepted_speedup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root,lean_success=False)
            result=analysis.analyze(root)
            self.assertEqual(result['groups']['lean']['accepted'],0)
            self.assertEqual(result['paired_token_savings_all_observed']['total_tokens']['observations'],1)
            self.assertEqual(result['paired_accepted_result_seconds_saved_successful_pairs']['observations'],0)
            self.assertIsNone(result['paired_results'][0]['accepted_result_seconds_saved'])
