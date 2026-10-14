/** Labelled network faults on real owned native API; no fabricated receipts. */
import { test, expect, type Page } from '@playwright/test';

const auth = process.env.CORE_NATIVE_AUTH === 'true';
const EMAIL = `core-recovery-${Date.now()}-${process.pid}@ashyq.invalid`;
const PASSWORD = 'synthetic-recovery-passphrase-2026';
async function login(page: Page) {
  await page.goto('/#/sign-in'); await page.getByTestId('auth-email').fill(EMAIL);
  await page.getByTestId('auth-password').fill(PASSWORD); await page.getByTestId('auth-submit').click();
  await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
}
async function editor(page: Page, label: string) {
  await page.getByRole('button', { name: 'Add a document task', exact: true }).click();
  await page.getByLabel('Task name', { exact: true }).fill(label);
}
test('native recovery: lost ACK replay, CAS, physical64 cap, selected cleanup, corrupt storage', async ({ page, browser }, info) => {
  test.setTimeout(360_000);
  if (auth) {
    await page.goto('/#/sign-in'); await page.getByTestId('auth-mode-toggle').click();
    await page.getByTestId('auth-name').fill('Synthetic Recovery Applicant');
    await page.getByTestId('auth-organization').fill('Synthetic Recovery Workspace');
    await page.getByTestId('auth-email').fill(EMAIL); await page.getByTestId('auth-password').fill(PASSWORD);
    await page.getByTestId('auth-submit').click(); await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  }
  await page.goto('/#/profile'); await page.getByTestId('load-demo-profile').click();
  const replacement = page.getByTestId('confirm-replace'); if (await replacement.isVisible().catch(() => false)) await replacement.click();
  const saved = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/profiles');
  await page.getByTestId('save-profile').click(); const savedResponse = await saved; expect(savedResponse.status()).toBe(201);
  const profile = await savedResponse.json(); const endpoint = `/api/profiles/${profile.id}/admissions-actions`;
  await page.goto('/#/documents');
  let originalReceipt: any; let dropped = false; const bodies: string[] = [];
  page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === endpoint + '/commands') bodies.push(request.postData()!); });
  // The server commits and returns its actual receipt. Only UI delivery is lost.
  await page.route('**' + endpoint + '/commands', async route => {
    if (dropped || route.request().method() !== 'POST') return route.continue();
    dropped = true; const response = await route.fetch(); expect(response.status()).toBe(200);
    originalReceipt = await response.json(); await route.abort('failed');
  });
  await editor(page, 'Synthetic lost response task'); await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  const recovery = page.getByTestId('admissions-recovery');
  await expect(recovery.getByText('Confirmation has not been received', { exact: true })).toBeVisible();
  expect(bodies).toHaveLength(1); const write = JSON.parse(bodies[0]);
  await page.unroute('**' + endpoint + '/commands'); await page.reload();
  await expect(page.getByRole('heading', { name: 'Synthetic lost response task', exact: true })).toBeVisible();
  const retried = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === endpoint + '/commands');
  await recovery.getByRole('button', { name: 'Retry original request', exact: true }).click();
  const replay = await retried; expect(replay.status()).toBe(200); expect(await replay.json()).toEqual(originalReceipt);
  expect(bodies).toHaveLength(2); expect(bodies[1]).toBe(bodies[0]);
  let current = await (await page.request.get(endpoint)).json(); expect(current.revision).toBe(1); expect(current.state.document_tasks).toHaveLength(1);
  const task = current.state.document_tasks[0];
  const secondContext = await browser.newContext(); const second = await secondContext.newPage();
  try {
    if (auth) await login(second); else await second.goto('/#/home');
    await second.getByRole('combobox', { name: 'Applicant', exact: true }).selectOption(profile.id);
    await second.goto('/#/documents');
    await expect(second.getByRole('heading', { name: task.personal.label, exact: true })).toBeVisible();
    const card = page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: task.personal.label, exact: true }) });
    await card.getByRole('button', { name: 'Edit document details', exact: true }).click();
    await page.getByLabel('Task name', { exact: true }).fill('Synthetic stale window edit');
    await page.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
    const other = second.getByTestId('personal-document-task').filter({ has: second.getByRole('heading', { name: task.personal.label, exact: true }) });
    await other.getByRole('button', { name: 'Edit document details', exact: true }).click();
    await second.getByLabel('Task name', { exact: true }).fill('Synthetic other window confirmed');
    await second.getByRole('checkbox', { name: 'I confirm these personal details; previous reports and requirement references remain in history.', exact: true }).check();
    const ack = second.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
    await second.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
    const conflict = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
    await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await conflict).status()).toBe(409);
    await expect(recovery.getByText('Data changed. Review the saved version before creating a new request.', { exact: true })).toBeVisible();
    current = await (await page.request.get(endpoint)).json(); expect(current.revision).toBe(2);
    expect(current.state.document_tasks[0].personal.label).toBe('Synthetic other window confirmed');
    await page.getByRole('button', { name: 'Close editor', exact: true }).click();
    await recovery.getByRole('button', { name: 'Refresh saved view', exact: true }).click();
  } finally { await secondContext.close(); }
  // Remove only the selected confirmed first receipt; the CAS request stays unresolved.
  await recovery.getByRole('checkbox').first().check();
  await recovery.getByRole('button', { name: 'Clear selected local confirmations', exact: true }).click();
  await expect(recovery.getByRole('checkbox')).toHaveCount(0);
  for (let index = 0; index < 63; index++) {
    await editor(page, `Synthetic cap task ${index}`);
    const ack = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
    await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
    await expect(page.getByTestId('personal-document-task').filter({ has: page.getByRole('heading', { name: `Synthetic cap task ${index}`, exact: true }) })).toHaveCount(1);
  }
  await expect(recovery.getByText('The local journal has 64 entries. A new request needs space; only selected confirmed entries can be cleared.', { exact: true })).toBeVisible();
  const physical = await page.evaluate((id: string) => {
    const rows = Object.keys(localStorage).map(key => ({ key, raw: localStorage.getItem(key)! })).flatMap(row => {
      try { return [{ ...row, value: JSON.parse(row.raw) }]; } catch { return []; }
    });
    return rows.find(row => row.value?.schema_version === 'g3-case-local-index-v1' && row.value.profile_id === id);
  }, profile.id);
  expect(physical?.value.entries).toHaveLength(64);
  const countBefore = bodies.length; const revisionBefore = (await (await page.request.get(endpoint)).json()).revision;
  await editor(page, 'Synthetic blocked65th'); await page.getByRole('button', { name: 'Save on server', exact: true }).click();
  await expect(page.getByText('Saving has not been confirmed. Keep the original request in recovery; do not create a duplicate.', { exact: true })).toBeVisible();
  expect(bodies).toHaveLength(countBefore); expect((await (await page.request.get(endpoint)).json()).revision).toBe(revisionBefore);
  await page.getByRole('button', { name: 'Close editor', exact: true }).click();
  await recovery.getByRole('checkbox').first().check(); await recovery.getByRole('button', { name: 'Clear selected local confirmations', exact: true }).click();
  await editor(page, 'Synthetic new request after selected cleanup');
  const ack = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/admissions-actions/commands'));
  await page.getByRole('button', { name: 'Save on server', exact: true }).click(); expect((await ack).status()).toBe(200);
  await page.reload(); await expect(recovery.getByText('Data changed. Review the saved version before creating a new request.', { exact: true })).toBeVisible();
  const beforeCorrupt = await page.evaluate((key: string) => localStorage.getItem(key), physical!.key);
  await page.evaluate((key: string) => localStorage.setItem(key, 'null'), physical!.key); await page.reload();
  await expect(page.getByRole('button', { name: 'Add a document task', exact: true })).toBeDisabled();
  expect(await page.evaluate((key: string) => localStorage.getItem(key), physical!.key)).toBe('null');
  expect((await (await page.request.get(endpoint)).json()).revision).toBe(revisionBefore + 1);
  // Restore only this test's exact preimage; this is fixture cleanup, not product recovery.
  await page.evaluate(({ key, raw }) => localStorage.setItem(key, raw), { key: physical!.key, raw: beforeCorrupt! });
  await info.attach('native-recovery-proof.json', { body: JSON.stringify({ auth, profile_id: profile.id, original_uuid: write.client_write_uuid, replay_event: originalReceipt.event_id, cas_status: 409, physical_entries: 64, blocked_without_http: true, pending_preserved: true, corrupt_bytes_preserved: true, accepted_revision: revisionBefore + 1 }), contentType: 'application/json' });
});
