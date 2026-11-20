"""Real subprocess contract tests with synthetic CLIs; never contact a model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import worker_provider as worker
REAL_MANAGED_POLICY = worker._managed_policy_present

SCHEMA = {'type': 'object', 'properties': {'answer': {'type': 'string', 'maxLength': 200}},
          'required': ['answer'], 'additionalProperties': False}
# Sanitized Codex 0.166.0 startup notices captured from a real isolated worker.
DEPRECATION_NOTICES = [
    '`[features].use_legacy_landlock` is deprecated and will be removed soon. (Remove this setting to stop opting into the legacy Linux sandbox behavior.)',
    '`[features].web_search_cached` is deprecated because web search is enabled by default. (Set `web_search` to `"live"`, `"indexed"`, `"cached"`, or `"disabled"` at the top level (or under a profile) in config.toml if you want to override it.)',
    '`[features].web_search_request` is deprecated because web search is enabled by default. (Set `web_search` to `"live"`, `"indexed"`, `"cached"`, or `"disabled"` at the top level (or under a profile) in config.toml if you want to override it.)',
]
FAKE = r'''
import json,sys,time,os,subprocess
from pathlib import Path
provider=sys.argv[1]
args=sys.argv[2:]
control=json.loads(Path(__file__).with_suffix('.json').read_text())
if '--help' in args:
 print('--safe-mode --restricted --setting-sources --strict-mcp-config --mcp-config --tools --disable-slash-commands --no-chrome --no-session-persistence --system-prompt --json-schema --settings --verbose --model --effort <level> (low, medium, high, xhigh, max) --output-format --ignore-user-config --ignore-rules --ephemeral --strict-config --output-schema --sandbox --json')
elif 'status' in args:
 if provider=='claude':
  print(json.dumps({'loggedIn':True,'authMethod':control.get('auth','claude.ai'),'apiProvider':'firstParty','subscriptionType':control.get('plan','max')}))
 else:
  print('Logged in using '+control.get('auth','ChatGPT'),file=sys.stderr)
elif 'features' in args:
 print('guardianv2.thread_context removed false')
 for name in ['shell_tool','unified_exec','code_mode','code_mode_host','multi_agent','apps','hooks','plugins','memories','web_search_request','skip_host_skill_discovery']:
  print(name+' stable false')
else:
 data=json.loads(sys.stdin.read())
 mode=data.get('mode','ok')
 if mode=='background':
  subprocess.Popen([sys.executable,'-c',"import time;time.sleep(1.2);open("+repr(data['marker'])+",'w').write('escaped')"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
 if mode in ['sleep','tree']:
  if mode=='tree':
   subprocess.Popen([sys.executable,'-c',"import time;time.sleep(1.2);open("+repr(data['marker'])+",'w').write('escaped')"])
  time.sleep(10)
 if mode=='overflow':
  sys.stdout.write('x'*1000000);sys.stdout.flush();time.sleep(10)
 if mode=='stderr':
  print('FAKE_PRIVATE_TOKEN',file=sys.stderr);sys.exit(9)
 value={'answer':data.get('answer','worked')}
 if mode=='bad_schema': value={'wrong':'answer'}
 if provider=='claude':
  print(json.dumps({'type':'system','subtype':'init','model':'model-test','tools':[]}))
  if mode=='tool': print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Bash','input':{'command':'unsafe'}}]}}))
  print(json.dumps({'type':'result','subtype':'success','is_error':False,'structured_output':value,'usage':{'input_tokens':12,'output_tokens':8}}))
 else:
  print(json.dumps({'type':'thread.started','thread_id':'synthetic'}))
  print(json.dumps({'type':'turn.started','model':'model-test'}))
  if mode=='tool': print(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'unsafe'}}))
  print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps(value)}}))
  if mode!='incomplete': print(json.dumps({'type':'turn.completed','usage':{'input_tokens':12,'output_tokens':8,'cached_input_tokens':3}}))
'''


class WorkerProviderTests(unittest.TestCase):
    def protocol_events(self):
        return [{'type': 'thread.started'},
                *[{'type': 'item.completed', 'item': {'type': 'error', 'message': notice}}
                  for notice in DEPRECATION_NOTICES + [worker.STARTUP_WARNING]],
                {'type': 'turn.started'},
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"answer":"worked"}'}},
                {'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 8,
                    'cache_write_input_tokens': 3, 'reasoning_output_tokens': 2}}]

    def parse_events(self, events):
        return worker.parse_output('codex', '\n'.join(json.dumps(event) for event in events), SCHEMA)

    def test_exact_startup_deprecations_preserve_output_and_usage(self):
        result = self.parse_events(self.protocol_events())
        self.assertEqual(result['output'], {'answer': 'worked'})
        self.assertEqual(result['usage'], {'input_tokens': 12, 'output_tokens': 8,
            'cache_write_input_tokens': 3, 'reasoning_output_tokens': 2})
        self.assertIsNone(result['observed_model'])
        self.assertIsNone(result['observed_effort'])

    def test_warning_allowlist_does_not_allow_changed_late_or_tool_events(self):
        cases = []
        changed = self.protocol_events()
        changed[1]['item']['message'] += ' Changed behavior.'
        cases.append(changed)
        rerouted = self.protocol_events()
        rerouted[1]['item']['message'] = 'model rerouted: model-test -> other (Capacity)'
        cases.append(rerouted)
        late = self.protocol_events()
        late.insert(-2, late.pop(1))
        cases.append(late)
        terminal = self.protocol_events()
        terminal.append(terminal[1])
        cases.append(terminal)
        tool = self.protocol_events()
        tool[1]['item']['type'] = 'command_execution'
        cases.append(tool)
        for events in cases:
            with self.subTest(events=events), self.assertRaises(worker.WorkerError):
                self.parse_events(events)

    def test_additional_usage_fields_require_bounded_integers(self):
        for name in ('cache_write_input_tokens', 'reasoning_output_tokens'):
            for value in (True, -1, 1.5, '3', 10**12 + 1):
                events = self.protocol_events()
                events[-1]['usage'][name] = value
                with self.subTest(name=name, value=value), self.assertRaises(worker.WorkerError):
                    self.parse_events(events)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='worker-provider-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script = self.root / 'fake.py'
        self.script.write_text(FAKE, encoding='utf-8')
        self.control = self.script.with_suffix('.json')
        self.control.write_text('{}', encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k.upper() in worker.ENV_ALLOWLIST}
        env.update(HOME=str(self.root), USERPROFILE=str(self.root), CODEX_HOME=str(self.root / '.codex'))
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, env, clear=True).start()
        patch.object(worker, '_resolve_command', side_effect=lambda provider: [sys.executable, str(self.script), provider]).start()
        patch.object(worker, '_managed_policy_present', return_value=False).start()
        self.allowed = {'model-test': ['medium', 'high']}

    def invoke(self, provider='codex', **kwargs):
        payload = kwargs.pop('payload', {'answer': 'worked'})
        return worker.invoke(provider, 'model-test', 'high', payload, SCHEMA,
                             cwd=self.root, allowed_models=self.allowed, **kwargs)

    def test_both_actual_fake_workers_return_structured_output_and_usage(self):
        for provider in ('claude', 'codex'):
            result = self.invoke(provider)
            self.assertEqual(result['output'], {'answer': 'worked'})
            self.assertEqual(result['observed_model'], 'model-test')
            self.assertIsNone(result['observed_effort'])
            self.assertEqual(result['usage']['input_tokens'], 12)
            self.assertTrue(result['cleanup_confirmed'])
            self.assertIn('subscription', result['auth_route'])
        self.assertFalse(list(self.root.glob('worker-*')))

    def test_selection_and_execution_arguments_are_actual_controls(self):
        for provider in ('claude', 'codex'):
            plan = worker.build_invocation(provider, 'model-test', 'high', {'answer': 'x'}, SCHEMA,
                                           cwd=self.root, features=['shell_tool', 'hooks'])
            argv = plan['args']
            self.assertIn('model-test', argv if provider == 'claude' else ' '.join(argv))
            self.assertIn('--effort', argv) if provider == 'claude' else self.assertIn('model_reasoning_effort="high"', argv)
            self.assertNotIn('ANTHROPIC_API_KEY', plan['env'])
            self.assertNotIn('OPENAI_API_KEY', plan['env'])
            if provider == 'claude':
                self.assertEqual(argv[argv.index('--tools') + 1], '')
                self.assertIn('--safe-mode', argv)
                self.assertNotIn('--bare', argv)
            else:
                self.assertIn('forced_login_method="chatgpt"', argv)
                self.assertIn('features.shell_tool=false', argv)
                self.assertIn('features.hooks=false', argv)

    def test_unknown_model_or_effort_refused_before_execution(self):
        with patch.object(worker, '_run_process') as run:
            with self.assertRaises(worker.WorkerError):
                worker.preflight('claude', 'missing', 'high', allowed_models=self.allowed)
            with self.assertRaises(worker.WorkerError):
                worker.preflight('codex', 'model-test', 'ultra', allowed_models=self.allowed)
            run.assert_not_called()

    def test_api_override_refused_instead_of_silently_stripped(self):
        for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_OAUTH_TOKEN'):
            with patch.dict(os.environ, {name: 'FAKE_PRIVATE_TOKEN'}):
                with self.assertRaises(worker.WorkerError) as caught:
                    self.invoke()
                self.assertNotIn('FAKE_PRIVATE_TOKEN', str(caught.exception))

    def test_subscription_auth_required_and_managed_plan_refused(self):
        for provider, control in [('codex', {'auth': 'API key'}), ('claude', {'auth': 'api_key'}),
                                  ('claude', {'plan': 'enterprise'})]:
            self.control.write_text(json.dumps(control), encoding='utf-8')
            with self.assertRaises(worker.WorkerError):
                self.invoke(provider)

    def test_conflicting_local_provider_config_is_refused(self):
        folder = self.root / '.codex'
        folder.mkdir()
        (folder / 'config.toml').write_text('model_provider="thirdparty"\n', encoding='utf-8')
        with self.assertRaises(worker.WorkerError):
            self.invoke('codex')

    def test_tool_attempt_schema_error_and_incomplete_turn_refused(self):
        for provider, mode in [('claude', 'tool'), ('codex', 'tool'), ('claude', 'bad_schema'),
                                ('codex', 'bad_schema'), ('codex', 'incomplete')]:
            with self.subTest(provider=provider, mode=mode), self.assertRaises(worker.WorkerError):
                self.invoke(provider, payload={'mode': mode})

    def test_timeout_and_cancel_stop_real_process_tree(self):
        marker = self.root / 'escaped.txt'
        with self.assertRaises(worker.WorkerError) as caught:
            self.invoke(payload={'mode': 'tree', 'marker': str(marker)}, timeout_seconds=.35)
        self.assertEqual(caught.exception.code, 'timed_out')
        self.assertTrue(caught.exception.cleanup_confirmed)
        time.sleep(1.3)
        self.assertFalse(marker.exists())
        event = threading.Event()
        timer = threading.Timer(.5, event.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with self.assertRaises(worker.WorkerError) as caught:
            self.invoke(payload={'mode': 'sleep'}, cancel_event=event)
        self.assertEqual(caught.exception.code, 'cancelled')
        self.assertTrue(caught.exception.cleanup_confirmed)

    def test_overflow_and_vendor_errors_do_not_leak_output(self):
        for mode, code in [('overflow', 'output_limit'), ('stderr', 'provider_failed')]:
            with self.assertRaises(worker.WorkerError) as caught:
                self.invoke(payload={'mode': mode}, max_output_bytes=4096)
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('FAKE_PRIVATE_TOKEN', str(caught.exception))
            self.assertTrue(caught.exception.cleanup_confirmed)

    def test_cancellation_before_start_does_not_probe_or_launch(self):
        event = threading.Event()
        event.set()
        with patch.object(worker, '_run_process') as run, self.assertRaises(worker.WorkerError):
            self.invoke(cancel_event=event)
        run.assert_not_called()

    def test_unsupported_schema_is_refused(self):
        with patch.object(worker, '_run_process') as run, self.assertRaises(worker.WorkerError):
            worker.invoke('claude', 'model-test', 'high', {}, {'$ref': 'https://example.com/schema'},
                          cwd=self.root, allowed_models=self.allowed)
        run.assert_not_called()

    def test_managed_policy_refused_before_any_cli_probe(self):
        with patch.object(worker, '_managed_policy_present', return_value=True), \
                patch.object(worker, '_run_process') as run, self.assertRaises(worker.WorkerError) as caught:
            self.invoke('claude')
        self.assertEqual(caught.exception.code, 'managed_policy_unsupported')
        run.assert_not_called()

    def test_unknown_cleanup_is_preserved_for_coordinator_inspection(self):
        original = worker._stop_process
        def stopped_but_unconfirmed(process):
            result = original(process)
            return False if '--output-schema' in process.args else result
        with patch.object(worker, '_stop_process', side_effect=stopped_but_unconfirmed), \
                self.assertRaises(worker.WorkerError) as caught:
            self.invoke(payload={'mode': 'sleep'}, timeout_seconds=.15)
        self.assertFalse(caught.exception.cleanup_confirmed)
        self.assertEqual(caught.exception.code, 'timed_out')
        self.assertTrue(list(self.root.glob('worker-*')))

    def test_preflight_reports_declared_not_observed_selection(self):
        report = worker.preflight('codex', 'model-test', 'high', allowed_models=self.allowed)
        self.assertTrue(report['ready'])
        self.assertFalse(report['model_called'])
        self.assertEqual(report['selection_source'], 'recipient_declared')
        self.assertIsNone(report['observed_model'])
        self.assertIsNone(report['observed_effort'])

    def test_successful_parent_cannot_leave_background_worker(self):
        marker = self.root / 'background-escaped.txt'
        result = self.invoke(payload={'mode': 'background', 'marker': str(marker)})
        self.assertTrue(result['cleanup_confirmed'])
        time.sleep(1.3)
        self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows job attachment contract')
    def test_provider_cannot_execute_or_spawn_before_job_attachment(self):
        marker = self.root/'startup-child-escaped.txt'
        began = self.root/'startup-began.txt'
        child = 'import time;from pathlib import Path;time.sleep(1.2);Path(' + repr(str(marker)) + ').write_text("escaped")'
        parent = ('import subprocess,sys,time;from pathlib import Path;'
                  'Path(' + repr(str(began)) + ').write_text("started");'
                  'subprocess.Popen([sys.executable,"-c",' + repr(child) + '],'
                  'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);'
                  'time.sleep(.5);print("ok")')
        original = worker._attach_windows_job
        before_attachment = []
        def delayed_attachment(process):
            time.sleep(.25)
            before_attachment.append(began.exists())
            return original(process)
        with patch.object(worker, '_attach_windows_job', side_effect=delayed_attachment):
            output, _ = worker._run_process([sys.executable, '-B', '-c', parent],
                cwd=self.root, env=worker.sanitized_environment(), timeout_seconds=3)
        # Let an escaped synthetic child finish before fixture cleanup, even on failure.
        time.sleep(1.3)
        self.assertEqual(output.strip(), 'ok')
        self.assertEqual(before_attachment, [False])
        self.assertFalse(marker.exists())

    def test_managed_policy_in_selected_codex_home_blocks_all_probes(self):
        selected = self.root/'selected-codex-home'
        selected.mkdir()
        policy = selected/'requirements.toml'
        policy.write_text('# Synthetic managed policy', encoding='utf-8')
        with patch.dict(os.environ, {'CODEX_HOME': str(selected)}), \
                patch.object(worker, '_managed_policy_present', side_effect=REAL_MANAGED_POLICY), \
                patch.object(Path, 'exists', lambda path: path == policy), \
                patch.object(worker, '_run_process', return_value=('', '')) as run, self.assertRaises(worker.WorkerError) as caught:
            worker.preflight('codex', 'model-test', 'high', allowed_models=self.allowed)
        self.assertEqual(caught.exception.code, 'managed_policy_unsupported')
        run.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows suspended startup contract')
    def test_failed_assignment_or_resume_stops_suspended_process_without_execution(self):
        for failing_step in ('_attach_windows_job', '_resume_windows_process'):
            marker = self.root/(failing_step + '.txt')
            command = [sys.executable, '-B', '-c',
                       'from pathlib import Path;Path(' + repr(str(marker)) + ').write_text("ran")']
            launched = []
            original = subprocess.Popen
            def launch(*args, **kwargs):
                process = original(*args, **kwargs)
                if args[0] == command:
                    launched.append(process)
                return process
            with self.subTest(step=failing_step), patch.object(worker, failing_step, return_value=None), \
                    patch.object(subprocess, 'Popen', side_effect=launch), \
                    self.assertRaises(worker.WorkerError) as caught:
                worker._run_process(command, cwd=self.root, env=worker.sanitized_environment(), timeout_seconds=3)
            self.assertEqual(caught.exception.code, 'process_control_unavailable')
            self.assertTrue(caught.exception.cleanup_confirmed)
            self.assertFalse(marker.exists())
            for stream in (launched[0].stdin, launched[0].stdout, launched[0].stderr):
                self.assertTrue(stream.closed)

    @unittest.skipUnless(os.name == 'nt', 'Windows thread handle ownership contract')
    def test_resuming_reused_thread_id_cannot_resume_another_process(self):
        import ctypes
        from types import SimpleNamespace
        resumed, closed = [], []
        def first(snapshot, entry):
            entry._obj.th32OwnerProcessID = 42
            entry._obj.th32ThreadID = 99
            return True
        kernel = SimpleNamespace(
            CreateToolhelp32Snapshot=lambda flags, pid: 123,
            Thread32First=first, Thread32Next=lambda handle, entry: False,
            OpenThread=lambda access, inherit, identifier: 456,
            GetProcessIdOfThread=lambda handle: 777,
            ResumeThread=lambda handle: resumed.append(handle) or 1,
            CloseHandle=lambda handle: closed.append(handle) or True)
        with patch.object(ctypes, 'WinDLL', return_value=kernel):
            self.assertFalse(worker._resume_windows_process(SimpleNamespace(pid=42)))
        self.assertEqual(resumed, [])
        self.assertEqual(closed, [123, 456])


if __name__ == '__main__':
    unittest.main()
