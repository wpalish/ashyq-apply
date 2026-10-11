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

/** Measured actual DOM geometry; no API mocks or synthetic layout overrides. */
async function mobileNavigationGeometry() {
  return page.evaluate(() => {
    const sidebar = document.querySelector<HTMLElement>('.sidebar')!;
    const nav = sidebar.querySelector<HTMLElement>('nav[aria-label="Main navigation"]')!;
    const main = document.querySelector<HTMLElement>('.main')!;
    const rectangle = (element: Element) => {
      const value = element.getBoundingClientRect();
      return { left: value.left, right: value.right, top: value.top, bottom: value.bottom, width: value.width, height: value.height };
    };
    const items = Array.from(nav.querySelectorAll<HTMLButtonElement>('button')).map(button => {
      const label = button.querySelector<HTMLElement>('.nav__label--compact') ?? button.querySelector<HTMLElement>('span')!;
      const style = getComputedStyle(label);
      return { accessibleName: button.getAttribute('aria-label'), box: rectangle(button),
        label: { text: label.textContent?.trim(), box: rectangle(label), fontSize: parseFloat(style.fontSize),
          lineHeight: parseFloat(style.lineHeight), scrollWidth: label.scrollWidth, clientWidth: label.clientWidth } };
    });
    const rows: number[] = [];
    for (const item of items) if (!rows.some(top => Math.abs(top - item.box.top) < 2)) rows.push(item.box.top);
    const style = getComputedStyle(sidebar);
    return { viewport: document.documentElement.clientWidth, rootFontSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
      sidebar: rectangle(sidebar), sidebarPosition: style.position,
      paddingTop: parseFloat(style.paddingTop), paddingBottom: parseFloat(style.paddingBottom),
      borderTop: parseFloat(style.borderTopWidth), nav: rectangle(nav), rowCount: rows.length,
      columnCount: getComputedStyle(nav).gridTemplateColumns.split(' ').length,
      mainBottomReserve: parseFloat(getComputedStyle(main).paddingBottom), items };
  });
}

test('six mobile destinations stay readable in one row with a matching safe bottom reserve', async () => {
  const originalViewport = page.viewportSize();
  try {
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 800 });
      const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
      await expect(nav.getByRole('button')).toHaveCount(6);
      await expect(nav.getByRole('button', { name: 'Exam preparation', exact: true })).toBeVisible();
      await expect.poll(async () => (await mobileNavigationGeometry()).rowCount).toBe(1);
      const measured = await mobileNavigationGeometry();
      expect(measured.viewport).toBe(width);
      expect(measured.sidebarPosition).toBe('fixed');
      expect(measured.columnCount).toBe(6);
      expect(measured.sidebar.left).toBeGreaterThanOrEqual(0);
      expect(measured.sidebar.right).toBeLessThanOrEqual(width + 1);
      expect(measured.items.map(item => item.label.text)).toEqual(['Home', 'Find', 'Plan', 'Prepare', 'Docs', 'People']);
      expect(measured.items.map(item => item.accessibleName)).toEqual(['Home', 'Find', 'Plan', 'Exam preparation', 'Documents', 'Community']);
      for (const item of measured.items) {
        expect(item.box.width).toBeGreaterThanOrEqual(44);
        expect(item.box.height).toBeGreaterThanOrEqual(44);
        expect(item.box.left).toBeGreaterThanOrEqual(measured.nav.left - 1);
        expect(item.box.right).toBeLessThanOrEqual(measured.nav.right + 1);
        expect(item.label.fontSize).toBeGreaterThanOrEqual(12);
        expect(item.label.box.left).toBeGreaterThanOrEqual(item.box.left - 1);
        expect(item.label.box.right).toBeLessThanOrEqual(item.box.right + 1);
        expect(item.label.scrollWidth).toBeLessThanOrEqual(item.label.clientWidth + 1);
        expect(item.label.box.height).toBeLessThanOrEqual(item.label.lineHeight + 1);
      }
      expect(measured.paddingBottom).toBeGreaterThanOrEqual(measured.paddingTop);
      expect(measured.sidebar.height).toBeLessThanOrEqual(measured.items[0]!.box.height + measured.paddingTop + measured.paddingBottom + measured.borderTop + 1);
      expect(measured.mainBottomReserve).toBeGreaterThanOrEqual(measured.sidebar.height + measured.rootFontSize * 0.75 - 1);
      await test.info().attach(`mobile-navigation-${width}.json`, { body: JSON.stringify(measured, null, 2), contentType: 'application/json' });
    }
  } finally { if (originalViewport) await page.setViewportSize(originalViewport); }
});

test('the final real practice actions scroll above the fixed navigation at 390 and 320', async () => {
  const originalViewport = page.viewportSize();
  try {
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
      const opened = page.waitForResponse(response => response.request().method() === 'GET' && /\/preparation\/lessons\/ielts-reading-1$/.test(new URL(response.url()).pathname));
      await page.getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true }).click();
      expect((await opened).ok()).toBeTruthy();
      await page.getByRole('radio', { name: 'Visits increased during the trial.', exact: true }).check();
      await page.getByRole('radio', { name: 'The harvest comparison is not given.', exact: true }).check();
      await page.getByRole('radio', { name: 'Heavy rain.', exact: true }).check();
      const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
      const lastAction = page.getByRole('button', { name: 'Restart lesson with a new attempt', exact: true });
      await expect(submit).toBeEnabled(); await expect(lastAction).toBeEnabled();
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      const action = await lastAction.evaluate(element => {
        const rect = element.getBoundingClientRect();
        const bar = document.querySelector<HTMLElement>('.sidebar')!.getBoundingClientRect();
        return { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right, height: rect.height,
          sidebarTop: bar.top, viewportWidth: document.documentElement.clientWidth,
          reached: document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.closest('button') === element };
      });
      expect(action.viewportWidth).toBe(width);
      expect(action.top).toBeGreaterThanOrEqual(0);
      expect(action.bottom).toBeLessThanOrEqual(action.sidebarTop - 8);
      expect(action.left).toBeGreaterThanOrEqual(0);
      expect(action.right).toBeLessThanOrEqual(width + 1);
      expect(action.height).toBeGreaterThanOrEqual(44);
      expect(action.reached).toBe(true);
      const submitBox = await submit.boundingBox(); expect(submitBox).not.toBeNull();
      expect(submitBox!.y + submitBox!.height).toBeLessThanOrEqual(action.sidebarTop - 8);
      await test.info().attach(`mobile-practice-final-action-${width}.json`, { body: JSON.stringify({ action, submit: submitBox }, null, 2), contentType: 'application/json' });
      await page.screenshot({ path: shot(`preparation-mobile-final-action-${width}.png`), fullPage: true });
    }
  } finally { if (originalViewport) await page.setViewportSize(originalViewport); }
});
