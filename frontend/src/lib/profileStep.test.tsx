import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { clearProfileStep, migrateProfileStep, readProfileStep, useProfileStep } from './profileStep';

beforeEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });

it('restores a case after remount without leaking steps across cases', () => {
  const { result, rerender, unmount } = renderHook(({ key }) => useProfileStep(key), { initialProps: { key: 'A' } });
  act(() => result.current[1](4));
  rerender({ key: 'B' });
  expect(result.current[0]).toBe(0);
  act(() => result.current[1](2));
  rerender({ key: 'A' });
  expect(result.current[0]).toBe(4);
  unmount();
  expect(renderHook(() => useProfileStep('B')).result.current[0]).toBe(2);
});

it('waits for a known case identity without overwriting its stored step', () => {
  migrateProfileStep(null, 'A', 5);
  const { result, rerender } = renderHook(({ key }) => useProfileStep(key), { initialProps: { key: null as string | null } });
  act(() => result.current[1](1));
  expect(readProfileStep('A')).toBe(5);
  rerender({ key: 'A' });
  expect(result.current[0]).toBe(5);
  rerender({ key: null });
  expect(result.current[0]).toBe(0);
});

it.each(['-1', '6', '1.5', 'NaN', 'null', '{}', '', ' 3'])('rejects malformed stored step %s', (raw) => {
  sessionStorage.setItem('ashyq.profileStep.v1.A', raw);
  expect(readProfileStep('A')).toBe(0);
});

it('ignores invalid navigation and resets explicitly', () => {
  const { result } = renderHook(() => useProfileStep('A'));
  act(() => result.current[1](3));
  act(() => result.current[1](9));
  expect(result.current[0]).toBe(3);
  act(() => result.current[1](0));
  expect(readProfileStep('A')).toBe(0);
});

it('migrates a local case on save and clears only the requested slot', () => {
  migrateProfileStep(null, 'local:A', 4);
  migrateProfileStep('local:A', 'saved:A', 4);
  expect(readProfileStep('saved:A')).toBe(4);
  expect(sessionStorage.getItem('ashyq.profileStep.v1.local:A')).toBeNull();
  migrateProfileStep(null, 'B', 2);
  clearProfileStep('saved:A');
  expect(readProfileStep('saved:A')).toBe(0);
  expect(readProfileStep('B')).toBe(2);
});

it('keeps navigation usable when storage is unavailable', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied'); });
  const { result } = renderHook(() => useProfileStep('A'));
  act(() => result.current[1](3));
  expect(result.current[0]).toBe(3);
});
