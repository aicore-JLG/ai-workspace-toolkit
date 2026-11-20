import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1] / 'tools'


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        (self.root / 'PROJECT.md').write_text('Synthetic project.', encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('Read only this project.', encoding='utf-8')
        (self.root / 'SESSION-STATE.md').write_text('Legacy project summary.', encoding='utf-8')
        (self.root / 'source.txt').write_text('initial', encoding='utf-8')
        self.config()

    def config(self, command=None, inputs=None):
        (self.root / 'checks.json').write_text(json.dumps({
            'command': command or ['{python}', '-c', 'pass'],
            'inputs': inputs or ['source.txt'], 'timeout_seconds': 3}), encoding='utf-8')

    def call(self, *args, root=None):
        proc = subprocess.run([sys.executable, '-B', str(TOOLS/'session.py'), '--root',
                               str(root or self.root), *args], capture_output=True,
                              text=True, encoding='utf-8', timeout=15)
        self.assertTrue(proc.stdout, proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def start(self):
        code, result = self.call('start', '--objective', 'Ship a checked change',
                                '--acceptance', 'Source passes declared check', '--input', 'source.txt')
        self.assertEqual(code, 0, result)
        return result

    def check(self):
        return subprocess.run([sys.executable, '-B', str(TOOLS/'verify.py'), '--root',
                               str(self.root), '--run'], capture_output=True, timeout=15)

    def test_restart_recovers_checkpoint_and_rejects_stale_writer(self):
        started = self.start()
        code, checkpoint = self.call('checkpoint', '--expect', started['revision'],
                                    '--next-step', 'Review the changed source', '--decision', 'Use local checks')
        self.assertEqual(code, 0, checkpoint)
        code, resumed = self.call('resume')
        self.assertEqual(code, 0)
        self.assertEqual(resumed['session']['next_step'], 'Review the changed source')
        self.assertEqual(resumed['session']['decisions'], ['Use local checks'])
        self.assertEqual(resumed['revision'], checkpoint['revision'])
        self.assertNotEqual(self.call('checkpoint', '--expect', started['revision'], '--next-step', 'Overwrite')[0], 0)
        self.assertEqual(self.call('resume')[1]['revision'], checkpoint['revision'])

    def test_changed_and_missing_inputs_are_visible_after_restart(self):
        self.start()
        (self.root/'source.txt').write_text('changed', encoding='utf-8')
        resumed = self.call('resume')[1]
        self.assertEqual(resumed['changed_inputs'], ['source.txt'])
        (self.root/'source.txt').unlink()
        resumed = self.call('resume')[1]
        self.assertEqual(resumed['missing_inputs'], ['source.txt'])

    def test_verified_finish_requires_current_success_and_complete_coverage(self):
        started = self.start()
        args = ('finish', '--expect', started['revision'], '--verified', '--next-step', 'None')
        self.assertNotEqual(self.call(*args)[0], 0)
        self.config(['{python}', '-c', 'raise SystemExit(2)'])
        self.assertNotEqual(self.check().returncode, 0)
        self.assertNotEqual(self.call(*args)[0], 0)
        self.config()
        self.assertEqual(self.check().returncode, 0)
        (self.root/'source.txt').write_text('stale', encoding='utf-8')
        self.assertNotEqual(self.call(*args)[0], 0)
        self.config(inputs=['AGENTS.md'])
        self.assertEqual(self.check().returncode, 0)
        self.assertNotEqual(self.call(*args)[0], 0)
        self.config()
        self.assertEqual(self.check().returncode, 0)
        code, finished = self.call(*args)
        self.assertEqual(code, 0, finished)
        self.assertEqual(finished['session']['status'], 'verified')
        (self.root/'source.txt').write_text('later modification', encoding='utf-8')
        self.assertFalse(self.call('resume')[1]['verification_current'])

    def test_unverified_handoff_is_honest_and_active_start_refused(self):
        started = self.start()
        self.assertNotEqual(self.call('start', '--objective', 'Clobber', '--acceptance', 'None', '--input', 'source.txt')[0], 0)
        code, finished = self.call('finish', '--expect', started['revision'], '--next-step', 'Run checks', '--blocker', 'Check unavailable')
        self.assertEqual(code, 0, finished)
        self.assertEqual(finished['session']['status'], 'handed_off')
        self.assertFalse(finished['verification_current'])
        self.assertNotEqual(self.call('start', '--objective', 'New work', '--acceptance', 'Check', '--input', 'source.txt')[0], 0)
        code, fresh = self.call('start', '--expect', finished['revision'], '--objective', 'New work', '--acceptance', 'Check', '--input', 'source.txt')
        self.assertEqual(code, 0, fresh)

    def test_scoped_context_and_bad_paths(self):
        sibling = self.root.parent/'other'
        sibling.mkdir()
        (sibling/'AGENTS.md').write_text('DO NOT DISCLOSE SIBLING', encoding='utf-8')
        started = self.start()
        self.assertNotIn('DO NOT DISCLOSE SIBLING', json.dumps(started))
        self.assertIn('Read only this project.', json.dumps(started))
        for path in ['../other/AGENTS.md', '.env', '.workspace/session/current.json']:
            isolated = self.root.parent/('case'+str(len(path)))
            isolated.mkdir(exist_ok=True)
            self.assertNotEqual(self.call('start', '--objective', 'Test', '--acceptance', 'Check', '--input', path, root=isolated)[0], 0)

    def test_existing_lock_and_linked_state_refuse_writes(self):
        started = self.start()
        lock = self.root/'.workspace/session/write.lock'
        lock.write_text('another writer', encoding='utf-8')
        self.assertNotEqual(self.call('checkpoint', '--expect', started['revision'], '--next-step', 'No')[0], 0)
        lock.unlink()
        state = self.root/'.workspace/session/current.json'
        alias = self.root/'state-alias.json'
        os.link(state, alias)
        self.assertNotEqual(self.call('resume')[0], 0)

    def test_context_budget_omits_whole_file_and_reports_it(self):
        (self.root/'AGENTS.md').write_text('x' * 20000, encoding='utf-8')
        self.start()
        code, resumed = self.call('resume', '--context-budget', '1024')
        self.assertEqual(code, 0)
        self.assertIn('AGENTS.md', resumed['context']['omitted'])
        self.assertLessEqual(resumed['context']['bytes'], 1024)

    def test_copied_handoff_cannot_impersonate_another_project(self):
        import shutil
        self.start()
        sibling = self.root.parent/'copied'
        shutil.copytree(self.root, sibling)
        code, result = self.call('resume', root=sibling)
        self.assertNotEqual(code, 0)
        self.assertNotIn('Ship a checked change', json.dumps(result))

    def test_new_files_extend_required_verification_scope(self):
        started = self.start()
        self.assertEqual(started['check_status']['status'], 'missing')
        (self.root/'new.txt').write_text('new output', encoding='utf-8')
        code, saved = self.call('checkpoint', '--expect', started['revision'], '--next-step', 'Check both files', '--input', 'new.txt')
        self.assertEqual(code, 0, saved)
        self.assertEqual(saved['session']['inputs'], ['source.txt', 'new.txt'])
        self.assertEqual(self.check().returncode, 0)
        self.assertEqual(self.call('resume')[1]['check_status']['status'], 'incomplete_coverage')
        self.assertNotEqual(self.call('finish', '--expect', saved['revision'], '--next-step', 'Done', '--verified')[0], 0)
        self.config(inputs=['source.txt', 'new.txt'])
        self.assertEqual(self.check().returncode, 0)
        self.assertEqual(self.call('finish', '--expect', saved['revision'], '--next-step', 'Done', '--verified')[0], 0)

    def test_project_marker_required_and_atomic_failure_keeps_old_state(self):
        from unittest.mock import patch
        sys.path.insert(0, str(TOOLS))
        import session
        started = self.start()
        state = self.root/'.workspace/session/current.json'
        original = state.read_bytes()
        with patch.object(session.os, 'replace', side_effect=OSError('synthetic replace failure')):
            with self.assertRaises(OSError):
                session.update(self.root, started['revision'], 'Should not persist')
        self.assertEqual(state.read_bytes(), original)
        self.assertEqual(list(state.parent.glob('write-*.tmp')), [])
        (self.root/'PROJECT.md').unlink()
        self.assertNotEqual(self.call('resume')[0], 0)
        self.assertNotEqual(self.call('checkpoint', '--expect', started['revision'], '--next-step', 'No')[0], 0)

    def test_scoped_recall_is_ephemeral_and_forget_affects_next_resume(self):
        sys.path.insert(0, str(TOOLS))
        from memory import MemoryStore
        store = MemoryStore(self.root)
        note = store.propose('launch.region', 'synthetic-blue-region', 'owner decision')
        store.confirm(note['id'])
        started = self.start()
        self.assertEqual(started['memory']['status'], 'query_required')
        original = (self.root/'.workspace/session/current.json').read_bytes()
        code, recalled = self.call('resume', '--memory-query', 'launch.region')
        self.assertEqual(code, 0, recalled)
        self.assertEqual(recalled['memory']['records'][0]['value'], 'synthetic-blue-region')
        self.assertEqual((self.root/'.workspace/session/current.json').read_bytes(), original)
        self.assertNotIn(b'synthetic-blue-region', original)
        store.forget('launch.region')
        code, resumed = self.call('resume', '--memory-query', 'launch.region')
        self.assertEqual(code, 0)
        self.assertEqual(resumed['memory']['records'], [])
        self.assertNotEqual(self.call('resume', '--memory-query', ' ')[0], 0)
        (self.root/'Memory/curated.json').write_text('{broken', encoding='utf-8')
        self.assertNotEqual(self.call('resume', '--memory-query', 'launch')[0], 0)

    def test_recalled_memory_obeys_byte_and_record_limits(self):
        sys.path.insert(0, str(TOOLS))
        from memory import MemoryStore
        store = MemoryStore(self.root)
        for number in range(10):
            note = store.propose('topic.' + str(number), 'x' * 1500, 'owner')
            store.confirm(note['id'])
        self.start()
        code, recalled = self.call('resume', '--memory-query', 'topic')
        self.assertEqual(code, 0, recalled)
        self.assertLessEqual(len(recalled['memory']['records']), 8)
        self.assertLessEqual(recalled['memory']['bytes'], 8192)
        self.assertTrue(recalled['memory']['truncated'])


if __name__ == '__main__':
    unittest.main()
