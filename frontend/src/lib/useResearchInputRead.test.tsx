import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useResearchInputRead } from './useResearchInputRead';
import { api } from '@/api/client';
import { deferred } from '@/screens/preparationFixtures';
import { isResearchInputStatus, isResultFreshness } from './researchReadContext';
import type { RunView, StoredProfile } from '@/types';
const state = vi.hoisted(() => ({ id: 'A', epoch: 1, profile: { revision:1, id: 'A', display_name: 'Synthetic', created_at: '', updated_at: '' } as StoredProfile, runId: 'run-A' }));
vi.mock('./store', () => ({ useStore: () => ({ currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.id, case_epoch: state.epoch }), savedProfile: state.profile, run: { id: state.runId, profile_id: state.id } }) }));
function wire(id: string, profile: string, status: 'current' | 'changed' = 'current'): RunView {
  return { id, profile_id: profile, profile_input_status: { schema_version: 'research-input-status-v1', state: status, changed_sections: status === 'changed' ? ['academics'] : [], observed_at: '2026-10-14T00:00:00Z', applicability: 'not_assessed' } } as RunView;
}
beforeEach(() => { state.id = 'A'; state.epoch = 1; state.runId = 'run-A'; state.profile = { revision:1, id: 'A', display_name: 'Synthetic', created_at: '', updated_at: '' }; vi.spyOn(api, 'getRun').mockImplementation(async id => wire(id, state.id)); });
afterEach(() => vi.restoreAllMocks());
it('reads the owned run once and refreshes after a newly saved profile even with equal timestamp precision', async () => {
  const { result, rerender } = renderHook(() => useResearchInputRead()); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  rerender(); expect(api.getRun).toHaveBeenCalledOnce();
  vi.mocked(api.getRun).mockResolvedValueOnce(wire('run-A', 'A', 'changed')); state.profile = { ...state.profile }; rerender();
  expect(result.current.status).toBeNull(); await waitFor(() => expect(result.current.status?.state).toBe('changed')); expect(api.getRun).toHaveBeenCalledTimes(2);
});
it('rejects stale callbacks and late responses after A→B→A and preserves only confirmed same-profile reads on error', async () => {
  const old = deferred<RunView>(); vi.mocked(api.getRun).mockImplementationOnce(() => old.promise);
  const { result, rerender } = renderHook(() => useResearchInputRead()); const refreshA = result.current.refresh;
  state.id = 'B'; state.runId = 'run-B'; state.epoch = 2; state.profile = { ...state.profile, id: 'B' };
  await act(async () => expect(await refreshA()).toBe(false)); expect(api.getRun).toHaveBeenCalledOnce(); rerender(); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  state.id = 'A'; state.runId = 'run-A'; state.epoch = 3; state.profile = { ...state.profile, id: 'A' }; rerender();
  await act(async () => old.resolve(wire('run-A', 'A', 'changed'))); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  vi.mocked(api.getRun).mockRejectedValueOnce(new Error('Synthetic failure')); await act(async () => { await result.current.refresh(); });
  expect(result.current.status?.state).toBe('current'); expect(result.current.error).not.toBe('');
});
it('rejects copied readiness or malformed sections and keeps unavailable evidence without a fabricated zero', () => {
  expect(isResearchInputStatus(wire('run-A', 'A').profile_input_status)).toBe(true);
  expect(isResearchInputStatus({ ...wire('run-A', 'A').profile_input_status, applicability: 'ready' })).toBe(false);
  expect(isResearchInputStatus({ ...wire('run-A', 'A').profile_input_status, changed_sections: ['academics', 'academics'] })).toBe(false);
  expect(isResultFreshness({ schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'not_available', stale_claim_count: null, assessment: 'stored_evaluation' })).toBe(true);
  expect(isResultFreshness({ schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'not_available', stale_claim_count: 0, assessment: 'stored_evaluation' })).toBe(false);
});
