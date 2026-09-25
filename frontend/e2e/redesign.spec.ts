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
  // Concept P: a night globe behind the card with the route from home to
  // this programme's city, both ends named.
  const globe = page.getByTestId('triage-globe');
  await expect(globe).toBeVisible();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');
  await expect(globe.locator('.globe__name--home')).toHaveText('Astana');
  const firstCity = await globe.locator('.globe__name:not(.globe__name--home)').innerText();
  // The answers stay above a phone's tab bar (defect I27); on a wide screen
  // the tabs are at the top and the answers stay in the first screen.
  const answers = (await page.locator('.triage__answers').boundingBox())!;
  const tabs = (await page.locator('.navtabs').boundingBox())!;
  const floor = tabs.y > answers.y ? tabs.y : page.viewportSize()!.height;
  expect(answers.y + answers.height).toBeLessThanOrEqual(floor);
  await page.screenshot({ path: shot('14-one-at-a-time.png'), fullPage: false });

  await page.getByTestId('triage-maybe').click();
  await expect(card).not.toHaveAttribute('data-testid', `triage-card-${firstId}`);
  // The globe turns to the next programme's route.
  await expect(globe).not.toHaveAttribute('data-turning', 'true');
  const nextCity = (await card.locator('.triage__prog').innerText()).split(' · ').pop()!.split(',')[0]!.trim();
  await expect(globe.locator('.globe__name:not(.globe__name--home)')).toHaveText(nextCity);
  expect(firstCity).not.toBe('');

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
  // Concept 10: the programme opens on its route from home, both ends named.
  const route = groningen.locator('[data-testid^="route-"]');
  await expect(route).toBeVisible();
  await expect(route.locator('.globe__name')).toHaveText(['Groningen', 'Astana']);
  await page.screenshot({ path: shot('15-shortlist-cards.png'), fullPage: false });
  // The ladder folds into one line here, as the concept's budget sheet.
  await expect(page.getByTestId('budget-ladder')).toContainText('3 within 6,000 USD');
});

test('region chips count the list and filter it', async () => {
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const chips = page.getByTestId('region-chips');
  const total = Number((await chips.getByTestId('region-all').innerText()).replace(/\D/g, ''));
  const counts = await chips.locator('button:not([data-testid="region-all"]) .region-chips__n').allTextContents();
  expect(counts.map(Number).reduce((a, b) => a + b, 0)).toBe(total);

  // Cards sit in more than one group (ranked, and the ones set aside), so count them all.
  const cards = page.locator('main article[data-testid^="card-"]');
  await chips.getByTestId('region-europe').click();
  const europe = Number((await chips.getByTestId('region-europe').innerText()).replace(/\D/g, ''));
  await expect(cards).toHaveCount(europe);
  await expect(cards.filter({ hasText: 'University of Toronto' })).toHaveCount(0);
  await chips.getByTestId('region-all').click();
  await expect(cards).toHaveCount(total);
});

test('the globe places every programme at its city, turns by region and opens a card', async () => {
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const globe = page.getByTestId('shortlist-globe');
  await expect(globe).toBeVisible();
  // Every demo city is in the checked table, so nothing is left off.
  await expect(page.getByTestId('globe-unplaced')).toHaveCount(0);

  await page.getByTestId('region-americas').click();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');
  const americas = Number((await page.getByTestId('region-americas').innerText()).replace(/\D/g, ''));
  await expect(globe.locator('[data-testid^="globe-marker-"]')).toHaveCount(americas);

  const marker = globe.locator('[data-testid^="globe-marker-"]').first();
  const id = (await marker.getAttribute('data-testid'))!.replace('globe-marker-', '');
  await marker.click();
  await expect(page.getByTestId(`card-open-${id}`)).toHaveAttribute('aria-expanded', 'true');
  await page.getByTestId(`card-open-${id}`).click();
  await page.getByTestId('region-all').click();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');

  // Nothing goes missing silently (concept N): every programme is a marker,
  // in a cluster, or named at the edge the globe hides it towards.
  const total = Number((await page.getByTestId('region-all').innerText()).replace(/\D/g, ''));
  const sum = async (id: string) => (await globe.getByTestId(id).evaluateAll(
    (els) => els.map((e) => Number(e.getAttribute('data-count'))),
  )).reduce((a, b) => a + b, 0);
  const markers = await globe.locator('[data-testid^="globe-marker-"]').count();
  const atEdges = await sum('globe-edge');
  expect(atEdges).toBeGreaterThan(0);
  expect(markers + (await sum('globe-cluster')) + atEdges).toBe(total);
  // A chip at the edge turns the globe to what it names.
  const edge = globe.getByTestId('globe-edge').filter({ hasText: 'Americas' });
  await edge.click();
  await expect(page.getByTestId('globe-out')).toBeVisible();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');
  await expect(globe.getByTestId('globe-edge').filter({ hasText: 'Americas' })).toHaveCount(0);
  await page.getByTestId('globe-out').click();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');

  // Crowded cities fold into a cluster with a count; tapping it zooms in, and
  // "Whole globe" comes back. A marker is never moved far from its city.
  const cluster = globe.getByTestId('globe-cluster').first();
  const before = Number(await cluster.getAttribute('data-count'));
  expect(before).toBeGreaterThanOrEqual(4);
  await cluster.click();
  await expect(page.getByTestId('globe-out')).toBeVisible();
  await expect(globe).not.toHaveAttribute('data-turning', 'true');
  const afterClusters = await globe.getByTestId('globe-cluster').evaluateAll((els) => els.map((e) => Number(e.getAttribute('data-count'))));
  expect(Math.max(0, ...afterClusters)).toBeLessThan(before);
  await page.getByTestId('globe-out').click();
  await expect(page.getByTestId('globe-out')).toHaveCount(0);

  await goTo(page, 'progress');
  await expect(page.getByTestId('reveal-globe')).toBeVisible();
  await goTo(page, 'start');
  await expect(page.getByTestId('start-globe')).toBeAttached();
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

test('a story card is drawn on the device, with the privacy defaults and the demo label', async () => {
  // Concept Q: the map of the search, from the reveal.
  await goTo(page, 'progress');
  await page.getByTestId('share-map').click();
  const sheet = page.getByTestId('share-sheet');
  await expect(sheet).toBeVisible();
  const card = sheet.getByTestId('share-canvas');
  await expect(card).toHaveAttribute('data-ready', 'true');
  // The demo case has no name to add; price and scores are off; demo data says so.
  await expect(sheet.getByTestId('share-name')).not.toBeChecked();
  await expect(card).toHaveAttribute('aria-label', /Demo data, not real university pages/);
  await expect(card).toHaveAttribute('aria-label', /20 programmes\. 15 countries/);
  await expect(card).not.toHaveAttribute('aria-label', /%|chance|probab|will get in/i);
  const [download] = await Promise.all([page.waitForEvent('download'), sheet.getByTestId('share-save').click()]);
  expect(download.suggestedFilename()).toBe('ashyq-map.png');
  const png = await download.createReadStream().then(async (stream) => {
    const chunks: Buffer[] = [];
    for await (const chunk of stream) chunks.push(chunk as Buffer);
    return Buffer.concat(chunks);
  });
  expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([1080, 1920]);
  const axe = await new AxeBuilder({ page }).include('[data-testid="share-sheet"]')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(axe.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')).toEqual([]);
  await page.screenshot({ path: shot('17-share-story.png'), fullPage: false });
  await page.keyboard.press('Escape');
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('share-map')).toBeFocused();

  // "Requirements met" from a programme that meets them, with the
  // university's decision beside the headline.
  await goTo(page, 'shortlist');
  await page.getByTestId('view-cards').click();
  const tokyo = page.locator('main article[data-testid^="card-"]').filter({ hasText: 'University of Tokyo' }).first();
  const id = (await tokyo.getAttribute('data-testid'))!.replace('card-', '');
  const opener = page.getByTestId(`card-open-${id}`);
  if ((await opener.getAttribute('aria-expanded')) !== 'true') await opener.click();
  await page.getByTestId(`share-${id}`).click();
  await sheet.getByTestId('share-kind-requirements').check();
  await expect(card).toHaveAttribute('aria-label', /Requirements met/);
  await expect(card).toHaveAttribute('aria-label', /The admission decision is the university's/);
  await expect(card).toHaveAttribute('aria-label', /minimum 6\.5/);
  await expect(card).not.toHaveAttribute('aria-label', /mine/);
  await sheet.getByTestId('share-close').click();
  await expect(sheet).toHaveCount(0);
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

test('the start, the reveal, the cards, the comparison, the plan and the triage have no serious axe violations', async () => {
  const views: [string, () => Promise<void>][] = [
    ['start', async () => { await goTo(page, 'start'); }],
    ['reveal', async () => { await goTo(page, 'progress'); }],
    ['cards', async () => { await goTo(page, 'shortlist'); await page.getByTestId('view-cards').click(); }],
    ['compare', async () => { await page.getByTestId('compare-go').click(); }],
    ['plan', async () => { await goTo(page, 'approved'); }],
    ['one at a time', async () => { await openShortlist(page); await page.getByTestId('triage-start').click(); }],
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
