/** Native saved profile input read after a labelled failed subsequent run start. */
import { test, expect } from '@playwright/test';
import { waitForResults } from './helpers';
import type { ProgramResult } from '../src/types';
test('native saved funding change warns on old research after an aborted subsequent start, without reranking history', async ({ page }, info) => {
  test.setTimeout(120_000); const auth = process.env.CORE_NATIVE_AUTH === 'true';
  if (auth) {
    await page.goto('/#/sign-in'); await page.getByTestId('auth-mode-toggle').click();
    await page.getByTestId('auth-name').fill('Synthetic Input Applicant'); await page.getByTestId('auth-organization').fill('Synthetic Input Workspace');
    await page.getByTestId('auth-email').fill(`core-input-${Date.now()}-${process.pid}@ashyq.invalid`);
    await page.getByTestId('auth-password').fill('synthetic-input-passphrase-2026'); await page.getByTestId('auth-submit').click();
    await expect(page.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  }
  await page.goto('/#/profile'); await page.getByTestId('load-demo-profile').click();
  const confirm = page.getByTestId('confirm-replace'); if (await confirm.isVisible().catch(() => false)) await confirm.click();
  const saved = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/profiles');
  let metadataDropped = false;
  await page.route('**/api/cases', async route => { if (!metadataDropped) { metadataDropped = true; const actual = await route.fetch(); expect(actual.status()).toBe(200); await route.abort('failed'); } else await route.continue(); });
  await page.getByTestId('save-profile').click(); const profileResponse = await saved; expect(profileResponse.status()).toBe(201); const profile = await profileResponse.json();
  await expect(page.getByText('Saved', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Applicant', exact: true })).toHaveValue(profile.id);
  await page.unroute('**/api/cases');
  await page.goto('/#/preferences'); await page.getByTestId('start-research').click(); await waitForResults(page);
  const runs = await (await page.request.get(`/api/runs?profile_id=${profile.id}`)).json(); expect(runs).toHaveLength(1); const runId = runs[0].id;
  const projection = (rows: ProgramResult[]) => rows.map(row => ({ id: row.id, eligibility: row.eligibility, admissions_fit: row.admissions_fit, funding_fit: row.funding_fit, funding_gap: row.funding_gap, ranking: row.ranking, user_decision: row.user_decision }));
  const original = projection(await (await page.request.get(`/api/runs/${runId}/results`)).json()); expect(original.length).toBeGreaterThan(0);
  const initial = await (await page.request.get(`/api/runs/${runId}`)).json(); expect(initial.profile_input_status.state).toBe('current');
  await page.goto('/#/preferences'); await page.getByTestId('max-budget').fill('10001');
  let aborted = false; await page.route('**/api/runs', async route => { if (route.request().method() === 'POST' && !aborted) { aborted = true; await route.abort('failed'); } else await route.continue(); });
  const updated = page.waitForResponse(r => r.request().method() === 'PUT' && new URL(r.url()).pathname === `/api/profiles/${profile.id}`);
  await page.getByTestId('start-research').click(); expect((await updated).status()).toBe(200);
  await expect(page.getByText('Your profile inputs have changed since this research.', { exact: true })).toBeVisible();
  await expect(page.getByText(/Changed sections: Funding/)).toBeVisible();
  const changed = await (await page.request.get(`/api/runs/${runId}`)).json(); expect(changed.profile_input_status.state).toBe('changed'); expect(changed.profile_input_status.changed_sections).toContain('funding');
  expect(projection(await (await page.request.get(`/api/runs/${runId}/results`)).json())).toEqual(original);
  expect(await (await page.request.get(`/api/runs?profile_id=${profile.id}`)).json()).toHaveLength(1);
  await page.unroute('**/api/runs'); await page.goto('/#/profile');
  await expect(page.getByTestId('save-profile')).toBeVisible();
  expect(await page.getByText('Unsaved changes', { exact: true }).count()).toBe(0);
  await info.attach('native-research-input-proof.json', { body: JSON.stringify({ auth, profile_id: profile.id, retained_run_id: runId, changed_sections: changed.profile_input_status.changed_sections, applicability: changed.profile_input_status.applicability, original_evaluation_preserved: true, subsequent_run_not_created: true }), contentType: 'application/json' });
});
