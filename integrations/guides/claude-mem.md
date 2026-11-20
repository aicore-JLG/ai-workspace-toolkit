# claude-mem

Optional episode-capture provider. It can coexist with curated knowledge when scope, retention and promotion ownership are explicit. Avoid duplicate observers through ECC or other services. No capture or sync with the local memory core is enabled here.

## Included and pinned

- Repository: [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)
- Source revision: [4b48c5727ab6](https://github.com/thedotmack/claude-mem/tree/4b48c5727ab62ee22e72a71b822a2fb225491fa2)
- Upstream licence: Apache-2.0. Retain licence notices for bundled source.
- Installation kind: npm. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

Node.js and an observer provider. Upstream setup offers account/provider/analytics choices and may start services or capture sessions. Installing the CLI here does not run its onboarding. Some integrations support search only.

## Setup from the extracted workspace root

```text
python -B tools/integrations.py install claude-mem
python -B tools/integrations.py install claude-mem --run
```

Read the pinned upstream README, then use the local CLI for an explicitly chosen setup. Do not run install/onboarding unattended or choose a provider for the recipient.

Runtime installs stay in `.workspace/tools/claude-mem/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
