"""Synthetic project walls and bounded prompt snapshots; never real client data."""
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))


class ClientScopeTests(unittest.TestCase):
    def setUp(self):
        self.scope = importlib.import_module('client_scope')
        self.temp = tempfile.TemporaryDirectory(prefix='client-scope-test-')
        self.addCleanup(self.temp.cleanup)
        self.kit = Path(self.temp.name)
        self.project = self.make_project('Clients/alpha/site')
        self.other = self.make_project('Clients/beta/site')
        (self.project/'app.py').write_text('result = 42\n', encoding='utf-8')
        (self.other/'private.txt').write_text('SYNTHETIC_OTHER_CLIENT', encoding='utf-8')

    def make_project(self, relative):
        root = self.kit/relative
        root.mkdir(parents=True, exist_ok=True)
        for name in ('PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md', 'AGENTS.md', 'CLAUDE.md'):
            (root/name).write_text('# Synthetic ' + name + '\n', encoding='utf-8')
        return root

    def test_exact_client_project_contains_only_scoped_inputs_and_rules(self):
        selected = self.scope.select_project(self.kit, 'Clients/alpha/site')
        self.assertEqual(selected, self.project)
        with patch.object(Path, 'iterdir', side_effect=AssertionError('No directory scans')), \
             patch.object(Path, 'rglob', side_effect=AssertionError('No recursive scans')):
            result = self.scope.snapshot(selected, ['app.py'], kit_root=self.kit)
        self.assertEqual(set(result['files']), {'PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md', 'AGENTS.md', 'CLAUDE.md', 'app.py'})
        self.assertEqual(result['files']['app.py']['sha256'], hashlib.sha256((self.project/'app.py').read_bytes()).hexdigest())
        self.assertNotIn('SYNTHETIC_OTHER_CLIENT', repr(result))
        self.assertNotIn(str(self.project), repr(result))
        self.assertTrue(result['ancestor_rules_checked'])

    def test_explicit_synthetic_example_project_is_allowed_but_pool_is_not(self):
        project = self.make_project('examples/orchestration-project')
        self.assertEqual(self.scope.select_project(self.kit, 'examples/orchestration-project'), project)
        self.assertTrue(self.scope.snapshot(project, [], kit_root=self.kit)['ancestor_rules_checked'])
        with self.assertRaises(ValueError):
            self.scope.select_project(self.kit, 'examples')

    def test_ancestor_rules_are_scoped_separate_and_fingerprint_bound(self):
        (self.kit/'WORKSPACE-RULES.md').write_text('Workspace rules', encoding='utf-8')
        (self.kit/'Clients/AGENTS.md').write_text('Category rules', encoding='utf-8')
        (self.kit/'Clients/alpha/CLAUDE.md').write_text('Alpha rules', encoding='utf-8')
        (self.kit/'Clients/beta/CLAUDE.md').write_text('SYNTHETIC_OTHER_CLIENT', encoding='utf-8')
        before = self.scope.snapshot(self.project, ['app.py'], kit_root=self.kit)
        self.assertEqual(set(before['parent_rules']), {'WORKSPACE-RULES.md', 'Clients/AGENTS.md', 'Clients/alpha/CLAUDE.md'})
        self.assertNotIn('SYNTHETIC_OTHER_CLIENT', repr(before))
        (self.kit/'Clients/alpha/CLAUDE.md').write_text('Updated alpha rules', encoding='utf-8')
        after = self.scope.snapshot(self.project, ['app.py'], kit_root=self.kit)
        self.assertNotEqual(before['fingerprint'], after['fingerprint'])
        self.assertEqual(before['scope'], after['scope'])
        local_only = self.scope.snapshot(self.project, ['app.py'])
        self.assertFalse(local_only['ancestor_rules_checked'])
        self.assertEqual(local_only['parent_rules'], {})

    def test_scope_identity_changes_when_project_is_copied(self):
        target = self.kit/'Apps/copy'
        shutil.copytree(self.project, target)
        before = self.scope.snapshot(self.project, ['app.py'])
        after = self.scope.snapshot(target, ['app.py'])
        self.assertEqual(before['files'], after['files'])
        self.assertNotEqual(before['scope'], after['scope'])
        self.assertNotEqual(before['fingerprint'], after['fingerprint'])

    def test_workspace_categories_client_roots_and_pools_cannot_be_selected(self):
        for relative in ('', '.', 'Clients', 'Clients/alpha', 'Apps', 'templates/project', 'integrations/vendor', 'Apps/shared', 'Systems/pools'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                self.scope.select_project(self.kit, relative)
        # Adding project-looking files to a client container does not make it a project.
        self.make_project('Clients/alpha')
        with self.assertRaises(ValueError):
            self.scope.select_project(self.kit, 'Clients/alpha')

    def test_project_markers_and_at_least_one_host_entry_are_required(self):
        for name in ('PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md'):
            original = (self.project/name).read_bytes()
            (self.project/name).unlink()
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.select_project(self.kit, 'Clients/alpha/site')
            (self.project/name).write_bytes(original)
        (self.project/'CLAUDE.md').unlink()
        self.scope.select_project(self.kit, 'Clients/alpha/site')
        (self.project/'AGENTS.md').unlink()
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, [])

    def test_nested_projects_are_neither_selectable_nor_readable_or_writable(self):
        nested = self.make_project('Clients/alpha/site/embedded')
        (nested/'code.py').write_text('nested = True', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.scope.select_project(self.kit, 'Clients/alpha/site/embedded')
        for name in ('embedded/code.py', 'embedded/PROJECT.md', 'embedded/new.txt'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.snapshot(self.project, [name])
            with self.subTest(output=name), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, [name])

    def test_traversal_absolute_sibling_and_ambiguous_paths_are_rejected(self):
        invalid = ['../beta/site', 'Clients/alpha/site/../site', str(self.project),
                   'Clients\\alpha\\site', 'Clients/alpha/site/', 'Clients//alpha/site']
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.scope.select_project(self.kit, value)
        invalid_files = ['../private.txt', '../../beta/site/private.txt', str(self.other/'private.txt'),
                         'app.py:secret', 'sub/../app.py', 'bad|name.py', 'NUL.txt', 'x./a.py', 'a\\b.py']
        for name in invalid_files:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.snapshot(self.project, [name])
            with self.subTest(output=name), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, [name])

    def test_credential_dependency_runtime_paths_are_rejected(self):
        names = ['.env', '.env.example', 'auth.json', 'token.json', '.git/config',
                 '.workspace/runs/log.txt', 'node_modules/pkg/a.js', 'vendor/a.py',
                 '.venv/lib/a.py', '.claude/settings.json', 'Memory/curated.json', 'secrets.txt']
        for name in names:
            target = self.project/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('synthetic', encoding='utf-8')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.snapshot(self.project, [name])
            with self.subTest(output=name), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, [name])

    def test_outputs_cannot_modify_instructions_checks_or_security_policy(self):
        names = ['AGENTS.md', 'CLAUDE.md', 'PROJECT.md', 'PROJECT-RULES.md', 'SESSION-STATE.md',
                 'WORKSPACE-RULES.md', 'checks.json', 'run.json', 'routing.json',
                 'config/orchestration.json', 'Security/policy.md', 'src/AGENTS.md', 'src/checks.json']
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, [name])
        self.assertEqual(self.scope.output_paths(self.project, ['app.py', 'src/new.py']), ['app.py', 'src/new.py'])
        self.assertFalse((self.project/'src').exists())

    def test_outputs_cannot_rewrite_tests_or_dependency_execution_configuration(self):
        names = ['tests/test_feature.py', 'test/fixtures.json', '__tests__/example.js',
                 'check.py', 'check_app.py', 'test_feature.py', 'feature_test.py',
                 'src/view.test.tsx', 'src/view.spec.js', 'conftest.py', 'pytest.ini',
                 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock',
                 'pyproject.toml', 'setup.py', 'requirements-dev.txt', 'uv.lock']
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, [name])
        self.assertEqual(self.scope.output_paths(self.project, ['src/feature.py']), ['src/feature.py'])

    def test_nested_input_and_new_output_ancestor_rules_are_explicit(self):
        source = self.project/'src'
        source.mkdir()
        (source/'app.py').write_text('result = 1', encoding='utf-8')
        (source/'AGENTS.md').write_text('Nested source rules', encoding='utf-8')
        target = self.project/'frontend'
        target.mkdir()
        (target/'CLAUDE.md').write_text('Nested frontend rules', encoding='utf-8')
        sibling = self.project/'unselected'
        sibling.mkdir()
        (sibling/'AGENTS.md').write_text('DO_NOT_INCLUDE_UNSELECTED_RULES', encoding='utf-8')
        result = self.scope.snapshot(self.project, ['src/app.py'], kit_root=self.kit,
                                     rule_paths=['frontend/new/view.js'])
        self.assertIn('src/AGENTS.md', result['rule_files'])
        self.assertIn('frontend/CLAUDE.md', result['rule_files'])
        self.assertIn('PROJECT-RULES.md', result['rule_files'])
        self.assertNotIn('src/app.py', result['rule_files'])
        self.assertEqual(result['files']['frontend/CLAUDE.md']['content'], 'Nested frontend rules')
        self.assertNotIn('DO_NOT_INCLUDE_UNSELECTED_RULES', repr(result))
        self.assertFalse((target/'new').exists())
        before = result['fingerprint']
        (source/'AGENTS.md').write_text('Revised nested source rules', encoding='utf-8')
        self.assertNotEqual(before, self.scope.snapshot(self.project, ['src/app.py'], kit_root=self.kit,
                                                      rule_paths=['frontend/new/view.js'])['fingerprint'])

    def test_duplicate_case_and_ancestor_overlapping_outputs_are_rejected(self):
        for names in (['app.py', 'APP.py'], ['src/new.py', 'SRC/new.py'], ['folder', 'folder/file.py']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.scope.output_paths(self.project, names)
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['app.py', 'APP.py'])

    def test_non_utf8_controls_and_recognizable_secret_content_fail_without_echo(self):
        fixtures = [b'\xff\xfe', b'hello\x00world', b'bad\x1bcontrol',
                    b'api_key = "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"',
                    b'-----BEGIN PRIVATE KEY-----\nprivate\n',
                    b'{"password":"synthetic-password-value"}']
        for raw in fixtures:
            (self.project/'input.txt').write_bytes(raw)
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError) as caught:
                    self.scope.snapshot(self.project, ['input.txt'])
                decoded = raw.decode('utf-8', errors='ignore')
                if decoded:
                    self.assertNotIn(decoded, str(caught.exception))

    def test_size_limits_fail_whole_packet_without_silent_truncation(self):
        (self.project/'large.txt').write_text('x'*1025, encoding='utf-8')
        with patch.object(self.scope, 'MAX_FILE_BYTES', 1024), self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['large.txt'])
        (self.project/'large.txt').write_text('x'*900, encoding='utf-8')
        with patch.object(self.scope, 'MAX_TOTAL_BYTES', 920), self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['large.txt'])

    def test_shared_output_text_validator_refuses_secrets_and_preserves_plain_text(self):
        text = 'A focused summary.\n\tNo provider calls were made.\n'
        self.assertEqual(self.scope.validate_text(text), text)
        self.assertEqual(self.scope.validate_text('api_key = "YOUR_API_KEY"'), 'api_key = "YOUR_API_KEY"')
        for value in ('token\x00value', 'ghp_' + 'a'*30, 'password = "real-shaped-value"', 'x'*(self.scope.MAX_FILE_BYTES+1), b'not text'):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                self.scope.validate_text(value)

    def test_parent_secret_and_outside_kit_are_refused(self):
        (self.kit/'Clients/alpha/AGENTS.md').write_text('password = "private-shaped-value"', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['app.py'], kit_root=self.kit)
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['app.py'], kit_root=self.other)

    def test_reported_reparse_directory_is_rejected_before_source_read(self):
        from types import SimpleNamespace
        target = self.project/'reparse'
        target.mkdir()
        (target/'data.txt').write_text('SYNTHETIC_JUNCTION_TARGET', encoding='utf-8')
        original = Path.lstat
        def attributes(path):
            info = original(path)
            if path == target:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        with patch.object(Path, 'lstat', attributes):
            with self.assertRaises(ValueError):
                self.scope.snapshot(self.project, ['reparse/data.txt'])
            with self.assertRaises(ValueError):
                self.scope.output_paths(self.project, ['reparse/new.txt'])

    def test_hardlinked_source_and_output_are_refused(self):
        target = self.project/'hardlink.txt'
        try:
            os.link(self.other/'private.txt', target)
        except OSError:
            self.skipTest('Hard links unavailable')
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['hardlink.txt'])
        with self.assertRaises(ValueError):
            self.scope.output_paths(self.project, ['hardlink.txt'])

    def test_symlinked_project_or_nested_directory_cannot_cross_clients(self):
        alias = self.kit/'Clients/alpha/alias'
        try:
            alias.symlink_to(self.other, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink permission unavailable')
        with self.assertRaises(ValueError):
            self.scope.select_project(self.kit, 'Clients/alpha/alias')
        (self.project/'linked').symlink_to(self.other, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.scope.snapshot(self.project, ['linked/private.txt'])
        with self.assertRaises(ValueError):
            self.scope.output_paths(self.project, ['linked/new.py'])


if __name__ == '__main__':
    unittest.main()
