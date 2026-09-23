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
  await page.goto('/#/profile');
  await page.getByTestId('profile-show-all').click();

  // Start from a blank profile so nothing synthetic is in play.
  await page.getByTestId('clear-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  await page.getByLabel('Citizenship').fill('Uzbekistan');
  await page.getByLabel('Field of study').fill('civil engineering');
  await page.getByTestId('ielts-overall').fill('7');
  await page.getByRole('button', { name: '+ Add activity' }).click();
  const activityLinks = page.getByTestId('activity-0-evidence');
  await activityLinks.getByRole('button', { name: '+ Add evidence link' }).click();
  await activityLinks.getByRole('textbox', { name: 'Evidence link 1', exact: true })
    .fill('https://example.org/activity?awards=one,two');
  await page.getByRole('button', { name: '+ Add achievement' }).click();
  const achievementLinks = page.getByTestId('achievement-0-evidence');
  await achievementLinks.getByRole('button', { name: '+ Add evidence link' }).click();
  await achievementLinks.getByRole('textbox', { name: 'Evidence link 1', exact: true })
    .fill('https://example.org/achievement#gold');
  await page.getByTestId('save-profile').click();
  await expect(page.getByText('Saved', { exact: true })).toBeVisible();

  await page.reload();
  // Hydration changes the activeCaseKey from its initial null value to the
  // saved profile id. Wait for that handoff before enabling temporary review
  // mode; otherwise the case-key guard correctly clears the early click.
  await expect(page.getByText('Loaded saved profile:', { exact: false })).toBeVisible();
  await page.getByTestId('profile-show-all').click();

  await expect(page.getByLabel('Citizenship')).toHaveValue('Uzbekistan', { timeout: 15_000 });
  await expect(page.getByLabel('Field of study')).toHaveValue('civil engineering');
  await expect(page.getByTestId('ielts-overall')).toHaveValue('7');
  await expect(page.getByTestId('activity-0-evidence').getByRole('textbox', { name: 'Evidence link 1', exact: true }))
    .toHaveValue('https://example.org/activity?awards=one,two');
  await expect(page.getByTestId('achievement-0-evidence').getByRole('textbox', { name: 'Evidence link 1', exact: true }))
    .toHaveValue('https://example.org/achievement#gold');
});

test('demo data is only ever loaded on request, and is labelled when it is', async ({ page }) => {
  await page.goto('/#/profile');
  await page.getByTestId('profile-show-all').click();
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
  await page.goto('/#/profile');
  await page.getByTestId('profile-show-all').click();
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
