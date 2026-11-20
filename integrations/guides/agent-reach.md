# agent-reach

Research public sources through the official upstream tool. Agent Search remains included at tools/agent_search.py for public repository discovery.

## Included and pinned

- Repository: [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)
- Source revision: [c70ae6da5d39](https://github.com/Panniantong/Agent-Reach/tree/c70ae6da5d39bc90e09ad2ae0575ccc89f31e284)
- Upstream licence: MIT. Retain licence notices for bundled source.
- Installation kind: python. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

Python + uv + Git. Channel setup installs extra tools; some channels need accounts or keys. Setup may change user-level skill/channel configuration, so inspect it separately after CLI installation. Never copy an author account or browser session into a recipient kit.

## Setup from the extracted workspace root

```text
python -B tools/integrations.py install agent-reach
python -B tools/integrations.py install agent-reach --run
```

python -B tools/integrations.py run agent-reach -- version
python -B tools/integrations.py run agent-reach -- doctor --text
Configure only needed channels using upstream instructions. Do not install the unrelated same-name package from PyPI.

Runtime installs stay in `.workspace/tools/agent-reach/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
