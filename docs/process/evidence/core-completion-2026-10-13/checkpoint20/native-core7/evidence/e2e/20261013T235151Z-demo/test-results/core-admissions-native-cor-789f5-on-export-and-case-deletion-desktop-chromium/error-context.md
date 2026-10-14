# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: core-admissions.spec.ts >> native core: research, owned records, Today, second session, export and case deletion
- Location: ../../../../../../2026-10-12/g3-execution/source/frontend/e2e/core-admissions.spec.ts:32:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Synthetic core renamed task', exact: true })
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for getByRole('heading', { name: 'Synthetic core renamed task', exact: true })

```

```yaml
- complementary:
  - text: Unimatch
  - navigation "Main navigation":
    - button "Home"
    - button "Find"
    - button "Plan"
    - button "Documents"
    - button "Community"
  - navigation "Optional tools":
    - paragraph: Optional tools
    - button "Exam preparation"
  - paragraph:
    - text: Same students.
    - strong: Bigger horizons.
  - group: Preferences
- banner:
  - text: Demo data
  - group: Explore⌄
  - text: Applicant
  - combobox "Applicant":
    - option "New applicant" [selected]
    - option "Demo Applicant (synthetic) · 1 run"
  - button "New case"
  - button "Settings"
  - button "Sign out"
- main "Documents & deadlines":
  - paragraph: Documents & deadlines
  - heading "Prepare with confidence." [level=1]
  - paragraph: Ordered by lead time, not by deadline. The items at the top depend on other people, so they are the ones that need starting first.
  - note: Save or select your applicant case to create document tasks.
  - note: The earlier checklist marks below are browser-only notes. They are not saved server tasks or official readiness; transfer requires your explicit review.
  - paragraph: No checklists yet
  - text: Choose a programme in Find, then collect its official requirements from Plan.
  - button "Choose programmes"
```

# Test source

```ts
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
  99  |   await page.getByTestId('collect-documents').click();
  100 |   await page.goto('/#/documents');
  101 |   const linked = await addTask(page, 'Synthetic core linked task', appId);
  102 |   const occurrence = page.getByRole('combobox', { name: 'Choose a programme requirement', exact: true });
  103 |   await expect(occurrence.locator('option')).not.toHaveCount(1);
  104 |   await occurrence.selectOption((await occurrence.locator('option').nth(1).getAttribute('value'))!);
  105 |   await page.getByRole('combobox', { name: 'Task to link', exact: true }).selectOption(linked.id);
  106 |   await page.getByRole('button', { name: 'Review current requirement', exact: true }).click();
  107 |   const bind = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  108 |   await page.getByRole('button', { name: 'Save reviewed requirement link', exact: true }).click();
  109 |   expect((await bind).status()).toBe(200);
  110 |   const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: 'Synthetic core linked task', exact: true }) });
  111 |   await card.getByRole('button', { name: 'Update personal status', exact: true }).click();
  112 |   await page.getByRole('combobox', { name: 'Your reported status', exact: true }).selectOption('prepared_reported');
  113 |   await page.getByRole('checkbox', { name: 'I confirm this is my own report, not an official university confirmation.', exact: true }).check();
  114 |   await save(page); await expect(card).toContainText('Prepared · self-reported');
  115 |   await page.goto('/#/home');
  116 |   const today = page.getByTestId('admissions-today');
  117 |   await expect(today.getByRole('heading', { name: 'Synthetic core manual task', exact: true })).toBeVisible();
  118 |   await today.getByTestId('today-action').filter({ has: page.getByRole('heading', { name: 'Synthetic core manual task', exact: true }) }).getByRole('link', { name: 'Open this record', exact: true }).click();
  119 |   await expect(page.getByLabel('Task name', { exact: true })).toHaveValue('Synthetic core manual task');
  120 |   await page.getByLabel('Task name', { exact: true }).fill('Synthetic core renamed task');
  121 |   await page.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
  122 |   await save(page);
  123 |   await page.reload(); await expect(page.getByRole('heading', { name: 'Synthetic core renamed task', exact: true }).first()).toBeVisible();
  124 |   for (const width of [320, 768, 1024, 1440]) {
  125 |     await page.setViewportSize({ width, height: 900 });
  126 |     await expect(page.getByRole('button', { name: 'Add a document task', exact: true })).toBeEnabled();
  127 |     expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  128 |     await page.screenshot({ path: info.outputPath(`documents-${width}.png`), fullPage: true });
  129 |   }
  130 |   const secondContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  131 |   const second = await secondContext.newPage();
  132 |   try {
  133 |     if (auth) await login(second); else await second.goto('/#/home');
  134 |     await second.goto('/#/documents');
> 135 |     await expect(second.getByRole('heading', { name: 'Synthetic core renamed task', exact: true })).toBeVisible();
      |                                                                                                     ^ Error: expect(locator).toBeVisible() failed
  136 |     const native = await second.request.get(endpoint); expect(native.status()).toBe(200);
  137 |     const state = await native.json(); expect(state.state.applications.some((app: {id: string}) => app.id === appId)).toBe(true);
  138 |     expect(state.state.document_tasks.find((task: {id: string}) => task.id === linked.id).binding).not.toBeNull();
  139 |     await second.screenshot({ path: info.outputPath('second-browser-native-documents.png'), fullPage: true });
  140 |   } finally { await secondContext.close(); }
  141 |   if (auth) {
  142 |     await page.getByTestId('sign-out').click(); await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  143 |     await login(page); await page.goto('/#/approved');
  144 |     await expect(page.getByRole('heading', { name: 'Synthetic core application', exact: true })).toBeVisible();
  145 |   }
  146 |   await page.goto('/#/export');
  147 |   const exported = page.waitForResponse(r => r.request().method() === 'GET' && /\/export$/.test(new URL(r.url()).pathname));
  148 |   await page.getByTestId('export-profile').click(); const data = await exported; expect(data.ok()).toBeTruthy();
  149 |   const exportBody = await data.json(); expect(JSON.stringify(exportBody)).toContain('Synthetic core renamed task');
  150 |   await page.getByTestId('delete-confirm').fill('DELETE');
  151 |   const deleted = page.waitForResponse(r => r.request().method() === 'DELETE' && new URL(r.url()).pathname === `/api/profiles/${profile.id}`);
  152 |   await page.getByTestId('delete-everything').click(); expect((await deleted).ok()).toBeTruthy();
  153 |   expect((await page.request.get(endpoint)).status()).toBe(404);
  154 |   await info.attach('native-api-statuses.json', { body: JSON.stringify({ auth, profile_id: profile.id, requests }, null, 2), contentType: 'application/json' });
  155 | });
  156 | 
```