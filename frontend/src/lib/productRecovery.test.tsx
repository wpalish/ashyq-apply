import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from '@/lib/store';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { writeDraftEnvelope } from '@/lib/caseDrafts';
import type { ProgramResult } from '@/types';
const profile = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), id, display_name: `Saved ${id}`, created_at: '2026-01-01', updated_at: '2026-01-01' });
const run = (id: string) => ({ id, profile_id: id.toUpperCase(), stage: 'failed', job_running: false, job_status: 'failed' });
const row = (id: string) => ({ id, claims: [] }) as unknown as ProgramResult;
function Probe() {
  const s = useStore();
  return <div>
  <span data-testid="draft-name">{String(s.profileDraft.display_name)}</span>
  <span data-testid="dirty">{String(s.dirty)}</span>
  <span data-testid="case">{s.savedProfile?.id ?? 'none'}</span>
  <span data-testid="rows">{s.results.map(r => r.id).join(',')}</span>
  <button onClick={() => s.setProfileDraft(d => ({ ...d, display_name: 'Unsaved marker' }))}>edit</button>
  <button onClick={() => s.newCase()}>new</button>
  <button onClick={() => s.discardDraft()}>discard</button>
  <button onClick={() => void s.switchCase('B')}>B</button>
  <button onClick={() => void s.refreshResults()}>refresh</button>
  </div>;
}
async function flush() { await act(async () => { for (let i = 0; i < 15; i++)
  await Promise.resolve(); }); }
async function tick(ms: number) { await act(async () => { vi.advanceTimersByTime(ms); for (let i = 0; i < 15; i++)
  await Promise.resolve(); }); }
function markerStored() { return Array.from({ length: localStorage.length }, (_, i) => localStorage.getItem(localStorage.key(i)!)).some(v => v?.includes('Unsaved marker')); }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); vi.useFakeTimers(); vi.spyOn(api, 'capabilities').mockResolvedValue({} as never); vi.spyOn(api, 'cases').mockResolvedValue([]); vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok' }); vi.spyOn(api, 'results').mockResolvedValue([]); vi.spyOn(api, 'summary').mockResolvedValue({} as never); vi.spyOn(api, 'shortlist').mockResolvedValue({} as never); vi.spyOn(api, 'conversionMethods').mockResolvedValue({ methods: [], note: '' }); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
it('first onboarding persists edits without requiring New applicant', async () => {
  const v = render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  fireEvent.click(screen.getByText('edit'));
  await tick(1000);
  expect(screen.getByTestId('draft-name')).toHaveTextContent('Unsaved marker');
  expect(screen.getByTestId('dirty')).toHaveTextContent('true');
  expect(markerStored()).toBe(true);
  v.unmount();
  const second = render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  expect(screen.getByTestId('draft-name')).toHaveTextContent('Unsaved marker');
  await tick(600);
  second.unmount();
  render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  expect(screen.getByTestId('draft-name')).toHaveTextContent('Unsaved marker');
});
it('discarding a recovered local draft resets and preserves the blank case', async () => {
  const v = render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  fireEvent.click(screen.getByText('new'));
  fireEvent.click(screen.getByText('edit'));
  await tick(600);
  v.unmount();
  const second = render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  fireEvent.click(screen.getByText('discard'));
  await flush();
  expect(screen.getByTestId('draft-name')).toHaveTextContent('New applicant');
  expect(screen.getByTestId('dirty')).toHaveTextContent('false');
  expect(markerStored()).toBe(false);
  second.unmount();
  render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  expect(screen.getByTestId('draft-name')).toHaveTextContent('New applicant');
  fireEvent.click(screen.getByText('edit'));
  await tick(600);
  expect(markerStored()).toBe(true);
});
it('late result refresh from case A cannot overwrite case B rows', async () => {
  sessionStorage.setItem('ashyq.activeProfile', 'A');
  sessionStorage.setItem('ashyq.activeRun', 'a');
  vi.spyOn(api, 'getProfile').mockImplementation(async (id) => profile(id) as never);
  vi.spyOn(api, 'getRun').mockResolvedValue(run('a') as never);
  vi.spyOn(api, 'listRuns').mockResolvedValue([run('b')] as never);
  const delayed = deferred<ProgramResult[]>();
  let slow = false;
  vi.mocked(api.results).mockImplementation((id) => id === 'a' && slow ? delayed.promise : Promise.resolve([row(id)]) as never);
  render(<StoreProvider><Probe /></StoreProvider>);
  await flush();
  slow = true;
  fireEvent.click(screen.getByText('refresh'));
  await flush();
  fireEvent.click(screen.getByText('B'));
  await flush();
  expect(screen.getByTestId('case')).toHaveTextContent('B');
  expect(screen.getByTestId('rows')).toHaveTextContent('b');
  delayed.resolve([row('A old result')]);
  await flush();
  expect(screen.getByTestId('case')).toHaveTextContent('B');
  expect(screen.getByTestId('rows')).toHaveTextContent('b');
});
it('recovered server draft stays local until explicit Save', async () => {
  sessionStorage.setItem('ashyq.activeProfile', 'A');
  vi.spyOn(api, 'getProfile').mockResolvedValue(profile('A') as never);
  writeDraftEnvelope('A', { ...structuredClone(DEFAULT_PROFILE), display_name: 'Unsaved marker' }, '2026-01-01');
  const update = vi.spyOn(api, 'updateProfile').mockImplementation(async (id, p) => ({ ...p as object, id, created_at: '2026-01-01', updated_at: '2026-01-02' }) as never);
  render(<StoreProvider><ProfileScreen onNext={() => { }}/></StoreProvider>);
  await flush();
  expect(screen.getByTestId('draft-restored')).toHaveTextContent('untouched until you press Save');
  await tick(3000);
  expect(update).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId('save-profile'));
  await flush();
  expect(update).toHaveBeenCalledTimes(1);
  expect(update).toHaveBeenCalledWith('A', expect.objectContaining({ display_name: 'Unsaved marker' }));
  expect(markerStored()).toBe(false);
});
