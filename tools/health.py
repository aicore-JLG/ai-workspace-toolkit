"""Read-only diagnosis for one selected project. Never cleans or promotes files."""
import argparse
import json
from pathlib import Path
from foundation import load_policy
from memory import MemoryStore
import session
import verify


def inspect_project(kit_root, project_root):
    policy = load_policy(kit_root)
    root = verify.strict_root(project_root)
    verify.read_bytes(root, 'PROJECT.md', 1024*1024)
    findings = []

    def add(code, action):
        findings.append({'code': code, 'action': action})

    state = verify.safe_path(root, 'SESSION-STATE.md', must_exist=False)
    if state.exists():
        lines = len(verify.read_bytes(root, 'SESSION-STATE.md', 1024*1024).splitlines())
        if lines > policy['maintenance']['state_line_limit']:
            add('state_compaction', 'Use hash-checked workspace compaction; preserve unresolved work and the old state.')
    else:
        add('state_missing', 'Create the concise project state or use the session lifecycle for an explicit handoff.')
    store = MemoryStore(root)
    confirmed, pending = store.search(limit=50), store.pending(limit=50)
    if pending:
        add('memory_pending', 'Review proposed memory against its source; confirm, explicitly replace a conflict, or forget obsolete notes.')
    memory = {'confirmed_sample_count': len(confirmed), 'pending_sample_count': len(pending),
              'sample_limit': 50, 'values_included': False}
    data, revision = session.load(root)
    session_state = 'missing'
    if data is None:
        add('session_missing', 'Start a scoped session with the objective, acceptance criteria and affected inputs.')
    else:
        packet = session.packet(root, data, revision)
        session_state = packet['status']
        if packet['changed_inputs'] or packet['missing_inputs']:
            add('session_changed', 'Resume, inspect changed or missing inputs, and checkpoint current work before relying on the old handoff.')
        if packet['context']['omitted']:
            add('context_omitted', 'Read the omitted project instructions explicitly; do not assume the context packet is complete.')
        if packet['check_status']['status'] in {'incomplete_coverage', 'invalid_or_unavailable'}:
            add('session_check_' + packet['check_status']['status'], 'Declare and check every affected session input; partial coverage cannot establish readiness.')
        if data['blockers']:
            add('session_blocked', 'Resolve recorded blockers or leave an honest unverified handoff.')
        if data['status'] == 'verified' and not packet['verification_current']:
            add('session_verification_stale', 'Rerun relevant checks; the previous verified handoff no longer establishes current success.')
    config_name = data['verification']['config'] if data and data['verification'] else 'checks.json'
    config = verify.safe_path(root, config_name, must_exist=False)
    verification_state = 'unconfigured'
    if config.exists():
        try:
            receipt, code = verify.status(root, config_name)
            verification_state = receipt['status']
        except (OSError, ValueError, KeyError, TypeError):
            code, verification_state = 1, 'invalid'
        if code:
            add('verification_' + verification_state, 'Inspect the declared trusted check and run it against current inputs.')
    else:
        add('verification_unconfigured', 'Declare a meaningful project check and its complete input dependencies in checks.json.')
    for name in ('.workspace/runs/resource.lock', '.workspace/verification/run.lock', session.LOCK, '.workspace/memory.lock'):
        if verify.safe_path(root, name, must_exist=False, allow_runtime=True).exists():
            add('operation_lock', 'Inspect the active or interrupted operation before recovery; never remove a live lock blindly.')
    return {'ready': not findings, 'read_only': True, 'findings': findings,
            'session': session_state, 'verification': verification_state, 'memory': memory,
            'policy': policy, 'optional_services': 'not checked',
            'notice': 'Local health indicators only. No deletion, provider calls, model-quality evaluation, account probe or global scan.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit-root', default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--root', required=True)
    a = p.parse_args(argv)
    try:
        report = inspect_project(a.kit_root, a.root)
        print(json.dumps(report, indent=2))
        return 0 if report['ready'] else 1
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'ready': False, 'error': 'Invalid or inaccessible selected project, policy, session or memory. No files changed.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
