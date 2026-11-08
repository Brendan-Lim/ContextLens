import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runners'))
import report
import telemetry

class SavingsTests(unittest.TestCase):
    def row(self, task, condition, tokens, success=True, **extra):
        return dict(agent='test', model='fixed', effort='high', task=task, trial=1,
                    condition=condition, usage={'total_tokens': tokens}, success=success, **extra)

    def test_arithmetic_mean_is_not_median_and_savings_can_be_negative(self):
        rows = []
        for task, a, b in [('01', 100, 50), ('02', 100, 80), ('03', 100, 400)]:
            rows += [self.row(task, 'manual', a), self.row(task, 'contextlens', b)]
        block = report.aggregate(rows)[0]['paired']['usage.total_tokens']
        savings = block['all_observed_savings_manual_minus_contextlens']
        self.assertAlmostEqual(savings['mean'], -230 / 3)
        self.assertEqual(savings['median'], 20)
        self.assertEqual(savings['n'], 3)

    def test_failures_and_missing_usage_are_not_zero_savings(self):
        rows = [self.row('01', 'manual', 100), self.row('01', 'contextlens', 50, False),
                self.row('02', 'manual', 200), self.row('02', 'contextlens', None)]
        paired = report.aggregate(rows)[0]['paired']['usage.total_tokens']
        self.assertEqual(paired['paired_attempts'], 2)
        self.assertEqual(paired['missing_measurement_pairs'], 1)
        self.assertEqual(paired['all_observed_savings_manual_minus_contextlens']['mean'], 50)
        self.assertIsNone(paired['successful_pair_savings_manual_minus_contextlens']['mean'])

    def test_incompatible_cli_or_source_cannot_be_paired(self):
        for field in ['cli_version', 'source_sha256', 'timeout_seconds', 'node_version', 'command', 'platform']:
            rows = [self.row('01', 'manual', 100, **{field: 'a'}), self.row('01', 'contextlens', 50, **{field: 'b'})]
            self.assertEqual(len(report.aggregate(rows)), 2)

    def test_invalid_token_values_are_rejected(self):
        import json
        for invalid in [-1, True, '123', float('inf'), 2.5]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    telemetry.codex(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': invalid, 'output_tokens': 1}}))
                with self.assertRaises(ValueError):
                    telemetry.claude(json.dumps({'type': 'result', 'usage': {'input_tokens': invalid}}))

    def test_malformed_usage_shape_is_reported(self):
        for trace in ['[]', '{"type":"turn.completed","usage":null}', '{"type":"turn.completed","usage":[]}']:
            with self.assertRaises(ValueError): telemetry.codex(trace)
        with self.assertRaises(ValueError): telemetry.claude('{"type":"result","usage":null}')

if __name__ == '__main__': unittest.main()
