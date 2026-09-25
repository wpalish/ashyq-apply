/**
 * The «Горизонт» additions on the shortlist, against the real demo run:
 * the budget ladder and deciding one programme at a time, plus the folded
 * optional sections on the profile.
 *
 * Its own session, so answers given here cannot change what the journey spec
 * counts on the Approved screen.
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { goTo, newSession, openShortlist, runDemoResearch, shot } from './helpers';

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

test('the shortlist reads as price cards, and a card opens its programme', async () => {
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const cards = page.getByTestId('shortlist-cards');
  await expect(cards).toBeVisible();
  const groningen = cards.locator('article').filter({ hasText: 'University of Groningen' }).first();
  await expect(groningen).toContainText('1,848 USD');
  await expect(groningen).toContainText('a year after grants, if awarded');
  for (const line of ['Requirements', 'Your profile', 'Money']) {
    await expect(groningen).toContainText(line);
  }
  await expect(groningen).not.toContainText('%');
  // The open programme carries across views: the ladder test above opened it.
  const opener = groningen.getByRole('button', { name: 'University of Groningen' });
  if ((await opener.getAttribute('aria-expanded')) !== 'true') await opener.click();
  await expect(groningen.getByRole('tab', { name: 'Funding' })).toBeVisible();
  await page.screenshot({ path: shot('15-shortlist-cards.png'), fullPage: false });
  // The ladder folds into one line here, as the concept's budget sheet.
  await expect(page.getByTestId('budget-ladder')).toContainText('3 within 6,000 USD');
});

test('the results reveal counts what the run found', async () => {
  await goTo(page, 'progress');
  const reveal = page.getByTestId('results-reveal');
  await expect(reveal).toContainText('20 programmes in 15 countries');
  await expect(reveal).not.toContainText('%');
  await page.screenshot({ path: shot('16-results-reveal.png'), fullPage: false });

  // What the run found along the way, each read off the run: an exclusion, a
  // year mismatch and a site that did not answer - the concept's three.
  const found = page.getByTestId('found-list');
  await expect(found).toContainText('Requirement not met');
  await expect(found).toContainText('Different years');
  await expect(found).toContainText('University of Toronto');
  await expect(found).toContainText('Did not answer');
  await expect(found).toContainText('University of Oslo');
  await expect(found).not.toContainText(/%|chance|probab/i);
});

test('two programmes compare row by row, an unknown left unknown', async () => {
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const cards = page.getByTestId('shortlist-cards');
  for (const name of ['University of Groningen', 'University of Toronto']) {
    const card = cards.locator('article').filter({ hasText: name }).first();
    await card.getByRole('button', { name: 'Compare', exact: true }).click();
    await expect(card.getByRole('button', { name: 'In comparison' })).toHaveAttribute('aria-pressed', 'true');
  }
  const tray = page.getByTestId('compare-tray');
  await expect(tray).toContainText('2 picked');
  await page.getByTestId('compare-go').click();

  const view = page.getByTestId('compare-view');
  await expect(view.getByRole('heading', { name: 'Row by row' })).toBeFocused();
  await expect(view.getByRole('columnheader')).toHaveCount(2);
  const left = view.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'Left to pay a year' }) });
  await expect(left).toContainText('1,848 USD');
  // Toronto's award year does not match its costs, so the remainder is unknown.
  await expect(left).toContainText('not computed');
  await expect(view).not.toContainText('%');
  await expect(view).not.toContainText(/chance|probab/i);
  await page.screenshot({ path: shot('17-compare.png'), fullPage: false });

  await page.getByTestId('compare-close').click();
  await expect(page.getByTestId('compare-go')).toBeFocused();
});

test('the plan puts the nearest deadline on the board and every one after it in order', async () => {
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const cards = page.getByTestId('shortlist-cards');
  for (const name of ['University of Groningen', 'University of Tokyo']) {
    const keep = cards.locator('article').filter({ hasText: name }).first().locator('.decision-btn--approve');
    if ((await keep.getAttribute('aria-pressed')) !== 'true') await keep.click();
    await expect(keep).toHaveAttribute('aria-pressed', 'true');
  }

  await goTo(page, 'approved');
  // A new screen starts at its top, not at the shortlist's scroll position.
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  const board = page.getByTestId('deadline-board');
  await expect(board).toBeVisible();
  // Kept and "maybe" programmes only, as the counts under the board say.
  const count = async (word: string) => Number((await page.getByText(new RegExp(`^\\d+ ${word}$`)).innerText()).split(' ')[0]);
  const planned = (await count('approved')) + (await count('maybe'));
  expect(planned).toBeGreaterThanOrEqual(2);
  const applications = board.locator('[data-kind="admission"]');
  await expect(applications).toHaveCount(planned);
  await expect(applications.filter({ hasText: 'University of Groningen' })).toContainText('Action needed');
  // A grant with its own application is a deadline too, and Groningen's comes three months earlier.
  await expect(board.locator('[data-kind="award"]').filter({ hasText: 'Groningen Talent Grant' }))
    .toContainText('before the admission deadline');

  // Upcoming rows are in date order: the days left never go down.
  const days = (await board.locator('.board__row:not(.is-passed) .board__left [aria-hidden]').allTextContents())
    .map((text) => Number(text)).filter((n) => !Number.isNaN(n));
  expect(days).toEqual([...days].sort((a, b) => a - b));
  if (days.length) await expect(page.getByTestId('board-next')).toContainText(new RegExp(`${days[0]} days? left`));

  // A row opens onto its programme: the three answers, the money and the documents.
  const opener = applications.filter({ hasText: 'University of Groningen' }).getByRole('button');
  await opener.click();
  await expect(opener).toHaveAttribute('aria-expanded', 'true');
  const detail = board.locator('[data-testid^="board-detail-"]');
  for (const line of ['Requirements', 'Your profile', 'Money', 'Documents']) await expect(detail).toContainText(line);
  await expect(detail).toContainText('not collected yet');
  // Nothing to start before the lists exist, and the panel says what would fill it.
  await expect(page.getByTestId('next-to-start')).toContainText('Collect documents for what you keep');

  await expect(board).toContainText('Days are counted from today');
  await expect(board).not.toContainText('%');
  await expect(board).not.toContainText(/chance|probab/i);
  // The tiles flip in on arrival; the picture is of the board at rest.
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)));
  await page.screenshot({ path: shot('18-plan-board.png'), fullPage: false });
});

test('the start, the reveal, the cards, the comparison and the plan have no serious axe violations', async () => {
  const views: [string, () => Promise<void>][] = [
    ['start', async () => { await goTo(page, 'start'); }],
    ['reveal', async () => { await goTo(page, 'progress'); }],
    ['cards', async () => { await goTo(page, 'shortlist'); await page.getByTestId('view-cards').click(); }],
    ['compare', async () => { await page.getByTestId('compare-go').click(); }],
    ['plan', async () => { await goTo(page, 'approved'); }],
  ];
  for (const [name, open] of views) {
    await open();
    const report = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const serious = report.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    );
    expect(serious, `${name}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`).toEqual([]);
  }
});

test('optional profile sections fold while empty and open on request', async () => {
  await goTo(page, 'profile');
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
