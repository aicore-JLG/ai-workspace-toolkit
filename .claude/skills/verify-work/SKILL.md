---
name: verify-work
description: Check a completed change against declared acceptance criteria and report current verification evidence.
---

# Verify the work

Read the project's acceptance criteria. Choose checks that demonstrate the requested behaviour, not tests that simply restate the implementation.

Inspect checks.json before running it. Ensure its input list covers the relevant dependencies and the argv is trusted and authorised. Preview the bundled verifier, then use --run only within the task's execution scope. This executes code with normal user permissions.

Inspect --status after execution. A changed input, configuration or verifier invalidates the old result. Failed or absent checks remain failures/unknowns; do not weaken criteria to get a pass.

For a visible flow, observe the actual result too. For important work, obtain a separate review when available. Report local checks, observation, independent review and publication separately. Command output is discarded by the verifier; diagnose a failing trusted check by running it directly when appropriate.
