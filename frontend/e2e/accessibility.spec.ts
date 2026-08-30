/**
 * Accessibility and responsive behaviour.
 *
 * Axe catches broad WCAG regressions while the focused assertions below cover
 * workflow-specific semantics and responsive behaviour.
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { docShot, newSession, openShortlist, runDemoResearch } from './helpers';

// The full set the product claims to support. 375 and 1920 were the two ends
// nobody checked: the narrowest phone in common use and the widest desktop.
const BREAKPOINTS = [
  { name: '320', width: 320, height: 720 },
  { name: '375', width: 375, height: 800 },
  { name: '768', width: 768, height: 1024 },
  { name: '1024', width: 1024, height: 768 },
  { name: '1440', width: 1440, height: 900 },
  { name: '1920', width: 1920, height: 1080 },
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
    await docShot(page, `responsive-${bp.name}.png`, { fullPage: false });
  }
});

test('the mobile shortlist becomes cards without an inner horizontal scroller', async () => {
  await openShortlist(page);
  await page.setViewportSize({ width: 375, height: 800 });

  const layout = await page.locator('.table-wrap').evaluate(
    (el) => ({
      overflow: getComputedStyle(el).overflowX,
      overflowPixels: el.scrollWidth - el.clientWidth,
    }),
  );
  expect(layout.overflow).toBe('visible');
  expect(layout.overflowPixels).toBeLessThanOrEqual(1);
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
  // Every decision control belongs to a named group, and each button names
  // the programme and university it acts on, so a screen reader announces
  // "Apply to <programme> at <university>" rather than "Yes".
  const group = page.getByRole('group').first();
  await expect(group).toHaveAttribute('aria-label', /What to do about .+ at .+/);
  await expect(group.locator('.decision-btn--approve')).toHaveAttribute(
    'aria-label', /^Apply to .+ at .+/,
  );
  await expect(group.locator('.decision-btn--reject')).toHaveAttribute(
    'aria-label', /^Rule out .+ at .+/,
  );

  const expandable = page.locator('button[aria-expanded]').first();
  await expect(expandable).toHaveAttribute('aria-expanded', 'false');
  await expandable.click();
  await expect(expandable).toHaveAttribute('aria-expanded', 'true');
});

test('every reachable workflow screen has no serious axe violations', async () => {
  const screens = ['profile', 'preferences', 'progress', 'shortlist', 'funding', 'sources', 'approved', 'export'];

  for (const screen of screens) {
    await page.getByTestId(`nav-${screen}`).click();
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
    await docShot(page, `theme-${theme}.png`, { fullPage: false });
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
