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

/**
 * Let finite animations and transitions end before a check reads colours.
 *
 * Axe samples the page at one instant: a navigation pill fading out of its
 * open state is, for a frame, grey text on grey, and CI once caught exactly
 * that frame. Infinite ones (the globe's pulse) never finish, so they are
 * left alone.
 */
export async function settle(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations()
    .filter((a) => a.effect?.getComputedTiming().iterations !== Infinity)
    .map((a) => a.finished.catch(() => undefined))));
}

/** The five areas the shell keeps in its main navigation (Unimatch's). */
const PRIMARY = new Set(['home', 'shortlist', 'approved', 'documents', 'feed']);

/**
 * Open a screen: a main area through its navigation button, the rest through
 * its address, the way the shell's Explore menu and links reach them.
 */
export async function goTo(page: Page, screen: string): Promise<void> {
  const item = page.getByTestId(`nav-${screen}`);
  if (PRIMARY.has(screen) && (await item.isVisible().catch(() => false))) {
    await item.click();
    return;
  }
  await page.evaluate((id) => { window.location.hash = `#/${id}`; }, screen);
}

/** The demo applicant's profile, then a research run from the preferences. */
export async function runDemoResearch(page: Page): Promise<void> {
  await page.goto('/#/profile');
  await page.getByTestId('load-demo-profile').click();
  await page.goto('/#/preferences');
  await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();
  await waitForResults(page);
}

export async function openShortlist(page: Page): Promise<void> {
  await goTo(page, 'shortlist');
  // Cards are the default view; the journeys assert on the table's rows, so
  // they choose it the way a person would, with the view switch.
  const table = page.getByTestId('view-table');
  if ((await table.getAttribute('aria-pressed')) !== 'true') await table.click();
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
