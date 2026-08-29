import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Where screenshots go.
 *
 * Not `docs/screenshots` by default, on purpose. Every E2E run rewrote all
 * forty tracked PNGs, and they are not byte-reproducible: two runs of
 * unchanged code differ by a pixel or two of text antialiasing in headless
 * Chromium. Cropping the differing bands and looking at them side by side
 * shows no visible change at all.
 *
 * Forty binaries appearing in `git status` after every test run is noise that
 * hides the one screenshot that changed for a real reason, and it is how
 * unreviewed binaries get committed — which already happened once here.
 *
 * So a normal run writes to an ignored directory, and refreshing the
 * documentation is a deliberate act: `npm run screenshots`.
 */
const SHOT_ROOT = process.env.ASHYQ_SHOT_DIR ?? 'test-results/screenshots';

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
 * CSS applied while a documentation screenshot is taken.
 *
 * A run id and a generation timestamp are different on every run, and they are
 * rendered on nearly every screen. The result was forty tracked PNGs differing
 * after every suite — noise that buries the one screenshot that changed for a
 * real reason, and forty binaries in `git status` that somebody eventually
 * commits without looking.
 *
 * The values stay on screen; they are held still. Anything marked volatile
 * keeps its box, so nothing reflows, and renders a fixed placeholder instead
 * of the value.
 */
const STEADY = `
  [data-volatile] { color: transparent !important; position: relative; }
  [data-volatile]::after {
    content: attr(data-volatile);
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink-faint, #666);
  }
`;

/**
 * Screenshot for the docs, with volatile values held still.
 *
 * Use this rather than `page.screenshot` for anything written under
 * docs/screenshots, so a rerun with no code change leaves the tree clean.
 */
export async function docShot(
  page: Page, name: string, options: { fullPage?: boolean } = {},
): Promise<void> {
  await page.screenshot({
    path: shot(name),
    fullPage: options.fullPage ?? true,
    style: STEADY,
  });
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

export async function runDemoResearch(page: Page): Promise<void> {
  await page.goto('/');
  await page.getByTestId('to-preferences').click();
  await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();
  await waitForResults(page);
}

export async function openShortlist(page: Page): Promise<void> {
  await page.getByTestId('nav-shortlist').click();
  await expect(page.getByTestId('shortlist-table')).toBeVisible();
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
  return row;
}
