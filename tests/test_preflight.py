import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).resolve().parents[1] / 'tools/preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

class PreflightTests(unittest.TestCase):
    def test_missing_optional_tools_do_not_block_core(self):
        report = preflight.inspect_tools(lambda command: None)
        self.assertTrue(report['python_supported'])
        self.assertTrue(next(row for row in report['tools'] if row['tool'] == 'python')['found_on_path'])
        self.assertFalse(next(row for row in report['tools'] if row['tool'] == 'git')['found_on_path'])

    def test_tool_paths_are_not_disclosed_and_presence_is_not_runtime_proof(self):
        report = preflight.inspect_tools(lambda command: '/synthetic/private-location/' + command)
        self.assertNotIn('private-location', str(report))
        for row in report['tools']:
            if row['tool'] != 'python':
                self.assertFalse(row['runtime_tested'])

    def test_excluded_media_tools_are_not_probed(self):
        requested = []
        report = preflight.inspect_tools(lambda command: requested.append(command))
        self.assertFalse({'ffmpeg','ffprobe','yt-dlp'} & set(requested))
        self.assertFalse({'ffmpeg','ffprobe','yt-dlp'} & {row['tool'] for row in report['tools']})

if __name__ == '__main__':
    unittest.main()
