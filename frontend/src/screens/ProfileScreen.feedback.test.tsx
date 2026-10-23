import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { api } from '@/api/client';
import type { StoredProfile } from '@/types';
import { setLocale } from '@/lib/i18n';

const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
const saved = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), revision:1, id, created_at: '2026-01-01', updated_at: '2026-01-01' }) as StoredProfile;
function deferred() { let resolve!: () => void; let reject!: (e: Error) => void;
  const promise = new Promise<void>((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
async function flush() { await act(async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); }); }
beforeEach(() => {
  setLocale('en');
  state.value = { profileDraft: structuredClone(DEFAULT_PROFILE), setProfileDraft: vi.fn(),
    validation: null, savedProfile: saved('A'), caseEpoch: 0, dirty: true,
    currentAdmissionsCase: () => ({ scope: null, profile_id: (state.value.savedProfile as StoredProfile | null)?.id ?? null, case_epoch: state.value.caseEpoch }),
    currentProfileDraft: () => ({ draft: state.value.profileDraft, generation: 0, gpa_generation: 0 }),
    draftRestored: true, loading: false, saveProfile: vi.fn(), loadDemoProfile: vi.fn(), clearProfile: vi.fn(), discardDraft: vi.fn() };
  vi.spyOn(api, 'conversionMethods').mockResolvedValue({ methods: [], note: '' });
});
afterEach(() => { cleanup(); setLocale('en'); vi.useRealTimers(); vi.restoreAllMocks(); });
it('follows a section link in the mounted form without replacing the draft or sending a save', async () => {
  const oldHash=location.hash;
  history.replaceState(null,'','#/profile');
  const draft=state.value.profileDraft;
  const view=render(<ProfileScreen onNext={() => {}} />);
  history.replaceState(null,'','#/profile?section=academics');
  fireEvent(window,new HashChangeEvent('hashchange'));
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Education & grades');
  history.replaceState(null,'','#/profile?section=activities');
  fireEvent(window,new HashChangeEvent('hashchange'));
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Activities & achievements');
  expect(state.value.profileDraft).toBe(draft);
  expect(state.value.saveProfile).not.toHaveBeenCalled();
  view.unmount();history.replaceState(null,'',oldHash||'#/home');
  await flush();
});
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

it('shows a confirmed replay accepted outside this mounted screen without re-sending', async () => {
  const storeSave = vi.fn(); state.value.saveProfile = storeSave; state.value.dirty = false;
  state.value.savedProfile = { ...saved('A'), revision:2, write_receipt:{command_id:'11111111-2222-4333-8444-555555555555',kind:'update',profile_id:'A',expected_revision:1,accepted_revision:2} };
  render(<ProfileScreen onNext={() => {}} />); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Saved'); expect(storeSave).not.toHaveBeenCalled();
});
it('does not label newer local typing saved merely because a previous receipt exists', async () => {
  state.value.dirty = true; state.value.savedProfile = { ...saved('A'), revision:2, write_receipt:{command_id:'11111111-2222-4333-8444-555555555555',kind:'update',profile_id:'A',expected_revision:1,accepted_revision:2} };
  render(<ProfileScreen onNext={() => {}} />); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Unsaved changes');
});

it('keeps a lost-response recovery distinct from a confirmed refusal', async () => {
  state.value.profileRecovery = { entry: { status: 'unknown', command: { command_id: 'original-command' }, draft: structuredClone(DEFAULT_PROFILE) }, base: {}, message: 'The save outcome is unknown.' };
  state.value.saveProfile = vi.fn().mockRejectedValue(new Error('Lost response'));
  render(<ProfileScreen onNext={() => {}} />);
  fireEvent.click(screen.getByTestId('save-profile')); await flush();
  expect(screen.getByText('Review the save notice above. Your current draft is retained.')).toBeInTheDocument();
  expect(screen.queryByText('Not saved. Your edits are still in this form.')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirm original save' })).toBeInTheDocument();
});

it('does not expose a blank editable profile before the active case has hydrated', async () => {
  state.value.hydrated = false;
  const view = render(<ProfileScreen onNext={() => {}} />); await flush();
  expect(screen.getByRole('status')).toHaveTextContent('Loading your saved applicant profile');
  expect(screen.queryByTestId('save-profile')).not.toBeInTheDocument();
  state.value.hydrated = true; view.rerender(<ProfileScreen onNext={() => {}} />); await flush();
  expect(screen.getByTestId('save-profile')).toBeInTheDocument();
});

it.each(['refused','newer-typing','created'] as const)('book Save and continue respects %s outcome',async(outcome)=>{
  setLocale('ru');
  const call=deferred(); state.value.saveProfile=vi.fn(()=>call.promise);
  if(outcome==='created') state.value.savedProfile=null;
  const view=render(<ProfileScreen onNext={()=>{}}/>);
  fireEvent.click(screen.getByTestId('to-preferences'));
  expect(screen.getByTestId('to-preferences')).toBeDisabled();
  if(outcome==='newer-typing') state.value.profileDraft={...state.value.profileDraft as object,display_name:'Newer unsaved typing'};
  if(outcome==='created') {state.value.savedProfile=saved('created-A');state.value.dirty=false;}
  view.rerender(<ProfileScreen onNext={()=>{}}/>);
  if(outcome==='refused') call.reject(new Error('Save refused')); else call.resolve();
  await flush();
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent(outcome==='created'?'Образование и оценки':'Личные данные');
});

it('clears a superseded refusal after the current draft matches a freshly read server revision without claiming a new write',async()=>{
 const save=vi.fn().mockRejectedValue(new Error('Synthetic stale revision'));state.value.saveProfile=save;
 const view=render(<ProfileScreen onNext={()=>{}}/>);
 fireEvent.click(screen.getByTestId('save-profile'));await flush();
 expect(screen.getByRole('status')).toHaveTextContent('Not saved');
 state.value={...state.value,savedProfile:{...saved('A'),revision:2},dirty:false};
 view.rerender(<ProfileScreen onNext={()=>{}}/>);await flush();
 expect(screen.getByRole('status')).toBeEmptyDOMElement();
 expect(save).toHaveBeenCalledTimes(1);
});

it('opens the actual exam editor from one section navigation and retains its route', () => {
  window.history.replaceState(null,'','#/profile'); setLocale('ru');
  render(<ProfileScreen onNext={()=>{}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Экзамены'}));
  expect(window.location.hash).toBe('#/profile?section=exams');
  expect(screen.getByLabelText('IELTS overall')).toBeVisible();
  expect(screen.getByLabelText('Средний балл (GPA)')).not.toBeVisible();
  window.history.replaceState(null,'','#/profile');
});
it('keeps the applicant on the form when saving before Budget is refused', async () => {
  window.history.replaceState(null,'','#/profile'); setLocale('ru');
  const call=deferred(); const next=vi.fn(); state.value.saveProfile=vi.fn(()=>call.promise);
  render(<ProfileScreen onNext={next}/>);
  fireEvent.click(screen.getByRole('button',{name:'Бюджет'}));
  call.reject(new Error('Synthetic refusal')); await flush();
  expect(next).not.toHaveBeenCalled();
  expect(screen.getByRole('status')).toHaveTextContent('Не сохранено');
});
