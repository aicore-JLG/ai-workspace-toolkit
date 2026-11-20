---
name: workspace-security
description: Inspect skill and agent configuration risks and configure scoped secret handling.
---

# workspace-security

Read Security/README.md. Select source and scope, use tools/skill_review.py for the required content-bound activation review; add SkillSpector static checks and explicit-path AgentShield when installed. Inspect complete source and resolve findings. Local attestations do not prove independence; scans/hashes are not a sandbox. Use docs/DOPPLER.md for runtime injection. Never print credentials.
