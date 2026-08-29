/**
 * FP-10: a saved profile must survive a reload unchanged.
 *
 * The draft used to stay as the synthetic demo profile after a reload while
 * `savedProfile` pointed at the real one, so the next save wrote demo data over
 * the applicant's own. Its own session on purpose: it needs a clean
 * localStorage and it edits the profile, which the shared journey relies on.
 */

import { expect, test } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

test('a saved profile is restored into the form after a reload', async ({ page }) => {
  await page.goto('/');

  // Start from a blank profile so nothing synthetic is in play.
  await page.getByTestId('clear-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  await page.getByLabel('Citizenship').fill('Uzbekistan');
  await page.getByLabel('Field of study').fill('civil engineering');
  await page.getByTestId('ielts-overall').fill('7');
  await page.getByTestId('save-profile').click();
  await expect(page.getByText('Saved')).toBeVisible();

  await page.reload();

  await expect(page.getByLabel('Citizenship')).toHaveValue('Uzbekistan', { timeout: 15_000 });
  await expect(page.getByLabel('Field of study')).toHaveValue('civil engineering');
  await expect(page.getByTestId('ielts-overall')).toHaveValue('7');
});

test('demo data is only ever loaded on request, and is labelled when it is', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('clear-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  await expect(page.getByLabel('Field of study')).toHaveValue('');
  await expect(page.getByText('synthetic demo data')).toBeHidden();

  await page.getByTestId('load-demo-profile').click();
  const confirm2 = page.getByTestId('confirm-replace');
  if (await confirm2.isVisible().catch(() => false)) await confirm2.click();

  await expect(page.getByLabel('Field of study')).toHaveValue('computer science');
  await expect(page.getByText('synthetic demo data')).toBeVisible();
});

test('replacing a saved profile asks first', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('clear-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  await page.getByLabel('Citizenship').fill('Georgia');
  await page.getByTestId('save-profile').click();
  await expect(page.getByText('Saved')).toBeVisible();

  await page.getByTestId('load-demo-profile').click();
  await expect(page.getByText('Replace the profile you have saved?')).toBeVisible();
  await page.getByRole('button', { name: 'Keep editing' }).click();
  await expect(page.getByLabel('Citizenship')).toHaveValue('Georgia');
});

test('the gap summary sits above the form and jumps to the detail', async ({ page }) => {
  // The panel explaining what each blank costs is six screens down, past
  // eighty fields. A student needs to know which blanks matter *before*
  // deciding what to fill in, so a summary leads the form.
  await page.goto('/');
  await page.getByTestId('load-demo-profile').click();

  const summary = page.getByTestId('jump-to-gaps');
  await expect(summary).toBeVisible();

  const summaryTop = await summary.evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
  const detailTop = await page
    .getByTestId('gap-list')
    .evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
  expect(summaryTop, 'the summary must come before the detail').toBeLessThan(detailTop);

  await summary.click();
  await expect(page.getByTestId('gap-list')).toBeInViewport();
});
