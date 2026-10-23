# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: core-admissions.spec.ts >> native core: research, owned records, Today, second session, export and case deletion
- Location: ../../../../../../2026-10-12/g3-execution/source/frontend/e2e/core-admissions.spec.ts:32:1

# Error details

```
Test timeout of 360000ms exceeded.
```

```
Error: locator.getAttribute: Test timeout of 360000ms exceeded.
Call log:
  - waiting for getByLabel('Programme reference', { exact: true }).locator('option').nth(1)

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
      - button "Plan" [ref=e17] [cursor=pointer]:
        - generic [ref=e21]: "2"
      - button "Documents" [ref=e22] [cursor=pointer]
      - button "Community" [ref=e26] [cursor=pointer]
    - navigation "Optional tools" [ref=e30]:
      - paragraph [ref=e31]: Optional tools
      - button "Exam preparation" [ref=e32] [cursor=pointer]
    - generic [ref=e36]:
      - paragraph [ref=e37]:
        - text: Same students.
        - strong [ref=e38]: Bigger horizons.
      - group [ref=e39]:
        - generic "Preferences" [ref=e40] [cursor=pointer]
        - option "Match system"
        - option "Light" [selected]
        - option "Dark"
        - option "English" [selected]
        - option "Русский"
        - option "Қазақша"
  - generic [ref=e41]:
    - banner [ref=e42]:
      - generic [ref=e43]: Demo data
      - group [ref=e44]:
        - generic "Explore⌄" [ref=e45] [cursor=pointer]
      - generic [ref=e46]:
        - text: Applicant
        - combobox "Applicant" [ref=e47]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 0 runs" [selected]
      - button "New case" [ref=e48] [cursor=pointer]
      - button "Settings" [ref=e49] [cursor=pointer]
      - button "Sign out" [ref=e50] [cursor=pointer]
    - main "Approved universities" [ref=e51]:
      - note [ref=e53]:
        - generic [ref=e54]:
          - strong [ref=e55]: Recorded assessment.
          - text: The evaluation reflects the research at that time. It does not establish current readiness or an admission probability.
      - generic [ref=e56]:
        - paragraph [ref=e57]: Your application journey
        - heading "A clearer plan. A brighter you." [level=1] [ref=e58]
        - paragraph [ref=e59]: Keep your chosen programmes together, check their deadlines and prepare what each one asks for. These are your choices, not admission offers.
      - generic [ref=e60]:
        - generic [ref=e61]:
          - generic [ref=e62]:
            - heading "Your saved applications" [level=2] [ref=e64]
            - generic [ref=e65]:
              - paragraph [ref=e66]: Applications work without research or an exam course. Plans and declarations are your personal records.
              - button "Add an application" [ref=e67] [cursor=pointer]
              - article [ref=e68]:
                - heading "Synthetic manual application" [level=3] [ref=e69]
                - paragraph [ref=e70]: Planning
                - paragraph [ref=e71]: Synthetic Unknown University
                - paragraph [ref=e72]: "Your entered context: Unknown · Unknown"
                - paragraph [ref=e73]: Current official requirements are not confirmed here. Your saved application remains available.
                - generic [ref=e74]:
                  - button "Start preparing this application" [ref=e75] [cursor=pointer]
                  - button "Edit date and notes" [ref=e76] [cursor=pointer]
                  - button "Edit application context" [ref=e77] [cursor=pointer]
                  - button "Remove personal record" [ref=e78] [cursor=pointer]
                  - button "Record my submission statement" [ref=e79] [cursor=pointer]
                  - button "Record my withdrawal statement" [ref=e80] [cursor=pointer]
                  - button "History" [ref=e81] [cursor=pointer]
          - generic [ref=e82]:
            - heading "Add an application" [level=2] [ref=e84]
            - generic [ref=e85]:
              - group [ref=e86]:
                - generic [ref=e87]:
                  - text: Application name
                  - textbox "Application name" [active] [ref=e88]: Synthetic core application
                - group [ref=e89]:
                  - generic [ref=e90]:
                    - text: Programme reference
                    - combobox "Programme reference" [ref=e91]:
                      - option "Enter manually · requirements unverified" [selected]
                      - option "University of Groningen · BSc Computing Science"
                      - option "KU Leuven · BSc Informatics"
                  - generic [ref=e92]:
                    - text: University, as entered by you
                    - textbox "University, as entered by you" [ref=e93]
                  - generic [ref=e94]:
                    - text: Programme, if known
                    - textbox "Programme, if known" [ref=e95]
                  - generic [ref=e96]:
                    - text: Application purpose
                    - combobox "Application purpose" [ref=e97]:
                      - option "Admission" [selected]
                      - option "Scholarship"
                  - generic [ref=e98]:
                    - text: Intake, if known
                    - textbox "Intake, if known" [ref=e99]
                  - generic [ref=e100]:
                    - text: Application route, if known
                    - textbox "Application route, if known" [ref=e101]
                - generic [ref=e102]:
                  - text: Your planning date
                  - textbox "Your planning date" [ref=e103]
                - generic [ref=e104]:
                  - text: Time zone
                  - textbox "Time zone" [ref=e105]:
                    - /placeholder: Asia/Almaty
                - paragraph [ref=e106]: Time zone unknown
                - generic [ref=e107]:
                  - text: Your notes
                  - textbox "Your notes" [ref=e108]
                - generic [ref=e109]:
                  - checkbox "I reviewed these personal details and confirm this is my own record." [ref=e110]
                  - text: I reviewed these personal details and confirm this is my own record.
              - generic [ref=e111]:
                - button "Save on server" [disabled] [ref=e112]
                - button "Close editor" [ref=e113] [cursor=pointer]
          - generic [ref=e114]:
            - heading "Save recovery" [level=2] [ref=e116]
            - generic [ref=e117]:
              - paragraph [ref=e118]: If confirmation is lost, keep the original request and retry it explicitly.
              - generic [ref=e119]:
                - generic [ref=e120]:
                  - strong [ref=e121]: Synthetic manual application
                  - generic [ref=e122]: Saving confirmed by the server
                - generic [ref=e123]:
                  - 'checkbox "Select local confirmation: Synthetic manual application" [ref=e124]'
                  - text: Select local confirmation
              - generic [ref=e125]:
                - generic [ref=e126]:
                  - strong [ref=e127]: Synthetic core manual task
                  - generic [ref=e128]: Saving confirmed by the server
                - generic [ref=e129]:
                  - 'checkbox "Select local confirmation: Synthetic core manual task" [ref=e130]'
                  - text: Select local confirmation
              - generic [ref=e131]:
                - paragraph [ref=e132]: Clearing selected local confirmations does not delete saved records or server history. Unresolved requests are kept.
                - button "Clear selected local confirmations" [disabled] [ref=e133]
              - button "Refresh saved records" [ref=e135] [cursor=pointer]
        - generic [ref=e136]:
          - heading "Exam preparation" [level=2] [ref=e138]
          - paragraph [ref=e139]: Optional practice. You can find universities, manage documents and plan applications without using our IELTS or SAT materials. Official exam requirements for a programme still apply.
          - button "Open exam goals & practice" [ref=e140] [cursor=pointer]
        - region "Your next step" [ref=e141]:
          - generic [ref=e142]:
            - generic [ref=e143]: NEXT STEP
            - 'heading "Closest recorded date: KU Leuven" [level=2] [ref=e144]'
            - paragraph [ref=e145]: Mar 01, 2027 · BSc Informatics
            - paragraph [ref=e146]: A calendar date does not establish the closing time. CET
          - generic [ref=e147]:
            - strong [ref=e148]: "2"
            - generic [ref=e149]: programmes in your plan
        - generic [ref=e151]:
          - generic [ref=e152]:
            - generic [ref=e153]: 2 chosen by you
            - generic [ref=e154]: 0 considering
            - generic [ref=e155]: 0 ruled out
            - generic [ref=e156]: 18 undecided
          - button "Collect documents for 2 programmes" [ref=e157] [cursor=pointer]
        - generic [ref=e158]:
          - heading "Chosen by you (2)" [level=2] [ref=e160]
          - generic [ref=e161]:
            - generic [ref=e162]:
              - generic [ref=e163]:
                - generic [ref=e164]:
                  - generic [ref=e165]: University of Groningen
                  - generic [ref=e166]: BSc Computing Science · Groningen, Netherlands
                - generic [ref=e167]:
                  - generic [ref=e168]: Chosen by you
                  - button "Undo" [ref=e169] [cursor=pointer]
              - generic [ref=e170]:
                - generic "Nothing is failing, but something is still outstanding — a test, a document, or a profile field." [ref=e171]: Pending
                - generic "An official source confirms tuition, mandatory fees, housing and meals (or a living stipend) are covered." [ref=e172]: Full ride
                - generic [ref=e173]: remaining 1,848 USD · 2026/27
                - generic [ref=e174]: deadline May 01, 2027
            - generic [ref=e175]:
              - generic [ref=e176]:
                - generic [ref=e177]:
                  - generic [ref=e178]: KU Leuven
                  - generic [ref=e179]: BSc Informatics · Leuven, Belgium
                - generic [ref=e180]:
                  - generic [ref=e181]: Chosen by you
                  - button "Undo" [ref=e182] [cursor=pointer]
              - generic [ref=e183]:
                - generic "Every published requirement that could be checked is satisfied." [ref=e184]: Met
                - generic "Tuition is covered. Living costs are not fully covered." [ref=e185]: Full tuition
                - generic [ref=e186]: remaining 7,554 USD · 2026/27
                - generic [ref=e187]: deadline Mar 01, 2027
```

# Test source

```ts
  1   | /** Actual owned API + isolated synthetic DB; no response/receipt fabrication. */
  2   | import { test, expect, type Page } from '@playwright/test';
  3   | import { openShortlist, waitForResults } from './helpers';
  4   | 
  5   | const auth = process.env.CORE_NATIVE_AUTH === 'true';
  6   | const EMAIL = `core-${Date.now()}-${process.pid}@ashyq.invalid`;
  7   | const PASSWORD = 'synthetic-core-passphrase-2026';
  8   | async function login(page: Page) {
  9   |   await page.goto('/#/sign-in');
  10  |   await page.getByTestId('auth-email').fill(EMAIL);
  11  |   await page.getByTestId('auth-password').fill(PASSWORD);
  12  |   await page.getByTestId('auth-submit').click();
  13  |   await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  14  | }
  15  | async function save(page: Page) {
  16  |   const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  17  |   await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  18  |   const accepted = await response;
  19  |   expect(accepted.status()).toBe(200);
  20  |   return accepted.json();
  21  | }
  22  | async function addTask(page: Page, name: string, application?: string) {
  23  |   await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  24  |   await page.getByLabel('Task name', { exact: true }).fill(name);
  25  |   if (application) await page.getByLabel('Linked application', { exact: true }).selectOption(application);
  26  |   await page.getByLabel('Your planning date', { exact: true }).fill('2026-10-20');
  27  |   const receipt = await save(page);
  28  |   await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  29  |   return receipt.applied_delta.document_tasks[0];
  30  | }
  31  | 
  32  | test('native core: research, owned records, Today, second session, export and case deletion', async ({ page, browser }, info) => {
  33  |   test.setTimeout(360_000);
  34  |   const requests: { method: string; path: string; status: number }[] = [];
  35  |   page.on('response', response => { const path = new URL(response.url()).pathname; if (path.startsWith('/api/')) requests.push({ method: response.request().method(), path, status: response.status() }); });
  36  |   if (auth) {
  37  |     await page.goto('/#/sign-in');
  38  |     await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  39  |     await page.getByTestId('auth-mode-toggle').click();
  40  |     await page.getByTestId('auth-name').fill('Synthetic Core Applicant');
  41  |     await page.getByTestId('auth-organization').fill('Synthetic Core Workspace');
  42  |     await page.getByTestId('auth-email').fill(EMAIL);
  43  |     await page.getByTestId('auth-password').fill(PASSWORD);
  44  |     await page.getByTestId('auth-submit').click();
  45  |     await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  46  |   }
  47  |   await page.goto('/#/profile');
  48  |   await page.getByTestId('load-demo-profile').click();
  49  |   const replacement = page.getByTestId('confirm-replace');
  50  |   if (await replacement.isVisible().catch(() => false)) await replacement.click();
  51  |   const saved = page.waitForResponse(r => ['POST', 'PUT'].includes(r.request().method()) && /\/api\/profiles(?:\/[^/]+)?$/.test(new URL(r.url()).pathname));
  52  |   await page.getByTestId('save-profile').click();
  53  |   const profileResponse = await saved; expect(profileResponse.ok()).toBeTruthy();
  54  |   const profile = await profileResponse.json();
  55  |   const endpoint = `/api/profiles/${profile.id}/admissions-actions`;
  56  |   await page.goto('/#/documents');
  57  |   const manual = await addTask(page, 'Synthetic core manual task');
  58  |   expect(manual.binding).toBeNull();
  59  |   await page.goto('/#/approved');
  60  |   await page.getByRole('button', { name: 'Add an application', exact: true }).click();
  61  |   await page.getByLabel('Application name', { exact: true }).fill('Synthetic manual application');
  62  |   await page.getByLabel('University, as entered by you', { exact: true }).fill('Synthetic Unknown University');
  63  |   await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  64  |   const manualApp = await save(page);
  65  |   expect(manualApp.applied_delta.applications[0].target.result_id).toBeNull();
  66  |   await page.goto('/#/preferences');
  67  |   await expect(page.getByTestId('start-research')).toBeEnabled();
  68  |   await page.getByTestId('start-research').click();
  69  |   await waitForResults(page);
  70  |   await openShortlist(page);
  71  |   const rows = page.locator('tbody tr').filter({ has: page.locator('.decision-btn--approve') });
  72  |   for (let i = 0; i < 2; i++) {
  73  |     const decision = page.waitForResponse(r => r.request().method() === 'POST' && /\/decision$/.test(new URL(r.url()).pathname));
  74  |     await rows.nth(i).locator('.decision-btn--approve').click(); expect((await decision).ok()).toBeTruthy();
  75  |   }
  76  |   await page.goto('/#/approved');
  77  |   await page.getByRole('button', { name: 'Add an application', exact: true }).click();
  78  |   await page.getByLabel('Application name', { exact: true }).fill('Synthetic core application');
  79  |   const selector = page.getByLabel('Programme reference', { exact: true });
> 80  |   const selected = await selector.locator('option').nth(1).getAttribute('value'); expect(selected).toBeTruthy();
      |                                                            ^ Error: locator.getAttribute: Test timeout of 360000ms exceeded.
  81  |   await selector.selectOption(selected!);
  82  |   await page.getByLabel('Intake, if known', { exact: true }).fill('Synthetic fall 2027');
  83  |   await page.getByLabel('Application route, if known', { exact: true }).fill('Synthetic own portal');
  84  |   await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  85  |   const created = await save(page); const appId = created.applied_delta.applications[0].id;
  86  |   await expect(page.getByRole('heading', { name: 'Synthetic core application', exact: true })).toBeVisible();
  87  |   const applicationCard = page.getByTestId('personal-application').filter({ has: page.getByRole('heading', { name: 'Synthetic core application', exact: true }) });
  88  |   await applicationCard.getByRole('button', { name: 'Start preparing this application', exact: true }).click();
  89  |   await expect(applicationCard).toContainText('Preparing');
  90  |   await applicationCard.getByRole('button', { name: 'Record my submission statement', exact: true }).click();
  91  |   await page.getByLabel('Your event date, if known', { exact: true }).fill('2026-10-14');
  92  |   await page.getByLabel('Submission channel, as entered by you', { exact: true }).fill('Synthetic own declaration');
  93  |   await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  94  |   await save(page); await expect(applicationCard).toContainText('Submission · declared by you');
  95  |   await applicationCard.getByRole('button', { name: 'History', exact: true }).click();
  96  |   await page.getByRole('button', { name: 'Correct this declaration', exact: true }).click();
  97  |   await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  98  |   await save(page); await expect(applicationCard).toContainText('Preparing');
  99  |   await page.goto('/#/documents');
  100 |   const linked = await addTask(page, 'Synthetic core linked task', appId);
  101 |   const occurrence = page.getByLabel('Choose a programme requirement', { exact: true });
  102 |   await expect(occurrence.locator('option')).not.toHaveCount(1);
  103 |   await occurrence.selectOption((await occurrence.locator('option').nth(1).getAttribute('value'))!);
  104 |   await page.getByLabel('Task to link', { exact: true }).selectOption(linked.id);
  105 |   await page.getByRole('button', { name: 'Review current requirement', exact: true }).click();
  106 |   const bind = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  107 |   await page.getByRole('button', { name: 'Save reviewed requirement link', exact: true }).click();
  108 |   expect((await bind).status()).toBe(200);
  109 |   const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: 'Synthetic core linked task', exact: true }) });
  110 |   await card.getByRole('button', { name: 'Update personal status', exact: true }).click();
  111 |   await page.getByLabel('Your reported status', { exact: true }).selectOption('prepared_reported');
  112 |   await page.getByRole('checkbox', { name: 'I confirm this is my own report, not an official university confirmation.', exact: true }).check();
  113 |   await save(page); await expect(card).toContainText('Prepared · self-reported');
  114 |   await page.goto('/#/home');
  115 |   const today = page.getByTestId('admissions-today');
  116 |   await expect(today.getByRole('heading', { name: 'Synthetic core manual task', exact: true })).toBeVisible();
  117 |   await today.getByTestId('today-action').filter({ has: page.getByRole('heading', { name: 'Synthetic core manual task', exact: true }) }).getByRole('link', { name: 'Open this record', exact: true }).click();
  118 |   await expect(page.getByLabel('Task name', { exact: true })).toHaveValue('Synthetic core manual task');
  119 |   await page.getByLabel('Task name', { exact: true }).fill('Synthetic core renamed task');
  120 |   await page.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
  121 |   await save(page);
  122 |   await page.reload(); await expect(page.getByRole('heading', { name: 'Synthetic core renamed task', exact: true }).first()).toBeVisible();
  123 |   for (const width of [320, 768, 1024, 1440]) {
  124 |     await page.setViewportSize({ width, height: 900 });
  125 |     await expect(page.getByRole('button', { name: 'Add a document task', exact: true })).toBeEnabled();
  126 |     expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  127 |     await page.screenshot({ path: info.outputPath(`documents-${width}.png`), fullPage: true });
  128 |   }
  129 |   const secondContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  130 |   const second = await secondContext.newPage();
  131 |   try {
  132 |     if (auth) await login(second); else await second.goto('/#/home');
  133 |     await second.goto('/#/documents');
  134 |     await expect(second.getByRole('heading', { name: 'Synthetic core renamed task', exact: true })).toBeVisible();
  135 |     const native = await second.request.get(endpoint); expect(native.status()).toBe(200);
  136 |     const state = await native.json(); expect(state.state.applications.some((app: {id: string}) => app.id === appId)).toBe(true);
  137 |     expect(state.state.document_tasks.find((task: {id: string}) => task.id === linked.id).binding).not.toBeNull();
  138 |     await second.screenshot({ path: info.outputPath('second-browser-native-documents.png'), fullPage: true });
  139 |   } finally { await secondContext.close(); }
  140 |   if (auth) {
  141 |     await page.getByTestId('sign-out').click(); await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  142 |     await login(page); await page.goto('/#/approved');
  143 |     await expect(page.getByRole('heading', { name: 'Synthetic core application', exact: true })).toBeVisible();
  144 |   }
  145 |   await page.goto('/#/export');
  146 |   const exported = page.waitForResponse(r => r.request().method() === 'GET' && /\/export$/.test(new URL(r.url()).pathname));
  147 |   await page.getByTestId('export-profile').click(); const data = await exported; expect(data.ok()).toBeTruthy();
  148 |   const exportBody = await data.json(); expect(JSON.stringify(exportBody)).toContain('Synthetic core renamed task');
  149 |   await page.getByTestId('delete-confirm').fill('DELETE');
  150 |   const deleted = page.waitForResponse(r => r.request().method() === 'DELETE' && new URL(r.url()).pathname === `/api/profiles/${profile.id}`);
  151 |   await page.getByTestId('delete-everything').click(); expect((await deleted).ok()).toBeTruthy();
  152 |   expect((await page.request.get(endpoint)).status()).toBe(404);
  153 |   await info.attach('native-api-statuses.json', { body: JSON.stringify({ auth, profile_id: profile.id, requests }, null, 2), contentType: 'application/json' });
  154 | });
  155 | 
```