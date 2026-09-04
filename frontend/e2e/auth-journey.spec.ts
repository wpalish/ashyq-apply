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

import { expect, test, type Page } from '@playwright/test';
import { newSession, openShortlist, shot, waitForResults } from './helpers';

test.describe.configure({ mode: 'serial' });

const PASSWORD = 'correct-horse-battery-staple';
const SIGN_IN = 'Sign in to ASHYQ Apply';

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

test('the sign-in screen stands in front of the app', async () => {
  await page.goto('/');
  // Also the interlock: if this run silently attached to an auth-disabled
  // backend, the app would render instead and every later assertion would
  // pass while proving nothing.
  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  await page.screenshot({ path: shot('auth-sign-in.png'), fullPage: true });
});

test('a new workspace can be registered', async () => {
  await page.getByTestId('auth-mode-toggle').click();
  await expect(page.getByRole('heading', { name: 'Create your workspace' })).toBeVisible();

  await page.getByTestId('auth-name').fill('E2E Applicant');
  await page.getByTestId('auth-organization').fill('E2E Workspace');
  await page.getByTestId('auth-email').fill(EMAIL);
  await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click();

  await expect(page.getByTestId('to-preferences')).toBeVisible();
});

test('the workspace can hold a profile and a finished run', async () => {
  await page.getByTestId('load-demo-profile').click();
  const confirm = page.getByTestId('confirm-replace');
  if (await confirm.isVisible().catch(() => false)) await confirm.click();
  await page.getByTestId('save-profile').click();

  await page.getByTestId('to-preferences').click();
  await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();
  await waitForResults(page);
});

test('signing out returns to the sign-in screen', async () => {
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
  await page.getByTestId('nav-profile').click();
  await page.getByTestId('save-profile').click();

  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  await expect(page.getByText('Authentication required.')).toBeHidden();
});
