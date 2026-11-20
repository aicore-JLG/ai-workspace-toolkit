# Coordinate a small build and a fresh review

This workflow uses `tools/orchestrate.py`. Workers receive explicit JSON packets
and return replacement proposals; they cannot browse the project or execute tools.
The coordinator stages proposals, runs the project's trusted checks and obtains a
fresh reviewer result. Applying the accepted candidate is a separate action.

The included exercise has two deliberately broken functions. Its initial checks
should fail. Run the exercise in a fresh extracted kit; keep the untouched release
separate from your populated workspace.

On Windows, use a short extraction path. Private run records add nested directories;
the development trial encountered a legacy path-length failure inside a deeply
nested checkout. A short fresh extraction resolved that fixture's setup failure.
No system-wide long-path setting is changed by the kit.

## Inspect the task without starting workers

From the kit root:

```text
python -B tools/orchestrate.py --manifest config/orchestration.example.json
```

Read the project brief, fixed tests, check command and manifest. Two independent
builders own `total.py` and `label.py`. They may run concurrently; neither can
replace the other's file. The example declares Sonnet with medium effort for the
builders and Opus with high effort for the separate reviewer. These are recipient
choices to validate, not a learned policy or proof of optimal performance.

For Codex, use `config/orchestration.codex.example.json` in place of the Claude
manifest in these commands. It declares GPT-6.2 Sol/medium builders and a separate
GPT-6.2 Astra/high reviewer, with one attempt per job. One Windows synthetic trial
completed with this requested profile. The CLI did not echo backend model/effort,
so those observed fields remained unknown. This is not proof of optimal routing.

Use an explicit model/effort policy supported by your CLI and subscription.
Unsupported choices fail; the system does not silently choose another model.
Provider-confirmed settings are recorded separately. Unknown observed effort or
usage remains unknown.

## Check the provider route without model calls

```text
python -B tools/orchestrate.py --manifest config/orchestration.example.json --preflight
```

Preflight checks local CLI capabilities and subscription authentication. It does
not prove that a real model task will succeed. Conflicting API environment or
configuration overrides are refused, even if the worker could strip them. The kit
does not clear your current environment, change active sessions or switch accounts.
Use a deliberately configured separate session if your current environment mixes
API and subscription routes.

Preflight does not check remaining included allowance or disable account-level
usage credits. Before an included-only trial, inspect the provider's usage page
and confirm enough allowance plus no automatic paid overage. If that cannot be
established, leave generation blocked. Record account setup time separately from
task execution; do not count an authentication probe as a successful model task.
If the owner instead authorises existing account credits, record that payer and
scope explicitly. A subscription login does not limit spending to included usage.

The initial Claude adapter is limited to supported personal subscription routes
without managed policy overrides. Account, host and operating-system limits must
be tested on the recipient's actual setup. Do not remove an organisation's policy
to make this exercise run.

## Start an explicitly requested subscription run

```text
python -B tools/orchestrate.py --manifest config/orchestration.example.json --run
```

This makes real worker and reviewer calls and consumes included allowance or
available account credits according to the provider's billing settings.
It also executes the trusted check command locally against a staged candidate.
Read that command first: checks execute with your user permissions and are not an
operating-system sandbox. Project scope checks and instruction files are not an
access-control wall.

Keep the returned run ID. The coordinator limits parallel jobs and attempts,
requires current check evidence, and binds the independent review to the final
candidate. A rejection, timeout or interrupted worker is not successful completion.
The original source files have not been changed at this stage.

The reviewer must use exactly `accept` or `revise`. Its `findings` array contains
only unresolved material defects or verification gaps. Acceptance requires `[]`;
positive observations and passed-check summaries do not belong in that field.
An accepting verdict with nonempty findings is still blocked, never silently fixed.

## Inspect or resume the run

Replace `RUN_ID` with the actual returned identifier:

```text
python -B tools/orchestrate.py --project examples/orchestration-project --status RUN_ID
python -B tools/orchestrate.py --manifest config/orchestration.example.json --run --resume RUN_ID
```

Status does not call a model. Resume can make further calls, remains subject to the
original attempt limits and refuses stale inputs. Do not blindly delete a retained
lock: it can mean process cleanup could not be confirmed. Inspect the private run
record and resolve the underlying condition first.

A rejected review is not eligible for a blind reroll. Resolve the findings in a revised task/manifest and start a new run. The current route requires at least one declared file deliverable so its checks and fresh review cover the actual result; research can produce a scoped report file. Automatic revision loops and learned model routing are not enabled.

Tests, instructions, dependencies and configuration are fixed inputs during a run.
If they need a legitimate change, handle it deliberately outside the worker
proposals and start a new run with new evidence. Do not weaken acceptance checks
to obtain a passing result.

## Review and explicitly apply the accepted candidate

```text
python -B tools/orchestrate.py --project examples/orchestration-project --apply RUN_ID
python -B tools/orchestrate.py --project examples/orchestration-project --apply RUN_ID --write
```

The first command previews application. The second changes the declared source
files only after rechecking source freshness, candidate hashes, current checks and
the accepting review. Existing files receive backups in the private run folder.
Concurrent edits or stale evidence are refused. Inspect any partial application
before retrying; do not overwrite unrelated work.

After application, run the ordinary project checks and save the actual handoff:

```text
python -B tools/verify.py --root examples/orchestration-project --run
```

Record what passed, what remains unverified and the next action in the project
state. Private run state, proposals, usage and backups stay in the project's
ignored `.workspace/orchestration/` folder and must not enter the shared release.

## Improve from evidence

Measure time through review and rework, all worker/reviewer usage, actual defects,
retries and owner intervention. Token totals are not exact subscription-quota
consumption. Compare fixed tasks and held-out cases before changing model routing.

This workflow does not install skills, rewrite its own tests, promote lessons to
memory automatically or run background learning. Save useful lessons as proposals
through the existing memory workflow; review them before confirmation.
