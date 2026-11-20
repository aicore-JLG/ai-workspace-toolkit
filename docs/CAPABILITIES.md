# Core capabilities and v0.5.0 orchestration

The table below describes the inherited offline core. Version 0.4 adds [16 integrations](../integrations/README.md), selected upstream skill bundles, integrity checks, runtime installation and explicit Doppler injection. Version 0.4.1 adds [the operational foundation](FOUNDATION.md): scoped curated memory, restartable sessions, content-bound completion, reviewed activation, bounded integration execution, read-only health diagnosis and an executable offline acceptance suite. Automatic episode capture, model evaluations and upstream account setup require separate configuration. See [folder tour](FOLDER-TOUR.md).

Executable tools, AI instructions and optional third-party installations are different. This map tells you exactly what each capability provides.

Version 0.5 adds executable [subscription orchestration](ORCHESTRATION.md): bounded parallel Claude/Codex CLI workers, explicit models/effort, protected project packets, staged proposals, trusted checks, fresh artifact-bound review and explicit guarded application. Small live Windows Codex builds and a seeded-defect review passed; broad model quality, Claude generation and other recipient environments remain unverified. It does not install global hooks, automatically tune models or create an OS client sandbox. The table below describes the inherited offline core and packet-only launcher separately; the [README feature list](../README.md) includes the later memory, session, maintenance, security and execution foundations with their limits.

| # | Feature | Benefit | Implementation and boundary |
|---|---|---|---|
| 1 | Organised project areas | Find work without mixing projects | Five areas and project template; not access isolation |
| 2 | Project-specific rules | Keep decisions close to the work | AGENTS, CLAUDE, project rules, brief and state |
| 3 | Scoped skills and context | Reduce irrelevant reading | Context selector with deduplication/budget and focused skills; read omitted required files separately |
| 4 | Generated maps | Inspect current structure | Local map command with safe default exclusions |
| 5 | Live work summaries | See current decisions and next steps | Selected project overview; no background monitor |
| 6 | Session handoffs | Continue without retelling everything | Handoff skill, state template and example |
| 7 | Safe compaction | Shorten current state while retaining history | Exact original archive, expected hash and deliberate replacement |
| 8 | Concurrent-work protection | Refuse stale replacements | Hash checks and cooperative locks; not hostile-process protection |
| 9 | Task-specific launchers | Start with a prepared brief | Local task-packet preview and explicit write; no provider calls |
| 10 | Agent routing and departments | Select relevant roles consistently | Editable route registry with maker/reviewer choices |
| 11 | Specialist teams | Apply task-specific standards | Nine role briefs: planning, building, review, research, debugging, web, funnels, copy and email |
| 12 | Independent reviewers | Catch mistakes the maker misses | Separate reviewer protocol; recipient starts a fresh reviewer context |
| 13 | Debugging and regression workflows | Diagnose causes and preserve fixes | Evidence-first workflow, debugger role and regression examples |
| 14 | Current verification records | Stop stale checks counting | Declared-input/config/tool hashes and stale/failure rejection |
| 15 | Browser and visual QA | Check what visitors see and do | Checklist and synthetic Playwright Test example; separate install |
| 16 | Safety guards | Catch common risky command shapes | Runner shell/destructive-command/credential-path checks; partial, not provider hooks or sandbox |
| 17 | Permission and ownership rules | Keep authority and data boundaries clear | Short working rules and commission template |
| 18 | Command logging and failure detection | Keep useful failure evidence | Bounded local logs, common-secret redaction, exit/timeout records; inspect before sharing |
| 19 | Resource coordination | Avoid overlapping cooperating jobs | One local runner lease per selected root; not machine-wide scheduling |
| 20 | Shared knowledge and retrieval | Reuse permitted evidence | Source register, provenance and scoped retrieval workflow; no private database |
| 21 | Brand, voice and story libraries | Ground writing in real material | Empty workbooks and clearly fictional example |
| 22 | Agent Search | Assess public tools before adopting them | Original public GitHub discovery helper; own gh install and explicit network run |
| 23 | Agent Reach | Add public web/social research | Original guidance for separately installed upstream tool and recipient access |
| 24 | Social outlier research | Identify unusually strong results fairly | Median-baseline worksheet and synthetic CSV; no scraper/account data |
| 25 | Playwright | Check interactions and layout | Optional CLI guide and Test example; recipient installs browsers |
| 26 | Development tools | Make work inspectable and repeatable | Read-only executable preflight and tool guide; runtimes separate |
| 27 | Design workflows | Build coherent, accessible websites | Strategy, art direction, implementation and rendered review playbook |
| 28 | Optional Learn mode | Understand actual changes, design choices and checks while building | Explicit user activation, adjustable depth, pause/off and project-local notes; an instruction workflow, not automatic hooks or extra permissions |

Short entry files point to selected project knowledge. Explicit routes make the maker and reviewer visible. Compact state retains old context in history. Verification records identify the inputs actually checked. These mechanisms help reduce repeated explanation and expose mistakes; no speed or token-saving benchmark is promised.

The local Python workflow is self-contained. No author workspace, private services or accounts are required. Optional third-party tools need their own installation and may need network access.
