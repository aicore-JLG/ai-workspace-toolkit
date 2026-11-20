# claude-md-management

Use claude-md-improver for instruction audits, and the bundled revise-claude-md command as an end-of-session reference.

## Included and pinned

- Repository: [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official)
- Source revision: [df9699a55c56](https://github.com/anthropics/claude-plugins-official/tree/df9699a55c56707e9948a32951ea356638ea8519)
- Upstream licence: Apache-2.0. Retain licence notices for bundled source.
- Installation kind: bundle. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

Claude-oriented. Review scope before scanning; adapt findings for AGENTS.md deliberately. Do not append every observation to the permanent rulebook.

## Setup from the extracted workspace root

```text
No automatic runtime installation. Use the source/activation or platform route below.
```

python -B tools/integrations.py activate claude-md-management claude-md-improver --host claude --write
The revise command is retained under integrations/vendor/claude-md-management/plugins/claude-md-management/commands/.

Runtime installs stay in `.workspace/tools/claude-md-management/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
