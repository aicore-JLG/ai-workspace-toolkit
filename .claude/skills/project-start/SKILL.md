---
name: project-start
description: Create a new scoped project from this toolkit's templates when the user asks to start a project.
---

# Start a project

Read the workspace rules and ask for the outcome, audience and observable definition of done if they are missing. Use a neutral name for confidential work.

From the known kit root, preview `python -B tools/workspace.py new-project AREA/PROJECT`. Confirm the destination is new and within the authorised workspace. If creation is authorised, repeat with `--write`.

Personalise the new PROJECT.md and SESSION-STATE.md. Do not overwrite an existing project, import unrelated records or change accounts/settings. Preserve template files.

Read back the new files and show the next action. If Python or file access is unavailable, provide manual instructions and do not claim the files were created.
