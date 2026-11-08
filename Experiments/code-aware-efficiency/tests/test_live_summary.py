"""Synthetic temporary records exercise analysis only; never model performance."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from summarize_live import summarize

class LiveSummaryTests(unittest.TestCase):
    def records(self,folder):
        rows=[dict(task='seat-allocation',condition=c,repeat=1) for c in ['current','code-aware']]
        (folder/'plan.json').write_text(json.dumps({'rows':rows}))
        for row,tokens,success in zip(rows,[100,80],[False,True]):
            dest=folder/'trials'/f"seat-allocation-{row['condition']}-1";dest.mkdir(parents=True)
            r=dict(row,kind='code-aware-efficiency-live-trial',status='accepted' if success else 'failed',success=success,
              baselineCommit='same',sourceBefore={},sourceAfter={},promptSHA256='same',imageSHA256='same',clockDiscrepancy=False,
              duration_seconds=10,evaluationSeconds=2,timeToIndependentlyAcceptedSeconds=12 if success else None,
              usage={'input_tokens':tokens-10,'output_tokens':10,'total_tokens':tokens,'cached_input_tokens':None,'uncached_input_tokens':None},
              activity={'commands':[],'recognizedSourceFilesRead':{},'sourceDiscoveryCommands':0,'filesInspectedRecognizedLowerBound':0})
            (dest/'result.json').write_text(json.dumps(r));(dest/'trace.jsonl').write_text('');(dest/'diff.patch').write_text('')

    def test_failed_attempt_stays_in_token_comparison_and_missing_cache_is_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);self.records(folder);r=summarize(folder)
            self.assertEqual(r['aggregates']['total_tokens']['completePairs'],1)
            self.assertEqual(r['aggregates']['total_tokens']['reductionOfMeansPercent'],20)
            self.assertEqual(r['aggregates']['uncached_input_tokens']['completePairs'],0)
            self.assertIsNone(r['aggregates']['uncached_input_tokens']['reductionOfMeansPercent'])
            self.assertEqual(r['bothAcceptedValidClockPairs'],0)
            self.assertEqual(r['correctness']['current']['accepted'],0)
            self.assertEqual(r['correctness']['code-aware']['accepted'],1)

    def test_anomalous_clock_excludes_execution_effect_but_keeps_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);self.records(folder);p=folder/'trials/seat-allocation-code-aware-1/result.json'
            r=json.loads(p.read_text());r['clockDiscrepancy']=True;p.write_text(json.dumps(r));r=summarize(folder)
            self.assertEqual(r['aggregates']['executionSeconds']['completePairs'],0)
            self.assertEqual(r['aggregates']['total_tokens']['completePairs'],1)

if __name__=='__main__':unittest.main()
