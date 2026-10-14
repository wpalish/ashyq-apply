/** Actual owned API + isolated synthetic DB; no response/receipt fabrication. */
import { test, expect, type Page } from '@playwright/test';
import { openShortlist, waitForResults } from './helpers';

const auth = process.env.CORE_NATIVE_AUTH === 'true';
const EMAIL = `core-${Date.now()}-${process.pid}@ashyq.invalid`;
const PASSWORD = 'synthetic-core-passphrase-2026';
async function login(page: Page) {
  await page.goto('/#/sign-in');
  await page.getByTestId('auth-email').fill(EMAIL);
  await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click();
  await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
}
async function save(page: Page) {
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  const accepted = await response;
  expect(accepted.status()).toBe(200);
  return accepted.json();
}
async function addTask(page: Page, name: string, application?: string) {
  await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  await page.getByLabel('Task name', { exact: true }).fill(name);
  if (application) await page.getByRole('combobox', { name: 'Linked application', exact: true }).selectOption(application);
  await page.getByLabel('Your planning date', { exact: true }).fill('2026-10-20');
  const receipt = await save(page);
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  return receipt.applied_delta.document_tasks[0];
}

test('native core: research, owned records, Today, second session, export and case deletion', async ({ page, browser }, info) => {
  test.setTimeout(360_000);
  const requests: { method: string; path: string; status: number }[] = [];
  page.on('response', response => { const path = new URL(response.url()).pathname; if (path.startsWith('/api/')) requests.push({ method: response.request().method(), path, status: response.status() }); });
  if (auth) {
    await page.goto('/#/sign-in');
    await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
    await page.getByTestId('auth-mode-toggle').click();
    await page.getByTestId('auth-name').fill('Synthetic Core Applicant');
    await page.getByTestId('auth-organization').fill('Synthetic Core Workspace');
    await page.getByTestId('auth-email').fill(EMAIL);
    await page.getByTestId('auth-password').fill(PASSWORD);
    await page.getByTestId('auth-submit').click();
    await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  }
  await page.goto('/#/profile');
  await page.getByTestId('load-demo-profile').click();
  const replacement = page.getByTestId('confirm-replace');
  if (await replacement.isVisible().catch(() => false)) await replacement.click();
  const saved = page.waitForResponse(r => ['POST', 'PUT'].includes(r.request().method()) && /\/api\/profiles(?:\/[^/]+)?$/.test(new URL(r.url()).pathname));
  await page.getByTestId('save-profile').click();
  const profileResponse = await saved; expect(profileResponse.ok()).toBeTruthy();
  const profile = await profileResponse.json();
  const endpoint = `/api/profiles/${profile.id}/admissions-actions`;
  await page.goto('/#/documents');
  const manual = await addTask(page, 'Synthetic core manual task');
  expect(manual.binding).toBeNull();
  await page.goto('/#/approved');
  await page.getByRole('button', { name: 'Add an application', exact: true }).click();
  await page.getByLabel('Application name', { exact: true }).fill('Synthetic manual application');
  await page.getByLabel('University, as entered by you', { exact: true }).fill('Synthetic Unknown University');
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  const manualApp = await save(page);
  expect(manualApp.applied_delta.applications[0].target.result_id).toBeNull();
  await page.goto('/#/preferences');
  await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();
  await waitForResults(page);
  await openShortlist(page);
  const rows = page.locator('tbody tr').filter({ has: page.locator('.decision-btn--approve') });
  for (let i = 0; i < 2; i++) {
    const decision = page.waitForResponse(r => r.request().method() === 'POST' && /\/decision$/.test(new URL(r.url()).pathname));
    await rows.nth(i).locator('.decision-btn--approve').click(); expect((await decision).ok()).toBeTruthy();
  }
  await page.goto('/#/approved');
  await page.getByRole('button', { name: 'Add an application', exact: true }).click();
  await page.getByLabel('Application name', { exact: true }).fill('Synthetic core application');
  const selector = page.getByRole('combobox', { name: 'Programme reference', exact: true });
  const selected = await selector.locator('option').nth(1).getAttribute('value'); expect(selected).toBeTruthy();
  await selector.selectOption(selected!);
  await page.getByLabel('Intake, if known', { exact: true }).fill('Synthetic fall 2027');
  await page.getByLabel('Application route, if known', { exact: true }).fill('Synthetic own portal');
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  const created = await save(page); const appId = created.applied_delta.applications[0].id;
  await expect(page.getByRole('heading', { name: 'Synthetic core application', exact: true })).toBeVisible();
  const applicationCard = page.getByTestId('personal-application').filter({ has: page.getByRole('heading', { name: 'Synthetic core application', exact: true }) });
  await applicationCard.getByRole('button', { name: 'Start preparing this application', exact: true }).click();
  await expect(applicationCard).toContainText('Preparing');
  await applicationCard.getByRole('button', { name: 'Record my submission statement', exact: true }).click();
  await page.getByLabel('Your event date, if known', { exact: true }).fill('2026-10-14');
  await page.getByLabel('Submission channel, as entered by you', { exact: true }).fill('Synthetic own declaration');
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  await save(page); await expect(applicationCard).toContainText('Submission · declared by you');
  await applicationCard.getByRole('button', { name: 'History', exact: true }).click();
  await page.getByRole('button', { name: 'Correct this declaration', exact: true }).click();
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  await save(page); await expect(applicationCard).toContainText('Preparing');
  await page.getByTestId('collect-documents').click();
  await page.goto('/#/documents');
  const linked = await addTask(page, 'Synthetic core linked task', appId);
  const occurrence = page.getByRole('combobox', { name: 'Choose a programme requirement', exact: true });
  await expect(occurrence.locator('option')).not.toHaveCount(1);
  await occurrence.selectOption((await occurrence.locator('option').nth(1).getAttribute('value'))!);
  await page.getByRole('combobox', { name: 'Task to link', exact: true }).selectOption(linked.id);
  await page.getByRole('button', { name: 'Review current requirement', exact: true }).click();
  const bind = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  await page.getByRole('button', { name: 'Save reviewed requirement link', exact: true }).click();
  expect((await bind).status()).toBe(200);
  const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: 'Synthetic core linked task', exact: true }) });
  await card.getByRole('button', { name: 'Update personal status', exact: true }).click();
  await page.getByRole('combobox', { name: 'Your reported status', exact: true }).selectOption('prepared_reported');
  await page.getByRole('checkbox', { name: 'I confirm this is my own report, not an official university confirmation.', exact: true }).check();
  await save(page); await expect(card).toContainText('Prepared · self-reported');
  await page.goto('/#/home');
  const today = page.getByTestId('admissions-today');
  await expect(today.getByRole('heading', { name: 'Synthetic core manual task', exact: true })).toBeVisible();
  await today.getByTestId('today-action').filter({ has: page.getByRole('heading', { name: 'Synthetic core manual task', exact: true }) }).getByRole('link', { name: 'Open this record', exact: true }).click();
  await expect(page.getByLabel('Task name', { exact: true })).toHaveValue('Synthetic core manual task');
  await page.getByLabel('Task name', { exact: true }).fill('Synthetic core renamed task');
  await page.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
  await save(page);
  await page.reload(); await expect(page.getByRole('heading', { name: 'Synthetic core renamed task', exact: true }).first()).toBeVisible();
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('button', { name: 'Add a document task', exact: true })).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.screenshot({ path: info.outputPath(`documents-${width}.png`), fullPage: true });
  }
  const secondContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const second = await secondContext.newPage();
  try {
    if (auth) await login(second); else await second.goto('/#/home');
    await second.goto('/#/documents');
    await expect(second.getByRole('heading', { name: 'Synthetic core renamed task', exact: true })).toBeVisible();
    const native = await second.request.get(endpoint); expect(native.status()).toBe(200);
    const state = await native.json(); expect(state.state.applications.some((app: {id: string}) => app.id === appId)).toBe(true);
    expect(state.state.document_tasks.find((task: {id: string}) => task.id === linked.id).binding).not.toBeNull();
    await second.screenshot({ path: info.outputPath('second-browser-native-documents.png'), fullPage: true });
  } finally { await secondContext.close(); }
  if (auth) {
    await page.getByTestId('sign-out').click(); await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
    await login(page); await page.goto('/#/approved');
    await expect(page.getByRole('heading', { name: 'Synthetic core application', exact: true })).toBeVisible();
  }
  await page.goto('/#/export');
  const exported = page.waitForResponse(r => r.request().method() === 'GET' && /\/export$/.test(new URL(r.url()).pathname));
  await page.getByTestId('export-profile').click(); const data = await exported; expect(data.ok()).toBeTruthy();
  const exportBody = await data.json(); expect(JSON.stringify(exportBody)).toContain('Synthetic core renamed task');
  await page.getByTestId('delete-confirm').fill('DELETE');
  const deleted = page.waitForResponse(r => r.request().method() === 'DELETE' && new URL(r.url()).pathname === `/api/profiles/${profile.id}`);
  await page.getByTestId('delete-everything').click(); expect((await deleted).ok()).toBeTruthy();
  expect((await page.request.get(endpoint)).status()).toBe(404);
  await info.attach('native-api-statuses.json', { body: JSON.stringify({ auth, profile_id: profile.id, requests }, null, 2), contentType: 'application/json' });
});
