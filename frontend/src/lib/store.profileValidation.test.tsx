/** Validation reports describe only their own current normalized input. */
import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { profile } from '@/lib/securityMergeFixtures';
import { StoreProvider, useStore } from './store';
import { deferred } from '@/screens/preparationFixtures';
import type { ProfileValidationReport } from '@/types';
let store: ReturnType<typeof useStore>;
function Probe() { store = useStore(); return <p>{store.validation?.summary ?? 'No current validation'}</p>; }
const report = (summary: string): ProfileValidationReport => ({ gaps: [], can_proceed: true, blocking_count: 0, summary });
async function flush() { await act(async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); }); }
async function tick() { await act(async () => { vi.advanceTimersByTime(400); }); await flush(); }
async function mount() { render(<StoreProvider><Probe /></StoreProvider>); await flush(); expect(store.savedProfile?.id).toBe('A'); }
async function edit(name: string) { await act(async () => store.setProfileDraft(d => ({ ...d, display_name: name }))); }
beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear(); localStorage.setItem('ashyq.activeProfile', 'A');
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network in synthetic validation controls'); }));
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never); vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'getProfile').mockImplementation(async id => profile(id)); vi.spyOn(api, 'listRuns').mockResolvedValue([]);
});
afterEach(() => { expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
it.each(['success', 'failure'] as const)('keeps the newer report after an old %s', async outcome => {
  const old = deferred<ProfileValidationReport>(); const next = deferred<ProfileValidationReport>();
  vi.spyOn(api, 'validateProfile').mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
  await mount(); await tick(); await edit('New input'); await tick(); expect(api.validateProfile).toHaveBeenCalledTimes(2);
  await act(async () => next.resolve(report('New input accepted')));
  await act(async () => { if (outcome === 'success') old.resolve(report('Old input')); else old.reject(new Error('Old failure')); });
  expect(store.validation?.summary).toBe('New input accepted');
});
it('hides the old report immediately when its checked draft changes', async () => {
  vi.spyOn(api, 'validateProfile').mockResolvedValue(report('Old input')); await mount(); await tick();
  expect(store.validation?.summary).toBe('Old input'); await edit('New input'); expect(store.validation).toBeNull();
});
it.each([['B'], ['B', 'A']])('rejects validation from an earlier case generation through %j', async (...cases: string[]) => {
  const old = deferred<ProfileValidationReport>(); vi.spyOn(api, 'validateProfile').mockReturnValue(old.promise); await mount(); await tick();
  for (const id of cases) { await act(async () => { await store.switchCase(id); }); await flush(); }
  await act(async () => old.resolve(report('Old case'))); expect(store.validation).toBeNull();
});
it('rejects validation when edits returned to the same serialized draft', async () => {
  const old = deferred<ProfileValidationReport>(); vi.spyOn(api, 'validateProfile').mockReturnValue(old.promise); await mount(); await tick();
  const name = String(store.profileDraft.display_name); await edit('Intermediate input'); await edit(name);
  await act(async () => old.resolve(report('Earlier input generation'))); expect(store.validation).toBeNull();
});
it('debounces unsent input while checking the exact latest draft', async () => {
  vi.spyOn(api, 'validateProfile').mockResolvedValue(report('Latest input')); await mount(); await edit('Intermediate input'); await edit('Latest input'); await tick();
  expect(api.validateProfile).toHaveBeenCalledOnce(); expect(vi.mocked(api.validateProfile).mock.calls[0]?.[0]).toEqual(store.profileDraft);
  expect(store.validation?.summary).toBe('Latest input');
});
