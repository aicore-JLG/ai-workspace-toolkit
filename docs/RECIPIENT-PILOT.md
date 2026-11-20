# Optional check of an untouched download

Use this checklist if you want to check your own setup or collect feedback. It is optional for sharing this workspace, not a formal product-certification process. Use a new extraction with synthetic projects and keep the original ZIP unchanged. The exercise checks whether a recipient can reach a verified result and resume it; it does not certify every optional integration or protect real client data.

## First session: offline foundation

1. Record the ZIP version/hash, operating system, Python version and AI host. Extract the entire ZIP, including `.agents` and `.claude`, into a new folder. Do not merge it with existing work.
2. Run the three commands below. Python 3.11+ is required. Missing optional tools should be reported without blocking the offline core.
3. Follow [the walkthrough](WALKTHROUGH.md): inspect the welcome project, run its checks, change a declared input in your copy and confirm the old check becomes stale. Run the check again.
4. Use [the setup prompt](../SETUP-PROMPT.md) with a neutral first project. Confirm it preserves the starter templates and creates only the selected project.
5. Follow [the foundation workflow](FOUNDATION.md) to save a meaningful checkpoint. Close and reopen the AI session. Resume from the saved state and confirm the objective, decisions, blockers and next action survive. A newly created project with no checks must not be described as verified.

```text
python -B tools/preflight.py
python -B tools/workspace.py doctor
python -B tools/integrations.py verify
```

The walkthrough executes trusted synthetic code with the current OS user's permissions. Use the [isolation pilot](ISOLATION-PILOT.md) before evaluating access boundaries. A folder named `Clients` is not an access-control wall.

## Optional session: real subscription workers

Use [the coordinated build](../workflows/coordinated-build.md) only after deliberately selecting a supported account and explicit worker/reviewer models. Confirm either available included allowance or explicit owner authorisation to use available existing account credits for this bounded trial. Authentication alone proves neither allowance nor spending authority. If the billing route or authority cannot be established, stop before generation and record that limitation. Existing-credit approval does not authorise purchases, top-ups, API fallback or changes to an organisation's policy.

Compare a two-builder run and a one-builder run on separate untouched copies of the same task. Give both the same requirements, fixed tests, review model and reasoning effort. Measure through the same final gate: accepted review, applied candidate and current passing checks. A failed run is a result, not a reason to hide it or weaken the tests. Record retries and their usage. Counterbalance the order and repeat with held-out tasks before adopting a model policy.

Suitable follow-up cases are a two-file code repair, a dependency-ordered feature and recovery of interrupted work. Keep real customer data out of the trial. Packet workers currently return file proposals; they do not browse repositories or run their own tools. Research quality needs separate source-verification cases.

## Record the result

| Field | Record |
|---|---|
| Environment | OS, Python, host/CLI versions; no usernames or credentials |
| Artifact | Release version and ZIP hash |
| Mode | Offline / one builder plus reviewer / parallel builders plus reviewer |
| Selection | Requested and provider-observed model and effort separately |
| Verified result | Pass, fail or blocked, with the actual acceptance gate |
| Time | Setup time separately from task start through verified application |
| Usage | Provider token fields, including cache fields; quota before/after only if available |
| Defects | Initial defects, failed checks/review findings, defects discovered afterward |
| Recovery | Failed attempts, retries, interruptions and recovery outcome |
| Owner help | Number and reason for interventions; separate initial account setup |
| Friction | Exact step, expected result and concise actual error code |

Unknown usage or observed effort stays unknown. Tokens are not an exact measure of subscription allowance or monetary cost. Do not submit raw prompts, project contents, `.workspace` logs, account files or secret values as feedback. A short sanitised report is enough.

## Release decision

The offline core, each provider route and each isolation environment have separate evidence. A successful Windows run does not establish macOS/Linux support. Share the untouched workspace with its tested scope and limits stated plainly, never a personalised working copy. Independent recipient feedback is useful optional follow-up. If a reported defect leads to a change, rerun the affected checks; do not advertise untested platforms or guarantees.
