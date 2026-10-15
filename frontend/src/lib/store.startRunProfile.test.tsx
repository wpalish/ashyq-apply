import { profileAck } from '@/lib/profileWriteFixtures';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import { ApiError, api } from '@/api/client';
import { deferred } from '@/screens/preparationFixtures';
import type { RunView, StoredProfile } from '@/types';
const A = { ...structuredClone(DEFAULT_PROFILE), revision:1, id: 'synthetic-case-A', created_at: '2026-10-14T00:00:00Z', updated_at: '2026-10-14T00:00:00Z' } as unknown as StoredProfile;
const run = { id: 'synthetic-run-A', profile_id: A.id, stage: 'completed', results_count: 0 } as RunView;
function savedBudget(value: number) {
  return { ...A, funding: { ...(A.funding as Record<string, unknown>), max_annual_budget: value }, updated_at: '2026-10-14T00:00:01Z' } as StoredProfile;
}
function Probe() {
  const state = useStore();
  return <><output data-testid="profile">{state.savedProfile?.id ?? 'none'}</output><output data-testid="saved-budget">{String((state.savedProfile?.funding as Record<string, unknown> | undefined)?.max_annual_budget)}</output>
    <output data-testid="draft-budget">{String((state.profileDraft.funding as Record<string, unknown>)?.max_annual_budget)}</output>
    <output data-testid="dirty">{String(state.dirty)}</output><output data-testid="run">{state.run?.id ?? 'none'}</output>
    <button onClick={() => state.setProfileDraft(draft => ({ ...draft, funding: { ...(draft.funding as Record<string, unknown>), max_annual_budget: 10000 } }))}>edit</button>
    <button onClick={() => state.setProfileDraft(draft => ({ ...draft, funding: { ...(draft.funding as Record<string, unknown>), max_annual_budget: 20000 } }))}>keep typing</button>
    <button onClick={() => void state.startRun(true)}>start</button><button onClick={state.newCase}>new case</button></>;
}
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); vi.restoreAllMocks();
  localStorage.setItem('ashyq.activeProfile', A.id); localStorage.setItem('ashyq.activeRun', run.id);
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never); vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'getProfile').mockResolvedValue(A); vi.spyOn(api, 'getRun').mockResolvedValue(run);
  vi.spyOn(api, 'results').mockResolvedValue([]); vi.spyOn(api, 'summary').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok' });
  vi.spyOn(api, 'startRun').mockRejectedValue(new ApiError(503, 'Synthetic run start unavailable'));
});
afterEach(() => vi.restoreAllMocks());
async function mount() {
  render(<StoreProvider><Probe /></StoreProvider>); await waitFor(() => expect(screen.getByTestId('profile')).toHaveTextContent(A.id));
  await waitFor(() => expect(screen.getByTestId('run')).toHaveTextContent(run.id));
}
it('accepts the durable normalized profile and baseline even when the following run POST fails', async () => {
  vi.spyOn(api, 'updateProfile').mockImplementation(async (_id,_body,command) => profileAck(savedBudget(10000),command)); await mount(); fireEvent.click(screen.getByText('edit'));
  expect(screen.getByTestId('dirty')).toHaveTextContent('true'); fireEvent.click(screen.getByText('start'));
  await waitFor(() => expect(api.startRun).toHaveBeenCalledOnce());
  expect(screen.getByTestId('saved-budget')).toHaveTextContent('10000'); expect(screen.getByTestId('draft-budget')).toHaveTextContent('10000');
  expect(screen.getByTestId('dirty')).toHaveTextContent('false'); expect(screen.getByTestId('run')).toHaveTextContent(run.id);
});
it('keeps newer typing against the accepted server baseline while retaining the old run after failure', async () => {
  const response = deferred<StoredProfile>(); vi.spyOn(api, 'updateProfile').mockReturnValue(response.promise); await mount();
  fireEvent.click(screen.getByText('edit')); fireEvent.click(screen.getByText('start')); await waitFor(() => expect(api.updateProfile).toHaveBeenCalledOnce());
  fireEvent.click(screen.getByText('keep typing')); await act(async () => response.resolve(profileAck(savedBudget(10000),vi.mocked(api.updateProfile).mock.calls[0]![2])));
  await waitFor(() => expect(api.startRun).toHaveBeenCalledOnce()); expect(screen.getByTestId('saved-budget')).toHaveTextContent('10000');
  expect(screen.getByTestId('draft-budget')).toHaveTextContent('20000'); expect(screen.getByTestId('dirty')).toHaveTextContent('true'); expect(screen.getByTestId('run')).toHaveTextContent(run.id);
});
it('rejects a stale saved-profile completion after a newer case intent without starting the old research', async () => {
  const response = deferred<StoredProfile>(); vi.spyOn(api, 'updateProfile').mockReturnValue(response.promise); await mount();
  fireEvent.click(screen.getByText('edit')); fireEvent.click(screen.getByText('start')); await waitFor(() => expect(api.updateProfile).toHaveBeenCalledOnce());
  fireEvent.click(screen.getByText('new case')); await act(async () => response.resolve(profileAck(savedBudget(10000),vi.mocked(api.updateProfile).mock.calls[0]![2])));
  expect(screen.getByTestId('profile')).toHaveTextContent('none'); expect(screen.getByTestId('run')).toHaveTextContent('none'); expect(api.startRun).not.toHaveBeenCalled();
});
