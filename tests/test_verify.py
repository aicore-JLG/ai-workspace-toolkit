import json
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'verify.py'


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'source.txt').write_text('first', encoding='utf-8')
        self.config(['{python}', '-c', 'pass'])

    def config(self, command, inputs=None):
        (self.root / 'checks.json').write_text(json.dumps({'command': command, 'inputs': inputs or ['source.txt'], 'timeout_seconds': 3}), encoding='utf-8')

    def call(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args], capture_output=True, text=True, timeout=15)
        self.assertTrue(p.stdout, p.stderr)
        return p.returncode, json.loads(p.stdout)

    def test_preview_does_not_execute_or_write(self):
        self.config(['{python}', '-c', "open('marker','w').write('ran')"])
        code, result = self.call()
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'preview')
        self.assertFalse((self.root / 'marker').exists())
        self.assertFalse((self.root / '.workspace').exists())

    def test_success_then_source_and_config_stale(self):
        self.assertEqual(self.call('--run')[0], 0)
        self.assertEqual(self.call('--status')[1]['status'], 'passed')
        (self.root / 'source.txt').write_text('changed', encoding='utf-8')
        self.assertNotEqual(self.call('--status')[0], 0)
        self.assertEqual(self.call('--run')[0], 0)
        self.config(['{python}', '-c', 'print(1)'])
        self.assertEqual(self.call('--status')[1]['status'], 'stale')

    def test_failure_is_retained_without_output(self):
        self.config(['{python}', '-c', "print('synthetic-private-output');raise SystemExit(7)"])
        code, result = self.call('--run')
        self.assertNotEqual(code, 0)
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(self.call('--status')[1]['status'], 'failed')
        self.assertNotIn('synthetic-private-output', (self.root / '.workspace/verification/latest.json').read_text())

    def test_input_change_during_check_refuses_pass(self):
        self.config(['{python}', '-c', "open('source.txt','w').write('changed')"])
        code, result = self.call('--run')
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'changed_during_check')

    def test_missing_receipt_and_bad_input_refused(self):
        self.assertEqual(self.call('--status')[1]['status'], 'missing')
        for path in ['../source.txt', '.env', '.git/config', 'missing.txt']:
            self.config(['{python}', '-c', 'pass'], [path])
            self.assertNotEqual(self.call('--run')[0], 0)

    def test_timeout_is_failure(self):
        self.config(['{python}', '-c', 'import time;time.sleep(8)'])
        config = json.loads((self.root / 'checks.json').read_text())
        config['timeout_seconds'] = 0.2
        (self.root / 'checks.json').write_text(json.dumps(config))
        self.assertEqual(self.call('--run')[1]['status'], 'timed_out')

    def test_timeout_stops_ordinary_child_process(self):
        import time
        child = "import time;time.sleep(1.5);open('child-marker','w').write('escaped')"
        parent = 'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(8)'
        self.config(['{python}','-c',parent])
        config = json.loads((self.root/'checks.json').read_text())
        config['timeout_seconds'] = 0.4
        (self.root/'checks.json').write_text(json.dumps(config))
        self.assertEqual(self.call('--run')[1]['status'],'timed_out')
        time.sleep(1.7)
        self.assertFalse((self.root/'child-marker').exists())

    def cancellation_fixture(self):
        import time
        sys.path.insert(0, str(SCRIPT.parent))
        import verify
        child = "import time;time.sleep(1.5);open('cancel-child-marker','w').write('escaped')"
        script = ("from pathlib import Path\nimport subprocess,sys,time\n"
                  "if Path('cancel-mode').exists():\n"
                  " subprocess.Popen([sys.executable,'-c'," + repr(child) + "])\n"
                  " Path('child-started').write_text('ready')\n time.sleep(8)\n")
        (self.root/'check.py').write_text(script, encoding='utf-8')
        self.config(['{python}', '-B', 'check.py'], ['source.txt', 'check.py'])
        self.assertEqual(verify.run_check(self.root, 'checks.json')[1], 0)
        (self.root/'cancel-mode').write_text('synthetic interruption trigger')
        original = subprocess.Popen
        processes = []

        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            if args[0][0] != sys.executable:
                return process
            wait = process.wait
            processes.append((process, wait))
            interrupted = False

            def wait_once_interrupted(*wait_args, **wait_kwargs):
                nonlocal interrupted
                if not interrupted:
                    interrupted = True
                    deadline = time.monotonic() + 3
                    while not (self.root/'child-started').exists():
                        if time.monotonic() > deadline or process.poll() is not None:
                            raise RuntimeError('Synthetic child did not start')
                        time.sleep(.01)
                    raise KeyboardInterrupt()
                return wait(*wait_args, **wait_kwargs)

            process.wait = wait_once_interrupted
            return process

        def cleanup():
            for process, wait in processes:
                process.wait = wait
                if process.poll() is None:
                    if sys.platform == 'win32':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       capture_output=True, timeout=5)
                    else:
                        import os, signal
                        os.killpg(process.pid, signal.SIGKILL)
                    wait(timeout=5)
        self.addCleanup(cleanup)
        return verify, launch, processes

    def test_cancel_stops_child_tree_and_invalidates_previous_success(self):
        import time
        verify, launch, processes = self.cancellation_fixture()
        try:
            with patch.object(subprocess, 'Popen', launch):
                receipt, code = verify.run_check(self.root, 'checks.json')
        except KeyboardInterrupt:
            self.fail('Cancellation escaped without invalidating prior successful evidence')
        self.assertEqual(code, 130)
        self.assertEqual(receipt['status'], 'cancelled')
        self.assertFalse(receipt['passed'])
        self.assertIsNotNone(processes[0][0].poll())
        self.assertFalse((self.root/'.workspace/verification/run.lock').exists())
        self.assertEqual(verify.status(self.root, 'checks.json')[0]['status'], 'cancelled')
        time.sleep(1.7)
        self.assertFalse((self.root/'cancel-child-marker').exists())

    def test_cancel_with_unresolved_cleanup_keeps_lock_and_blocks_old_success(self):
        verify, launch, processes = self.cancellation_fixture()
        with patch.object(subprocess, 'Popen', launch), patch.object(verify, 'stop_check', return_value=False):
            receipt, code = verify.run_check(self.root, 'checks.json')
        self.assertEqual(code, 130)
        self.assertEqual(receipt['status'], 'cancelled')
        self.assertTrue(receipt['lease_retained'])
        self.assertIsNone(processes[0][0].poll())
        self.assertTrue((self.root/'.workspace/verification/run.lock').exists())
        status, status_code = verify.status(self.root, 'checks.json')
        self.assertEqual(status['status'], 'running_or_interrupted')
        self.assertFalse(status['passed'])
        self.assertNotEqual(status_code, 0)
        with self.assertRaises(ValueError):
            verify.run_check(self.root, 'checks.json')

    def test_empty_inputs_rejected(self):
        (self.root / 'checks.json').write_text(json.dumps({'command':['{python}', '-c', 'pass'], 'inputs': []}))
        self.assertNotEqual(self.call('--run')[0], 0)

    def test_changed_verifier_invalidates_receipt(self):
        copied = self.root / 'verify-copy.py'
        shutil.copyfile(SCRIPT, copied)
        command = [sys.executable,str(copied),'--root',str(self.root)]
        self.assertEqual(subprocess.run([*command,'--run'],capture_output=True).returncode,0)
        with copied.open('a',encoding='utf-8') as stream:
            stream.write('\n# Updated verifier.\n')
        result = subprocess.run([*command,'--status'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)['status'],'stale')

    def test_hardlink_input_is_rejected(self):
        import os
        try:
            os.link(self.root/'source.txt',self.root/'alias.txt')
        except OSError:
            self.skipTest('Creating hard links is unavailable')
        self.config(['{python}','-c','pass'],['alias.txt'])
        self.assertNotEqual(self.call('--run')[0],0)

    def test_failed_launch_and_active_lock_cannot_pass(self):
        self.config(['workspace-nonexistent-test-command'])
        self.assertEqual(self.call('--run')[1]['status'],'launch_failed')
        self.config(['{python}','-c','pass'])
        self.assertEqual(self.call('--run')[0],0)
        (self.root/'.workspace/verification/run.lock').write_text('synthetic lease')
        self.assertEqual(self.call('--status')[1]['status'],'running_or_interrupted')
        self.assertNotEqual(self.call('--run')[0],0)

    def test_symlink_rejected_when_available(self):
        link = self.root / 'alias.txt'
        try:
            link.symlink_to(self.root / 'source.txt')
        except OSError:
            self.skipTest('Creating symlinks is unavailable')
        self.config(['{python}', '-c', 'pass'], ['alias.txt'])
        self.assertNotEqual(self.call('--run')[0], 0)

    def test_invalid_filename_config_is_refused_before_file_lookup(self):
        for name in ['bad|name.txt','bad<name.txt','bad>name.txt','bad"name.txt','bad\x02.txt']:
            with self.subTest(name=repr(name)):
                self.config(['{python}','-c',"open('should-not-run','w').write('ran')"],[name])
                code,result = self.call()
                self.assertNotEqual(code,0)
                self.assertIn('filename',result['error'].lower())
                self.assertFalse((self.root/'should-not-run').exists())


if __name__ == '__main__':
    unittest.main()
