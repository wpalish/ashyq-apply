import { webcrypto } from 'node:crypto';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { useAdmissionsActions } from './useAdmissionsActions';
import { admissionsRecoveryEntryRaw, journalAdmissionsAction, openAdmissionsActionsRecovery, readAdmissionsActionsRecovery, type G3LiveCaseIdentity } from './admissionsActionsRecovery';
import { acceptedActions, actionBody, emptyActions, FIXTURE_UUID } from '@/test/admissionsFixtures';
import type { AdmissionsCommandOutcome } from './useAdmissionsActions';
let live: G3LiveCaseIdentity;
const getter = () => live;
vi.mock('@/lib/store', () => ({ useStore: () => ({ currentAdmissionsCase: getter }) }));
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve };
}
function binding() {
  const value = openAdmissionsActionsRecovery(live.scope, live.profile_id ?? 'A', live.case_epoch, getter);
  if (!value.ok) throw new Error(value.reason); return value.value;
}
async function loaded() {
  const hook = renderHook(() => useAdmissionsActions());
  await waitFor(() => expect(hook.result.current.current?.profile_id).toBe(live.profile_id));
  return hook;
}
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto); localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo');
  live = { scope: undefined, profile_id: 'A', case_epoch: 1 };
  vi.spyOn(api, 'admissionsActions').mockImplementation(async profile => emptyActions(profile));
  vi.spyOn(api, 'writeAdmissionsAction').mockRejectedValue(new Error('Synthetic network loss'));
  vi.spyOn(api, 'admissionsActionEvent').mockRejectedValue(new ApiError(404, 'Synthetic missing event'));
  vi.spyOn(api, 'admissionsActionsHistory').mockResolvedValue({ profile_id: 'A', events: [], next_after_revision: null, source_evaluation: 'not_evaluated' });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('G3 transport uses the original command and fresh own server state', () => {
  it('does not dispatch on initial hydration or merely reading recovery', async () => {
    const b = binding(); await journalAdmissionsAction(b, actionBody(), 1);
    const hook = await loaded();
    expect(hook.result.current.entries).toHaveLength(1);
    expect(api.writeAdmissionsAction).not.toHaveBeenCalled();
  });

  it('records body before dispatch and recovers a lost postcommit response with the same request', async () => {
    const fixture = acceptedActions(); let committed = false; const bodies: unknown[] = [];
    vi.mocked(api.admissionsActions).mockImplementation(async () => committed ? fixture.current : emptyActions());
    vi.mocked(api.writeAdmissionsAction).mockImplementation(async (profile, body) => {
      bodies.push(structuredClone(body));
      const recorded = await readAdmissionsActionsRecovery(binding());
      expect(recorded.ok && recorded.value.entries[0]?.body).toEqual(body);
      expect(profile).toBe('A');
      if (!committed) { committed = true; throw new Error('Synthetic lost response after commit'); }
      return fixture.receipt;
    });
    const hook = await loaded(); let outcome: AdmissionsCommandOutcome | undefined;
    await act(async () => { outcome = await hook.result.current.submit(actionBody()); });
    expect(outcome?.accepted).toBe(false);
    expect(hook.result.current.entries[0]?.pending_state).toBe('uncertain');
    await act(async () => { outcome = await hook.result.current.retry(FIXTURE_UUID); });
    expect(bodies).toEqual([actionBody(), actionBody()]);
    expect(outcome?.accepted).toBe(true); expect(outcome?.currentRefreshed).toBe(true);
    expect(hook.result.current.current?.revision).toBe(1);
    expect(hook.result.current.entries[0]?.descriptor.status).toBe('acknowledged');
  });

  it('retains conflict body/CAS and reads the server comparison without an automatic retry', async () => {
    const original = actionBody(); const newer = acceptedActions(actionBody('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'));
    vi.mocked(api.writeAdmissionsAction).mockRejectedValue(new ApiError(409, 'Synthetic conflict', 'admissions_actions_revision_conflict'));
    const hook = await loaded(); vi.mocked(api.admissionsActions).mockResolvedValue(newer.current);
    await act(async () => { await hook.result.current.submit(original); });
    expect(hook.result.current.entries[0]?.body).toEqual(original);
    expect(hook.result.current.entries[0]?.pending_state).toBe('conflict');
    expect(hook.result.current.current?.revision).toBe(1); expect(api.writeAdmissionsAction).toHaveBeenCalledTimes(1);
    await act(async () => { await hook.result.current.retry(FIXTURE_UUID); });
    expect(api.writeAdmissionsAction).toHaveBeenCalledTimes(1);
  });

  it('never sends if journal storage fails and keeps the last confirmed server view', async () => {
    const hook = await loaded(); const native = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (key.includes('.intent.')) throw new Error('Synthetic storage denial');
      native.call(this, key, value);
    });
    await act(async () => { await hook.result.current.submit(actionBody()); });
    expect(api.writeAdmissionsAction).not.toHaveBeenCalled();
    expect(hook.result.current.journalError).toBe('storage'); expect(hook.result.current.current?.revision).toBe(0);
  });

  it('does not apply an old A response to B or a newly activated A', async () => {
    const response = deferred<ReturnType<typeof acceptedActions>['receipt']>();
    vi.mocked(api.writeAdmissionsAction).mockReturnValue(response.promise);
    const hook = await loaded(); let old: Promise<AdmissionsCommandOutcome> | undefined;
    act(() => { old = hook.result.current.submit(actionBody()); });
    await waitFor(() => expect(api.writeAdmissionsAction).toHaveBeenCalledTimes(1));
    live = { ...live, profile_id: 'B', case_epoch: 2 }; hook.rerender();
    await waitFor(() => expect(hook.result.current.current?.profile_id).toBe('B'));
    live = { ...live, profile_id: 'A', case_epoch: 3 }; hook.rerender();
    await waitFor(() => expect(hook.result.current.current?.profile_id).toBe('A'));
    await act(async () => { response.resolve(acceptedActions().receipt); await old; });
    expect(hook.result.current.current?.revision).toBe(0);
    expect(hook.result.current.entries[0]?.descriptor.status).toBe('pending');
  });

  it('distinguishes a confirmed save from a failed refresh rather than applying the receipt delta', async () => {
    const fixture = acceptedActions(); const hook = await loaded();
    vi.mocked(api.writeAdmissionsAction).mockResolvedValue(fixture.receipt);
    vi.mocked(api.admissionsActions).mockRejectedValue(new ApiError(503, 'Synthetic read failure'));
    let outcome: AdmissionsCommandOutcome | undefined;
    await act(async () => { outcome = await hook.result.current.submit(actionBody()); });
    expect(outcome?.accepted).toBe(true); expect(outcome?.currentRefreshed).toBe(false);
    expect(hook.result.current.acceptedButUnrefreshed).toBe(true);
    expect(hook.result.current.current?.revision).toBe(0);
    expect(hook.result.current.current?.state).toBeNull();
  });

  it('requires a matching own receipt, not a successful HTTP response alone', async () => {
    const hook = await loaded(); vi.mocked(api.writeAdmissionsAction).mockResolvedValue(acceptedActions(actionBody(), 'foreign').receipt);
    await act(async () => { expect((await hook.result.current.submit(actionBody())).accepted).toBe(false); });
    expect(hook.result.current.entries[0]?.descriptor.status).toBe('pending');
    expect(hook.result.current.entries[0]?.pending_state).toBe('uncertain');
  });

  it('fetches the selected own event before local ACK cleanup and does not change server current', async () => {
    const fixture = acceptedActions(); vi.mocked(api.admissionsActions).mockResolvedValue(fixture.current);
    const b = binding(); await journalAdmissionsAction(b, fixture.body, 1);
    const { acknowledgeAdmissionsAction } = await import('./admissionsActionsRecovery');
    expect((await acknowledgeAdmissionsAction(b, fixture.body, fixture.receipt)).ok).toBe(true);
    vi.mocked(api.admissionsActionEvent).mockResolvedValue(fixture.receipt);
    const hook = await loaded();
    await act(async () => { expect(await hook.result.current.clearAcknowledged([FIXTURE_UUID])).toBe(true); });
    expect(api.admissionsActionEvent).toHaveBeenCalledWith('A', fixture.receipt.event_id);
    expect(hook.result.current.entries).toHaveLength(0);
    expect(hook.result.current.current?.revision).toBe(1); expect(api.writeAdmissionsAction).not.toHaveBeenCalled();
  });

  it('does not silently reserialize an original envelope before retry', async () => {
    const b = binding(); const saved = await journalAdmissionsAction(b, actionBody(), 1);
    if (!saved.ok) throw new Error(saved.reason);
    const originalRaw = JSON.stringify(saved.value.entry, null, 2);
    localStorage.setItem(`${b.family}intent.${FIXTURE_UUID}`, originalRaw);
    const hook = await loaded(); const fixture = acceptedActions();
    vi.mocked(api.writeAdmissionsAction).mockResolvedValue(fixture.receipt); vi.mocked(api.admissionsActions).mockResolvedValue(fixture.current);
    const raw = admissionsRecoveryEntryRaw(b, FIXTURE_UUID); expect(raw.ok && raw.value).toBe(originalRaw);
    await act(async () => { expect((await hook.result.current.retry(FIXTURE_UUID)).accepted).toBe(true); });
    expect(api.writeAdmissionsAction).toHaveBeenCalledWith('A', actionBody());
  });
});


it('reserves the same-case cleanup slot before its first await and rejects a duplicate click', async () => {
  const fixture = acceptedActions(); vi.mocked(api.admissionsActions).mockResolvedValue(fixture.current);
  const b = binding(); await journalAdmissionsAction(b, fixture.body, 1);
  const { acknowledgeAdmissionsAction } = await import('./admissionsActionsRecovery');
  await acknowledgeAdmissionsAction(b, fixture.body, fixture.receipt);
  const response = deferred<typeof fixture.receipt>(); vi.mocked(api.admissionsActionEvent).mockReturnValue(response.promise);
  const hook = await loaded(); let first: Promise<boolean> | undefined; let second: Promise<boolean> | undefined;
  act(() => { first = hook.result.current.clearAcknowledged([FIXTURE_UUID]); second = hook.result.current.clearAcknowledged([FIXTURE_UUID]); });
  await waitFor(() => expect(api.admissionsActionEvent).toHaveBeenCalledTimes(1));
  expect(await second).toBe(false);
  await act(async () => { response.resolve(fixture.receipt); expect(await first).toBe(true); });
  expect(hook.result.current.entries).toHaveLength(0);
});
