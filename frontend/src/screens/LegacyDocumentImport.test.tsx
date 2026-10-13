import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { LegacyDocumentImport } from './LegacyDocumentImport';
import { setLocale } from '@/lib/i18n';
import { acceptedActions } from '@/test/admissionsFixtures';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import type { ProgramResult } from '@/types';
const live = { scope: undefined, profile_id: 'A', case_epoch: 1 };
let rows: ProgramResult[];
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile: { id: 'A' }, run: { id: 'run-a', profile_id: 'A' }, results: rows, currentAdmissionsCase: () => live }) }));
let actions: AdmissionsActionsController;
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto); setLocale('en'); localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo');
  live.profile_id = 'A'; live.case_epoch = 1;
  rows = [{ id: 'result-a', run_id: 'run-a', university: 'Synthetic Uni', program: 'BSc', checklist: {
    applicant_actions: [{ name: 'Own mark' }], school_actions: [], recommender_actions: [], certification_actions: [] } }] as unknown as ProgramResult[];
  actions = { key: 'A:1', caseKey: 'A:1', activeCase: 'A', current: acceptedActions().current, historyPage: null, entries: [], indexRaw: null,
    journalError: null, loading: false, sending: false, error: null, acceptedButUnrefreshed: false,
    refresh: vi.fn().mockResolvedValue(true), submit: vi.fn().mockResolvedValue({ accepted: true, currentRefreshed: true, receipt: null }),
    retry: vi.fn(), loadHistory: vi.fn(), clearAcknowledged: vi.fn(), reconcile: vi.fn() };
  vi.spyOn(api, 'previewAdmissionsImport').mockImplementation(async (profile, request) => ({ profile_id: profile, revision: request.expected_revision,
    legacy_snapshot_digest: request.legacy_snapshot_digest, mappings: request.mappings, observed_at: '2026-10-13T10:00:00Z' }));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
it('offers only exact unambiguous marks from the own loaded case and requires explicit mapping', async () => {
  localStorage.setItem('ashyq.docsDone', JSON.stringify({ 'result-a::Own mark': true, 'foreign-result::Foreign mark': true }));
  render(<LegacyDocumentImport controller={actions} />); fireEvent.click(screen.getByRole('button', { name: 'Read marks for this case' }));
  await waitFor(() => expect(screen.getByLabelText('Earlier browser mark').querySelectorAll('option')).toHaveLength(2));
  expect(screen.queryByText(/Foreign mark/)).toBeNull();
  const option = screen.getByLabelText('Earlier browser mark').querySelectorAll('option')[1]; if (!option) throw new Error('Synthetic mark');
  fireEvent.change(screen.getByLabelText('Earlier browser mark'), { target: { value: option.value } });
  fireEvent.change(screen.getByLabelText('Your unreported personal task'), { target: { value: 'task-a' } });
  expect(screen.getByRole('button', { name: 'Review selected transfer' })).toBeDisabled(); fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Review selected transfer' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save reviewed personal mark' })).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed personal mark' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'import_legacy_marks', expected_revision: 1,
    entered_at: null, mappings: [expect.objectContaining({ task_id: 'task-a', source_version: 'unknown', original_reported_at: null, confirmed_prepared_report: true })] })));
});
it('does not import duplicate-name marks or overwrite an existing personal report', async () => {
  const checklist = rows[0]?.checklist; if (checklist) checklist.applicant_actions.push(checklist.applicant_actions[0]!);
  localStorage.setItem('ashyq.docsDone', JSON.stringify({ 'result-a::Own mark': true }));
  const task = actions.current?.state?.document_tasks[0]; if (task) task.report.origin = 'explicit_browser_mark_import';
  render(<LegacyDocumentImport controller={actions} />); fireEvent.click(screen.getByRole('button', { name: 'Read marks for this case' }));
  await waitFor(() => expect(screen.getByText(/No unambiguous positive marks/)).toBeInTheDocument());
  expect(screen.getByLabelText('Your unreported personal task').querySelectorAll('option')).toHaveLength(1); expect(actions.submit).not.toHaveBeenCalled();
});

it('blocks a second import UUID after a lost save confirmation', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  localStorage.setItem('ashyq.docsDone', JSON.stringify({ 'result-a::Own mark': true }));
  render(<LegacyDocumentImport controller={actions} />); fireEvent.click(screen.getByRole('button', { name: 'Read marks for this case' }));
  await waitFor(() => expect(screen.getByLabelText('Earlier browser mark').querySelectorAll('option')).toHaveLength(2));
  const option = screen.getByLabelText('Earlier browser mark').querySelectorAll('option')[1]; if (!option) throw new Error('Synthetic mark');
  fireEvent.change(screen.getByLabelText('Earlier browser mark'), { target: { value: option.value } });
  fireEvent.change(screen.getByLabelText('Your unreported personal task'), { target: { value: 'task-a' } });
  fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Review selected transfer' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save reviewed personal mark' })).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed personal mark' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(screen.getByRole('button', { name: 'Save reviewed personal mark' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed personal mark' })); expect(actions.submit).toHaveBeenCalledOnce();
});
