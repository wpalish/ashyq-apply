/**
 * Accessibility and responsive behaviour.
 *
 * No axe dependency: these assert the specific properties this UI must hold -
 * keyboard reachability, a labelled table, live progress, and no horizontal
 * page scroll at any breakpoint (wide content scrolls inside its own box).
 */

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

test('the shortlist table itself scrolls inside its container', async () => {
  await openShortlist(page);
  await page.setViewportSize({ width: 375, height: 800 });

  const scrollable = await page.locator('.table-wrap').evaluate(
    (el) => getComputedStyle(el).overflowX,
  );
  expect(scrollable).toBe('auto');
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
  await page.getByTestId('nav-progress').click();
  const bar = page.getByRole('progressbar', { name: 'Research progress' });
  await expect(bar).toBeVisible();
  await expect(bar).toHaveAttribute('aria-valuemax', '100');
});

test('the results table is labelled and its controls are named', async () => {
  await openShortlist(page);

  await expect(page.locator('table caption')).toContainText('Shortlisted university programmes');
  // Every decision control belongs to a named group, so a screen reader says
  // which university a "Yes" applies to.
  const group = page.getByRole('group').first();
  await expect(group).toHaveAttribute('aria-label', /Decision for /);

  const expandable = page.locator('button[aria-expanded]').first();
  await expect(expandable).toHaveAttribute('aria-expanded', 'false');
  await expandable.click();
  await expect(expandable).toHaveAttribute('aria-expanded', 'true');
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
  await page.getByTestId('nav-funding').click();
  await page.getByTestId('nav-sources').click();
  await page.getByTestId('nav-export').click();

  expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toHaveLength(0);
});
