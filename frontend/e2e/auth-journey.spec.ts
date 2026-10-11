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

  await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  await page.getByRole('button', { name: 'Create profile' }).click();
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

test('original practice persists into a second signed-in browser session', async ({ browser }) => {
  await page.goto('/#/preparation');
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  await page.getByRole('button', { name: 'Start Math: linear relations and proportional reasoning', exact: true }).click();
  for (const [index, value] of ['4', '20', '30'].entries()) await page.locator('fieldset').nth(index).getByRole('radio', { name: value, exact: true }).check();
  const receipt = page.waitForResponse(response => response.request().method() === 'POST' && /\/preparation\/attempts$/.test(new URL(response.url()).pathname));
  await page.getByRole('button', { name: 'Submit practice', exact: true }).click();
  const submitted = await receipt;
  expect(submitted.ok()).toBeTruthy();
  const attempt = await submitted.json();
  expect(attempt).toMatchObject({ lesson_id: 'sat-math-1', correct: 3, total: 3 });
  await expect(page.getByTestId('practice-result')).toHaveText('3 / 3 correct — practice only');

  const dateAfter = (days: number) => { const date = new Date(); date.setUTCDate(date.getUTCDate() + days); return date.toISOString().slice(0, 10); };
  const calendar = await page.request.put(`/api/profiles/${attempt.profile_id}/preparation/schedule`, { data: {
    expected_revision: 0, settings: { exam: 'digital_sat', starts_on: dateAfter(0), certificate_deadline: dateAfter(90),
      first_exam_on: dateAfter(60), retake_on: null, result_wait_days: 14, delivery_days: 7, safety_days: 7,
      timezone: 'UTC', weekly_minutes: 180, study_days: [0, 2, 4], target_scores: { total: 1400, math: 700, reading_writing: 700 },
      baseline_scores: {}, baseline_on: null, confirmed_planning_dates: true, completed_task_ids: [] },
  } });
  expect(calendar.status()).toBe(200);
  const savedCalendar = await calendar.json(); expect(savedCalendar.revision).toBe(1);

  // Fresh cookies/localStorage: a second session cannot recover an attempt from the first tab.
  const second = await newSession(browser);
  try {
    await second.goto('/#/sign-in');
    await second.getByTestId('auth-email').fill(EMAIL);
    await second.getByTestId('auth-password').fill(PASSWORD);
    await second.getByTestId('auth-submit').click();
    await expect(second.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
    await second.goto('/#/preparation');
    await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
    await expect(second.getByTestId('progress-summary')).toContainText('1 saved attempts');
    const stored = await second.request.get(`/api/profiles/${attempt.profile_id}/preparation/progress`);
    expect(stored.ok()).toBeTruthy();
    expect((await stored.json()).attempts[0].attempt_id).toBe(attempt.attempt_id);
    await second.screenshot({ path: shot('auth-preparation-second-session.png'), fullPage: true });
    await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
    await expect(second.getByLabel('Total target', { exact: true })).toHaveValue('1400');
    const restored = await second.request.get(`/api/profiles/${attempt.profile_id}/preparation/schedule`);
    expect(restored.ok()).toBeTruthy(); expect((await restored.json()).settings).toEqual(savedCalendar.settings);
    await expect(second.getByText('Readiness: not assessed.', { exact: true })).toBeVisible();
    await second.getByRole('heading', { name: 'Saved dated tasks', exact: true }).scrollIntoViewIfNeeded();
    await second.screenshot({ path: shot('auth-study-schedule-second-session.png'), fullPage: false });

  } finally {
    await second.context().close();
  }
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
  await page.goto('/#/profile');
  await page.getByTestId('save-profile').click();

  await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  await expect(page.getByText('Authentication required.')).toBeHidden();
});
