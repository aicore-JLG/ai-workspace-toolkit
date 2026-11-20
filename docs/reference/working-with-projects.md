# Working with projects

## Start small

Use one area and one project first. Copy the entire `templates/project/` folder to a new folder in the appropriate area. Set the outcome and definition of done in `PROJECT.md`; keep the next step in that project's `SESSION-STATE.md`.

Each project contains its own entry files and working rules. This keeps the instructions available when the project is opened separately. If your AI does not load them automatically, explicitly ask it to read them before work.

## Keep context useful

Keep instructions short, state current, and longer explanations in references. A written handoff helps the next session only if the AI reads it. It is not a guarantee of memory or accuracy.

Project history belongs in that project's own `docs/session-history/`. Root history is for workspace-level changes. Copy old state to a new, uniquely named history file before shortening it, and keep all open decisions and blockers in the current summary.

## Reuse a workflow

The included handoff skill is a small example of a reusable recipe. Read `.claude/skills/session-handoff/SKILL.md` from the workspace root when needed. For another repeated job, write a short workflow describing its inputs, output, checks and approval boundaries. Do not copy sensitive examples or private tooling into it.

## Share a clean copy

Once you personalise this starter it may contain private information, including in histories and backups. To share the original kit, use the untouched download. To share a changed version, make a separate copy and review every file, including hidden files and archives. Git ignore rules are not a privacy review.

Tool installations, account connections, enforced permission controls, automatic backups, hosted services and employee orchestration are separate setup work. This starter does not provide them.
