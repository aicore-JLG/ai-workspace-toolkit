#!/usr/bin/env python3
"""Run offline foundation acceptance cases in fresh synthetic projects.

Preview is read-only. --run executes trusted local test code, not model calls.
Reports contain counts and source hashes, never captured test output or tracebacks.
This checks local lifecycle contracts, not AI answer quality or live integrations.
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import unittest
import uuid

import run as runner
import verify

CASE = 'tests/test_acceptance.py'
LATEST = '.workspace/evaluations/latest.json'
NOTICE = 'Offline synthetic workflow acceptance only; not a model accuracy benchmark, security certification or live service check.'


def identity(root):
    root = verify.strict_root(root)
    folder = verify.safe_path(root, 'tools')
    names = sorted(path.relative_to(root).as_posix() for path in folder.glob('*.py'))
    required = {'tools/evaluate.py', 'tools/memory.py', 'tools/session.py', 'tools/verify.py', 'tools/run.py'}
    if not required.issubset(names) or len(names) > 100:
        raise ValueError('Incomplete or oversized foundation tool set.')
    files = verify.selected_files(root, names + [CASE])
    result = {'files': {name: verify.digest(raw) for name, raw in files.items()},
              'python': sys.version, 'platform': sys.platform}
    return result, verify.digest(json.dumps(result, sort_keys=True).encode('utf-8'))


def clean_id(test):
    value = test.id()
    return value if re.fullmatch(r'[A-Za-z0-9_.]{1,200}', value) else 'redacted-case-id'


def worker(root):
    """Internal process protocol; all test diagnostics are discarded."""
    result = unittest.TestResult()
    import_failed = False
    with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink), redirect_stderr(sink):
        try:
            path = verify.safe_path(root, CASE)
            spec = importlib.util.spec_from_file_location('foundation_acceptance', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            unittest.defaultTestLoader.loadTestsFromModule(module).run(result)
        except Exception:
            import_failed = True
    counts = {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors) + int(import_failed),
              'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures),
              'unexpected_successes': len(result.unexpectedSuccesses)}
    failed_ids = [clean_id(test) for test, _ in result.failures + result.errors]
    if import_failed:
        failed_ids.append('suite-load-error')
    # Acceptance cannot be declared green by skipping or expecting failures.
    passed = counts['run'] > 0 and all(value == 0 for name, value in counts.items() if name != 'run')
    data = {'counts': counts, 'failed_cases': failed_ids, 'passed': passed}
    print(json.dumps(data))
    return 0 if passed else 1


def validate_outcome(data):
    keys = {'run', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'}
    if not isinstance(data, dict) or set(data) != {'counts', 'failed_cases', 'passed'}:
        raise ValueError('Invalid acceptance outcome.')
    counts = data['counts']
    if not isinstance(counts, dict) or set(counts) != keys or any(type(v) is not int or not 0 <= v <= 10000 for v in counts.values()):
        raise ValueError('Invalid acceptance counts.')
    if not isinstance(data['failed_cases'], list) or len(data['failed_cases']) > 1000 or any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', v) for v in data['failed_cases']):
        raise ValueError('Invalid failed case identifiers.')
    passed = counts['run'] > 0 and all(v == 0 for key, v in counts.items() if key != 'run')
    if type(data['passed']) is not bool or data['passed'] != passed or (passed and data['failed_cases']):
        raise ValueError('Inconsistent acceptance result.')
    return data


def save(root, receipt):
    folder = verify.runtime_dir(root, '.workspace/evaluations')
    temporary = folder / ('report-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        target = verify.safe_path(root, LATEST, must_exist=False, allow_runtime=True)
        verify.check_chain(folder)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            verify.safe_path(root, '.workspace/evaluations/' + temporary.name, allow_runtime=True).unlink()


def evaluate(root):
    root = verify.strict_root(root)
    identity(root)
    with runner.resource_lease(root) as lease:
        before, fingerprint = identity(root)
        started = time.monotonic()
        outcome = {'counts': {'run': 0, 'failures': 0, 'errors': 1, 'skipped': 0, 'expected_failures': 0, 'unexpected_successes': 0}, 'failed_cases': ['worker-error'], 'passed': False}
        reason, unresolved = None, False
        try:
            code, reason, output, unresolved = runner.capture(
                [sys.executable, '-B', str(verify.safe_path(root, 'tools/evaluate.py')), '--root', str(root), '--worker'], root, 120, 65536)
            if reason is None:
                outcome = validate_outcome(json.loads(output[0]))
                if code != (0 if outcome['passed'] else 1):
                    reason = 'worker_protocol_error'
        except (OSError, ValueError, TypeError):
            reason = 'worker_error'
        try:
            _, after = identity(root)
            stable = fingerprint == after
        except (OSError, ValueError):
            stable = False
        status = reason or ('changed_during_evaluation' if not stable else 'passed' if outcome['passed'] else 'failed')
        receipt = {'schema': 1, 'status': status, 'passed': status == 'passed',
                   'fingerprint': fingerprint, 'identity': before, 'stable': stable,
                   'counts': outcome['counts'], 'failed_cases': outcome['failed_cases'],
                   'elapsed_seconds': round(time.monotonic() - started, 3),
                   'checked_at': datetime.now(timezone.utc).isoformat(), 'notice': NOTICE}
        save(root, receipt)
        lease['retain'] = unresolved
        return receipt, 0 if receipt['passed'] else 1


def status(root):
    root = verify.strict_root(root)
    current_identity, fingerprint = identity(root)
    if verify.safe_path(root, runner.LOCK, must_exist=False, allow_runtime=True).exists():
        return {'status': 'running_or_interrupted', 'passed': False, 'notice': NOTICE}, 1
    if not verify.safe_path(root, LATEST, must_exist=False, allow_runtime=True).exists():
        return {'status': 'missing', 'passed': False, 'notice': NOTICE}, 1
    data = json.loads(verify.read_bytes(root, LATEST, 1024 * 1024, True))
    expected = {'schema', 'status', 'passed', 'fingerprint', 'identity', 'stable', 'counts', 'failed_cases', 'elapsed_seconds', 'checked_at', 'notice'}
    if not isinstance(data, dict) or set(data) != expected or type(data['schema']) is not int or data['schema'] != 1:
        raise ValueError('Invalid evaluation receipt.')
    known_statuses = {'passed', 'failed', 'cancelled', 'changed_during_evaluation', 'worker_error',
                      'worker_protocol_error', 'timed_out', 'output_limit', 'incomplete_output'}
    if type(data['stable']) is not bool or not isinstance(data['status'], str) or data['status'] not in known_statuses:
        raise ValueError('Invalid evaluation state.')
    if data['fingerprint'] != fingerprint:
        return {'status': 'stale', 'passed': False, 'notice': NOTICE}, 1
    if data['identity'] != current_identity:
        raise ValueError('Inconsistent evaluation input identity.')
    if not isinstance(data['counts'], dict):
        raise ValueError('Invalid acceptance counts.')
    outcome_passed = data['counts'].get('run', 0) > 0 and all(v == 0 for k, v in data['counts'].items() if k != 'run')
    validate_outcome({'counts': data['counts'], 'failed_cases': data['failed_cases'], 'passed': outcome_passed})
    if ((data['status'] in {'passed', 'failed'} and not data['stable'])
            or (data['status'] == 'changed_during_evaluation' and data['stable'])
            or (data['status'] == 'passed' and not outcome_passed)
            or (data['status'] == 'failed' and outcome_passed)):
        raise ValueError('Contradictory evaluation state.')
    passed = data['status'] == 'passed' and data['stable'] is True and outcome_passed
    if type(data['passed']) is not bool or data['passed'] != passed:
        raise ValueError('Inconsistent evaluation receipt.')
    return data, 0 if passed else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]), help='Kit root, not a live project')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--status', action='store_true')
    mode.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        root = verify.strict_root(args.root)
        if args.worker:
            return worker(root)
        if args.run:
            result, code = evaluate(root)
        elif args.status:
            result, code = status(root)
        else:
            data, fingerprint = identity(root)
            result, code = {'status': 'preview', 'fingerprint': fingerprint, 'files': sorted(data['files']), 'notice': NOTICE + ' No code ran and no report was written.'}, 0
        print(json.dumps(result, indent=2))
        return code
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({'status': 'refused', 'passed': False, 'error': 'Invalid or unavailable acceptance source, receipt, scope or operation lock.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
