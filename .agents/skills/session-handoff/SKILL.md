---
name: session-handoff
description: Save a concise handoff when the user asks to wrap up work or preserve progress for the next session.
---

# Save a handoff

Use the current task's workspace or project root. If it is unclear, ask which one; do not search unrelated folders to infer it.

For a project using the local lifecycle, first run tools/session.py --root PROJECT resume, then checkpoint/finish with the returned revision. Use --verified only with current passing checks covering all declared inputs. Preserve blockers when handing off incomplete work. See docs/SESSION-CORE.md. The operational handoff lives in .workspace/session/current.json; keep SESSION-STATE.md consistent as a short human summary. Recalled memory stays in its own store.

1. Read that scope's current `SESSION-STATE.md` and relevant task instructions. Use the work observed in this session; do not invent missing history.
2. Check for changes made by another session before writing. Preserve both sets of open work; ask when they conflict.
3. Write the current objective, decisions, relevant file paths, next action, blockers, and actual verification results. State explicitly what was not checked or released.
4. Keep private details within their authorised project. Root state should hold only non-sensitive workspace coordination. Never include credentials.
5. Prefer the bundled `tools/workspace.py` state-hash and compact commands from the known kit root. Read the state, obtain its hash, write a truthful summary in the same authorised project, preview compaction, then use `--write` when saving is authorised. Carry every unresolved decision and blocker. If the state changed, read it again; do not force the old summary. If tools are unavailable, preserve the complete old state in a uniquely named local history file before replacing it and disclose the manual check's limits.
6. Reopen the saved state and verify it reflects the work and points to existing files. Report where it was saved and the next action.

This workflow saves local notes only. It does not authorise publishing, sending messages, spending, deleting files or changing settings. If local file tools are unavailable, return a proposed handoff for the user to save and say it was not written.
