# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: preparation.spec.ts >> practice is submitted to the real API and keeps official scores separate
- Location: ../../../../../integration-2026-10-11/source/frontend/e2e/preparation.spec.ts:34:1

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: page.waitForResponse: Target page, context or browser has been closed
```

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true })
    - locator resolved to <button type="button" class="btn btn--sm">Start Reading: stated evidence and inference</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div class="stack stack--loose">…</div> intercepts pointer events
    - retrying click action
    - waiting 20ms
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - <div class="stack stack--loose">…</div> intercepts pointer events
  2 × retrying click action
      - waiting 100ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <span class="chip chip--demo ">Demo data</span> from <header class="topbar">…</header> subtree intercepts pointer events
  56 × retrying click action
       - waiting 500ms
       - waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <section class="panel ">…</section> intercepts pointer events
     - retrying click action
       - waiting 500ms
       - waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <div class="stack stack--loose">…</div> intercepts pointer events
     - retrying click action
       - waiting 500ms
       - waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <span class="chip chip--demo ">Demo data</span> from <header class="topbar">…</header> subtree intercepts pointer events
     - retrying click action
       - waiting 500ms
       - waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <span class="chip chip--demo ">Demo data</span> from <header class="topbar">…</header> subtree intercepts pointer events
  - retrying click action
    - waiting 500ms
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - <section class="panel ">…</section> intercepts pointer events
  - retrying click action
    - waiting 500ms
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - <div class="stack stack--loose">…</div> intercepts pointer events
  - retrying click action
    - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - navigation "Main navigation" [ref=e5]:
      - button "Home" [ref=e6] [cursor=pointer]
      - button "Find" [ref=e10] [cursor=pointer]
      - button "Plan" [ref=e14] [cursor=pointer]
      - button "Exam preparation" [ref=e18] [cursor=pointer]:
        - generic [ref=e21]: Prepare
      - button "Documents" [ref=e22] [cursor=pointer]:
        - generic [ref=e25]: Docs
      - button "Community" [ref=e26] [cursor=pointer]:
        - generic [ref=e29]: People
  - generic [ref=e30]:
    - banner [ref=e31]:
      - generic [ref=e32]: Unimatch
      - generic [ref=e33]: Demo data
      - group [ref=e34]:
        - generic "Explore⌄" [ref=e35] [cursor=pointer]
      - generic [ref=e36]:
        - text: Applicant
        - combobox "Applicant" [ref=e37]:
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
      - button "New case" [ref=e38] [cursor=pointer]
      - button "Settings" [ref=e39] [cursor=pointer]
    - main "Exam preparation" [ref=e40]:
      - generic [ref=e41]:
        - generic [ref=e42]:
          - paragraph [ref=e43]: ORIGINAL PRACTICE · YOUR CASE
          - heading "Prepare for your next step." [level=1] [ref=e44]
          - paragraph [ref=e45]: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
        - note [ref=e46]:
          - generic [ref=e47]:
            - strong [ref=e48]: Development starter access
            - paragraph [ref=e49]: Original IELTS Reading, SAT Math and SAT Reading & Writing starters. This is not a full exam course or an official mock test.
            - paragraph [ref=e50]: "Access reason: development mode"
        - navigation "Preparation views" [ref=e51]:
          - button "Goals & evidence" [ref=e52] [cursor=pointer]
          - button "Practice" [active] [pressed] [ref=e53] [cursor=pointer]
          - button "Progress" [ref=e54] [cursor=pointer]
        - paragraph [ref=e55]: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
        - generic [ref=e56]:
          - heading "Original starter lessons" [level=2] [ref=e58]
          - paragraph [ref=e59]: Original starter practice, not official exam items or a full course. Raw correct/total is not an IELTS band, SAT score, certificate or admission prediction. Official resources are external links; test booking and fees are separate. Planned courses have no starter lessons.
          - generic [ref=e60]:
            - generic [ref=e61]:
              - heading "IELTS Reading" [level=3] [ref=e62]
              - generic [ref=e63]:
                - generic [ref=e64]: "Reading: stated evidence and inference · 3 questions"
                - 'button "Start Reading: stated evidence and inference" [ref=e65] [cursor=pointer]'
            - generic [ref=e66]:
              - heading "SAT Math" [level=3] [ref=e67]
              - generic [ref=e68]:
                - generic [ref=e69]: "Math: linear relations and proportional reasoning · 3 questions"
                - 'button "Start Math: linear relations and proportional reasoning" [ref=e70] [cursor=pointer]'
            - generic [ref=e71]:
              - heading "SAT Reading and Writing" [level=3] [ref=e72]
              - generic [ref=e73]:
                - generic [ref=e74]: "Reading and Writing: evidence and sentence clarity · 3 questions"
                - 'button "Start Reading and Writing: evidence and sentence clarity" [ref=e75] [cursor=pointer]'
          - heading "Official exam information & planned courses" [level=3] [ref=e76]
          - paragraph [ref=e77]: Exam information below is not a requirement for every programme. Use your programme’s confirmed policy and current official edition.
          - generic [ref=e78]:
            - generic [ref=e79]:
              - heading "IELTS Academic" [level=3] [ref=e80]
              - generic [ref=e81]: Original starters available
              - paragraph [ref=e82]: Starter covers Reading only. Verify overall AND component minima and the recipient's accepted delivery type/retake/waiver policy. Recognition is not acceptance of General Training, Online, UKVI or One Skill Retake. Validity is recipient-specific.
              - paragraph [ref=e83]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e84]:
                - text: "Official information (external):"
                - link "https://ielts.org/take-a-test/test-types/ielts-academic-test" [ref=e85] [cursor=pointer]:
                  - /url: https://ielts.org/take-a-test/test-types/ielts-academic-test
              - generic [ref=e86]:
                - text: "Official practice (external):"
                - link "https://ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test" [ref=e87] [cursor=pointer]:
                  - /url: https://ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test
            - generic [ref=e88]:
              - heading "Digital SAT" [level=3] [ref=e89]
              - generic [ref=e90]: Original starters available
              - paragraph [ref=e91]: Original non-adaptive starters, not Bluebook or an official SAT score. Verify the programme's required/optional/not-considered, score-age and superscore policies; admission and scholarship requirements can differ. No universal two-year expiry.
              - paragraph [ref=e92]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e93]:
                - text: "Official information (external):"
                - link "https://satsuite.collegeboard.org/sat/whats-on-the-test/structure" [ref=e94] [cursor=pointer]:
                  - /url: https://satsuite.collegeboard.org/sat/whats-on-the-test/structure
              - generic [ref=e95]:
                - text: "Official practice (external):"
                - link "https://satsuite.collegeboard.org/practice/practice-tests/bluebook" [ref=e96] [cursor=pointer]:
                  - /url: https://satsuite.collegeboard.org/practice/practice-tests/bluebook
                - link "https://satsuite.collegeboard.org/practice/student-question-bank" [ref=e97] [cursor=pointer]:
                  - /url: https://satsuite.collegeboard.org/practice/student-question-bank
            - generic [ref=e98]:
              - heading "TOEFL iBT" [level=3] [ref=e99]
              - generic [ref=e100]: Course planned — not available here
              - paragraph [ref=e101]: No starter course yet. Tests from 21 January 2026 use 1–6 bands with a transitional comparable overall estimate. Preserve report scale/edition/date/components; do not invent old section conversions. Recipient acceptance of edition/MyBest/Home Edition must be checked. Existing profile fields support the legacy scale only.
              - paragraph [ref=e102]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e103]:
                - text: "Official information (external):"
                - link "https://www.ets.org/toefl/test-takers/ibt/scores/understand-scores.html" [ref=e104] [cursor=pointer]:
                  - /url: https://www.ets.org/toefl/test-takers/ibt/scores/understand-scores.html
              - generic [ref=e105]:
                - text: "Official practice (external):"
                - link "https://www.ets.org/toefl/test-takers/ibt/prepare.html" [ref=e106] [cursor=pointer]:
                  - /url: https://www.ets.org/toefl/test-takers/ibt/prepare.html
            - generic [ref=e107]:
              - heading "Duolingo English Test" [level=3] [ref=e108]
              - generic [ref=e109]: Course planned — not available here
              - paragraph [ref=e110]: No starter course yet. Preserve the certificate's component schema and date. An owner recognition directory does not settle programme/intake or visa acceptance; a practice estimated range is not a certified result.
              - paragraph [ref=e111]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e112]:
                - text: "Official information (external):"
                - link "https://blog.englishtest.duolingo.com/how-is-the-duolingo-english-test-scored/" [ref=e113] [cursor=pointer]:
                  - /url: https://blog.englishtest.duolingo.com/how-is-the-duolingo-english-test-scored/
              - generic [ref=e114]:
                - text: "Official practice (external):"
                - link "https://blog.englishtest.duolingo.com/duolingo-english-test-readiness/" [ref=e115] [cursor=pointer]:
                  - /url: https://blog.englishtest.duolingo.com/duolingo-english-test-readiness/
            - generic [ref=e116]:
              - heading "HSK / HSK Speaking (HSKK)" [level=3] [ref=e117]
              - generic [ref=e118]: Course planned — not available here
              - paragraph [ref=e119]: No starter course yet. Level, speaking report and booked edition matter. The announced worldwide HSK3.0 rollout on 13 December 2026 is still future at this catalogue's check date; a published syllabus does not prove a booked test switched. Check recipient/version-specific validity; HSK is not a universal China requirement.
              - paragraph [ref=e120]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e121]:
                - text: "Official information (external):"
                - link "https://www.chinesetest.cn/HSK" [ref=e122] [cursor=pointer]:
                  - /url: https://www.chinesetest.cn/HSK
                - link "https://www.chinesetest.cn/hskk/" [ref=e123] [cursor=pointer]:
                  - /url: https://www.chinesetest.cn/hskk/
                - link "https://old.chinesetest.cn/gonewcontent.do?flag=kdnew&id=51336883" [ref=e124] [cursor=pointer]:
                  - /url: https://old.chinesetest.cn/gonewcontent.do?flag=kdnew&id=51336883
              - generic [ref=e125]:
                - text: "Official practice (external):"
                - link "https://www.chinesetest.cn/" [ref=e126] [cursor=pointer]:
                  - /url: https://www.chinesetest.cn/
            - generic [ref=e127]:
              - heading "CSCA" [level=3] [ref=e128]
              - generic [ref=e129]: Course planned — not available here
              - paragraph [ref=e130]: No starter course yet. Mathematics, Physics, Chemistry and Professional Chinese depend on the selected university/programme/route. Distinct from HSK. No universal China mandate, entry score or score-validity duration is established. 2026 adoption examples are not 2027 requirements.
              - paragraph [ref=e131]: Metadata checked 2026-10-11. External links do not unlock a local course.
              - generic [ref=e132]:
                - text: "Official information (external):"
                - link "https://csca.cn/about/examintro" [ref=e133] [cursor=pointer]:
                  - /url: https://csca.cn/about/examintro
              - generic [ref=e134]:
                - text: "Official practice (external):"
                - link "https://csca.cn/testprep/" [ref=e135] [cursor=pointer]:
                  - /url: https://csca.cn/testprep/
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
  29  |   await expect(page.getByText('IELTS writing', { exact: true })).toBeVisible();
  30  |   await expect(page.getByText('Development starter access', { exact: true })).toBeVisible();
  31  |   await page.screenshot({ path: shot('preparation-goals.png'), fullPage: true });
  32  | });
  33  | 
  34  | test('practice is submitted to the real API and keeps official scores separate', async () => {
  35  |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  36  |   const opened = page.waitForResponse(response => response.request().method() === 'GET' && /\/preparation\/lessons\/ielts-reading-1$/.test(new URL(response.url()).pathname));
> 37  |   await page.getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true }).click();
      |                                                                                                         ^ Error: locator.click: Target page, context or browser has been closed
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
  130 |       expect(measured.sidebar.right).toBeLessThanOrEqual(width + 1);
  131 |       expect(measured.items.map(item => item.label.text)).toEqual(['Home', 'Find', 'Plan', 'Prepare', 'Docs', 'People']);
  132 |       expect(measured.items.map(item => item.accessibleName)).toEqual(['Home', 'Find', 'Plan', 'Exam preparation', 'Documents', 'Community']);
  133 |       for (const item of measured.items) {
  134 |         expect(item.box.width).toBeGreaterThanOrEqual(44);
  135 |         expect(item.box.height).toBeGreaterThanOrEqual(44);
  136 |         expect(item.box.left).toBeGreaterThanOrEqual(measured.nav.left - 1);
  137 |         expect(item.box.right).toBeLessThanOrEqual(measured.nav.right + 1);
```