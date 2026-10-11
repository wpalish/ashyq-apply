import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import { applicantStorageKey, bindApplicantOwner } from '@/lib/applicantStorage';
import { adoptPointer, readDraftEnvelope, writeDraftEnvelope, writePointer } from '@/lib/caseDrafts';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import { caseRow, profile, research, result } from '@/lib/securityMergeFixtures';
import { blankProfile, StoreProvider, useStore } from '@/lib/store';
import type { AuthStatus, StoredProfile } from '@/types';

const status: AuthStatus = { enabled: true, registration_enabled: false, authenticated: true,
  principal: { user_id: 'synthetic-A', organization_id: 'synthetic-org-A',
    email: 'synthetic-a@example.invalid', display_name: 'A', organization_name: 'A',
    role: 'owner', local_development: false } };
const scope = JSON.stringify(['synthetic-A', 'synthetic-org-A']);
let store: ReturnType<typeof useStore>;
function Probe() { store = useStore(); return <p>Owned case</p>; }
function tree() {
  return <DraftIdentityContext.Provider value={scope}><StoreProvider><Probe /></StoreProvider></DraftIdentityContext.Provider>;
}
async function flush() { await act(async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); }); }
function deferred<T>() {
  let resolve!: (v: T) => void; let reject!: (e: unknown) => void;
  const promise = new Promise<T>((r, j) => { resolve = r; reject = j; });
  return { promise, resolve, reject };
}
function marks() { return JSON.parse(localStorage.getItem(applicantStorageKey('ashyq.docsDone')!) ?? '{}') as Record<string, boolean>; }
beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear(); bindApplicantOwner(status);
  writePointer('profile', 'A', scope); writePointer('run', 'run-A', scope);
  writeDraftEnvelope('A', { ...blankProfile(), display_name: 'Unsaved A' }, undefined, scope);
  writeDraftEnvelope('B', { ...blankProfile(), display_name: 'Unsaved B' }, undefined, scope);
  localStorage.setItem(applicantStorageKey('ashyq.docsDone')!, JSON.stringify({ 'result-A::Passport': true, 'result-B::Passport': true }));
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([caseRow('A'), caseRow('B')]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok' });
  vi.spyOn(api, 'getProfile').mockImplementation(async id => profile(id));
  vi.spyOn(api, 'getRun').mockResolvedValue(research('run-A', 'A'));
  vi.spyOn(api, 'listRuns').mockResolvedValue([research('run-B', 'B')]);
  vi.spyOn(api, 'results').mockImplementation(async id => [result(id === 'run-A' ? 'result-A' : 'result-B', id)]);
  vi.spyOn(api, 'summary').mockResolvedValue({ total: 1, by_eligibility: {}, by_funding: {},
    by_decision: {}, with_conflicts: 0, with_open_questions: 0, demo_data: true });
  vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

it('a late acknowledged deletion of A retires A slots and marks without resetting active B', async () => {
  const reply = deferred<void>(); vi.spyOn(api, 'deleteProfile').mockReturnValue(reply.promise);
  render(tree()); await flush();
  let deletion!: Promise<boolean>;
  await act(async () => { deletion = store.deleteEverything(); });
  await act(async () => { await store.switchCase('B'); }); await flush();
  const epoch = store.caseEpoch;
  let accepted!: boolean;
  await act(async () => { reply.resolve(); accepted = await deletion; }); await flush();
  expect(accepted).toBe(false);
  expect(store.savedProfile?.id).toBe('B'); expect(store.run?.id).toBe('run-B');
  expect(store.profileDraft.display_name).toBe('Unsaved B');
  expect(store.results.map(row => row.id)).toEqual(['result-B']); expect(store.caseEpoch).toBe(epoch);
  expect(adoptPointer('profile', scope)).toBe('B'); expect(adoptPointer('run', scope)).toBe('run-B');
  expect(readDraftEnvelope('A', scope)).toBeNull();
  expect(readDraftEnvelope('B', scope)?.draft.display_name).toBe('Unsaved B');
  expect(marks()).toEqual({ 'result-B::Passport': true });
  expect(store.cases.map(row => row.id)).toEqual(['B']);
});
it('successful current-case deletion returns a boolean receipt, resets private state and preserves future local edits', async () => {
  vi.spyOn(api, 'deleteProfile').mockResolvedValue(undefined);
  const first = render(tree()); await flush();
  const previousEpoch = store.caseEpoch;
  let accepted!: boolean;
  await act(async () => { accepted = await store.deleteEverything(); }); await flush();
  expect(accepted).toBe(true); expect(store.caseEpoch).toBe(previousEpoch + 1);
  expect(store.savedProfile).toBeNull(); expect(store.run).toBeNull(); expect(store.results).toEqual([]);
  expect(store.summary).toBeNull(); expect(store.shortlist).toBeNull(); expect(store.paywall).toBeNull();
  expect(store.validation).toBeNull(); expect(store.profileDraft).toEqual(blankProfile());
  expect(store.dirty).toBe(false); expect(store.draftRestored).toBe(false); expect(store.restored).toBe(false);
  expect(adoptPointer('profile', scope)).toBeNull(); expect(adoptPointer('run', scope)).toBeNull();
  expect(readDraftEnvelope('A', scope)).toBeNull(); expect(marks()).toEqual({ 'result-B::Passport': true });
  await act(async () => { store.setProfileDraft(d => ({ ...d, display_name: 'Fresh edit after deletion' })); });
  await act(async () => { vi.advanceTimersByTime(600); }); await flush();
  const newCase = adoptPointer('profile', scope)!;
  expect(newCase).toMatch(/^local:/); expect(newCase).not.toBe('A');
  expect(readDraftEnvelope(newCase, scope)?.draft.display_name).toBe('Fresh edit after deletion');
  first.unmount(); render(tree()); await flush();
  expect(store.savedProfile).toBeNull(); expect(store.profileDraft.display_name).toBe('Fresh edit after deletion');
});
it('a rejected deletion returns false and leaves the draft, checklist marks and active case intact', async () => {
  vi.spyOn(api, 'deleteProfile').mockRejectedValue(new ApiError(503, 'Synthetic deletion refused'));
  render(tree()); await flush(); const previous = structuredClone(store.profileDraft); const epoch = store.caseEpoch;
  let accepted!: boolean;
  await act(async () => { accepted = await store.deleteEverything(); }); await flush();
  expect(accepted).toBe(false); expect(store.error).toBe('Synthetic deletion refused');
  expect(store.savedProfile?.id).toBe('A'); expect(store.run?.id).toBe('run-A');
  expect(store.profileDraft).toEqual(previous); expect(store.caseEpoch).toBe(epoch);
  expect(adoptPointer('profile', scope)).toBe('A');
  expect(readDraftEnvelope('A', scope)?.draft.display_name).toBe('Unsaved A');
  expect(marks()).toEqual({ 'result-A::Passport': true, 'result-B::Passport': true });
});
it('a mounted save rechecks its original owner before follow-up requests when a deferred creation resolves', async () => {
  const created = deferred<StoredProfile>(); vi.spyOn(api, 'createProfile').mockReturnValue(created.promise);
  render(tree()); await flush(); await act(async () => { store.newCase(); }); await flush();
  const caseCalls = vi.mocked(api.cases).mock.calls.length;
  let save!: Promise<void>;
  await act(async () => { save = store.saveProfile(); });
  const rejected = save.catch(error => error);
  bindApplicantOwner({ ...status, principal: { ...status.principal!, user_id: 'synthetic-B', organization_id: 'synthetic-org-B' } });
  let error: unknown;
  await act(async () => { created.resolve(profile('created-for-A')); error = await rejected; }); await flush();
  expect(error).toBeInstanceOf(ApiError); expect((error as ApiError).status).toBe(401);
  expect(api.cases).toHaveBeenCalledTimes(caseCalls);
  expect(adoptPointer('profile', scope)).toBeNull();
  expect(adoptPointer('profile', JSON.stringify(['synthetic-B', 'synthetic-org-B']))).toBeNull();
});
