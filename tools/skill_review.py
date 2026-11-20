"""Content-bound skill hygiene scan and review attestation; not a malware detector.

The reviewer must inspect the complete source, including instructions and scripts.
Receipts are local self-attestations, not identity or independence guarantees.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid
from verify import digest, exclusive_lock, read_bytes, runtime_dir, safe_path, strict_root

RULES = {
    'remote-code': r'(?i)(curl|wget)[^\n]{0,300}\|\s*(ba)?sh|(?:eval|exec)\s*\(',
    'credential-access': r'(?i)\.env\b|\.ssh\b|(?:api[_-]?key|access[_-]?token|password)\b',
    'external-transfer': r'(?i)https?://|requests\.(?:post|put)|fetch\s*\(',
    'destructive-operation': r'(?i)\brm\s+-[rf]|Remove-Item|shutil\.rmtree|git\s+(?:reset|clean)\b',
    'instruction-override': r'(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|disable\s+(?:security|verification)',
}


def names(integration, skill):
    if any(not isinstance(v, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,70}', v) for v in (integration, skill)):
        raise ValueError('Invalid integration or skill name.')
    return '.workspace/skill-reviews/' + integration + '/' + skill


def snapshot(root, integration, skill):
    import integrations
    names(integration, skill)
    root = strict_root(root)
    if not integrations.verify_bundles(root)['ok']:
        raise ValueError('Bundle integrity failed.')
    matches = [p for p in integrations.available_skills(root, integration) if p.name == skill]
    if len(matches) != 1:
        raise ValueError('Select a unique bundled skill.')
    hashes, findings = {}, []
    total = 0
    for path in sorted(matches[0].rglob('*')):
        relative = path.relative_to(root).as_posix()
        safe_path(root, relative)
        if not path.is_file():
            continue
        raw = read_bytes(root, relative, 8*1024*1024)
        total += len(raw)
        if len(hashes) >= 1000 or total > 32*1024*1024:
            raise ValueError('Skill source exceeds review limits.')
        hashes[relative] = digest(raw)
        try:
            text = raw.decode('utf-8')
            codes = [code for code, pattern in RULES.items() if re.search(pattern, text)]
        except UnicodeError:
            codes = ['binary-review-required']
        for code in codes:
            findings.append({'id': digest((relative + ':' + code).encode())[:20], 'path': relative, 'rule': code})
    identity = {'files': hashes, 'catalog': integrations.entry(root, integration),
                'scanner': digest(Path(__file__).read_bytes())}
    fingerprint = digest(json.dumps(identity, sort_keys=True).encode())
    return {'schema': 1, 'integration': integration, 'skill': skill, 'fingerprint': fingerprint,
            'files': hashes, 'findings': findings,
            'notice': 'Heuristic hygiene only. Findings may be benign; absence of findings does not establish safety. Review complete source.'}


def save(root, relative, data):
    folder = runtime_dir(root, str(Path(relative).parent).replace('\\', '/'))
    temporary = folder / ('record-' + uuid.uuid4().hex + '.tmp')
    destination = safe_path(root, relative, must_exist=False, allow_runtime=True)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2)
        safe_path(root, relative, must_exist=False, allow_runtime=True)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            safe_path(root, temporary.relative_to(root).as_posix(), allow_runtime=True).unlink()


def scan(root, integration, skill):
    root = strict_root(root)
    base = names(integration, skill)
    with exclusive_lock(root, base + '/review.lock'):
        result = snapshot(root, integration, skill)
        save(root, base + '/scan.json', result)
    return result


def attest(root, integration, skill, fingerprint, acknowledged, reviewer, rationale):
    root = strict_root(root)
    base = names(integration, skill)
    if any(not isinstance(v, str) or not v.strip() or len(v) > cap for v, cap in ((reviewer, 120), (rationale, 2000))):
        raise ValueError('A reviewer and concise non-secret rationale are required.')
    with exclusive_lock(root, base + '/review.lock'):
        current = snapshot(root, integration, skill)
        saved = json.loads(read_bytes(root, base + '/scan.json', 1024*1024, True))
        if fingerprint != current['fingerprint'] or saved != current:
            raise ValueError('Scan is missing, modified or stale; scan and inspect current source.')
        expected = {row['id'] for row in current['findings']}
        if not isinstance(acknowledged, list) or any(not isinstance(v, str) for v in acknowledged) or set(acknowledged) != expected:
            raise ValueError('Explicitly acknowledge every finding after reviewing its scope and behavior.')
        record = {'schema': 1, 'fingerprint': fingerprint, 'accepted': True,
                  'acknowledged': sorted(expected), 'reviewer': reviewer, 'rationale': rationale,
                  'reviewed_at': datetime.now(timezone.utc).isoformat(),
                  'notice': 'Local self-attestation; not an independent security certification.'}
        save(root, base + '/review.json', record)
    return record


def require_review(root, integration, skill):
    root = strict_root(root)
    base = names(integration, skill)
    current = snapshot(root, integration, skill)
    saved = json.loads(read_bytes(root, base + '/scan.json', 1024*1024, True))
    review = json.loads(read_bytes(root, base + '/review.json', 16384, True))
    fields = {'schema', 'fingerprint', 'accepted', 'acknowledged', 'reviewer', 'rationale', 'reviewed_at', 'notice'}
    if not isinstance(review, dict) or set(review) != fields or type(review['schema']) is not int:
        raise ValueError('Invalid review attestation schema.')
    for field, limit in (('reviewer', 120), ('rationale', 2000), ('reviewed_at', 40), ('notice', 200)):
        value = review[field]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Incomplete review attestation.')
    if datetime.fromisoformat(review['reviewed_at']).tzinfo is None:
        raise ValueError('Review timestamp requires a timezone.')
    if saved != current or review.get('schema') != 1 or review.get('fingerprint') != current['fingerprint'] or review.get('accepted') is not True or review.get('acknowledged') != sorted(row['id'] for row in current['findings']):
        raise ValueError('A current source scan and accepted review are required before activation.')
    return review


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('action', choices=['scan', 'accept', 'status'])
    p.add_argument('integration'); p.add_argument('skill')
    p.add_argument('--fingerprint'); p.add_argument('--ack', action='append', default=[])
    p.add_argument('--reviewer'); p.add_argument('--rationale')
    a = p.parse_args(argv)
    try:
        if a.action == 'scan': result = scan(a.root, a.integration, a.skill)
        elif a.action == 'accept': result = attest(a.root, a.integration, a.skill, a.fingerprint, a.ack, a.reviewer, a.rationale)
        else: result = require_review(a.root, a.integration, a.skill)
        print(json.dumps(result, indent=2)); return 0
    except (OSError, ValueError, KeyError):
        print(json.dumps({'ok': False, 'error': 'Review refused: inspect names, current bundle integrity, scan fingerprint and finding acknowledgements.'})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
