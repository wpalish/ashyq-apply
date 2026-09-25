/**
 * The «Горизонт» additions on the shortlist, against the real demo run:
 * the budget ladder and deciding one programme at a time, plus the folded
 * optional sections on the profile.
 *
 * Its own session, so answers given here cannot change what the journey spec
 * counts on the Approved screen.
 */

import { expect, test, type Page } from '@playwright/test';
import { newSession, openShortlist, runDemoResearch, shot } from './helpers';

test.describe.configure({ mode: 'serial' });

let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
  await runDemoResearch(page);
});

test.afterAll(async () => {
  await page.close();
});

test('the budget ladder sorts the demo shortlist by what is left to pay', async () => {
  await openShortlist(page);
  const ladder = page.getByTestId('budget-ladder');
  await expect(ladder).toBeVisible();
  await expect(ladder).toContainText('6,000 USD');
  await expect(page.getByTestId('ladder-within')).toContainText(/Within budget · [1-9]/);
  // Nothing on the ladder is a chance: amounts and reasons only.
  await expect(ladder).not.toContainText('%');
  await expect(ladder).not.toContainText(/probab|chance of/i);

  // Every row within budget really is at or under the ceiling.
  const amounts = await ladder.locator('.ladder__row--within .ladder__amount').allTextContents();
  expect(amounts.length).toBeGreaterThan(0);
  for (const text of amounts) {
    expect(Number(text.replace(/[^\d]/g, ''))).toBeLessThanOrEqual(6000);
  }
  await page.screenshot({ path: shot('13-budget-ladder.png'), fullPage: false });
});

test('a ladder row opens its programme in the table', async () => {
  await openShortlist(page);
  const first = page.locator('[data-testid^="ladder-row-"]').first();
  const id = (await first.getAttribute('data-testid'))!.replace('ladder-row-', '');
  await first.click();
  await expect(page.getByTestId(`expand-${id}`)).toHaveAttribute('aria-expanded', 'true');
});

test('one at a time: an answer moves to the next programme and shows in the table', async () => {
  await openShortlist(page);
  await page.getByTestId('triage-start').click();
  const card = page.locator('[data-testid^="triage-card-"]');
  await expect(card).toBeVisible();
  const firstId = (await card.getAttribute('data-testid'))!.replace('triage-card-', '');
  await page.screenshot({ path: shot('14-one-at-a-time.png'), fullPage: false });

  await page.getByTestId('triage-maybe').click();
  await expect(card).not.toHaveAttribute('data-testid', `triage-card-${firstId}`);

  // A rejection still asks why before it is saved.
  await page.getByTestId('triage-reject').click();
  await expect(page.getByTestId('triage-reason')).toBeVisible();
  await page.getByRole('button', { name: 'Cancel' }).click();

  await page.getByTestId('triage-close').click();
  await expect(page.getByTestId(`maybe-${firstId}`)).toHaveAttribute('aria-pressed', 'true');
});

test('optional profile sections fold while empty and open on request', async () => {
  await page.getByTestId('nav-profile').click();
  const activities = page.getByTestId('fold-activities');
  // The demo profile has activities, so the section starts open.
  await expect(activities).toHaveAttribute('open', '');

  await page.getByTestId('clear-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.count()) await confirm.click();

  await expect(activities).not.toHaveAttribute('open');
  await expect(activities).toContainText('optional');
  await activities.locator('summary').click();
  await expect(activities).toHaveAttribute('open', '');
  await expect(activities.getByRole('button', { name: /Add activity/ })).toBeVisible();
});
