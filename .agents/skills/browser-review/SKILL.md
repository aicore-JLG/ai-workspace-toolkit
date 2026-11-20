---
name: browser-review
description: Inspect an authorised website's actual user flow, responsiveness and errors using available browser tooling.
---

# Review in a browser

Follow workflows/browser-review.md from the known kit root. Read the intended flow and acceptance criteria first.

Use installed browser tooling such as Playwright CLI or the host's browser tool. Inspect current page state before acting. Check the outcome, narrow/desktop layouts and relevant errors; capture minimal non-sensitive evidence.

Do not install dependencies, reuse another person's browser session or submit external actions without the relevant authorisation. A Playwright CLI interaction is not automatically a repeatable Playwright Test suite.

Report observed behaviour, concrete defects and what was not checked. Do not infer visual quality from a successful build alone.
