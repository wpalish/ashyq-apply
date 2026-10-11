/** Actual synthetic API: opt-in content, short answers and preserved calendar/score data. */
import { expect, test, type Page } from '@playwright/test';
import { newSession, runDemoResearch, shot } from './helpers';
import type { PreparationCatalogue, StudyAttempt } from '../src/types';

const PACK_VERSION = 'learning-pack-2026-10-11-v1';
let page: Page;

test.describe.configure({ mode: 'serial' });
test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
  await runDemoResearch(page);
});
test.afterAll(async () => { await page.context().close(); });

test('the ordered unit saves short answers, reviews mistakes and opens the exact next version', async () => {
  const catalogue = await page.request.get(`/api/preparation/catalogue?catalogue_version=${PACK_VERSION}`);
  expect(catalogue.ok()).toBeTruthy();
  const pack = await catalogue.json() as PreparationCatalogue;
  expect(pack.version).toBe(PACK_VERSION);
  expect(pack.lessons).toHaveLength(9);
  expect(pack.lessons.reduce((sum, lesson) => sum + lesson.question_count, 0)).toBe(39);
  expect(pack.tracks.find(track => track.id === 'ielts_reading')?.lesson_ids).toEqual([
    'ielts-reading-1', 'ielts-reading-headings-1', 'ielts-reading-completion-1', 'ielts-reading-features-1',
  ]);
  const legacy = await page.request.get('/api/preparation/catalogue');
  expect(legacy.ok()).toBeTruthy(); expect((await legacy.json()).lessons).toHaveLength(3);

  await page.goto('/#/preparation');
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  const completion = pack.lessons.find(lesson => lesson.id === 'ielts-reading-completion-1')!;
  const opened = page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname.endsWith('/preparation/lessons/ielts-reading-completion-1'));
  await page.getByRole('button', { name: `Start ${completion.title}`, exact: true }).click();
  const lessonResponse = await opened;
  expect(lessonResponse.ok()).toBeTruthy();
  expect(new URL(lessonResponse.url()).searchParams.get('version')).toBe(PACK_VERSION);
  const profileId = new URL(lessonResponse.url()).pathname.split('/')[3]!;
  const publicLesson = await lessonResponse.json();
  expect(publicLesson.version).toBe(PACK_VERSION);
  expect(publicLesson.questions).toHaveLength(5);
  expect(JSON.stringify(publicLesson)).not.toContain('accepted_answers');
  expect(JSON.stringify(publicLesson)).not.toContain('correct_choice_id');
  const profileBefore = await page.request.get(`/api/profiles/${profileId}`);
  expect(profileBefore.ok()).toBeTruthy(); const academics = (await profileBefore.json()).academics;
  const scheduleBefore = await page.request.get(`/api/profiles/${profileId}/preparation/schedule`);
  expect(scheduleBefore.ok()).toBeTruthy(); const calendar = await scheduleBefore.json();

  const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
  await expect(submit).toBeDisabled();
  for (const [index, answer] of ['dividers', '36', 'sheet', 'briefing', 'memory stick'].entries()) {
    await page.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill(answer);
  }
  const accepted = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith('/preparation/attempts'));
  await submit.click();
  const receipt = await accepted; expect(receipt.ok()).toBeTruthy();
  const attempt = await receipt.json() as StudyAttempt;
  expect(attempt).toMatchObject({ profile_id: profileId, lesson_id: completion.id, version: PACK_VERSION, correct: 4, total: 5 });
  await expect(page.getByTestId('practice-result')).toHaveText('4 / 5 correct — practice only');
  await expect(page.getByTestId('feedback-item').first()).toHaveAttribute('data-correct', 'false');
  await expect(page.getByText('Your answer: memory stick', { exact: true })).toBeVisible();
  const replay = await page.request.post(`/api/profiles/${profileId}/preparation/attempts`, { data: receipt.request().postDataJSON() });
  expect(replay.ok()).toBeTruthy(); expect((await replay.json()).id).toBe(attempt.id);

  const next = page.getByTestId('next-lesson');
  await expect(next).toHaveAttribute('data-lesson-id', 'ielts-reading-features-1');
  await expect(next).toHaveAttribute('data-version', PACK_VERSION);
  await next.click();
  const features = pack.lessons.find(lesson => lesson.id === 'ielts-reading-features-1')!;
  await expect(page.getByRole('heading', { name: features.title, exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  await page.locator(`[data-testid="review-attempt"][data-attempt-id="${attempt.attempt_id}"]`).click();
  const review = page.getByRole('region', { name: 'Saved attempt review' });
  await expect(page.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', attempt.attempt_id);
  await expect(review.getByText('Your answer: memory stick', { exact: true })).toBeVisible();
  await expect(review.getByTestId('feedback-item').first()).toHaveAttribute('data-correct', 'false');
  const profileAfter = await page.request.get(`/api/profiles/${profileId}`);
  expect((await profileAfter.json()).academics).toEqual(academics);
  const scheduleAfter = await page.request.get(`/api/profiles/${profileId}/preparation/schedule`);
  expect(await scheduleAfter.json()).toEqual(calendar);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 850 });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.getByTestId('saved-attempt-review').scrollIntoViewIfNeeded();
    await page.screenshot({ path: shot(`learning-path-review-${width}.png`), fullPage: false });
  }
});
