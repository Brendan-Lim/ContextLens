from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import profile_agent_exploration as p


class ExplorationProfilerTests(unittest.TestCase):
    def test_shell_output_redirection_is_not_counted_as_a_file_read(self):
        c=p.classify("cat > new.js <<'EOF'\nhello\nEOF")
        self.assertEqual(c['recognized_reads'],[])
    def test_batched_reads_and_searches_are_classified_without_token_attribution(self):
        c=p.classify("/bin/zsh -lc 'cat evidence/context.md; cat app.js styles.css; rg --files; git diff --check'")
        self.assertEqual(c['recognized_reads'],['evidence/context.md','app.js','styles.css'])
        self.assertTrue(c['source_search_or_listing']);self.assertTrue(c['test_or_assertion_command'])
        self.assertIn('source_code_reading',c['categories'])

    def test_heredoc_python_read_does_not_turn_arbitrary_strings_into_shell(self):
        c=p.classify("python3 - <<'PY'\ntext=Path('styles.css').read_text()\nassert text\nPY")
        self.assertEqual(c['recognized_source_reads'],['styles.css'])

    def test_outside_and_glob_paths_are_not_asserted_as_project_reads(self):
        self.assertIsNone(p.project_path('../other/private.js'))
        self.assertIsNone(p.project_path('/etc/config.json'))
        self.assertIsNone(p.project_path('*.js'))
        self.assertEqual(p.project_path('./styles.css'),'styles.css')
