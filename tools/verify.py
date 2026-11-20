#!/usr/bin/env python3
"""Run an explicitly trusted check and bind its result to declared file contents.

Preview is the default. --run executes local code with your user permissions: this
is not a sandbox. Command output is discarded, not stored. Receipts are private.
Only declared inputs are covered; include every dependency relevant to your check.
"""
import argparse
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
import uuid
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILES = 1000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_chain(path):
    for item in reversed((path, *path.parents)):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Linked or reparse paths are not supported.')


def strict_root(value):
    root = Path(os.path.abspath(value))
    check_chain(root)
    if not root.is_dir():
        raise ValueError('Root must be an existing directory.')
    return root


def relative_name(value, allow_runtime=False):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Use a non-empty relative path with forward slashes.')
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('Absolute, ambiguous or traversal paths are refused.')
    for part in path.parts:
        if any(c in ':*?[]<>"|' or unicodedata.category(c) in {'Cc','Cs'} for c in part):
            raise ValueError('Invalid filename characters, controls, wildcards or streams are refused.')
        if part.endswith((' ', '.')) or len(part.encode('utf-16-le')) // 2 > 255 or len(part.encode('utf-8')) > 255:
            raise ValueError('Ambiguous or overlong filename components are refused.')
    forbidden = {'.git', '.ssh', '.aws', '.azure', '.config', 'node_modules', '__pycache__'}
    if not allow_runtime:
        forbidden.add('.workspace')
    for part in path.parts:
        lower = part.lower()
        if lower in forbidden or lower.startswith('.env') or lower in {'id_rsa', 'id_ed25519', '.mcp.json'}:
            raise ValueError('Credential, runtime or dependency paths are excluded.')
        if lower.endswith(('.pem', '.key', '.p12', '.pfx')) or any(word in lower for word in ('credentials', 'secrets', 'settings.local')):
            raise ValueError('Potential credential files are excluded.')
        if lower.split('.')[0].rstrip(' ') in {'con', 'prn', 'aux', 'nul', 'conin$', 'conout$', 'clock$',
                *(f'com{i}' for i in (*range(1,10),'\u00b9','\u00b2','\u00b3')),
                *(f'lpt{i}' for i in (*range(1,10),'\u00b9','\u00b2','\u00b3'))}:
            raise ValueError('Reserved device names are refused.')
    return path.as_posix()


def safe_path(root, relative, must_exist=True, allow_runtime=False):
    name = relative_name(relative, allow_runtime)
    path = root.joinpath(*PurePosixPath(name).parts)
    check_chain(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes the selected root.')
    if must_exist and not path.exists():
        raise ValueError(f'Required path is missing: {name}')
    if path.is_file() and path.stat().st_nlink > 1:
        raise ValueError('Hard-linked files are not supported.')
    return path


def read_bytes(root, relative, limit=MAX_FILE, allow_runtime=False):
    path = safe_path(root, relative, allow_runtime=allow_runtime)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Expected a regular file within the size limit.')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('File grew beyond the size limit.')
    check_chain(path)
    return data


def selected_files(root, names):
    if not isinstance(names, list) or not 1 <= len(names) <= MAX_FILES:
        raise ValueError(f'Select 1 to {MAX_FILES} explicit files.')
    normal = [relative_name(name) for name in names]
    if len({name.casefold() for name in normal}) != len(normal):
        raise ValueError('Duplicate or case-colliding files are refused.')
    values, total = {}, 0
    for name in sorted(normal):
        data = read_bytes(root, name)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('Selected files exceed the total size limit.')
        values[name] = data
    return values


def runtime_dir(root, relative):
    path = safe_path(root, relative, must_exist=False, allow_runtime=True)
    path.mkdir(parents=True, exist_ok=True)
    return safe_path(root, relative, allow_runtime=True)


@contextmanager
def exclusive_lock(root, relative):
    parent = PurePosixPath(relative).parent.as_posix()
    runtime_dir(root, parent)
    path = safe_path(root, relative, must_exist=False, allow_runtime=True)
    token = uuid.uuid4().hex
    try:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(token)
    except FileExistsError:
        raise ValueError('Another operation holds the lock; inspect it rather than deleting it blindly.')
    # Existing callers release normally. Process owners can retain the lock when
    # interruption or failed cleanup leaves execution unresolved.
    state = {'retain': False}
    try:
        yield state
    finally:
        if not state['retain']:
            try:
                if read_bytes(root, relative, 100, allow_runtime=True).decode() == token:
                    path.unlink()
            except (OSError, ValueError):
                pass


def inspect_config(root, config_name):
    raw = read_bytes(root, config_name, 1024 * 1024)
    config = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(config, dict) or set(config) - {'command', 'inputs', 'timeout_seconds'}:
        raise ValueError('Configuration must contain command, inputs and optional timeout_seconds only.')
    command = config.get('command')
    if not isinstance(command, list) or not command or len(command) > 100 or any(not isinstance(v,str) or not v or '\x00' in v or len(v)>10000 for v in command):
        raise ValueError('command must be a non-empty array of arguments.')
    timeout = config.get('timeout_seconds', 30)
    if isinstance(timeout, bool) or not isinstance(timeout, (int,float)) or not 0 < timeout <= 600:
        raise ValueError('timeout_seconds must be greater than zero and at most 600.')
    inputs = selected_files(root, config.get('inputs'))
    identity = {'schema':1, 'config':digest(raw), 'tool':digest(Path(__file__).read_bytes()),
                'inputs':{name:digest(data) for name,data in inputs.items()}}
    fingerprint = digest(json.dumps(identity, sort_keys=True, separators=(',',':')).encode())
    return config, identity, fingerprint


def status(root, config_name):
    _, _, fingerprint = inspect_config(root, config_name)
    lock = safe_path(root, '.workspace/verification/run.lock', must_exist=False, allow_runtime=True)
    if lock.exists():
        return {'status':'running_or_interrupted', 'passed':False}, 1
    receipt_path = safe_path(root, '.workspace/verification/latest.json', must_exist=False, allow_runtime=True)
    if not receipt_path.exists():
        return {'status':'missing', 'passed':False}, 1
    receipt = json.loads(read_bytes(root, '.workspace/verification/latest.json', 1024*1024, True))
    if not isinstance(receipt,dict) or receipt.get('schema') != 1:
        raise ValueError('Receipt format is invalid.')
    if receipt.get('fingerprint') != fingerprint:
        return {'status':'stale', 'passed':False, 'reason':'Declared input, configuration or tool contents changed.'}, 1
    passed = receipt.get('status') == 'passed' and receipt.get('exit_code') == 0 and receipt.get('stable') is True
    return {**receipt, 'passed':passed}, 0 if passed else 1


def stop_check(process):
    """Best-effort bounded tree cleanup; False requires inspection and a retained lock."""
    tree_stopped = False
    try:
        if os.name == 'nt':
            result = subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,shell=False)
            tree_stopped = result.returncode == 0
        else:
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            tree_stopped = True
    except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
        # Killing only the parent cannot establish that its children stopped.
        pass
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
        return False
    return tree_stopped and process.poll() is not None


def execute_bounded(command, root, timeout, *, env=None):
    options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session':True}
    process = subprocess.Popen(command,cwd=root,shell=False,stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env,**options)
    try:
        return process.wait(timeout=timeout), None, False
    except subprocess.TimeoutExpired:
        reason = 'timed_out'
    except KeyboardInterrupt:
        reason = 'cancelled'
    except OSError:
        reason = 'execution_failed'
    resolved = stop_check(process)
    # This is cooperative process management, not a sandbox against deliberately
    # detached children. Failed tree cleanup keeps the lease for inspection.
    return process.poll(), reason, not resolved


def run_check(root, config_name, *, env=None):
    with exclusive_lock(root, '.workspace/verification/run.lock') as lease:
        config, identity, before = inspect_config(root, config_name)
        command = [sys.executable if value == '{python}' else value for value in config['command']]
        started = time.monotonic()
        reason, exit_code, launch_failed, unresolved = None, None, False, False
        # Unexpected interruption after launch must not expose older success.
        lease['retain'] = True
        try:
            # Discard output entirely: no unbounded buffering or accidental log export.
            exit_code,reason,unresolved = execute_bounded(command,root,config.get('timeout_seconds',30),env=env)
        except OSError:
            launch_failed = True
        try:
            _, _, after = inspect_config(root, config_name)
            stable = before == after
        except (OSError, ValueError):
            stable = False
        state = reason or ('launch_failed' if launch_failed else
                           'changed_during_check' if not stable else 'passed' if exit_code == 0 else 'failed')
        receipt = {'schema':1, 'status':state, 'passed':state=='passed', 'exit_code':exit_code,
                   'stable':stable, 'fingerprint':before, 'declared_input_hashes':identity['inputs'],
                   'elapsed_seconds':round(time.monotonic()-started,3),
                   'checked_at':datetime.now(timezone.utc).isoformat(),
                   'reviewed':False, 'observed':False, 'released':False,
                   'lease_retained':unresolved,
                   'scope':'Declared inputs only; command output discarded. Receipt is not an attestation of independent review.'}
        folder = runtime_dir(root, '.workspace/verification')
        name = f'run-{uuid.uuid4().hex}.json'
        with (folder/name).open('x',encoding='utf-8') as stream:
            json.dump(receipt,stream,indent=2)
        latest = safe_path(root, '.workspace/verification/latest.json', must_exist=False, allow_runtime=True)
        temporary = folder / f'latest-{uuid.uuid4().hex}.tmp'
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(receipt,stream,indent=2)
        check_chain(folder)
        os.replace(temporary,latest)
        lease['retain'] = unresolved
        return receipt, 0 if state=='passed' else 130 if state=='cancelled' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--config', default='checks.json')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run',action='store_true')
    mode.add_argument('--status',action='store_true')
    args = parser.parse_args(argv)
    try:
        root = strict_root(args.root)
        if args.run:
            result, code = run_check(root,args.config)
        elif args.status:
            result, code = status(root,args.config)
        else:
            config, _, identity = inspect_config(root,args.config)
            result, code = {'status':'preview','command':config['command'],'inputs':config['inputs'],
                            'fingerprint':identity,'notice':'Use --run only for a trusted command. It runs with your permissions, not in a sandbox.'},0
        print(json.dumps(result,indent=2))
        return code
    except (ValueError,OSError,UnicodeError) as error:
        print(json.dumps({'status':'refused','error':str(error)},indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
