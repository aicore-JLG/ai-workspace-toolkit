# Coordinated specialists and model selection

Status: implemented reusable workspace. `tools/orchestrate.py` coordinates real subscription CLI subprocesses through `tools/worker_provider.py`; `tools/client_scope.py` builds bounded project packets. Live Windows Codex tasks completed through builders, fixed checks, fresh review, guarded application and hidden checks. A fresh reviewer also caught a planted defect and application was blocked. Offline contracts cover further failure cases. These narrow observations do not establish Claude execution, general model quality or every recipient environment. Follow [the worked workflow](../workflows/coordinated-build.md).

## Required working behavior

One coordinator turns the request into bounded jobs. Straightforward tasks can stay with one worker. Independent jobs may run together; dependent jobs wait. Each worker receives only the selected project's relevant rules, sources, acceptance criteria and permitted work scope. The coordinator integrates results, obtains independent review and saves recoverable run state. Save the project session handoff explicitly after application using the foundation workflow.

Model selection and reasoning effort must be actual supported execution parameters. Fast models may handle straightforward retrieval or tightly scoped transformations; difficult planning, implementation and review may need stronger reasoning. These are starting hypotheses to measure, not fixed claims about which model is best. Preserve the owner's choices and active session settings. Configure only newly requested workers within the task's authority.

The complete workflow is: request -> scoped jobs -> appropriate specialists -> integration and checks -> fresh review -> verified result -> proposed reusable lessons. Parallelism and worker counts are means, not success metrics.

## Implemented execution layer

- The current route uses fresh packet-only Claude/Codex CLI processes. The host running the coordinator does not need native subagents. Model and effort are explicit CLI/config parameters, not a sentence asking a worker to use a different model. Native host orchestration is an alternative future adapter, not an additional installed capability.
- Subscription preflight checks installed CLI capabilities and the login route. Conflicting API environment/configuration overrides, unknown authentication and supported-route policy conflicts are refused. No API fallback is supplied. The initial Claude path supports selected personal subscriptions; managed policies and unsupported platform/account combinations fail closed. No accounts or global settings are changed.
- A subscription login is not a spending cap. Preflight does not verify remaining included allowance or account-level usage-credit settings. An included-only trial requires separate current evidence before generation; unknown billing state remains a blocker. See the [recipient pilot](RECIPIENT-PILOT.md) for the measured comparison.
- Each job declares an identifier, role, dependencies, scoped inputs, permitted files and provider/model/effort. The manifest sets the shared timeout, acceptance-check configuration and required reviewer. Reject unsupported settings clearly. Record requested and provider-confirmed settings separately; unavailable observations remain unknown.
- Concurrency and attempts are bounded. Workers receive explicit packets and return replacement proposals for disjoint declared files. They have no project filesystem tools. The coordinator stages proposals, runs the user's fixed trusted checks, then requests review. Resumption uses a fresh staging directory and preserves completed worker results; unknown cleanup retains a lock. Tests, entry instructions, dependency manifests and check configuration cannot be worker outputs.
- Start review in a fresh context with original requirements, final artifact and check evidence. Exclude the maker's private reasoning and preferred verdict. Bind review to artifact hashes; edits invalidate it. The existing session tool's `verified` status covers current declared checks and does not itself establish this review.
- Job state and outcomes stay in the owning project's existing private runtime area. `--apply RUN_ID` previews application; `--write` applies only frozen reviewed bytes after current source/check/review validation, with original-file backups. Partial application preserves its journal and lock rather than overwriting concurrent work. Run ordinary project verification and save the handoff after application.
- Trusted checks execute code with the caller's OS privileges, using a reduced environment without inherited service credentials. They are not an OS sandbox. A restricted OS identity/container and separated credentials are needed before claiming confidentiality against arbitrary code. See [security boundaries](SECURITY-BOUNDARIES.md).

## Files and commands

The existing layout stays intact. These files now implement the local route:

```text
tools/orchestrate.py                 job validation, scheduling, result collection
tools/worker_provider.py            isolated subscription CLI adapters
tools/client_scope.py               exact-file project and instruction boundaries
config/orchestration.example.json   inert worker/model/effort profile example
config/orchestration.codex.example.json  optional Codex profile, explicit models/effort
workflows/coordinated-build.md      task execution and independent review procedure
tests/test_orchestration.py         deterministic execution-contract regressions
examples/orchestration-project/     two deliberately broken synthetic functions and fixed tests
<project>/.workspace/orchestration/ private job state, usage and outcome records
```

Preview: `python -B tools/orchestrate.py --manifest config/orchestration.example.json`. Substitute `config/orchestration.codex.example.json` for Codex. Add `--preflight` for help/authentication checks without generation. Add `--run` only for an authorised account-funded run; it consumes included allowance or account credits and executes trusted checks. The workflow documents status, resume and explicit apply. `tools/launch.py` remains the separate provider-neutral brief generator; it does not run workers.

## Release acceptance

The offline regressions cover execution contracts. Before describing the candidate as recipient-proven subscription orchestration, observe the following on each declared supported host/platform:

1. Preview makes no model calls or account/configuration changes; an explicitly requested run creates real, identifiable workers.
2. Requested model and effort are passed through supported controls. Missing capabilities and conflicting authentication fail clearly. Evidence distinguishes requested settings from observed settings.
3. Two independent workers demonstrably overlap. Dependencies, timeouts, cancellation, writer conflicts and bounded retries behave correctly. Failure prevents downstream success claims.
4. A fresh reviewer finds a seeded defect. Changing the artifact invalidates review. Completion requires both current acceptance checks and all required independent review evidence.
5. Restart recovers pending work without duplicating completed external actions. Handoffs identify inputs, decisions, failures, ownership and the next action.
6. An untouched recipient extraction completes setup, a real task, review and a resumed handoff on each declared supported host/OS combination. Optional services are validated separately when enabled.
7. Logs contain no credentials and are excluded from exports. Subscription authentication and observed allowance behavior are verified without changing active sessions or adding API billing.

## Measure verified outcomes

Compare the current workflow with the candidate on a bug with regression tests, independent changes requiring integration, and a sourced research task resumed in a fresh session. Freeze inputs and acceptance criteria; initially hold model and effort constant to isolate orchestration. Use repeated trials, then test model/effort policies separately on held-out tasks.

Record total time through review/rework, all worker/reviewer usage, actual defects, failed attempts, retries and owner questions/intervention time. Record subscription allowance changes where the provider exposes them, and unrelated account activity that could confound the measurement. Token totals and estimated API prices are not exact subscription-quota consumption. Unknown usage stays unknown.

Only propose a routing or skill change when evidence supports it, no material quality regression occurs and owner intervention does not increase. Keep the baseline and rollback. Neither a worker nor an optimiser may rewrite its own acceptance tests or promote itself solely on its own success report.

The current [validation record](VALIDATION.md) distinguishes offline mechanics, an earlier interrupted baseline and a later clean comparison. In the clean small fixture, parallel workers took 24.30 seconds versus 31.12 seconds for one builder, with greater token usage; both passed hidden checks. One sample does not establish a general speed advantage. Use one worker for simple tasks and parallel jobs for separable work. Routing uses explicit recipient choices; automatic model tuning or skill promotion is not enabled. RooFlow or Ruflo is not a dependency. Human feedback is optional for this shared workspace; stronger performance or platform claims need further evidence.
