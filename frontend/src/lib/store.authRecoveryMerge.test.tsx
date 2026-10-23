import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { bindApplicantOwner } from '@/lib/applicantStorage';
import { adoptPointer, readDraftEnvelope } from '@/lib/caseDrafts';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import { caseRow, profile, research, result } from '@/lib/securityMergeFixtures';
import { StoreProvider, useStore } from '@/lib/store';
import type { AuthStatus, StoredProfile } from '@/types';

const identity = JSON.stringify(['synthetic-A', 'synthetic-org-A']);
const status: AuthStatus = { enabled: true, registration_enabled: false, authenticated: true,
  principal: { user_id: 'synthetic-A', organization_id: 'synthetic-org-A',
    email: 'synthetic-a@example.invalid', display_name: 'A', organization_name: 'A',
    role: 'owner', local_development: false } };
let store: ReturnType<typeof useStore>;
function Probe() { store = useStore(); return <p>Recovery union control</p>; }
function tree() {
  return <DraftIdentityContext.Provider value={identity}><StoreProvider><Probe /></StoreProvider></DraftIdentityContext.Provider>;
}
async function flush() { await act(async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); }); }
function deferred<T>() { let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear(); bindApplicantOwner(status);
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic recovery control'); }));
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([caseRow('A')]);
  vi.spyOn(api, 'getProfile').mockResolvedValue(profile('A'));
  vi.spyOn(api, 'listRuns').mockResolvedValue([research('run-A', 'A')]);
  vi.spyOn(api, 'results').mockResolvedValue([result('result-A', 'run-A')]);
  vi.spyOn(api, 'summary').mockResolvedValue({ total: 1, by_eligibility: {}, by_funding: {},
    by_decision: {}, with_conflicts: 0, with_open_questions: 0, demo_data: true });
  vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok' });
  vi.spyOn(api, 'createProfile'); vi.spyOn(api, 'updateProfile'); vi.spyOn(api, 'startRun');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});
it('pointerless authenticated recovery uses the verified tree scope and case-filtered latest run without creating work', async () => {
  render(tree()); await flush();
  expect(store.hydrated).toBe(true); expect(store.savedProfile?.id).toBe('A');
  expect(store.run?.id).toBe('run-A'); expect(store.run?.profile_id).toBe(store.savedProfile?.id);
  expect(store.results.map(row => row.id)).toEqual(['result-A']);
  expect(api.getProfile).toHaveBeenCalledWith('A'); expect(api.listRuns).toHaveBeenCalledWith('A', 1);
  expect(api.results).toHaveBeenCalledWith('run-A');
  expect(adoptPointer('profile', identity)).toBe('A'); expect(adoptPointer('run', identity)).toBe('run-A');
  expect(api.createProfile).not.toHaveBeenCalled(); expect(api.updateProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
});
it('an explicit new case overtakes delayed recovery detail and still persists its own edits after hydration settles', async () => {
  const detail = deferred<StoredProfile>(); vi.mocked(api.getProfile).mockReturnValue(detail.promise);
  const first = render(tree()); await flush();
  expect(api.getProfile).toHaveBeenCalledWith('A'); expect(store.hydrated).toBe(false);
  await act(async () => { store.newCase(); });
  const newCase = adoptPointer('profile', identity)!; expect(newCase).toMatch(/^local:/);
  await act(async () => { detail.resolve(profile('A')); }); await flush();
  expect(store.hydrated).toBe(true); expect(store.savedProfile).toBeNull(); expect(store.run).toBeNull(); expect(store.results).toEqual([]);
  expect(adoptPointer('profile', identity)).toBe(newCase); expect(adoptPointer('run', identity)).toBeNull();
  await act(async () => { store.setProfileDraft(d => ({ ...d, display_name: 'Explicit fresh draft after recovery' })); });
  await act(async () => { vi.advanceTimersByTime(600); }); await flush();
  expect(readDraftEnvelope(newCase, identity)?.draft.display_name).toBe('Explicit fresh draft after recovery');
  first.unmount(); render(tree()); await flush();
  expect(store.savedProfile).toBeNull(); expect(store.profileDraft.display_name).toBe('Explicit fresh draft after recovery');
  expect(api.getProfile).toHaveBeenCalledTimes(1);
  expect(api.createProfile).not.toHaveBeenCalled(); expect(api.updateProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
});
