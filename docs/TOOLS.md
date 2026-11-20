# Choose tools for the job

Version 0.4 adds [16 integration routes](../integrations/README.md), project-local setup through `tools/integrations.py`, and [Doppler injection](DOPPLER.md). Selected third-party skill sources are now bundled; the executable dependencies remain optional. The core prerequisite guidance below still applies.

Run `python -B tools/preflight.py` for executable presence only. It cannot confirm login, quota or runtime health. Nothing is installed or connected automatically.

| Tool | Use | Needed for |
|---|---|---|
| Python 3.11+ | Bundled standard-library utilities | Local commands and Python example |
| Git | Deliberate version control | Optional |
| Node.js and npm | JavaScript and browser tooling | Optional web work |
| ripgrep (rg) | Scoped text search | Optional local retrieval |
| GitHub CLI (gh) | Public repository discovery | Agent Search network mode |
| uv | Python environments and packages | Optional external tools |
| Playwright CLI | AI-driven browser operations/screenshots | Optional browser QA |
| Playwright Test | Repeatable browser assertions | Optional browser example |
| Agent Reach | Supported public web/social research | Optional external research |

## Agent Search is included

`python -B tools/agent_search.py "browser testing" --limit 5` previews discovery.
Add `--run` when you want a public GitHub search. Results are review signals, not endorsements. Read `.claude/skills/agent-search/SKILL.md`. No result is installed or executed.

## Playwright has two separate uses

The interactive CLI's upstream repository is Microsoft / playwright-cli; its package is `@playwright/cli`. Read its current official README for installation and requirements. The CLI is separate from Playwright Test.

The `examples/browser-check/` README supplies optional Test setup and a synthetic test. Packages and browser binaries are separate downloads. Use a separate test browser; never copy another person's cookies or profile.

## Agent Reach is optional

Identify its upstream repository as Panniantong / Agent-Reach. Read its current installation guide. That guide uses a GitHub release via uv and warns that a similarly named PyPI package is unrelated. Do not guess packages by name.

After your own installation, follow upstream setup/health checks and enable only needed channels. Availability can change. Keep credentials in supported local secret storage, never in prompts or the Knowledge register. Use [RESEARCH.md](RESEARCH.md) for evidence handling.

## Keep installation deliberate

Use the publisher's current official documentation, confirm exact package/repository, inspect permissions/licence and install only what you need. This release embeds no third-party installer, remote asset, owner endpoint or external document dependency.

Public research sends your chosen queries to external services. Do not include private client information, unreleased plans or confidential source text.
