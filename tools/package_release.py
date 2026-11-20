"""Package only untouched, explicitly manifested release files; never personal data."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify import safe_path, strict_root

def package(root, output):
    root=strict_root(root)
    manifest=safe_path(root,'RELEASE-MANIFEST.json')
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1:raise ValueError('Unsupported release manifest.')
    payload=[];seen=set()
    for item in data['files']:
        name=item['path']
        if name in seen or name=='RELEASE-MANIFEST.json':raise ValueError('Invalid manifest entry.')
        seen.add(name)
        p=safe_path(root,name)
        if not p.is_file() or p.stat().st_size>8*1024*1024:raise ValueError('Invalid release file.')
        content=p.read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['sha256']:raise ValueError('Release source changed: '+name)
        payload.append((name,content))
    if len(payload)>1000 or sum(len(b) for _,b in payload)>32*1024*1024:raise ValueError('Release exceeds limits.')
    payload.append(('RELEASE-MANIFEST.json',manifest.read_bytes()))
    output=Path(output)
    # Exclusive mode preserves any previous release. Only manifest entries are read.
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,body in sorted(payload):
            info=zipfile.ZipInfo(name,(2026,11,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,body)
    return {'output':str(output),'files':len(payload),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(package(a.root,a.output),indent=2))
    except (ValueError,OSError,KeyError) as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
