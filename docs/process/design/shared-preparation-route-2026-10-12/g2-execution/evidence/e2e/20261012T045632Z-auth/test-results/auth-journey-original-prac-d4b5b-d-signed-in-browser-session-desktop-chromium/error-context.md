# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth-journey.spec.ts >> original practice persists into a second signed-in browser session
- Location: ../../../../source/frontend/e2e/auth-journey.spec.ts:72:1

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: locator.check: Target page, context or browser has been closed
Call log:
  - waiting for locator('fieldset').first().getByRole('radio', { name: '4', exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]: Unimatch
    - navigation "Main navigation" [ref=e7]:
      - button "Home" [ref=e8] [cursor=pointer]
      - button "Find" [ref=e12] [cursor=pointer]:
        - generic [ref=e16]: "20"
      - button "Plan" [ref=e17] [cursor=pointer]
      - button "Exam preparation" [ref=e21] [cursor=pointer]
      - button "Documents" [ref=e25] [cursor=pointer]
      - button "Community" [ref=e29] [cursor=pointer]
    - generic [ref=e33]:
      - paragraph [ref=e34]:
        - text: Same students.
        - strong [ref=e35]: Bigger horizons.
      - group [ref=e36]:
        - generic "Preferences" [ref=e37] [cursor=pointer]
        - option "Match system"
        - option "Light" [selected]
        - option "Dark"
        - option "English" [selected]
        - option "Русский"
        - option "Қазақша"
  - generic [ref=e38]:
    - banner [ref=e39]:
      - generic [ref=e40]: Demo data
      - group [ref=e41]:
        - generic "Explore⌄" [ref=e42] [cursor=pointer]
      - generic [ref=e43]:
        - text: Applicant
        - combobox "Applicant" [ref=e44]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 0 runs" [selected]
      - button "New case" [ref=e45] [cursor=pointer]
      - button "Settings" [ref=e46] [cursor=pointer]
      - button "Sign out" [ref=e47] [cursor=pointer]
    - main "Exam preparation" [ref=e48]:
      - generic [ref=e49]:
        - generic [ref=e50]:
          - paragraph [ref=e51]: ORIGINAL PRACTICE · YOUR CASE
          - heading "Prepare for your next step." [level=1] [ref=e52]
          - paragraph [ref=e53]: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
        - note [ref=e54]:
          - generic [ref=e55]:
            - strong [ref=e56]: Development starter access
            - paragraph [ref=e57]: Original IELTS Reading, SAT Math and SAT Reading & Writing practice units. This is not a full exam course or an official mock test.
            - paragraph [ref=e58]: Local preview access
        - navigation "Preparation views" [ref=e59]:
          - button "Goals & evidence" [ref=e60] [cursor=pointer]
          - button "Study plan" [ref=e61] [cursor=pointer]
          - button "Shared route" [ref=e62] [cursor=pointer]
          - button "Practice" [pressed] [ref=e63] [cursor=pointer]
          - button "Progress" [ref=e64] [cursor=pointer]
        - paragraph [ref=e65]: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
        - generic [ref=e66]:
          - 'heading "Math: linear relations and proportional reasoning" [level=2] [ref=e68]'
          - paragraph [ref=e69]: Original practice. No official IELTS band or SAT scaled score is produced.
          - paragraph [ref=e70]: SAT Math · Original practice unit · Lesson 1 of 3
          - paragraph [ref=e72]: Use a linear equation, a percentage and a rate. These original questions are formative practice, not an adaptive Digital SAT module.
          - generic [ref=e73]:
            - generic [ref=e74]:
              - group "1. A bicycle rental costs 6 units plus 4 units per hour. The total is 22 units. How many hours were rented?" [ref=e75]:
                - generic [ref=e77] [cursor=pointer]:
                  - radio "3" [ref=e78]
                  - text: "3"
                - generic [ref=e79] [cursor=pointer]:
                  - radio "4" [ref=e80]
                  - text: "4"
                - generic [ref=e81] [cursor=pointer]:
                  - radio "7" [ref=e82]
                  - text: "7"
              - group "2. A club has 80 members. Exactly 25% volunteer at an event. How many members volunteer?" [ref=e83]:
                - generic [ref=e85] [cursor=pointer]:
                  - radio "20" [ref=e86]
                  - text: "20"
                - generic [ref=e87] [cursor=pointer]:
                  - radio "25" [ref=e88]
                  - text: "25"
                - generic [ref=e89] [cursor=pointer]:
                  - radio "60" [ref=e90]
                  - text: "60"
              - group "3. A machine packs 18 boxes in 3 minutes at a constant rate. At that rate, how many boxes does it pack in 5 minutes?" [ref=e91]:
                - generic [ref=e93] [cursor=pointer]:
                  - radio "20" [ref=e94]
                  - text: "20"
                - generic [ref=e95] [cursor=pointer]:
                  - radio "27" [ref=e96]
                  - text: "27"
                - generic [ref=e97] [cursor=pointer]:
                  - radio "30" [ref=e98]
                  - text: "30"
            - status [ref=e99]: Answers are not saved until submission succeeds.
            - button "Submit practice" [disabled] [ref=e100]
          - button "Restart lesson with a new attempt" [ref=e101] [cursor=pointer]
```

# Test source

```ts
  1   | /**
  2   |  * The workspace round trip, with authentication actually on.
  3   |  *
  4   |  * Every other spec runs against a backend where `auth_enabled` is false, so
  5   |  * `get_optional_principal` hands back the development principal and the
  6   |  * sign-in screen never appears. That left the whole registered-user path —
  7   |  * the one real deployments use — covered by unit tests only.
  8   |  *
  9   |  * Run with `npm run e2e:auth` (playwright.auth.config.ts). It must not run at
  10  |  * the same time as `npm run e2e`: both bind 5173 and 8099.
  11  |  */
  12  | 
  13  | import { expect, test, type Page } from '@playwright/test';
  14  | import { newSession, openShortlist, shot, waitForResults } from './helpers';
  15  | 
  16  | test.describe.configure({ mode: 'serial' });
  17  | 
  18  | const PASSWORD = 'correct-horse-battery-staple';
  19  | const SIGN_IN = 'Welcome back.';
  20  | 
  21  | // Unique per run: the database persists between runs, and a duplicate email
  22  | // is a 409. Playwright forbids Date.now() in no way, but the worker index and
  23  | // a timestamp together survive a re-run inside the same second.
  24  | const EMAIL = `e2e-${Date.now()}-${process.pid}@ashyq.invalid`;
  25  | 
  26  | let page: Page;
  27  | 
  28  | test.beforeAll(async ({ browser }) => {
  29  |   page = await newSession(browser);
  30  | });
  31  | 
  32  | test.afterAll(async () => {
  33  |   await page.context().close();
  34  | });
  35  | 
  36  | test('the sign-in screen stands in front of the app', async () => {
  37  |   await page.goto('/#/sign-in');
  38  |   // Also the interlock: if this run silently attached to an auth-disabled
  39  |   // backend, the app would render instead and every later assertion would
  40  |   // pass while proving nothing.
  41  |   await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  42  |   await page.screenshot({ path: shot('auth-sign-in.png'), fullPage: true });
  43  | });
  44  | 
  45  | test('a new workspace can be registered', async () => {
  46  |   await page.getByTestId('auth-mode-toggle').click();
  47  |   await expect(page.getByRole('heading', { name: 'Start your journey.' })).toBeVisible();
  48  | 
  49  |   await page.getByTestId('auth-name').fill('E2E Applicant');
  50  |   await page.getByTestId('auth-organization').fill('E2E Workspace');
  51  |   await page.getByTestId('auth-email').fill(EMAIL);
  52  |   await page.getByTestId('auth-password').fill(PASSWORD);
  53  |   await page.getByTestId('auth-submit').click();
  54  | 
  55  |   await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  56  |   await page.getByRole('button', { name: 'Create profile' }).click();
  57  |   await expect(page.getByTestId('to-preferences')).toBeVisible();
  58  | });
  59  | 
  60  | test('the workspace can hold a profile and a finished run', async () => {
  61  |   await page.getByTestId('load-demo-profile').click();
  62  |   const confirm = page.getByTestId('confirm-replace');
  63  |   if (await confirm.isVisible().catch(() => false)) await confirm.click();
  64  |   await page.getByTestId('save-profile').click();
  65  | 
  66  |   await page.goto('/#/preferences');
  67  |   await expect(page.getByTestId('start-research')).toBeEnabled();
  68  |   await page.getByTestId('start-research').click();
  69  |   await waitForResults(page);
  70  | });
  71  | 
  72  | test('original practice persists into a second signed-in browser session', async ({ browser }) => {
  73  |   await page.goto('/#/preparation');
  74  |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  75  |   await page.getByRole('button', { name: 'Start Math: linear relations and proportional reasoning', exact: true }).click();
> 76  |   for (const [index, value] of ['4', '20', '30'].entries()) await page.locator('fieldset').nth(index).getByRole('radio', { name: value, exact: true }).check();
      |                                                                                                                                                        ^ Error: locator.check: Target page, context or browser has been closed
  77  |   const receipt = page.waitForResponse(response => response.request().method() === 'POST' && /\/preparation\/attempts$/.test(new URL(response.url()).pathname));
  78  |   await page.getByRole('button', { name: 'Submit practice', exact: true }).click();
  79  |   const submitted = await receipt;
  80  |   expect(submitted.ok()).toBeTruthy();
  81  |   const attempt = await submitted.json();
  82  |   expect(attempt).toMatchObject({ lesson_id: 'sat-math-1', correct: 3, total: 3 });
  83  |   await expect(page.getByTestId('practice-result')).toHaveText('3 / 3 correct — practice only');
  84  | 
  85  |   const dateAfter = (days: number) => { const date = new Date(); date.setUTCDate(date.getUTCDate() + days); return date.toISOString().slice(0, 10); };
  86  |   const calendar = await page.request.put(`/api/profiles/${attempt.profile_id}/preparation/schedule`, { data: {
  87  |     expected_revision: 0, settings: { exam: 'digital_sat', starts_on: dateAfter(0), certificate_deadline: dateAfter(90),
  88  |       first_exam_on: dateAfter(60), retake_on: null, result_wait_days: 14, delivery_days: 7, safety_days: 7,
  89  |       timezone: 'UTC', weekly_minutes: 180, study_days: [0, 2, 4], target_scores: { total: 1400, math: 700, reading_writing: 700 },
  90  |       baseline_scores: {}, baseline_on: null, confirmed_planning_dates: true, completed_task_ids: [] },
  91  |   } });
  92  |   expect(calendar.status()).toBe(200);
  93  |   const savedCalendar = await calendar.json(); expect(savedCalendar.revision).toBe(1);
  94  | 
  95  |   // Fresh cookies/localStorage: a second session cannot recover an attempt from the first tab.
  96  |   const second = await newSession(browser);
  97  |   try {
  98  |     await second.goto('/#/sign-in');
  99  |     await second.getByTestId('auth-email').fill(EMAIL);
  100 |     await second.getByTestId('auth-password').fill(PASSWORD);
  101 |     await second.getByTestId('auth-submit').click();
  102 |     await expect(second.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  103 |     await second.goto('/#/preparation');
  104 |     await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  105 |     await expect(second.getByTestId('progress-summary')).toContainText('1 saved attempts');
  106 |     const stored = await second.request.get(`/api/profiles/${attempt.profile_id}/preparation/progress`);
  107 |     expect(stored.ok()).toBeTruthy();
  108 |     expect((await stored.json()).attempts[0].attempt_id).toBe(attempt.attempt_id);
  109 |     await second.screenshot({ path: shot('auth-preparation-second-session.png'), fullPage: true });
  110 |     await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  111 |     await expect(second.getByLabel('Total target', { exact: true })).toHaveValue('1400');
  112 |     const restored = await second.request.get(`/api/profiles/${attempt.profile_id}/preparation/schedule`);
  113 |     expect(restored.ok()).toBeTruthy(); expect((await restored.json()).settings).toEqual(savedCalendar.settings);
  114 |     await expect(second.getByText('Readiness: not assessed.', { exact: true })).toBeVisible();
  115 |     await second.getByRole('heading', { name: 'Saved dated tasks', exact: true }).scrollIntoViewIfNeeded();
  116 |     await second.screenshot({ path: shot('auth-study-schedule-second-session.png'), fullPage: false });
  117 | 
  118 |   } finally {
  119 |     await second.context().close();
  120 |   }
  121 | });
  122 | 
  123 | test('signing out returns to the sign-in screen', async () => {
  124 |   await page.getByTestId('sign-out').click();
  125 |   await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  126 | });
  127 | 
  128 | test('signing in again finds the work still there', async () => {
  129 |   await page.getByTestId('auth-email').fill(EMAIL);
  130 |   await page.getByTestId('auth-password').fill(PASSWORD);
  131 |   await page.getByTestId('auth-submit').click();
  132 | 
  133 |   // Asserted against the shortlist rather than the profile form: sign-out
  134 |   // clears the cookie but not localStorage, so a profile could reappear from
  135 |   // the browser alone. Results can only have come back from the server.
  136 |   await openShortlist(page);
  137 |   await expect(page.getByTestId('shortlist-table').locator('tbody tr').first()).toBeVisible();
  138 |   await page.screenshot({ path: shot('auth-after-second-sign-in.png'), fullPage: true });
  139 | });
  140 | 
  141 | test('a session that dies mid-use returns to sign-in, not an error banner', async () => {
  142 |   // The defect this pins: AuthGate asks /api/auth/status once, at mount, and
  143 |   // every later 401 was rendered by the store's `fail` as a topbar banner —
  144 |   // "Something went wrong. Authentication required." — on a screen the user
  145 |   // could no longer act on and could not leave.
  146 |   await page.context().clearCookies();
  147 | 
  148 |   // Saving, not navigating: the screen links are client-side route changes
  149 |   // that render from state already in memory, so they never reach the server
  150 |   // and never learn the session is gone. A write is the first thing the user
  151 |   // does that actually asks.
  152 |   await page.goto('/#/profile');
  153 |   await page.getByTestId('save-profile').click();
  154 | 
  155 |   await expect(page.getByRole('heading', { name: SIGN_IN })).toBeVisible();
  156 |   await expect(page.getByText('Authentication required.')).toBeHidden();
  157 | });
  158 | 
  159 | test('versioned short practice and its accepted feedback survive a fresh signed-in session', async ({ browser }) => {
  160 |   const packVersion = 'learning-pack-2026-10-11-v1';
  161 |   const first = await newSession(browser);
  162 |   let profileId = '';
  163 |   let savedAttemptId = '';
  164 |   let academics: unknown;
  165 |   let calendar: unknown;
  166 |   const signIn = async (session: Page) => {
  167 |     await session.goto('/#/sign-in');
  168 |     await session.getByTestId('auth-email').fill(EMAIL);
  169 |     await session.getByTestId('auth-password').fill(PASSWORD);
  170 |     await session.getByTestId('auth-submit').click();
  171 |     await expect(session.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  172 |   };
  173 |   try {
  174 |     await signIn(first);
  175 |     const response = await first.request.get(`/api/preparation/catalogue?catalogue_version=${packVersion}`);
  176 |     expect(response.ok()).toBeTruthy();
```