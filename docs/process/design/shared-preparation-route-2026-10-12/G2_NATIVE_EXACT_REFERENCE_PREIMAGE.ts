/** Native synthetic API round trip: programme evidence, original practice and saved history. */
import { expect, test, type Page } from '@playwright/test';
import { newSession, runDemoResearch, shot } from './helpers';
import type { StudyScheduleOut } from '../src/types';

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
      // Respect native smooth scrolling; observe the real geometry before measuring it.
      await expect.poll(async () => lastAction.evaluate(element => {
        const rect = element.getBoundingClientRect();
        const bar = document.querySelector<HTMLElement>('.sidebar')!.getBoundingClientRect();
        return rect.top >= 0 && rect.bottom <= bar.top - 8
          && document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.closest('button') === element;
      })).toBe(true);
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

/** Keep catalogue links readable without expanding the mobile layout viewport. */
test('personal practice stays inside the requested viewport and all starter lessons open by normal clicks', async () => {
  const originalViewport = page.viewportSize();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Goals & evidence', exact: true }).click();
  const evidence = page.locator('.preparation-evidence').filter({ has: page.locator('.preparation-evidence__claim') }).first();
  const summary = evidence.locator(':scope > summary');
  await expect(summary).toBeVisible();
  await expect(evidence).not.toHaveAttribute('open');
  const quote = evidence.locator('.preparation-evidence__claim p').first();
  await expect(quote).toBeHidden();
  await summary.click();
  await expect(evidence).toHaveAttribute('open', '');
  await expect(quote).toBeVisible();
  await expect(evidence.locator('a[href], code').first()).toBeVisible();
  await expect(evidence.getByText(/Recorded source scope:/).first()).toBeVisible();
  await summary.click();
  await expect(quote).toBeHidden();
  const response = await page.request.get('/api/preparation/catalogue');
  expect(response.ok()).toBeTruthy();
  const catalogue = await response.json() as {
    exams: { official_info_urls: string[]; official_practice_urls: string[] }[];
    lessons: { id: string; title: string }[];
  };
  const expectedURLs = catalogue.exams.flatMap(exam => [...exam.official_info_urls, ...exam.official_practice_urls]);
  const starters = catalogue.lessons.filter(lesson => ['ielts-reading-1', 'sat-math-1', 'sat-rw-1'].includes(lesson.id));
  expect(starters).toHaveLength(3);
  const practice = page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true });
  try {
    for (const width of [320, 390]) {
      await page.setViewportSize({ width, height: 844 });
      await practice.click();
      await expect(page.getByRole('heading', { name: 'Original starter lessons', exact: true })).toBeVisible();
      await expect.poll(() => page.evaluate(() => window.innerWidth)).toBe(width);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      const links = await page.locator('.preparation-page a.mono').evaluateAll(nodes => nodes.map(node => {
        const box = node.getBoundingClientRect();
        return { href: node.getAttribute('href'), text: node.textContent?.trim(), left: box.left, right: box.right };
      }));
      expect(links.map(link => link.href)).toEqual(expectedURLs);
      expect(links.map(link => link.text)).toEqual(expectedURLs);
      for (const link of links) {
        expect(link.left).toBeGreaterThanOrEqual(0);
        expect(link.right).toBeLessThanOrEqual(width);
      }
      await test.info().attach(`preparation-catalogue-layout-${width}`, {
        body: JSON.stringify({ width, links }), contentType: 'application/json',
      });
      for (const lesson of starters) {
        await practice.click();
        const start = page.getByRole('button', { name: `Start ${lesson.title}`, exact: true });
        await start.scrollIntoViewIfNeeded();
        await expect.poll(() => start.evaluate(element => {
          const box = element.getBoundingClientRect();
          const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
          return hit === element || Boolean(hit && element.contains(hit));
        })).toBe(true);
        const opened = page.waitForResponse(reply => reply.request().method() === 'GET'
          && new URL(reply.url()).pathname.endsWith(`/preparation/lessons/${lesson.id}`));
        await start.click();
        expect((await opened).ok()).toBeTruthy();
        await expect(page.getByRole('heading', { name: lesson.title, exact: true })).toBeVisible();
        const choices = await page.locator('.preparation-choice').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().height));
        expect(choices.length).toBeGreaterThan(0);
        for (const height of choices) expect(height).toBeGreaterThanOrEqual(44);
      }
    }
  } finally {
    if (originalViewport) await page.setViewportSize(originalViewport);
  }
});


const scheduleDate = (offset: number) => {
  const date = new Date(); date.setUTCHours(0, 0, 0, 0); date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
};
test('deadline plan persists dated targets, task completion and backward timing without changing official scores', async () => {
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your deadline study plan', exact: true })).toBeVisible();
  await page.getByLabel('Exam', { exact: true }).selectOption('digital_sat');
  await page.getByLabel('Preparation starts', { exact: true }).fill(scheduleDate(0));
  await page.getByLabel('Certificate deadline', { exact: true }).fill(scheduleDate(84));
  await page.getByLabel('First exam', { exact: true }).fill(scheduleDate(56));
  await page.getByLabel('Result wait (days)', { exact: true }).fill('5');
  await page.getByLabel('Delivery (days)', { exact: true }).fill('2');
  await page.getByLabel('Safety buffer (days)', { exact: true }).fill('7');
  await page.getByLabel('Time zone', { exact: true }).fill('UTC');
  for (const [field, value] of [['Total', '1400'], ['Math', '700'], ['Reading & Writing', '700']]) {
    await page.getByLabel(`${field} target`, { exact: true }).fill(value!);
  }
  for (const [field, value] of [['Total', '1200'], ['Math', '600'], ['Reading & Writing', '600']]) {
    await page.getByLabel(`${field} current score (optional)`, { exact: true }).fill(value!);
  }
  await page.getByLabel('Current-score date (optional)', { exact: true }).fill(scheduleDate(0));
  await page.getByLabel('Weekly study minutes', { exact: true }).fill('180');
  for (const day of ['Monday', 'Wednesday', 'Friday']) await page.getByRole('checkbox', { name: day, exact: true }).check();
  await page.getByRole('checkbox', { name: /I confirm these are my planning dates/ }).check();
  const saved = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  await page.getByRole('button', { name: 'Save study plan', exact: true }).click();
  const reply = await saved; expect(reply.status()).toBe(200);
  const calendar = await reply.json() as StudyScheduleOut;
  expect(calendar.profile_id).toBe(savedProfileId); expect(calendar.revision).toBe(1);
  expect(calendar.schedule).toMatchObject({ readiness: 'not_assessed', latest_safe_exam_on: scheduleDate(70), timing: 'within_entered_buffers' });
  expect(calendar.settings?.target_scores).toEqual({ total: 1400, math: 700, reading_writing: 700 });
  const tasks = calendar.schedule!.tasks;
  const totals: Record<string, number> = {};
  for (const task of tasks.filter(item => item.minutes > 0)) {
    expect(task.due_on).not.toBe(scheduleDate(56));
    const weekday = new Date(`${task.due_on}T00:00:00Z`).getUTCDay(); expect([1, 3, 5]).toContain(weekday);
    const monday = new Date(`${task.due_on}T00:00:00Z`); monday.setUTCDate(monday.getUTCDate() - (weekday + 6) % 7);
    const week = monday.toISOString().slice(0, 10); totals[week] = (totals[week] ?? 0) + task.minutes;
  }
  expect(Object.keys(totals).length).toBeGreaterThan(4);
  for (const minutes of Object.values(totals)) expect(minutes).toBeLessThanOrEqual(180);
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  await expect(page.getByLabel('Total target', { exact: true })).toHaveValue('1400');
  await expect(page.getByText('Readiness: not assessed.', { exact: true })).toBeVisible();
  const firstTask = page.getByRole('checkbox', { name: /^Completed:/ }).first();
  const checked = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  await firstTask.click(); expect((await checked).status()).toBe(200); await expect(firstTask).toBeChecked();
  const history = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`); expect(history.ok()).toBeTruthy();
  const receipt = await history.json() as StudyScheduleOut; expect(receipt.revision).toBe(2); expect(receipt.settings?.completed_task_ids).toHaveLength(1);
  const exported = await page.request.get(`/api/profiles/${savedProfileId}/export`); expect(exported.ok()).toBeTruthy();
  const document = await exported.json(); expect(document.counts.study_schedules).toBe(1); expect(document.study_schedules[0].settings).toEqual(receipt.settings);
  const profile = await page.request.get(`/api/profiles/${savedProfileId}`); expect(profile.ok()).toBeTruthy(); expect((await profile.json()).academics).toEqual(officialScores);
  const viewport = page.viewportSize();
  try {
    for (const width of [320, 390]) {
      await page.setViewportSize({ width, height: 844 });
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      const button = page.getByRole('button', { name: 'Save study plan', exact: true }); await button.scrollIntoViewIfNeeded();
      await expect.poll(() => button.evaluate(element => { const box = element.getBoundingClientRect(); const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2); return hit === element || Boolean(hit && element.contains(hit)); })).toBe(true);
      await page.screenshot({ path: shot(`study-schedule-mobile-${width}.png`), fullPage: false });
    }
  } finally { if (viewport) await page.setViewportSize(viewport); }
  await page.getByRole('heading', { name: 'Saved dated tasks', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot('study-schedule-timeline.png'), fullPage: false });
});

test('deadline risk and concurrent saved calendar remain explicit through the real UI and API', async () => {
  await page.getByLabel('First exam', { exact: true }).fill(scheduleDate(80));
  await page.getByRole('checkbox', { name: /I confirm these are my planning dates/ }).check();
  await page.getByRole('checkbox', { name: 'Rebuild the calendar and clear previous task checkmarks', exact: true }).check();
  const saved = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  await page.getByRole('button', { name: 'Save study plan', exact: true }).click();
  expect((await saved).status()).toBe(200);
  await expect(page.getByText(/Timing: at risk/)).toBeVisible();
  const current = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`);
  const record = await current.json() as StudyScheduleOut;
  expect(record.schedule?.delivery_expected_on).toBe(scheduleDate(87));
  expect(record.schedule?.tasks.some(task => task.kind === 'delivery' && task.due_on > record.settings!.certificate_deadline)).toBe(true);
  const other = await page.request.put(`/api/profiles/${savedProfileId}/preparation/schedule`, { data: { expected_revision: record.revision, settings: { ...record.settings, weekly_minutes: 240, completed_task_ids: [] } } });
  expect(other.ok()).toBeTruthy();
  const conflict = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  const rejectedTask = page.getByRole('checkbox', { name: /^Completed:/ }).first();
  await rejectedTask.click();
  expect((await conflict).status()).toBe(409);
  await expect(rejectedTask).not.toBeChecked();
  await expect(page.getByRole('checkbox', { name: 'I reviewed the latest saved version before replacing it', exact: true })).toBeVisible();
  await expect(page.getByLabel('Weekly study minutes', { exact: true })).toHaveValue('180');
  const unchanged = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`); expect((await unchanged.json()).settings.weekly_minutes).toBe(240);
  await expect(page.getByRole('button', { name: 'Save study plan', exact: true })).toBeDisabled();
  await page.screenshot({ path: shot('study-schedule-conflict.png'), fullPage: false });
});

test('dated opt-in materials preserve legacy settings and reopen the exact saved attempt after reload', async () => {
  // The preceding conflict scenario intentionally retains an unsaved form.
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  const endpoint = `/api/profiles/${savedProfileId}/preparation/schedule`;
  const legacy = await page.request.get(endpoint); expect(legacy.ok()).toBeTruthy();
  const before = await legacy.json() as StudyScheduleOut;
  expect(before.settings?.weekly_minutes).toBe(240);
  await expect(page.getByLabel('Weekly study minutes', { exact: true })).toHaveValue('240');
  const calendarUrl = endpoint + '/learning-path';
  const initial = await page.request.get(calendarUrl); expect((await initial.json()).learning_path).toBeNull();
  await page.getByRole('button', { name: 'View learning calendar' }).click();
  const prepared = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname.endsWith('/learning-path/preview'));
  await expect(page.getByRole('button', { name: 'Preview updated learning path' })).toBeEnabled();
  await page.getByRole('button', { name: 'Preview updated learning path' }).click();
  const previewReply = await prepared; expect(previewReply.ok()).toBeTruthy();
  const preview = await previewReply.json() as import('../src/types').LearningPathOut;
  expect((await (await page.request.get(calendarUrl)).json()).learning_path).toBeNull();
  const dated = preview.learning_path!.schedule.tasks.filter(task => task.due_on >= preview.learning_path!.schedule.as_of).slice(0, 14)
    .find(task => task.learning_ref?.kind === 'lesson' && task.availability === 'available');
  const ref = dated?.learning_ref;
  if (!dated || !ref || ref.kind !== 'lesson') throw new Error('No visible dated exact lesson');
  const saved = page.waitForResponse(reply => reply.request().method() === 'PUT' && new URL(reply.url()).pathname.endsWith('/learning-path'));
  await page.getByRole('button', { name: 'Use this updated path' }).click();
  expect((await saved).ok()).toBeTruthy();
  const row = page.locator(`li[data-learning-task="${dated.id}"]`);
  const opened = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/lessons/${ref.lesson_id}`));
  await row.getByRole('button', { name: 'Open lesson', exact: true }).click();
  const response = await opened; expect(response.ok()).toBeTruthy();
  expect(new URL(response.url()).searchParams.get('version')).toBe(ref.content_version);
  const lesson = await response.json() as import('../src/types').PreparationLesson;
  expect(lesson).toMatchObject({ id: ref.lesson_id, version: ref.content_version });
  for (const [index, question] of lesson.questions.entries()) {
    if ('answer_format' in question) await page.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill('sample');
    else await page.locator('.preparation-question').nth(index).getByRole('radio').first().check();
  }
  const submitted = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname.endsWith('/preparation/attempts'));
  await page.getByRole('button', { name: 'Submit practice', exact: true }).click();
  const submitReply = await submitted; expect(submitReply.ok()).toBeTruthy();
  const attempt = await submitReply.json() as import('../src/types').StudyAttempt;
  expect(attempt).toMatchObject({ profile_id: savedProfileId, lesson_id: ref.lesson_id, version: ref.content_version });
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  await page.getByRole('button', { name: 'View learning calendar' }).click();
  const restored = page.locator(`li[data-learning-task="${dated.id}"]`);
  await expect(restored.getByText('Saved submission — not mastery')).toBeVisible();
  const reviewed = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/attempts/${attempt.attempt_id}/review`));
  await restored.getByRole('button', { name: 'Review my saved attempt' }).click();
  expect((await reviewed).ok()).toBeTruthy();
  await expect(page.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', attempt.attempt_id);
  expect((await (await page.request.get(endpoint)).json()).settings).toEqual(before.settings);
  expect((await (await page.request.get(`/api/profiles/${savedProfileId}`)).json()).academics).toEqual(officialScores);
  await page.screenshot({ path: shot('learning-calendar-exact-review.png'), fullPage: true });
});

// Append after the current final test in frontend/e2e/preparation.spec.ts.
// The existing imports already provide expect, test, page, shot, savedProfileId and savedAttemptId.
test('explicit own programme comparison reads real G1 evidence without changing saved learning', async () => {
  // The preceding conflict/learning tests share this page. Reload first so their
  // mounted legacy form cannot leak into the new scenario.
  await page.reload();
  const scheduleUrl = `/api/profiles/${savedProfileId}/preparation/schedule`;
  const sidecarUrl = `${scheduleUrl}/learning-path`;
  const progressUrl = `/api/profiles/${savedProfileId}/preparation/progress`;
  const beforeScheduleReply = await page.request.get(scheduleUrl);
  const beforeSidecarReply = await page.request.get(sidecarUrl);
  const beforeProgressReply = await page.request.get(progressUrl);
  expect(beforeScheduleReply.ok()).toBeTruthy();
  expect(beforeSidecarReply.ok()).toBeTruthy();
  expect(beforeProgressReply.ok()).toBeTruthy();
  const beforeSchedule = await beforeScheduleReply.json() as import('../src/types').StudyScheduleOut;
  const beforeSidecar = await beforeSidecarReply.json() as import('../src/types').LearningPathOut;
  const beforeProgress = await beforeProgressReply.json() as import('../src/types').PreparationProgress;
  expect(beforeSidecar.learning_path).not.toBeNull();
  expect(beforeProgress.attempts.some(item => item.attempt_id === savedAttemptId)).toBe(true);

  await page.goto('/#/shortlist');
  const delft = page.locator('.find-card').filter({ has: page.getByRole('heading', {
    name: 'Delft University of Technology', exact: true,
  }) }).first();
  await expect(delft.getByRole('button', { name: 'Saved', exact: true })).toBeVisible();
  const second = page.locator('.find-card').filter({ hasNotText: 'Delft University of Technology' })
    .filter({ has: page.getByRole('button', { name: 'Save', exact: true }) }).first();
  await expect(second).toBeVisible();
  const cardId = async (card: import('@playwright/test').Locator) => {
    const marker = await card.getAttribute('data-testid');
    expect(marker).toMatch(/^card-\S+$/);
    return marker!.slice(5);
  };
  const firstId = await cardId(delft);
  const secondId = await cardId(second);
  expect(secondId).not.toBe(firstId);
  const firstName = (await delft.locator('h2').innerText()).trim();
  const firstProgramme = (await delft.locator('.find-card__body > p').first().innerText()).trim();
  const secondName = (await second.locator('h2').innerText()).trim();
  const secondProgramme = (await second.locator('.find-card__body > p').first().innerText()).trim();
  const decided = page.waitForResponse(reply => reply.request().method() === 'POST'
    && new URL(reply.url()).pathname.endsWith(`/results/${secondId}/decision`));
  await second.getByRole('button', { name: 'Save', exact: true }).click();
  const decisionReply = await decided;
  expect(decisionReply.ok()).toBeTruthy();
  expect((await decisionReply.json()).user_decision).toBe('maybe');

  let graphReads = 0;
  const countGraphRead = (request: import('@playwright/test').Request) => {
    if (request.method() === 'GET' && new URL(request.url()).pathname ===
      `/api/profiles/${savedProfileId}/preparation/graph`) graphReads += 1;
  };
  page.on('request', countGraphRead);
  await page.goto('/#/preparation');
  await expect(page.getByRole('heading', { name: 'Exam goals from your chosen programmes' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
  const choices = page.getByRole('group', { name: 'Programmes to compare' });
  const choose = (name: string, programme: string) => choices.locator('label')
    .filter({ hasText: `${name} — ${programme}` }).getByRole('checkbox');
  await choose(firstName, firstProgramme).check();
  await choose(secondName, secondProgramme).check();
  expect(graphReads).toBe(0);
  const selected = [firstId, secondId];
  const graphReplyPromise = page.waitForResponse(reply => {
    const url = new URL(reply.url());
    return reply.request().method() === 'GET'
      && url.pathname === `/api/profiles/${savedProfileId}/preparation/graph`
      && url.searchParams.getAll('result_id').length === 2;
  });
  await page.getByRole('button', { name: 'View combined evidence', exact: true }).click();
  const graphReply = await graphReplyPromise;
  expect(graphReply.ok()).toBeTruthy();
  expect(graphReads).toBe(1);
  page.off('request', countGraphRead);
  const graphUrl = new URL(graphReply.url());
  expect(graphUrl.searchParams.getAll('result_id')).toEqual(selected);
  const graph = await graphReply.json() as import('../src/types').PreparationGraph;
  expect(graph).toMatchObject({
    schema_version: 'preparation-graph-v1', profile_id: savedProfileId,
    selection_source: 'server_verified_owned_explicit',
    requested_result_ids: selected, selected_result_ids: selected,
  });
  expect(graph.programmes.map(item => item.result_id)).toEqual(selected);
  expect(graph.source_manifest.map(item => item.result_id)).toEqual(selected);
  expect(graph.programmes.every(item => item.user_decision === 'approved' || item.user_decision === 'maybe')).toBe(true);
  expect(graph.exam_workstreams.length).toBeGreaterThan(0);

  const firstCard = page.getByRole('region', { name: `Programme evidence ${firstId}` });
  const secondCard = page.getByRole('region', { name: `Programme evidence ${secondId}` });
  await expect(firstCard).toBeVisible();
  await expect(secondCard).toBeVisible();
  await expect(page.getByText(/has not created or saved a shared study plan/)).toBeVisible();
  await expect(page.getByText(/Family observation only/)).toBeVisible();
  const atom = graph.requirements.find(item => item.result_id === firstId);
  if (!atom) throw new Error('The own Delft graph omitted its stored exam requirement');
  const requirement = firstCard.getByRole('region', { name: atom.original_check.requirement }).first();
  await expect(requirement).toBeVisible();
  if (atom.original_check.explanation) {
    await expect(requirement.getByText(atom.original_check.explanation, { exact: true })).toBeVisible();
  }
  if (atom.unresolved_reasons.length) await expect(requirement.getByText('Unresolved evidence')).toBeVisible();
  await requirement.getByText('Source evidence', { exact: true }).click();
  if (atom.proofs.length) {
    await expect(requirement.getByText(atom.proofs[0]!.claim.original_text_excerpt, { exact: true })).toBeVisible();
    await expect(requirement.locator('a, code').filter({ hasText: atom.proofs[0]!.claim.source_url }).first()).toBeVisible();
    expect(atom.proofs[0]!.scope.requested).toEqual(graph.programmes[0]!.requested_scope);
  } else {
    await expect(requirement.getByText('No exact linked proof establishes this requirement.')).toBeVisible();
  }
  await expect(requirement.getByText(/Original stored references:/)).toBeVisible();
  await expect(requirement.getByText(/Exact resolved claim IDs:/)).toBeVisible();

  const viewport = page.viewportSize();
  try {
    for (const width of [320, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect.poll(() => page.evaluate(() =>
        document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      await firstCard.scrollIntoViewIfNeeded();
      await page.screenshot({ path: shot(`g1-own-graph-${width}.png`), fullPage: true });
    }
  } finally { if (viewport) await page.setViewportSize(viewport); }

  let graphReadsAfterReload = 0;
  const observe = (request: import('@playwright/test').Request) => {
    if (request.method() === 'GET' && new URL(request.url()).pathname ===
      `/api/profiles/${savedProfileId}/preparation/graph`) graphReadsAfterReload += 1;
  };
  page.on('request', observe);
  try {
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
    await expect(page.getByRole('group', { name: 'Programmes to compare' })
      .getByRole('checkbox', { checked: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'View combined evidence' })).toBeDisabled();
    expect(graphReadsAfterReload).toBe(0);
  } finally { page.off('request', observe); }

  const afterScheduleReply = await page.request.get(scheduleUrl);
  const afterSidecarReply = await page.request.get(sidecarUrl);
  const afterProgressReply = await page.request.get(progressUrl);
  expect(afterScheduleReply.ok()).toBeTruthy();
  expect(afterSidecarReply.ok()).toBeTruthy();
  expect(afterProgressReply.ok()).toBeTruthy();
  const afterSchedule = await afterScheduleReply.json() as import('../src/types').StudyScheduleOut;
  const afterSidecar = await afterSidecarReply.json() as import('../src/types').LearningPathOut;
  const afterProgress = await afterProgressReply.json() as import('../src/types').PreparationProgress;
  expect(afterSchedule.revision).toBe(beforeSchedule.revision);
  expect(afterSchedule.settings).toEqual(beforeSchedule.settings);
  expect(afterSidecar.revision).toBe(beforeSidecar.revision);
  expect(afterSidecar.learning_path?.draft.fingerprint).toBe(beforeSidecar.learning_path?.draft.fingerprint);
  expect(afterProgress.attempts.some(item => item.attempt_id === savedAttemptId)).toBe(true);
});


test('one shared route saves an exact real receipt and opens its own versioned materials after reload', async () => {
  await page.reload();
  const endpoint = `/api/profiles/${savedProfileId}/preparation/shared-route`;
  const before = await page.request.get(`/api/profiles/${savedProfileId}/export`);
  expect(before.ok()).toBeTruthy();
  const baseline = await before.json();
  expect(baseline.shared_route_current).toBeNull();
  expect(baseline.shared_route_history).toEqual([]);
  await page.goto('/#/shortlist');
  const savedCards = page.locator('.find-card').filter({ has: page.getByRole('button', { name: 'Saved', exact: true }) });
  await expect(savedCards.nth(1)).toBeVisible();
  const selectedIds: string[] = [];
  for (const card of [savedCards.nth(0), savedCards.nth(1)]) {
    const id = await card.getAttribute('data-testid');
    expect(id).toMatch(/^card-\S+$/); selectedIds.push(id!.slice(5));
  }
  await page.goto('/#/preparation');
  const nav = page.getByRole('navigation', { name: 'Preparation views' });
  await nav.getByRole('button', { name: 'Shared route', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Shared preparation route' })).toBeVisible();
  const form = page.getByRole('region', { name: 'Plan a shared route', exact: true });
  for (const id of selectedIds) {
    await form.getByLabel('Older saved result ID', { exact: true }).fill(id);
    await form.getByRole('button', { name: 'Add saved ID', exact: true }).click();
  }
  const date = (offset: number) => { const value = new Date(); value.setUTCDate(value.getUTCDate() + offset); return value.toISOString().slice(0, 10); };
  await form.getByLabel('Planning starts on', { exact: true }).fill(date(1));
  await form.getByLabel('Your time zone', { exact: true }).fill('UTC');
  await form.getByLabel('Minutes available each week across all exams', { exact: true }).fill('240');
  for (const exam of ['IELTS Academic', 'Digital SAT']) {
    const group = form.getByRole('group', { name: exam, exact: true });
    await group.getByLabel('Include this personal exam', { exact: true }).check();
    await group.getByLabel('First exam date', { exact: true }).fill(date(60));
    await group.getByLabel('Date by which you want the certificate', { exact: true }).fill(date(90));
    await group.getByLabel('Days for results', { exact: true }).fill('5');
    await group.getByLabel('Delivery days', { exact: true }).fill('2');
    await group.getByLabel('Safety buffer days', { exact: true }).fill('7');
    await group.getByLabel('I entered these personal dates and buffers myself', { exact: true }).check();
  }
  await form.getByRole('group', { name: 'Digital SAT', exact: true }).getByRole('button', { name: 'Make this exam first in the allocation order', exact: true }).click();
  const reviews = form.locator('details').filter({ has: page.getByText('My saved attempt reviews', { exact: true }) });
  await reviews.locator('summary').click();
  await reviews.locator('.row').filter({ hasText: 'ielts-reading-1' }).first().getByRole('button', { name: 'Add own review', exact: true }).click();
  await reviews.getByLabel('Exam stream', { exact: true }).selectOption('ielts_academic');
  await reviews.getByLabel('Minutes for this review', { exact: true }).fill('30');
  await form.getByLabel('I chose these programmes, study capacity and personal exam plans explicitly', { exact: true }).check();
  const previewPromise = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname === `${endpoint}/preview`);
  await form.getByRole('button', { name: 'Preview route', exact: true }).click();
  const previewReply = await previewPromise;
  expect(previewReply.ok()).toBeTruthy();
  const preview = await previewReply.json() as import('../src/types').SharedRoutePreviewOutV1;
  expect(preview.saved).toBe(false); expect(preview.requested_result_ids).toEqual(selectedIds);
  expect(preview.allocation.ordered_exam_choices.map(item => item.exam)).toEqual(['digital_sat', 'ielts_academic']);
  expect(preview.allocation.slots.some(item => item.ref.kind === 'attempt_review' && item.ref.attempt_id === savedAttemptId)).toBe(true);
  for (const week of preview.allocation.capacity) expect(week.allocated_minutes).toBeLessThanOrEqual(240);
  const unsaved = await page.request.get(endpoint); expect(unsaved.ok()).toBeTruthy();
  expect((await unsaved.json()).revision).toBe(0);
  const savedPromise = page.waitForResponse(reply => reply.request().method() === 'PUT' && new URL(reply.url()).pathname === endpoint);
  await form.getByRole('button', { name: 'Save this exact preview', exact: true }).click();
  const savedReply = await savedPromise; expect(savedReply.ok()).toBeTruthy();
  const receipt = await savedReply.json() as import('../src/types').SharedRouteWriteReceiptV1;
  expect(receipt.profile_id).toBe(savedProfileId); expect(receipt.revision).toBe(1);
  expect(receipt.allocation_digest).toBe(preview.allocation.digest);
  const replay = await page.request.put(endpoint, { data: savedReply.request().postDataJSON() });
  expect(replay.ok()).toBeTruthy(); expect(await replay.json()).toEqual(receipt);
  await page.reload();
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Shared route', exact: true }).click();
  const current = page.getByRole('region', { name: 'Current saved route', exact: true });
  await expect(current).toContainText('Revision 1');
  const loaded = await page.request.get(endpoint); expect(loaded.ok()).toBeTruthy();
  expect((await loaded.json()).view.receipt).toEqual(receipt);
  const earlier = page.locator('details').filter({ has: page.getByText('Earlier saved revisions', { exact: true }) });
  await earlier.locator('summary').click();
  await earlier.getByLabel('Revision', { exact: true }).fill('1');
  await earlier.getByRole('button', { name: 'Open revision', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Earlier saved route', exact: true })).toContainText('Revision 1');
  const viewport = page.viewportSize();
  try {
    for (const width of [320, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await current.scrollIntoViewIfNeeded();
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      await page.screenshot({ path: shot(`g2-shared-route-${width}.png`), fullPage: true });
    }
  } finally { if (viewport) await page.setViewportSize(viewport); }
  const reviewReplyPromise = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${savedAttemptId}`));
  await current.getByRole('button', { name: 'Open my exact review', exact: true }).click();
  const reviewReply = await reviewReplyPromise; expect(reviewReply.ok()).toBeTruthy();
  expect((await reviewReply.json()).attempt.attempt_id).toBe(savedAttemptId);
  await expect(page.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', savedAttemptId);
  await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  const oldPlan = page.locator('details').filter({ has: page.getByText('Earlier personal study plan', { exact: true }) }).first();
  await oldPlan.locator('summary').click();
  await expect(oldPlan.getByRole('button', { name: 'Save study plan', exact: true })).toBeDisabled();
  const after = await page.request.get(`/api/profiles/${savedProfileId}/export`); expect(after.ok()).toBeTruthy();
  const exported = await after.json();
  expect(exported.shared_route_current).toEqual(receipt); expect(exported.shared_route_history).toEqual([receipt]);
  expect(exported.study_schedules).toEqual(baseline.study_schedules);
  expect(exported.study_attempts).toEqual(baseline.study_attempts);
  expect(exported.profile.academics).toEqual(baseline.profile.academics);
});
