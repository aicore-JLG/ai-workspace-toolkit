"""Preview, install and run curated integrations. No global setup or account login.

Install/run executes trusted third-party code with the user's privileges. This is
not a sandbox. Pins identify sources; they do not prove security. Dependencies
are resolved at installation time; npm's generated lockfile stays local.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import uuid
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import execute_trusted, redact, secret_values

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'claude':'.claude/skills', 'codex':'.agents/skills'}

def checked(root, relative='.'):
    root = Path(os.path.abspath(root))
    parts = str(relative).replace('\\','/').split('/')
    if any(p=='..' or ':' in p for p in parts) or str(relative).startswith(('/','\\')):
        raise ValueError('Use a relative path within this workspace.')
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()): raise ValueError('Path escapes workspace.')
    for item in [*reversed(path.parents),path]:
        if item.exists() or item.is_symlink():
            info=item.lstat()
            if item.is_symlink() or getattr(info,'st_file_attributes',0)&0x400 or (item.is_file() and info.st_nlink>1):
                raise ValueError('Linked and reparse paths are refused.')
    return path

def read_json(root, relative):
    p=checked(root,relative)
    if p.stat().st_size>4_000_000:raise ValueError('Metadata too large.')
    return json.loads(p.read_text(encoding='utf-8'))

def catalog(root):
    data=read_json(root,'integrations/catalog.json')
    if data.get('schema_version')!=1:raise ValueError('Unsupported catalog schema.')
    rows={}
    for item in data['integrations']:
        ident=item['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,60}',ident) or ident in rows:raise ValueError('Invalid integration id.')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+',item['repository']) or not re.fullmatch('[a-f0-9]{40}',item['commit']):raise ValueError('Invalid source pin.')
        rows[ident]=item
    return rows

def entry(root, ident):
    try:return catalog(root)[ident]
    except KeyError:raise ValueError('Unknown integration.') from None

def verify_bundles(root):
    locked=read_json(root,'integrations/bundles.lock.json')['files']
    expected={}; problems=[]
    for item in locked:
        name=item['path']
        if not name.startswith('integrations/vendor/'+item['integration']+'/') or name in expected:
            raise ValueError('Invalid bundle lock entry.')
        expected[name]=item['sha256']
        try:
            p=checked(root,name)
            if not p.is_file() or p.stat().st_size>8*1024*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
                problems.append(name)
        except (OSError,ValueError):problems.append(name)
    vendor=checked(root,'integrations/vendor')
    if vendor.exists():
        for folder,dirs,files in os.walk(vendor,followlinks=False):
            for name in dirs+files:
                p=Path(folder)/name
                relative=p.relative_to(root).as_posix()
                try:checked(root,relative)
                except ValueError:problems.append(relative)
                if p.is_file() and relative not in expected:problems.append(relative)
    return {'ok':not problems,'checked_files':len(expected),'problems':sorted(set(problems)),
            'notice':'Content integrity only; not a security audit or runtime verification.'}

def available_skills(root, ident):
    entry(root,ident)
    base=checked(root,'integrations/vendor/'+ident)
    return [p.parent for p in base.rglob('SKILL.md')] if base.exists() else []

def activate(root, integration, skill, host='claude', write=False):
    root=checked(root)
    if host not in HOSTS or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,70}',skill):raise ValueError('Invalid skill or host.')
    if not verify_bundles(root)['ok']:raise ValueError('Bundled source changed, missing or has extra files; inspect integrity report.')
    matches=[p for p in available_skills(root,integration) if p.name==skill]
    if len(matches)!=1:raise ValueError('Select one available skill directory from list.')
    source=checked(root,matches[0].relative_to(root))
    destination=checked(root,HOSTS[host]+'/'+skill)
    if destination.exists():raise ValueError('Existing skill preserved. Review/merge separately; no overwrite.')
    result={'written':False,'source':str(source),'destination':str(destination),'host':host,
            'review_required':True}
    if write:
        from skill_review import require_review
        require_review(root,integration,skill)
        stage=checked(root,'.workspace/staging/'+uuid.uuid4().hex)
        stage.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source,stage)
        destination.parent.mkdir(parents=True,exist_ok=True)
        # Both absolute paths have been checked inside the explicit workspace.
        checked(root,stage.relative_to(root)); checked(root,destination.relative_to(root))
        if destination.exists():raise ValueError('Destination appeared during activation.')
        require_review(root,integration,skill)
        stage.rename(destination)
        result['written']=True
    return result

def asset_for(item):
    operating={'Windows':'win32','Darwin':'darwin','Linux':'linux'}.get(platform.system())
    arch={'amd64':'x64','x86_64':'x64','aarch64':'arm64','arm64':'arm64'}.get(platform.machine().lower())
    suffix=f'_{operating}-{arch}'+('.zip' if operating=='win32' else '.tar.gz')
    assets=[a for name,a in item.get('assets',{}).items() if name.endswith(suffix)]
    if len(assets)!=1 or not re.fullmatch(r'sha256:[a-f0-9]{64}',assets[0].get('digest') or ''):raise ValueError('No verified asset for this platform.')
    return assets[0]

def install_plan(root, integration):
    item=entry(root,integration); dest=checked(root,'.workspace/tools/'+integration)
    commands=[]; asset=None; kind=item['kind']
    if kind=='npm':
        if not re.fullmatch(r'[@a-z0-9/_.-]+',item['package']) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?',item['version']):raise ValueError('Invalid npm pin.')
        commands=[['npm','install','--prefix',str(dest),'--ignore-scripts','--no-audit','--no-fund','--save-exact',item['package']+'@'+item['version']]]
    elif kind=='python':
        requirement=item['package']+' @ git+https://github.com/'+item['repository']+'.git@'+item['commit']
        if item['requirement']!=requirement:raise ValueError('Python requirement does not match source pin.')
        python=dest/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        constraints=item.get('constraints',[])
        if not all(isinstance(c,str) and re.fullmatch(r'[a-zA-Z0-9_.-]+==[0-9][a-zA-Z0-9.+-]*',c) for c in constraints):raise ValueError('Invalid dependency constraint.')
        commands=[['uv','venv','--python','3.13',str(dest)],['uv','pip','install','--python',str(python),'--prerelease=allow',requirement,*constraints]]
    elif kind=='release':asset=asset_for(item)
    elif kind not in ('bundle','external'):raise ValueError('Unsupported installation kind.')
    return {'integration':integration,'kind':kind,'destination':str(dest),'commands':commands,'asset':asset,
            'guide':item.get('setup_document'),'executed':False,
            'notice':'Third-party dependencies may execute build code. No account, hook, channel or background service is configured.'}

def unpack_release(data, destination):
    """Reject links, traversal, device names and oversized archives before writing."""
    checked(destination)
    if any(Path(destination).iterdir()):raise ValueError('Release destination must be empty.')
    if os.name=='nt':
        absolute=str(Path(destination).absolute())
        if not absolute.startswith('\\\\?\\'):
            absolute='\\\\?\\UNC\\'+absolute[2:] if absolute.startswith('\\\\') else '\\\\?\\'+absolute
        destination=Path(absolute)
    entries=[]; total=0
    if data[:2]==b'PK':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():continue
                if stat.S_ISLNK(info.external_attr>>16):raise ValueError('Archive links refused.')
                if info.file_size>180*1024*1024:raise ValueError('Archive member too large.')
                total+=info.file_size
                if total>400*1024*1024 or len(entries)>=40000:raise ValueError('Archive exceeds limits.')
                entries.append((info.filename,archive.read(info),info.external_attr>>16))
    else:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            for info in archive.getmembers():
                if info.isdir():continue
                if not info.isfile() or info.size>180*1024*1024:raise ValueError('Archive links/special entries refused.')
                total+=info.size
                if total>400*1024*1024 or len(entries)>=40000:raise ValueError('Archive exceeds limits.')
                entries.append((info.name,archive.extractfile(info).read(),info.mode))
    seen=set()
    for name,_,_ in entries:
        if '\\' in name or name.startswith('/') or any(p in ('','..','.') or re.search(r'[<>:"|?*\x00-\x1f]',p) or p.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',p) for p in name.split('/')):raise ValueError('Unsafe archive member.')
        if name.casefold() in seen:raise ValueError('Duplicate archive member.')
        seen.add(name.casefold())
    for name,body,mode in entries:
        # Fresh destination and fully validated members; not protection from a hostile concurrent writer.
        path=destination.joinpath(*PurePosixPath(name).parts);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as out:out.write(body)
        if os.name!='nt':path.chmod(0o755 if mode&0o111 else 0o644)

def install(root, integration, run=False):
    plan=install_plan(root,integration)
    if not run:return plan
    if plan['kind'] in ('bundle','external'):raise ValueError('Use the bundled skill activation or the platform-specific guide for this integration.')
    dest=Path(plan['destination'])
    if dest.exists():raise ValueError('Local installation already exists; preserve it and inspect before changing versions.')
    for command in plan['commands']:
        if not shutil.which(command[0]):raise ValueError('Missing prerequisite: '+command[0])
    dest.parent.mkdir(parents=True,exist_ok=True)
    if plan['asset']:
        asset=plan['asset']
        if not asset['url'].startswith('https://github.com/'+entry(root,integration)['repository']+'/releases/download/'):raise ValueError('Unexpected release URL.')
        with urllib.request.urlopen(asset['url'],timeout=90) as response:data=response.read(150*1024*1024+1)
        if len(data)>150*1024*1024 or hashlib.sha256(data).hexdigest()!=asset['digest'].split(':')[1]:raise ValueError('Release digest mismatch or oversized download.')
        dest.mkdir();unpack_release(data,dest)
    else:
        for command in plan['commands']:
            argv=native_package_manager(command)
            receipt,code=execute_trusted(root,argv,operation='install-'+integration,
                output_mode='discard',identity=entry(root,integration),**execution_limits(root))
            if code:raise ValueError('Installation did not complete; inspect .workspace/runs/latest.json. Partial local directory retained.')
        if plan['kind']=='npm':
            item=entry(root,integration)
            lock=json.loads((dest/'package-lock.json').read_text(encoding='utf-8'))
            actual=lock['packages']['node_modules/'+item['package']].get('integrity')
            if actual!=item['integrity']:raise ValueError('npm root package integrity differs from catalog.')
    fingerprint=hashlib.sha256(json.dumps(entry(root,integration),sort_keys=True).encode()).hexdigest()
    (dest/'_ready.json').write_text(json.dumps({'catalog_sha256':fingerprint,'status':'installed; runtime and account setup separate'}),encoding='utf-8')
    return {**plan,'executed':True}

def executable(root, ident):
    item=entry(root,ident);base=checked(root,'.workspace/tools/'+ident)
    marker=base/'_ready.json'
    if marker.exists():
        fingerprint=hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()
        if read_json(root,marker.relative_to(root)).get('catalog_sha256')!=fingerprint:raise ValueError('Installation receipt is stale.')
        command=item.get('executable')
        candidates=[base/'node_modules/.bin'/(command+('.cmd' if os.name=='nt' else '')),base/('Scripts' if os.name=='nt' else 'bin')/(command+('.exe' if os.name=='nt' else ''))]
        if item['kind']=='release':
            # Official release has one top-level directory; avoid walking dependencies.
            candidates+=list(base.glob('*/'+command+('.exe' if os.name=='nt' else '')))+list(base.glob('*/'+command+'.cmd'))
            if os.name!='nt':candidates+=list(base.glob('*/'+command))
        for p in candidates:
            if p.is_file():return str(p)
    # Only externally managed tools may use PATH; local installs never silently switch versions.
    if item['kind']=='external' and item.get('executable'):return shutil.which(item['executable'])
    return None


def execution_limits(root):
    from foundation import load_policy
    return dict(load_policy(root)['execution'])


def native_package_manager(command):
    """Bypass Windows npm.cmd so user arguments never pass through cmd.exe."""
    binary=shutil.which(command[0])
    if not binary:raise ValueError('Missing package-manager prerequisite.')
    if command[0]=='npm' and binary.lower().endswith('.cmd'):
        base=Path(binary).parent
        script=base/'node_modules/npm/bin/npm-cli.js'
        node=base/'node.exe'
        if not script.is_file():raise ValueError('Could not resolve native npm entrypoint; inspect Node installation.')
        selected=str(node) if node.is_file() else shutil.which('node')
        if not selected:raise ValueError('Node is required for npm.')
        return [selected,str(script),*command[1:]]
    return [binary,*command[1:]]


def runtime_argv(root,ident,arguments):
    command=executable(root,ident)
    if not command:raise ValueError('CLI is not locally installed; use install preview or its guide.')
    item=entry(root,ident)
    base=checked(root,'.workspace/tools/'+ident)
    if item['kind']=='python':
        python=checked(root,(base/('Scripts/python.exe' if os.name=='nt' else 'bin/python')).relative_to(root))
        return [str(python),'-B',str(checked(root,'tools/python_cli.py')),item['executable'],*arguments]
    if item['kind']=='npm':
        if not re.fullmatch(r'[@a-z0-9/_.-]+',item['package']):raise ValueError('Invalid package name.')
        package=checked(root,(base/'node_modules'/item['package']).relative_to(root))
        metadata=read_json(package,'package.json')
        entrypoint=metadata.get('bin')
        if isinstance(entrypoint,dict):entrypoint=entrypoint.get(item['executable'])
        if not isinstance(entrypoint,str):raise ValueError('Package executable entrypoint is missing.')
        target=checked(package,entrypoint)
        if not target.is_file():raise ValueError('Package executable entrypoint is missing.')
        node=shutil.which('node')
        if not node:raise ValueError('Node is required for this integration.')
        return [node,str(target),*arguments]
    if item['kind']=='release' and ident=='skilled' and command.lower().endswith('.cmd'):
        package=Path(command).parent
        node=checked(root,(package/'runtime/node.exe').relative_to(root))
        bootstrap=checked(root,(package/'app/dist/src/bootstrap.js').relative_to(root))
        if not node.is_file() or not bootstrap.is_file():raise ValueError('Pinned skillEd native entrypoint is missing.')
        return [str(node),str(bootstrap),*arguments]
    return [command,*arguments]


def run_integration(root,ident,arguments):
    return execute_trusted(root,runtime_argv(root,ident,arguments),operation='run-'+ident,
        output_mode='discard' if ident=='doppler' else 'redact',
        identity=entry(root,ident),**execution_limits(root))


def run_doppler(root,project,config,child,names):
    command=doppler_command(project,config,child,names)
    binary=shutil.which('doppler')
    if not binary:raise ValueError('Install Doppler using its platform guide first.')
    command[0]=binary
    # Injected values are unknown here. Discard both streams; never echo or log them.
    return execute_trusted(root,command,operation='doppler',output_mode='discard',
        **execution_limits(root))

def doppler_command(project, config, command, names):
    if not all(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}',x or '') for x in (project,config)):raise ValueError('Explicit Doppler project and config are required.')
    if not names or not all(re.fullmatch(r'[A-Z_][A-Z0-9_]*',n) for n in names):raise ValueError('Specify only the required secret names, never values.')
    if not command or not command[0] or command[0].startswith('-'):raise ValueError('A child executable is required.')
    return ['doppler','run','--project',project,'--config',config,'--no-fallback','--no-check-version','--only-secrets',','.join(names),'--',*command]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default=str(DEFAULT_ROOT))
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('list');sub.add_parser('doctor');sub.add_parser('verify')
    p=sub.add_parser('install');p.add_argument('integration');p.add_argument('--run',action='store_true')
    p=sub.add_parser('activate');p.add_argument('integration');p.add_argument('skill');p.add_argument('--host',choices=HOSTS,default='claude');p.add_argument('--write',action='store_true')
    p=sub.add_parser('run');p.add_argument('integration');p.add_argument('arguments',nargs=argparse.REMAINDER)
    p=sub.add_parser('doppler');p.add_argument('--project',required=True);p.add_argument('--config',required=True);p.add_argument('--only',required=True);p.add_argument('--run',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args();root=checked(args.root)
    if args.action=='list':
        result=[{**item,'available_skills':[p.name for p in available_skills(root,ident)]} for ident,item in catalog(root).items()]
    elif args.action=='verify':
        result=verify_bundles(root);print(json.dumps(result,indent=2));return 0 if result['ok'] else 1
    elif args.action=='doctor':
        result={'integrity':verify_bundles(root),'integrations':[{'id':ident,'bundled_skills':[p.name for p in available_skills(root,ident)],'local_cli_available':bool(executable(root,ident)),'account_status':'not checked','runtime_status':'not checked'} for ident in catalog(root)]}
        print(json.dumps(result,indent=2));return 0 if result['integrity']['ok'] else 1
    elif args.action=='activate':result=activate(root,args.integration,args.skill,args.host,args.write)
    elif args.action=='install':result=install(root,args.integration,args.run)
    elif args.action=='run':
        extra=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
        result,code=run_integration(root,args.integration,extra)
        print(json.dumps(result,indent=2));return code
    else:
        child=args.command[1:] if args.command[:1]==['--'] else args.command
        command=doppler_command(args.project,args.config,child,args.only.split(','))
        if args.run:
            result,code=run_doppler(root,args.project,args.config,child,args.only.split(','))
            print(json.dumps(result,indent=2));return code
        result={'executed':False,'project':args.project,'config':args.config,'secret_names':args.only.split(','),'child_executable':child[0],'arguments':'omitted from preview','fallback_file':False}
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,KeyError,subprocess.SubprocessError,zipfile.BadZipFile,tarfile.TarError) as error:
        print(json.dumps({'ok':False,'error':redact(str(error),secret_values())}));sys.exit(1)
