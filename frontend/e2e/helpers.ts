import { expect, test, type Browser, type Page } from '@playwright/test';

const SHOT_ROOT = '../docs/screenshots';

/**
 * Screenshot path for the current project.
 *
 * Both projects run the same specs, so without namespacing the mobile run
 * silently overwrites the desktop captures with narrow-layout versions.
 */
export function shot(name: string): string {
  const project = test.info().project.name;
  return project === 'desktop-chromium'
    ? `${SHOT_ROOT}/${name}`
    : `${SHOT_ROOT}/mobile/${name}`;
}

/**
 * One browser page shared across a spec file.
 *
 * The research pipeline is the slow part, and re-running it per test would
 * turn a 30-second suite into a 10-minute one while testing nothing extra.
 * Sharing a page also mirrors how the product is actually used: one session
 * that walks the workflow from profile to export.
 */
export async function newSession(browser: Browser): Promise<Page> {
  // browser.newContext() ignores the project's `use` block, so the viewport and
  // device settings have to be carried across explicitly - otherwise the
  // desktop project silently renders at the default 1280x720 and the mobile
  // project loses its device emulation entirely.
  const { viewport, userAgent, deviceScaleFactor, isMobile, hasTouch } = test.info().project.use;
  const context = await browser.newContext({
    ...(viewport !== undefined ? { viewport } : {}),
    ...(userAgent ? { userAgent } : {}),
    ...(deviceScaleFactor ? { deviceScaleFactor } : {}),
    ...(isMobile !== undefined ? { isMobile } : {}),
    ...(hasTouch !== undefined ? { hasTouch } : {}),
  });
  return context.newPage();
}

export async function waitForResults(page: Page, timeout = 120_000): Promise<void> {
  await expect(page.getByTestId('stage-list')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId('to-shortlist')).toBeVisible({ timeout });
}

/** Which tab holds each screen: the «Горизонт» navigation, as App.tsx has it. */
const TAB_OF: Record<string, string> = {
  start: 'match', progress: 'match', shortlist: 'match', funding: 'match', sources: 'match',
  approved: 'plan',
  documents: 'documents',
  feed: 'people', discover: 'people', messages: 'people',
  profile: 'me', preferences: 'me', me: 'me', export: 'me', moderation: 'me', legal: 'me',
};
/** Tabs with one screen have no sub-navigation: the tab is the screen. */
const SINGLE = new Set(['approved', 'documents']);

/**
 * Open a screen the way a person would: its tab, then its sub-navigation item.
 *
 * Every screen used to sit in one sidebar, one click away from anywhere. Under
 * five tabs a screen in another tab is two clicks away, and a test that clicks
 * `nav-*` directly only works from inside the same tab.
 */
export async function goTo(page: Page, screen: string): Promise<void> {
  const item = page.getByTestId(`nav-${screen}`);
  if (!SINGLE.has(screen) && (await item.isVisible().catch(() => false))) {
    await item.click();
    return;
  }
  await page.getByTestId(`navtab-${TAB_OF[screen]}`).click();
  if (SINGLE.has(screen)) return;
  await page.getByTestId(`nav-${screen}`).click();
}

/** The three-field search on the start screen, with the demo applicant's values. */
export async function runDemoResearch(page: Page): Promise<void> {
  await page.goto('/');
  await expect(page.getByTestId('start-search')).toBeEnabled();
  await page.getByTestId('start-search').click();
  await waitForResults(page);
}

export async function openShortlist(page: Page): Promise<void> {
  await goTo(page, 'shortlist');
  await expect(page.getByTestId('shortlist-table')).toBeVisible();

  // Out-of-budget, needs-clarification and excluded rows sit in sections that
  // are collapsed by design - the ranked table is the answer to "where can I
  // go", not "what exists". The journey asserts on rows from all of them, so
  // it opens every section rather than each test remembering to.
  const sections = page.locator('details[data-testid^="section-"]');
  for (let i = 0; i < (await sections.count()); i += 1) {
    const section = sections.nth(i);
    if (!(await section.evaluate((el: HTMLDetailsElement) => el.open))) {
      await section.locator('summary').click();
    }
  }
}

/** The shortlist row whose university cell carries `name`. */
export function rowFor(page: Page, name: string) {
  return page
    .locator('tbody tr')
    .filter({ has: page.getByRole('button', { name, exact: true }) })
    .first();
}

export async function expandRow(page: Page, name: string) {
  const row = rowFor(page, name);
  await expect(row).toBeVisible();
  await row.getByRole('button', { name, exact: true }).click();
  // Bring the opened programme to the top, as a person scrolls to read it. On
  // a phone the tab bar is fixed along the bottom edge, and Playwright counts
  // a control under it as "in view" - then waits forever to click it.
  await row.evaluate((element) => element.scrollIntoView({ block: 'start' }));
  return row;
}
