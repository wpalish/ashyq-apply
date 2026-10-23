# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: core-admissions.spec.ts >> native core: research, owned records, Today, second session, export and case deletion
- Location: ../../../../../../2026-10-12/g3-execution/source/frontend/e2e/core-admissions.spec.ts:32:1

# Error details

```
Error: expect(locator).not.toHaveCount(expected) failed

Locator:  getByRole('combobox', { name: 'Choose a programme requirement', exact: true }).locator('option')
Expected: not 1
Received: 1
Timeout:  20000ms

Call log:
  - Expect "not toHaveCount" with timeout 20000ms
  - waiting for getByRole('combobox', { name: 'Choose a programme requirement', exact: true }).locator('option')
    44 × locator resolved to 1 element
       - unexpected value "1"

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
    - main "Documents & deadlines" [ref=e51]:
      - note [ref=e53]:
        - generic [ref=e54]:
          - strong [ref=e55]: Recorded assessment.
          - text: The evaluation reflects the research at that time. It does not establish current readiness or an admission probability.
      - generic [ref=e56]:
        - paragraph [ref=e57]: Documents & deadlines
        - heading "Prepare with confidence." [level=1] [ref=e58]
        - paragraph [ref=e59]: Ordered by lead time, not by deadline. The items at the top depend on other people, so they are the ones that need starting first.
      - generic [ref=e60]:
        - generic [ref=e61]:
          - generic [ref=e62]:
            - heading "Your saved document tasks" [level=2] [ref=e64]
            - generic [ref=e65]:
              - paragraph [ref=e66]: Personal tasks are saved on the server and work without a research result or an exam course.
              - note [ref=e67]: Saving confirmed by the server. This is your personal record.
              - button "Add a document task" [ref=e68] [cursor=pointer]
              - article [ref=e69]:
                - heading "Synthetic core manual task" [level=3] [ref=e70]
                - generic [ref=e71]: You · Not started
                - generic [ref=e72]: "Your planning date: 2026-10-20 · Time zone unknown"
                - generic [ref=e73]: A personal report is not university verification or proof of an official submission.
                - generic [ref=e74]:
                  - button "Edit document details" [ref=e75] [cursor=pointer]
                  - button "Update personal status" [ref=e76] [cursor=pointer]
                  - button "Remove personal record" [ref=e77] [cursor=pointer]
                  - button "History" [ref=e78] [cursor=pointer]
              - article [ref=e79]:
                - heading "Synthetic core linked task" [level=3] [ref=e80]
                - generic [ref=e81]: You · Not started
                - generic [ref=e82]: "Your planning date: 2026-10-20 · Time zone unknown"
                - generic [ref=e83]: A personal report is not university verification or proof of an official submission.
                - generic [ref=e84]:
                  - button "Edit document details" [ref=e85] [cursor=pointer]
                  - button "Update personal status" [ref=e86] [cursor=pointer]
                  - button "Remove personal record" [ref=e87] [cursor=pointer]
                  - button "History" [ref=e88] [cursor=pointer]
          - generic [ref=e89]:
            - heading "Link an exact requirement" [level=2] [ref=e91]
            - generic [ref=e92]:
              - paragraph [ref=e93]: Choose one original requirement occurrence from a selected programme. Identical names are not merged.
              - paragraph [ref=e94]: No requirement references from this loaded case are available. You can still create a personal task.
              - generic [ref=e95]:
                - text: Choose a programme requirement
                - combobox "Choose a programme requirement" [ref=e96]:
                  - option "Choose a programme requirement" [selected]
              - generic [ref=e97]:
                - text: Task to link
                - combobox "Task to link" [ref=e98]:
                  - option "Create a new linked task" [selected]
                  - option "Synthetic core manual task"
              - button "Review current requirement" [disabled] [ref=e99]
          - generic [ref=e100]:
            - heading "Review earlier browser marks" [level=2] [ref=e102]
            - generic [ref=e103]:
              - paragraph [ref=e104]: Only unambiguous marks from this loaded case can be offered. Choose your own unreported task and confirm the mapping. Source version and original reporting time remain unknown.
              - button "Read marks for this case" [ref=e105] [cursor=pointer]
          - generic [ref=e106]:
            - heading "Save recovery" [level=2] [ref=e108]
            - generic [ref=e109]:
              - paragraph [ref=e110]: If confirmation is lost, keep the original request and retry it explicitly.
              - generic [ref=e111]:
                - generic [ref=e112]:
                  - strong [ref=e113]: Synthetic core linked task
                  - generic [ref=e114]: Saving confirmed by the server
                - generic [ref=e115]:
                  - 'checkbox "Select local confirmation: Synthetic core linked task" [ref=e116]'
                  - text: Select local confirmation
              - generic [ref=e117]:
                - generic [ref=e118]:
                  - strong [ref=e119]: Correct a declaration
                  - generic [ref=e120]: Saving confirmed by the server
                - generic [ref=e121]:
                  - 'checkbox "Select local confirmation: Correct a declaration" [ref=e122]'
                  - text: Select local confirmation
              - generic [ref=e123]:
                - generic [ref=e124]:
                  - strong [ref=e125]: Update application plan
                  - generic [ref=e126]: Saving confirmed by the server
                - generic [ref=e127]:
                  - 'checkbox "Select local confirmation: Update application plan" [ref=e128]'
                  - text: Select local confirmation
              - generic [ref=e129]:
                - generic [ref=e130]:
                  - strong [ref=e131]: Synthetic core application
                  - generic [ref=e132]: Saving confirmed by the server
                - generic [ref=e133]:
                  - 'checkbox "Select local confirmation: Synthetic core application" [ref=e134]'
                  - text: Select local confirmation
              - generic [ref=e135]:
                - generic [ref=e136]:
                  - strong [ref=e137]: Synthetic manual application
                  - generic [ref=e138]: Saving confirmed by the server
                - generic [ref=e139]:
                  - 'checkbox "Select local confirmation: Synthetic manual application" [ref=e140]'
                  - text: Select local confirmation
              - generic [ref=e141]:
                - generic [ref=e142]:
                  - strong [ref=e143]: Declare a submission
                  - generic [ref=e144]: Saving confirmed by the server
                - generic [ref=e145]:
                  - 'checkbox "Select local confirmation: Declare a submission" [ref=e146]'
                  - text: Select local confirmation
              - generic [ref=e147]:
                - generic [ref=e148]:
                  - strong [ref=e149]: Synthetic core manual task
                  - generic [ref=e150]: Saving confirmed by the server
                - generic [ref=e151]:
                  - 'checkbox "Select local confirmation: Synthetic core manual task" [ref=e152]'
                  - text: Select local confirmation
              - generic [ref=e153]:
                - paragraph [ref=e154]: Clearing selected local confirmations does not delete saved records or server history. Unresolved requests are kept.
                - button "Clear selected local confirmations" [disabled] [ref=e155]
              - button "Refresh saved records" [ref=e157] [cursor=pointer]
        - note [ref=e158]: The earlier checklist marks below are browser-only notes. They are not saved server tasks or official readiness; transfer requires your explicit review.
        - generic [ref=e159]:
          - generic [ref=e160]:
            - paragraph [ref=e161]: No checklists yet
            - text: Collect official requirements for your selected programmes from Plan.
          - button "Open plan" [ref=e162] [cursor=pointer]
        - group [ref=e163]:
          - generic "Calendar and deadlines across your shortlist (24)" [ref=e164] [cursor=pointer]
          - generic [ref=e165]:
            - generic [ref=e166]:
              - heading "Every deadline across your shortlist" [level=2] [ref=e167]
              - link "Add to calendar (.ics)" [ref=e168] [cursor=pointer]:
                - /url: /api/runs/bf16d3aa7eb84cadb43b32dcefff6dde/deadlines.ics
            - paragraph [ref=e169]: Calendar dates have no confirmed closing time here. An unknown time zone prevents a precise expiry comparison.
            - generic [ref=e170]:
              - generic [ref=e171]:
                - generic [ref=e172]: Jan 15, 2026
                - generic [ref=e173]:
                  - strong [ref=e175]: Melbourne International Undergraduate Scholarship
                  - generic [ref=e176]: University of Melbourne
              - generic [ref=e177]:
                - generic [ref=e178]: Oct 15, 2026
                - generic [ref=e179]:
                  - strong [ref=e181]: Deutschlandstipendium
                  - generic [ref=e182]: Technical University of Munich
              - generic [ref=e183]:
                - generic [ref=e184]: Nov 01, 2026
                - generic [ref=e185]:
                  - strong [ref=e187]: MEXT Undergraduate Scholarship (University Recommendation)
                  - generic [ref=e188]: University of Tokyo
              - generic [ref=e189]:
                - generic [ref=e190]: Nov 15, 2026
                - generic [ref=e191]:
                  - strong [ref=e193]: Lester B. Pearson International Scholarship
                  - generic [ref=e194]: University of Toronto
              - generic [ref=e195]:
                - generic [ref=e196]: Dec 01, 2026
                - generic [ref=e197]:
                  - strong [ref=e199]: Admission application (JST)
                  - generic [ref=e200]: University of Tokyo — PEAK Environmental Sciences (Computing track)
              - generic [ref=e201]:
                - generic [ref=e202]: Dec 01, 2026
                - generic [ref=e203]:
                  - strong [ref=e205]: Justus & Louise van Effen Excellence Scholarship
                  - generic [ref=e206]: Delft University of Technology
              - generic [ref=e207]:
                - generic [ref=e208]: Dec 15, 2026
                - generic [ref=e209]:
                  - strong [ref=e211]: EPFL Excellence Fellowship
                  - generic [ref=e212]: EPFL
              - generic [ref=e213]:
                - generic [ref=e214]: Jan 09, 2027
                - generic [ref=e215]:
                  - strong [ref=e217]: Admission application (EET)
                  - generic [ref=e218]: Aalto University — BSc Computer Science
              - generic [ref=e219]:
                - generic [ref=e220]: Jan 15, 2027
                - generic [ref=e221]:
                  - strong [ref=e223]: Admission application (EST)
                  - generic [ref=e224]: University of Toronto — HBSc Computer Science
              - generic [ref=e225]:
                - generic [ref=e226]: Jan 15, 2027
                - generic [ref=e227]:
                  - strong [ref=e229]: Admission application (PST)
                  - generic [ref=e230]: University of British Columbia — BSc Computer Science
              - generic [ref=e231]:
                - generic [ref=e232]: Jan 15, 2027
                - generic [ref=e233]:
                  - strong [ref=e235]: Admission application (CET)
                  - generic [ref=e236]: Technical University of Munich — BSc Informatics
              - generic [ref=e237]:
                - generic [ref=e238]: Jan 15, 2027
                - generic [ref=e239]:
                  - strong [ref=e241]: Admission application (CET)
                  - generic [ref=e242]: Delft University of Technology — BSc Computer Science and Engineering
              - generic [ref=e243]:
                - generic [ref=e244]: Jan 15, 2027
                - generic [ref=e245]:
                  - strong [ref=e247]: Admission application (CET)
                  - generic [ref=e248]: EPFL — BSc Computer Science
              - generic [ref=e249]:
                - generic [ref=e250]: Feb 01, 2027
                - generic [ref=e251]:
                  - strong [ref=e253]: Groningen Talent Grant
                  - generic [ref=e254]: University of Groningen
              - generic [ref=e255]:
                - generic [ref=e256]: Feb 01, 2027
                - generic [ref=e257]:
                  - strong [ref=e259]: Science@Leuven Scholarship
                  - generic [ref=e260]: KU Leuven
              - generic [ref=e261]:
                - generic [ref=e262]: Feb 01, 2027
                - generic [ref=e263]:
                  - strong [ref=e265]: Admission application (MST)
                  - generic [ref=e266]: Arizona State University — BS Computer Science
              - generic [ref=e267]:
                - generic [ref=e268]: Feb 01, 2027
                - generic [ref=e269]:
                  - strong [ref=e271]: Admission application (GMT)
                  - generic [ref=e272]: Trinity College Dublin — BA (Mod) Computer Science
              - generic [ref=e273]:
                - generic [ref=e274]: Feb 21, 2027
                - generic [ref=e275]:
                  - strong [ref=e277]: Admission application (SGT)
                  - generic [ref=e278]: National University of Singapore — Bachelor of Computing (Computer Science)
              - generic [ref=e279]:
                - generic [ref=e280]: Mar 01, 2027
                - generic [ref=e281]:
                  - strong [ref=e283]: Admission application (CET)
                  - generic [ref=e284]: KU Leuven — BSc Informatics
              - generic [ref=e285]:
                - generic [ref=e286]: Mar 31, 2027
                - generic [ref=e287]:
                  - strong [ref=e289]: NUS Financial Aid for International Students
                  - generic [ref=e290]: National University of Singapore
              - generic [ref=e291]:
                - generic [ref=e292]: May 01, 2027
                - generic [ref=e293]:
                  - strong [ref=e295]: Admission application (CET)
                  - generic [ref=e296]: University of Groningen — BSc Computing Science
              - generic [ref=e297]:
                - generic [ref=e298]: Jul 05, 2027
                - generic [ref=e299]:
                  - strong [ref=e301]: Admission application (CET)
                  - generic [ref=e302]: University of Warsaw — BSc Computer Science
              - generic [ref=e303]:
                - generic [ref=e304]: Sep 05, 2027
                - generic [ref=e305]:
                  - strong [ref=e307]: Admission application (CET)
                  - generic [ref=e308]: University of Vienna — BSc Computer Science
              - generic [ref=e309]:
                - generic [ref=e310]: Oct 10, 2027
                - generic [ref=e311]:
                  - strong [ref=e313]: Rector's Scholarship for Best Students
                  - generic [ref=e314]: University of Warsaw
```

# Test source

```ts
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
  25  |   if (application) await page.getByRole('combobox', { name: 'Linked application', exact: true }).selectOption(application);
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
  79  |   const selector = page.getByRole('combobox', { name: 'Programme reference', exact: true });
  80  |   const selected = await selector.locator('option').nth(1).getAttribute('value'); expect(selected).toBeTruthy();
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
  101 |   const occurrence = page.getByRole('combobox', { name: 'Choose a programme requirement', exact: true });
> 102 |   await expect(occurrence.locator('option')).not.toHaveCount(1);
      |                                                  ^ Error: expect(locator).not.toHaveCount(expected) failed
  103 |   await occurrence.selectOption((await occurrence.locator('option').nth(1).getAttribute('value'))!);
  104 |   await page.getByRole('combobox', { name: 'Task to link', exact: true }).selectOption(linked.id);
  105 |   await page.getByRole('button', { name: 'Review current requirement', exact: true }).click();
  106 |   const bind = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  107 |   await page.getByRole('button', { name: 'Save reviewed requirement link', exact: true }).click();
  108 |   expect((await bind).status()).toBe(200);
  109 |   const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: 'Synthetic core linked task', exact: true }) });
  110 |   await card.getByRole('button', { name: 'Update personal status', exact: true }).click();
  111 |   await page.getByRole('combobox', { name: 'Your reported status', exact: true }).selectOption('prepared_reported');
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