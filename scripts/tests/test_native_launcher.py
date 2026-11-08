import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
SPEC=importlib.util.spec_from_file_location('native_launcher',Path(__file__).resolve().parents[1]/'verify-native.py')
launcher=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(launcher)


class NativeLauncherTests(unittest.TestCase):
    def test_without_isolation_no_app_or_cli_is_launched_or_output_created(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher.subprocess,'run') as run:
            output=Path(temp)/'must-not-exist'
            with self.assertRaises(SystemExit) as error:
                launcher.main(['--output',str(output)])
            self.assertEqual(error.exception.code,2)
            self.assertFalse(output.exists());run.assert_not_called()

    def test_key_probe_is_explicit_not_the_default(self):
        args=launcher.parser().parse_args(['--isolated-environment','--closure-only'])
        self.assertFalse(args.key_probe);self.assertEqual(args.probe_style,'original')

    def test_timeout_is_not_a_success_or_raw_output_dump(self):
        with patch.object(launcher.subprocess,'run',side_effect=launcher.subprocess.TimeoutExpired('fixture',40,output=b'private diagnostic text')):
            result=launcher.invoke(['fixture'])
        self.assertEqual(result['status'],'timeout');self.assertNotIn('private diagnostic text',str(result))

    def test_wrong_bundle_version_is_rejected_before_any_launch(self):
        import json,plistlib
        expected=json.loads((launcher.ROOT/'config/version.json').read_text())
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher.subprocess,'run') as run:
            app=Path(temp)/'ContextLens.app';binary=app/'Contents/MacOS';binary.mkdir(parents=True)
            (binary/'ContextLens').write_text('fixture');(binary/'contextlens-cli').write_text('fixture')
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString':'0.0.0','CFBundleVersion':'1','CFBundleIdentifier':expected['bundleID']}))
            output=Path(temp)/'report'
            with self.assertRaises(SystemExit):launcher.main(['--isolated-environment','--app',str(app),'--output',str(output)])
            run.assert_not_called();self.assertFalse(output.exists())

    def test_partial_previous_evidence_is_not_overwritten(self):
        import json,plistlib
        expected=json.loads((launcher.ROOT/'config/version.json').read_text())
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher.subprocess,'run') as run:
            app=Path(temp)/'ContextLens.app';binary=app/'Contents/MacOS';binary.mkdir(parents=True)
            (binary/'ContextLens').write_text('fixture');(binary/'contextlens-cli').write_text('fixture')
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString':expected['version'],'CFBundleVersion':str(expected['build']),'CFBundleIdentifier':expected['bundleID']}))
            output=Path(temp)/'report';output.mkdir();(output/'window.png').write_text('preserve original evidence')
            with self.assertRaises(SystemExit):launcher.main(['--isolated-environment','--app',str(app),'--output',str(output)])
            run.assert_not_called();self.assertEqual((output/'window.png').read_text(),'preserve original evidence')

    def test_other_native_launchers_refuse_owner_desktop_before_creating_evidence(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            for name,extra in [('measure-capture-soak.py',[]),('measure-native-memory.py',['--baseline-app','/fixture/ContextLens.app'])]:
                output=Path(temp)/name
                result=subprocess.run([sys.executable,str(launcher.ROOT/'scripts'/name),'--output',str(output),*extra],capture_output=True,text=True)
                self.assertEqual(result.returncode,2);self.assertIn('--isolated-environment',result.stderr)
                self.assertFalse(output.exists())
