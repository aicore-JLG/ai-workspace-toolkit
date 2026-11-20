---
name: doppler
description: Run a trusted project command with selected Doppler secrets, without storing values in the workspace.
---

# doppler

Read docs/DOPPLER.md. Require explicit project/config and variable names. Preview first; use --run within existing authority. Login is interactive recipient setup. Never fetch/print values or export .env files. The wrapper discards child stdout/stderr and retains a hashed receipt; it does not isolate inherited environment or prevent child-created files/network logs.
