"""Synthetic regression tests for the local workspace utilities."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'workspace.py'
spec = importlib.util.spec_from_file_location('workspace_core', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workspace-fixture-')
        self.root = Path(self.temp.name)
        self.ws = module.Workspace(self.root)
        self.put('AGENTS.md', 'Read `WORKSPACE-RULES.md` and `SESSION-STATE.md`.\n')
        self.put('CLAUDE.md', self.read('AGENTS.md'))
        self.put('WORKSPACE-RULES.md', '# Rules\nRead before editing.\n')
        self.put('SESSION-STATE.md', '# State\r\nAn unfinished task.\r\n')
        self.put('WHERE-THINGS-LIVE.md', '# Map\n')
        for name in ['AGENTS.md', 'CLAUDE.md', 'PROJECT-RULES.md', 'PROJECT.md', 'SESSION-STATE.md']:
            self.put('templates/project/' + name, '# Template\n')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return path

    def read(self, name):
        return (self.root / name).read_text(encoding='utf-8')

    def test_new_project_preview_and_actual_copy_preserve_templates(self):
        result = self.ws.new_project('Apps/sample')
        self.assertFalse(result['written'])
        self.assertFalse((self.root / 'Apps').exists())
        result = self.ws.new_project('Apps/sample', write=True)
        self.assertTrue(result['written'])
        self.assertEqual(self.read('Apps/sample/PROJECT.md'), self.read('templates/project/PROJECT.md'))
        with self.assertRaises(ValueError):
            self.ws.new_project('Apps/sample', write=True)

    def test_paths_cannot_escape_or_use_absolute_destinations(self):
        for destination in ['../outside', 'Apps/../../outside', '/outside', 'X:/outside', r'Apps\..\outside']:
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                self.ws.new_project(destination, write=True)

    def test_hidden_or_private_destination_refused(self):
        for destination in ['.git/project', '.workspace/project', 'private/project']:
            with self.assertRaises(ValueError):
                self.ws.new_project(destination, write=True)

    def test_invalid_portable_destination_names_leave_parent_uncreated(self):
        invalid_names = ['invalid|name', 'invalid?name', 'invalid*name', 'invalid<name',
                         'invalid>name', 'invalid"name', 'control\x1fname', 'delete\x7fname',
                         'trailing.', 'trailing ', 'CON', 'nul.txt', 'COM1', 'LPT9.md',
                         'COM\u00b9.txt', 'x' * 256, '\U0001f600' * 128]
        for name in invalid_names:
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValueError):
                    self.ws.new_project('newparent/' + name, write=True)
                self.assertFalse((self.root / 'newparent').exists())
        self.assertEqual(self.ws.path('.'), self.root)
        self.assertEqual(self.ws.path('./Apps/a valid-project', exists=False), self.root / 'Apps/a valid-project')

    def test_compaction_preserves_exact_history_and_rejects_stale_summary(self):
        original = (self.root / 'SESSION-STATE.md').read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        self.put('summary.md', '# Current\nContinue the unfinished task.\n')
        preview = self.ws.compact('SESSION-STATE.md', 'summary.md', digest)
        self.assertFalse(preview['written'])
        self.assertFalse((self.root / 'docs').exists())
        result = self.ws.compact('SESSION-STATE.md', 'summary.md', digest, write=True)
        self.assertEqual((self.root / result['archive']).read_bytes(), original)
        self.assertIn('Continue the unfinished task', self.read('SESSION-STATE.md'))
        self.assertIn(result['archive'], self.read('SESSION-STATE.md'))
        with self.assertRaises(ValueError):
            self.ws.compact('SESSION-STATE.md', 'summary.md', digest, write=True)

    def test_existing_lock_prevents_compaction_without_touching_state(self):
        original = (self.root / 'SESSION-STATE.md').read_bytes()
        self.put('summary.md', '# New\n')
        self.put('SESSION-STATE.md.compact.lock', 'another-writer')
        with self.assertRaises(ValueError):
            self.ws.compact('SESSION-STATE.md', 'summary.md', hashlib.sha256(original).hexdigest(), write=True)
        self.assertEqual((self.root / 'SESSION-STATE.md').read_bytes(), original)
        self.assertEqual(self.read('SESSION-STATE.md.compact.lock'), 'another-writer')

    def test_conflicting_archive_is_not_overwritten(self):
        digest = self.ws.state_hash()['sha256']
        self.put('summary.md', '# New\n')
        archive = self.ws.compact('SESSION-STATE.md', 'summary.md', digest)['archive']
        self.put(archive, 'existing unrelated archive')
        with self.assertRaises(ValueError):
            self.ws.compact('SESSION-STATE.md', 'summary.md', digest, write=True)
        self.assertEqual(self.read(archive), 'existing unrelated archive')

    def test_intervening_writer_is_preserved_after_archive(self):
        original = (self.root / 'SESSION-STATE.md').read_bytes()
        self.put('summary.md', '# Summary\n')
        digest = hashlib.sha256(original).hexdigest()
        reader = self.ws.read
        state_reads = 0

        def competing_read(path):
            nonlocal state_reads
            if path == self.root / 'SESSION-STATE.md':
                state_reads += 1
                if state_reads == 3:
                    self.put('SESSION-STATE.md', '# Another session\nKeep this newer work.\n')
            return reader(path)

        with patch.object(self.ws, 'read', competing_read):
            with self.assertRaises(ValueError):
                self.ws.compact('SESSION-STATE.md', 'summary.md', digest, write=True)
        self.assertIn('Keep this newer work', self.read('SESSION-STATE.md'))
        archives = list((self.root / 'docs/session-history').glob('*.md'))
        self.assertEqual(archives[0].read_bytes(), original)
        self.assertFalse((self.root / 'SESSION-STATE.md.compact.lock').exists())

    def test_missing_project_brief_prevents_creation(self):
        (self.root / 'templates/project/PROJECT.md').unlink()
        with self.assertRaises(ValueError):
            self.ws.new_project('Apps/sample', write=True)
        self.assertFalse((self.root / 'Apps').exists())

    def test_project_compaction_archives_within_its_project(self):
        self.put('Apps/sample/SESSION-STATE.md', '# Project\n')
        self.put('Apps/sample/summary.md', '# Next\n')
        digest = self.ws.state_hash('Apps/sample/SESSION-STATE.md')['sha256']
        result = self.ws.compact('Apps/sample/SESSION-STATE.md', 'Apps/sample/summary.md', digest, write=True)
        self.assertTrue(result['archive'].startswith('Apps/sample/docs/session-history/'))
        self.assertIn('docs/session-history/', self.read('Apps/sample/SESSION-STATE.md'))

    def test_doctor_finds_broken_link_and_entry_reference(self):
        self.put('README.md', '[Missing](docs/missing.md)\n')
        self.put('AGENTS.md', 'Read `gone.md`.\n')
        report = self.ws.doctor()
        self.assertFalse(report['ok'])
        self.assertEqual({f['code'] for f in report['findings']}, {'missing_link', 'missing_entry_reference'})

    def test_doctor_ignores_external_links_fences_and_inline_future_paths(self):
        self.put('README.md', '[Site](https://example.invalid)\nCreate `future/file.md` later.\n```md\n[Example](future.md)\n```\n')
        self.assertTrue(self.ws.doctor()['ok'])

    def test_doctor_checks_explicit_hidden_skill_reference_without_scanning_it(self):
        self.put('.claude/skills/example/SKILL.md', '[Unvisited](missing.md)\n')
        self.put('AGENTS.md', 'Read `.claude/skills/example/SKILL.md` when needed.\n')
        self.assertTrue(self.ws.doctor()['ok'])

    def test_doctor_follows_contained_parent_link_but_not_escape(self):
        self.put('docs/guide.md', '[Rules](../WORKSPACE-RULES.md)\n')
        self.assertTrue(self.ws.doctor()['ok'])
        self.put('docs/guide.md', '[Escape](../../outside.md)\n')
        self.assertIn('unsafe_link', {f['code'] for f in self.ws.doctor()['findings']})

    def test_context_is_scoped_deduplicated_and_never_silently_truncated(self):
        self.put('Apps/sample/PROJECT.md', '# Project\nOnly this project.\n')
        self.put('Clients/private-project/PROJECT.md', 'Never include this.\n')
        result = self.ws.context('Apps/sample')
        self.assertEqual(len(result['files']), 1)
        self.assertNotIn('Never include', json.dumps(result))
        root_context = self.ws.context()
        self.assertEqual(sum(1 for item in root_context['files'] if 'Read `WORKSPACE-RULES.md`' in item['content']), 1)
        limited = self.ws.context(max_chars=25)
        self.assertTrue(limited['over_budget'])
        self.assertTrue(limited['omitted'])
        self.assertLessEqual(limited['characters'], 25)

    def test_scans_skip_hidden_private_and_dependency_directories(self):
        for name in ['.workspace/log.md', 'private/note.md', 'node_modules/pkg/broken.md', 'Clients/client/brief.md']:
            self.put(name, '[broken](missing.md)\n')
        self.assertTrue(self.ws.doctor()['ok'])
        names = [item['path'] for item in self.ws.map()['files']]
        self.assertFalse(any('node_modules' in name or 'private/' in name or name.startswith('Clients/') for name in names))

    def test_linked_scope_and_linked_descendant_are_rejected(self):
        target = self.root / 'real'
        target.mkdir()
        try:
            (self.root / 'alias').symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('Creating symlinks requires permission on this system')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                                     'New-Item -ItemType Junction -Path $env:WORKSPACE_TEST_LINK -Target $env:WORKSPACE_TEST_TARGET | Out-Null'],
                                    env={**os.environ, 'WORKSPACE_TEST_LINK': str(self.root / 'alias'),
                                         'WORKSPACE_TEST_TARGET': str(target)}, capture_output=True, timeout=15)
            if result.returncode:
                self.skipTest('Neither symbolic links nor junctions can be created on this system')
        with self.assertRaises(ValueError):
            module.Workspace(self.root / 'alias')
        with self.assertRaises(ValueError):
            self.ws.map('alias')
        with self.assertRaises(ValueError):
            self.ws.new_project('alias/new', write=True)
        self.assertIn('unsafe_path', {f['code'] for f in self.ws.doctor()['findings']})

    def test_cli_outputs_json_and_failure_exit(self):
        result = subprocess.run([sys.executable, str(MODULE_PATH), '--root', str(self.root), 'state-hash'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['file'], 'SESSION-STATE.md')
        result = subprocess.run([sys.executable, str(MODULE_PATH), '--root', str(self.root), 'new-project', '../escape', '--write'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_hardlinked_external_state_is_never_read_or_mapped_as_regular_content(self):
        with tempfile.TemporaryDirectory(prefix='outside-workspace-fixture-') as outside:
            original = Path(outside) / 'outside-state.md'
            original.write_text('# Outside information\nMust not enter selected context.\n', encoding='utf-8')
            target = self.root / 'SESSION-STATE.md'
            target.unlink()
            os.link(original, target)
            with self.assertRaises(ValueError):
                self.ws.path('SESSION-STATE.md')
            with self.assertRaises(ValueError):
                self.ws.read(target)
            with self.assertRaises(ValueError):
                self.ws.context()
            with self.assertRaises(ValueError):
                self.ws.state_hash()
            inventory = self.ws.map()
            self.assertFalse(inventory['ok'])
            self.assertIn('SESSION-STATE.md', inventory['unsafe_paths'])
            self.assertNotIn('SESSION-STATE.md', [item['path'] for item in inventory['files']])
            self.assertNotIn('Must not enter selected context', json.dumps(inventory))
            report = self.ws.doctor()
            self.assertIn('unsafe_path', {finding['code'] for finding in report['findings']})

    def test_overview_reads_current_project_notes_and_excludes_templates_examples_and_client_pool(self):
        self.put('Apps/sample/PROJECT.md', '# Example app\n')
        self.put('Apps/sample/SESSION-STATE.md', '# State\n\n## Doing now\nBuild the first screen.\n\n## Next action\nCheck keyboard access.\n\n## Verification\nNot checked yet.\n')
        self.put('Clients/client/PROJECT.md', '# Private scope\n')
        self.put('Clients/client/SESSION-STATE.md', '# State\nDo not read in a root overview.\n')
        self.put('examples/demo/PROJECT.md', '# Demonstration\n')
        self.put('examples/demo/SESSION-STATE.md', '# State\n')
        report = self.ws.overview()
        self.assertEqual([p['path'] for p in report['projects']], ['Apps/sample'])
        self.assertEqual(report['projects'][0]['doing_now'], 'Build the first screen.')
        self.assertEqual(report['projects'][0]['next_action'], 'Check keyboard access.')
        self.assertEqual(report['projects'][0]['verification_note'], 'Not checked yet.')
        self.put('Apps/sample/SESSION-STATE.md', '# State\n\n## Next action\nChanged since the last overview.\n')
        self.assertEqual(self.ws.overview()['projects'][0]['next_action'], 'Changed since the last overview.')
        self.assertEqual(self.ws.overview('examples/demo')['projects'][0]['path'], 'examples/demo')
        self.assertEqual(self.ws.overview('Clients/client')['projects'][0]['path'], 'Clients/client')

    def test_overview_reports_missing_state_without_inventing_status(self):
        self.put('Apps/no-state/PROJECT.md', '# Brief\n')
        project = self.ws.overview()['projects'][0]
        self.assertEqual(project['path'], 'Apps/no-state')
        self.assertEqual(project['state_status'], 'missing')
        self.assertIsNone(project['doing_now'])
        self.assertIsNone(project['verification_note'])


if __name__ == '__main__':
    unittest.main()
