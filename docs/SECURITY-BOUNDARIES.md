# Security, hooks and client boundaries

The toolkit provides scoped inputs and local checks. It does not create an operating-system security boundary. A folder named `Clients/`, a skill instruction or a successful scan cannot prevent a process with wider access from reading another folder or using another account.

Status: the workspace implements the foundation, project-scoped orchestration and worker-adapter controls. Offline tests exercise scheduling, scoped packets, metadata validation, independent-review contracts, stale-evidence rejection and controlled application. Live Windows Codex synthetic tasks completed through review and application, and a seeded-defect review prevented application. These checks do not establish an OS sandbox, general model reliability or every provider/platform route. Process cleanup and host behavior require their own current release evidence. See the [validation record](VALIDATION.md) for the final checked scope.

## Four different kinds of protection

| Layer | What it does | What it does not establish |
|---|---|---|
| Instructions | Tell an agent which project to use, how to handle untrusted text and when to ask for missing authority | An agent cannot access anything outside that project |
| Deterministic tool gates | Refuse invalid paths, stale checks or unreviewed skill activation when the relevant tool is invoked | Every other host tool or subprocess follows the same restrictions |
| Host hooks | Let a particular AI host inspect or block events it actually emits and supports | Identical coverage in another host, or that a configured hook actually ran |
| OS/account isolation | Restricts filesystem access, identities, credentials and possibly network access outside the agent's discretion | Application correctness, trustworthy source material or a correct model answer |

The first two layers are part of the portable foundation. Global host hooks and OS/account isolation are not installed by this kit.

## What the existing tools enforce

- **Selected paths:** `tools/verify.py` supplies shared path validation. It rejects traversal, linked/reparse paths and designated credential/runtime locations on its supported routes. Root overview/context tools omit client pools unless an authorised project is selected explicitly. These checks constrain what these utilities collect; they do not constrain arbitrary host reads.
- **Memory and handoff scope:** `tools/memory.py` and `tools/session.py` bind their local stores to the selected root. A copied store cannot silently become another project's state. Recalled text is reference material, never authority to read more data or execute an action.
- **Skill activation:** `tools/skill_review.py` fingerprints source and records findings plus an explicit review attestation. `tools/integrations.py` requires the current attestation before staging and before activation. Source changes invalidate the evidence; existing destinations are preserved.
- **Verification:** `tools/verify.py` binds a check receipt to declared inputs. Missing, failed, changed or incomplete evidence cannot support the session tool's verified finish. Only declared dependencies are covered. A passing check does not by itself prove an independent review occurred.
- **Execution:** `tools/run.py` bounds time/output and coordinates cooperating calls through a lease. Integration logs are private and redacted on a best-effort basis. Doppler and installer output is discarded. Ordinary children still execute with the user's privileges and may create files or make network requests. See [execution details](EXECUTION-CORE.md).
- **Release export:** `tools/package_release.py` includes only hash-matching release-manifest entries. Personal runtime state and account setup are not included in the untouched release. Exporting a populated workspace manually bypasses this protection.

Receipts are local records, not tamper-proof evidence or authenticated reviewer identities. Someone able to rewrite the tools and records is outside the protection these tools provide.

## How orchestration hooks work

`tools/orchestrate.py` applies checks within its own execution path, using `tools/client_scope.py` and the worker adapter. These are lifecycle checks, not newly installed global Claude or Codex hooks:

1. **Before dispatch:** validate the selected client/project, allowed input paths, job dependencies, model/effort controls, intended subscription authentication and resource limits. Refuse unknown or conflicting settings before sending a packet.
2. **After a worker result:** validate the response contract, retain failures, account for available usage and reject unexpected tool events. A worker's claim that it succeeded is not sufficient.
3. **Before applying changes:** validate proposed destinations and the original input fingerprints, preserve rollback, prevent conflicting writers and reject changes outside the declared scope. A packet-only worker proposes changes; the controlled parent applies eligible changes.
4. **Before completion:** require current acceptance checks and the required fresh review of the exact artifact. Changed artifacts invalidate review. Interrupted jobs remain interrupted until inspected or safely resumed.

These controls have offline contract tests; the subscription-host acceptance gates are separate. Verify the current functions and test evidence before relying on them; event names alone do not prove coverage. Calls made outside the orchestrator do not automatically pass through its checks. Ordinary failed jobs may resume within the declared attempt budget. Cleanup uncertainty retains the execution lock and must be investigated rather than bypassed. Partial application preserves its record and backups without rolling back possible concurrent user edits.

The packet-only adapter design disables model tools and automatic discovery where the host supports it, and sends only explicitly selected material. This reduces opportunities for a worker to browse unrelated folders. It is not a substitute for testing that the installed host really honours those settings, nor for isolating the parent process when handling confidential clients. See [orchestration requirements](ORCHESTRATION.md).

## What a client wall means here

A client/project scope should choose exactly one project root, explicit inputs and permitted output paths. Do not collect other clients' memory, transcripts, project lists or credentials into its packet. Cross-project knowledge must be deliberately reviewed as generic, shareable material before reuse. Content already pasted into an allowed file may still contain another client's information; path checks cannot determine its rightful owner.

This is a **data-selection boundary**. It helps prevent accidental mixing through the toolkit's supported paths. It does not stop the same operating-system user, an unrestricted shell, a host connector or a compromised dependency from accessing other data available to that identity. A separate Git worktree prevents some editing collisions; it is not confidentiality isolation.

For a stronger boundary, configure and test isolation separately:

- Use a separate OS identity, VM or appropriately restricted container for confidential client work. Mount only that client's necessary files and approved generic tools, with read-only inputs where practical.
- Separate account/profile and credential access. Do not mount a shared credential directory or expose unrelated tokens through environment variables, MCP connections, browser profiles or desktop connectors.
- Permit only needed network destinations and services where the execution platform supports this. Confirm the destination account as well as the command's working directory.
- Test denial: a synthetic worker must fail to read a second client's canary, obtain its credentials or write outside its output scope. A successful in-scope task alone does not test isolation.

None of these OS/account changes happens during ordinary toolkit setup. They need an explicit setup scope and platform-specific validation. Selecting a Doppler project/config restricts the secrets requested by that command; it is not an OS access boundary, and the child must still be trusted.

## Scanning is evidence, not certification

The built-in skill scan is a small set of heuristic checks. SkillSpector and AgentShield are optional external scanners with their own coverage and configuration. A finding may be benign; no findings may still miss dangerous behavior. Read executable helpers as well as the skill instructions, keep revisions pinned, inspect dependencies and record unresolved findings. Do not activate an entire framework merely because one skill passed a scan.

Prompt injection remains relevant: retrieved pages, repository instructions, memory and worker results may contain malicious instructions. Keep them separate from governing instructions and permission decisions. Tool restrictions and controlled application of changes provide enforcement that prompt wording alone cannot.

## What proves a hook is working

Record these separately:

1. **Configured:** the intended host configuration registers the event and points to an existing hook implementation.
2. **Invoked:** a harmless test records that the actual host emitted that event to that implementation.
3. **Enforced:** a synthetic disallowed action is blocked before its effect; an allowed action still works.
4. **Failure handling:** missing executables, timeouts, malformed input and hook errors produce the documented outcome. A hook that fails open is useful advice, not a fail-closed barrier.

Developer-machine hooks do not travel with this download. Claude configuration does not establish equivalent Codex protection, and a registration or trust hash does not establish invocation. The release's [validation record](VALIDATION.md) must distinguish offline tests, configured integrations and actual host observations. Report absent evidence as unverified.
