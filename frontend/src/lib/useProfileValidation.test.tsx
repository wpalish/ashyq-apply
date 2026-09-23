import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { useProfileValidation } from './useProfileValidation';
import type { ProfileValidationReport } from '@/types';

const report: ProfileValidationReport = { gaps: [], can_proceed: true, blocking_count: 0, summary: 'current' };
function deferred() {
  let resolve!: (value: ProfileValidationReport) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<ProfileValidationReport>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const tick = () => act(async () => { await vi.advanceTimersByTimeAsync(400); });
beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

it('debounces edits and exposes only the current draft report', async () => {
  const validate = vi.spyOn(api, 'validateProfile').mockResolvedValue(report);
  const { result, rerender } = renderHook(({ draft }) => useProfileValidation(draft, true), { initialProps: { draft: {} } });
  rerender({ draft: { version: 2 } });
  expect(validate).not.toHaveBeenCalled();
  await tick();
  expect(validate).toHaveBeenCalledTimes(1);
  expect(result.current.validation).toBe(report);
  rerender({ draft: { version: 3 } });
  expect(result.current.validation).toBeNull();
  expect(result.current.validationStatus).toBe('pending');
});

it.each(['success', 'failure'])('ignores a late old %s after the newer response', async (outcome) => {
  const old = deferred();
  vi.spyOn(api, 'validateProfile').mockReturnValueOnce(old.promise).mockResolvedValue(report);
  const { result, rerender } = renderHook(({ draft }) => useProfileValidation(draft, true), { initialProps: { draft: {} } });
  await tick();
  rerender({ draft: { newCase: true } });
  await tick();
  await act(async () => { if (outcome === 'success') old.resolve({ ...report, can_proceed: false }); else old.reject(new Error('old')); });
  expect(result.current.validation).toBe(report);
  expect(result.current.validationStatus).toBe('ready');
});

it('reports unavailable checks and retries without stale readiness', async () => {
  vi.spyOn(api, 'validateProfile').mockRejectedValueOnce(new Error('offline')).mockResolvedValue(report);
  const draft = {};
  const { result } = renderHook(() => useProfileValidation(draft, true));
  await tick();
  expect(result.current.validationStatus).toBe('error');
  act(() => result.current.retryValidation());
  expect(result.current.validationStatus).toBe('pending');
  await tick();
  expect(result.current.validation).toBe(report);
});

it('distinguishes invalid input from unavailable validation', async () => {
  vi.spyOn(api, 'validateProfile').mockRejectedValue(new ApiError(422, 'invalid'));
  const draft = {};
  const { result } = renderHook(() => useProfileValidation(draft, true));
  await tick();
  expect(result.current.validationStatus).toBe('invalid');
  expect(result.current.validation).toBeNull();
});

it('waits for hydration and cancels a pending timer on unmount', async () => {
  const validate = vi.spyOn(api, 'validateProfile').mockResolvedValue(report);
  const draft = {};
  const { rerender, unmount } = renderHook(({ enabled }) => useProfileValidation(draft, enabled), { initialProps: { enabled: false } });
  await tick();
  expect(validate).not.toHaveBeenCalled();
  rerender({ enabled: true });
  unmount();
  await tick();
  expect(validate).not.toHaveBeenCalled();
});

it('invalidates a previous report when hydration restarts with the same draft', async () => {
  vi.spyOn(api, 'validateProfile').mockResolvedValue(report);
  const draft = {};
  const { result, rerender } = renderHook(({ enabled }) => useProfileValidation(draft, enabled), { initialProps: { enabled: true } });
  await tick();
  expect(result.current.validation).toBe(report);
  rerender({ enabled: false });
  rerender({ enabled: true });
  expect(result.current.validation).toBeNull();
  expect(result.current.validationStatus).toBe('pending');
  await tick();
  expect(result.current.validation).toBe(report);
});
