import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
import run_study as runner
import analyze

class ControlledStudyTests(unittest.TestCase):
    def test_private_dependency_copy_preserves_npm_bin_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'node_modules';runner.copy_dependencies(BASE/'fixture/node_modules',target)
            self.assertTrue((target/'.bin/tsc').is_symlink())
            self.assertTrue((target/'.bin/tsc').resolve().is_relative_to(target.resolve()))
            p=subprocess.run(['node',str(target/'.bin/tsc'),'--version'],text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('5.9.3',p.stdout)
            (target/'typescript/package.json').write_text('changed')
            self.assertNotEqual((target/'typescript/package.json').read_bytes(),(BASE/'fixture/node_modules/typescript/package.json').read_bytes())

    def test_plan_has_four_matched_pairs_and_counterbalances_later_replication(self):
        rows=runner.schedule();self.assertEqual(len(rows),8)
        for task in runner.TASKS:
            self.assertEqual({r['condition'] for r in rows if r['task']==task},{'current','code-aware'})
            self.assertEqual([r['condition'] for r in runner.schedule(2) if r['task']==task],list(reversed([r['condition'] for r in rows if r['task']==task])))

    def test_prior_authorization_and_wrong_caps_fail_closed(self):
        with self.assertRaises(ValueError):runner.require_authorization(None)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'auth.json'
            auth=dict(study='visual-to-code',authorized=True,max_invocations=12,user_instruction='prior study',billing_scope='existing-allocation-no-purchases-no-api')
            p.write_text(json.dumps(auth))
            with self.assertRaises(ValueError):runner.require_authorization(p)
            auth.update(study=runner.STUDY,max_invocations=8);p.write_text(json.dumps(auth));self.assertEqual(runner.require_authorization(p),auth)
            auth['max_invocations']=24;p.write_text(json.dumps(auth))
            with self.assertRaises(ValueError):runner.require_authorization(p)

    def test_activity_keeps_output_counts_separate_from_tokens(self):
        events=[{'type':'item.completed','item':{'type':'command_execution','command':c,'exit_code':0,'aggregated_output':'é'}} for c in ['find src -type f','cat src/state/useSeatAllocation.ts','cat src/state/useSeatAllocation.ts','npm run check']]
        report=runner.activity('\n'.join(map(json.dumps,events)),Path('/tmp/fake'))
        self.assertEqual(report['sourceDiscoveryCommands'],1);self.assertEqual(report['filesInspectedRecognizedLowerBound'],1)
        self.assertEqual(report['repeatedReadOccurrences'],1);self.assertEqual(report['testExecutionsRecognized'],1);self.assertEqual(report['commandOutputUTF8Bytes'],8)
        self.assertTrue(all(c['tokens'] is None for c in report['commands']))

    def test_empty_study_has_no_effect_estimates_and_rejects_synthetic_results(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'plan.json').write_text(json.dumps({'rows':runner.schedule()}))
            r=analyze.analyze(out);self.assertEqual(r['executed'],0);self.assertFalse(r['newLiveResultsAvailable']);self.assertEqual(r['descriptivePairedMeans'],{})
            p=out/'trials/fake';p.mkdir(parents=True);(p/'result.json').write_text(json.dumps({'kind':'synthetic-local-runner-check'}))
            with self.assertRaises(ValueError):analyze.analyze(out)

    def test_evidence_pairs_only_add_data_and_provenance(self):
        comparisons=json.loads((BASE/'reports/packages/comparison.json').read_text())
        for row in comparisons['rows']:
            folder=BASE/'reports/packages'/row['task'];a=folder/'current';b=folder/'code-aware'
            self.assertTrue((b/'context.md').read_text().startswith((a/'context.md').read_text()))
            extra=(b/'context.md').read_text()[len((a/'context.md').read_text()):]
            self.assertNotIn('Open a relevant candidate first',extra)
            for file in row['files']['current']:
                if file!='context.md':self.assertEqual((a/file).read_bytes(),(b/file).read_bytes())
            self.assertEqual(set(row['files']['code-aware'])-set(row['files']['current']),{'code-context/CL-001.json'})

if __name__=='__main__':unittest.main()
