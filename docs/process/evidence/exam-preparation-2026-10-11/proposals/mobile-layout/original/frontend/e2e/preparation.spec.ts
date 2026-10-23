/** Native synthetic API round trip: programme evidence, original practice and saved history. */
import { expect, test, type Page } from '@playwright/test';
import { newSession, runDemoResearch, shot } from './helpers';

test.describe.configure({ mode: 'serial' });
let page: Page;
let savedProfileId = '';
let savedAttemptId = '';
let officialScores: unknown;

test.beforeAll(async ({ browser }) => {
  page = await newSession(browser);
  await runDemoResearch(page);
});

test.afterAll(async () => { await page.context().close(); });

test('a programme saved from Find retains its exam evidence in Preparation', async () => {
  await page.goto('/#/shortlist');
  const delft = page.locator('.find-card').filter({ has: page.getByRole('heading', { name: 'Delft University of Technology', exact: true }) });
  await delft.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(delft.getByRole('button', { name: 'Saved', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByTestId('nav-preparation').click();
  await expect(page).toHaveURL(/#\/preparation$/);
  const programme = page.getByLabel('Programme evidence');
  const value = await programme.locator('option').filter({ hasText: 'Delft University of Technology' }).getAttribute('value');
  expect(value).toBeTruthy();
  await programme.selectOption(value!);
  await expect(page.getByText('IELTS writing', { exact: true })).toBeVisible();
  await expect(page.getByText('Development starter access', { exact: true })).toBeVisible();
  await page.screenshot({ path: shot('preparation-goals.png'), fullPage: true });
});

test('practice is submitted to the real API and keeps official scores separate', async () => {
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  const opened = page.waitForResponse(response => response.request().method() === 'GET' && /\/preparation\/lessons\/ielts-reading-1$/.test(new URL(response.url()).pathname));
  await page.getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true }).click();
  const lessonResponse = await opened;
  expect(lessonResponse.ok()).toBeTruthy();
  savedProfileId = new URL(lessonResponse.url()).pathname.split('/')[3]!;
  const initialProfile = await page.request.get(`/api/profiles/${savedProfileId}`);
  expect(initialProfile.ok()).toBeTruthy();
  officialScores = (await initialProfile.json()).academics;
  expect(officialScores).toMatchObject({ ielts: { overall: 7 } });
  const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
  await expect(submit).toBeDisabled();
  await page.getByRole('radio', { name: 'Visits increased during the trial.', exact: true }).check();
  await page.getByRole('radio', { name: 'The harvest comparison is not given.', exact: true }).check();
  await page.getByRole('radio', { name: 'Heavy rain.', exact: true }).check();
  await expect(submit).toBeEnabled();
  const persisted = page.waitForResponse(response => response.request().method() === 'POST' && /\/preparation\/attempts$/.test(new URL(response.url()).pathname));
  await submit.click();
  const response = await persisted;
  expect(response.ok()).toBeTruthy();
  const attempt = await response.json();
  expect(attempt.profile_id).toBe(savedProfileId); savedAttemptId = attempt.attempt_id;
  expect(attempt).toMatchObject({ lesson_id: 'ielts-reading-1', correct: 3, total: 3 });
  await expect(page.getByTestId('practice-result')).toHaveText('3 / 3 correct — practice only');
  await expect(page.getByTestId('practice-result')).toHaveAttribute('data-attempt-id', savedAttemptId);
  const profile = await page.request.get(`/api/profiles/${savedProfileId}`);
  expect(profile.ok()).toBeTruthy();
  expect((await profile.json()).academics).toEqual(officialScores);
  const duplicate = await page.request.post(`/api/profiles/${savedProfileId}/preparation/attempts`, { data: response.request().postDataJSON() });
  expect(duplicate.ok()).toBeTruthy();
  expect((await duplicate.json()).id).toBe(attempt.id);
  const current = await page.request.get(`/api/profiles/${savedProfileId}`);
  expect((await current.json()).academics).toEqual(officialScores);
  await page.screenshot({ path: shot('preparation-feedback.png'), fullPage: true });
});

test('one persisted attempt survives reload and is included in own export', async () => {
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByTestId('progress-summary')).toContainText('1');
  await expect(page.getByRole('heading', { name: 'Your saved practice', exact: true })).toBeVisible();
  const progress = await page.request.get(`/api/profiles/${savedProfileId}/preparation/progress`);
  expect(progress.ok()).toBeTruthy();
  const history = await progress.json();
  expect(history.attempt_count).toBe(1);
  expect(history.attempts[0].attempt_id).toBe(savedAttemptId);
  const exported = await page.request.get(`/api/profiles/${savedProfileId}/export`);
  expect(exported.ok()).toBeTruthy();
  expect((await exported.json()).study_attempts).toHaveLength(1);
  await page.screenshot({ path: shot('preparation-progress.png'), fullPage: true });
});
