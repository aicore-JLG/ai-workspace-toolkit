"""Prepare/validate a synthetic Docker isolation pilot; never launch or install Docker.

Preview by default. Prepared commands use only an explicitly selected local image.
Validation checks local evidence, not tamper-proof attestation or general isolation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from verify import check_chain, safe_path, strict_root

IMAGE = re.compile(r'sha256:[a-f0-9]{64}')
CHECKS = ('allowed_read', 'input_readonly', 'other_client_unreadable',
          'account_canary_unreadable', 'ambient_credential_absent', 'root_write_denied',
          'output_write', 'ipv4_route_denied', 'ipv6_route_denied')
FIXTURES = ('client-a/allowed.txt', 'client-a/probe.py', 'client-b/canary.txt', 'account/canary.txt')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def location(value):
    path = Path(os.path.abspath(value))
    if any(char in str(path) for char in ',\n\r\x00'):
        raise ValueError('Pilot directory contains unsupported mount characters.')
    check_chain(path)
    return path


def image_id(value):
    if not isinstance(value, str) or not IMAGE.fullmatch(value):
        raise ValueError('Select an existing local image by full sha256 ID; tags/pulls are refused.')
    return value


def probe_source(nonce, other, account):
    # Only synthetic paths are embedded. No credential value is sent into the container.
    return '''import errno,json,os,socket
from pathlib import Path
NONCE = ''' + repr(nonce) + '''
OTHER = ''' + repr(str(other)) + '''
ACCOUNT = ''' + repr(str(account)) + '''
def cannot_read(path):
    try:
        with open(path,'rb') as stream: stream.read(1)
        return False
    except OSError as error:
        return error.errno in {errno.ENOENT,errno.EACCES,errno.EPERM,errno.ENOTDIR}
def cannot_write(path):
    try:
        with open(path,'xb') as stream: stream.write(b'synthetic denied write')
        return False
    except OSError as error:
        return error.errno in {errno.EROFS,errno.EACCES,errno.EPERM}
def no_route(family,address):
    try:
        with socket.socket(family,socket.SOCK_DGRAM) as connection:
            connection.settimeout(2)
            connection.connect(address)  # Routing only: no packet is sent.
        return False
    except OSError as error:
        return error.errno in {errno.ENETUNREACH,errno.EHOSTUNREACH,errno.EPERM,errno.EACCES,errno.EAFNOSUPPORT,errno.EPROTONOSUPPORT}
checks = {}
checks['allowed_read'] = Path('/input/allowed.txt').read_text() == 'synthetic allowed input\\n'
checks['input_readonly'] = cannot_write('/input/unexpected-write.txt')
checks['other_client_unreadable'] = all(cannot_read(p) for p in [OTHER,'/workspace/client-b/canary.txt','/client-b/canary.txt'])
checks['account_canary_unreadable'] = all(cannot_read(p) for p in [ACCOUNT,'/workspace/account/canary.txt','/account/canary.txt'])
checks['ambient_credential_absent'] = 'ISOLATION_PILOT_CREDENTIAL' not in os.environ
checks['root_write_denied'] = cannot_write('/etc/isolation-pilot-write')
try:
    Path('/output/write-canary.txt').write_text('synthetic scoped output\\n')
    checks['output_write'] = True
except OSError:
    checks['output_write'] = False
checks['ipv4_route_denied'] = no_route(socket.AF_INET,('192.0.2.1',9))
checks['ipv6_route_denied'] = no_route(socket.AF_INET6,('2001:db8::1',9))
Path('/output/result.json').write_text(json.dumps({'schema':1,'nonce':NONCE,'checks':checks}))
raise SystemExit(0 if all(checks.values()) else 1)
'''


def commands(root, image, name):
    # Explicit local socket + empty Docker config avoid inherited remote contexts/logins.
    host = 'npipe:////./pipe/docker_engine' if os.name == 'nt' else 'unix:///var/run/docker.sock'
    base = ['docker', '--config', str(root / 'docker-config'), '--host', host]
    create = base + ['run', '--name', name, '--pull=never', '--network=none', '--read-only',
        '--cap-drop=ALL', '--security-opt=no-new-privileges:true', '--user=65534:65534',
        '--pids-limit=32', '--memory=128m', '--cpus=1',
        '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m',
        '--mount', 'type=bind,source=' + str(root / 'client-a') + ',target=/input,readonly',
        '--mount', 'type=bind,source=' + str(root / 'output') + ',target=/output',
        '--workdir=/tmp', '--env=PYTHONDONTWRITEBYTECODE=1', '--env=PYTHONNOUSERSITE=1',
        '--entrypoint=python3', image, '/input/probe.py']
    return {'image_inspect': base + ['image', 'inspect', image], 'run': create,
            'container_inspect': base + ['inspect', name], 'cleanup_after_inspection': base + ['rm', '-f', name]}


def preview(directory, image):
    root = location(directory)
    image_id(image)
    return {'status': 'preview', 'executed': False, 'directory': str(root), 'image': image,
            'runtime_observed': False,
            'notice': 'Prepare creates synthetic fixtures only. No Docker command, image pull, account access or model call is executed.'}


def prepare(directory, image):
    root = location(directory)
    image_id(image)
    if not root.parent.is_dir():
        raise ValueError('Create the explicit parent directory first.')
    root.mkdir(mode=0o700, exist_ok=False)
    for name in ('client-a', 'client-b', 'account', 'output', 'docker-config'):
        (root / name).mkdir(mode=0o755)
    # Only this newly minted synthetic output directory is made writable to the container UID.
    (root / 'output').chmod(0o777)
    nonce = uuid.uuid4().hex
    files = {'client-a/allowed.txt': 'synthetic allowed input\n',
             'client-b/canary.txt': 'synthetic-other-client-' + uuid.uuid4().hex,
             'account/canary.txt': 'synthetic-account-' + uuid.uuid4().hex,
             'client-a/probe.py': probe_source(nonce, root/'client-b/canary.txt', root/'account/canary.txt')}
    for name, text in files.items():
        (root / name).write_bytes(text.encode('utf-8'))
        (root / name).chmod(0o644)
    manifest = {'schema': 1, 'nonce': nonce, 'image': image, 'name': 'workspace-isolation-' + nonce,
                'root': str(root.resolve()), 'files': {name: digest((root/name).read_bytes()) for name in FIXTURES}}
    (root/'pilot.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    plan = commands(root, image, manifest['name'])
    (root/'commands.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    return {'status': 'prepared_unobserved', 'executed': False, 'runtime_observed': False,
            'directory': str(root), 'commands_file': 'commands.json',
            'notice': 'Synthetic fixtures only. Follow ISOLATION-PILOT.md; missing evidence always refuses validation.'}


def read_json(root, name):
    path = safe_path(root, name)
    if not path.is_file() or path.stat().st_size > 1024*1024:
        raise ValueError('Missing or oversized local evidence.')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source_name(value):
    value = value.replace('\\', '/')
    if os.name == 'nt':
        for prefix in ('/run/desktop/mnt/host/', '/host_mnt/'):
            if value.startswith(prefix):
                value = value[len(prefix):]
                if re.match(r'^[A-Za-z]/', value): value = value[0] + ':' + value[1:]
        return value.rstrip('/').casefold()
    return value.rstrip('/')


def validate(directory):
    root = strict_root(location(directory))
    data = read_json(root, 'pilot.json')
    if set(data) != {'schema','nonce','image','name','root','files'} or type(data['schema']) is not int or data['schema'] != 1:
        raise ValueError('Invalid pilot manifest.')
    if data['root'] != str(root.resolve()) or not re.fullmatch(r'[a-f0-9]{32}', data['nonce']) or data['name'] != 'workspace-isolation-' + data['nonce']:
        raise ValueError('Pilot evidence belongs to another root or run.')
    image_id(data['image'])
    if read_json(root, 'commands.json') != commands(root, data['image'], data['name']):
        raise ValueError('Prepared commands changed.')
    if set(data['files']) != set(FIXTURES): raise ValueError('Invalid fixture set.')
    for name, expected in data['files'].items():
        path = safe_path(root, name)
        if not path.is_file() or path.stat().st_size > 65536 or digest(path.read_bytes()) != expected:
            raise ValueError('A synthetic fixture changed.')
    for area, expected in [('client-a', {'allowed.txt','probe.py'}), ('client-b', {'canary.txt'}),
                           ('account', {'canary.txt'}), ('output', {'result.json','write-canary.txt'}), ('docker-config', set())]:
        path = safe_path(root, area)
        if {entry.name for entry in path.iterdir()} != expected:
            raise ValueError('Unexpected file in a scoped pilot directory.')
    result = read_json(root, 'output/result.json')
    if set(result) != {'schema','nonce','checks'} or type(result['schema']) is not int or result['schema'] != 1 or result['nonce'] != data['nonce'] or set(result['checks']) != set(CHECKS) or any(value is not True for value in result['checks'].values()):
        raise ValueError('A required canary check failed or is missing.')
    if safe_path(root, 'output/write-canary.txt').read_bytes() != b'synthetic scoped output\n':
        raise ValueError('Scoped output was not observed.')
    records = read_json(root, 'container-inspect.json')
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError('Exactly one container inspection is required.')
    container = records[0]; config = container['Config']; host = container['HostConfig']; state = container['State']
    if container['Name'] != '/' + data['name'] or container['Image'] != data['image'] or config['Image'] != data['image']:
        raise ValueError('Unexpected container or image identity.')
    if config['User'] != '65534:65534' or config['Entrypoint'] != ['python3'] or config['Cmd'] != ['/input/probe.py'] or config['WorkingDir'] != '/tmp':
        raise ValueError('Unexpected container execution settings.')
    if state['Running'] is not False or type(state['ExitCode']) is not int or state['ExitCode'] != 0 or state.get('OOMKilled') is not False or state.get('Error'):
        raise ValueError('Container did not finish successfully.')
    if host['NetworkMode'] != 'none' or host['ReadonlyRootfs'] is not True or host['Privileged'] is not False or host['CapDrop'] != ['ALL']:
        raise ValueError('Required runtime restrictions are absent.')
    if set(host.get('SecurityOpt') or []) not in ({'no-new-privileges'}, {'no-new-privileges:true'}):
        raise ValueError('Unexpected security options.')
    if any(host.get(key) for key in ('CapAdd','Devices','DeviceRequests','VolumesFrom','Binds','Links','PortBindings','PublishAllPorts')) or any(host.get(key) == 'host' for key in ('PidMode','IpcMode','UTSMode','CgroupnsMode')):
        raise ValueError('Unexpected host access or published ports.')
    for field, cap in [('PidsLimit',32),('Memory',134217728),('NanoCpus',1000000000)]:
        if type(host.get(field)) is not int or not 0 < host[field] <= cap:
            raise ValueError('Missing runtime resource limit.')
    tmpfs = host.get('Tmpfs')
    if not isinstance(tmpfs, dict) or set(tmpfs) != {'/tmp'} or not {'noexec','nosuid','nodev'}.issubset(tmpfs['/tmp'].split(',')):
        raise ValueError('Unexpected temporary filesystem configuration.')
    mounts = container['Mounts']
    if not isinstance(mounts, list) or len(mounts) != 2:
        raise ValueError('Unexpected mounted directories.')
    expected = {'/input': (root/'client-a', False), '/output': (root/'output', True)}
    if {mount['Destination'] for mount in mounts} != set(expected):
        raise ValueError('Unexpected mount destination.')
    for mount in mounts:
        source, writable = expected[mount['Destination']]
        if mount['Type'] != 'bind' or mount['RW'] is not writable or source_name(mount['Source']) != source_name(str(source)):
            raise ValueError('Unexpected mount source or permissions.')
    env = config.get('Env') or []
    if not isinstance(env, list) or any(not isinstance(item,str) for item in env):
        raise ValueError('Invalid container environment evidence.')
    if any(re.search(r'(?i)(secret|token|password|credential|api[_-]?key)', item.split('=',1)[0]) for item in env):
        raise ValueError('Credential-shaped environment name reached the container.')
    return {'status': 'synthetic_evidence_validated', 'runtime_observed': 'reported_by_local_receipt', 'nonce': data['nonce'],
            'image': data['image'], 'checks': list(CHECKS),
            'notice': 'Supplied local reports passed validation; this tool never launched or independently observed Docker. Evidence is not tamper-proof or a production client/model isolation certification. The main orchestrator is not automatically contained.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True);parser.add_argument('--image')
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--prepare',action='store_true');mode.add_argument('--validate',action='store_true')
    args=parser.parse_args(argv)
    try:
        result = validate(args.directory) if args.validate else prepare(args.directory,args.image) if args.prepare else preview(args.directory,args.image)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError,AttributeError):
        print(json.dumps({'status':'refused','runtime_observed':False,'error':'Missing, changed, failed or incompatible isolation evidence. No isolation success is inferred.'}));return 1


if __name__ == '__main__':
    raise SystemExit(main())
