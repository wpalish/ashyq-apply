import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { manualFixture } from '@/test/manualAdmissionsFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import { acknowledgeAdmissionsAction, admissionsActionRetryBody, journalAdmissionsAction, openAdmissionsActionsRecovery, readAdmissionsActionsRecovery,
  validateAdmissionsActionReceipt, validateAdmissionsActionsCurrent, type G3RecoveryResult } from './admissionsActionsRecovery';
function value<T>(result: G3RecoveryResult<T>) { if (!result.ok) throw new Error(result.reason); return result.value; }
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); localStorage.clear(); sessionStorage.clear(); localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo'); });
afterEach(() => { vi.unstubAllGlobals(); });
it('journals and retries the exact manual body without creating a fake result reference', async () => {
  const live = { scope: undefined, profile_id: 'A', case_epoch: 1 };
  const binding = value(openAdmissionsActionsRecovery(undefined, 'A', 1, () => live));
  const { body, receipt, current } = manualFixture();
  const saved = value(await journalAdmissionsAction(binding, body, 1));
  expect(saved.entry.descriptor.result_ids).toEqual([]);
  expect(value(await admissionsActionRetryBody(binding, body.client_write_uuid, saved.raw))).toEqual(body);
  expect(await validateAdmissionsActionReceipt('A', body, receipt)).toBe(true);
  expect(await validateAdmissionsActionsCurrent(current, 'A')).toEqual(current);
  expect(await validateAdmissionsActionsCurrent(current, 'B')).toBeNull();
  expect((await acknowledgeAdmissionsAction(binding, body, receipt)).ok).toBe(true);
  expect(value(await readAdmissionsActionsRecovery(binding)).entries[0]?.descriptor.status).toBe('acknowledged');
});
it('retains V1 receipt hashing and rejects a mismatched V2 request or target', async () => {
  const old = acceptedActions(); expect(await validateAdmissionsActionReceipt('A', old.body, old.receipt)).toBe(true);
  const { body, receipt } = manualFixture();
  expect(await validateAdmissionsActionReceipt('A', { ...body, label: 'Different original intent' }, receipt)).toBe(false);
  const corrupt = structuredClone(receipt); corrupt.after_state_digest = 'f'.repeat(64);
  expect(await validateAdmissionsActionReceipt('A', body, corrupt)).toBe(false);
});
