"""Synthetic tests for local task packets; no AI provider is contacted."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('workspace_launcher', TOOLS / 'launch.py')
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='launcher-fixture-')
        self.root = Path(self.temp.name)
        self.put('roles/planner.md', '# Planner\nPlan only the requested work.\n')
        self.put('roles/builder.md', '# Builder\nBuild within the approved scope.\n')
        self.put('roles/reviewer.md', '# Reviewer\nReview the result independently.\n')
        self.routes = {'version': 1, 'departments': {'engineering': {
            'purpose': 'Build a software change.', 'planner': 'roles/planner.md',
            'maker': 'roles/builder.md', 'reviewer': 'roles/reviewer.md',
            'tool_suggestions': ['python', 'git', 'rg']}}}
        self.put('routing.json', json.dumps(self.routes))
        self.put('Apps/sample/PROJECT.md', '# Project\nBuild a local example.\n')
        self.put('Apps/sample/PROJECT-RULES.md', '# Rules\nRead before editing.\n')
        self.put('Apps/sample/SESSION-STATE.md', '# State\n## Next action\nMake the first draft.\n')
        self.put('Apps/unrelated/PROJECT.md', 'UNRELATED PROJECT CONTENT\n')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def packet(self, **kwargs):
        return launch.make_packet(self.root, 'engineering', 'Apps/sample', task='Add a useful example.', **kwargs)

    def test_preview_has_selected_roles_and_context_without_writing(self):
        report = self.packet()
        self.assertTrue(report['ok'])
        self.assertFalse(report['written'])
        self.assertFalse(report['executed'])
        self.assertEqual(report['roles']['maker'], 'roles/builder.md')
        self.assertIn('Build a local example', report['maker_packet'])
        self.assertNotIn('UNRELATED PROJECT CONTENT', json.dumps(report))
        self.assertIn('fresh', report['review_packet'].lower())
        self.assertNotIn('# Builder', report['review_packet'])
        self.assertEqual(report['commands']['context'][-2:], ['--scope', 'Apps/sample'])
        self.assertFalse((self.root / 'Apps/sample/task-packets').exists())

    def test_write_creates_new_project_local_packet_and_refuses_overwrite(self):
        report = self.packet(output='task-packets/first.md', write=True)
        destination = self.root / 'Apps/sample/task-packets/first.md'
        self.assertTrue(report['written'])
        self.assertEqual(destination.read_text(encoding='utf-8'), report['packet'])
        with self.assertRaises(ValueError):
            self.packet(output='task-packets/first.md', write=True)

    def test_unknown_department_missing_role_and_unsafe_route_refuse_before_write(self):
        with self.assertRaises(ValueError):
            launch.make_packet(self.root, 'missing', 'Apps/sample', task='Example')
        self.routes['departments']['engineering']['maker'] = 'roles/missing.md'
        self.put('routing.json', json.dumps(self.routes))
        with self.assertRaises(ValueError):
            self.packet(output='task-packets/no.md', write=True)
        self.routes['departments']['engineering']['maker'] = '../outside.md'
        self.put('routing.json', json.dumps(self.routes))
        with self.assertRaises(ValueError):
            self.packet(output='task-packets/no.md', write=True)
        self.assertFalse((self.root / 'Apps/sample/task-packets').exists())

    def test_output_cannot_escape_selected_project_or_create_invalid_parent(self):
        for output in ['../other.md', '/outside.md', 'new/invalid|name.md', '.git/output.md']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.packet(output=output, write=True)
        self.assertFalse((self.root / 'Apps/sample/new').exists())

    def test_over_budget_context_is_explicit_and_whole_files_only(self):
        report = self.packet(max_chars=10)
        self.assertTrue(report['context']['over_budget'])
        self.assertTrue(report['context']['omitted'])
        self.assertIn('Read the omitted', report['maker_packet'])
        self.assertLessEqual(report['context']['characters'], 10)

    def test_brief_file_must_be_within_selected_project(self):
        self.put('Apps/sample/brief.md', 'Create an accessible first draft.\n')
        report = launch.make_packet(self.root, 'engineering', 'Apps/sample', brief='brief.md')
        self.assertIn('accessible first draft', report['maker_packet'])
        with self.assertRaises(ValueError):
            launch.make_packet(self.root, 'engineering', 'Apps/sample', brief='../unrelated/PROJECT.md')

    def test_hardlinked_role_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='outside-role-fixture-') as outside:
            source = Path(outside) / 'role.md'
            source.write_text('Outside role material', encoding='utf-8')
            (self.root / 'roles/builder.md').unlink()
            os.link(source, self.root / 'roles/builder.md')
            with self.assertRaises(ValueError):
                self.packet()

    def test_role_config_is_data_not_command_execution(self):
        self.routes['departments']['engineering']['command'] = ['unexpected-program']
        self.put('routing.json', json.dumps(self.routes))
        with self.assertRaises(ValueError):
            self.packet()

    def test_cli_lists_routes_and_previews_json(self):
        args = [sys.executable, str(TOOLS / 'launch.py'), '--root', str(self.root)]
        listed = subprocess.run(args + ['--list'], capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout)['departments'][0]['id'], 'engineering')
        result = subprocess.run(args + ['--department', 'engineering', '--project', 'Apps/sample', '--task', 'Make an example.'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['executed'])


if __name__ == '__main__':
    unittest.main()
