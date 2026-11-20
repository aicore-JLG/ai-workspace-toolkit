# AI Workspace Toolkit

A working home for building with AI: organise projects, keep useful memory, coordinate specialists, check their work, clean up deliberately and leave a reliable handoff for the next session.

Version 0.5.0 candidate r7. Portable files for your own AI tool. Python 3.11+ runs the offline utilities; optional integrations and subscription workers have their own runtimes and accounts.

The [foundation](docs/FOUNDATION.md) now provides scoped persistent memory, restartable sessions, stale-check rejection, bounded integration execution, reviewed skill activation and read-only maintenance diagnosis. Skills guide the AI through these tools. Optional services extend them; no global hooks or accounts are installed.

The expanded kit includes 16 integration routes for skill management, improvement, memory, security, research, cleanup and Doppler. Selected upstream skill sources are bundled with licences and hashes. See the [folder tour](docs/FOLDER-TOUR.md), [integration directory](integrations/README.md) and [setup commands](docs/INTEGRATIONS.md).

## What you need

- An AI tool that can open a local folder and read/write files. Claude Code and Codex entry instructions are included; other hosts can follow the files manually. A chat without local file access cannot operate these tools for you.
- Python 3.11 or newer for the local utilities. Check with `python --version`; use `python3` if that is your system's command. The core uses Python's standard library: no `pip install` or Node installation is required for it.
- Your own AI account if you use an AI host. The Python core itself needs no account, API key, external memory service or subscription-worker calls.

Development checks were observed on Windows with Python 3.13.7. Other platforms are not yet verified. Missing optional tools do not stop the offline core.

## Installation

1. Extract the complete ZIP into a **new folder**. Keep both hidden skill directories: `.claude` and `.agents`. On Windows, choose a short location such as `C:\AI-Workspace`; deeply nested paths can exceed runtime file-path limits.
2. Open that exact folder in your AI tool. Do not merge the starter into existing work or install every integration at once.
3. Open [SETUP-PROMPT.md](SETUP-PROMPT.md), copy the text under **Prompt to paste**, and send it to your AI. Answer its three questions about your work, preferred areas and first project.
4. The setup prompt checks the folder, preserves copies of changed starter files and creates your selected project. It does not install software, sign into accounts, import existing work or start background agents.
5. After setup, follow the separate [worked example](docs/WALKTHROUGH.md). Run a real check, see stale evidence rejected, and save a recoverable handoff. The deliberately broken orchestration example is a later optional exercise, not a setup failure.

To inspect the untouched kit yourself, open a terminal in its folder and run:

```text
python -B tools/preflight.py
python -B tools/workspace.py doctor
python -B tools/integrations.py verify
```

Preflight reports available executables; doctor checks the workspace; verify checks the bundled upstream files. These commands do not install anything, connect an account or make model calls. Run them as your own checks outside the setup prompt's restricted personalisation step. If Python is unavailable, you can still read and personalise the templates manually; the executable utilities will not run.

If your AI has no local file access, use the templates manually. Python is optional for reading the kit and required for its utilities. Your AI tool needs its own installation/account.

## Features and their actual limits

**Built-in tool** means executable behavior when invoked. **Workflow** means instructions the AI must follow. **Optional** means additional setup is needed. A skill file is not a background service, and these protections do not automatically wrap every action in your AI host.

| Area | What the workspace provides | Type and limit |
|---|---|---|
| Hallucination reduction | Evidence/provenance guidance, explicit unknowns, fixed checks and fresh review | Workflow plus tools. Reduces unsupported claims; cannot guarantee factual accuracy or automatically fact-check every answer. |
| Client/project separation | Selected project packets, permitted paths, separate memory and handoffs; rejection of traversal and linked/protected paths on supported routes | Built-in tools. Helps prevent accidental mixing; not an OS sandbox or a wall around unrestricted host tools/accounts. |
| Hooks and lifecycle checks | Validation before worker dispatch, response checks, review/check gates before applying changes | Built into the orchestrator. No global Claude/Codex startup, stop or pre-tool hooks are installed. |
| Model choice per task | Explicit provider, model and reasoning effort for each worker and reviewer; unsupported choices refused | Built-in orchestrator. You/the coordinating agent choose supported settings; no automatic optimal-model selector. |
| Parallel specialists | Bounded independent jobs, dependency ordering, separate file ownership and focused packets | Built-in orchestrator. Optional CLI/account setup; workers propose files and have no project tools of their own. |
| Independent review | Fresh reviewer sees requirements, candidate and check evidence; verdict bound to that artifact | Enforced inside orchestration. Ordinary non-orchestrated work uses a review workflow that the host must invoke. Review can still miss defects. |
| Verification | Current checks tied to declared files, configuration and tool hashes | Built-in. Stale, missing, failed or incomplete checks cannot establish verified completion; quality depends on the checks declared. |
| Safe application | Stage proposals, preserve originals, reject conflicting edits and apply only reviewed bytes | Built-in orchestrator. Does not protect edits made outside that route. |
| Persistent memory | Project-local facts, provenance, proposals, explicit confirmation, recall, conflict resolution and forgetting | Built-in, offline. Not a change to the LLM's weights or global memory; automatic episode capture is optional. |
| Optional Learn mode | Explains actual code, decisions and checks; adjusts depth and offers guided design practice | Included skill/workflow, activated by the user. Pause/off anytime; no automatic startup, separate teaching model or additional approval ritual. |
| Focused context | Project maps, bounded context packets, relevant rules and selected memory recall | Built-in plus workflow. Omitted required instructions still need reading; nothing loads all clients by default. |
| Handoff and resume | Save objectives, decisions, blockers, files, checks and next action; resume in a fresh session | Built-in session tools plus skill. The AI must actually checkpoint; unwritten chat cannot be recovered. |
| Session close | Finish as verified only with current covering checks and no blockers; otherwise preserve an unfinished handoff | Built-in when invoked. Closing the app does not trigger an automatic save or hook. |
| State compaction | Shorten current summaries while retaining exact prior history and rejecting stale replacement | Built-in plus handoff workflow. Not automatic pruning of the model's context window. |
| Workspace cleanup | Read-only health diagnosis, instruction/skill maintenance and scoped cleanup planning | Built-in diagnosis plus workflows/optional tools. No silent deletion, scheduled sweeper or automatic skill rewrite. |
| Code cleanup | Review recent changes, simplify code and verify affected behavior | Workflow and optional code-simplifier/Desloppify. Not automatic approval of rewritten code. |
| Skill/pipeline improvement | Candidate copies, fixed baselines, holdouts, evaluation records, review and rollback before promotion | Built-in gates plus workflows/optional evaluators. No unreviewed self-modification or background learning. |
| Skill security | Heuristic scan, content-bound review before activation, preserved existing destinations and bundled-file hashes | Built-in; SkillSpector/AgentShield optional. Scans and hashes do not prove code is harmless. |
| Secrets and Doppler | Explicit project/config and secret-name selection for a child command; wrapper discards child output | Optional account/CLI. Injected secrets remain accessible to that child; not credential isolation. Never paste secrets into chat. |
| Permission and injection handling | Ownership/authority rules; external pages, memory and outputs treated as untrusted reference material | Workflow plus selected tool restrictions. No universal prompt-injection immunity. |
| Failures and interruptions | Time/output limits, cancellation handling, durable job state, bounded attempts and retained locks when cleanup is uncertain | Built-in supported runners. Not guaranteed recovery from every forced kill or detached process. |
| Concurrent work | Revision checks, source fingerprints and cooperative leases | Built-in. Protects cooperating writers, not malicious processes with the same OS permissions. |
| Usage tracking | Attempts, elapsed time, available token counters, requested versus observed model/effort | Built-in orchestration. Unknown values stay unknown; tokens are not exact subscription-credit charges or a spending cap. |
| Research and discovery | Source-handling workflow, public GitHub Agent Search helper and optional Agent Reach | Search requires explicit execution and own prerequisites/access; results are not endorsements or auto-installed skills. |
| Specialist workflows | Planning, building, debugging, research, review, web/design, funnels, copy and email; brand/source workbooks | Included instructions/templates. No connected accounts, autonomous employees or automatic external sending. |
| Browser and visual QA | Browser-review workflow and synthetic Playwright example | Optional browser/runtime setup. A checklist alone is not an observed browser test. |
| Portable export | Explicit package allowlist and integrity checks; private runtime records excluded from the shipped ZIP | Built-in packaging route. Manually zipping a populated workspace bypasses that protection. |

For implementation detail see [foundation](docs/FOUNDATION.md), [security boundaries](docs/SECURITY-BOUNDARIES.md) and [capability map](docs/CAPABILITIES.md).

## The 15 included skills

The same core workflows are supplied in `.agents/skills/` for Codex and `.claude/skills/` for Claude. Read only the skill needed for the task. These instructions guide the host; they do not install the optional services named below.

| Skill | Why it is included |
|---|---|
| `project-start` | Create a scoped project with its own rules, context and state. |
| `memory-manager` | Propose, confirm, recall and maintain project-specific facts with sources. |
| `session-handoff` | Preserve decisions, verification status, blockers and the next action. |
| `verify-work` | Require current evidence before calling work complete. |
| `learn-mode` | Explain actual work at the user's chosen depth when explicitly activated. |
| `workspace-doctor` | Diagnose missing references, oversized context and structural issues. |
| `workspace-maintenance` | Inspect health and plan deliberate, scoped maintenance. |
| `workspace-code-cleanup` | Simplify code while preserving behavior and verifying changes. |
| `skill-improvement` | Compare candidate skills against fixed cases and holdouts before promotion. |
| `workspace-security` | Review sources, permissions and findings before activating skills. |
| `agent-search` | Find public GitHub candidates for investigation without auto-installing them. |
| `research-brief` | Produce sourced findings with clear uncertainty. |
| `browser-review` | Guide real browser checks against meaningful acceptance criteria. |
| `integration-manager` | Inspect, set up and activate selected integrations with review gates. |
| `doppler` | Guide explicit, scoped secret injection when the user configures Doppler. |

Core memory, handoff and Learn mode work without a third-party memory plugin. The [16 integration routes](integrations/README.md) are optional extensions, not 16 more services running in the background. Learn mode is an original included workflow inspired by VibeWise; the VibeWise plugin is not installed.

## Turn on Learn mode

Say **“Turn on Learn mode for this project.”** The AI will explain useful concepts and meaningful changes as it works, using your actual project. No extra plugin or account is required; normal AI-host usage still applies.

- **“Explain it like I'm new to this”** — use simpler explanations.
- **“Go deeper”** or **“Guide me through the design”** — explore the design and trade-offs together.
- **“Just implement this step”** — skip teaching pauses for that step.
- **“Pause Learn mode”** or **“Turn off Learn mode”** — return to ordinary work.
- **“Save what I learned”** — save a concise project-local recap when file access is available.
- **“Resume Learn mode for this project”** — explicitly resume in a later conversation.

The mode starts off and stays specific to the selected project. It does not stop already authorised routine work to ask repeated permission. Learning notes, when saved, live in that project's `.workspace/learning/notes.md`; they do not replace confirmed memory or the task handoff. A new conversation starts in Build mode until you activate Learn mode again. Hosts must load and follow the skill or entry instructions; this is not an automatic hook. See [Learn mode](workflows/learn-mode.md).

## Everyday use

Open one project and use plain requests such as:

- **Start/resume:** “Read this project's instructions and saved state, recall relevant confirmed memory, and continue the next step.”
- **Build:** “Implement this change, run the relevant checks, then get a fresh review. Use parallel workers only for separable work and within my approved account usage.”
- **Remember:** “Propose this decision for this project's memory, with its source. Ask me to confirm it before storing it as a fact.”
- **Clean up:** “Inspect this project's health and propose cleanup. Preserve existing work and verify any authorised changes.”
- **Close:** “Save a handoff with decisions, files changed, checks, blockers and next action. Finish the session truthfully; only mark it verified if current checks cover the work.”

Check that the AI actually used the tools and saved the result. “I will remember” is not evidence of a saved memory or handoff. See [session commands](docs/SESSION-CORE.md) and [memory commands](docs/MEMORY-CORE.md).

## Where to start for each job

| You want to... | Start here |
|---|---|
| Stop repeating project context | [Project template](templates/project/PROJECT.md), instructions and current state |
| Read only relevant information | Scoped context and map [commands](docs/COMMANDS.md) |
| Choose a specialist | [Agent directory](docs/AGENTS.md), [routing](routing.json) and [launch packets](docs/LAUNCHERS.md) |
| Coordinate subscription workers | [Staged build and fresh review](workflows/coordinated-build.md), with explicit model/effort choices |
| Build and review separately | [Build and review](workflows/build-and-review.md) |
| Know whether a check still counts | File-bound [verification](docs/COMMANDS.md) |
| Keep failures visible | [Local runner](docs/RUNNER.md), bounded logs and cooperative resource lease |
| Save the next session's starting point | [Handoff skill](.claude/skills/session-handoff/SKILL.md) and hash-checked compaction |
| Research tools and opportunities | [Research guide](docs/RESEARCH.md), Agent Search and optional Agent Reach |
| Ground writing in your real material | [Brand, voice and story workbook](Brand/README.md) |
| Design and assess a website | [Design workflow](workflows/design-a-website.md) and [browser review](workflows/browser-review.md) |

See the [core capability map](docs/CAPABILITIES.md) and [integration directory](integrations/README.md) for implementations, benefits and limits.

## Inside the folder

`Apps/`, `Websites/`, `Ventures/`, `Clients/` and `Systems/` organise work.
`roles/` supplies specialist briefs; `workflows/` explains how to work.
`Knowledge/` records reusable sources and permissions. `Brand/` starts empty for your own material.
`tools/` holds runnable Python utilities; `tests/` checks them.
`examples/` contains synthetic projects and an optional browser test.

`Memory/` holds approved reusable notes; project-specific memory stays in the project.
`evaluations/` organises skill tests; `Security/` explains the scan and permissions workflow.
`integrations/` holds pinned definitions, selected source bundles and setup guides.
`config/foundation.json` supplies active local limits; other configuration examples remain inert. `.workspace/` is ignored local runtime storage.

Use [the map](WHERE-THINGS-LIVE.md). Do not load every file into every conversation: select one project, relevant roles and the workflow you need.

## First commands

From the extracted folder:

```text
python -B tools/preflight.py
python -B tools/workspace.py doctor
python -B tools/workspace.py context --scope examples/welcome-project
python -B tools/verify.py --root examples/welcome-project --run
python -B tools/workspace.py new-project Ventures/my-first-project
python -B tools/integrations.py doctor
python -B tools/integrations.py verify
```

Use `python3` if that is your system's command. Creation/compaction preview first; `--write` applies them. Check execution and public search require `--run`. Read commands/configurations before executing trusted code.

## Bring your own tools

[TOOLS.md](docs/TOOLS.md) covers core prerequisites. The [integration directory](integrations/README.md) adds ECC, Vercel Skills, Anthropic skill-creator, SkillSpector, Basic Memory, Claude.md Management, skilled, Agent Reach, AgentShield, agent-cleanup, Claude-Mem, Desloppify, Skill Eval Harness, code-simplifier, Superpowers and Doppler. Optional executable dependencies are not included in the ZIP; selected skill source is. Core examples work offline; online research sends queries to configured services.

Start with the core. When a particular task needs an integration:

1. Run `python -B tools/integrations.py list` and read only that integration's guide.
2. Use `python -B tools/integrations.py doctor` to inspect its local setup state. A detected executable does not prove login or working account access.
3. Follow [integration setup](docs/INTEGRATIONS.md). For supported installer routes, `install NAME` previews; adding `--run` downloads and executes the installer. Some tools require separate external setup. Review the source and permissions first.
4. Follow the required scan/review/activation steps for selected skills. Existing destinations are not overwritten. Configure only your own accounts, with credentials outside the workspace.

The 16 routes cover: **improvement/evaluation** (ECC, skill-creator, skilled, Skill Eval Harness, Superpowers, Claude.md Management); **discovery** (Vercel Skills, Agent Reach, plus the built-in Agent Search helper); **security** (SkillSpector, AgentShield); **memory** (Basic Memory, Claude-Mem); **cleanup** (agent-cleanup, code-simplifier, Desloppify); and **secrets** (Doppler). They are choices, not a requirement to run everything. Built-in memory is enough to start.

## Optional subscription agents

Use your own supported Claude Code or Codex CLI installation and login. Choose the provider-specific example manifest, inspect its tasks and model/effort settings, and check your available allowance or explicitly authorised credits. Account authentication alone does not prove affordable/available usage.

For Codex, these commands inspect the plan and then check CLI/authentication support without generating a model response:

```text
python -B tools/orchestrate.py --manifest config/orchestration.codex.example.json
python -B tools/orchestrate.py --manifest config/orchestration.codex.example.json --preflight
```

Use `config/orchestration.example.json` for the Claude example. Follow [coordinated build](workflows/coordinated-build.md) for the explicit run, review, application and final verification steps. Adding `--run` to orchestration consumes provider usage; it is not part of installation. No API-key fallback, credit purchase or automatic account switch is supplied. Use a fresh copy for the deliberately broken exercise.

Roles and skills are instructions, not connected employees. Launch packets prepare tasks; they do not start background agents. Runner guards and folder boundaries are not a sandbox. No global settings, accounts, browser profiles or provider hooks are installed by the kit. Upstream onboarding can change these and is a separate, explicit setup step. Automatic learning and competing memory capture are off until deliberately configured.

The [orchestrator](docs/ORCHESTRATION.md) executes bounded parallel subscription workers with explicit model/effort settings, scoped packets, staged proposals, fixed checks, fresh review and separate guarded application. Preview is the default; `--run` consumes included allowance or account credits under the provider's billing settings. Real Codex runs on Windows passed a small single-versus-parallel comparison with hidden checks; a fresh reviewer also caught a planted defect and blocked application. These are specific observations, not universal reliability or speed guarantees. Claude execution and other platforms remain unverified. See [actual security boundaries](docs/SECURITY-BOUNDARIES.md): no OS-level client isolation or global hooks are installed.

## Make it yours

You may use and adapt the original parts of this kit for personal or commercial projects. Third-party source retains its own terms; read [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). Desloppify is an external integration only. No particular performance or outcome is promised.

Run `python -B -m unittest discover -s tests`. See [VALIDATION.md](docs/VALIDATION.md) for release evidence and limits, and [GITHUB.md](docs/GITHUB.md) for publication preparation.

This is a reusable workspace to adapt; see validation for precisely what was tested. The [optional setup checklist](docs/RECIPIENT-PILOT.md) helps check onboarding and recovery on your own platform. There is no account inside the kit. After personalisation, files and local logs may be private. Redistribute the untouched release, not your populated working folder.
