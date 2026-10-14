import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { api } from '@/api/client';
import type { StoredProfile } from '@/types';

const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
const saved = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), revision:1, id, created_at: '2026-01-01', updated_at: '2026-01-01' }) as StoredProfile;
function deferred() { let resolve!: () => void; let reject!: (e: Error) => void;
  const promise = new Promise<void>((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
async function flush() { await act(async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); }); }
beforeEach(() => {
  state.value = { profileDraft: structuredClone(DEFAULT_PROFILE), setProfileDraft: vi.fn(),
    validation: null, savedProfile: saved('A'), caseEpoch: 0, dirty: true,
    currentAdmissionsCase: () => ({ scope: null, profile_id: (state.value.savedProfile as StoredProfile | null)?.id ?? null, case_epoch: state.value.caseEpoch }),
    currentProfileDraft: () => ({ draft: state.value.profileDraft, generation: 0, gpa_generation: 0 }),
    draftRestored: true, loading: false, saveProfile: vi.fn(), loadDemoProfile: vi.fn(), clearProfile: vi.fn(), discardDraft: vi.fn() };
  vi.spyOn(api, 'conversionMethods').mockResolvedValue({ methods: [], note: '' });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
it('announces an actual pending save and acknowledges only its resolved clean profile', async () => {
  const call = deferred(); state.value.saveProfile = vi.fn(() => call.promise);
  render(<ProfileScreen onNext={() => {}} />); fireEvent.click(screen.getByTestId('save-profile'));
  expect(screen.getByTestId('save-profile')).toBeDisabled(); expect(screen.getByTestId('save-profile')).toHaveAttribute('aria-busy', 'true');
  expect(screen.getByRole('status')).toHaveTextContent('Saving…'); expect(screen.getByRole('status')).not.toHaveTextContent('Saved');
  state.value.dirty = false; call.resolve(); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Saved'); expect(screen.getByTestId('save-profile')).toBeEnabled();
});
it('keeps a rejected save from announcing success and permits retry', async () => {
  const call = deferred(); const saveProfile = vi.fn(() => call.promise); state.value.saveProfile = saveProfile;
  render(<ProfileScreen onNext={() => {}} />); fireEvent.click(screen.getByTestId('save-profile')); call.reject(new Error('Synthetic refusal')); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Not saved. Your edits are still in this form.');
  expect(screen.getByRole('status')).not.toHaveTextContent(/^Saved$/); expect(screen.getByTestId('save-profile')).toBeEnabled();
});
it.each(['resolve', 'reject'] as const)('ignores a late %s from a save belonging to the previous case', async outcome => {
  const call = deferred(); state.value.saveProfile = vi.fn(() => call.promise);
  const view = render(<ProfileScreen onNext={() => {}} />); fireEvent.click(screen.getByTestId('save-profile'));
  state.value = { ...state.value, savedProfile: saved('B'), caseEpoch: 1, dirty: false };
  view.rerender(<ProfileScreen onNext={() => {}} />); await flush();
  if (outcome === 'resolve') call.resolve(); else call.reject(new Error('Late A failure')); await flush();
  expect(screen.getByRole('status')).toBeEmptyDOMElement(); expect(screen.getByTestId('save-profile')).toBeEnabled();
});
it('acknowledges creation of a local case when saving gives it a server id', async () => {
  const call = deferred(); state.value.savedProfile = null; state.value.saveProfile = vi.fn(() => call.promise);
  const view = render(<ProfileScreen onNext={() => {}} />); fireEvent.click(screen.getByTestId('save-profile'));
  state.value = { ...state.value, savedProfile: saved('created-A'), dirty: false };
  view.rerender(<ProfileScreen onNext={() => {}} />); call.resolve(); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Saved');
});
it('does not describe a case read or other store loading as Saving', async () => {
  state.value.loading = true; state.value.dirty = false;
  render(<ProfileScreen onNext={() => {}} />); await flush();
  expect(screen.getByTestId('save-profile')).toHaveTextContent('Please wait…'); expect(screen.getByTestId('save-profile')).toBeDisabled();
  expect(screen.getByRole('status')).not.toHaveTextContent('Saving');
});
it('does not show Saved while edits made during the request remain dirty', async () => {
  state.value.saveProfile = vi.fn().mockResolvedValue(undefined);
  render(<ProfileScreen onNext={() => {}} />); fireEvent.click(screen.getByTestId('save-profile')); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Unsaved changes');
});

it('does not automatically retry an unchanged failed saved draft and allows an explicit Save retry', async () => {
  vi.useFakeTimers();
  state.value.draftRestored = false;
  const call = deferred(); const save = vi.fn(() => call.promise); state.value.saveProfile = save;
  const view = render(<ProfileScreen onNext={() => {}} />);
  await act(async () => { vi.advanceTimersByTime(1500); }); await flush();
  expect(save).toHaveBeenCalledTimes(1);
  // Model the Store busy interval and its release after the API rejects.
  state.value.loading = true; view.rerender(<ProfileScreen onNext={() => {}} />); await flush();
  state.value.loading = false; call.reject(new Error('Synthetic permanent 503'));
  view.rerender(<ProfileScreen onNext={() => {}} />); await flush();
  await act(async () => { vi.advanceTimersByTime(20_000); }); await flush();
  expect(save).toHaveBeenCalledTimes(1); expect(screen.getByRole('status')).toHaveTextContent('Not saved');
  save.mockImplementationOnce(async () => { state.value.dirty = false; });
  fireEvent.click(screen.getByTestId('save-profile')); await flush();
  expect(save).toHaveBeenCalledTimes(2); expect(screen.getByRole('status')).toHaveTextContent('Saved');
});
it('a new semantic edit after failure permits one autosave without relying on an input-specific handler', async () => {
  vi.useFakeTimers(); state.value.draftRestored = false;
  const save = vi.fn().mockRejectedValueOnce(new Error('Synthetic 503')).mockImplementationOnce(async () => { state.value.dirty = false; });
  state.value.saveProfile = save; const view = render(<ProfileScreen onNext={() => {}} />);
  fireEvent.click(screen.getByTestId('save-profile')); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Not saved');
  await act(async () => { vi.advanceTimersByTime(5000); }); await flush(); expect(save).toHaveBeenCalledTimes(1);
  // A transcript, conversion or list editor may replace the draft directly.
  state.value.profileDraft = { ...state.value.profileDraft as Record<string, unknown>, display_name: 'A newer semantic edit' };
  view.rerender(<ProfileScreen onNext={() => {}} />); await flush();
  await act(async () => { vi.advanceTimersByTime(1500); }); await flush();
  expect(save).toHaveBeenCalledTimes(2); expect(screen.getByRole('status')).toHaveTextContent('Saved');
});
