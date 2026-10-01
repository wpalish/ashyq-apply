/**
 * FP-10: a saved profile must survive a reload unchanged.
 *
 * The draft used to stay as the synthetic demo profile after a reload while
 * `savedProfile` pointed at the real one, so the next save wrote demo data over
 * the applicant's own. Its own session on purpose: it needs a clean
 * localStorage and it edits the profile, which the shared journey relies on.
 *
 * The `Saved` chip is asserted with `exact: true`. Without it the match is a
 * case-insensitive substring, so the transcript hint — "it is never saved" —
 * answers for the chip and the assertion fails in strict mode. Only the chip's
 * whole text is `Saved`.
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
  await expect(page.getByText('Saved', { exact: true })).toBeVisible();

  await page.reload();

  await expect(page.getByLabel('Citizenship')).toHaveValue('Uzbekistan', { timeout: 15_000 });
  await expect(page.getByLabel('Field of study')).toHaveValue('civil engineering');
  await expect(page.getByTestId('ielts-overall')).toHaveValue('7');
});

test('demo data is only ever loaded on request, and is labelled when it is', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByLabel('Field of study')).toHaveValue('');
  await expect(page.getByLabel('Citizenship')).toHaveValue('');
  await expect(page.getByLabel('GPA / average')).toHaveValue('');
  await expect(page.getByLabel('SAT total')).toHaveValue('');
  await expect(page.getByTestId('ielts-overall')).toHaveValue('');
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
  await expect(page.getByText('Saved', { exact: true })).toBeVisible();

  await page.getByTestId('load-demo-profile').click();
  await expect(page.getByText('Replace the profile you have saved?')).toBeVisible();
  await page.getByRole('button', { name: 'Keep editing' }).click();
  await expect(page.getByLabel('Citizenship')).toHaveValue('Georgia');
});

test('typing multiple subjects and countries keeps separators and saves complete lists', async ({ page }) => {
  await page.goto('/');
  const field = page.getByLabel('Field of study');
  await field.pressSequentially('Computer Science, Mathematics, ');
  await expect(field).toHaveValue('Computer Science, Mathematics, ');
  await page.getByTestId('to-preferences').click();

  const excluded = page.getByLabel('Excluded countries');
  await excluded.pressSequentially('Austria, Canada, Czech Republic, ');
  await expect(excluded).toHaveValue('Austria, Canada, Czech Republic, ');
  await page.getByLabel('Preferred countries').pressSequentially('Singapore, United Kingdom');
  await page.getByLabel('Research interests').pressSequentially('machine learning, data science');
  await page.getByTestId('nav-profile').click();

  const profileRequest = page.waitForRequest((request) =>
    request.method() === 'POST' && request.url().endsWith('/api/profiles'));
  await page.getByTestId('save-profile').click();
  expect((await profileRequest).postDataJSON()).toMatchObject({
    context: { intended_fields: ['Computer Science', 'Mathematics'] },
    preferences: {
      preferred_countries: ['Singapore', 'United Kingdom'],
      excluded_countries: ['Austria', 'Canada', 'Czech Republic'],
      research_interests: ['machine learning', 'data science'],
    },
  });
  await expect(page.getByText('Saved', { exact: true })).toBeVisible();
  await page.reload();
  await expect(field).toHaveValue('Computer Science, Mathematics');
  await page.getByTestId('to-preferences').click();
  await expect(excluded).toHaveValue('Austria, Canada, Czech Republic');
});
