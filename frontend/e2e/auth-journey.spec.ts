/**
 * The workspace round trip, with authentication actually on.
 *
 * Every other spec runs against a backend where `auth_enabled` is false, so
 * `get_optional_principal` hands back the development principal and the
 * sign-in screen never appears. That left the whole registered-user path —
 * the one real deployments use — covered by unit tests only.
 *
 * Run with `npm run e2e:auth` (playwright.auth.config.ts). It must not run at
 * the same time as `npm run e2e`: both bind 5173 and 8099.
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { newSession, openShortlist, shot, waitForResults } from './helpers';

test.describe.configure({ mode: 'serial' });

const PASSWORD = 'correct-horse-battery-staple';
const SIGN_IN = 'Welcome back.';

// Unique per run: the database persists between runs, and a duplicate email
// is a 409. Playwright forbids Date.now() in no way, but the worker index and
// a timestamp together survive a re-run inside the same second.
const EMAIL = `e2e-${Date.now()}-${process.pid}@ashyq.invalid`;

let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
});

test.afterAll(async () => {
  await page.context().close();
});

// The public landing only shows to a visitor, so it is covered here.
test('the landing tells its story on scroll, and the way in opens sign-up', async ({ browser }) => {
  const visitor = await newSession(browser);
  await visitor.goto('/#/welcome');
  const story = visitor.getByTestId('landing-story');
  const scene = (name: string) => story.locator(`[data-ls="${name}"]`);
  const opacity = (name: string) => scene(name).evaluate((node) => Number(getComputedStyle(node).opacity));
  const scrollTo = (p: number) => visitor.evaluate((at) => {
    const track = document.querySelector<HTMLElement>('[data-testid="landing-story"]')!;
    window.scrollTo(0, track.getBoundingClientRect().top + window.scrollY + at * (track.offsetHeight - window.innerHeight));
  }, p);

  const axe = async (where: string) => {
    const report = await new AxeBuilder({ page: visitor }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    const serious = report.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    expect(serious, `${where}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`).toEqual([]);
  };

  await expect(visitor.getByRole('heading', { level: 1, name: 'Where can you study — and what will it cost?' })).toBeVisible();
  await expect.poll(() => opacity('s1')).toBeGreaterThan(0.95);
  await expect.poll(() => opacity('s6')).toBeLessThan(0.05);
  await axe('landing, top');

  // Halfway, the passes; their figures are an example and say so.
  await scrollTo(0.56);
  await expect.poll(() => opacity('s3')).toBeGreaterThan(0.95);
  await expect(scene('pass-nl')).toContainText('Example · demo data');

  // At the end: the three answers, the source and the way in; the question has gone.
  await scrollTo(1);
  await expect.poll(() => opacity('s6')).toBeGreaterThan(0.95);
  await expect.poll(() => opacity('s1')).toBeLessThan(0.05);
  await expect(scene('sheet')).toContainText('if the grant is awarded');
  await expect(scene('sheet')).toContainText('rug.nl · demo fixture · read Oct 05');
  await expect(story).not.toContainText(/%|chance|probab/i);
  await axe('landing, end of the story');
  await visitor.screenshot({ path: shot('landing-end.png') });

  await story.getByRole('link', { name: /Start with your profile/ }).click();
  await expect(visitor).toHaveURL(/#\/sign-in\?create=1/);
  await expect(visitor.getByRole('heading', { name: 'Start your journey.' })).toBeVisible();
  await visitor.context().close();
});

test('with reduced motion the landing stands still, the question and the way in both shown', async ({ browser }) => {
  const visitor = await newSession(browser);
  await visitor.emulateMedia({ reducedMotion: 'reduce' });
  await visitor.goto('/#/welcome');
  const story = visitor.getByTestId('landing-story');
  await expect(visitor.getByRole('heading', { level: 1, name: /Where can you study/ })).toBeVisible();
  // Nothing to scrub: the story is as tall as what it shows.
  const { track, stage } = await story.evaluate((node: HTMLElement) => ({
    track: node.offsetHeight,
    stage: node.querySelector<HTMLElement>('.ls__stage')!.offsetHeight,
  }));
  expect(track).toBe(stage);
  // On a desk the way in sits beside the opened pass, in the first screen.
  await expect(story.getByRole('link', { name: /Start with your profile/ })).toBeInViewport();
  for (const name of ['s1', 'pass-nl', 'sheet', 's6']) {
    await expect.poll(() => story.locator(`[data-ls="${name}"]`).evaluate((node) => Number(getComputedStyle(node).opacity))).toBe(1);
  }
  await visitor.context().close();
});

test('the sign-in screen stands in front of the app', async () => {
  await page.goto('/#/sign-in');
  // Also the interlock: if this run silently attached to an auth-disabled
  // backend, the app would render instead and every later assertion would
  // pass while proving nothing.
  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  await page.screenshot({ path: shot('auth-sign-in.png'), fullPage: true });
});

test('a new workspace can be registered', async () => {
  await page.getByTestId('auth-mode-toggle').click();
  await expect(page.getByRole('heading', { name: 'Start your journey.' })).toBeVisible();

  await page.getByTestId('auth-name').fill('E2E Applicant');
  await page.getByTestId('auth-organization').fill('E2E Workspace');
  await page.getByTestId('auth-email').fill(EMAIL);
  await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click();

  await expect(page.getByRole('heading', { name: /Where can you study/ })).toBeVisible();
  await page.getByTestId('home-cta').click();
  await expect(page.getByTestId('to-preferences')).toBeVisible();
});

test('the workspace can hold a profile and a finished run', async () => {
  await page.getByTestId('load-demo-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();
  await page.getByTestId('save-profile').click();

  await page.goto('/#/preferences');
  await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();
  await waitForResults(page);
});

test('signing out returns to the sign-in screen', async () => {
  // Signing out lives in the applicant's menu.
  await page.locator('.account > summary').click();
  await page.getByTestId('sign-out').click();
  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
});

test('signing in again finds the work still there', async () => {
  await page.getByTestId('auth-email').fill(EMAIL);
  await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click();

  // Asserted against the shortlist rather than the profile form: sign-out
  // clears the cookie but not localStorage, so a profile could reappear from
  // the browser alone. Results can only have come back from the server.
  await openShortlist(page);
  await expect(page.getByTestId('shortlist-table').locator('tbody tr').first()).toBeVisible();
  await page.screenshot({ path: shot('auth-after-second-sign-in.png'), fullPage: true });
});

test('a session that dies mid-use returns to sign-in, not an error banner', async () => {
  // The defect this pins: AuthGate asks /api/auth/status once, at mount, and
  // every later 401 was rendered by the store's `fail` as a topbar banner —
  // "Something went wrong. Authentication required." — on a screen the user
  // could no longer act on and could not leave.
  await page.context().clearCookies();

  // Saving, not navigating: the screen links are client-side route changes
  // that render from state already in memory, so they never reach the server
  // and never learn the session is gone. A write is the first thing the user
  // does that actually asks.
  await page.goto('/#/profile');
  await page.getByTestId('save-profile').click();

  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  await expect(page.getByText('Authentication required.')).toBeHidden();
});
