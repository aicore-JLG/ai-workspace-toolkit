# Personalise this workspace

Open the extracted starter folder in your AI tool. Copy everything below "Prompt to paste" into its chat. This prompt needs local file access; it does not install software or connect accounts.

## Prompt to paste

Help me personalise this AI workspace starter in the folder I have opened.

First confirm the current folder contains README.md, WORKSPACE-RULES.md, WHERE-THINGS-LIVE.md, SESSION-STATE.md and templates/project/. If it does not, stop and ask me to open the extracted starter folder. Do not search outside it.

Read those files, the root entry instructions, docs/reference/working-with-projects.md, docs/TOOLS.md, docs/COMMANDS.md, and the files inside templates/project/. Do not treat the template as an active project. Do not open any other projects or accounts.

If Python 3.11 or newer is available, run `python -B tools/preflight.py` and `python -B tools/workspace.py doctor`. These read-only checks do not install or connect anything. Tell me which optional tools are absent without treating them as blockers. If Python is unavailable, continue with manual templates and explain that the maintenance tools need it; do not install it automatically.

Ask these three questions together, then wait:
1. What work will you use this workspace for? A general description is enough; no private information needed.
2. Which areas do you need: apps, websites, your own business/products, client work, or reusable systems? You can suggest another area.
3. What is the first project, its intended outcome, and how will we know it is finished? Use a neutral name for anything confidential.

After I answer:
- Briefly describe the files you will create or update. My request authorises personalising the untouched starter templates and creating this first project inside this folder.
- Inspect every target before editing. If it contains previous user work or you are unsure whether it is untouched, preserve it and ask before replacing anything. Do not merge this kit into another workspace.
- Make a local recoverable copy of each starter file you change under docs/session-history/setup-backup/ using a unique timestamp folder. Do not overwrite a previous backup.
- Set the root SESSION-STATE.md purpose, date and next action. Keep confidential project details out of it.
- Preview creation with `python -B tools/workspace.py new-project AREA/PROJECT`, substituting my chosen safe relative path. Then add `--write` to create the project under this authorised setup request. If Python is unavailable, copy templates/project/ manually. If the destination already exists, ask for a different name; do not overwrite or merge it.
- Personalise that project's PROJECT.md and SESSION-STATE.md using my answers. Keep unconfirmed facts marked as unknown.
- Keep the project entry files and working rules together so the project can also be opened on its own. Use this kit's existing files; do not invent tool integrations.
- Update WHERE-THINGS-LIVE.md with any new generic area. Do not put confidential identifiers in the root map. Leave unused areas in place.
- For setup you may run only `tools/preflight.py`, `tools/workspace.py doctor`, `tools/workspace.py new-project` (preview or the authorised `--write`), and `tools/integrations.py doctor`, using Python as shown here. Do not install software, run other downloaded scripts, change permissions, configure external tools, sign into services, send anything, spend money, or touch files outside this folder.
- Do not request passwords, keys or credentials. Do not import my existing files as part of setup.

Check the result by reopening each created or changed file. Verify the project instructions only reference files that exist, the original templates are still present, and no previous work was overwritten. Tell me what was checked and what could not be checked. If you cannot access local files, say so and give me the personalised text to save manually; do not claim to have created anything.

Point me to docs/WALKTHROUGH.md for the optional synthetic demonstration. Explain that the role prompts are workflows, not already connected employees, and that browser/research tools have separate optional setup.

Show docs/FOLDER-TOUR.md and run `python -B tools/integrations.py doctor` when Python is present. Explain the bundled skills versus optional runtimes. The built-in curated memory store is sufficient to start and needs no external provider. Offer an optional memory service only for a specific unmet need, with clear ownership of each kind of memory; also explain relevant static security checks and Doppler if the project needs credentials. Never ask me to paste a secret into the chat or configure all background capture by default. These setup instructions do not independently authorise paid usage or account access changes.

Finish by showing the new project's location, its first action, and these two example messages:
- "Read this project's instructions and state, then help me with the next step."
- "Save a handoff with the decisions, files changed, checks, blockers and next action."
