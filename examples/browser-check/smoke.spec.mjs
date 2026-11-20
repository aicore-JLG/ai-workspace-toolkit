import { test, expect } from '@playwright/test';

test('a visitor can reveal the next action without mobile overflow', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.setContent(`<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Workspace example</title><main><h1>Start a project</h1>
    <button type="button" onclick="document.querySelector('#result').hidden=false">Show next action</button>
    <p id="result" hidden>Write the project outcome.</p></main></html>`);
  await page.getByRole('button', { name: 'Show next action' }).click();
  await expect(page.getByText('Write the project outcome.')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
