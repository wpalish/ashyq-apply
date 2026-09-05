/**
 * The messenger, from the one screen a person actually uses.
 *
 * Runs against the dev principal, so there is one account here: enough to prove
 * the wiring — the screen loads, the setting saves, the badge reacts. The rule
 * about who may write first needs two people and is covered by the backend
 * suite, which can register several accounts without paying for a browser.
 */

import { expect, test } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

test('messages has its own screen, reachable and empty until someone writes', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('nav-messages').click();

  await expect(page.getByRole('heading', { name: 'Messages' })).toBeVisible();
  await expect(page.getByText('No conversations yet')).toBeVisible();
  // The empty state points at the setting rather than leaving a dead end.
  await expect(page.getByText(/Who may write to you first is up to you/)).toBeVisible();
});

test('the first-contact setting is on your own profile and saves', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('nav-me').click();

  const open = page.getByRole('button', { name: /^(Create profile|Edit profile)$/ });
  await expect(open).toBeVisible();
  if ((await open.textContent()) === 'Edit profile') await open.click();

  // A round trip in both directions, restoring what it found: the dev database
  // is shared between the two projects, so a test that asserted the default
  // would fail for whichever ran second. The default itself is pinned by
  // `test_a_new_profile_starts_on_the_narrow_policy` in the backend suite.
  const save = page.getByRole('button', { name: /^(Save profile|Create profile)$/ });
  for (const choice of ['anyone', 'threads'] as const) {
    await page.getByLabel('Who may write to you first').selectOption(choice);
    await save.click();

    await page.reload();
    await page.getByTestId('nav-me').click();
    await page.getByRole('button', { name: 'Edit profile' }).click();
    await expect(page.getByLabel('Who may write to you first')).toHaveValue(choice);
  }
});

test('the navigation carries no badge when nothing is unread', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('nav-messages').click();

  await expect(page.getByTestId('nav-messages').locator('.nav__badge')).toHaveCount(0);
});
