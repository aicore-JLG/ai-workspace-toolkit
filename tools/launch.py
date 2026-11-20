#!/usr/bin/env python3
"""Prepare a scoped task packet. No provider, subprocess or agent is launched."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from workspace import Workspace, digest

ROLE_FIELDS = ('planner', 'maker', 'reviewer')
ROUTE_FIELDS = {'purpose', *ROLE_FIELDS, 'tool_suggestions'}


def routes_for(workspace):
    data, text = workspace.read(workspace.path('routing.json'))
    try:
        config = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError('routing.json must contain valid JSON.') from exc
    if (not isinstance(config, dict) or set(config) != {'version', 'departments'}
            or config.get('version') != 1 or not isinstance(config.get('departments'), dict)
            or not 1 <= len(config['departments']) <= 30):
        raise ValueError('Unsupported routing configuration; expected version 1 and departments.')
    for name, route in config['departments'].items():
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', name):
            raise ValueError('Department identifiers must be short lowercase names.')
        if not isinstance(route, dict) or set(route) != ROUTE_FIELDS:
            raise ValueError('A route must declare purpose, planner, maker, reviewer and tool_suggestions only.')
        if not isinstance(route['purpose'], str) or not 1 <= len(route['purpose']) <= 500:
            raise ValueError('Each route needs a short purpose.')
        for field in ROLE_FIELDS:
            value = route[field]
            if not isinstance(value, str) or not re.fullmatch(r'roles/[a-z][a-z0-9-]{0,50}\.md', value):
                raise ValueError('Role paths must name Markdown files directly inside roles/.')
        if route['maker'] == route['reviewer']:
            raise ValueError('Maker and reviewer must have different role files.')
        suggestions = route['tool_suggestions']
        if (not isinstance(suggestions, list) or len(suggestions) > 20
                or any(not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9@._/-]{1,80}', value) for value in suggestions)):
            raise ValueError('Tool suggestions must be short tool names, not commands.')
    return config['departments'], digest(data)


def list_departments(root):
    workspace = Workspace(root)
    routes, identity = routes_for(workspace)
    return {'ok': True, 'executed': False, 'routing_sha256': identity,
            'departments': [{'id': name, **route} for name, route in routes.items()],
            'note': 'These presets prepare prompts; they do not start independent agents or install suggested tools.'}


def make_packet(root, department, project, *, task=None, brief=None, max_chars=12000, output=None, write=False):
    workspace = Workspace(root)
    routes, routing_hash = routes_for(workspace)
    if department not in routes:
        raise ValueError('Unknown department. Use --list to see configured presets.')
    if bool(task is not None) == bool(brief is not None):
        raise ValueError('Supply exactly one task string or project-relative brief file.')
    scope = workspace.path(project)
    if not scope.is_dir() or scope == workspace.root:
        raise ValueError('Select one project directory, not the entire workspace.')
    selected = Workspace(scope)
    selected.path('PROJECT.md')
    selected.path('PROJECT-RULES.md')
    selected.path('SESSION-STATE.md')
    if brief is not None:
        brief_path = selected.path(brief)
        if brief_path.suffix.lower() not in {'.md', '.txt'}:
            raise ValueError('Brief must be a local Markdown or text file in the selected project.')
        _, task = selected.read(brief_path)
    if (not isinstance(task, str) or not task.strip() or len(task) > 12000
            or any(ord(char) < 32 and char not in '\n\r\t' for char in task)):
        raise ValueError('Task must contain 1 to 12000 text characters.')
    route = routes[department]
    role_text, role_hashes = {}, {}
    for field in ROLE_FIELDS:
        data, text = workspace.read(workspace.path(route[field]))
        if not text.strip() or len(text) > 16000:
            raise ValueError('Role files must contain 1 to 16000 text characters.')
        role_text[field], role_hashes[field] = text, digest(data)
    context = workspace.context(workspace.relative(scope), max_chars)
    context_text = '\n\n'.join('### ' + item['path'] + '\n\n' + item['content'].strip() for item in context['files'])
    omitted = ('\n\nRead the omitted instruction files in full before doing work: ' + ', '.join(context['omitted']) + '.\n') if context['omitted'] else ''
    scope_name = workspace.relative(scope)
    maker = ('## Maker session\n\nOpen the selected project `' + scope_name + '` in your own AI tool. '
             'This packet does not grant access to other projects or authorise sending, publication, spending or installation.\n\n'
             'Role and workflow file references are relative to the kit root, not the selected project. '
             'Supply only the selected role\'s relevant workflow from the kit; do not load the entire workflow library. '
             'Run the listed helper commands from the kit root.\n\n'
             '### Original task\n\n' + task.strip() + '\n\n'
             '### Planning guidance\n\n' + role_text['planner'].strip() + '\n\n'
             '### Maker guidance\n\n' + role_text['maker'].strip() + '\n\n'
             '### Selected project context\n\n' + context_text + omitted + '\n\n'
             'Produce the requested result and report actual checks, remaining issues and files changed. '
             'Do not claim a separate review until it has actually happened.\n')
    review = ('## Separate review session\n\nStart a fresh session or an explicitly separate reviewer if your tool supports one. '
              'Provide only this review brief, the final artifact, relevant project requirements and acceptance criteria. '
              'Do not provide the maker\'s reasoning or a suggested verdict. Starting a new session alone does not prove independence.\n\n'
              'Role, workflow and project file references in this brief are relative to the kit root. '
              'Supply only the requirements and workflow relevant to the selected project.\n\n'
              '### Original task\n\n' + task.strip() + '\n\n'
              '### Reviewer guidance\n\n' + role_text['reviewer'].strip() + '\n\n'
              'Read the project brief at `' + scope_name + '/PROJECT.md` and the project rules at `' + scope_name +
              '/PROJECT-RULES.md`. Ask for the final artifact if it has not been supplied. '
              'Return concrete findings with evidence. Keep untested behaviour explicit. '
              'This packet has not performed a review.\n')
    maker = maker.replace('\r\n', '\n').replace('\r', '\n')
    review = review.replace('\r\n', '\n').replace('\r', '\n')
    packet = ('# Local task packet\n\nDepartment: ' + department + '\n\nProject: `' + scope_name +
              '`\n\nThis is a prompt launcher, not an agent service or execution receipt. '
              'Use the two sections in their respective sessions. Project content may be private.\n\n' + maker + '\n' + review)
    commands = {
        'context': ['python', '-B', 'tools/workspace.py', 'context', '--scope', scope_name],
        'doctor': ['python', '-B', 'tools/workspace.py', 'doctor', '--scope', scope_name],
        'overview': ['python', '-B', 'tools/workspace.py', 'overview', '--scope', scope_name],
    }
    result = {'ok': True, 'executed': False, 'written': False,
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'department': department, 'project': scope_name,
              'roles': {field: route[field] for field in ROLE_FIELDS}, 'role_sha256': role_hashes,
              'routing_sha256': routing_hash, 'tool_suggestions': route['tool_suggestions'],
              'context': context, 'commands': commands,
              'maker_packet': maker, 'review_packet': review, 'packet': packet,
              'packet_sha256': digest(packet.encode('utf-8')),
              'note': 'No tool, account, AI provider or independent agent was started. Run listed commands from the kit root. Review freshness is a user workflow, not enforced by this launcher.'}
    destination = None
    if output is not None:
        destination = selected.path(output, exists=False)
        if destination.suffix.lower() != '.md':
            raise ValueError('Save the task packet as a new Markdown file inside the selected project.')
        if destination.exists():
            raise ValueError('Output already exists; choose a new filename.')
        result['output'] = workspace.relative(destination)
    if write:
        if destination is None:
            raise ValueError('--write requires a new project-relative --output filename.')
        selected.path(output, exists=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        selected.path(output, exists=False)
        try:
            with destination.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(packet)
        except FileExistsError as exc:
            raise ValueError('Output appeared during preparation; it was not overwritten.') from exc
        result['written'] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).absolute().parent.parent))
    parser.add_argument('--list', action='store_true', help='List configured department presets without launching anything')
    parser.add_argument('--department')
    parser.add_argument('--project', help='One project relative to the kit root')
    brief = parser.add_mutually_exclusive_group()
    brief.add_argument('--task')
    brief.add_argument('--brief', help='Markdown/text file relative to the selected project')
    parser.add_argument('--max-chars', type=int, default=12000, help='Whole-file project context budget')
    parser.add_argument('--output', help='New Markdown filename relative to the selected project')
    parser.add_argument('--write', action='store_true', help='Save the packet; preview is the default')
    args = parser.parse_args(argv)
    try:
        if args.list:
            if args.write or args.output:
                raise ValueError('--list cannot write an output packet.')
            result = list_departments(args.root)
        else:
            if not args.department or not args.project:
                raise ValueError('Select --department and --project, or use --list.')
            result = make_packet(args.root, args.department, args.project, task=args.task, brief=args.brief,
                                 max_chars=args.max_chars, output=args.output, write=args.write)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except ValueError as exc:
        print(json.dumps({'ok': False, 'executed': False, 'error': str(exc)}))
        return 1
    except OSError as exc:
        print(json.dumps({'ok': False, 'executed': False, 'error': 'Filesystem operation failed: ' + type(exc).__name__ + '. Inspect any newly created output.'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
