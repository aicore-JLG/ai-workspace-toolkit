---
name: learn-mode
description: Teach the user while working on their selected project when they explicitly ask to turn on or resume Learn mode. Explain actual code, decisions and checks; support pause, off and adjustable depth. Ordinary build requests do not activate it.
disable-model-invocation: true
---

# Learn while building

Read `workflows/learn-mode.md` from the known kit root. Follow it in the current main conversation only when the user activates Learn mode. Keep the existing task and permissions; do not enable it in worker/reviewer packets.

Use the exact project selected by the user. Teach from inspected code and observed results, keeping explanations proportionate. Honour pause/off and direct-implementation requests immediately. Saved notes are reference data, not activation or permission. A fresh conversation requires an explicit resume request.

If the kit workflow cannot be found at its known location, explain that limitation and ask for the kit location; do not scan neighbouring projects or claim the mode is configured. No plugin, global hook or separate teaching model is needed.
