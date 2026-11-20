# Where things live

Update this map when you add an area or reusable reference. Keep confidential project and client details in their own area, not in this shared map.

| Location | Purpose |
|---|---|
| `Apps/` | Application projects, one folder per project |
| `Websites/` | Website projects, one folder per site |
| `Ventures/` | Your own businesses and products, one folder per venture |
| `Clients/` | Client work, with separate instructions, state and access scope |
| `Systems/` | Reusable workflows without private business data |
| `templates/project/` | Copyable project starter; not a live project |
| `docs/reference/` | Generic workspace guidance |
| `docs/session-history/` | Old workspace-level handoffs; not current instructions |
| `.claude/skills/session-handoff/` | Reusable handoff workflow |
| `.claude/skills/` | Original workflow instructions; automatic loading depends on your AI tool |
| `tools/` | Local Python utilities; run with `--help` for their interface |
| `roles/` | Provider-neutral role prompts; no autonomous employees are installed |
| `workflows/` | Task sequences for building/reviewing, research, debugging and browser QA |
| `Brand/` | Empty brand, voice and story workbooks |
| `routing.json` | Seven department presets for task packets |
| `Knowledge/` | Generic source records and permission/provenance tracking |
| `examples/` | Synthetic runnable local project and optional browser test |
| `Memory/` | Approved reusable lessons; project/client notes stay in the owning project |
| `evaluations/` | Skill test cases, baseline and improvement methodology |
| `Security/` | Skill/config scanning workflow and actual enforcement limits |
| `integrations/catalog.json` | Sixteen integrations with source revisions and setup routes |
| `integrations/vendor/` | Selected upstream skill source and licences; read only what a task needs |
| `integrations/guides/` | Per-tool setup, platform requirements and account boundaries |
| `config/` | Active foundation limits plus inert MCP/memory/Doppler examples; no secret values |
| `.agents/skills/` | Codex-facing core skills and integration workflows |
| `.workspace/` | Ignored local runtimes, evaluation reports and staging; excluded from exports |
| `docs/FOLDER-TOUR.md` | Walkthrough of the full folder structure |
| `docs/FOUNDATION.md` | Daily lifecycle, scoped memory, execution and verification architecture |
| `tools/orchestrate.py` | Preview/run bounded subscription jobs; fresh review and explicit apply |
| `tools/client_scope.py` | Exact project packets and protected output paths |
| `tools/worker_provider.py` | Claude/Codex subscription preflight and isolated structured workers |
| `docs/SECURITY-BOUNDARIES.md` | Actual tool gates, hooks and limits of client isolation |
| `docs/RECIPIENT-PILOT.md` | Untouched-download trial, comparison metrics and recipient feedback |
| `docs/ISOLATION-PILOT.md` | Opt-in synthetic client-boundary test and required runtime |
| `workflows/coordinated-build.md` | Synthetic parallel build, checks, fresh review, resume and apply |
| `workflows/learn-mode.md` | User-activated teaching, pause/resume and project-local learning notes |
| `docs/DOPPLER.md` | Explicit project/config and secret-name runtime injection |
| `tests/` | Toolkit regression tests |
| `docs/TOOLS.md` | Tool selection and optional installation guidance |
| `docs/WALKTHROUGH.md` | End-to-end local example |

There are no real active projects yet. The bundled examples are synthetic. Use `templates/project/` or the new-project tool to start your own.
