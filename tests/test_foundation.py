import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from foundation import load_policy


class PolicyTests(unittest.TestCase):
    def test_safe_defaults_and_actual_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policy = load_policy(root)
            self.assertEqual(policy['execution']['timeout_seconds'], 120)
            (root / 'config').mkdir()
            policy['execution']['timeout_seconds'] = 3
            (root / 'config/foundation.json').write_text(json.dumps(policy))
            self.assertEqual(load_policy(root)['execution']['timeout_seconds'], 3)

    def test_invalid_or_unsupported_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config').mkdir()
            for field, value in [('timeout_seconds', True), ('timeout_seconds', 601), ('max_output_bytes', 0)]:
                policy = {'schema_version': 1, 'execution': {'timeout_seconds': 120, 'max_output_bytes': 65536}, 'maintenance': {'state_line_limit': 150}}
                policy['execution'][field] = value
                (root / 'config/foundation.json').write_text(json.dumps(policy))
                with self.assertRaises(ValueError):
                    load_policy(root)
            (root / 'config/foundation.json').write_text('{"paid_runs_enabled": true}')
            with self.assertRaises(ValueError):
                load_policy(root)


class HealthTests(unittest.TestCase):
    def test_passing_partial_check_is_not_ready(self):
        from health import inspect_project
        import session
        import verify
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'PROJECT.md').write_text('Project')
            (root/'SESSION-STATE.md').write_text('Ready')
            (root/'a.py').write_text('pass')
            (root/'b.py').write_text('untested')
            (root/'checks.json').write_text(json.dumps({'command':['{python}','a.py'], 'inputs':['a.py']}))
            session.start(root, 'Check project', ['A and B work'], ['a.py','b.py'])
            self.assertEqual(verify.run_check(root, 'checks.json')[1], 0)
            report = inspect_project(root, root)
            self.assertFalse(report['ready'])
            self.assertIn('session_check_incomplete_coverage', [r['code'] for r in report['findings']])

    def test_read_only_audit_exposes_missing_setup_without_memory_values(self):
        from health import inspect_project
        from memory import MemoryStore
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'PROJECT.md').write_text('Project A')
            (root / 'SESSION-STATE.md').write_text('old line\n' * 151)
            MemoryStore(root).propose('color', 'PRIVATE_SAMPLE_VALUE', 'Owner decision')
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            report = inspect_project(root, root)
            self.assertFalse(report['ready'])
            self.assertEqual(report['verification'], 'unconfigured')
            self.assertEqual(report['memory']['pending_sample_count'], 1)
            self.assertNotIn('PRIVATE_SAMPLE_VALUE', json.dumps(report))
            self.assertIn('state_compaction', [r['code'] for r in report['findings']])
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})
