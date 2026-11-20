"""Synthetic orchestration contracts: no account or model calls."""
import json
import io
import os
import shutil
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import Future
from unittest.mock import patch
from contextlib import contextmanager, redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import orchestrate


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.kit = Path(self.temp.name)
        self.project = self.kit / 'Apps' / 'sample'
        self.project.mkdir(parents=True)
        for name in ('PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md', 'AGENTS.md'):
            (self.project / name).write_text('# Synthetic project\n', encoding='utf-8')
        (self.kit / 'WORKSPACE-RULES.md').write_text('Keep scope and verify work.', encoding='utf-8')
        (self.kit / 'roles').mkdir()
        for role in ('builder', 'researcher', 'reviewer'):
            (self.kit / 'roles' / (role + '.md')).write_text('Act as ' + role, encoding='utf-8')
        (self.project / 'value.txt').write_text('before', encoding='utf-8')
        (self.project / 'check.py').write_text("from pathlib import Path\nassert Path('value.txt').read_text() == 'after'\n", encoding='utf-8')
        (self.project / 'checks.json').write_text(json.dumps({'command': ['{python}', '-B', 'check.py'],
            'inputs': ['check.py', 'value.txt'], 'timeout_seconds': 5}), encoding='utf-8')
        self.manifest = {'schema_version': 1, 'project': 'Apps/sample', 'objective': 'Change the synthetic value.',
            'inputs': ['value.txt', 'check.py'], 'checks': 'checks.json', 'max_workers': 2, 'max_attempts': 2,
            'timeout_seconds': 10, 'models': {'claude': {'sonnet': ['medium', 'high']}},
            'jobs': [self.job('build', outputs=['value.txt'])],
            'reviewer': {'provider': 'claude', 'model': 'sonnet', 'effort': 'high'}}
        self.calls = []

    def job(self, identifier, depends=None, outputs=None):
        return {'id': identifier, 'role': 'builder', 'provider': 'claude', 'model': 'sonnet',
            'effort': 'medium', 'task': 'Perform this bounded synthetic task.', 'depends_on': depends or [],
            'inputs': ['value.txt'], 'outputs': outputs or []}

    def save(self):
        path = self.kit / 'jobs.json'
        path.write_text(json.dumps(self.manifest), encoding='utf-8')
        return 'jobs.json'

    def probe(self, *args, **kwargs):
        return {'auth_route': 'claude_subscription', 'ready': True}

    def worker(self, provider, model, effort, payload, schema, **kwargs):
        self.calls.append(payload)
        if payload['kind'] == 'review':
            output = {'verdict': 'accept', 'findings': [], 'artifact_sha256': payload['artifact_sha256']}
        else:
            output = {'summary': 'Synthetic result', 'findings': [],
                      'changes': [{'path': name, 'content': 'after'} for name in payload['outputs']]}
        return {'output': output, 'usage': {'input_tokens': 3, 'output_tokens': 2},
            'observed_model': model, 'observed_effort': None, 'auth_route': 'claude_subscription',
            'cleanup_confirmed': True, 'elapsed_seconds': 0.01}

    def run_plan(self, worker=None, resume=None):
        return orchestrate.execute(self.kit, self.save(), invoke=worker or self.worker,
                                   probe=self.probe, resume=resume)

    def test_preview_creates_nothing_and_requires_actual_model_effort(self):
        report = orchestrate.preview(self.kit, self.save())
        self.assertEqual(report['status'], 'preview')
        self.assertFalse((self.project / '.workspace').exists())
        self.assertNotIn('content', json.dumps(report))
        del self.manifest['jobs'][0]['effort']
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())

    def test_staging_review_and_explicit_apply_preserve_source_until_ready(self):
        result = self.run_plan()
        self.assertEqual(result['status'], 'verified')
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')
        reviewer = self.calls[-1]
        self.assertEqual(reviewer['kind'], 'review')
        self.assertNotIn('Synthetic result', json.dumps(reviewer))
        pending = orchestrate.apply(self.kit, 'Apps/sample', result['id'])
        self.assertEqual(pending['status'], 'apply_preview')
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')
        applied = orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        self.assertEqual(applied['status'], 'applied')
        self.assertEqual((self.project / 'value.txt').read_text(), 'after')
        self.assertTrue(applied['backups'])

    def test_parallel_workers_overlap_and_dependencies_wait(self):
        self.manifest['jobs'] = [self.job('a'), self.job('b'), self.job('build', ['a', 'b'], ['value.txt'])]
        barrier = threading.Barrier(2)
        completed = set()
        mutex = threading.Lock()
        def worker(*args, **kwargs):
            payload = args[3]
            if payload['kind'] == 'work':
                if payload['job_id'] in {'a', 'b'}:
                    barrier.wait(timeout=4)
                    with mutex:
                        completed.add(payload['job_id'])
                else:
                    self.assertEqual(completed, {'a', 'b'})
            return self.worker(*args, **kwargs)
        self.assertEqual(self.run_plan(worker)['status'], 'verified')

    def test_failed_checks_do_not_call_reviewer_or_pass(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            result['output']['changes'][0]['content'] = 'wrong'
            return result
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'checks_failed')
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(ValueError):
            orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)

    def test_review_rejection_and_forged_artifact_hash_block_apply(self):
        for wrong_hash in (False, True):
            def worker(*args, **kwargs):
                result = self.worker(*args, **kwargs)
                if args[3]['kind'] == 'review':
                    result['output'].update(verdict='accept' if wrong_hash else 'revise',
                                            findings=['A seeded defect'] if not wrong_hash else [])
                    if wrong_hash:
                        result['output']['artifact_sha256'] = '0' * 64
                return result
            result = self.run_plan(worker)
            self.assertNotEqual(result['status'], 'verified')
            with self.assertRaises(ValueError):
                orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)

    def test_accept_with_positive_findings_is_contradictory_and_blocks_apply(self):
        notes = ['All declared checks passed.', 'The candidate satisfies the requirements.']
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            if args[3]['kind'] == 'review':
                result['output'].update(verdict='accept', findings=notes)
            return result
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'review_failed')
        state = orchestrate.load(self.project, result['id'])
        self.assertTrue(state['checks']['passed'])
        self.assertEqual(state['review']['findings'], notes)
        for write in (False, True):
            with self.assertRaises(ValueError):
                orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=write)
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_source_change_or_candidate_edit_invalidates_apply(self):
        result = self.run_plan()
        (self.project / 'value.txt').write_text('concurrent edit')
        with self.assertRaises(ValueError):
            orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        self.assertEqual((self.project / 'value.txt').read_text(), 'concurrent edit')
        (self.project / 'value.txt').write_text('before')
        stage = self.project / '.workspace' / 'orchestration' / result['id'] / 'stage' / 'value.txt'
        stage.write_text('tampered')
        with self.assertRaises(ValueError):
            orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)

    def test_scope_escape_policy_write_conflict_and_cycle_refused(self):
        for name in ('../other.txt', 'AGENTS.md', 'checks.json', '.env'):
            self.manifest['jobs'] = [self.job('build', outputs=[name])]
            with self.assertRaises(ValueError):
                orchestrate.preview(self.kit, self.save())
        self.manifest['jobs'] = [self.job('a', outputs=['value.txt']), self.job('b', outputs=['value.txt'])]
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())
        self.manifest['jobs'] = [self.job('a', ['b']), self.job('b', ['a'])]
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())

    def test_out_of_scope_provider_change_is_rejected_before_staging(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            result['output']['changes'] = [{'path': '../other.txt', 'content': 'escaped'}]
            return result
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.project.parent / 'other.txt').exists())
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_resume_reuses_completed_workers_and_bounds_failed_attempts(self):
        self.manifest['jobs'] = [self.job('a'), self.job('build', ['a'], ['value.txt'])]
        class Failure(ValueError):
            cleanup_confirmed = True
            code = 'synthetic_failure'
        def worker(*args, **kwargs):
            if args[3].get('job_id') == 'build':
                raise Failure()
            return self.worker(*args, **kwargs)
        first = self.run_plan(worker)
        self.assertEqual(first['status'], 'failed')
        second = self.run_plan(resume=first['id'])
        self.assertEqual(second['status'], 'verified')
        self.assertEqual(sum(p.get('job_id') == 'a' for p in self.calls), 1)
        self.assertEqual(second['attempts'], 4)  # a, failed build, build, review

    def test_preflight_failure_starts_no_workers(self):
        def probe(*args, **kwargs):
            raise ValueError('Unavailable subscription route')
        with self.assertRaises(ValueError):
            orchestrate.execute(self.kit, self.save(), invoke=self.worker, probe=probe)
        self.assertEqual(self.calls, [])

    def test_unresolved_worker_cleanup_keeps_execution_lock(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            result['cleanup_confirmed'] = False
            return result
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['lease_retained'])
        self.assertTrue((self.project / '.workspace/orchestration/run.lock').exists())

    def test_unresolved_reviewer_cleanup_keeps_execution_lock(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            if args[3]['kind'] == 'review':
                result['cleanup_confirmed'] = False
            return result
        result = self.run_plan(worker)
        self.assertNotEqual(result['status'], 'verified')
        self.assertTrue(result['lease_retained'])

    def test_codex_usage_fields_survive_worker_review_and_persisted_state(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            result['usage'].update(cache_write_input_tokens=7, reasoning_output_tokens=5)
            return result
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'verified')
        expected = {'input_tokens': 3, 'output_tokens': 2,
                    'cache_write_input_tokens': 7, 'reasoning_output_tokens': 5}
        self.assertEqual(result['usage'], [expected, expected])
        state = orchestrate.load(self.project, result['id'])
        self.assertEqual(state['jobs']['build']['attempts'][0]['usage'], expected)
        self.assertEqual(state['review_attempts'][0]['usage'], expected)

    def test_codex_usage_fields_reject_noninteger_and_unbounded_values(self):
        for field in ('cache_write_input_tokens', 'reasoning_output_tokens'):
            for value in (True, -1, 1.5, '3', 2**53 + 1):
                with self.subTest(field=field, value=value):
                    def worker(*args, **kwargs):
                        result = self.worker(*args, **kwargs)
                        result['usage'][field] = value
                        return result
                    result = self.run_plan(worker)
                    self.assertEqual(result['status'], 'failed')
                    self.assertEqual((self.project / 'value.txt').read_text(), 'before')
                    self.assertEqual(result['usage'], [None])

    def test_untrusted_metadata_and_api_route_never_pass_or_echo(self):
        for override in ({'usage': {'unexpected': 'synthetic-confidential-value'}},
                         {'auth_route': 'unconfirmed_api'}, {'usage': {'input_tokens': -1}}):
            def worker(*args, **kwargs):
                result = self.worker(*args, **kwargs)
                result.update(override)
                return result
            result = self.run_plan(worker)
            self.assertNotEqual(result['status'], 'verified')
            raw = (self.project / '.workspace/orchestration' / result['id'] / 'state.json').read_text()
            self.assertNotIn('synthetic-confidential-value', raw + json.dumps(result))

    def test_project_rules_always_present_and_independent_workers_get_original(self):
        self.manifest['inputs'].append('PROJECT-RULES.md')
        self.manifest['max_workers'] = 1
        self.manifest['jobs'] = [self.job('writer', outputs=['value.txt']), self.job('reader')]
        result = self.run_plan()
        self.assertEqual(result['status'], 'verified')
        reader = next(p for p in self.calls if p.get('job_id') == 'reader')
        self.assertIn('PROJECT-RULES.md', reader['files'])
        self.assertEqual(reader['files']['value.txt'], 'before')

    def test_cross_job_path_prefix_and_check_source_changes_are_rejected(self):
        config = json.loads((self.project / 'checks.json').read_text())
        config['inputs'] += ['new', 'new/child.txt']
        (self.project / 'checks.json').write_text(json.dumps(config))
        self.manifest['jobs'] = [self.job('a', outputs=['new']), self.job('b', outputs=['new/child.txt'])]
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())
        self.manifest['jobs'] = [self.job('build', outputs=['check.py'])]
        config['inputs'] = ['check.py', 'value.txt']
        (self.project / 'checks.json').write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())

    def test_apply_uses_reviewed_bytes_even_if_stage_changes_after_check(self):
        result = self.run_plan()
        original = orchestrate.verify.status
        def racing_status(root, config):
            proof = original(root, config)
            (Path(root) / 'value.txt').write_text('unreviewed mutation')
            return proof
        with patch.object(orchestrate.verify, 'status', racing_status):
            try:
                orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
            except ValueError:
                pass
        self.assertNotEqual((self.project / 'value.txt').read_text(), 'unreviewed mutation')

    def test_apply_rechecks_non_output_source_after_acquiring_lease(self):
        result = self.run_plan()
        original = orchestrate.verify.exclusive_lock
        @contextmanager
        def racing_lock(*args, **kwargs):
            with original(*args, **kwargs) as lease:
                (self.project / 'check.py').write_text('# concurrent check edit\n')
                yield lease
        with patch.object(orchestrate.verify, 'exclusive_lock', racing_lock):
            with self.assertRaises(ValueError):
                orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_resume_does_not_reuse_undeclared_check_artifacts(self):
        (self.project / 'check.py').write_text("from pathlib import Path\np=Path('leftover')\nif not p.exists():\n p.write_text('cache')\n raise SystemExit(1)\n")
        first = self.run_plan()
        self.assertEqual(first['status'], 'checks_failed')
        second = self.run_plan(resume=first['id'])
        self.assertEqual(second['status'], 'checks_failed')
        self.assertEqual(len(self.calls), 1)

    def test_status_revalidates_candidate_and_handles_applied_history(self):
        result = self.run_plan()
        stage = self.project / '.workspace/orchestration' / result['id'] / 'stage/value.txt'
        stage.write_text('changed after review')
        output = io.StringIO()
        with redirect_stdout(output):
            code = orchestrate.main(['--root', str(self.kit), '--project', 'Apps/sample', '--status', result['id']])
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'stale')
        stage.write_text('after')
        orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        output = io.StringIO()
        with redirect_stdout(output):
            code = orchestrate.main(['--root', str(self.kit), '--project', 'Apps/sample', '--status', result['id']])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'applied')

    def test_staged_checks_do_not_inherit_ambient_service_credentials(self):
        with (self.project / 'check.py').open('a') as stream:
            stream.write("import os\nassert 'SYNTHETIC_SERVICE_SECRET' not in os.environ\n")
        with patch.dict(os.environ, {'SYNTHETIC_SERVICE_SECRET': 'synthetic-only'}):
            self.assertEqual(self.run_plan()['status'], 'verified')

    def test_resume_stops_when_attempt_budget_is_exhausted(self):
        self.manifest['max_attempts'] = 1
        class Failure(ValueError):
            cleanup_confirmed = True
        def worker(*args, **kwargs):
            raise Failure()
        result = self.run_plan(worker)
        with self.assertRaises(ValueError):
            self.run_plan(resume=result['id'])

    def test_unexpected_reviewer_error_retains_lease(self):
        def worker(*args, **kwargs):
            if args[3]['kind'] == 'review':
                raise RuntimeError('unknown provider interruption')
            return self.worker(*args, **kwargs)
        result = self.run_plan(worker)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['lease_retained'])

    def test_copied_historical_status_is_not_adopted(self):
        result = self.run_plan()
        orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        shutil.copytree(self.project, self.kit / 'Apps/copied')
        output = io.StringIO()
        with redirect_stdout(output):
            code = orchestrate.main(['--root', str(self.kit), '--project', 'Apps/copied', '--status', result['id']])
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'refused')

    def test_check_script_spelling_cannot_make_it_worker_writable(self):
        (self.project / 'audit.py').write_text('pass\n')
        self.manifest['inputs'].append('audit.py')
        self.manifest['jobs'] = [self.job('build', outputs=['audit.py'])]
        for command in (['{python}', './audit.py'], ['{python}', './AUDIT.py'], ['{python}', '-m', 'audit']):
            (self.project / 'checks.json').write_text(json.dumps({'command': command, 'inputs': ['audit.py']}))
            with self.assertRaises(ValueError):
                orchestrate.preview(self.kit, self.save())

    def test_complete_route_uses_real_adapter_subprocess_without_model(self):
        import worker_provider
        script = self.kit / 'synthetic-cli.py'
        script.write_text('''import json,sys
p=json.loads(sys.stdin.read())
if p['kind']=='review':
 out={'verdict':'accept','findings':[],'artifact_sha256':p['artifact_sha256']}
else:
 out={'summary':'Synthetic subprocess result','findings':[], 'changes':[{'path':n,'content':'after'} for n in p['outputs']]}
print(json.dumps({'type':'system','subtype':'init','model':sys.argv[sys.argv.index('--model')+1],'tools':[]}))
print(json.dumps({'type':'result','subtype':'success','is_error':False,'structured_output':out,'usage':{'input_tokens':7,'output_tokens':4}}))
''', encoding='utf-8')
        def preflight(*args, **kwargs):
            return {**self.probe(), 'features': [], 'selection_source': 'synthetic_probe'}
        with patch.object(worker_provider, 'preflight', preflight), patch.object(
                worker_provider, '_resolve_command', return_value=[sys.executable, str(script)]):
            result = orchestrate.execute(self.kit, self.save(), invoke=worker_provider.invoke, probe=preflight)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(len(result['usage']), 2)
        self.assertEqual(result['usage'][0]['input_tokens'], 7)
        self.assertEqual(orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)['status'], 'applied')

    def test_rejected_review_cannot_be_rerolled_without_revised_work(self):
        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            if args[3]['kind'] == 'review':
                result['output'].update(verdict='revise', findings=['A material defect remains.'])
            return result
        result = self.run_plan(worker)
        with self.assertRaises(ValueError):
            self.run_plan(resume=result['id'])

    def test_analysis_only_jobs_cannot_claim_unreviewed_answers_verified(self):
        self.manifest['jobs'] = [self.job('research')]
        with self.assertRaises(ValueError):
            orchestrate.preview(self.kit, self.save())

    def test_observed_effort_or_model_disagreement_fails(self):
        for override in ({'observed_effort': 'low'}, {'observed_model': 'unrequested-model'}):
            def worker(*args, **kwargs):
                result = self.worker(*args, **kwargs)
                result.update(override)
                return result
            self.assertNotEqual(self.run_plan(worker)['status'], 'verified')

    def test_coordinator_interrupt_drains_workers_and_keeps_usage(self):
        self.manifest['jobs'] = [self.job('a', outputs=['value.txt']), self.job('b')]
        started = threading.Barrier(3)
        def worker(*args, **kwargs):
            started.wait(timeout=4)
            if not kwargs['cancel_event'].wait(timeout=4):
                raise RuntimeError('Cancellation signal was not delivered')
            return self.worker(*args, **kwargs)
        def interrupt(*args, **kwargs):
            started.wait(timeout=4)
            raise KeyboardInterrupt()
        with patch.object(orchestrate, 'wait', interrupt):
            result = self.run_plan(worker)
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(result['lease_retained'])
        self.assertEqual(len(result['usage']), 2)
        self.assertTrue(all(row and row['input_tokens'] == 3 for row in result['usage']))
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_interrupt_collecting_result_keeps_cleanup_and_usage_evidence(self):
        for cleanup_confirmed in (True, False):
            with self.subTest(cleanup_confirmed=cleanup_confirmed):
                original_result = Future.result
                interrupted = False

                def interrupt_result(future, *args, **kwargs):
                    nonlocal interrupted
                    result = original_result(future, *args, **kwargs)
                    if not interrupted:
                        interrupted = True
                        raise KeyboardInterrupt()
                    return result

                def worker(*args, **kwargs):
                    result = self.worker(*args, **kwargs)
                    result['cleanup_confirmed'] = cleanup_confirmed
                    if not cleanup_confirmed:
                        self.addCleanup(shutil.rmtree, kwargs['cwd'], ignore_errors=True)
                    return result

                with patch.object(Future, 'result', interrupt_result):
                    result = self.run_plan(worker)
                self.assertEqual(result['status'], 'cancelled')
                self.assertEqual(result['lease_retained'], not cleanup_confirmed)
                self.assertEqual((self.project / '.workspace/orchestration/run.lock').exists(), not cleanup_confirmed)
                self.assertEqual(result['jobs']['build'], 'interrupted')
                self.assertEqual(result['usage'], [{'input_tokens': 3, 'output_tokens': 2}] if cleanup_confirmed else [None])
                self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_interrupt_after_dispatch_before_future_registration_retains_lease(self):
        self.assert_unregistered_dispatch_retains_lease(False)

    def test_unobserved_clean_dispatch_still_requires_cleanup_proof(self):
        self.assert_unregistered_dispatch_retains_lease(True)

    def assert_unregistered_dispatch_retains_lease(self, cleanup_confirmed):
        started = threading.Event()
        original_pool = orchestrate.ThreadPoolExecutor

        class InterruptedSubmit(original_pool):
            def submit(pool, *args, **kwargs):
                super().submit(*args, **kwargs)
                if not started.wait(timeout=4):
                    raise RuntimeError('Synthetic worker did not start')
                raise KeyboardInterrupt()

        def worker(*args, **kwargs):
            started.set()
            if not kwargs['cancel_event'].wait(timeout=4):
                raise RuntimeError('Cancellation signal was not delivered')
            result = self.worker(*args, **kwargs)
            result['cleanup_confirmed'] = cleanup_confirmed
            if not cleanup_confirmed:
                self.addCleanup(shutil.rmtree, kwargs['cwd'], ignore_errors=True)
            return result

        with patch.object(orchestrate, 'ThreadPoolExecutor', InterruptedSubmit):
            result = self.run_plan(worker)
        self.assertEqual(result['status'], 'cancelled')
        self.assertTrue(result['lease_retained'])
        self.assertTrue((self.project / '.workspace/orchestration/run.lock').exists())
        self.assertEqual(result['jobs']['build'], 'interrupted')
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['usage'], [None])
        state = orchestrate.load(self.project, result['id'])
        self.assertEqual(state['jobs']['build']['attempts'][0]['error'], 'dispatch_ownership_unconfirmed')
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')

    def test_cancel_resume_reuses_completed_work_with_scoped_handoff_and_attempts(self):
        self.manifest['jobs'] = [self.job('research'), self.job('build', ['research'], ['value.txt'])]
        handoff = '# Synthetic handoff\nCurrent task: update value and verify it.\n'
        (self.project / 'SESSION-STATE.md').write_bytes(handoff.encode('utf-8'))
        for directory in (self.kit / 'Memory', self.kit / 'Apps/other-client', self.project / '.workspace/session'):
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'private.txt').write_text('SYNTHETIC_UNSELECTED_MEMORY_CANARY', encoding='utf-8')
        build_started = threading.Event()
        original_wait = orchestrate.wait

        def worker(*args, **kwargs):
            if args[3].get('job_id') == 'build':
                build_started.set()
                if not kwargs['cancel_event'].wait(timeout=4):
                    raise RuntimeError('Cancellation signal was not delivered')
            return self.worker(*args, **kwargs)

        def interrupt_build(futures, **kwargs):
            if build_started.is_set() or build_started.wait(timeout=.05):
                raise KeyboardInterrupt()
            return original_wait(futures, **kwargs)

        with patch.object(orchestrate, 'wait', interrupt_build):
            cancelled = self.run_plan(worker)
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual(cancelled['jobs'], {'research': 'completed', 'build': 'interrupted'})
        self.assertFalse(cancelled['lease_retained'])
        previous = orchestrate.load(self.project, cancelled['id'])
        old_stage = orchestrate.stage_path(self.project, previous)
        (old_stage / 'discarded-cache.txt').write_text('SYNTHETIC_UNSELECTED_MEMORY_CANARY')
        resumed = self.run_plan(resume=cancelled['id'])
        self.assertEqual(resumed['status'], 'verified')
        self.assertEqual(resumed['attempts'], 4)
        self.assertEqual(resumed['usage'], [{'input_tokens': 3, 'output_tokens': 2}] * 4)
        self.assertEqual(sum(p.get('job_id') == 'research' for p in self.calls), 1)
        self.assertEqual(sum(p.get('job_id') == 'build' for p in self.calls), 2)
        self.assertNotIn('SYNTHETIC_UNSELECTED_MEMORY_CANARY', json.dumps(self.calls))
        for payload in self.calls:
            if payload['kind'] == 'work':
                self.assertEqual(payload['files']['SESSION-STATE.md'], handoff)
                self.assertEqual(set(payload['files']), {'PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md', 'AGENTS.md', 'value.txt'})
        current_stage = orchestrate.stage_path(self.project, orchestrate.load(self.project, resumed['id']))
        self.assertNotEqual(current_stage, old_stage)
        self.assertFalse((current_stage / 'discarded-cache.txt').exists())
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')
        self.assertEqual(orchestrate.apply(self.kit, 'Apps/sample', resumed['id'], write=True)['status'], 'applied')
        self.assertEqual((self.project / 'value.txt').read_text(), 'after')
        self.assertEqual((self.project / 'SESSION-STATE.md').read_text(), handoff)

    def test_independent_holdout_rejects_seeded_defect_after_smoke_checks_pass(self):
        self.manifest['objective'] = 'Set adult fare to 5; children and seniors must travel free.'
        (self.project / 'check.py').write_text(
            "import json\nfrom pathlib import Path\nr=json.loads(Path('value.txt').read_text())\nassert r['adult']==5 and r['child']==0\n",
            encoding='utf-8')

        def worker(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            payload = args[3]
            if payload['kind'] == 'work':
                result['output']['summary'] = 'MAKER_CLAIMS_EVERY_CASE_IS_CORRECT'
                result['output']['changes'][0]['content'] = json.dumps({'adult': 5, 'child': 0, 'senior': 5})
            else:
                self.assertNotIn('MAKER_CLAIMS_EVERY_CASE_IS_CORRECT', json.dumps(payload))
                fares = json.loads(payload['candidate']['value.txt'])
                if fares['senior'] != 0:
                    result['output'].update(verdict='revise', findings=['Senior fare violates the explicit requirement.'])
            return result

        result = self.run_plan(worker)
        state = orchestrate.load(self.project, result['id'])
        self.assertTrue(state['checks']['passed'])
        self.assertEqual(result['status'], 'review_failed')
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(state['review']['findings'], ['Senior fare violates the explicit requirement.'])
        with self.assertRaises(ValueError):
            orchestrate.apply(self.kit, 'Apps/sample', result['id'], write=True)
        self.assertEqual((self.project / 'value.txt').read_text(), 'before')


if __name__ == '__main__':
    unittest.main()
