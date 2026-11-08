import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import scripted_agent_trials as study

class ScriptedReportTests(unittest.TestCase):
    def write(self, root, name, condition, tokens, success, seconds):
        path=Path(root)/name;path.mkdir()
        (path/'result.json').write_text(json.dumps(dict(task='01',trial=1,condition=condition,success=success,usage={'total_tokens':tokens},agent_to_acceptance_seconds=seconds)))
    def test_failures_remain_in_tokens_and_missing_time_is_not_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            self.write(folder,'a','plain-screenshots',100,True,20)
            self.write(folder,'b','contextlens',150,False,None)
            result=study.summarize(Path(folder))
            pair=result['paired']['contextlens']
            self.assertEqual(pair['mean_tokens_saved_all_observed'],-50)
            self.assertIsNone(pair['mean_tokens_saved_successful_pairs'])
            self.assertIsNone(pair['mean_agent_to_acceptance_seconds_saved_successful_pairs'])
            self.assertIsNone(result['human_preparation_seconds'])
            self.assertEqual(result['conditions']['contextlens']['passed'],0)
    def test_unavailable_usage_and_duplicate_attempts_are_not_savings(self):
        with tempfile.TemporaryDirectory() as folder:
            self.write(folder,'a','plain-screenshots',100,True,20)
            self.write(folder,'b','contextlens',None,True,10)
            pair=study.summarize(Path(folder))['paired']['contextlens']
            self.assertEqual(pair['missing_usage_pairs'],1)
            self.assertIsNone(pair['mean_tokens_saved_all_observed'])
            self.write(folder,'duplicate','contextlens',100,True,10)
            with self.assertRaises(ValueError):study.summarize(Path(folder))

    def test_different_models_or_sources_cannot_be_pooled(self):
        with tempfile.TemporaryDirectory() as folder:
            self.write(folder,'a','plain-screenshots',100,True,20)
            self.write(folder,'b','contextlens',50,True,10)
            path=Path(folder)/'b/result.json'; row=json.loads(path.read_text()); row['model']='other-model'; path.write_text(json.dumps(row))
            with self.assertRaises(ValueError):study.summarize(Path(folder))
