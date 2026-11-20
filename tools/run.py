#!/usr/bin/env python3
"""Preview or explicitly run one trusted foreground command with a private log.

The guard is partial, not a sandbox. Trusted scripts run with your permissions and
environment. No provider hooks are installed. Output redaction is best effort;
logs may still contain personal or project information and must remain private.
Background children/services are unsupported. A completion describes only the
foreground process; an unresolved output pipe retains the lease for inspection.
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

from verify import (check_chain, digest, read_bytes, runtime_dir,
                    safe_path, selected_files, strict_root)

LOCK = '.workspace/runs/resource.lock'
LATEST = '.workspace/runs/latest.json'
SHELLS = {'sh','bash','zsh','fish','dash','cmd','powershell','pwsh','wscript','cscript'}
DESTRUCTIVE = {'rm','rmdir','del','erase','format','mkfs','diskpart','sudo','su','chmod','chown','takeown','icacls','reg'}


@contextmanager
def resource_lease(root):
    runtime_dir(root,'.workspace/runs')
    path = safe_path(root,LOCK,must_exist=False,allow_runtime=True)
    token = uuid.uuid4().hex
    record = {'token':token,'owner_pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat()}
    try:
        with path.open('x',encoding='utf-8') as stream:
            json.dump(record,stream)
    except FileExistsError:
        raise ValueError('Another run or unresolved operation holds the resource lease; inspect it before removing it.')
    # Default to preserving the lease if an unexpected exception interrupts cleanup.
    state = {'retain':True}
    try:
        yield state
    finally:
        if not state['retain']:
            try:
                if json.loads(read_bytes(root,LOCK,2048,True)).get('token')==token:
                    path.unlink()
            except (OSError,ValueError):
                pass


def guard(command):
    """Reject common direct hazards; never claim to understand arbitrary programs."""
    executable = command[0].replace('\\','/').rsplit('/',1)[-1].lower()
    stem = executable.removesuffix('.exe').removesuffix('.com')
    if executable.endswith(('.cmd','.bat','.ps1')) or stem in SHELLS | DESTRUCTIVE:
        raise ValueError('The partial guard refuses shell wrappers and destructive direct commands.')
    if '/' in command[0] or '\\' in command[0] or ':' in command[0]:
        raise ValueError('Use an executable name on PATH or the {python} placeholder.')
    if any(arg.lower() in {'-c','-command','-encodedcommand','-enc','-e','--eval','/c','/k'} or
           arg.lower().startswith(('-c','-e','--eval=')) for arg in command[1:]):
        raise ValueError('Inline code and shell-command arguments are refused; use a reviewed local script.')
    if stem == 'git' and any(word in command[1:] for word in ('clean','reset','push','checkout','restore')):
        raise ValueError('Potentially destructive or publishing Git operations are outside this runner guard.')
    if any(arg in {';','&&','||','|','>','>>','<'} for arg in command):
        raise ValueError('Shell control operators are refused.')
    for argument in command[1:]:
        text = argument.replace('\\','/').lower()
        if re.search(r'(^|[/=\s])(?:\.env[^/]*|\.ssh(?:/|$)|\.aws(?:/|$)|id_rsa\b|id_ed25519\b)',text):
            raise ValueError('Credential-shaped paths are refused.')
        if re.search(r'(?:credentials|secrets)(?:\.[a-z]+)?(?:$|/)|\.(?:pem|pfx|p12|key)(?:$|\s)',text):
            raise ValueError('Credential-shaped paths are refused.')
        if re.match(r'--?(?:api[-_]?key|token|password|secret|authorization)(?:=|$)',text):
            raise ValueError('Do not put credentials in command arguments.')


def secret_values():
    return [value for name,value in os.environ.items()
            if len(value)>=4 and re.search(r'key|secret|token|password|credential|authorization',name,re.I)]


def redact(text, values):
    for value in sorted(values,key=len,reverse=True):
        text = text.replace(value,'[REDACTED]')
        # A bounded capture may end in only the beginning of a known secret.
        for length in range(min(len(value),len(text)),3,-1):
            if text.endswith(value[:length]):
                text = text[:-length]+'[REDACTED]'
                break
    text = re.sub(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)',
                  '[REDACTED PRIVATE KEY]',text)
    text = re.sub(r'(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s]+',r'\1[REDACTED]',text)
    text = re.sub(r'(?i)(https?://)[^/\s:@]+:[^/\s@]+@',r'\1[REDACTED]@',text)
    text = re.sub(r'''(?i)(\b(?:api[_-]?key|access[_-]?token|token|password|secret)\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s]+)''',
                  r'\1[REDACTED]',text)
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b','[REDACTED]',text)
    return text


def inspect_config(root,name):
    raw = read_bytes(root,name,1024*1024)
    config = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(config,dict) or set(config)-{'command','inputs','timeout_seconds','max_output_bytes'}:
        raise ValueError('Use command, inputs, timeout_seconds and max_output_bytes only.')
    command = config.get('command')
    if not isinstance(command,list) or not 1<=len(command)<=100 or any(not isinstance(arg,str) or not arg or '\x00' in arg or len(arg)>10000 for arg in command):
        raise ValueError('command must be a non-empty argument array.')
    guard(command)
    timeout = config.get('timeout_seconds',30)
    cap = config.get('max_output_bytes',65536)
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 0<timeout<=600:
        raise ValueError('timeout_seconds must be greater than zero and no more than 600.')
    if type(cap) is not int or not 1024<=cap<=1024*1024:
        raise ValueError('max_output_bytes must be between 1024 and 1048576.')
    inputs = selected_files(root,config.get('inputs'))
    identity = {'config':digest(raw),'tool':digest(Path(__file__).read_bytes()),
                'path_helpers':digest(Path(__file__).with_name('verify.py').read_bytes()),
                'inputs':{name:digest(data) for name,data in inputs.items()}}
    fingerprint = digest(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
    return config,fingerprint


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        try:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,shell=False)
        except (OSError,subprocess.TimeoutExpired):
            process.kill()
    else:
        try:
            os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def capture(command,root,timeout,cap,retain_output=True):
    options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
    process = subprocess.Popen(command,cwd=root,shell=False,stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,**options)
    buffers = [bytearray(),bytearray()]
    captured = [0]
    mutex = threading.Lock()
    excess = threading.Event()
    def consume(stream,index):
        try:
            while True:
                block = stream.read(4096)
                if not block:
                    break
                with mutex:
                    remaining = cap-captured[0]
                    captured[0] += min(len(block),max(0,remaining))
                    if retain_output:
                        buffers[index].extend(block[:max(0,remaining)])
                    if len(block)>remaining:
                        excess.set()
        finally:
            stream.close()
    readers = [threading.Thread(target=consume,args=(stream,index),daemon=True)
               for index,stream in enumerate((process.stdout,process.stderr))]
    for thread in readers:
        thread.start()
    deadline = time.monotonic()+timeout
    reason = None
    try:
        while process.poll() is None:
            if excess.is_set():
                reason = 'output_limit'
                break
            if time.monotonic()>=deadline:
                reason = 'timed_out'
                break
            time.sleep(.02)
    except KeyboardInterrupt:
        reason = 'cancelled'
    if reason:
        stop_process(process)
    for thread in readers:
        thread.join(timeout=1)
    unresolved_output = any(thread.is_alive() for thread in readers)
    if unresolved_output:
        reason = reason or 'incomplete_output'
    if excess.is_set():
        reason = reason or 'output_limit'
    with mutex:
        output = [bytes(buffer).decode('utf-8',errors='replace') for buffer in buffers]
    return process.poll(),reason,output,unresolved_output


def execute_trusted(root,command,*,operation='integration',timeout_seconds=120,
                    max_output_bytes=65536,output_mode='redact',identity=None):
    """Run a caller-vetted native argv with the same foreground controls.

    This Python API deliberately accepts resolved executable paths; it is not a
    new command-line escape from guard(). Callers must select trusted code.
    It never records raw argv. Secret-bearing jobs must use output_mode=discard.
    """
    root = strict_root(root)
    if not isinstance(command,list) or not 1<=len(command)<=100 or any(
            not isinstance(arg,str) or not arg or '\x00' in arg or len(arg)>10000 for arg in command):
        raise ValueError('Use a bounded, non-empty argument array.')
    executable = command[0].replace('\\','/').rsplit('/',1)[-1].lower()
    if executable.endswith(('.cmd','.bat','.ps1')) or executable.removesuffix('.exe') in SHELLS:
        raise ValueError('Resolve a native executable entrypoint, not a shell shim.')
    if isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float)) or not 0<timeout_seconds<=600:
        raise ValueError('timeout_seconds must be greater than zero and no more than 600.')
    if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=1024*1024:
        raise ValueError('max_output_bytes must be between 1024 and 1048576.')
    if output_mode not in {'redact','discard'} or not re.fullmatch(r'[a-z][a-z0-9-]{0,80}',operation):
        raise ValueError('Invalid operation or output mode.')
    command_hash = digest(json.dumps(command,separators=(',',':')).encode())
    fingerprint = digest(json.dumps({'command_hash':command_hash,'identity':identity,
        'tool':digest(Path(__file__).read_bytes()),'timeout_seconds':timeout_seconds,
        'max_output_bytes':max_output_bytes,'output_mode':output_mode},sort_keys=True).encode())
    with resource_lease(root) as lease:
        identifier = uuid.uuid4().hex
        started = time.monotonic()
        values = secret_values() if output_mode=='redact' else []
        exit_code,reason,output,unresolved = None,None,['',''],False
        try:
            exit_code,reason,output,unresolved = capture(command,root,timeout_seconds,
                max_output_bytes,retain_output=output_mode=='redact')
        except OSError:
            reason = 'launch_failed'
        state = reason or ('completed' if exit_code==0 else 'failed')
        log = None
        if output_mode=='redact':
            folder = runtime_dir(root,'.workspace/runs')
            log = f'.workspace/runs/run-{identifier}.log'
            with (folder/f'run-{identifier}.log').open('x',encoding='utf-8') as stream:
                stream.write('stdout:\n'+redact(output[0],values)+'\nstderr:\n'+redact(output[1],values))
        receipt = {'schema':1,'id':identifier,'operation':operation,'status':state,
            'exit_code':exit_code,'fingerprint':fingerprint,'command_hash':command_hash,
            'elapsed_seconds':round(time.monotonic()-started,3),
            'finished_at':datetime.now(timezone.utc).isoformat(),'log':log,
            'output_mode':output_mode,'successful':state=='completed',
            'lease_retained':unresolved,'timeout_seconds':timeout_seconds,
            'max_output_bytes':max_output_bytes,'reviewed':False,'released':False,
            'notice':'Foreground controls only; not a sandbox or provider spending guard. No raw arguments recorded.'}
        write_receipt(root,receipt)
        lease['retain'] = unresolved
        code = 0 if state=='completed' else exit_code if state=='failed' and isinstance(exit_code,int) and 1<=exit_code<=255 else 1
        return receipt,code


def write_receipt(root,receipt):
    folder = runtime_dir(root,'.workspace/runs')
    name = f"run-{receipt['id']}.json"
    with (folder/name).open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)
    temporary = folder/f'latest-{uuid.uuid4().hex}.tmp'
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)
    latest = safe_path(root,LATEST,must_exist=False,allow_runtime=True)
    check_chain(folder)
    os.replace(temporary,latest)


def status(root,config_name):
    _,fingerprint = inspect_config(root,config_name)
    if safe_path(root,LOCK,must_exist=False,allow_runtime=True).exists():
        return {'status':'running_or_interrupted','successful':False,
                'note':'A lease exists. Inspect its owner; it is never deleted automatically.'},1
    if not safe_path(root,LATEST,must_exist=False,allow_runtime=True).exists():
        return {'status':'missing','successful':False},1
    receipt = json.loads(read_bytes(root,LATEST,1024*1024,True))
    if not isinstance(receipt,dict) or receipt.get('schema')!=1:
        raise ValueError('Invalid run receipt.')
    if receipt.get('fingerprint')!=fingerprint:
        return {'status':'stale','successful':False},1
    successful = receipt.get('status')=='completed' and receipt.get('exit_code')==0 and receipt.get('stable') is True
    return {**receipt,'successful':successful},0 if successful else 1


def run(root,config_name):
    # Refuse bad configurations before creating runtime files.
    inspect_config(root,config_name)
    with resource_lease(root) as lease:
        config,before = inspect_config(root,config_name)
        identifier = uuid.uuid4().hex
        started = time.monotonic()
        values = secret_values()
        command = [sys.executable if arg=='{python}' else arg for arg in config['command']]
        exit_code,reason,output = None,None,['','']
        unresolved_output = False
        try:
            exit_code,reason,output,unresolved_output = capture(command,root,config.get('timeout_seconds',30),config.get('max_output_bytes',65536))
        except OSError:
            reason = 'launch_failed'
        try:
            _,after = inspect_config(root,config_name)
            stable = before==after
        except (OSError,ValueError,UnicodeError):
            stable = False
        state = reason or ('changed_during_run' if not stable else 'completed' if exit_code==0 else 'failed')
        folder = runtime_dir(root,'.workspace/runs')
        log_name = f'run-{identifier}.log'
        with (folder/log_name).open('x',encoding='utf-8') as stream:
            stream.write('stdout:\n'+redact(output[0],values)+'\nstderr:\n'+redact(output[1],values))
        receipt = {'schema':1,'id':identifier,'status':state,'exit_code':exit_code,'stable':stable,
                   'fingerprint':before,'command_hash':digest(json.dumps(config['command']).encode()),
                   'elapsed_seconds':round(time.monotonic()-started,3),'finished_at':datetime.now(timezone.utc).isoformat(),
                   'log':f'.workspace/runs/{log_name}','successful':state=='completed',
                   'lease_retained':unresolved_output,
                   'reviewed':False,'released':False,
                   'notice':'Partial guard; not a sandbox. Log redaction is not a privacy guarantee.'}
        write_receipt(root,receipt)
        lease['retain'] = unresolved_output
        # Keep ordinary positive failure codes; use 1 for tool-level failures.
        code = 0 if state=='completed' else exit_code if state=='failed' and isinstance(exit_code,int) and 1<=exit_code<=255 else 1
        return receipt,code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--config',default='run.json')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run',action='store_true')
    mode.add_argument('--status',action='store_true')
    args = parser.parse_args(argv)
    try:
        root = strict_root(args.root)
        if args.run:
            result,code = run(root,args.config)
        elif args.status:
            result,code = status(root,args.config)
        else:
            config,fingerprint = inspect_config(root,args.config)
            result,code = {'status':'preview','command_preview':[redact(value,secret_values()) for value in config['command']],
                           'inputs':config['inputs'],'fingerprint':fingerprint,
                           'notice':'No command ran. Review trusted code before using --run; this is not a sandbox.'},0
        print(json.dumps(result,indent=2))
        return code
    except (OSError,ValueError,UnicodeError) as error:
        print(json.dumps({'status':'refused','error':redact(str(error),secret_values())},indent=2))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
