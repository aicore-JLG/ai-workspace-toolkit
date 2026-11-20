#!/usr/bin/env python3
"""Scoped local workspace utilities. Python 3.11+, no third-party packages.

No command executes code, installs tools, contacts services or scans the home folder.
Filesystem checks and the compaction lock protect ordinary cooperative use; they
are not an operating-system sandbox against hostile concurrent filesystem changes.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {'node_modules', '__pycache__', 'venv', 'dist', 'build', 'out',
             'coverage', 'target', 'private', 'secrets', 'clients', 'session-history', 'vendor'}
TEXT_EXTENSIONS = {'.md', '.txt', '.json', '.py', '.html', '.css', '.js', '.mjs', '.toml', '.yml', '.yaml'}
CONTEXT_FILES = ('AGENTS.md', 'CLAUDE.md', 'WORKSPACE-RULES.md', 'PROJECT-RULES.md',
                 'PROJECT.md', 'SESSION-STATE.md', 'WHERE-THINGS-LIVE.md')
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 2000
MAX_DEPTH = 12


def validate_component(name):
    """Reject non-portable components before any filesystem mutation."""
    if name in {'', '.'}:
        return
    if (name.endswith((' ', '.')) or re.search(r'[<>:"|?*]', name)
            or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in name)):
        raise ValueError('Path contains an invalid or non-portable component name.')
    if len(name.encode('utf-8')) > 255 or len(name.encode('utf-16-le')) // 2 > 255:
        raise ValueError('Path component is too long for a portable workspace.')
    basename = name.split('.', 1)[0].rstrip(' .')
    if re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9\u00b9\u00b2\u00b3]|LPT[1-9\u00b9\u00b2\u00b3])', basename, re.IGNORECASE):
        raise ValueError('Reserved device names cannot be used in workspace paths.')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def linked(path):
    info = path.lstat()
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, 'st_file_attributes', 0) & 0x400)
            or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1))


def check_ancestors(path):
    """Inspect the spelling supplied, before resolve could hide a link."""
    for item in [*reversed(path.parents), path]:
        if item.exists() or item.is_symlink():
            if linked(item):
                raise ValueError('Symbolic links, hardlinked files and reparse-point paths are not supported.')


class Workspace:
    def __init__(self, root):
        original = Path(os.path.abspath(os.fspath(root)))
        check_ancestors(original)
        if not original.is_dir():
            raise ValueError('The selected workspace root must be an existing directory.')
        self.root = original.resolve()

    def path(self, relative='.', *, exists=True, allow_history=False, allow_hidden=False):
        raw = str(relative).replace('\\', '/')
        if not raw or '\x00' in raw or ':' in raw or raw.startswith('/') or PureWindowsPath(raw).is_absolute():
            raise ValueError('Use a relative path inside the selected workspace.')
        parts = raw.split('/')
        if '..' in parts:
            raise ValueError('Parent traversal is not permitted in command paths.')
        for part in parts:
            validate_component(part)
        forbidden = {'private', 'secrets', 'node_modules', '__pycache__', 'venv'}
        if any((part.startswith('.') and part != '.' and not allow_hidden) or part.lower() in forbidden for part in parts):
            raise ValueError('Hidden, private and dependency paths are excluded.')
        if not allow_history and 'session-history' in [part.lower() for part in parts]:
            raise ValueError('Historical records are outside the current-work scope.')
        path = self.root.joinpath(*parts)
        check_ancestors(path)
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Path escapes the selected workspace.')
        if exists and not path.exists():
            raise ValueError('Requested path does not exist inside the selected workspace.')
        return path

    def relative(self, path):
        return path.relative_to(self.root).as_posix()

    def read(self, path):
        check_ancestors(path)
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('Expected a regular text file no larger than 1 MB.')
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES or b'\x00' in data:
            raise ValueError('File is too large or contains binary data.')
        try:
            return data, data.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Expected UTF-8 text.') from exc

    def scan(self, scope='.'):
        selected = self.path(scope)
        if not selected.is_dir():
            raise ValueError('Scope must name a directory.')
        files, skipped, unsafe = [], set(), []
        entries_seen = 0

        def visit(folder, depth):
            nonlocal entries_seen
            if depth > MAX_DEPTH:
                raise ValueError('Scope exceeds the depth limit; select a smaller project.')
            for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
                entries_seen += 1
                if entries_seen > 10000:
                    raise ValueError('Scope exceeds the entry limit; select a smaller project.')
                if path.name.startswith('.') or path.name.casefold() in SKIP_DIRS:
                    skipped.add(self.relative(path))
                    continue
                if linked(path):
                    unsafe.append(self.relative(path))
                    continue
                if path.is_dir():
                    visit(path, depth + 1)
                elif path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
                    files.append(path)
                    if len(files) > MAX_FILES:
                        raise ValueError('Scope exceeds the file limit; select a smaller project.')
        visit(selected, 0)
        return files, sorted(skipped), unsafe

    def map(self, scope='.'):
        files, skipped, unsafe = self.scan(scope)
        return {'ok': not unsafe, 'scope': scope, 'files': [
            {'path': self.relative(p), 'bytes': p.stat().st_size} for p in files],
            'skipped': skipped, 'unsafe_paths': unsafe,
            'note': 'Names and sizes only. Hidden, private, client pools, history and dependency folders are skipped; select an authorised project explicitly.'}

    def overview(self, scope='.'):
        """Read current project handoffs, not a separately maintained status table."""
        selected = self.path(scope)
        files, skipped, unsafe = self.scan(scope)
        projects = []
        excluded_roots = {'templates', 'examples', 'docs', 'roles', 'tools', 'tests', 'knowledge'}

        def section(text, headings):
            active, lines = False, []
            for line in text.splitlines():
                if line.startswith('#'):
                    if active:
                        break
                    active = line.lstrip('#').strip().casefold() in headings
                    continue
                if active and line.strip():
                    lines.append(line.strip())
            return '\n'.join(lines)[:500] or None

        for brief in files:
            if brief.name != 'PROJECT.md':
                continue
            if selected == self.root and brief.relative_to(self.root).parts[0].casefold() in excluded_roots:
                continue
            project = brief.parent
            state = project / 'SESSION-STATE.md'
            item = {'path': self.relative(project), 'brief': self.relative(brief),
                    'state_status': 'missing', 'doing_now': None, 'next_action': None,
                    'blockers': None, 'verification_note': None, 'state_sha256': None}
            if state.exists() or state.is_symlink():
                try:
                    data, text = self.read(state)
                    item.update(state_status='present', state_sha256=digest(data),
                                doing_now=section(text, {'doing now', 'current work'}),
                                next_action=section(text, {'next action', 'next step', 'next steps'}),
                                blockers=section(text, {'blockers', 'waiting on you', 'waiting on me'}),
                                verification_note=section(text, {'verification', 'checks'}))
                except (ValueError, OSError):
                    item['state_status'] = 'unsafe_or_unreadable'
            projects.append(item)
        return {'ok': not unsafe and all(p['state_status'] != 'unsafe_or_unreadable' for p in projects),
                'scope': scope, 'generated_at': datetime.now(timezone.utc).isoformat(),
                'projects': projects, 'skipped': skipped, 'unsafe_paths': unsafe,
                'note': 'Live local handoff summaries, not verified service health. Root overview excludes templates, examples and client pools; explicitly select an authorised project when needed. Notes may be private.'}

    def context(self, scope='.', max_chars=12000):
        if not 1 <= max_chars <= 100000:
            raise ValueError('Context budget must be between 1 and 100000 characters.')
        selected = self.path(scope)
        if not selected.is_dir():
            raise ValueError('Scope must name a directory.')
        files, omitted, duplicates, seen = [], [], [], set()
        characters = 0
        for name in CONTEXT_FILES:
            path = selected / name
            if not path.exists() and not path.is_symlink():
                continue
            data, content = self.read(path)
            identity = digest(data)
            if identity in seen:
                duplicates.append(self.relative(path))
                continue
            seen.add(identity)
            if characters + len(content) > max_chars:
                omitted.append(self.relative(path))
                continue
            files.append({'path': self.relative(path), 'content': content})
            characters += len(content)
        return {'ok': True, 'scope': scope, 'files': files, 'characters': characters,
                'max_characters': max_chars, 'over_budget': bool(omitted), 'omitted': omitted,
                'duplicate_content_omitted': duplicates,
                'note': 'Whole files only; omitted instructions must be read separately before work. This output is local context, not automatically safe to share.'}

    def doctor(self, scope='.'):
        files, skipped, unsafe = self.scan(scope)
        findings = [{'code': 'unsafe_path', 'file': name, 'severity': 'error'} for name in unsafe]
        checked_links = 0
        for path in files:
            if path.suffix.lower() != '.md':
                continue
            try:
                data, content = self.read(path)
            except ValueError:
                findings.append({'code': 'unreadable_text', 'file': self.relative(path), 'severity': 'error'})
                continue
            if path.name in CONTEXT_FILES and len(content) > 12000:
                findings.append({'code': 'large_context_file', 'file': self.relative(path),
                                 'characters': len(content), 'severity': 'warning'})
            in_fence = False
            for line_number, line in enumerate(content.splitlines(), 1):
                if re.match(r'^\s*(```|~~~)', line):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                clean = re.sub(r'`[^`]*`', '', line)
                targets = [(value, 'link') for value in re.findall(r'\[[^\]]*\]\(([^)]+)\)', clean)]
                if path.name in {'AGENTS.md', 'CLAUDE.md'}:
                    targets += [(value, 'entry_reference') for value in re.findall(r'`([^`\s]+\.(?:md|json))`', line)
                                if not re.search(r'[<>{}*]', value)]
                for target, kind in targets:
                    target = target.strip()
                    if target.startswith('<') and '>' in target:
                        target = target[1:target.index('>')]
                    else:
                        target = target.split(' "', 1)[0]
                    parsed = urlsplit(target)
                    if parsed.scheme in {'http', 'https', 'mailto'} or not parsed.path:
                        continue
                    checked_links += 1
                    decoded = unquote(parsed.path).replace('\\', '/')
                    try:
                        if parsed.scheme or decoded.startswith('/') or ':' in decoded:
                            raise ValueError('Absolute link')
                        absolute = Path(os.path.abspath(path.parent / decoded))
                        relative = absolute.relative_to(self.root).as_posix()
                        candidate = self.path(relative, exists=False, allow_history=True, allow_hidden=True)
                        if not candidate.exists():
                            findings.append({'code': 'missing_' + kind, 'file': self.relative(path),
                                             'line': line_number, 'target': target, 'severity': 'error'})
                    except (ValueError, OSError):
                        findings.append({'code': 'unsafe_link', 'file': self.relative(path),
                                         'line': line_number, 'severity': 'error'})
        return {'ok': not any(f['severity'] == 'error' for f in findings), 'scope': scope,
                'markdown_files_checked': sum(p.suffix.lower() == '.md' for p in files),
                'references_checked': checked_links, 'findings': findings, 'skipped': skipped,
                'limits': 'Checks explicit local Markdown links and entry-file references, not all prose, fragment anchors, remote URLs, code behaviour or privacy.'}

    def new_project(self, destination, write=False):
        target = self.path(destination, exists=False)
        if target == self.root or target.exists():
            raise ValueError('Choose a new project directory; existing destinations are never merged.')
        template = self.path('templates/project')
        if target.is_relative_to(template):
            raise ValueError('Create the project outside the template folder.')
        for required in ('AGENTS.md', 'CLAUDE.md', 'PROJECT-RULES.md', 'PROJECT.md', 'SESSION-STATE.md'):
            if not (template / required).is_file():
                raise ValueError('The project template is incomplete; restore the untouched kit template.')
        files, skipped, unsafe = self.scan('templates/project')
        if skipped or unsafe or not files:
            raise ValueError('Template contains excluded paths or no usable files.')
        payload = []
        for path in files:
            if path.suffix.lower() not in {'.md', '.txt', '.json'}:
                raise ValueError('Project templates must contain plain Markdown, text or JSON only.')
            data, _ = self.read(path)
            payload.append((path.relative_to(template), data))
        result = {'ok': True, 'destination': self.relative(target),
                  'files': [p.as_posix() for p, _ in payload], 'written': False}
        if not write:
            return result
        self.path(destination, exists=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.path(destination, exists=False)
        try:
            target.mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise ValueError('Destination appeared during setup; no existing work was overwritten.') from exc
        for relative, data in payload:
            output = target / relative
            self.path(self.relative(output), exists=False)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('xb') as handle:
                handle.write(data)
        result['written'] = True
        return result

    def state_hash(self, file='SESSION-STATE.md'):
        path = self.path(file)
        if path.suffix.lower() != '.md':
            raise ValueError('State must be a Markdown file.')
        data, _ = self.read(path)
        return {'ok': True, 'file': self.relative(path), 'bytes': len(data), 'sha256': digest(data)}

    def compact(self, file, summary, expect_hash, write=False):
        path, summary_path = self.path(file), self.path(summary)
        if path == summary_path or path.suffix.lower() != '.md' or summary_path.suffix.lower() != '.md':
            raise ValueError('Use separate Markdown state and summary files.')
        if not re.fullmatch(r'[0-9a-f]{64}', expect_hash):
            raise ValueError('Supply the SHA256 returned by state-hash.')
        original, _ = self.read(path)
        _, text = self.read(summary_path)
        if digest(original) != expect_hash:
            raise ValueError('State changed since the summary was prepared; read it again.')
        if not text.strip() or len(text) > 12000:
            raise ValueError('Summary must contain 1 to 12000 characters.')
        archive = path.parent / 'docs' / 'session-history' / (path.stem + '-' + expect_hash + '.md')
        self.path(self.relative(archive), exists=False, allow_history=True)
        archive_link = archive.relative_to(path.parent).as_posix()
        new_bytes = (text.strip() + '\n\nPrevious complete state: [history](<' + archive_link +
                     '>). SHA256: `' + expect_hash + '`.\n').encode('utf-8')
        result = {'ok': True, 'file': self.relative(path), 'archive': self.relative(archive),
                  'previous_sha256': expect_hash, 'previous_bytes': len(original),
                  'current_bytes': len(new_bytes), 'written': False}
        if not write:
            return result
        lock = path.with_name(path.name + '.compact.lock')
        temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            handle = lock.open('xb')
        except FileExistsError as exc:
            raise ValueError('Another writer holds the state lock; inspect before retrying.') from exc
        token = uuid.uuid4().hex.encode('ascii')
        try:
            with handle:
                handle.write(token)
            if digest(self.read(path)[0]) != expect_hash:
                raise ValueError('State changed while acquiring the lock.')
            self.path(self.relative(archive), exists=False, allow_history=True)
            archive.parent.mkdir(parents=True, exist_ok=True)
            self.path(self.relative(archive), exists=False, allow_history=True)
            if archive.exists():
                if archive.read_bytes() != original:
                    raise ValueError('Existing archive differs; it will not be overwritten.')
            else:
                with archive.open('xb') as output:
                    output.write(original)
                    output.flush()
                    os.fsync(output.fileno())
            with temporary.open('xb') as output:
                output.write(new_bytes)
                output.flush()
                os.fsync(output.fileno())
            if digest(self.read(path)[0]) != expect_hash:
                raise ValueError('State changed before replacement; current work was preserved.')
            os.replace(temporary, path)
            result['written'] = True
            return result
        finally:
            if temporary.exists() and not linked(temporary):
                temporary.unlink()
            if lock.exists() and not linked(lock) and lock.read_bytes() == token:
                lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).absolute().parent.parent), help='Existing workspace directory')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'map', 'context', 'overview'):
        command = commands.add_parser(name)
        command.add_argument('--scope', default='.', help='Relative project directory; default workspace root')
        if name == 'context':
            command.add_argument('--max-chars', type=int, default=12000)
    new = commands.add_parser('new-project')
    new.add_argument('destination')
    new.add_argument('--write', action='store_true', help='Create the new directory; otherwise preview only')
    state = commands.add_parser('state-hash')
    state.add_argument('--file', default='SESSION-STATE.md')
    compact = commands.add_parser('compact')
    compact.add_argument('--file', default='SESSION-STATE.md')
    compact.add_argument('--summary', required=True)
    compact.add_argument('--expect-sha256', required=True)
    compact.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    try:
        workspace = Workspace(args.root)
        if args.command in {'doctor', 'map', 'overview'}:
            result = getattr(workspace, args.command)(args.scope)
        elif args.command == 'context':
            result = workspace.context(args.scope, args.max_chars)
        elif args.command == 'new-project':
            result = workspace.new_project(args.destination, args.write)
        elif args.command == 'state-hash':
            result = workspace.state_hash(args.file)
        else:
            result = workspace.compact(args.file, args.summary, args.expect_sha256, args.write)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result.get('ok') else 1
    except ValueError as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    except OSError as exc:
        print(json.dumps({'ok': False, 'error': 'Filesystem operation failed: ' + type(exc).__name__ + '. No existing work should be discarded; inspect any partial new output.'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
