# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: preparation.spec.ts >> a programme saved from Find retains its exam evidence in Preparation
- Location: ../../../../../integration-2026-10-11/source/frontend/e2e/preparation.spec.ts:18:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('IELTS writing', { exact: true })
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for getByText('IELTS writing', { exact: true })

```

```yaml
- complementary:
  - navigation "Main navigation":
    - button "Home"
    - button "Find"
    - button "Plan"
    - button "Exam preparation": Prepare
    - button "Documents": Docs
    - button "Community": People
- banner:
  - text: Unimatch Demo data
  - group: Explore⌄
  - text: Applicant
  - combobox "Applicant":
    - option "New applicant"
    - option "Demo Applicant (synthetic) · 0 runs" [selected]
    - option "Demo Applicant (synthetic) · 1 run"
    - option "Demo Applicant (synthetic) · 1 run"
    - option "New applicant · 0 runs"
    - option "New applicant · 0 runs"
    - option "New applicant · 0 runs"
    - option "Demo Applicant (synthetic) · 1 run"
    - option "Demo Applicant (synthetic) · 1 run"
    - option "Demo Applicant (synthetic) · 1 run"
  - button "New case"
  - button "Settings"
- main "Exam preparation":
  - paragraph: ORIGINAL PRACTICE · YOUR CASE
  - heading "Prepare for your next step." [level=1]
  - paragraph: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
  - note:
    - strong: Development starter access
    - paragraph: Original IELTS Reading, SAT Math and SAT Reading & Writing starters. This is not a full exam course or an official mock test.
    - paragraph: "Access reason: development mode"
  - navigation "Preparation views":
    - button "Goals & evidence" [pressed]
    - button "Practice"
    - button "Progress"
  - paragraph: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
  - heading "Exam goals from your chosen programmes" [level=2]
  - text: Programme evidence
  - combobox "Programme evidence":
    - option "Personal practice — no programme requirement selected"
    - option "Delft University of Technology — BSc Computer Science and Engineering · fall 2027" [selected]
  - status: Loading stored exam evidence…
```

# Test source

```ts
  1   | /** Native synthetic API round trip: programme evidence, original practice and saved history. */
  2   | import { expect, test, type Page } from '@playwright/test';
  3   | import { newSession, runDemoResearch, shot } from './helpers';
  4   | 
  5   | test.describe.configure({ mode: 'serial' });
  6   | let page: Page;
  7   | let savedProfileId = '';
  8   | let savedAttemptId = '';
  9   | let officialScores: unknown;
  10  | 
  11  | test.beforeAll(async ({ browser }) => {
  12  |   page = await newSession(browser);
  13  |   await runDemoResearch(page);
  14  | });
  15  | 
  16  | test.afterAll(async () => { await page.context().close(); });
  17  | 
  18  | test('a programme saved from Find retains its exam evidence in Preparation', async () => {
  19  |   await page.goto('/#/shortlist');
  20  |   const delft = page.locator('.find-card').filter({ has: page.getByRole('heading', { name: 'Delft University of Technology', exact: true }) });
  21  |   await delft.getByRole('button', { name: 'Save', exact: true }).click();
  22  |   await expect(delft.getByRole('button', { name: 'Saved', exact: true })).toHaveAttribute('aria-pressed', 'true');
  23  |   await page.getByTestId('nav-preparation').click();
  24  |   await expect(page).toHaveURL(/#\/preparation$/);
  25  |   const programme = page.getByLabel('Programme evidence');
  26  |   const value = await programme.locator('option').filter({ hasText: 'Delft University of Technology' }).getAttribute('value');
  27  |   expect(value).toBeTruthy();
  28  |   await programme.selectOption(value!);
> 29  |   await expect(page.getByText('IELTS writing', { exact: true })).toBeVisible();
      |                                                                  ^ Error: expect(locator).toBeVisible() failed
  30  |   await expect(page.getByText('Development starter access', { exact: true })).toBeVisible();
  31  |   await page.screenshot({ path: shot('preparation-goals.png'), fullPage: true });
  32  | });
  33  | 
  34  | test('practice is submitted to the real API and keeps official scores separate', async () => {
  35  |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  36  |   const opened = page.waitForResponse(response => response.request().method() === 'GET' && /\/preparation\/lessons\/ielts-reading-1$/.test(new URL(response.url()).pathname));
  37  |   await page.getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true }).click();
  38  |   const lessonResponse = await opened;
  39  |   expect(lessonResponse.ok()).toBeTruthy();
  40  |   savedProfileId = new URL(lessonResponse.url()).pathname.split('/')[3]!;
  41  |   const initialProfile = await page.request.get(`/api/profiles/${savedProfileId}`);
  42  |   expect(initialProfile.ok()).toBeTruthy();
  43  |   officialScores = (await initialProfile.json()).academics;
  44  |   expect(officialScores).toMatchObject({ ielts: { overall: 7 } });
  45  |   const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
  46  |   await expect(submit).toBeDisabled();
  47  |   await page.getByRole('radio', { name: 'Visits increased during the trial.', exact: true }).check();
  48  |   await page.getByRole('radio', { name: 'The harvest comparison is not given.', exact: true }).check();
  49  |   await page.getByRole('radio', { name: 'Heavy rain.', exact: true }).check();
  50  |   await expect(submit).toBeEnabled();
  51  |   const persisted = page.waitForResponse(response => response.request().method() === 'POST' && /\/preparation\/attempts$/.test(new URL(response.url()).pathname));
  52  |   await submit.click();
  53  |   const response = await persisted;
  54  |   expect(response.ok()).toBeTruthy();
  55  |   const attempt = await response.json();
  56  |   expect(attempt.profile_id).toBe(savedProfileId); savedAttemptId = attempt.attempt_id;
  57  |   expect(attempt).toMatchObject({ lesson_id: 'ielts-reading-1', correct: 3, total: 3 });
  58  |   await expect(page.getByTestId('practice-result')).toHaveText('3 / 3 correct — practice only');
  59  |   await expect(page.getByTestId('practice-result')).toHaveAttribute('data-attempt-id', savedAttemptId);
  60  |   const profile = await page.request.get(`/api/profiles/${savedProfileId}`);
  61  |   expect(profile.ok()).toBeTruthy();
  62  |   expect((await profile.json()).academics).toEqual(officialScores);
  63  |   const duplicate = await page.request.post(`/api/profiles/${savedProfileId}/preparation/attempts`, { data: response.request().postDataJSON() });
  64  |   expect(duplicate.ok()).toBeTruthy();
  65  |   expect((await duplicate.json()).id).toBe(attempt.id);
  66  |   const current = await page.request.get(`/api/profiles/${savedProfileId}`);
  67  |   expect((await current.json()).academics).toEqual(officialScores);
  68  |   await page.screenshot({ path: shot('preparation-feedback.png'), fullPage: true });
  69  | });
  70  | 
  71  | test('one persisted attempt survives reload and is included in own export', async () => {
  72  |   await page.reload();
  73  |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  74  |   await expect(page.getByTestId('progress-summary')).toContainText('1');
  75  |   await expect(page.getByRole('heading', { name: 'Your saved practice', exact: true })).toBeVisible();
  76  |   const progress = await page.request.get(`/api/profiles/${savedProfileId}/preparation/progress`);
  77  |   expect(progress.ok()).toBeTruthy();
  78  |   const history = await progress.json();
  79  |   expect(history.attempt_count).toBe(1);
  80  |   expect(history.attempts[0].attempt_id).toBe(savedAttemptId);
  81  |   const exported = await page.request.get(`/api/profiles/${savedProfileId}/export`);
  82  |   expect(exported.ok()).toBeTruthy();
  83  |   expect((await exported.json()).study_attempts).toHaveLength(1);
  84  |   await page.screenshot({ path: shot('preparation-progress.png'), fullPage: true });
  85  | });
  86  | 
  87  | /** Measured actual DOM geometry; no API mocks or synthetic layout overrides. */
  88  | async function mobileNavigationGeometry() {
  89  |   return page.evaluate(() => {
  90  |     const sidebar = document.querySelector<HTMLElement>('.sidebar')!;
  91  |     const nav = sidebar.querySelector<HTMLElement>('nav[aria-label="Main navigation"]')!;
  92  |     const main = document.querySelector<HTMLElement>('.main')!;
  93  |     const rectangle = (element: Element) => {
  94  |       const value = element.getBoundingClientRect();
  95  |       return { left: value.left, right: value.right, top: value.top, bottom: value.bottom, width: value.width, height: value.height };
  96  |     };
  97  |     const items = Array.from(nav.querySelectorAll<HTMLButtonElement>('button')).map(button => {
  98  |       const label = button.querySelector<HTMLElement>('.nav__label--compact') ?? button.querySelector<HTMLElement>('span')!;
  99  |       const style = getComputedStyle(label);
  100 |       return { accessibleName: button.getAttribute('aria-label'), box: rectangle(button),
  101 |         label: { text: label.textContent?.trim(), box: rectangle(label), fontSize: parseFloat(style.fontSize),
  102 |           lineHeight: parseFloat(style.lineHeight), scrollWidth: label.scrollWidth, clientWidth: label.clientWidth } };
  103 |     });
  104 |     const rows: number[] = [];
  105 |     for (const item of items) if (!rows.some(top => Math.abs(top - item.box.top) < 2)) rows.push(item.box.top);
  106 |     const style = getComputedStyle(sidebar);
  107 |     return { viewport: document.documentElement.clientWidth, rootFontSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
  108 |       sidebar: rectangle(sidebar), sidebarPosition: style.position,
  109 |       paddingTop: parseFloat(style.paddingTop), paddingBottom: parseFloat(style.paddingBottom),
  110 |       borderTop: parseFloat(style.borderTopWidth), nav: rectangle(nav), rowCount: rows.length,
  111 |       columnCount: getComputedStyle(nav).gridTemplateColumns.split(' ').length,
  112 |       mainBottomReserve: parseFloat(getComputedStyle(main).paddingBottom), items };
  113 |   });
  114 | }
  115 | 
  116 | test('six mobile destinations stay readable in one row with a matching safe bottom reserve', async () => {
  117 |   const originalViewport = page.viewportSize();
  118 |   try {
  119 |     for (const width of [390, 320]) {
  120 |       await page.setViewportSize({ width, height: 800 });
  121 |       const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  122 |       await expect(nav.getByRole('button')).toHaveCount(6);
  123 |       await expect(nav.getByRole('button', { name: 'Exam preparation', exact: true })).toBeVisible();
  124 |       await expect.poll(async () => (await mobileNavigationGeometry()).rowCount).toBe(1);
  125 |       const measured = await mobileNavigationGeometry();
  126 |       expect(measured.viewport).toBe(width);
  127 |       expect(measured.sidebarPosition).toBe('fixed');
  128 |       expect(measured.columnCount).toBe(6);
  129 |       expect(measured.sidebar.left).toBeGreaterThanOrEqual(0);
```