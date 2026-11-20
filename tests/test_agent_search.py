import importlib.util
import subprocess
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('agent_search', Path(__file__).resolve().parents[1] / 'tools/agent_search.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AgentSearchTests(unittest.TestCase):
    def test_github_unicode_decodes_as_utf8(self):
        def fake(command, **kwargs):
            self.assertEqual(kwargs.get('encoding'), 'utf-8')
            return subprocess.CompletedProcess(command, 0, '[]', '')
        self.assertEqual(module.search('tools', run=True, runner=fake)['results'], [])

    def test_preview_does_not_execute(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('preview called a process')
        result = module.search('browser agent', 4, run=False, runner=forbidden)
        self.assertFalse(result['executed'])
        self.assertIn('--visibility=public', result['command'])

    def test_private_or_unknown_visibility_is_never_reported(self):
        rows = [dict(fullName='example/public', isPrivate=False, visibility='public', stargazersCount=1, license=None),
                dict(fullName='example/private', isPrivate=True, visibility='private'),
                dict(fullName='example/unknown')]
        import json
        def fake(*args, **kwargs):
            self.assertFalse(kwargs['shell'])
            return subprocess.CompletedProcess(args[0], 0, json.dumps(rows), '')
        result = module.search('tools', 5, run=True, runner=fake)
        self.assertEqual([r['repository'] for r in result['results']], ['example/public'])
        self.assertEqual(result['withheld'], 2)

    def test_rejects_query_options_and_visibility_override(self):
        for query in ['--web', 'tools visibility:private', 'tools is:private', 'a\nb']:
            with self.assertRaises(ValueError):
                module.search(query, 5)
        for limit in [0, 51, -1]:
            with self.assertRaises(ValueError):
                module.search('tools', limit)

    def test_provider_failure_does_not_echo_sensitive_output(self):
        def fake(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, '', 'synthetic confidential details')
        with self.assertRaisesRegex(RuntimeError, 'GitHub CLI failed') as caught:
            module.search('tools', 5, run=True, runner=fake)
        self.assertNotIn('confidential', str(caught.exception))

if __name__ == '__main__':
    unittest.main()
