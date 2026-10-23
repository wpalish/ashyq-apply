import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApplicationsPanel } from './ApplicationsPanel';
import { acceptedActions, emptyActions } from '@/test/admissionsFixtures';
import { manualFixture } from '@/test/manualAdmissionsFixtures';
import { setLocale } from '@/lib/i18n';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import type { ProgramResult } from '@/types';
let actions: AdmissionsActionsController;
let rows: ProgramResult[]; let run: { profile_id: string } | null;
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => actions }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: rows, run }) }));
beforeEach(() => {
  window.history.replaceState(null, '', '#');
  vi.stubGlobal('crypto', webcrypto); setLocale('en'); rows = []; run = null;
  actions = { key: 'A:1', caseKey: 'A:1', activeCase: 'A', current: emptyActions(), historyPage: null,
    entries: [], indexRaw: null, journalError: null, loading: false, sending: false, error: null, acceptedButUnrefreshed: false,
    refresh: vi.fn().mockResolvedValue(true), submit: vi.fn().mockResolvedValue({ accepted: true, currentRefreshed: true, receipt: null }),
    retry: vi.fn(), loadHistory: vi.fn().mockResolvedValue(true), clearAcknowledged: vi.fn(), reconcile: vi.fn() };
});
afterEach(() => {
  window.history.replaceState(null, '', '#'); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function openManual() {
  fireEvent.click(screen.getByRole('button', { name: 'Add an application' }));
  fireEvent.change(screen.getByLabelText('Application name'), { target: { value: 'My synthetic application' } });
  fireEvent.change(screen.getByLabelText('University, as entered by you'), { target: { value: 'Synthetic entered university' } });
}
it('saves a confirmed manual application with unknown programme and no invented evidence IDs', async () => {
  render(<ApplicationsPanel />); openManual();
  const save = screen.getByRole('button', { name: 'Save on server' }); expect(save).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /I reviewed these personal details/ }));
  fireEvent.click(save);
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ schema_version: 'admissions-actions-v2', kind: 'create_application', expected_revision: 0,
    target: { origin: 'applicant_entered', result_id: null, award_id: null, purpose: 'admission', university: 'Synthetic entered university',
      programme: { state: 'unknown' }, award: { state: 'unknown' }, intake: { state: 'unknown' }, route: { state: 'unknown' },
      confirmed_entered_context: true, official_verification: 'not_performed' } }));
  expect(screen.getByText(/Saving confirmed by the server/)).toBeInTheDocument();
});
it('keeps lost-response drafts and original revision for conflict review', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  const view = render(<ApplicationsPanel />); openManual();
  actions = { ...actions, current: { ...emptyActions(), revision: 3 } }; view.rerender(<ApplicationsPanel />);
  expect(screen.getByText(/Saved data changed while this editor/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ expected_revision: 0 })));
  expect(screen.getByText(/Saving has not been confirmed/)).toBeInTheDocument();
  expect(screen.getByLabelText('Application name')).toHaveValue('My synthetic application');
});
it('lists saved manual applications without a research result and records submission as an own declaration', async () => {
  actions.current = manualFixture().current; render(<ApplicationsPanel />);
  const app = screen.getByTestId('personal-application'); expect(within(app).getByText('Synthetic own university')).toBeInTheDocument();
  expect(within(app).getByText(/official requirements are not confirmed/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Record my submission statement' }));
  expect(screen.getByLabelText('Your event date, if known')).toHaveValue(''); expect(screen.getByLabelText('Time zone')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Your event date, if known'), { target: { value: '2026-10-10' } });
  fireEvent.change(screen.getByLabelText('Submission channel, as entered by you'), { target: { value: 'Synthetic portal' } });
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'declare_submission', application_id: 'manual-application', expected_revision: 1,
    submission: { entered_at: { local_date: '2026-10-10', local_time: null, timezone: null, origin: 'applicant_entered' },
      channel: 'Synthetic portal', reference: '', document_task_ids: [], confirmed_applicant_declaration: true } })));
});
it('fences late feedback and hides an old editor when the case generation changes', async () => {
  let finish!: (value: { accepted: boolean; currentRefreshed: boolean; receipt: null }) => void;
  vi.mocked(actions.submit).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const view = render(<ApplicationsPanel />); openManual(); fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  actions = { ...actions, caseKey: 'A:2' }; view.rerender(<ApplicationsPanel />);
  finish({ accepted: true, currentRefreshed: true, receipt: null });
  await waitFor(() => expect(screen.queryByLabelText('Application name')).not.toBeInTheDocument());
  expect(screen.queryByText(/Saving confirmed by the server/)).not.toBeInTheDocument();
});
it('offers exact own selected results and excludes a foreign run', () => {
  rows = [{ id: 'r-approved', university: 'Synthetic selected', program: 'BSc', user_decision: 'approved' },
    { id: 'r-rejected', university: 'Synthetic rejected', program: 'BSc', user_decision: 'rejected' }] as ProgramResult[];
  run = { profile_id: 'B' }; const view = render(<ApplicationsPanel />); openManual();
  expect(screen.getByLabelText('Programme reference').querySelectorAll('option')).toHaveLength(1);
  run = { profile_id: 'A' }; view.rerender(<ApplicationsPanel />);
  expect(screen.getByLabelText('Programme reference').querySelectorAll('option')).toHaveLength(2);
});
it('corrects the exact historical declaration without overwriting its entered time', async () => {
  const fixture = manualFixture(); actions.current = { ...fixture.current, revision: 2 };
  const event = { ...fixture.receipt, event_id: 'exact-declaration', kind: 'declare_submission' as const, revision: 2,
    applied_delta: { ...fixture.receipt.applied_delta, declaration: null } };
  actions.historyPage = { profile_id: 'A', events: [event], next_after_revision: null, source_evaluation: 'not_evaluated' };
  render(<ApplicationsPanel />); fireEvent.click(screen.getByRole('button', { name: 'History' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Correct this declaration' })).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Correct this declaration' }));
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'correct_declaration', application_id: 'manual-application',
    expected_revision: 2, prior_declaration: { event_id: 'exact-declaration', revision: 2, kind: 'declare_submission' }, confirmed_correction: true,
    replacement: { kind: 'planning', status: 'preparing' } })));
});

it('starts personal application preparation without a course or submission declaration', async () => {
  actions.current = manualFixture().current; render(<ApplicationsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Start preparing this application' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'set_planning_status',
    application_id: 'manual-application', status: 'preparing', expected_revision: 1 })));
});

it('freezes an attempted draft and sends no new UUID after an unconfirmed response', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  render(<ApplicationsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Add an application' }));
  fireEvent.change(screen.getByLabelText('Application name'), { target: { value: 'Synthetic retained draft' } });
  fireEvent.change(screen.getByLabelText('University, as entered by you'), { target: { value: 'Synthetic university' } }); fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(screen.getByRole('button', { name: 'Save on server' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  expect(actions.submit).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Application name')).toHaveValue('Synthetic retained draft');
  expect(screen.getByRole('button', { name: 'Close editor' })).toBeEnabled();
});

it('edits an entered scholarship context without dropping the saved award or inventing source IDs', async () => {
  const fixture = manualFixture(); fixture.app.target.purpose = 'scholarship'; fixture.app.target.award = { state: 'applicant_entered', value: 'My entered award' };
  actions.current = fixture.current; render(<ApplicationsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit application context' }));
  expect(screen.getByLabelText('Scholarship name, if known')).toHaveValue('My entered award');
  fireEvent.change(screen.getByLabelText('Application name'), { target: { value: 'Renamed own scholarship' } });
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ operation: 'application_context', target: { kind: 'application', id: 'manual-application' },
    label: 'Renamed own scholarship', application_target: expect.objectContaining({ result_id: null, award_id: null, purpose: 'scholarship', award: { state: 'applicant_entered', value: 'My entered award' } }), confirmed_personal_context: true })));
});
it('locks the submitted target context while allowing a personal label change', () => {
  const fixture = manualFixture(); fixture.app.status = 'submitted_declared'; actions.current = fixture.current;
  render(<ApplicationsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Edit application context' }));
  expect(screen.getByLabelText('Programme reference')).toBeDisabled(); expect(screen.getByLabelText('Intake, if known')).toBeDisabled();
  expect(screen.getByLabelText('Application name')).toBeEnabled(); expect(screen.getByText(/Correct the declaration before/)).toBeInTheDocument();
});
it('prevents removal of an application with linked documents and tells the user how to resolve it', () => {
  const fixture = manualFixture(); const task = acceptedActions().current.state?.document_tasks[0]; if (!task) throw new Error('Synthetic task');
  task.application_id = fixture.app.id; fixture.current.state?.document_tasks.push(task); actions.current = fixture.current;
  render(<ApplicationsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Remove personal record' }));
  fireEvent.click(screen.getByRole('checkbox')); expect(screen.getByRole('button', { name: 'Save on server' })).toBeDisabled();
  expect(screen.getByText(/First unlink or remove/)).toBeInTheDocument(); expect(actions.submit).not.toHaveBeenCalled();
});
it('removes only the exact reviewed personal application after confirmation', async () => {
  actions.current = manualFixture().current; render(<ApplicationsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Remove personal record' }));
  expect(screen.getByRole('button', { name: 'Save on server' })).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'remove_personal_action', expected_revision: 1,
    target: { kind: 'application', id: 'manual-application' }, confirmed_personal_removal: true })));
  expect(actions.loadHistory).toHaveBeenCalled();
});

it('opens only the exact application and rejects a different target case', () => {
  actions.current = manualFixture().current; window.history.replaceState(null, '', '#/approved?case=B&kind=application&id=manual-application');
  const view = render(<ApplicationsPanel />); expect(screen.getByText(/This exact record is unavailable/)).toBeInTheDocument(); expect(screen.queryByLabelText('Your notes')).toBeNull();
  window.history.replaceState(null, '', '#/approved?case=A&kind=application&id=manual-application'); view.rerender(<ApplicationsPanel />);
  expect(screen.getByLabelText('Your notes')).toBeInTheDocument();
});

it('opens the book application without inventing a submission portal or university decision and restores focus',()=>{
  setLocale('ru');actions.current=manualFixture().current;
  render(<ApplicationsPanel pageHeading/>);
  const open=within(screen.getByTestId('personal-application')).getByRole('button',{name:/Synthetic own university/});
  fireEvent.click(open);
  expect(screen.getByRole('heading',{level:1,name:'Synthetic own university'})).toHaveFocus();
  expect(screen.getByText('Официальное решение').nextElementSibling).toHaveTextContent('Неизвестно');
  expect(screen.getByText(/Рабочая ссылка на страницу программы сейчас не подтверждена/)).toBeVisible();
  expect(screen.queryByRole('link',{name:/Подать заявку/})).toBeNull();
  expect(actions.submit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'К списку заявок'}));
  expect(within(screen.getByTestId('personal-application')).getByRole('button',{name:/Synthetic own university/})).toHaveFocus();
});

it('prefills a selected programme once and preserves personal date and timezone in the confirmed create command',async()=>{
 setLocale('ru');run={profile_id:'A'};rows=[{id:'r1',user_decision:'approved',university:'Synthetic programme uni',program:'BSc Test',intake:'Fall2027'} as ProgramResult];
 window.history.replaceState(null,'','#/applications?case=A&programme=r1&action=new');
 const view=render(<ApplicationsPanel pageHeading/>);
 expect(screen.getByLabelText('Название заявки')).toHaveValue('Synthetic programme uni - BSc Test');
 expect(screen.getByLabelText('Связь с программой')).toHaveValue('r1');expect(actions.submit).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Название заявки'),{target:{value:'My planned application'}});
 fireEvent.change(screen.getByLabelText('Ваша плановая дата'),{target:{value:'2026-10-22'}});
 fireEvent.change(screen.getByLabelText('Часовой пояс'),{target:{value:'Asia/Almaty'}});
 view.rerender(<ApplicationsPanel pageHeading/>);expect(screen.getByLabelText('Название заявки')).toHaveValue('My planned application');
 fireEvent.click(screen.getByRole('checkbox',{name:/Я проверил/}));fireEvent.click(screen.getByRole('button',{name:'Сохранить на сервере'}));
 await waitFor(()=>expect(actions.submit).toHaveBeenCalledOnce());
 expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({kind:'create_application',label:'My planned application',target:expect.objectContaining({result_id:'r1'}),details:{notes:'',due:{origin:'applicant_entered',local_date:'2026-10-22',timezone:'Asia/Almaty',official_deadline:false}}}));
});
it('does not prefill or create an application for a programme link belonging to another case',()=>{
 setLocale('ru');run={profile_id:'B'};rows=[{id:'r1',user_decision:'approved'} as ProgramResult];actions={...actions,caseKey:'B:1',activeCase:'B',current:emptyActions('B')};
 window.history.replaceState(null,'','#/applications?case=A&programme=r1&action=new');render(<ApplicationsPanel pageHeading/>);
 expect(screen.queryByLabelText('Название заявки')).toBeNull();expect(screen.getByText(/недоступна в текущем профиле/)).toBeInTheDocument();expect(actions.submit).not.toHaveBeenCalled();
});
