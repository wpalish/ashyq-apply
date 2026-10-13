from pathlib import Path
s=Path(__file__).resolve().parent;out=s/'today5a-proposal';pre=s/'today5a-preimages'
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
put('frontend/src/lib/admissionsNavigation.test.ts','''import { expect, it } from 'vitest';
import { parseAdmissionsTarget, targetHref } from './admissionsNavigation';
it.each(['document_task', 'application', 'result'] as const)('preserves exact own %s IDs with reserved characters', kind => {
  const value = { profileId: 'A', screen: kind === 'document_task' ? 'documents' as const : kind === 'application' ? 'approved' as const : 'sources' as const, target: { kind, id: 'same/name+second' } };
  expect(parseAdmissionsTarget(targetHref(value))).toEqual(value);
});
it('preserves an exact lesson/version and rejects duplicate, unsupported or mismatched parameters', () => {
  const value = { profileId: 'A', screen: 'preparation' as const, target: { kind: 'lesson' as const, id: 'task-1', lesson_id: 'lesson-1', content_version: 'v1' } };
  expect(parseAdmissionsTarget(targetHref(value))).toEqual(value);
  expect(parseAdmissionsTarget('#/documents?case=A&kind=document_task&id=1&id=2')).toBeNull();
  expect(parseAdmissionsTarget('#/documents?case=A&kind=application&id=1')).toBeNull();
  expect(parseAdmissionsTarget('#/sources?case=A&kind=result&id=1&name=University')).toBeNull();
});
''')
put('frontend/src/lib/useAdmissionsToday.test.tsx','''import { act, renderHook, waitFor } from '@testing-library/react';
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
''')
put('frontend/src/components/AdmissionsTodayPanel.test.tsx','''import { render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { AdmissionsTodayPanel } from './AdmissionsTodayPanel';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import { setLocale } from '@/lib/i18n';
let value = emptyToday(); let error = '';
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ profileId: 'A', value, loading: false, error, refresh: vi.fn() }) }));
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => ({ current: acceptedActions().current, refresh: vi.fn() }) }));
beforeEach(() => { value = emptyToday(); error = ''; setLocale('en'); });
it('shows personal tasks without research or a preparation plan and links the exact saved record', () => {
  value.action_state = 'readable'; value.action_revision = 1; value.action_digest = 'a'.repeat(64);
  value.undated_personal = [{ id: 'own-task-card', reason: 'personal_document_action', target: { kind: 'document_task', id: 'task-a' }, target_result_id: null,
    date: { local_date: null, timezone: null, certainty: 'unknown', comparison_zone: 'UTC', fallback_display_only: true, official_closure: 'not_assessed' },
    dependency_reasons: ['dependency_missing'], workload_origin: 'personal_unallocated', planned_minutes: null, source_state: 'applicant_entered', actionable: true }];
  render(<AdmissionsTodayPanel />); const card = screen.getByTestId('today-action');
  expect(within(card).getByRole('heading')).toHaveTextContent('Synthetic document task');
  expect(within(card).getByRole('link', { name: 'Open this record' })).toHaveAttribute('href', '#/documents?case=A&kind=document_task&id=task-a');
  expect(within(card).getByText('An earlier required task is unavailable.')).toBeInTheDocument();
  expect(screen.queryByText('Optional study actions')).toBeNull(); expect(card).not.toHaveTextContent('planned study minutes');
});
it('distinguishes unavailable data from an empty personal list and last-confirmed read', () => {
  value.action_state = 'unavailable'; value.action_revision = null; error = 'Synthetic API failure'; render(<AdmissionsTodayPanel />);
  expect(screen.getByText(/Showing the last confirmed view/)).toBeInTheDocument(); expect(screen.queryByText(/No active personal actions/)).toBeNull();
});
''')
# Add exact target controls to the existing own mocked form suites, with explicit hash cleanup.
for p,kind,screenName,buttonName in [('frontend/src/screens/PersonalDocumentsPanel.test.tsx','document_task','documents','Task name'),('frontend/src/screens/ApplicationsPanel.test.tsx','application','approved','Your notes')]:
 t=(pre/p).read_text();t=t.replace('beforeEach(() => {','beforeEach(() => {\n  window.history.replaceState(null, \'\', \'#\');',1).replace('afterEach(() => {','afterEach(() => {\n  window.history.replaceState(null, \'\', \'#\');',1)
 if kind=='document_task':
  t+='''
it('opens only the exact document target and never falls back for a deleted ID', () => {
  actions.current = acceptedActions().current; window.history.replaceState(null, '', '#/documents?case=A&kind=document_task&id=gone');
  const view = render(<PersonalDocumentsPanel />); expect(screen.getByText(/This exact record is unavailable/)).toBeInTheDocument();
  expect(screen.queryByLabelText('Task name')).toBeNull();
  window.history.replaceState(null, '', '#/documents?case=A&kind=document_task&id=task-a'); view.rerender(<PersonalDocumentsPanel />);
  expect(screen.getByLabelText('Task name')).toHaveValue('Synthetic document task');
});
'''
 else:
  t+='''
it('opens only the exact application and rejects a different target case', () => {
  actions.current = manualFixture().current; window.history.replaceState(null, '', '#/approved?case=B&kind=application&id=manual-application');
  const view = render(<ApplicationsPanel />); expect(screen.getByText(/This exact record is unavailable/)).toBeInTheDocument(); expect(screen.queryByLabelText('Your notes')).toBeNull();
  window.history.replaceState(null, '', '#/approved?case=A&kind=application&id=manual-application'); view.rerender(<ApplicationsPanel />);
  expect(screen.getByLabelText('Your notes')).toBeInTheDocument();
});
'''
 put(p,t)
p='frontend/src/screens/SourcesScreen.test.tsx';t=(pre/p).read_text().replace('useStore: () => ({ results: [result], run })',"useStore: () => ({ results: [result], run, savedProfile: { id: 'A' } })",1);t+='''
it('does not substitute another programme when the exact evidence target is missing or from another case', () => {
  window.history.replaceState(null, '', '#/sources?case=A&kind=result&id=missing'); const view = render(<SourcesScreen />);
  expect(screen.getByText(/This exact record is unavailable/)).toBeInTheDocument(); expect(screen.queryByText('Example University')).toBeNull();
  window.history.replaceState(null, '', '#/sources?case=B&kind=result&id=result-1'); view.rerender(<SourcesScreen />);
  expect(screen.getByText(/This exact record is unavailable/)).toBeInTheDocument(); window.history.replaceState(null, '', '#');
});
''';put(p,t)
print('External exact target/native read/UI controls ready. No source apply or test run.')
