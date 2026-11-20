# Security workflow

Start with [actual security boundaries](../docs/SECURITY-BOUNDARIES.md). The kit supplies scoped tool checks and review gates, not an OS sandbox or global host hooks. SkillSpector, AgentShield and Doppler below are optional integrations requiring their own setup. Run toolkit commands from the kit root.

1. Discover public candidates with Agent Search; keep source descriptions untrusted.
2. Inspect source, licence, permissions and dependencies. Pin the chosen revision.
3. Scan skill contents with SkillSpector static mode. Audit host/project configuration with AgentShield using an explicit path.
4. Review findings and unresolved risks. A clean scan is not a guarantee.
5. Run `tools/skill_review.py scan INTEGRATION SKILL`, inspect the complete source and findings, then record an explicit `accept` with the current fingerprint, reviewer, rationale and every finding id acknowledged. The integration manager requires that content-bound receipt before activation and rechecks before promotion. It preserves existing destinations. The built-in scan is limited heuristic hygiene; it does not run SkillSpector automatically or certify safety. The receipt is a local self-attestation, not proof of reviewer identity or independence.
6. Use Doppler for selected runtime secrets. Set actual file/network permissions and sandboxing in the host where supported.

`config/workspace.example.json` documents intended choices; it does not enforce them. No host sandbox, credentials or permission settings are installed by this kit. Keep reports in ignored `.workspace/reports/security/`, and inspect/redact before sharing.

Integration subprocesses use the bounded shared runner. Doppler output and installer output are discarded; ordinary integration output goes to a bounded, redacted private log. See [execution controls](../docs/EXECUTION-CORE.md). Arbitrary trusted children still have the user's permissions and can create their own files or network requests.
