import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runners"))
import telemetry

class UsageTests(unittest.TestCase):
    def test_codex_does_not_double_count_cumulative_usage(self):
        p = Path(__file__).resolve().parents[1] / "fixtures/codex-usage.jsonl"
        u = telemetry.codex(p.read_text())
        self.assertEqual(u["input_tokens"], 2500)
        self.assertEqual(u["uncached_input_tokens"], 1200)
        self.assertEqual(u["total_tokens"], 2750)
        self.assertEqual(u["turns"], 2)
        self.assertIsNone(u["reasoning_output_tokens"])
        self.assertIsNone(u["cost_usd"])
    def test_claude_cache_accounting_uses_only_root(self):
        p = Path(__file__).resolve().parents[1] / "fixtures/claude-usage.json"
        u = telemetry.claude(p.read_text())
        self.assertEqual(u["input_tokens"], 900)
        self.assertEqual(u["total_tokens"], 1020)
        self.assertEqual(u["cost_usd"], 0.02)
    def test_missing_is_not_zero(self):
        self.assertIsNone(telemetry.codex('{"type":"turn.completed","usage":{"output_tokens":1}}')["total_tokens"])
        self.assertIsNone(telemetry.claude('{"type":"result","usage":{"input_tokens":20,"output_tokens":1}}')["input_tokens"])
    def test_invalid_cache_rejected(self):
        with self.assertRaises(ValueError):
            telemetry.codex('{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":5}}')
    def test_nested_claude_not_accepted(self):
        with self.assertRaises(ValueError): telemetry.claude('[]')

if __name__ == "__main__": unittest.main()
