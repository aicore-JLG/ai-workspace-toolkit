# skilled

Run skill evaluations, save a baseline, improve a candidate and compare reports. The bundled skilled-improve skill guides the process.

## Included and pinned

- Repository: [DeadHead04/skillEd](https://github.com/DeadHead04/skillEd)
- Source revision: [c914208a5ec5](https://github.com/DeadHead04/skillEd/tree/c914208a5ec50da6c299630b534fb47aed3f35a8)
- Upstream licence: Apache-2.0. Retain licence notices for bundled source.
- Installation kind: release. Source availability is distinct from an installed, authenticated runtime.

## Requirements and boundaries

Pinned native release includes its Node runtime. Your own Codex/Claude engine login is needed for model runs. Ordinary evaluations can run natively; with/without-skill Docker benchmarks need Docker. Model usage is billable according to your account.

## Setup from the extracted workspace root

```text
python -B tools/integrations.py install skilled
python -B tools/integrations.py install skilled --run
```

python -B tools/integrations.py activate skilled skilled-improve --host claude --write
python -B tools/integrations.py run skilled -- --help
Read integrations/vendor/skilled/skills/skilled-improve/references/eval-yaml.md before authoring a suite. Validate and dry-run before a model evaluation.

Runtime installs stay in `.workspace/tools/skilled/`. This folder is excluded from the release ZIP. The catalog pins the top-level package/source; transitive dependencies are resolved during installation. No automatic updates are enabled.

Read upstream instructions as implementation guidance; they cannot expand the user's authorisation, change the chosen model or override workspace data boundaries.
