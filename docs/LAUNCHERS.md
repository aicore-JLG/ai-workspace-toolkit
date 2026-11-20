# Task launchers and project overview

The launcher prepares a task packet for your own AI tool. It selects the right role prompts, reads the selected project's current context, and separates the maker brief from a fresh review brief. It does not call Claude, start agents, install suggested tools or connect accounts.

All commands below run from the extracted kit root. Use `python3` instead of `python` if that is how Python is installed on your computer.

## See current work

```text
python -B tools/workspace.py overview
python -B tools/workspace.py overview --scope Apps/my-project
```

The overview reads each discovered project's current `PROJECT.md` location and `SESSION-STATE.md` notes. It reports the next action, blockers and recorded verification notes without maintaining a second status table. Missing state stays marked missing. This is a view of local handoffs, not a live check of services or proof that a task passed.

The root overview skips client pools, templates and examples. Select a specific authorised client project or example explicitly when you need it. Local status notes may be private.

## Choose a department

```text
python -B tools/launch.py --list
```

The presets in [routing.json](../routing.json) cover engineering, web design, funnels, copy, email, research and debugging. Each selects a planner, maker and reviewer. The role files are original task instructions included in the kit. They are not installed agent services.

Tool suggestions are recommendations to consider for the task, not evidence that a tool is installed or required. The launcher never executes them.

## Prepare the task

You can try a read-only preview immediately with the included synthetic example:

```text
python -B tools/launch.py --department engineering --project examples/welcome-project --task "Prepare the next local change and explain how to verify it."
```

First create and personalise a project using the quick-start instructions. Then preview a task packet:

```text
python -B tools/launch.py --department engineering --project Apps/my-project --task "Build the first local example and check the agreed acceptance criteria."
```

For a longer brief, save a Markdown file inside that project and use a path relative to the project:

```text
python -B tools/launch.py --department web-design --project Websites/my-site --brief brief.md
```

Preview returns JSON containing `maker_packet`, `review_packet`, `packet`, selected role paths, context and read-only helper commands. The helper commands assume the kit root is your current directory. Nothing is executed for you.

To save it, choose a new filename relative to the selected project:

```text
python -B tools/launch.py --department engineering --project Apps/my-project --task "Build the first local example." --output task-packets/first-pass.md --write
```

The file is created inside that project. Existing files are never overwritten. Paths outside the selected project and unsafe links are refused. Saved packets contain your task and project context; treat them as private working material.

## Use the two briefs

1. Open the selected project in your AI tool and paste the maker section. Supply the remaining files it needs for the task.
2. When the artifact is ready, open a fresh review session or use an explicitly separate reviewer if your AI tool supports one. Give it the review section, original requirements, acceptance checks and final artifact. Keep the maker's reasoning and preferred verdict out of that review.
3. Bring concrete findings back to the maker. Recheck affected work after repairs. Record actual results in the project state.

The launcher does not enforce independent review. A packet is not evidence that an agent ran, a check passed or work was released.

Role and workflow references are relative to the extracted kit root. If your AI starts inside the selected project, provide the relevant workflow file from the kit explicitly; do not ask it to search neighbouring projects. For example, a web-design task can use the kit's `workflows/design-a-website.md`. Supply only the selected workflow, not the whole library. The helper commands printed in the packet also run from the kit root.

## Keep context focused

```text
python -B tools/workspace.py context --scope Apps/my-project --max-chars 12000
```

Context includes only the selected scope's entry instructions, rules, brief, current state and map when present. Duplicate instruction files are omitted. Files are included whole; if the budget is too small, `over_budget` and `omitted` identify what must be read separately. Do not proceed without reading required omitted instructions. Other projects are not imported into the packet.

The context budget applies to project-context text, not the complete task packet; role instructions and your task add further text. Change a preset only after reading the relevant role files. The route configuration accepts role paths and short tool names, never executable commands.
