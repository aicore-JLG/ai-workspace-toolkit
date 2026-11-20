# Offline foundation acceptance

Run from the kit directory:

```text
python tools/evaluate.py
python tools/evaluate.py --run
python tools/evaluate.py --status
```

The default command previews the source fingerprint without writing files.
`--run` executes trusted local Python tests in fresh synthetic projects, bounded
to 120 seconds and 64 KiB of captured worker output. It uses the shared foreground
resource lease. It makes no model/provider calls and does not open real projects.

`tests/test_acceptance.py` checks four workflows using real CLI subprocesses:

1. Start, checkpoint and resume in new processes; propose/confirm project memory,
   recall it only in its owner project, query it from the session packet, and
   verify forgetting removes it from later recall without stored packet copies.
2. Run an actual small application's checks for empty, positive and signed sums;
   permit verified finish only with current passing evidence, then introduce an
   incorrect result and confirm stale/failed checks prevent success claims.
3. Recover an unfinished session's next step and blockers, refusing blind
   overwrite and stale checkpoint revisions.
4. Check the evaluator itself in a separate tiny fixture: read-only preview,
   passing receipt, malformed receipt rejection, stale source detection, failed
   checks and an empty suite. The fixture does not recursively run this suite.

The compact report is `.workspace/evaluations/latest.json`. It contains source
hashes, interpreter/platform identity, test counts, failed case ids and elapsed
time. Raw output, tracebacks, memory values and project paths are not retained.
The test cases use only synthetic data. `--status` invalidates the receipt if any
top-level Python tool, acceptance case or interpreter/platform identity changes.
An interrupted resource lease requires inspection before recovery.

Zero tests, skips, expected failures, unexpected successes, actual failures,
errors, timeouts and changes during execution all prevent a passing result.
The source must be trusted before `--run`; a local receipt is not tamper-proof
attestation or a sandbox. This suite demonstrates the named local behavior. It
does not measure model accuracy, prompt injection resistance of a live model,
authenticated services, host startup hooks, paid evaluations or every operating
system. Keep those measurements separate from these deterministic checks.
