# agentshield

Audit the selected project configuration alongside SkillSpector. Specify a path instead of defaulting to the home directory.

## Included and pinned

- Repository: [affaan-m/agentshield](https://github.com/affaan-m/agentshield)
- Source revision: [b0891303bdcd](https://github.com/affaan-m/agentshield/tree/b0891303bdcd6037376a94263d45cfd2ff3dfb98)
- Upstream licence: MIT. Retain licence notices for bundled source.
- Installation kind: npm. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

Node.js/npm. Static audit does not enforce runtime access. Optional deeper model analysis requires a separate budget and provider setup.

## Setup from the extracted workspace root

```text
python -B tools/integrations.py install agentshield
python -B tools/integrations.py install agentshield --run
```

python -B tools/integrations.py run agentshield -- scan --path . --format json

Runtime installs stay in `.workspace/tools/agentshield/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
