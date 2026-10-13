import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { PersonalDocumentsPanel } from './PersonalDocumentsPanel';
import { acceptedActions, emptyActions } from '@/test/admissionsFixtures';
import { setLocale } from '@/lib/i18n';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
let actions: AdmissionsActionsController;
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => actions }));
const inactiveCase = () => ({ scope: null, profile_id: null, case_epoch: 0 });
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: [], run: null, savedProfile: null, currentAdmissionsCase: inactiveCase }) }));
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto); setLocale('en');
  actions = { key: 'A:1', caseKey: 'A:1', activeCase: 'A', current: emptyActions(), historyPage: null,
    entries: [], indexRaw: null, journalError: null, loading: false, sending: false, error: null, acceptedButUnrefreshed: false,
    refresh: vi.fn().mockResolvedValue(true), submit: vi.fn().mockResolvedValue({ accepted: true, currentRefreshed: true, receipt: null }),
    retry: vi.fn().mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null }), loadHistory: vi.fn().mockResolvedValue(true),
    clearAcknowledged: vi.fn().mockResolvedValue(true), reconcile: vi.fn().mockResolvedValue(true) };
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('creates an own manual task without a research result or preparation access', async () => {
  render(<PersonalDocumentsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Add a document task' }));
  fireEvent.change(screen.getByLabelText('Task name'), { target: { value: 'Prepare own transcript' } });
  fireEvent.change(screen.getByLabelText('Your planning date'), { target: { value: '2027-01-10' } });
  fireEvent.change(screen.getByLabelText('Your notes'), { target: { value: 'Synthetic own note' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'create_personal_task', expected_revision: 0,
    application_id: null, personal: { label: 'Prepare own transcript', responsible_actor: 'applicant', depends_on_task_ids: [],
      details: { notes: 'Synthetic own note', due: { origin: 'applicant_entered', local_date: '2027-01-10', timezone: null, official_deadline: false } } } }));
  expect(screen.getByText(/Saving confirmed by the server/)).toBeInTheDocument();
});
it('keeps the reviewed task ID and revision when editing date and notes', async () => {
  actions.current = acceptedActions().current;
  const view = render(<PersonalDocumentsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Edit date and notes' }));
  fireEvent.change(screen.getByLabelText('Your notes'), { target: { value: 'My newer draft' } });
  actions = { ...actions, current: { ...actions.current, revision: 2 } }; view.rerender(<PersonalDocumentsPanel />);
  expect(screen.getByText(/Saved data changed while this editor/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'set_personal_details', expected_revision: 1,
    target: { kind: 'document_task', id: 'task-a' }, details: { due: null, notes: 'My newer draft' } })));
});
it('requires explicit self-report confirmation and never assumes the event date or time zone', async () => {
  const fixture = acceptedActions(); if (!fixture.current.state) throw new Error('Synthetic task');
  const task = fixture.current.state.document_tasks[0]; if (!task) throw new Error('Synthetic task');
  task.personal.details.due = { local_date: '2027-01-10', timezone: 'Asia/Almaty', origin: 'applicant_entered', official_deadline: false };
  actions.current = fixture.current; render(<PersonalDocumentsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Update personal status' }));
  const save = screen.getByRole('button', { name: 'Save on server' }); expect(save).toBeDisabled();
  expect(screen.getByLabelText('Your event date, if known')).toHaveValue('');
  expect(screen.getByLabelText('Time zone')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Your reported status'), { target: { value: 'prepared_reported' } });
  fireEvent.click(screen.getByRole('checkbox')); expect(save).toBeEnabled(); fireEvent.click(save);
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'set_document_self_report', task_id: 'task-a',
    report: { state: 'prepared_reported', entered_at: null, confirmed_personal_report: true } })));
});
it('does not turn an unconfirmed response into a saved record and retains the draft', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  render(<PersonalDocumentsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Add a document task' }));
  fireEvent.change(screen.getByLabelText('Task name'), { target: { value: 'My draft task' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(screen.getByText(/Saving has not been confirmed/)).toBeInTheDocument());
  expect(screen.getByLabelText('Task name')).toHaveValue('My draft task');
});
it('drops the visible A draft on a new case generation and keeps last confirmed records when reads fail', () => {
  actions.current = acceptedActions().current; const view = render(<PersonalDocumentsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit date and notes' }));
  actions = { ...actions, key: 'B:2', caseKey: 'B:2', activeCase: 'B', current: emptyActions('B') };
  view.rerender(<PersonalDocumentsPanel />); expect(screen.queryByRole('button', { name: 'Save on server' })).toBeNull();
  actions = { ...actions, key: 'A:3', caseKey: 'A:3', activeCase: 'A', current: acceptedActions().current, error: 'Synthetic unavailable read' };
  view.rerender(<PersonalDocumentsPanel />);
  expect(within(screen.getByTestId('personal-document-task')).getByRole('heading')).toHaveTextContent('Synthetic document task');
  expect(screen.getAllByText('Synthetic unavailable read').length).toBeGreaterThan(0);
});

it('freezes an attempted draft and sends no new UUID after an unconfirmed response', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  render(<PersonalDocumentsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Add a document task' }));
  fireEvent.change(screen.getByLabelText('Task name'), { target: { value: 'Synthetic retained draft' } });
  
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(screen.getByRole('button', { name: 'Save on server' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  expect(actions.submit).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Task name')).toHaveValue('Synthetic retained draft');
  expect(screen.getByRole('button', { name: 'Close editor' })).toBeEnabled();
});
