/** Deferred public-tool answers must never edit a newer applicant input. */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import { StoreProvider, useStore } from '@/lib/store';
import { profile } from '@/lib/securityMergeFixtures';
import { deferred } from '@/screens/preparationFixtures';
import { ProfileScreen } from './ProfileScreen';
import type { TranscriptReading } from '@/types';

let store: ReturnType<typeof useStore>;
const GPA = { raw_value: 4.8, raw_scale_max: 5, raw_scale_label: 'Synthetic scale' };
const method = { key: 'synthetic', description: 'Synthetic method', source: 'synthetic fixture', caveat: 'Not official', to_scale: '4' };
const reading: TranscriptReading = { note: 'Synthetic reading', suggestions: [{
  field: 'academics.gpa', label: 'Grade average', value: { raw_value: 4.82, raw_scale_max: 5 }, excerpt: 'Synthetic average 4.82/5',
}] };
const pdf = () => new File(['synthetic fixture'], 'synthetic.pdf', { type: 'application/pdf' });
function Probe() { store = useStore(); return <ProfileScreen onNext={() => {}} />; }
async function flush() { await act(async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); }); }
async function mount() { render(<StoreProvider><Probe /></StoreProvider>); await flush(); expect(store.savedProfile?.id).toBe('A'); }
async function switchTo(id: string) { await act(async () => { await store.switchCase(id); }); await flush(); }
const gpa = () => (store.profileDraft.academics as Record<string, unknown>).gpa as Record<string, unknown>;
async function editGrade(value: number) {
  await act(async () => { store.setProfileDraft(d => ({ ...d, academics: { ...(d.academics as Record<string, unknown>), gpa: { ...gpa(), raw_value: value } } })); });
}
beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.activeProfile', 'A');
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network in synthetic profile context controls'); }));
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never); vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'getProfile').mockImplementation(async id => ({ ...profile(id), academics: { ...profile(id).academics as Record<string, unknown>, gpa: { ...GPA, raw_value: id === 'A' ? 4.8 : 3.2 } } }));
  vi.spyOn(api, 'listRuns').mockResolvedValue([]);
  vi.spyOn(api, 'conversionMethods').mockResolvedValue({ methods: [method], note: '' });
  vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'Synthetic' });
});
afterEach(() => { expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([['B'], ['B', 'A']])('rejects a conversion from an earlier case generation through %j', async (...cases: string[]) => {
  const reply = deferred<Record<string, unknown>>(); vi.spyOn(api, 'previewConversion').mockReturnValue(reply.promise);
  await mount(); fireEvent.click(screen.getByTestId('convert-synthetic'));
  for (const id of cases) await switchTo(id);
  const current = structuredClone(gpa()); await act(async () => reply.resolve({ ...GPA, converted_value: 3.9 }));
  expect(gpa()).toEqual(current); expect(screen.queryByTestId('conversion-error')).toBeNull();
});
it.each([false, true])('rejects a preview after GPA editing, even when reverted: %s', async reverted => {
  const reply = deferred<Record<string, unknown>>(); vi.spyOn(api, 'previewConversion').mockReturnValue(reply.promise);
  await mount(); fireEvent.click(screen.getByTestId('convert-synthetic')); await editGrade(4.1); if (reverted) await editGrade(4.8);
  const current = structuredClone(gpa()); await act(async () => reply.resolve({ ...GPA, converted_value: 3.9 })); expect(gpa()).toEqual(current);
});
it.each(['success', 'error'] as const)('ignores an old conversion %s after a newer accepted preview', async outcome => {
  const old = deferred<Record<string, unknown>>(); const next = deferred<Record<string, unknown>>();
  vi.spyOn(api, 'previewConversion').mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
  await mount(); fireEvent.click(screen.getByTestId('convert-synthetic')); fireEvent.click(screen.getByTestId('convert-synthetic'));
  await act(async () => next.resolve({ ...GPA, converted_value: 3.9 }));
  await act(async () => { if (outcome === 'success') old.resolve({ ...GPA, converted_value: 2 }); else old.reject(new ApiError(400, 'Old refusal')); });
  expect(gpa().converted_value).toBe(3.9); expect(screen.queryByTestId('conversion-error')).toBeNull();
});
it.each([['B'], ['B', 'A']])('discards accepted transcript suggestions on case change through %j', async (...cases: string[]) => {
  vi.spyOn(api, 'readTranscript').mockResolvedValue(reading); await mount();
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } }); await flush();
  expect(screen.getByTestId('apply-academics.gpa')).toBeInTheDocument();
  for (const id of cases) await switchTo(id);
  expect(screen.queryByTestId('apply-academics.gpa')).toBeNull(); expect(screen.queryByTestId('transcript-note')).toBeNull();
});
it.each([['B'], ['B', 'A']])('rejects a pending transcript response through %j', async (...cases: string[]) => {
  const reply = deferred<TranscriptReading>(); vi.spyOn(api, 'readTranscript').mockReturnValue(reply.promise); await mount();
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });
  for (const id of cases) await switchTo(id);
  await act(async () => reply.resolve(reading));
  expect(screen.queryByTestId('apply-academics.gpa')).toBeNull(); expect(screen.queryByTestId('transcript-note')).toBeNull();
});
it('requires a fresh transcript choice after editing the input GPA', async () => {
  vi.spyOn(api, 'readTranscript').mockResolvedValue(reading); await mount();
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } }); await flush();
  expect(screen.getByTestId('apply-academics.gpa')).toBeInTheDocument(); await editGrade(4.1);
  expect(screen.queryByTestId('apply-academics.gpa')).toBeNull(); expect(gpa().raw_value).toBe(4.1);
});
it('retains only the newest transcript read and its explicit suggestion', async () => {
  const old = deferred<TranscriptReading>(); const next = deferred<TranscriptReading>();
  vi.spyOn(api, 'readTranscript').mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise); await mount();
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });
  await act(async () => next.resolve({ ...reading, note: 'Newest reading' })); await act(async () => old.resolve({ note: 'Old reading', suggestions: [] }));
  expect(screen.getByTestId('transcript-note')).toHaveTextContent('Newest reading');
  fireEvent.click(screen.getByTestId('apply-academics.gpa')); await flush(); expect(gpa().raw_value).toBe(4.82); expect(gpa().raw_scale_label).toBe(GPA.raw_scale_label);
});
it('withdraws an accepted suggestion when GPA was edited and reverted in one render batch', async () => {
  vi.spyOn(api, 'readTranscript').mockResolvedValue(reading); await mount();
  fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } }); await flush();
  expect(screen.getByTestId('apply-academics.gpa')).toBeInTheDocument();
  await act(async () => {
    store.setProfileDraft(d => ({ ...d, academics: { ...(d.academics as Record<string, unknown>), gpa: { ...GPA, raw_value: 4.1 } } }));
    store.setProfileDraft(d => ({ ...d, academics: { ...(d.academics as Record<string, unknown>), gpa: { ...GPA } } }));
  });
  expect(gpa().raw_value).toBe(4.8); expect(screen.queryByTestId('apply-academics.gpa')).toBeNull();
});
it('does not show methods returned for an earlier scale', async () => {
  const old = deferred<{ methods: typeof method[]; note: string }>();
  vi.mocked(api.conversionMethods).mockReturnValueOnce(old.promise).mockResolvedValue({ methods: [], note: '' }); await mount();
  await act(async () => store.setProfileDraft(d => ({ ...d, academics: { ...(d.academics as Record<string, unknown>), gpa: { ...gpa(), raw_scale_label: 'Different scale' } } })));
  await flush(); await act(async () => old.resolve({ methods: [method], note: '' })); expect(screen.queryByTestId('convert-synthetic')).toBeNull();
});
