"""Read-only tool discovery. No installs, subprocesses, account probes or network calls."""
import json
import shutil
import sys

TOOLS = [
    ('python', 'Core toolkit', ('python', 'python3'), True),
    ('git', 'Version history and project collaboration', ('git',), False),
    ('node', 'JavaScript projects and browser tooling', ('node',), False),
    ('ripgrep', 'Fast scoped file search', ('rg',), False),
    ('uv', 'Optional Python tool installation', ('uv',), False),
    ('github-cli', 'Optional public repository research', ('gh',), False),
    ('playwright-cli', 'Optional browser inspection and interaction', ('playwright-cli',), False),
    ('agent-reach', 'Optional web and platform research', ('agent-reach',), False),
]

def inspect_tools(finder=shutil.which):
    rows = []
    for name, purpose, commands, required in TOOLS:
        found = name == 'python' or any(finder(command) for command in commands)
        rows.append({'tool': name, 'purpose': purpose, 'required_for_core': required,
                     'found_on_path': found, 'runtime_tested': name == 'python',
                     'account_status': 'not_checked'})
    return {'python_supported': sys.version_info >= (3, 11), 'tools': rows,
            'note': 'Presence is not an operational or login check. Optional tools are not required for the core kit. No settings were read or changed.'}

if __name__ == '__main__':
    report = inspect_tools()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report['python_supported'] else 1)
