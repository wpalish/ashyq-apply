import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useAdmissionsToday } from './useAdmissionsToday';
import { api } from '@/api/client';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import { deferred } from '@/screens/preparationFixtures';
import { isTodayProjection, type TodayProjectionV1 } from '@/types/admissionsActions';
const state = vi.hoisted(() => ({ id: 'A', epoch: 1 }));
vi.mock('./store', () => ({ useStore: () => ({ currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.id, case_epoch: state.epoch }) }) }));
beforeEach(() => { state.id = 'A'; state.epoch = 1; vi.spyOn(api, 'admissionsToday').mockImplementation(async id => emptyToday(id)); });
afterEach(() => vi.restoreAllMocks());
it('reads the native projection once even when a store getter function changes identity', async () => {
  const { result, rerender } = renderHook(() => useAdmissionsToday()); await waitFor(() => expect(result.current.value?.profile_id).toBe('A'));
  rerender(); expect(api.admissionsToday).toHaveBeenCalledOnce(); expect(isTodayProjection(result.current.value)).toBe(true);
});
it('keeps last confirmed own data on failed refresh and rejects a foreign profile response', async () => {
  const { result } = renderHook(() => useAdmissionsToday()); await waitFor(() => expect(result.current.value?.profile_id).toBe('A'));
  vi.mocked(api.admissionsToday).mockResolvedValueOnce(emptyToday('B')); await act(async () => { await result.current.refresh(); });
  expect(result.current.value?.profile_id).toBe('A'); expect(result.current.error).not.toBe('');
});
it('fences late A→B→A reads and old callbacks before React rerenders', async () => {
  const old = deferred<TodayProjectionV1>(); const fresh = deferred<TodayProjectionV1>();
  vi.mocked(api.admissionsToday).mockImplementationOnce(() => old.promise).mockResolvedValueOnce(emptyToday('B')).mockImplementationOnce(() => fresh.promise);
  const { result, rerender } = renderHook(() => useAdmissionsToday()); const oldRefresh = result.current.refresh;
  state.id = 'B'; state.epoch = 2; await act(async () => { expect(await oldRefresh()).toBe(false); });
  expect(api.admissionsToday).toHaveBeenCalledOnce(); rerender(); await waitFor(() => expect(result.current.value?.profile_id).toBe('B'));
  state.id = 'A'; state.epoch = 3; rerender(); await act(async () => old.resolve(emptyToday('A'))); expect(result.current.value).toBeNull();
  await act(async () => fresh.resolve(emptyToday('A'))); expect(result.current.value?.profile_id).toBe('A');
});
it('rejects unknown shapes, foreign plan head, fabricated readiness and duplicate IDs', () => {
  const value = emptyToday(); expect(isTodayProjection(value)).toBe(true);
  expect(isTodayProjection({ ...value, readiness: 'ready' })).toBe(false); expect(isTodayProjection({ ...value, extra: 1 })).toBe(false);
  expect(isTodayProjection({ ...value, consistency: 'mixed_revision', needs_refresh: false })).toBe(false);
});
