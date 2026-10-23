# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: preparation.spec.ts >> six mobile destinations stay readable in one row with a matching safe bottom reserve
- Location: ../../../../source/frontend/e2e/preparation.spec.ts:117:1

# Error details

```
Error: expect(received).toBeLessThanOrEqual(expected)

Expected: <= 46
Received:    48
```

# Page snapshot

```yaml
- generic [ref=f1e3]:
  - complementary [ref=f1e4]:
    - generic [ref=f1e5]: Unimatch
    - navigation "Main navigation" [ref=f1e7]:
      - button "Home" [ref=f1e8] [cursor=pointer]
      - button "Find" [ref=f1e12] [cursor=pointer]:
        - generic [ref=f1e16]: "20"
      - button "Plan" [ref=f1e17] [cursor=pointer]:
        - generic [ref=f1e21]: "1"
      - button "Exam preparation" [ref=f1e22] [cursor=pointer]
      - button "Documents" [ref=f1e26] [cursor=pointer]
      - button "Community" [ref=f1e30] [cursor=pointer]
    - generic [ref=f1e34]:
      - paragraph [ref=f1e35]:
        - text: Same students.
        - strong [ref=f1e36]: Bigger horizons.
      - group [ref=f1e37]:
        - generic "Preferences" [ref=f1e38] [cursor=pointer]
        - option "Match system"
        - option "Light" [selected]
        - option "Dark"
        - option "English" [selected]
        - option "Русский"
        - option "Қазақша"
  - generic [ref=f1e39]:
    - banner [ref=f1e40]:
      - generic [ref=f1e41]: Demo data
      - group [ref=f1e42]:
        - generic "Explore⌄" [ref=f1e43] [cursor=pointer]
      - generic [ref=f1e44]:
        - text: Applicant
        - combobox "Applicant" [ref=f1e45]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 1 run" [selected]
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
      - button "New case" [ref=f1e46] [cursor=pointer]
      - button "Settings" [ref=f1e47] [cursor=pointer]
      - button "Sign out" [ref=f1e48] [cursor=pointer]
    - main "Exam preparation" [ref=f1e49]:
      - generic [ref=f1e50]:
        - generic [ref=f1e51]:
          - paragraph [ref=f1e52]: ORIGINAL PRACTICE · YOUR CASE
          - heading "Prepare for your next step." [level=1] [ref=f1e53]
          - paragraph [ref=f1e54]: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
        - note [ref=f1e55]:
          - generic [ref=f1e56]:
            - strong [ref=f1e57]: Development starter access
            - paragraph [ref=f1e58]: Original IELTS Reading, SAT Math and SAT Reading & Writing practice units. This is not a full exam course or an official mock test.
            - paragraph [ref=f1e59]: Local preview access
        - navigation "Preparation views" [ref=f1e60]:
          - button "Goals & evidence" [ref=f1e61] [cursor=pointer]
          - button "Study plan" [ref=f1e62] [cursor=pointer]
          - button "Practice" [ref=f1e63] [cursor=pointer]
          - button "Progress" [pressed] [ref=f1e64] [cursor=pointer]
        - paragraph [ref=f1e65]: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
        - generic [ref=f1e66]:
          - heading "Your saved practice" [level=2] [ref=f1e68]
          - paragraph [ref=f1e69]: Completed means submitted, not mastered. These results are not official exam scores.
          - button "Refresh saved history" [ref=f1e70] [cursor=pointer]
          - paragraph [ref=f1e71]: 1 saved attempts · 1 practice lessons submitted.
          - paragraph [ref=f1e72]: 3 correct answers out of 3 answered across saved attempts.
          - list [ref=f1e73]:
            - listitem [ref=f1e74]:
              - text: "Reading: stated evidence and inference: 3 / 3 correct · Oct 12, 2026, 03:16 AM"
              - button "Review saved attempt 1" [ref=f1e75] [cursor=pointer]
```

# Test source

```ts
  42  |   const initialProfile = await page.request.get(`/api/profiles/${savedProfileId}`);
  43  |   expect(initialProfile.ok()).toBeTruthy();
  44  |   officialScores = (await initialProfile.json()).academics;
  45  |   expect(officialScores).toMatchObject({ ielts: { overall: 7 } });
  46  |   const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
  47  |   await expect(submit).toBeDisabled();
  48  |   await page.getByRole('radio', { name: 'Visits increased during the trial.', exact: true }).check();
  49  |   await page.getByRole('radio', { name: 'The harvest comparison is not given.', exact: true }).check();
  50  |   await page.getByRole('radio', { name: 'Heavy rain.', exact: true }).check();
  51  |   await expect(submit).toBeEnabled();
  52  |   const persisted = page.waitForResponse(response => response.request().method() === 'POST' && /\/preparation\/attempts$/.test(new URL(response.url()).pathname));
  53  |   await submit.click();
  54  |   const response = await persisted;
  55  |   expect(response.ok()).toBeTruthy();
  56  |   const attempt = await response.json();
  57  |   expect(attempt.profile_id).toBe(savedProfileId); savedAttemptId = attempt.attempt_id;
  58  |   expect(attempt).toMatchObject({ lesson_id: 'ielts-reading-1', correct: 3, total: 3 });
  59  |   await expect(page.getByTestId('practice-result')).toHaveText('3 / 3 correct — practice only');
  60  |   await expect(page.getByTestId('practice-result')).toHaveAttribute('data-attempt-id', savedAttemptId);
  61  |   const profile = await page.request.get(`/api/profiles/${savedProfileId}`);
  62  |   expect(profile.ok()).toBeTruthy();
  63  |   expect((await profile.json()).academics).toEqual(officialScores);
  64  |   const duplicate = await page.request.post(`/api/profiles/${savedProfileId}/preparation/attempts`, { data: response.request().postDataJSON() });
  65  |   expect(duplicate.ok()).toBeTruthy();
  66  |   expect((await duplicate.json()).id).toBe(attempt.id);
  67  |   const current = await page.request.get(`/api/profiles/${savedProfileId}`);
  68  |   expect((await current.json()).academics).toEqual(officialScores);
  69  |   await page.screenshot({ path: shot('preparation-feedback.png'), fullPage: true });
  70  | });
  71  | 
  72  | test('one persisted attempt survives reload and is included in own export', async () => {
  73  |   await page.reload();
  74  |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  75  |   await expect(page.getByTestId('progress-summary')).toContainText('1');
  76  |   await expect(page.getByRole('heading', { name: 'Your saved practice', exact: true })).toBeVisible();
  77  |   const progress = await page.request.get(`/api/profiles/${savedProfileId}/preparation/progress`);
  78  |   expect(progress.ok()).toBeTruthy();
  79  |   const history = await progress.json();
  80  |   expect(history.attempt_count).toBe(1);
  81  |   expect(history.attempts[0].attempt_id).toBe(savedAttemptId);
  82  |   const exported = await page.request.get(`/api/profiles/${savedProfileId}/export`);
  83  |   expect(exported.ok()).toBeTruthy();
  84  |   expect((await exported.json()).study_attempts).toHaveLength(1);
  85  |   await page.screenshot({ path: shot('preparation-progress.png'), fullPage: true });
  86  | });
  87  | 
  88  | /** Measured actual DOM geometry; no API mocks or synthetic layout overrides. */
  89  | async function mobileNavigationGeometry() {
  90  |   return page.evaluate(() => {
  91  |     const sidebar = document.querySelector<HTMLElement>('.sidebar')!;
  92  |     const nav = sidebar.querySelector<HTMLElement>('nav[aria-label="Main navigation"]')!;
  93  |     const main = document.querySelector<HTMLElement>('.main')!;
  94  |     const rectangle = (element: Element) => {
  95  |       const value = element.getBoundingClientRect();
  96  |       return { left: value.left, right: value.right, top: value.top, bottom: value.bottom, width: value.width, height: value.height };
  97  |     };
  98  |     const items = Array.from(nav.querySelectorAll<HTMLButtonElement>('button')).map(button => {
  99  |       const label = button.querySelector<HTMLElement>('.nav__label--compact') ?? button.querySelector<HTMLElement>('span')!;
  100 |       const style = getComputedStyle(label);
  101 |       return { accessibleName: button.getAttribute('aria-label'), box: rectangle(button),
  102 |         label: { text: label.textContent?.trim(), box: rectangle(label), fontSize: parseFloat(style.fontSize),
  103 |           lineHeight: parseFloat(style.lineHeight), scrollWidth: label.scrollWidth, clientWidth: label.clientWidth } };
  104 |     });
  105 |     const rows: number[] = [];
  106 |     for (const item of items) if (!rows.some(top => Math.abs(top - item.box.top) < 2)) rows.push(item.box.top);
  107 |     const style = getComputedStyle(sidebar);
  108 |     return { viewport: document.documentElement.clientWidth, rootFontSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
  109 |       sidebar: rectangle(sidebar), sidebarPosition: style.position,
  110 |       paddingTop: parseFloat(style.paddingTop), paddingBottom: parseFloat(style.paddingBottom),
  111 |       borderTop: parseFloat(style.borderTopWidth), nav: rectangle(nav), rowCount: rows.length,
  112 |       columnCount: getComputedStyle(nav).gridTemplateColumns.split(' ').length,
  113 |       mainBottomReserve: parseFloat(getComputedStyle(main).paddingBottom), items };
  114 |   });
  115 | }
  116 | 
  117 | test('six mobile destinations stay readable in one row with a matching safe bottom reserve', async () => {
  118 |   const originalViewport = page.viewportSize();
  119 |   try {
  120 |     for (const width of [390, 320]) {
  121 |       await page.setViewportSize({ width, height: 800 });
  122 |       const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  123 |       await expect(nav.getByRole('button')).toHaveCount(6);
  124 |       await expect(nav.getByRole('button', { name: 'Exam preparation', exact: true })).toBeVisible();
  125 |       await expect.poll(async () => (await mobileNavigationGeometry()).rowCount).toBe(1);
  126 |       const measured = await mobileNavigationGeometry();
  127 |       expect(measured.viewport).toBe(width);
  128 |       expect(measured.sidebarPosition).toBe('fixed');
  129 |       expect(measured.columnCount).toBe(6);
  130 |       expect(measured.sidebar.left).toBeGreaterThanOrEqual(0);
  131 |       expect(measured.sidebar.right).toBeLessThanOrEqual(width + 1);
  132 |       expect(measured.items.map(item => item.label.text)).toEqual(['Home', 'Find', 'Plan', 'Prepare', 'Docs', 'People']);
  133 |       expect(measured.items.map(item => item.accessibleName)).toEqual(['Home', 'Find', 'Plan', 'Exam preparation', 'Documents', 'Community']);
  134 |       for (const item of measured.items) {
  135 |         expect(item.box.width).toBeGreaterThanOrEqual(44);
  136 |         expect(item.box.height).toBeGreaterThanOrEqual(44);
  137 |         expect(item.box.left).toBeGreaterThanOrEqual(measured.nav.left - 1);
  138 |         expect(item.box.right).toBeLessThanOrEqual(measured.nav.right + 1);
  139 |         expect(item.label.fontSize).toBeGreaterThanOrEqual(12);
  140 |         expect(item.label.box.left).toBeGreaterThanOrEqual(item.box.left - 1);
  141 |         expect(item.label.box.right).toBeLessThanOrEqual(item.box.right + 1);
> 142 |         expect(item.label.scrollWidth).toBeLessThanOrEqual(item.label.clientWidth + 1);
      |                                        ^ Error: expect(received).toBeLessThanOrEqual(expected)
  143 |         expect(item.label.box.height).toBeLessThanOrEqual(item.label.lineHeight + 1);
  144 |       }
  145 |       expect(measured.paddingBottom).toBeGreaterThanOrEqual(measured.paddingTop);
  146 |       expect(measured.sidebar.height).toBeLessThanOrEqual(measured.items[0]!.box.height + measured.paddingTop + measured.paddingBottom + measured.borderTop + 1);
  147 |       expect(measured.mainBottomReserve).toBeGreaterThanOrEqual(measured.sidebar.height + measured.rootFontSize * 0.75 - 1);
  148 |       await test.info().attach(`mobile-navigation-${width}.json`, { body: JSON.stringify(measured, null, 2), contentType: 'application/json' });
  149 |     }
  150 |   } finally { if (originalViewport) await page.setViewportSize(originalViewport); }
  151 | });
  152 | 
  153 | test('the final real practice actions scroll above the fixed navigation at 390 and 320', async () => {
  154 |   const originalViewport = page.viewportSize();
  155 |   try {
  156 |     for (const width of [390, 320]) {
  157 |       await page.setViewportSize({ width, height: 800 });
  158 |       await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  159 |       const opened = page.waitForResponse(response => response.request().method() === 'GET' && /\/preparation\/lessons\/ielts-reading-1$/.test(new URL(response.url()).pathname));
  160 |       await page.getByRole('button', { name: 'Start Reading: stated evidence and inference', exact: true }).click();
  161 |       expect((await opened).ok()).toBeTruthy();
  162 |       await page.getByRole('radio', { name: 'Visits increased during the trial.', exact: true }).check();
  163 |       await page.getByRole('radio', { name: 'The harvest comparison is not given.', exact: true }).check();
  164 |       await page.getByRole('radio', { name: 'Heavy rain.', exact: true }).check();
  165 |       const submit = page.getByRole('button', { name: 'Submit practice', exact: true });
  166 |       const lastAction = page.getByRole('button', { name: 'Restart lesson with a new attempt', exact: true });
  167 |       await expect(submit).toBeEnabled(); await expect(lastAction).toBeEnabled();
  168 |       await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  169 |       // Respect native smooth scrolling; observe the real geometry before measuring it.
  170 |       await expect.poll(async () => lastAction.evaluate(element => {
  171 |         const rect = element.getBoundingClientRect();
  172 |         const bar = document.querySelector<HTMLElement>('.sidebar')!.getBoundingClientRect();
  173 |         return rect.top >= 0 && rect.bottom <= bar.top - 8
  174 |           && document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.closest('button') === element;
  175 |       })).toBe(true);
  176 |       const action = await lastAction.evaluate(element => {
  177 |         const rect = element.getBoundingClientRect();
  178 |         const bar = document.querySelector<HTMLElement>('.sidebar')!.getBoundingClientRect();
  179 |         return { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right, height: rect.height,
  180 |           sidebarTop: bar.top, viewportWidth: document.documentElement.clientWidth,
  181 |           reached: document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.closest('button') === element };
  182 |       });
  183 |       expect(action.viewportWidth).toBe(width);
  184 |       expect(action.top).toBeGreaterThanOrEqual(0);
  185 |       expect(action.bottom).toBeLessThanOrEqual(action.sidebarTop - 8);
  186 |       expect(action.left).toBeGreaterThanOrEqual(0);
  187 |       expect(action.right).toBeLessThanOrEqual(width + 1);
  188 |       expect(action.height).toBeGreaterThanOrEqual(44);
  189 |       expect(action.reached).toBe(true);
  190 |       const submitBox = await submit.boundingBox(); expect(submitBox).not.toBeNull();
  191 |       expect(submitBox!.y + submitBox!.height).toBeLessThanOrEqual(action.sidebarTop - 8);
  192 |       await test.info().attach(`mobile-practice-final-action-${width}.json`, { body: JSON.stringify({ action, submit: submitBox }, null, 2), contentType: 'application/json' });
  193 |       await page.screenshot({ path: shot(`preparation-mobile-final-action-${width}.png`), fullPage: true });
  194 |     }
  195 |   } finally { if (originalViewport) await page.setViewportSize(originalViewport); }
  196 | });
  197 | 
  198 | /** Keep catalogue links readable without expanding the mobile layout viewport. */
  199 | test('personal practice stays inside the requested viewport and all starter lessons open by normal clicks', async () => {
  200 |   const originalViewport = page.viewportSize();
  201 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Goals & evidence', exact: true }).click();
  202 |   const evidence = page.locator('.preparation-evidence').filter({ has: page.locator('.preparation-evidence__claim') }).first();
  203 |   const summary = evidence.locator(':scope > summary');
  204 |   await expect(summary).toBeVisible();
  205 |   await expect(evidence).not.toHaveAttribute('open');
  206 |   const quote = evidence.locator('.preparation-evidence__claim p').first();
  207 |   await expect(quote).toBeHidden();
  208 |   await summary.click();
  209 |   await expect(evidence).toHaveAttribute('open', '');
  210 |   await expect(quote).toBeVisible();
  211 |   await expect(evidence.locator('a[href], code').first()).toBeVisible();
  212 |   await expect(evidence.getByText(/Recorded source scope:/).first()).toBeVisible();
  213 |   await summary.click();
  214 |   await expect(quote).toBeHidden();
  215 |   const response = await page.request.get('/api/preparation/catalogue');
  216 |   expect(response.ok()).toBeTruthy();
  217 |   const catalogue = await response.json() as {
  218 |     exams: { official_info_urls: string[]; official_practice_urls: string[] }[];
  219 |     lessons: { id: string; title: string }[];
  220 |   };
  221 |   const expectedURLs = catalogue.exams.flatMap(exam => [...exam.official_info_urls, ...exam.official_practice_urls]);
  222 |   const starters = catalogue.lessons.filter(lesson => ['ielts-reading-1', 'sat-math-1', 'sat-rw-1'].includes(lesson.id));
  223 |   expect(starters).toHaveLength(3);
  224 |   const practice = page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true });
  225 |   try {
  226 |     for (const width of [320, 390]) {
  227 |       await page.setViewportSize({ width, height: 844 });
  228 |       await practice.click();
  229 |       await expect(page.getByRole('heading', { name: 'Original starter lessons', exact: true })).toBeVisible();
  230 |       await expect.poll(() => page.evaluate(() => window.innerWidth)).toBe(width);
  231 |       await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  232 |       const links = await page.locator('.preparation-page a.mono').evaluateAll(nodes => nodes.map(node => {
  233 |         const box = node.getBoundingClientRect();
  234 |         return { href: node.getAttribute('href'), text: node.textContent?.trim(), left: box.left, right: box.right };
  235 |       }));
  236 |       expect(links.map(link => link.href)).toEqual(expectedURLs);
  237 |       expect(links.map(link => link.text)).toEqual(expectedURLs);
  238 |       for (const link of links) {
  239 |         expect(link.left).toBeGreaterThanOrEqual(0);
  240 |         expect(link.right).toBeLessThanOrEqual(width);
  241 |       }
  242 |       await test.info().attach(`preparation-catalogue-layout-${width}`, {
```