# Optional browser test example

This is a synthetic page exercised in memory by Playwright Test. It does not contact a website or use an account. It is separate from the Python core example.

In this folder, after deliberately choosing to install the optional dependency:

```text
npm install --save-dev @playwright/test
npx playwright install chromium
npx playwright test
```

These commands download packages/browser binaries and change this example folder. They are not part of the core setup and were not automatically run when the kit was built. Review the official current Playwright instructions linked in [the tool guide](../../docs/TOOLS.md).

The test checks a user-visible interaction and a narrow viewport for horizontal overflow. Replace the synthetic page with your authorised application and meaningful acceptance criteria when adapting it.
