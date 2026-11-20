# Your workspace, folder by folder

```text
AI-Workspace/
  AGENTS.md / CLAUDE.md       entry points for the AI
  WORKSPACE-RULES.md          short shared working rules
  WHERE-THINGS-LIVE.md        navigation map
  SESSION-STATE.md            current workspace handoff
  Apps/                      application projects
  Websites/                  website projects
  Ventures/                  business/product projects
  Clients/                   separate client projects
  Brand/                     your brand and voice references
  Knowledge/                 research and source records
  Memory/                    approved reusable lessons/preferences
  Systems/                   reusable workflows and systems
  Security/                  security workflow and boundaries
  evaluations/               skill test cases and evaluation plans
  integrations/
    catalog.json             16 integrations, revisions and setup routes
    bundles.lock.json        hashes of supplied upstream files
    guides/                  one setup guide per integration
    vendor/                  original selected skills, scripts and licences
  config/foundation.json     active integration limits and health thresholds
  config/*example*           inert provider setup examples, no secret values
  .claude/skills/             task-facing Claude skills
  .agents/skills/             equivalent task-facing Codex skills
  roles/                     specialist briefs
  workflows/                 task sequences
  templates/                 new-project, memory and evaluation starters
  tools/                     runnable local workspace utilities
  tests/                     offline regression checks
  examples/                  synthetic demonstrations
  docs/                      walkthroughs and verification limits
    ORCHESTRATION.md          subscription execution and recipient validation limits
    SECURITY-BOUNDARIES.md    enforced checks, hook coverage and client isolation limits
    ISOLATION-PILOT.md        synthetic access-boundary test in a restricted runtime
    RECIPIENT-PILOT.md        fresh-download checks and measured worker comparison
  .workspace/                local installs, reports and staging; never shipped
```

## Where a real project goes

An application goes in `Apps/my-app/`. Its brief, rules, current state, code and `Memory/` stay together. Put a client project under its owning `Clients/` folder and select it explicitly. Root memory is only for approved reusable material.

Within each project, `Memory/curated.json` holds proposed/confirmed knowledge and `.workspace/session/current.json` holds the operational handoff. `.workspace/verification/` and `.workspace/runs/` hold private check/run evidence. These are separate from task skills. [The foundation guide](FOUNDATION.md) connects the layers.

## Where coordinated workers fit

The existing `roles/` and `workflows/` remain the specialist layer. `tools/launch.py` prepares role packets; it does not execute workers. The new `tools/orchestrate.py` coordinates workers, `tools/worker_provider.py` supplies isolated subscription CLI calls, and `tools/client_scope.py` selects bounded project packets. `config/orchestration.example.json` declares a synthetic two-worker task and reviewer with explicit models/effort. Private proposals, usage, evidence and backups stay in each project's `.workspace/orchestration/`. No second global memory tree is introduced. Follow [orchestration](ORCHESTRATION.md) and its recipient validation limits.

## Where skills live

The two hidden skill folders contain a small set of task-facing workflows. `integrations/vendor/` holds the upstream library without auto-loading it. Activate selected skills through the manager when needed. Existing skills are not overwritten. Do not keep a second full copy of every framework active in both hosts unnecessarily.

Both host skill folders include `learn-mode/`; its shared [workflow](../workflows/learn-mode.md) is loaded only when the user activates it. Optional learning notes stay inside the selected project's `.workspace/learning/notes.md`, separate from confirmed memory and the operational handoff. No second global memory service or startup hook is added.

## Where secrets live

Values live in the recipient's Doppler account. `config/` contains examples and variable names only. A command gets selected values at runtime. `.workspace/` is private runtime storage, not a secret vault or security boundary.

## A normal working session

1. Open the workspace and select/create one project.
2. Read that project's brief, resume/start its session and query relevant confirmed memory; load the relevant skill.
3. Build or research, then verify the result.
4. If a repeated failure appears, create an improvement candidate and evaluate it.
5. Checkpoint/finish the session with its current revision and actual verification status; propose source-backed lessons for deliberate confirmation.

Start with `python -B tools/integrations.py doctor`. Missing optional runtimes are setup work, not a broken offline core. Use `docs/INTEGRATIONS.md` for installation and `docs/DOPPLER.md` for secrets.
