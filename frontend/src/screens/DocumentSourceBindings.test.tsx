import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { DocumentSourceBindings } from './DocumentSourceBindings';
import { setLocale } from '@/lib/i18n';
import { emptyActions } from '@/test/admissionsFixtures';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import type { ProgramResult } from '@/types';
import type { SourceBindingPreviewOutV1 } from '@/types/admissionsActions';
const live = { scope: undefined, profile_id: 'A', case_epoch: 1 };
let rows: ProgramResult[];
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile: { id: 'A' }, run: { id: 'run-a', profile_id: 'A' }, results: rows, currentAdmissionsCase: () => live }) }));
let actions: AdmissionsActionsController;
function preview(index = 0): SourceBindingPreviewOutV1 {
  const d = 'a'.repeat(64); return { profile_id: 'A', result_id: 'result-a', source_preview_digest: d, observed_at: '2026-10-13T10:00:00Z',
    source_status: { result_id: 'result-a', target_state: 'eligible', source_state: 'current_reference', current_digest: d, reasons: [], observed_at: '2026-10-13T10:00:00Z' },
    selection: { result_id: 'result-a', purpose: 'admission', award_id: null, award_relation: 'unknown', checklist_digest: d, procedure_digest: d,
      occurrences: [{ result_id: 'result-a', location: 'applicant_actions', index, item_digest: d, item_semantics_digest: d, proof_reference_digest: d }],
      original_claim_ids: [], g1_document: null, g1_relation: 'document_predicate_not_projected' } };
}
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto); setLocale('en'); live.profile_id = 'A'; live.case_epoch = 1;
  rows = [{ id: 'result-a', run_id: 'run-a', university: 'Synthetic Uni', program: 'BSc', user_decision: 'approved',
    checklist: { admission_documents: [], scholarship_documents: [], applicant_actions: [{ name: 'Same name', purpose: 'admission' }, { name: 'Same name', purpose: 'admission' }],
      school_actions: [], recommender_actions: [], certification_actions: [] } }] as unknown as ProgramResult[];
  actions = { key: 'A:1', caseKey: 'A:1', activeCase: 'A', current: emptyActions(), historyPage: null, entries: [], indexRaw: null,
    journalError: null, loading: false, sending: false, error: null, acceptedButUnrefreshed: false,
    refresh: vi.fn().mockResolvedValue(true), submit: vi.fn().mockResolvedValue({ accepted: true, currentRefreshed: true, receipt: null }),
    retry: vi.fn(), loadHistory: vi.fn(), clearAcknowledged: vi.fn(), reconcile: vi.fn() };
  vi.spyOn(api, 'previewAdmissionsSource').mockImplementation(async (_profile, request) => preview(request.occurrences[0]?.index));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
it('retains distinct exact positions for equal names and journals the reviewed preview', async () => {
  render(<DocumentSourceBindings controller={actions} />);
  const selector = screen.getByLabelText('Choose a programme requirement');
  expect(selector.querySelectorAll('option')).toHaveLength(3);
  fireEvent.change(selector, { target: { value: JSON.stringify(['result-a', 'applicant_actions', 1]) } });
  fireEvent.click(screen.getByRole('button', { name: 'Review current requirement' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save reviewed requirement link' })).toBeInTheDocument());
  expect(api.previewAdmissionsSource).toHaveBeenCalledWith('A', { result_id: 'result-a', purpose: 'admission', award_id: null, occurrences: [{ location: 'applicant_actions', index: 1 }] });
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed requirement link' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'bind_source_task', expected_revision: 0, source: preview(1).selection })));
});
it('rejects a foreign or mismatched preview rather than turning it into a task', async () => {
  vi.mocked(api.previewAdmissionsSource).mockResolvedValue({ ...preview(), profile_id: 'foreign' });
  render(<DocumentSourceBindings controller={actions} />);
  fireEvent.change(screen.getByLabelText('Choose a programme requirement'), { target: { value: JSON.stringify(['result-a', 'applicant_actions', 0]) } });
  fireEvent.click(screen.getByRole('button', { name: 'Review current requirement' }));
  await waitFor(() => expect(screen.getByText(/could not be confirmed for linking/)).toBeInTheDocument());
  expect(screen.queryByRole('button', { name: 'Save reviewed requirement link' })).toBeNull(); expect(actions.submit).not.toHaveBeenCalled();
});
it('does not offer requirements from another loaded run or unselected programme', () => {
  rows = rows.map(row => ({ ...row, run_id: 'another', user_decision: 'undecided' }));
  render(<DocumentSourceBindings controller={actions} />);
  expect(screen.getByLabelText('Choose a programme requirement').querySelectorAll('option')).toHaveLength(1);
});

it('retains the reviewed preview and prevents a new task UUID after an unconfirmed save', async () => {
  vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  render(<DocumentSourceBindings controller={actions} />);
  fireEvent.change(screen.getByLabelText('Choose a programme requirement'), { target: { value: JSON.stringify(['result-a', 'applicant_actions', 0]) } });
  fireEvent.click(screen.getByRole('button', { name: 'Review current requirement' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save reviewed requirement link' })).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed requirement link' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledOnce());
  expect(screen.getByRole('button', { name: 'Save reviewed requirement link' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save reviewed requirement link' }));
  expect(actions.submit).toHaveBeenCalledOnce(); expect(screen.getByText(/Saving has not been confirmed/)).toBeInTheDocument();
});

it('limits requirement choices to the selected programme and binds only the explicitly selected application',async()=>{
 const current=emptyActions();current.state={schema_version:'admissions-actions-v1',profile_id:'A',revision:0,head_event_id:'head',document_tasks:[],applications:[{id:'app-a',profile_id:'A',label:'Synthetic app',details:{due:null,notes:''},status:'planning',target:{result_id:'result-a',purpose:'admission',award_id:null,intake:{state:'unknown'},route:{state:'unknown'},confirmed_entered_context:true},created_ref:{event_id:'create',revision:0,kind:'create_application'},latest_ref:{event_id:'create',revision:0,kind:'create_application'},status_ref:null}],active_preparation:null};actions.current=current;
 rows.push({...rows[0]!,id:'other-result'});
 render(<DocumentSourceBindings controller={actions} programmeId="result-a" applicationId="app-a"/>);
 expect(screen.getByLabelText('Choose a programme requirement').querySelectorAll('option')).toHaveLength(3);
 fireEvent.change(screen.getByLabelText('Choose a programme requirement'),{target:{value:JSON.stringify(['result-a','applicant_actions',0])}});
 fireEvent.click(screen.getByRole('button',{name:'Review current requirement'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Save reviewed requirement link'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed requirement link'}));await waitFor(()=>expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({kind:'bind_source_task',application_id:'app-a',source:preview().selection})));
});
it('refuses an application context that is absent from the current native state',()=>{
 render(<DocumentSourceBindings controller={actions} programmeId="result-a" applicationId="foreign-app"/>);
 fireEvent.change(screen.getByLabelText('Choose a programme requirement'),{target:{value:JSON.stringify(['result-a','applicant_actions',0])}});
 expect(screen.getByRole('button',{name:'Review current requirement'})).toBeDisabled();expect(api.previewAdmissionsSource).not.toHaveBeenCalled();expect(actions.submit).not.toHaveBeenCalled();
});
