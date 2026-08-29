/**
 * The critical path, end to end, plus a screenshot of each main state.
 *
 * Assertions target published behaviour rather than pixels: that a full-tuition
 * award is not called a full ride, that an ineligible scholarship is marked
 * ineligible, that a zero gap is refused when the figures are not comparable.
 */

import { expect, test, type Page } from '@playwright/test';
import { expandRow, newSession, openShortlist, rowFor, shot, waitForResults } from './helpers';

test.describe.configure({ mode: 'serial' });

let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
});

test.afterAll(async () => {
  await page.close();
});

test('profile screen states the cost of every gap', async () => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Who is applying' })).toBeVisible();
  await expect(page.locator('.topbar').getByText('Demo data')).toBeVisible();
  await page.screenshot({ path: shot('01-profile.png'), fullPage: true });

  // Removing the English scores must produce a gap that explains the consequence.
  await page.getByTestId('ielts-overall').fill('');
  await expect(page.getByTestId('gap-list')).toContainText('English-language minimums', {
    timeout: 10_000,
  });
  await page.getByTestId('ielts-overall').fill('7');
});

test('preferences screen exposes the scoring weights and warns about live mode', async () => {
  await page.goto('/');
  await page.getByTestId('to-preferences').click();
  await expect(page.getByRole('heading', { name: 'What matters to you' })).toBeVisible();
  await expect(page.getByText('It is not a probability of admission')).toBeVisible();

  await page.getByTestId('demo-toggle').uncheck();
  await expect(page.getByText('Live mode fetches real university websites')).toBeVisible();
  await page.getByTestId('demo-toggle').check();
  await page.screenshot({ path: shot('02-preferences.png'), fullPage: true });
});

test('research runs to completion and reports what it could not read', async () => {
  await page.getByTestId('nav-preferences').click();
  await page.getByTestId('start-research').click();

  await expect(page.getByTestId('stage-list')).toBeVisible();
  await page.screenshot({ path: shot('03-progress-running.png'), fullPage: true });

  await waitForResults(page);
  await expect(page.getByText('Research complete')).toBeVisible();
  // Unreadable pages are surfaced, not swallowed.
  await expect(page.getByText(/Pages that could not be read/)).toBeVisible();
  await page.screenshot({ path: shot('04-progress-complete.png'), fullPage: true });
});

test('the shortlist separates eligibility, fit and funding', async () => {
  await openShortlist(page);

  const headers = page.locator('thead th');
  await expect(headers.nth(1)).toHaveText('Eligibility');
  await expect(headers.nth(2)).toHaveText('Admissions fit');
  await expect(headers.nth(3)).toHaveText('Funding');

  await expect(page.locator('tbody tr')).not.toHaveCount(0);
  await expect(page.getByText('Demo data.', { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: shot('05-shortlist.png'), fullPage: true });
});

test('marketing language does not turn full tuition into a full ride', async () => {
  await openShortlist(page);

  const asu = rowFor(page, 'Arizona State University');
  await expect(asu).toBeVisible();
  // The corpus page for this award literally says "a full ride to an ASU degree".
  await expect(asu).toContainText('Full tuition');
  await expect(asu).not.toContainText('Full ride');
  // The tooltip still carries the full meaning behind the shortened chip.
  await expect(asu.getByTitle(/Tuition is covered/)).toBeVisible();
});

test('a past deadline is flagged and blocks eligibility', async () => {
  await openShortlist(page);

  const melbourne = rowFor(page, 'University of Melbourne');
  await expect(melbourne).toContainText('passed');
  await expect(melbourne).toContainText('Gap');
});

test('a citizenship-restricted award is shown as not eligible', async () => {
  await openShortlist(page);

  await expandRow(page, 'KU Leuven');
  await page.getByTestId('tab-funding').click();

  const flemish = page.locator('.panel').filter({ hasText: 'Flemish Community Tuition Grant' }).first();
  await expect(flemish).toContainText('Not eligible');
  await expect(flemish).toContainText('European Economic Area');
  await page.screenshot({ path: shot('06-university-detail-funding.png'), fullPage: true });
});

test('an incomparable zero is refused rather than shown as nothing to pay', async () => {
  await openShortlist(page);

  // Toronto's award amount is published for 2024/25 while costs are 2026/27.
  const toronto = rowFor(page, 'University of Toronto');
  await expect(toronto).toContainText('not computable');

  await expandRow(page, 'University of Toronto');
  await page.getByTestId('tab-costs').click();
  await expect(page.getByText('Not computed.')).toBeVisible();
  await expect(page.getByText(/not directly comparable/)).toBeVisible();
});

test('a per-section IELTS minimum is enforced independently of the overall band', async () => {
  await openShortlist(page);

  // The demo applicant has overall 7.0 but writing 6.0; Delft requires 6.5 per band.
  const delft = rowFor(page, 'Delft University of Technology');
  await expect(delft).toContainText('Gap');

  await expandRow(page, 'Delft University of Technology');
  const barrier = page.locator('.notice--risk').filter({ hasText: 'Confirmed requirement not met' });
  await expect(barrier).toBeVisible();
  await expect(barrier).toContainText('IELTS writing');
  await page.screenshot({ path: shot('07-university-detail-requirements.png'), fullPage: true });
});

test('missing scholarship data reads as unknown, not as no funding', async () => {
  await openShortlist(page);

  const vienna = rowFor(page, 'University of Vienna');
  await expect(vienna).toContainText('Unknown');

  await expandRow(page, 'University of Vienna');
  await page.getByTestId('tab-funding').click();
  await expect(page.getByText(/that is not the same as there being none/)).toBeVisible();
});

test('conflicting official sources are shown with a drafted question', async () => {
  await openShortlist(page);
  await page.getByTestId('nav-sources').click();

  await expect(page.getByRole('heading', { name: 'What we could not settle' })).toBeVisible();
  await expect(page.getByTestId('conflict-list')).toContainText('minimum overall IELTS band');
  await expect(page.getByTestId('conflict-list')).toContainText('more specific source');

  await page.getByText('Draft question for the admissions office').first().click();
  await expect(page.getByText('Dear Admissions Office,')).toBeVisible();
  await page.screenshot({ path: shot('09-sources-conflicts.png'), fullPage: true });
});

test('funding comparison hatches what it cannot compare', async () => {
  await openShortlist(page);
  await page.getByTestId('nav-funding').click();

  await expect(page.getByRole('heading', { name: 'What you would actually pay' })).toBeVisible();
  await expect(page.locator('.fund-bar__unknown').first()).toBeVisible();
  await page.screenshot({ path: shot('08-funding-comparison.png'), fullPage: true });
});

test('approve, collect documents, and export', async () => {
  await openShortlist(page);

  // Approve the two best-funded rows.
  const rows = page.locator('tbody tr').filter({ has: page.locator('.decision-btn--approve') });
  await rows.nth(0).locator('.decision-btn--approve').click();
  await rows.nth(1).locator('.decision-btn--approve').click();
  await expect(rows.nth(0).locator('.decision-btn--approve')).toHaveAttribute('aria-pressed', 'true');

  await page.getByTestId('nav-approved').click();
  await expect(page.getByText('2 applying')).toBeVisible();
  await page.screenshot({ path: shot('10-approved.png'), fullPage: true });

  await page.getByTestId('collect-documents').click();
  await expect(page.getByRole('heading', { name: 'What to prepare, and when' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.locator('.doc').first()).toBeVisible({ timeout: 30_000 });
  // Lead-time ordering puts the referee first, because that is what sinks applications.
  await expect(page.locator('.doc').first()).toContainText(/reference|transcript|diploma|statement/i);
  await page.screenshot({ path: shot('11-documents.png'), fullPage: true });

  await page.getByTestId('nav-export').click();
  await expect(page.getByRole('heading', { name: 'Take it with you, or erase it' })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByTestId('export-csv').click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.csv$/);
  await page.screenshot({ path: shot('12-export.png'), fullPage: true });
});

test('rejection is remembered with the row kept', async () => {
  await openShortlist(page);

  const first = page.locator('tbody tr').first();
  const name = await first.locator('.uni-cell__name').innerText();
  await first.locator('.decision-btn--reject').click();
  await expect(first.locator('.decision-btn--reject')).toHaveAttribute('aria-pressed', 'true');
  await expect(first).toHaveClass(/is-rejected/);

  await page.getByTestId('nav-approved').click();
  await expect(page.getByText('Rejected (1)')).toBeVisible();
  await expect(page.getByText(name)).toBeVisible();
  await expect(page.getByText(/not proposed again unless something material changes/)).toBeVisible();
});
