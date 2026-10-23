/** Native owned case-generation/auth boundaries; synthetic data, loopback only. */
import { test, expect, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
const auth = process.env.CORE_NATIVE_AUTH === 'true';
const EMAIL = `core-fences-${Date.now()}-${process.pid}@ashyq.invalid`;
const PASSWORD = 'synthetic-fences-passphrase-2026';
async function register(page: Page, email: string) {
  await page.goto('/#/sign-in'); await page.getByTestId('auth-mode-toggle').click();
  await page.getByTestId('auth-name').fill('Synthetic Case Applicant');
  await page.getByTestId('auth-organization').fill('Synthetic Case Workspace');
  await page.getByTestId('auth-email').fill(email); await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click(); await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
}
async function createCase(page: Page) {
  await page.goto('/#/profile'); await page.getByTestId('load-demo-profile').click();
  const confirm = page.getByTestId('confirm-replace'); if (await confirm.isVisible().catch(() => false)) await confirm.click();
  const response = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/profiles');
  await page.getByTestId('save-profile').click(); const out = await response; expect(out.status()).toBe(201); return out.json();
}
async function task(page: Page, label: string) {
  await page.goto('/#/documents'); await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  await expect(page.getByLabel('Task name', { exact: true })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('combobox', { name: 'Who acts', exact: true })).toBeFocused();
  await page.getByLabel('Task name', { exact: true }).fill(label);
  await page.getByLabel('Your planning date', { exact: true }).fill('2026-10-20');
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await response).status()).toBe(200);
  await expect(page.getByRole('heading', { name: label, exact: true })).toBeVisible();
}
test('native fences: precommit unknown, late A→B→A read, date-only zones and foreign principal', async ({ page, browser }, info) => {
  test.setTimeout(180_000);
  if (auth) await register(page, EMAIL);
  const a = await createCase(page); await task(page, 'Synthetic case A initial');
  await page.getByRole('button', { name: 'New case', exact: true }).click();
  const b = await createCase(page); await task(page, 'Synthetic case B retained');
  await page.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(a.id);
  await expect(page.getByRole('heading', { name: 'Synthetic case A initial', exact: true })).toBeVisible();
  const endpoint = `/api/profiles/${a.id}/admissions-actions`;
  let held = false; let release!: () => void; let arrived!: () => void;
  const delivery = new Promise<void>(resolve => { release = resolve; });
  const readArrived = new Promise<void>(resolve => { arrived = resolve; });
  await page.route('**' + endpoint, async route => {
    if (!held && route.request().method() === 'GET') {
      held = true; const actual = await route.fetch(); expect(actual.status()).toBe(200); arrived();
      await delivery; await route.fulfill({ response: actual });
    } else await route.continue();
  });
  await page.getByTestId('admissions-recovery').getByRole('button', { name: 'Refresh saved records', exact: true }).click();
  await readArrived;
  await page.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(b.id);
  await expect(page.getByRole('heading', { name: 'Synthetic case B retained', exact: true })).toBeVisible();
  const changed = await page.request.post(endpoint + '/commands', { data: {
    schema_version: 'admissions-actions-v1', kind: 'create_personal_task', expected_revision: 1, client_write_uuid: randomUUID(), application_id: null,
    personal: { label: 'Synthetic case A after old read', responsible_actor: 'applicant', details: { due: null, notes: '' }, depends_on_task_ids: [] },
  } }); expect(changed.status()).toBe(200);
  await page.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(a.id);
  await expect(page.getByRole('heading', { name: 'Synthetic case A after old read', exact: true })).toBeVisible();
  const lateRead = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === endpoint);
  release(); await lateRead; await page.unroute('**' + endpoint);
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: 'Synthetic case A after old read', exact: true })).toBeVisible();
  expect((await (await page.request.get(endpoint)).json()).revision).toBe(2);
  // Abort before a server request; the UI still must report uncertainty, not save.
  let aborted = false;
  await page.route('**' + endpoint + '/commands', async route => { if (!aborted) { aborted = true; await route.abort('failed'); } else await route.continue(); });
  await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  await page.getByLabel('Task name', { exact: true }).fill('Synthetic before commit');
  await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  await expect(page.getByTestId('admissions-recovery').getByText('Confirmation has not been received', { exact: true })).toBeVisible();
  expect((await (await page.request.get(endpoint)).json()).revision).toBe(2);
  await page.unroute('**' + endpoint + '/commands'); await page.reload();
  const retried = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  await page.getByTestId('admissions-recovery').getByRole('button', { name: 'Retry original request', exact: true }).click(); expect((await retried).status()).toBe(200);
  expect((await (await page.request.get(endpoint)).json()).revision).toBe(3);
  for (const timezoneId of ['Pacific/Honolulu', 'Pacific/Kiritimati']) {
    const context = await browser.newContext({ timezoneId }); const other = await context.newPage();
    try {
      if (auth) {
        await other.goto('/#/sign-in'); await other.getByTestId('auth-email').fill(EMAIL); await other.getByTestId('auth-password').fill(PASSWORD);
        await other.getByTestId('auth-submit').click(); await expect(other.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
      } else await other.goto('/#/home');
      await other.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(a.id); await other.goto('/#/documents');
      const card = other.getByTestId('personal-document-task').filter({ has: other.getByRole('heading', { name: 'Synthetic case A initial', exact: true }) });
      await expect(card).toContainText('2026-10-20'); await expect(card).toContainText('Time zone unknown');
      await other.screenshot({ path: info.outputPath(`date-only-${timezoneId.replace('/', '-')}.png`), fullPage: true });
    } finally { await context.close(); }
  }
  if (auth) {
    const foreignContext = await browser.newContext(); const foreign = await foreignContext.newPage();
    try {
      await register(foreign, `foreign-${EMAIL}`);
      expect((await foreign.request.get(endpoint)).status()).toBe(404);
      expect((await foreign.request.get(`/api/profiles/${a.id}/export`)).status()).toBe(404);
      expect((await foreign.request.delete(`/api/profiles/${a.id}`)).status()).toBe(404);
      expect((await page.request.get(endpoint)).status()).toBe(200);
      expect((await (await page.request.get(endpoint)).json()).revision).toBe(3);
    } finally { await foreignContext.close(); }
  }
  const bState = await (await page.request.get(`/api/profiles/${b.id}/admissions-actions`)).json();
  expect(bState.revision).toBe(1); expect(bState.state.document_tasks[0].personal.label).toBe('Synthetic case B retained');
  await info.attach('native-fence-proof.json', { body: JSON.stringify({ auth, late_owned_read_forwarded_unchanged: true, a_revision: 3, b_revision: 1, precommit_failure_unconfirmed: true, date_only_zones: ['Pacific/Honolulu', 'Pacific/Kiritimati'], foreign_principal_checked: auth }), contentType: 'application/json' });
});
