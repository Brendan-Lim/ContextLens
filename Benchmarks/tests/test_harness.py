import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import harness
import report

class HarnessTests(unittest.TestCase):
    def test_seeded_counterbalanced_plan(self):
        a=harness.plan(['01','04'],3,1729)
        self.assertEqual(a,harness.plan(['01','04'],3,1729));self.assertEqual(len(a),18)
        self.assertEqual(len({(r['task'],r['trial'],r['condition']) for r in a}),18)
        self.assertNotEqual(a,harness.plan(['01','04'],3,27))
    def test_no_cost_default(self):
        p=subprocess.run([sys.executable,str(Path(harness.__file__)),'--tasks','01'],capture_output=True,text=True,check=True)
        d=json.loads(p.stdout);self.assertEqual(d['kind'],'no-cost-run-plan');self.assertEqual(len(d['runs']),3)
    def test_live_requires_explicit_gate(self):
        p=subprocess.run([sys.executable,str(Path(harness.__file__)),'--live'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('--allow-paid',p.stderr)
    def test_preparation_requires_observed_times(self):
        with self.assertRaises(ValueError): harness.validate_preparation({'path':'/tmp','operator_observed':False})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'task.md').write_text('User instructions')
            folder,seconds=harness.validate_preparation({'path':d,'operator_observed':True,'T0':'2026-01-01T00:00:00Z','T1':'2026-01-01T00:00:07Z'})
            self.assertEqual(seconds,7);self.assertEqual(folder,p.resolve())
    def test_provider_commands_keep_sandbox_and_budget(self):
        c=harness.command('codex','test-model','high',1)
        self.assertIn('workspace-write',c);self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',c)
        c=harness.command('claude','test-model','high',1)
        self.assertIn('--max-budget-usd',c);self.assertNotIn('--dangerously-skip-permissions',c)
    def test_failure_retained_without_zero_time(self):
        rows=[]
        for c,tokens,success,time in [('manual',100,True,20),('contextlens',50,False,None)]:
            rows.append(dict(agent='codex',model='test-model',effort='high',task='01',trial=1,condition=c,usage={'total_tokens':tokens},success=success,end_to_end_seconds=time))
        g=report.aggregate(rows)[0]
        self.assertEqual(g['conditions']['contextlens']['usage.total_tokens']['median'],50)
        self.assertEqual(g['conditions']['contextlens']['failures_or_censored'],1)
        self.assertIsNone(g['conditions']['contextlens']['end_to_end_seconds']['median'])
        self.assertEqual(g['paired']['usage.total_tokens']['successful_pair_reduction_percent']['n'],0)
    def test_paired_reduction_and_speedup(self):
        rows=[dict(agent='codex',model='m',effort='high',task='01',trial=1,condition=c,usage={'total_tokens':v},success=True,end_to_end_seconds=t) for c,v,t in [('manual',100,20),('contextlens',50,10)]]
        g=report.aggregate(rows)[0]
        self.assertEqual(g['paired']['usage.total_tokens']['successful_pair_reduction_percent']['median'],50)
        self.assertEqual(g['paired']['end_to_end_seconds']['end_to_end_speedup_manual_over_contextlens']['median'],2)
        self.assertIsNone(g['paired']['usage.total_tokens']['median_difference_95pct_paired_bootstrap'])
    def test_providers_and_models_are_separate(self):
        rows=[dict(agent=a,model=m,effort='high',task='01',trial=1,condition='manual',usage={},success=False) for a,m in [('codex','m'),('claude','m'),('codex','n')]]
        self.assertEqual(len(report.aggregate(rows)),3)

if __name__=='__main__':unittest.main()
