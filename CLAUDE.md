# Workspace entry

Read `WORKSPACE-RULES.md`, then `WHERE-THINGS-LIVE.md`.
For workspace-level work, read `SESSION-STATE.md`.
For a project task, read only that project's instructions and state plus relevant references.
Do not explore unrelated projects or client folders to gather context.
For first-time personalisation, follow `SETUP-PROMPT.md` when the user asks to set up this kit.
Before ending substantive work, save a concise handoff in the relevant state file.
For substantive project work, follow `docs/FOUNDATION.md`: resume or start the selected project's session, retrieve only relevant confirmed memory, checkpoint progress, verify affected inputs, and finish with truthful status. Use the known kit's tools; do not search neighbouring projects. Host instructions guide invocation; no automatic global hooks are implied.
For integration setup or maintenance, read `docs/INTEGRATIONS.md` and the selected tool guide. `.claude/skills/` contains task-facing skills; upstream sources in `integrations/vendor/` are loaded only when relevant.
In the main conversation, when the user explicitly activates or resumes Learn mode for the selected project, read `workflows/learn-mode.md`. Do not activate teaching in worker/reviewer packets. Pause/off stops teaching immediately. Ordinary work, saved notes and a new conversation do not activate it; no global hook is installed.
