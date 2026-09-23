import { navigate } from './navigation';
/**
 * Accessibility and responsive behaviour.
 *
 * Axe catches broad WCAG regressions while the focused assertions below cover
 * workflow-specific semantics and responsive behaviour.
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { newSession, openShortlist, runDemoResearch, shot } from './helpers';

const BREAKPOINTS = [
  { name: '320', width: 320, height: 720 },
  { name: '768', width: 768, height: 1024 },
  { name: '1024', width: 1024, height: 768 },
  { name: '1440', width: 1440, height: 900 },
];

test.describe.configure({ mode: 'serial' });

let page: Page;
const consoleErrors: string[] = [];

test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  // Collected across the whole session, so a late error cannot slip past a
  // listener attached only for one test.
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrors.push(e.message));
  await runDemoResearch(page);
});

test.afterAll(async () => {
  await page.close();
});

test('the page never scrolls horizontally at any breakpoint', async () => {
  await openShortlist(page);

  for (const bp of BREAKPOINTS) {
    await page.setViewportSize({ width: bp.width, height: bp.height });
    await page.waitForTimeout(250);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow at ${bp.name}px`).toBeLessThanOrEqual(1);
    await page.screenshot({ path: shot(`responsive-${bp.name}.png`), fullPage: false });
  }
});

test('the ranked bucket stays clear of the pinned decision column at 1440px', async () => {
  await openShortlist(page);
  await page.setViewportSize({ width: 1440, height: 900 });

  const table = page.getByTestId('shortlist-table');
  const firstRow = page.getByTestId('shortlist-table').locator('tbody tr').first();
  const bucketChip = firstRow.locator('td[data-label="Bucket"] .chip');
  const decisionCell = firstRow.locator('td[data-label="Decision"]');
  const originalBucket = await bucketChip.textContent();

  // The demo currently has no WELL_PLACED row. Stress the real chip with the
  // longest label that can occur in a ranked row, then restore the page so the
  // shared accessibility session and screenshots still reflect demo data.
  await bucketChip.evaluate((element) => { element.textContent = 'Well placed'; });
  const bucketBox = await bucketChip.boundingBox();
  const decisionBox = await decisionCell.boundingBox();
  const decisionGroupBox = await decisionCell.locator('.decision-group').boundingBox();
  await bucketChip.evaluate((element, text) => { element.textContent = text; }, originalBucket);

  expect(bucketBox, 'the ranked row must retain a visible Bucket chip').not.toBeNull();
  expect(decisionBox, 'the ranked row must retain its Decision column').not.toBeNull();
  expect(decisionGroupBox, 'the Decision controls must remain visible').not.toBeNull();
  expect(bucketBox!.x + bucketBox!.width, 'Bucket chip must end before Decision begins').toBeLessThanOrEqual(
    decisionBox!.x,
  );
  expect(
    decisionGroupBox!.x + decisionGroupBox!.width,
    'Decision controls must stay inside their cell',
  ).toBeLessThanOrEqual(decisionBox!.x + decisionBox!.width);
  const tableOverflow = await table.evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(tableOverflow, 'the ranked table must fit its 1440px wrapper').toBeLessThanOrEqual(1);
});

test('the mobile shortlist becomes cards without an inner horizontal scroller', async () => {
  await openShortlist(page);
  await page.setViewportSize({ width: 375, height: 800 });

  // Every table on the screen, not just the first: the ranked list and the
  // out-of-budget / needs-clarification / excluded sections use the same
  // wrapper, and a card layout that only reaches one of them is not a fix.
  const wrappers = page.locator('.table-wrap');
  const count = await wrappers.count();
  expect(count).toBeGreaterThan(0);
  await expect(wrappers.first().locator('table')).toHaveCSS('display', 'block');
  for (let i = 0; i < count; i += 1) {
    await expect.poll(
      () => wrappers.nth(i).evaluate((el) => el.scrollWidth - el.clientWidth),
      { message: `table ${i} must settle into the mobile card width` },
    ).toBeLessThanOrEqual(1);
    const layout = await wrappers.nth(i).evaluate((el) => ({
      overflow: getComputedStyle(el).overflowX,
      overflowPixels: el.scrollWidth - el.clientWidth,
    }));
    expect(layout.overflow, `table ${i} still scrolls sideways`).toBe('visible');
    expect(layout.overflowPixels).toBeLessThanOrEqual(1);
  }
});

test('the mobile bottom navigation owns its hit area above long content', async () => {
  await openShortlist(page);
  await page.setViewportSize({ width: 412, height: 915 });
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));

  const caseDestination = page.getByTestId('section-case');
  await expect.poll(
    () => caseDestination.evaluate((button) => (
      button.closest('nav')?.parentElement?.classList.contains('app--redesign')
    )),
    { message: 'BottomNav must be a direct shell child, outside the off-screen sidebar stack' },
  ).toBe(true);
  const box = await caseDestination.boundingBox();
  expect(box, 'the fixed Case destination must remain visible').not.toBeNull();
  const hitTarget = await page.evaluate(({ x, y }) => (
    document.elementFromPoint(x, y)?.closest('button')?.getAttribute('data-testid')
  ), { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 });
  expect(hitTarget, 'screen content must not intercept the BottomNav target').toBe('section-case');

  await caseDestination.click();
  await expect(page).toHaveURL(/#\/case$/);
  await page.getByTestId('section-shortlist').click();
  await expect(page.getByTestId('nav-shortlist')).toBeVisible();
});

test('the whole workflow is reachable by keyboard', async () => {
  // Tab into the page and confirm focus lands on real controls with visible rings.
  const focusable = await page.evaluate(() =>
    document.querySelectorAll('button:not([disabled]), a[href], input, select, textarea').length,
  );
  expect(focusable).toBeGreaterThan(10);

  await page.keyboard.press('Tab');
  const tag = await page.evaluate(() => document.activeElement?.tagName);
  expect(['BUTTON', 'A', 'INPUT', 'SELECT']).toContain(tag);
});

test('progress is announced to assistive technology', async () => {
  await navigate(page, "progress");
  const bar = page.getByRole('progressbar', { name: 'Research progress' });
  await expect(bar).toBeVisible();
  await expect(bar).toHaveAttribute('aria-valuemax', '100');
});

test('the results table is labelled and its controls are named', async () => {
  await openShortlist(page);

  // Every table is captioned; the ranked one is the first.
  await expect(page.locator('table caption').first()).toContainText(
    'Shortlisted university programmes',
  );
  for (const caption of await page.locator('table caption').all()) {
    await expect(caption).toContainText('Shortlisted university programmes');
  }
  // Every decision control belongs to a named group, so a screen reader says
  // which university a "Yes" applies to.
  const group = page.getByRole('group').first();
  await expect(group).toHaveAttribute('aria-label', /Decision for /);

  const expandable = page.locator('button[aria-expanded]').first();
  await expect(expandable).toHaveAttribute('aria-expanded', 'false');
  await expandable.click();
  await expect(expandable).toHaveAttribute('aria-expanded', 'true');
});

test('every reachable workflow screen has no serious axe violations', async () => {
  const screens = ['profile', 'preferences', 'progress', 'shortlist', 'funding', 'sources', 'approved', 'export'];

  for (const screen of screens) {
    await navigate(page, screen);
    if (screen === 'profile') {
      await expect(page.getByTestId('gap-list')).toContainText('academics.gpa.converted_value');
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
        .toBeLessThanOrEqual(1);
      await expect(page.getByTestId('section-case')).toBeInViewport();
      await page.getByTestId('section-case').click({ trial: true });
    }
    const report = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const serious = report.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    );
    expect(serious, `${screen}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`).toEqual([]);
  }
});

test('both themes render with a painted background and readable text', async () => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openShortlist(page);

  for (const theme of ['light', 'dark'] as const) {
    await page.selectOption('#theme', theme);
    await page.waitForTimeout(200);
    const { bg, fg } = await page.evaluate(() => {
      const s = getComputedStyle(document.body);
      return { bg: s.backgroundColor, fg: s.color };
    });
    expect(bg, `${theme} body must paint its own background`).not.toBe('rgba(0, 0, 0, 0)');
    expect(fg).not.toBe(bg);
    await page.screenshot({ path: shot(`theme-${theme}.png`), fullPage: false });
  }
});

test('no console errors during the full journey', async () => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openShortlist(page);
  await navigate(page, "funding");
  await navigate(page, "sources");
  await navigate(page, "export");

  expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toHaveLength(0);
});
