# Maintain and improve the workspace

Select one project and a bounded objective. Read its instructions/state and inspect the current baseline. Run workspace doctor and integration integrity checks first.
Run `python -B tools/health.py --root SELECTED_PROJECT` for a read-only maintenance diagnosis. Resume the project's operational session before repairs; checkpoint findings and run affected checks. The health command never deletes work or promotes skills.

- Instructions: claude-md-management; review corresponding AGENTS.md deliberately.
- Skill inventory: ECC skill-stocktake, scoped to the intended paths. Missing usage data is not proof of disuse.
- Skill changes: skill-creator plus skilled; retain baseline, independent cases and rollback.
- Code cleanup: code-simplifier for a bounded diff; optional external Desloppify for a separately licensed project-wide loop.
- Disk cleanup: agent-cleanup on supported platforms, preview and recheck active work before an authorised deletion.
- Memory: tools/memory.py proposals/confirmed records, plus optional separately scoped providers. No cross-client promotion.
- Security: SkillSpector/AgentShield and Doppler; scanners do not replace real host controls.

Save findings, failed checks and next actions in the project handoff. Routine reversible work within the user's scope can proceed. Broader capture, deletion, spending and external effects need authority covering those actions. Scheduling is a separate setup step; these workflows do not run themselves.
