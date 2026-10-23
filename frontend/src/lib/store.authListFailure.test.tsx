/** A server roster 500 must not make a valid owner's new local edits disposable. */
import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import { applicantStorageKey, bindApplicantOwner } from '@/lib/applicantStorage';
import { adoptPointer, readDraftEnvelope } from '@/lib/caseDrafts';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import { profile, research, result } from '@/lib/securityMergeFixtures';
import { StoreProvider, useStore } from '@/lib/store';
import type { AuthStatus, Capabilities, ProfileValidationReport, ShortlistSummary } from '@/types';

const identity = JSON.stringify(['synthetic-current-owner', 'synthetic-current-workspace']);
const status: AuthStatus = {
  enabled: true, authenticated: true, registration_enabled: false, password_reset_enabled: false,
  principal: { user_id: 'synthetic-current-owner', organization_id: 'synthetic-current-workspace',
    email: 'current@example.test', display_name: 'Synthetic current owner',
    organization_name: 'Synthetic current workspace', role: 'owner', local_development: false },
};
const capabilities: Capabilities = {
  demo_mode: true, data_origin: 'synthetic local regression', adapters: [], fetch_tiers: [],
  currency: { supported: [], rate_date: '2026-10-09', rate_source: 'synthetic fixture' },
  guarantees: [], limits: [], live_coverage: { institutions: 0, countries: [], recall_note: 'Synthetic only' },
};
const validation: ProfileValidationReport = { gaps: [], can_proceed: true, blocking_count: 0, summary: 'Synthetic local edit' };
const summary: ShortlistSummary = { total: 0, by_eligibility: {}, by_funding: {}, by_decision: {},
  with_conflicts: 0, with_open_questions: 0, demo_data: true };
let store: ReturnType<typeof useStore>;
function Probe() { store = useStore(); return <p>Current owner local draft control</p>; }
function tree() {
  return <DraftIdentityContext.Provider value={identity}><StoreProvider><Probe /></StoreProvider></DraftIdentityContext.Provider>;
}
async function flush() { await act(async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); }); }

beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear(); bindApplicantOwner(status);
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic case-list failure control'); }));
  vi.spyOn(api, 'capabilities').mockResolvedValue(capabilities);
  // An explicit API response error from a valid owner; no auth/transport ambiguity.
  vi.spyOn(api, 'cases').mockRejectedValue(new ApiError(500, 'Synthetic authorized case list unavailable'));
  vi.spyOn(api, 'validateProfile').mockResolvedValue(validation);
  vi.spyOn(api, 'getProfile').mockResolvedValue(profile('unexpected-saved-case'));
  vi.spyOn(api, 'listRuns').mockResolvedValue([]);
  vi.spyOn(api, 'getRun').mockResolvedValue(research('unexpected-run', 'unexpected-saved-case'));
  vi.spyOn(api, 'results').mockResolvedValue([result('unexpected-result', 'unexpected-run')]);
  vi.spyOn(api, 'summary').mockResolvedValue(summary);
  vi.spyOn(api, 'createProfile').mockResolvedValue(profile('unexpected-created-case'));
  vi.spyOn(api, 'updateProfile').mockResolvedValue(profile('unexpected-updated-case'));
  vi.spyOn(api, 'startRun').mockResolvedValue(research('unexpected-started-run', 'unexpected-saved-case'));
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

it('retains current-owner edits after an authorized case-list 500 and restores its own local slot on remount', async () => {
  const first = render(tree()); await flush();
  expect(api.cases).toHaveBeenCalled();
  expect(store.hydrated).toBe(true);
  expect(store.error).toBe('Synthetic authorized case list unavailable');
  expect(store.savedProfile).toBeNull(); expect(store.run).toBeNull(); expect(store.results).toEqual([]);
  expect(adoptPointer('profile', identity)).toBeNull();

  await act(async () => { store.setProfileDraft(draft => ({ ...draft, display_name: 'Retained local edit after case-list 500' })); });
  await act(async () => { vi.advanceTimersByTime(600); }); await flush();
  const localCase = adoptPointer('profile', identity);
  expect(localCase).not.toBeNull();
  expect(localCase).toMatch(/^local:/);
  expect(readDraftEnvelope(localCase!, identity)?.draft.display_name).toBe('Retained local edit after case-list 500');
  const slot = applicantStorageKey(`ashyq.draft.${localCase}`);
  expect(slot).toBe(`ashyq.owner.${encodeURIComponent(`auth:${identity}`)}.ashyq.draft.${localCase}`);
  expect(localStorage.getItem(slot!)).toContain('Retained local edit after case-list 500');
  expect(store.dirty).toBe(true);

  first.unmount(); render(tree()); await flush();
  expect(store.hydrated).toBe(true);
  expect(store.profileDraft.display_name).toBe('Retained local edit after case-list 500');
  expect(store.draftRestored).toBe(true);
  expect(adoptPointer('profile', identity)).toBe(localCase);
  expect(store.savedProfile).toBeNull(); expect(store.run).toBeNull(); expect(store.results).toEqual([]);
  expect(api.getProfile).not.toHaveBeenCalled(); expect(api.listRuns).not.toHaveBeenCalled();
  expect(api.getRun).not.toHaveBeenCalled(); expect(api.results).not.toHaveBeenCalled();
  expect(api.createProfile).not.toHaveBeenCalled(); expect(api.updateProfile).not.toHaveBeenCalled();
  expect(api.startRun).not.toHaveBeenCalled();
});
