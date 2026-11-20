# code-simplifier

Bundled agent brief for simplifying recently changed code. Invoke it through the workspace-code-cleanup skill with the changed files and acceptance checks.

## Included and pinned

- Repository: [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official)
- Source revision: [df9699a55c56](https://github.com/anthropics/claude-plugins-official/tree/df9699a55c56707e9948a32951ea356638ea8519)
- Upstream licence: Apache-2.0. Retain licence notices for bundled source.
- Installation kind: bundle. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

The original agent specifies Opus and JS/React conventions. The wrapper preserves the user-selected model and applies actual project conventions. It is an agent definition rather than SKILL.md, so activate does not install it as a skill.

## Setup from the extracted workspace root

```text
No automatic runtime installation. Use the source/activation or platform route below.
```

Source: integrations/vendor/code-simplifier/plugins/code-simplifier/agents/code-simplifier.md. No global agent or model configuration is installed.

Runtime installs stay in `.workspace/tools/code-simplifier/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
