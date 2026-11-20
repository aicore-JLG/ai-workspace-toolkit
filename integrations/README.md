# Integration directory

These 16 optional integration routes extend the [15 included core skills](../README.md#the-15-included-skills). Selected upstream sources are available offline; complete runtimes, dependencies and account setup are separate. Start with the core and add a tool only when a task needs it.

Built-in memory, handoff and user-activated [Learn mode](../workflows/learn-mode.md) need none of these services. Learn mode is part of this kit, not an installed VibeWise plugin or a seventeenth integration. Agent Search is also a built-in helper; Agent Reach is the separate optional research integration below.

| Integration | Job | Delivery | Licence | Guide |
|---|---|---|---|---|
| ecc | Learning, skill audits, compaction and evaluation | npm | MIT | [Setup](guides/ecc.md) |
| skills-cli | Skill discovery, installation and version management | npm | MIT | [Setup](guides/skills-cli.md) |
| skill-creator | Author and improve skills with evaluations | bundle | Apache-2.0 | [Setup](guides/skill-creator.md) |
| skillspector | Static and optional model-based skill security scanning | python | Apache-2.0 | [Setup](guides/skillspector.md) |
| basic-memory | Markdown knowledge and project memory through MCP | python | AGPL-3.0 | [Setup](guides/basic-memory.md) |
| claude-md-management | Maintain project instructions and capture lessons | bundle | Apache-2.0 | [Setup](guides/claude-md-management.md) |
| skilled | Skill evaluation, regression comparison and improvement workflow | release | Apache-2.0 | [Setup](guides/skilled.md) |
| agent-reach | Public web and platform research | python | MIT | [Setup](guides/agent-reach.md) |
| agentshield | Audit agent configuration, hooks and MCP permissions | npm | MIT | [Setup](guides/agentshield.md) |
| agent-cleanup | Inspect stale worktrees, caches and temporary artifacts | bundle | MIT | [Setup](guides/agent-cleanup.md) |
| claude-mem | Alternative automatic session memory | npm | Apache-2.0 | [Setup](guides/claude-mem.md) |
| desloppify | Code quality scan and improvement loop | external | OSNL-0.2 | [Setup](guides/desloppify.md) |
| skill-eval-harness | Paired skill evaluations and holdouts | python | MIT | [Setup](guides/skill-eval-harness.md) |
| code-simplifier | Refine recently changed code | bundle | Apache-2.0 | [Setup](guides/code-simplifier.md) |
| superpowers | Optional development workflow skill pack | bundle | MIT | [Setup](guides/superpowers.md) |
| doppler | Inject project secrets into a child process | external | Apache-2.0 | [Setup](guides/doppler.md) |

`catalog.json` records immutable source commits, top-level package versions and supported setup routes. `bundles.lock.json` hashes every distributed upstream file. `vendor/` contains selected original sources and licences; do not load it wholesale into context or edit it in place. Create a candidate copy for improvements.

No automatic scanner, observer, cleanup job or host hook is running just because a file exists. The manager supports project-local installation for supported routes and reviewed skill activation; external routes have their own setup. See [integration commands](../docs/INTEGRATIONS.md). Run commands from the kit root. Installation previews do not install; explicit execution may download and run third-party code. Optional model-based evaluations/scans may consume separate provider usage; an integration listing does not grant account access or included subscription coverage.
