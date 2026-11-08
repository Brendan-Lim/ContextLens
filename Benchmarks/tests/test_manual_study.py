import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import manual_study as study
import analyze_manual_study as analysis


class ManualStudyTests(unittest.TestCase):
    def test_patch_capture_handles_ignored_evidence_and_new_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'app.js').write_text('const n=0;\n');study.harness.baseline_commit(root)
            (root/'.gitignore').write_text('evidence/\n');(root/'evidence').mkdir();(root/'evidence/private.txt').write_text('reference')
            (root/'app.js').write_text('const n=1;\n');(root/'helper.js').write_text('export const x=1;\n')
            patch=study.capture_patch(root)
            self.assertIn('app.js',patch);self.assertIn('helper.js',patch)
            self.assertNotIn('private.txt',patch);self.assertNotIn('.gitignore',patch)

    def test_cumulative_cap_includes_excluded_pilot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous=root/'prior';previous.mkdir();folder=previous/'attempt';folder.mkdir();(folder/'result.json').write_text('{}')
            (root/'trials/current').mkdir(parents=True)
            self.assertEqual(study.invocation_count(root,{'previous_attempts_directory':str(previous)}),2)

    def row(self,root,condition,success=True,total=100,uncached=30,seconds=20):
        folder=root/'trials'/condition;folder.mkdir(parents=True)
        study.write(folder/'result.json',{'kind':'manual-equivalent-contextlens-agent-trial',
            'task':'01','trial':1,'condition':condition,'success':success,'status':'completed','T2':'observed',
            'usage':{'total_tokens':total,'uncached_input_tokens':uncached},
            'agent_execution_seconds':seconds,'time_to_accepted_solution_seconds':seconds+1 if success else None,
            'protocol_sha256':'same','model':'gpt-6.1-sol','effort':'high'})

    def test_schedule_reproducible_unique_and_counterbalanced(self):
        rows=study.schedule()
        self.assertEqual(rows,study.schedule());self.assertNotEqual(rows,study.schedule(2))
        self.assertEqual(len(rows),24)
        self.assertEqual(len({(r['task'],r['condition'],r['trial']) for r in rows}),24)
        self.assertTrue(all(r['phase']=='pilot' for r in rows[:4]))
        self.assertEqual({r['task'] for r in rows[:4]},{'01','08'})
        for task in {r['task'] for r in rows}:
            first=[r['condition'] for r in rows if r['task']==task and r['trial']==1]
            second=[r['condition'] for r in rows if r['task']==task and r['trial']==2]
            self.assertEqual(first,second[::-1])

    def test_empty_data_is_unavailable_never_zero_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=analysis.analyze(Path(tmp))
            self.assertEqual(result['actual_attempt_records'],0)
            self.assertIsNone(result['groups']['contextlens']['metrics']['total_tokens']['mean'])
            self.assertIsNone(result['human_workflow_seconds'])
            self.assertIsNone(result['paired_comparisons']['total_tokens']['reduction_of_paired_means_percent'])

    def test_failed_faster_fix_retains_tokens_but_has_no_accepted_speedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.row(root,'manual-equivalent',total=100,uncached=30)
            self.row(root,'contextlens',success=False,total=50,uncached=40,seconds=1)
            result=analysis.analyze(root)
            self.assertEqual(result['paired_comparisons']['total_tokens']['paired_differences']['mean'],50)
            self.assertEqual(result['paired_comparisons']['uncached_input_tokens']['paired_differences']['mean'],-10)
            self.assertEqual(result['paired_comparisons']['time_to_accepted_solution_seconds']['paired_differences']['n'],0)
            self.assertEqual(result['groups']['contextlens']['failed_or_incomplete'],1)

    def test_mixed_protocols_and_duplicate_attempts_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.row(root,'manual-equivalent');self.row(root,'contextlens')
            file=root/'trials/contextlens/result.json';data=json.loads(file.read_text());data['protocol_sha256']='changed';study.write(file,data)
            with self.assertRaisesRegex(ValueError,'pool'):analysis.analyze(root)
            data['protocol_sha256']='same';study.write(file,data)
            duplicate=root/'trials/duplicate';duplicate.mkdir();study.write(duplicate/'result.json',data)
            with self.assertRaisesRegex(ValueError,'Duplicate'):analysis.analyze(root)

    def test_partial_attempt_reserved_directory_is_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=study.schedule();row=rows[0]
            folder=root/'trials'/f"{row['task']}-{row['condition']}-{row['trial']}";folder.mkdir(parents=True)
            self.assertEqual(len(study.pending_rows(root,rows,'pilot')),3)
            study.write(folder/'result.json',{'status':'interrupted'})
            self.assertNotIn(row,study.pending_rows(root,rows,'pilot'))

    def test_prior_authorization_cannot_start_this_study(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            study.write(root/'authorization.json',{'scope':'old study','authorized':True,'max_trials':24})
            with self.assertRaisesRegex(ValueError,'study-specific'):study.authorization(root)

    def test_cluster_bootstrap_counts_tasks_not_attempts(self):
        pairs=[]
        for task in ['01','03','04']:
            for repeat in [1,2]:
                pairs.append({'task':task,'metrics':{'total_tokens':{'manual':100,'contextlens':80,'difference_manual_minus_contextlens':20}}})
        interval=analysis.cluster_interval(pairs,'total_tokens')
        self.assertEqual(interval['task_clusters'],3)
        self.assertEqual(interval['low'],20);self.assertEqual(interval['high'],20)
        self.assertEqual(analysis.cluster_interval(pairs,'total_tokens',True)['low'],20)

    def test_reasoning_is_not_added_again_and_nested_usage_is_ignored(self):
        trace='\n'.join(json.dumps(x) for x in [
            {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':70,'output_tokens':20,'reasoning_output_tokens':10}},
            {'type':'item.completed','item':{'usage':{'input_tokens':999},'type':'command_execution','exit_code':1}}])
        usage=study.telemetry.codex(trace)
        self.assertEqual(usage['total_tokens'],120);self.assertEqual(usage['uncached_input_tokens'],30)
        self.assertEqual(study.activity(trace)['failed_shell_calls'],1)
