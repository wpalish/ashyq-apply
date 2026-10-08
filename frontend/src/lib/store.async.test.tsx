import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { StoreProvider, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import type { ProgramResult, RunView, StoredProfile } from '@/types';

let store!: ReturnType<typeof useStore>;
function Probe() {
  store = useStore();
  return <div><span data-testid="run">{store.run?.id}</span><span data-testid="rows">{store.results.map((r) => r.id).join(',')}</span><span data-testid="error">{store.error}</span></div>;
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((r) => { resolve = r; }); return { promise, resolve }; }
const profile = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), id, created_at: '', updated_at: '' }) as StoredProfile;
const run = (id: string) => ({ id, profile_id: id, stage: 'completed', job_running: false, job_status: 'succeeded' }) as RunView;
const row = (id: string) => ({ id, document_progress: {} }) as ProgramResult;
beforeEach(() => {
  vi.restoreAllMocks(); window.localStorage.clear(); window.sessionStorage.clear();
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'getProfile').mockImplementation(async (id) => profile(id));
  vi.spyOn(api, 'listRuns').mockImplementation(async (id) => [run(id!)]);
  vi.spyOn(api, 'results').mockImplementation(async (id) => [row(id)]);
  vi.spyOn(api, 'summary').mockResolvedValue({} as never);
  vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({} as never);
});
async function open(id: string) { await act(async () => { await store.switchCase(id); }); await waitFor(() => expect(screen.getByTestId('run')).toHaveTextContent(id)); }

it('ignores a late result refresh belonging to the previous applicant', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<ProgramResult[]>(); vi.mocked(api.results).mockImplementation(async (id) => id === 'A' ? pending.promise : [row(id)]);
  let refresh!: Promise<void>; act(() => { refresh = store.refreshResults(); });
  await open('B');
  await act(async () => { pending.resolve([row('late-A')]); await refresh; });
  expect(screen.getByTestId('rows')).toHaveTextContent('B');
  expect(screen.getByTestId('rows')).not.toHaveTextContent('late-A');
});

it.each(['cancelRun', 'retryRun', 'recheckNow', 'collectDocuments'] as const)('ignores a late %s response after switching applicants', async (method) => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<RunView>(); vi.spyOn(api, method).mockReturnValue(pending.promise);
  let action!: Promise<unknown>; act(() => { action = store[method](); }); await open('B');
  await act(async () => { pending.resolve(run('A')); await action; });
  expect(screen.getByTestId('run')).toHaveTextContent('B');
});

it('does not clear the newly opened applicant after deletion of the old one', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<{ status: string }>(); vi.spyOn(api, 'deleteProfile').mockReturnValue(pending.promise as never);
  let action!: Promise<boolean>; act(() => { action = store.deleteEverything(); }); await open('B');
  await act(async () => { pending.resolve({ status: 'deleted' }); expect(await action).toBe(false); });
  expect(screen.getByTestId('run')).toHaveTextContent('B');
  expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBe('B');
});

it('a late GET cannot erase a freshly saved document mark on the same run', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<ProgramResult[]>(); vi.mocked(api.results).mockReturnValue(pending.promise);
  let refresh!: Promise<void>; act(() => { refresh = store.refreshResults(); });
  vi.spyOn(api, 'setDocumentProgress').mockResolvedValue({ ...row('A'), document_progress: { document: true } });
  await act(async () => { expect(await store.setDocumentProgress('A', 'document', true)).toBe(true); });
  await act(async () => { pending.resolve([row('A')]); await refresh; });
  expect(store.results[0]?.document_progress).toEqual({ document: true });
});

it('opening a case whose result read fails never leaves old rows underneath it', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  vi.mocked(api.results).mockRejectedValue(new Error('offline'));
  await open('B'); expect(store.results).toEqual([]);
});

it('a fresh case releases loading while an obsolete save is still pending', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); const pending = deferred<StoredProfile>(); vi.spyOn(api, 'createProfile').mockReturnValue(pending.promise);
  let save!: Promise<boolean>; act(() => { save = store.saveProfile(); }); expect(store.loading).toBe(true);
  act(() => store.newCase()); expect(store.loading).toBe(false);
  await act(async () => { pending.resolve(profile('old')); expect(await save).toBe(false); });
  expect(store.savedProfile).toBeNull();
});

it('a confirmed deletion resets the form and releases an obsolete pending save', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<StoredProfile>(); vi.spyOn(api, 'updateProfile').mockReturnValue(pending.promise);
  vi.spyOn(api, 'deleteProfile').mockResolvedValue({ status: 'deleted' } as never);
  let save!: Promise<boolean>; act(() => { save = store.saveProfile(); });
  expect(store.loading).toBe(true);
  await act(async () => { expect(await store.deleteEverything()).toBe(true); });
  expect(store.loading).toBe(false); expect(store.savedProfile).toBeNull();
  expect(store.profileDraft.display_name).toBe('New applicant'); expect(store.validation).toBeNull();
  await act(async () => { pending.resolve(profile('A')); expect(await save).toBe(false); });
  expect(store.loading).toBe(false); expect(store.profileDraft.display_name).toBe('New applicant');
});

it('a confirmed first save survives unavailable case metadata and does not create a duplicate', async () => {
  render(<StoreProvider><Probe /></StoreProvider>);
  await waitFor(() => expect(store.hydrated).toBe(true));
  const key = store.profileViewKey;
  const create = vi.spyOn(api, 'createProfile').mockResolvedValue(profile('new'));
  const update = vi.spyOn(api, 'updateProfile').mockResolvedValue(profile('new'));
  vi.mocked(api.cases).mockRejectedValue(new Error('list offline'));
  await act(async () => { expect(await store.saveProfile()).toBe(true); });
  expect(store.savedProfile?.id).toBe('new'); expect(store.profileViewKey).toBe(key);
  expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBe('new');
  await act(async () => { expect(await store.saveProfile()).toBe(true); });
  expect(create).toHaveBeenCalledTimes(1); expect(update).toHaveBeenCalledTimes(1);
});

it('starting research binds a newly created profile even when case metadata is unavailable', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await waitFor(() => expect(store.hydrated).toBe(true));
  vi.spyOn(api, 'createProfile').mockResolvedValue(profile('new'));
  vi.spyOn(api, 'startRun').mockResolvedValue(run('new'));
  vi.mocked(api.cases).mockRejectedValue(new Error('list offline'));
  await act(async () => { expect(await store.startRun(true)).toBe(true); });
  expect(store.savedProfile?.id).toBe('new'); expect(store.run?.id).toBe('new');
});

it('a delayed case-switch read cannot erase document progress acknowledged on that same case', async () => {
  render(<StoreProvider><Probe /></StoreProvider>); await open('A');
  const pending = deferred<ProgramResult[]>();
  vi.mocked(api.results).mockReturnValueOnce(pending.promise).mockResolvedValue([row('B')]);
  let switching!: Promise<void>; act(() => { switching = store.switchCase('B'); });
  await waitFor(() => expect(store.run?.id).toBe('B'));
  await act(async () => { await store.refreshResults(); });
  vi.spyOn(api, 'setDocumentProgress').mockResolvedValue({ ...row('B'), document_progress: { document: true } });
  await act(async () => { expect(await store.setDocumentProgress('B', 'document', true)).toBe(true); });
  await act(async () => { pending.resolve([row('B')]); await switching; });
  expect(store.results[0]?.document_progress).toEqual({ document: true });
});
