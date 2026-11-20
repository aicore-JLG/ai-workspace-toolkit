import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import importlib.util
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/run.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('workspace_runner', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.configure("print('hello')")

    def configure(self, body, **options):
        (self.root/'task.py').write_text(body, encoding='utf-8')
        config = {'command':['{python}','task.py'], 'inputs':['task.py'], 'timeout_seconds':5, 'max_output_bytes':65536}
        config.update(options)
        (self.root/'run.json').write_text(json.dumps(config), encoding='utf-8')

    def call(self, *args, env=None):
        result = subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),*args], capture_output=True,text=True,timeout=20,env=env)
        self.assertTrue(result.stdout,result.stderr)
        return result.returncode,json.loads(result.stdout)

    def test_preview_does_not_execute_or_write(self):
        self.configure("open('marker','w').write('ran')")
        code,result = self.call()
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'preview')
        self.assertFalse((self.root/'marker').exists())
        self.assertFalse((self.root/'.workspace').exists())

    def test_run_preserves_success_and_status_becomes_stale(self):
        code,result = self.call('--run')
        self.assertEqual(code,0,result)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.call('--status')[0],0)
        (self.root/'task.py').write_text("print('different')")
        self.assertEqual(self.call('--status')[1]['status'],'stale')

    def test_failure_exit_is_preserved_without_raw_command_in_receipt(self):
        self.configure("print('needs attention');raise SystemExit(7)")
        code,result = self.call('--run')
        self.assertEqual(code,7)
        self.assertEqual(result['exit_code'],7)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(self.call('--status')[1]['status'],'failed')
        receipt = (self.root/'.workspace/runs/latest.json').read_text()
        self.assertNotIn('raise SystemExit',receipt)
        self.assertNotIn('command":',receipt)

    def test_sensitive_output_is_redacted_across_chunks(self):
        secret = 'synthetic_value_'+'a'*32
        body = "import os,sys,time\nv=os.environ['RUNNER_TEST_SECRET']\nsys.stdout.write('API_KEY='+v[:10]);sys.stdout.flush();time.sleep(.05);print(v[10:])\nprint('Authorization: Bearer synthetic-bearer-value')"
        self.configure(body)
        code,result = self.call('--run',env={**os.environ,'RUNNER_TEST_SECRET':secret})
        self.assertEqual(code,0,result)
        log = (self.root/result['log']).read_text()
        self.assertNotIn(secret,log)
        self.assertNotIn('synthetic-bearer-value',log)
        self.assertIn('[REDACTED]',log)
        self.assertNotIn('RUNNER_TEST_SECRET',json.dumps(result))

    def test_excessive_output_stops_and_does_not_create_large_log(self):
        self.configure("import sys,time\nwhile True:\n sys.stdout.write('x'*4096);sys.stdout.flush()",max_output_bytes=2048)
        code,result = self.call('--run')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'output_limit')
        self.assertLess((self.root/result['log']).stat().st_size,4096)

    def test_timeout_is_not_success(self):
        self.configure('import time;time.sleep(10)',timeout_seconds=.2)
        code,result = self.call('--run')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'timed_out')

    def test_input_changes_during_run_invalidate_success(self):
        self.configure("open('task.py','a').write('\\n# changed')")
        code,result = self.call('--run')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'changed_during_run')

    def test_dangerous_direct_commands_and_credential_arguments_refused(self):
        for command in [['cmd','/c','echo harmless'],['powershell','-Command','echo harmless'],['rm','-rf','folder'],['{python}','-c','print(1)'],['{python}','-cprint(1)'],['node','--eval=1'],['git','reset','--hard'],['{python}','task.py','.env'],['{python}','task.py','.envrc'],['{python}','task.py','--token=synthetic']]:
            with self.subTest(command=command):
                self.configure('pass',command=command)
                code,result = self.call('--run')
                self.assertNotEqual(code,0)
                self.assertEqual(result['status'],'refused')
                self.assertFalse((self.root/'.workspace').exists())

    def test_cooperative_lease_prevents_a_second_run(self):
        self.configure('import time;time.sleep(1.5)')
        first = subprocess.Popen([sys.executable,str(SCRIPT),'--root',str(self.root),'--run'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        deadline = time.monotonic()+5
        while not (self.root/'.workspace/runs/resource.lock').exists() and time.monotonic()<deadline:
            time.sleep(.03)
        self.assertTrue((self.root/'.workspace/runs/resource.lock').exists())
        self.assertEqual(self.call('--status')[1]['status'],'running_or_interrupted')
        self.assertNotEqual(self.call('--run')[0],0)
        stdout,stderr = first.communicate(timeout=8)
        self.assertEqual(first.returncode,0,(stdout,stderr))
        self.assertFalse((self.root/'.workspace/runs/resource.lock').exists())

    def test_missing_config_and_invalid_input_are_refused(self):
        self.assertEqual(self.call('--status')[1]['status'],'missing')
        self.configure('pass',inputs=['../other.txt'])
        self.assertNotEqual(self.call('--run')[0],0)

    def test_trusted_secret_operation_discards_output_and_argument_values(self):
        secret = 'unknown-injected-synthetic-value'
        self.configure("import sys\nprint(sys.argv[1]);print(sys.argv[1],file=sys.stderr)")
        receipt, code = runner.execute_trusted(self.root, [sys.executable, 'task.py', secret],
            operation='secret-injection', output_mode='discard')
        self.assertEqual(code, 0, receipt)
        self.assertIsNone(receipt['log'])
        self.assertNotIn(secret, json.dumps(receipt))
        for path in (self.root/'.workspace/runs').iterdir():
            self.assertNotIn(secret, path.read_text())

    def test_trusted_operation_uses_limits_and_same_lease(self):
        self.configure('import time;time.sleep(5)')
        receipt, code = runner.execute_trusted(self.root, [sys.executable, 'task.py'],
            operation='integration', timeout_seconds=.1)
        self.assertNotEqual(code, 0)
        self.assertEqual(receipt['status'], 'timed_out')
        self.assertFalse((self.root/runner.LOCK).exists())
        with runner.resource_lease(self.root) as lease:
            with self.assertRaises(ValueError):
                runner.execute_trusted(self.root, [sys.executable, 'task.py'])
            lease['retain'] = False

    def test_trusted_operation_discards_flood_and_preserves_failure(self):
        self.configure("print('x'*10000)")
        receipt, code = runner.execute_trusted(self.root, [sys.executable, 'task.py'],
            output_mode='discard', max_output_bytes=1024)
        self.assertEqual(receipt['status'], 'output_limit')
        self.assertNotEqual(code, 0)
        self.assertIsNone(receipt['log'])
        self.configure('raise SystemExit(7)')
        receipt, code = runner.execute_trusted(self.root, [sys.executable, 'task.py'])
        self.assertEqual(code, 7)
        self.assertEqual(receipt['status'], 'failed')

    def test_trusted_operation_rejects_shell_shims_and_invalid_limits(self):
        for command, options in [(['tool.cmd'], {}), (['tool.bat'], {}),
                ([sys.executable, 'task.py'], {'timeout_seconds':601}),
                ([sys.executable, 'task.py'], {'output_mode':'echo'})]:
            with self.subTest(command=command, options=options):
                with self.assertRaises(ValueError):
                    runner.execute_trusted(self.root, command, **options)
        self.assertFalse((self.root/'.workspace').exists())

    def test_cancelled_operation_is_receipted_and_releases_lease(self):
        with mock.patch.object(runner, 'capture', return_value=(None,'cancelled',['',''],False)):
            receipt, code = runner.execute_trusted(self.root, [sys.executable, 'task.py'])
        self.assertEqual(receipt['status'], 'cancelled')
        self.assertNotEqual(code, 0)
        self.assertFalse((self.root/runner.LOCK).exists())

    def test_capture_interrupt_stops_running_foreground_process(self):
        self.configure('import time;time.sleep(30)')
        with mock.patch.object(runner.time,'sleep',side_effect=KeyboardInterrupt):
            exit_code,reason,output,unresolved = runner.capture(
                [sys.executable,'task.py'],self.root,5,1024)
        self.assertEqual(reason,'cancelled')
        self.assertIsNotNone(exit_code)
        self.assertFalse(unresolved)

    def test_truncated_known_secret_and_url_credentials_are_redacted(self):
        secret = 'synthetic_value_'+'b'*60
        self.configure("import os,sys\nprint('https://sample:synthetic-password@example.invalid/path')\nsys.stdout.write('x'*960+os.environ['RUNNER_TEST_SECRET']);sys.stdout.flush()",max_output_bytes=1024)
        _,result = self.call('--run',env={**os.environ,'RUNNER_TEST_SECRET':secret})
        log = (self.root/result['log']).read_text()
        self.assertNotIn('synthetic-password',log)
        self.assertNotIn('synthetic_value_',log)

    def test_exited_parent_with_open_child_pipes_retains_lease(self):
        child = "import time;time.sleep(8);open('child-marker','w').write('finished')"
        body = 'import subprocess,sys\np=subprocess.Popen([sys.executable,"-c",'+repr(child)+'])\nopen("child.pid","w").write(str(p.pid))'
        self.configure(body,timeout_seconds=.4)
        try:
            code,result = self.call('--run')
            self.assertNotEqual(code,0)
            self.assertEqual(result['status'],'incomplete_output')
            self.assertTrue((self.root/'.workspace/runs/resource.lock').exists())
            self.assertTrue(result['lease_retained'])
            self.assertEqual(self.call('--status')[1]['status'],'running_or_interrupted')
            self.assertNotEqual(self.call('--run')[0],0)
        finally:
            pidfile = self.root/'child.pid'
            if pidfile.exists():
                pid = int(pidfile.read_text())
                if os.name=='nt':
                    subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                else:
                    import signal
                    try:
                        os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == '__main__':
    unittest.main()
