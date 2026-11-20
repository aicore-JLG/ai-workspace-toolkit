---
name: workspace-doctor
description: Inspect a selected project's navigation, instruction references and context size when the user asks about workspace health or confusing context.
---

# Inspect workspace health

Choose the smallest authorised scope. From the known kit root run `python -B tools/workspace.py doctor --scope PROJECT` and, if helpful, its map/context commands. Do not broaden into client or personal folders to find more issues.

Explain each finding and its practical effect. The doctor checks explicit references and context size; it does not certify privacy, code correctness, remote services or hidden skill content.

Prepare narrowly scoped fixes, read files before editing and preserve current work. Follow existing authority for writes. Run the affected check after a change and report exclusions and remaining warnings.
