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

test('versioned short practice and its accepted feedback survive a fresh signed-in session', async ({ browser }) => {
  const packVersion = 'learning-pack-2026-10-11-v1';
  const first = await newSession(browser);
  let profileId = '';
  let savedAttemptId = '';
  let academics: unknown;
  let calendar: unknown;
  const signIn = async (session: Page) => {
    await session.goto('/#/sign-in');
    await session.getByTestId('auth-email').fill(EMAIL);
    await session.getByTestId('auth-password').fill(PASSWORD);
    await session.getByTestId('auth-submit').click();
    await expect(session.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  };
  try {
    await signIn(first);
    const response = await first.request.get(`/api/preparation/catalogue?catalogue_version=${packVersion}`);
    expect(response.ok()).toBeTruthy();
    const pack = await response.json();
    const completion = pack.lessons.find((lesson: { id: string }) => lesson.id === 'ielts-reading-completion-1');
    expect(completion.version).toBe(packVersion);
    await first.goto('/#/preparation');
    await first.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
    const opened = first.waitForResponse(item => item.request().method() === 'GET' && new URL(item.url()).pathname.endsWith('/preparation/lessons/ielts-reading-completion-1'));
    await first.getByRole('button', { name: `Start ${completion.title}`, exact: true }).click();
    const lesson = await opened; expect(lesson.ok()).toBeTruthy();
    profileId = new URL(lesson.url()).pathname.split('/')[3]!;
    const profile = await first.request.get(`/api/profiles/${profileId}`); expect(profile.ok()).toBeTruthy();
    academics = (await profile.json()).academics;
    const schedule = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`); expect(schedule.ok()).toBeTruthy();
    calendar = await schedule.json();
    for (const [index, answer] of ['dividers', '36', 'SHEET.', 'briefing', 'code'].entries()) {
      await first.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill(answer);
    }
    const saved = first.waitForResponse(item => item.request().method() === 'POST' && new URL(item.url()).pathname.endsWith('/preparation/attempts'));
    await first.getByRole('button', { name: 'Submit practice', exact: true }).click();
    const submitted = await saved; expect(submitted.ok()).toBeTruthy();
    const attempt = await submitted.json();
    expect(attempt).toMatchObject({ profile_id: profileId, version: packVersion, lesson_id: 'ielts-reading-completion-1', correct: 5, total: 5 });
    savedAttemptId = attempt.attempt_id;
    await expect(first.getByTestId('practice-result')).toHaveText('5 / 5 correct — practice only');
  } finally { await first.context().close(); }

  const second = await newSession(browser);
  try {
    await signIn(second);
    await second.goto('/#/preparation');
    await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
    await second.locator(`[data-testid="review-attempt"][data-attempt-id="${savedAttemptId}"]`).click();
    await expect(second.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', savedAttemptId);
    const review = second.getByRole('region', { name: 'Saved attempt review' });
    await expect(review.getByText('Your answer: SHEET.', { exact: true })).toBeVisible();
    await expect(review.getByTestId('feedback-item')).toHaveCount(5);
    const progress = await second.request.get(`/api/profiles/${profileId}/preparation/progress?catalogue_version=${packVersion}`);
    expect(progress.ok()).toBeTruthy();
    const history = await progress.json();
    expect(history.completed_lessons).toContainEqual({ lesson_id: 'ielts-reading-completion-1', version: packVersion });
    expect(history.attempts.some((attempt: { attempt_id: string }) => attempt.attempt_id === savedAttemptId)).toBe(true);
    const profile = await second.request.get(`/api/profiles/${profileId}`); expect((await profile.json()).academics).toEqual(academics);
    const schedule = await second.request.get(`/api/profiles/${profileId}/preparation/schedule`); expect(await schedule.json()).toEqual(calendar);
    await second.screenshot({ path: shot('auth-learning-path-second-session.png'), fullPage: true });
  } finally { await second.context().close(); }
});

/*
 * Proposal: append this test to frontend/e2e/auth-journey.spec.ts after its
 * existing tests. It uses that file's expect, test, Page, newSession and shot
 * imports, serial account EMAIL/PASSWORD, and the auth-enabled Playwright config.
 * It is intentionally not a standalone spec because playwright.auth.config.ts
 * matches only auth-journey.spec.ts. No route stubs or provider calls are used.
 */
test('opt-in dated material and own receipt persist through reload and a clean signed-in browser', async ({ browser }) => {
  test.setTimeout(180_000);
  const first = await newSession(browser);
  const signIn = async (session: Page) => {
    await session.goto('/#/sign-in');
    await session.getByTestId('auth-email').fill(EMAIL);
    await session.getByTestId('auth-password').fill(PASSWORD);
    await session.getByTestId('auth-submit').click();
    await expect(session.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  };
  const showSavedTask = async (session: Page, id: string) => {
    const row = session.locator(`li[data-learning-task="${id}"]`);
    await expect(row).toBeAttached();
    if (!(await row.isVisible())) {
      await session.locator('summary').filter({ hasText: 'Other dated tasks, including past dates' }).click();
    }
    await expect(row).toBeVisible();
    return row;
  };
  let profileId = '';
  let savedRevision = 0;
  let receiptUuid = '';
  let datedTaskId = '';
  let exactLessonId = '';
  let exactVersion = '';
  let originalSettings: import('../src/types').ScheduleSettings | null = null;
  let originalScores: unknown;
  try {
    await signIn(first);
    await first.goto('/#/preparation');
    const legacyLoaded = first.waitForResponse(reply => reply.request().method() === 'GET'
      && /\/preparation\/schedule$/.test(new URL(reply.url()).pathname));
    await first.getByRole('navigation', { name: 'Preparation views' })
      .getByRole('button', { name: 'Study plan', exact: true }).click();
    const legacyReply = await legacyLoaded;
    expect(legacyReply.ok()).toBeTruthy();
    profileId = new URL(legacyReply.url()).pathname.split('/')[3]!;

    // The earlier serial auth test saves this synthetic account's legacy plan.
    // Add a self-reported tick so the v2 path must preserve visible v1 history.
    const firstTick = first.getByRole('checkbox', { name: /^Completed:/ }).first();
    await expect(firstTick).toBeVisible();
    if (!(await firstTick.isChecked())) {
      const tickSaved = first.waitForResponse(reply => reply.request().method() === 'PUT'
        && /\/preparation\/schedule$/.test(new URL(reply.url()).pathname));
      await firstTick.click();
      expect((await tickSaved).ok()).toBeTruthy();
    }
    await expect(firstTick).toBeChecked();
    const before = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`);
    expect(before.ok()).toBeTruthy();
    const legacy = await before.json() as import('../src/types').StudyScheduleOut;
    originalSettings = legacy.settings;
    expect(originalSettings?.completed_task_ids.length).toBeGreaterThan(0);
    const profile = await first.request.get(`/api/profiles/${profileId}`);
    expect(profile.ok()).toBeTruthy(); originalScores = (await profile.json()).academics;

    const sidecarUrl = `/api/profiles/${profileId}/preparation/schedule/learning-path`;
    const emptyRead = await first.request.get(sidecarUrl);
    expect(emptyRead.ok()).toBeTruthy();
    expect((await emptyRead.json()).learning_path).toBeNull();
    await first.getByRole('button', { name: 'View learning calendar' }).click();
    await expect(first.getByRole('heading', { name: 'Learning calendar' })).toBeVisible();
    await expect(first.getByRole('button', { name: 'Use this updated path' })).toHaveCount(0);

    const previewed = first.waitForResponse(reply => reply.request().method() === 'POST'
      && /\/preparation\/schedule\/learning-path\/preview$/.test(new URL(reply.url()).pathname));
    await first.getByRole('button', { name: 'Preview updated learning path' }).click();
    const previewReply = await previewed;
    expect(previewReply.ok()).toBeTruthy();
    const preview = await previewReply.json() as import('../src/types').LearningPathOut;
    expect(preview.profile_id).toBe(profileId);
    expect(preview.revision).toBe(legacy.revision);
    expect(preview.learning_path?.legacy_settings).toEqual(originalSettings);
    const upcoming = preview.learning_path!.schedule.tasks
      .filter(task => task.due_on >= preview.learning_path!.schedule.as_of).slice(0, 14);
    const dated = upcoming.find(task => task.learning_ref?.kind === 'lesson' && task.availability === 'available');
    expect(dated).toBeDefined();
    const ref = dated?.learning_ref;
    if (!dated || !ref || ref.kind !== 'lesson') throw new Error('No visible exact dated lesson in preview');
    datedTaskId = dated.id; exactLessonId = ref.lesson_id; exactVersion = ref.content_version;
    expect(ref.id).toBe(`lesson:${exactLessonId}:${exactVersion}`);
    await expect(first.locator(`li[data-learning-task="${datedTaskId}"]`)).toContainText(dated.due_on);
    const stillEmpty = await first.request.get(sidecarUrl);
    expect((await stillEmpty.json()).learning_path).toBeNull();

    const saved = first.waitForResponse(reply => reply.request().method() === 'PUT'
      && /\/preparation\/schedule\/learning-path$/.test(new URL(reply.url()).pathname));
    await first.getByRole('button', { name: 'Use this updated path' }).click();
    const saveReply = await saved;
    expect(saveReply.ok()).toBeTruthy();
    const accepted = await saveReply.json() as import('../src/types').LearningPathOut;
    expect(accepted.profile_id).toBe(profileId);
    expect(accepted.revision).toBe(legacy.revision + 1);
    expect(accepted.learning_path?.draft.fingerprint).toBe(preview.learning_path?.draft.fingerprint);
    savedRevision = accepted.revision;
    const legacyAfterSave = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`);
    expect((await legacyAfterSave.json()).settings).toEqual(originalSettings);

    const row = await showSavedTask(first, datedTaskId);
    const lessonOpened = first.waitForResponse(reply => reply.request().method() === 'GET'
      && new URL(reply.url()).pathname.endsWith(`/preparation/lessons/${exactLessonId}`));
    await row.locator(`button[data-learning-ref="lesson:${exactLessonId}:${exactVersion}"]`).click();
    const lessonReply = await lessonOpened;
    expect(lessonReply.ok()).toBeTruthy();
    expect(new URL(lessonReply.url()).searchParams.get('version')).toBe(exactVersion);
    const lesson = await lessonReply.json() as import('../src/types').PreparationLesson;
    expect(lesson).toMatchObject({ id: exactLessonId, version: exactVersion });
    await expect(first.getByRole('heading', { name: lesson.title, exact: true })).toBeVisible();
    for (const [index, question] of lesson.questions.entries()) {
      if ('answer_format' in question) {
        await first.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill('sample');
      } else {
        await first.locator('.preparation-question').nth(index).getByRole('radio').first().check();
      }
    }
    const submitted = first.waitForResponse(reply => reply.request().method() === 'POST'
      && /\/preparation\/attempts$/.test(new URL(reply.url()).pathname));
    await first.getByRole('button', { name: 'Submit practice', exact: true }).click();
    const submitReply = await submitted;
    expect(submitReply.ok()).toBeTruthy();
    const attempt = await submitReply.json() as import('../src/types').StudyAttempt;
    expect(attempt).toMatchObject({ profile_id: profileId, lesson_id: exactLessonId, version: exactVersion });
    receiptUuid = attempt.attempt_id;
    await expect(first.getByTestId('practice-result')).toHaveAttribute('data-attempt-id', receiptUuid);

    await first.getByRole('navigation', { name: 'Preparation views' })
      .getByRole('button', { name: 'Study plan', exact: true }).click();
    await first.getByRole('button', { name: 'View learning calendar' }).click();
    const receiptRow = await showSavedTask(first, datedTaskId);
    await expect(receiptRow.getByText('Saved submission — not mastery')).toBeVisible();
    const reviewed = first.waitForResponse(reply => reply.request().method() === 'GET'
      && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${receiptUuid}/review`));
    await receiptRow.getByRole('button', { name: 'Review my saved attempt' }).click();
    const reviewReply = await reviewed;
    expect(reviewReply.ok()).toBeTruthy();
    const ownReview = await reviewReply.json() as import('../src/types').PreparationAttemptReview;
    expect(ownReview.attempt).toMatchObject({ profile_id: profileId, attempt_id: receiptUuid,
      lesson_id: exactLessonId, version: exactVersion });
    await expect(first.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', receiptUuid);

    await first.reload();
    await first.getByRole('navigation', { name: 'Preparation views' })
      .getByRole('button', { name: 'Study plan', exact: true }).click();
    await first.getByRole('button', { name: 'View learning calendar' }).click();
    await expect((await showSavedTask(first, datedTaskId))
      .getByRole('button', { name: 'Review my saved attempt' })).toBeVisible();
  } finally { await first.context().close(); }

  // newSession makes a new browser context without the first session's cookies
  // or localStorage. Signing in is required to recover this server-owned path.
  const second = await newSession(browser);
  try {
    await signIn(second);
    await second.goto('/#/preparation');
    await second.getByRole('navigation', { name: 'Preparation views' })
      .getByRole('button', { name: 'Study plan', exact: true }).click();
    await second.getByRole('button', { name: 'View learning calendar' }).click();
    const persisted = await second.request.get(`/api/profiles/${profileId}/preparation/schedule/learning-path`);
    expect(persisted.ok()).toBeTruthy();
    const path = await persisted.json() as import('../src/types').LearningPathOut;
    expect(path.profile_id).toBe(profileId);
    expect(path.revision).toBe(savedRevision);
    expect(path.learning_path?.legacy_settings).toEqual(originalSettings);
    expect(path.learning_path?.schedule.tasks.some(task => task.id === datedTaskId
      && task.submitted_attempt_id === receiptUuid)).toBe(true);
    const secondRow = await showSavedTask(second, datedTaskId);
    await expect(secondRow.getByRole('button', { name: 'Review my saved attempt' })).toBeVisible();
    for (const width of [320, 768, 1024, 1440]) {
      await second.setViewportSize({ width, height: 900 });
      await expect.poll(() => second.evaluate(() =>
        document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      await secondRow.scrollIntoViewIfNeeded();
      await second.screenshot({ path: shot(`auth-learning-calendar-second-session-${width}.png`), fullPage: false });
    }
    await secondRow.getByRole('button', { name: 'Review my saved attempt' }).click();
    await expect(second.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', receiptUuid);
    const legacyCheck = await second.request.get(`/api/profiles/${profileId}/preparation/schedule`);
    expect((await legacyCheck.json()).settings).toEqual(originalSettings);
    const profileCheck = await second.request.get(`/api/profiles/${profileId}`);
    expect((await profileCheck.json()).academics).toEqual(originalScores);
  } finally { await second.context().close(); }
});

// Append after the current final test in frontend/e2e/auth-journey.spec.ts.
// Existing imports provide expect, test, Page, newSession, openShortlist and EMAIL/PASSWORD.
test('own G1 comparison is explicit again in a clean signed-in browser and leaves saved learning intact', async ({ browser }) => {
  const signIn = async (session: Page) => {
    await session.goto('/#/sign-in');
    await session.getByTestId('auth-email').fill(EMAIL);
    await session.getByTestId('auth-password').fill(PASSWORD);
    await session.getByTestId('auth-submit').click();
    await expect(session.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  };
  const resultId = async (card: import('@playwright/test').Locator) => {
    const marker = await card.getAttribute('data-testid');
    expect(marker).toMatch(/^card-\S+$/);
    return marker!.slice(5);
  };
  const label = async (card: import('@playwright/test').Locator) => ({
    name: (await card.locator('h2').innerText()).trim(),
    programme: (await card.locator('.find-card__body > p').first().innerText()).trim(),
  });
  const select = async (session: Page, choice: { name: string; programme: string }) => {
    const control = session.getByRole('group', { name: 'Programmes to compare' }).locator('label')
      .filter({ hasText: `${choice.name} — ${choice.programme}` }).getByRole('checkbox');
    await expect(control).toHaveCount(1);
    await control.check();
  };
  const first = await newSession(browser);
  let profileId = '';
  let chosenIds: string[] = [];
  let chosenLabels: { name: string; programme: string }[] = [];
  let beforeSchedule: import('../src/types').StudyScheduleOut;
  let beforeSidecar: import('../src/types').LearningPathOut;
  let beforeProgress: import('../src/types').PreparationProgress;
  try {
    await signIn(first);
    await openShortlist(first);
    const cards = first.locator('.find-card');
    await expect(cards.nth(1)).toBeVisible();
    const firstCard = cards.nth(0);
    const firstLabel = await label(firstCard);
    let secondCard: import('@playwright/test').Locator | null = null;
    for (let index = 1; index < await cards.count(); index += 1) {
      const candidate = cards.nth(index);
      const choice = await label(candidate);
      if (choice.name !== firstLabel.name || choice.programme !== firstLabel.programme) {
        secondCard = candidate; break;
      }
    }
    if (!secondCard) throw new Error('Own research returned fewer than two distinct programme choices');
    chosenIds = [await resultId(firstCard), await resultId(secondCard)];
    chosenLabels = [firstLabel, await label(secondCard)];
    expect(new Set(chosenIds).size).toBe(2);
    for (const id of chosenIds) {
      const card = first.getByTestId(`card-${id}`);
      const save = card.getByRole('button', { name: 'Save', exact: true });
      if (await save.count()) {
        const decided = first.waitForResponse(reply => reply.request().method() === 'POST'
          && new URL(reply.url()).pathname.endsWith(`/results/${id}/decision`));
        await save.click();
        const decision = await decided;
        expect(decision.ok()).toBeTruthy();
        expect(['approved', 'maybe']).toContain((await decision.json()).user_decision);
      }
    }
    await first.goto('/#/preparation');
    await expect(first.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
    await select(first, chosenLabels[0]!); await select(first, chosenLabels[1]!);
    const graphRead = first.waitForResponse(reply => reply.request().method() === 'GET'
      && new URL(reply.url()).pathname.endsWith('/preparation/graph'));
    await first.getByRole('button', { name: 'View combined evidence' }).click();
    const reply = await graphRead;
    expect(reply.ok()).toBeTruthy();
    const url = new URL(reply.url());
    profileId = url.pathname.split('/')[3]!;
    expect(url.searchParams.getAll('result_id')).toEqual(chosenIds);
    const graph = await reply.json() as import('../src/types').PreparationGraph;
    expect(graph.profile_id).toBe(profileId);
    expect(graph.selection_source).toBe('server_verified_owned_explicit');
    expect(graph.requested_result_ids).toEqual(chosenIds);
    expect(graph.selected_result_ids).toEqual(chosenIds);
    expect(graph.programmes.map(item => item.result_id)).toEqual(chosenIds);
    expect(graph.source_manifest.map(item => item.result_id)).toEqual(chosenIds);
    for (const item of graph.programmes) {
      const card = first.getByRole('region', { name: `Programme evidence ${item.result_id}` });
      await expect(card).toBeVisible();
      if (!item.research_access) {
        await expect(card).toContainText('Research evidence is locked');
        await expect(card).not.toContainText(item.university ?? chosenLabels[chosenIds.indexOf(item.result_id)]!.name);
      }
    }
    const schedule = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`);
    const sidecar = await first.request.get(`/api/profiles/${profileId}/preparation/schedule/learning-path`);
    const progress = await first.request.get(`/api/profiles/${profileId}/preparation/progress`);
    expect(schedule.ok()).toBeTruthy(); expect(sidecar.ok()).toBeTruthy(); expect(progress.ok()).toBeTruthy();
    beforeSchedule = await schedule.json(); beforeSidecar = await sidecar.json(); beforeProgress = await progress.json();
    expect(beforeSidecar.learning_path).not.toBeNull();
    expect(beforeProgress.attempt_count).toBeGreaterThan(0);
  } finally { await first.context().close(); }

  // A new context has no first-browser local selection. Its own authenticated
  // server results and learning records must be read anew.
  const second = await newSession(browser);
  try {
    await signIn(second);
    let graphReads = 0;
    second.on('request', request => {
      if (request.method() === 'GET' && new URL(request.url()).pathname ===
        `/api/profiles/${profileId}/preparation/graph`) graphReads += 1;
    });
    await second.goto('/#/preparation');
    await expect(second.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
    await expect(second.getByRole('group', { name: 'Programmes to compare' })
      .getByRole('checkbox', { checked: true })).toHaveCount(0);
    await expect(second.getByRole('button', { name: 'View combined evidence' })).toBeDisabled();
    expect(graphReads).toBe(0);
    await select(second, chosenLabels[0]!); await select(second, chosenLabels[1]!);
    expect(graphReads).toBe(0);
    const graphRead = second.waitForResponse(reply => reply.request().method() === 'GET'
      && new URL(reply.url()).pathname === `/api/profiles/${profileId}/preparation/graph`);
    await second.getByRole('button', { name: 'View combined evidence' }).click();
    const reply = await graphRead;
    expect(reply.ok()).toBeTruthy();
    expect(graphReads).toBe(1);
    expect(new URL(reply.url()).searchParams.getAll('result_id')).toEqual(chosenIds);
    const graph = await reply.json() as import('../src/types').PreparationGraph;
    expect(graph.profile_id).toBe(profileId);
    expect(graph.requested_result_ids).toEqual(chosenIds);
    expect(graph.selected_result_ids).toEqual(chosenIds);
    expect(graph.programmes.map(item => item.result_id)).toEqual(chosenIds);
    expect(graph.source_manifest.map(item => item.result_id)).toEqual(chosenIds);
    for (const id of chosenIds) await expect(second.getByRole('region', { name: `Programme evidence ${id}` })).toBeVisible();
    await second.screenshot({ path: shot('auth-g1-own-graph-second-session.png'), fullPage: true });
    const schedule = await second.request.get(`/api/profiles/${profileId}/preparation/schedule`);
    const sidecar = await second.request.get(`/api/profiles/${profileId}/preparation/schedule/learning-path`);
    const progress = await second.request.get(`/api/profiles/${profileId}/preparation/progress`);
    expect(schedule.ok()).toBeTruthy(); expect(sidecar.ok()).toBeTruthy(); expect(progress.ok()).toBeTruthy();
    const afterSchedule = await schedule.json() as import('../src/types').StudyScheduleOut;
    const afterSidecar = await sidecar.json() as import('../src/types').LearningPathOut;
    const afterProgress = await progress.json() as import('../src/types').PreparationProgress;
    expect(afterSchedule.revision).toBe(beforeSchedule!.revision);
    expect(afterSchedule.settings).toEqual(beforeSchedule!.settings);
    expect(afterSidecar.revision).toBe(beforeSidecar!.revision);
    expect(afterSidecar.learning_path?.draft.fingerprint).toBe(beforeSidecar!.learning_path?.draft.fingerprint);
    expect(afterProgress.attempts.map(item => item.attempt_id)).toEqual(beforeProgress!.attempts.map(item => item.attempt_id));
  } finally { await second.context().close(); }
});
