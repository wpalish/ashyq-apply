from pathlib import Path
r=Path(__file__).resolve().parent;pre=r/'applications4d-preimages';out=r/'applications4d-proposal'
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='frontend/src/types/admissionsActions.ts';t=(out/p).read_text()
t=t.replace("  return (context === null || object(context)) && (applicationRecord(record) || manualApplicationRecord(record));", """  return (applicationRecord(record) || manualApplicationRecord(record)) && object(record.created_ref) && object(record.latest_ref)
    && typeof record.created_ref.revision === 'number' && typeof record.latest_ref.revision === 'number'
    && record.created_ref.kind === 'create_application' && record.latest_ref.revision >= record.created_ref.revision
    && (context === null || (object(context) && typeof context.revision === 'number' && context.revision > record.created_ref.revision && context.revision <= record.latest_ref.revision));""",1)
t=t.replace("function sameEntered(a: EnteredOrUnknownText, b: EnteredOrUnknownText): boolean {\n  return a.state === b.state", "function sameEntered(a: unknown, b: EnteredOrUnknownText): boolean {\n  return object(a) && enteredText(a) && a.state === b.state",1)
t=t.replace('actual.intake as EnteredOrUnknownText','actual.intake').replace('actual.route as EnteredOrUnknownText','actual.route')
t=t.replace("  const apps = state.applications; const tasks = state.document_tasks; const revision = v.revision;", """  if (Object.hasOwn(state, 'head_ref') && (!object(state.head_ref) || state.head_ref.kind !== v.head_receipt.kind)) return false;
  if (v.head_receipt.kind === 'remove_personal_action' && !Object.hasOwn(state, 'head_ref')) return false;
  const apps = state.applications; const tasks = state.document_tasks; const revision = v.revision;
  if ((v.head_receipt.applied_delta.removed_application && apps.some(item => object(item) && item.id === v.head_receipt.applied_delta.removed_application?.id))
    || (v.head_receipt.applied_delta.removed_document_task && tasks.some(item => object(item) && item.id === v.head_receipt.applied_delta.removed_document_task?.id))) return false;""",1)
t=t.replace("(!object(item.binding) || item.binding.result_id !== app.target.result_id)) {", "(!object(item.binding) || item.binding.result_id !== app.target.result_id || item.binding.award_id !== app.target.award_id\n        || (item.binding.purpose !== app.target.purpose && item.binding.purpose !== 'both'))) {",1)
put(p,t)
put('frontend/src/test/admissionsEditsFixtures.ts','''/** Synthetic closed edit/removal wire data signed independently by Node, not native API evidence. */
import { acceptedActions, emptyActions, fixtureHash } from './admissionsFixtures';
import { manualFixture } from './manualAdmissionsFixtures';
import type { ActionRequest, ActionWriteReceipt, ActionsCurrentOut, CaseActionsState, ContextApplicationRecordV2, RemovePersonalActionV2, SetDocumentMetadataV2, SetApplicationContextV2 } from '@/types/admissionsActions';
const editUuid = '33333333-4444-4555-8666-777777777777';
export function editDocumentFixture() {
  const previous = acceptedActions(); const old = previous.current.state?.document_tasks[0]; if (!old) throw new Error('Synthetic task missing');
  const body: SetDocumentMetadataV2 = { schema_version: 'admissions-actions-v2', kind: 'set_personal_details', operation: 'document_metadata',
    client_write_uuid: editUuid, expected_revision: 1, target: { kind: 'document_task', id: old.id }, application_id: null,
    personal: { ...structuredClone(old.personal), label: 'Edited synthetic document', responsible_actor: 'school' }, confirmed_personal_metadata: true };
  const head = { event_id: 'edit-event', revision: 2, kind: body.kind };
  const task = { ...structuredClone(old), personal: structuredClone(body.personal), latest_ref: head };
  const state: CaseActionsState = { schema_version: 'admissions-actions-v2', profile_id: 'A', revision: 2,
    head_event_id: head.event_id, head_ref: head, applications: [], document_tasks: [task], active_preparation: null };
  return editedWire(body, state, previous.receipt, { applications: [], document_tasks: [task], active_preparation: null,
    corrected_declaration: null, previous_binding_digest: null, declaration: null, removed_application: null, removed_document_task: null });
}
export function editApplicationFixture() {
  const previous = manualFixture(); const body: SetApplicationContextV2 = { schema_version: 'admissions-actions-v2', kind: 'set_personal_details',
    operation: 'application_context', client_write_uuid: editUuid, expected_revision: 1, target: { kind: 'application', id: previous.app.id },
    application_target: { ...structuredClone(previous.app.target), programme: { state: 'applicant_entered', value: 'Entered BSc' } },
    label: 'Edited synthetic application', details: { due: null, notes: '' }, confirmed_personal_context: true };
  const head = { event_id: 'edit-event', revision: 2, kind: body.kind };
  const app: ContextApplicationRecordV2 = { ...structuredClone(previous.app), target: structuredClone(body.application_target), label: body.label, latest_ref: head, context_ref: head };
  const state: CaseActionsState = { ...previous.state, revision: 2, head_event_id: head.event_id, head_ref: head, applications: [app] };
  return editedWire(body, state, previous.receipt, { applications: [app], document_tasks: [], active_preparation: null,
    corrected_declaration: null, previous_binding_digest: null, declaration: null, removed_application: null, removed_document_task: null });
}
export function removalFixture(kind: 'application' | 'document_task' = 'document_task') {
  const previous = kind === 'application' ? manualFixture() : acceptedActions();
  const removedApp = kind === 'application' ? previous.current.state?.applications[0] ?? null : null;
  const removedTask = kind === 'document_task' ? previous.current.state?.document_tasks[0] ?? null : null;
  const id = removedApp?.id ?? removedTask?.id; if (!id) throw new Error('Synthetic removal target missing');
  const body: RemovePersonalActionV2 = { schema_version: 'admissions-actions-v2', kind: 'remove_personal_action', client_write_uuid: editUuid,
    expected_revision: 1, target: { kind, id }, confirmed_personal_removal: true };
  const head = { event_id: 'remove-event', revision: 2, kind: body.kind };
  const state: CaseActionsState = { schema_version: 'admissions-actions-v2', profile_id: 'A', revision: 2,
    head_event_id: head.event_id, head_ref: head, applications: [], document_tasks: [], active_preparation: null };
  return editedWire(body, state, previous.receipt, { applications: [], document_tasks: [], active_preparation: null,
    corrected_declaration: null, previous_binding_digest: null, declaration: null, removed_application: structuredClone(removedApp), removed_document_task: structuredClone(removedTask) });
}
function editedWire<T extends ActionRequest>(body: T, state: CaseActionsState, previous: ActionWriteReceipt, delta: ActionWriteReceipt['applied_delta']) {
  const removedApp = delta.removed_application; const removedTask = delta.removed_document_task;
  const wire: Omit<ActionWriteReceipt, 'receipt_digest'> = { ...previous, schema_version: 'admissions-actions-v2', event_id: state.head_event_id,
    kind: body.kind, revision: state.revision, expected_revision: body.expected_revision, client_write_uuid: body.client_write_uuid, request: body,
    canonical_request_digest: fixtureHash({ schema_version: 'g3-action-request-digest-v1', profile_id: 'A', request: body }),
    predecessor_event_id: previous.event_id, before_state_digest: previous.after_state_digest,
    after_state_digest: fixtureHash({ schema_version: 'g3-state-digest-v1', state }), applied_delta: delta,
    affected_refs: { application_ids: [...delta.applications.map(app => app.id), ...(removedApp ? [removedApp.id] : [])],
      document_task_ids: [...delta.document_tasks.map(task => task.id), ...(removedTask ? [removedTask.id] : [])], active_selector_changed: false } };
  // The hash excludes the predecessor receipt_digest inherited above.
  const { receipt_digest: _oldDigest, ...unsigned } = wire as Omit<ActionWriteReceipt, 'receipt_digest'> & { receipt_digest?: string };
  const receipt: ActionWriteReceipt = { ...unsigned, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: unsigned }) };
  const current: ActionsCurrentOut = { ...emptyActions(), revision: state.revision, state, head_receipt: receipt };
  return { body, state, receipt, current };
}
''')
# Fixture signing use clean previous explicitly instead of unnecessary cast/discard.
p='frontend/src/test/admissionsEditsFixtures.ts';t=(out/p).read_text();t=t.replace("  const wire: Omit<ActionWriteReceipt, 'receipt_digest'> = { ...previous,", "  const { receipt_digest: _previousDigest, ...previousWire } = previous;\n  const wire: Omit<ActionWriteReceipt, 'receipt_digest'> = { ...previousWire,",1)
t=t.replace("  // The hash excludes the predecessor receipt_digest inherited above.\n  const { receipt_digest: _oldDigest, ...unsigned } = wire as Omit<ActionWriteReceipt, 'receipt_digest'> & { receipt_digest?: string };\n  const receipt: ActionWriteReceipt = { ...unsigned, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: unsigned }) };", "  const receipt: ActionWriteReceipt = { ...wire, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: wire }) };",1);put(p,t)
put('frontend/src/types/admissionsActions.edits.test.ts','''import { expect, it } from 'vitest';
import { editApplicationFixture, editDocumentFixture, removalFixture } from '@/test/admissionsEditsFixtures';
import { isActionRequest, isActionRequestV1, isActionsCurrentOut, isActionWriteReceiptShape, isActionWriteReceiptShapeV1 } from './admissionsActions';
it.each([editDocumentFixture, editApplicationFixture, () => removalFixture('document_task'), () => removalFixture('application')])('reads closed companion edit/removal while original V1 stays closed', make => {
  const { body, receipt, current } = make();
  expect(isActionRequest(body)).toBe(true); expect(isActionRequestV1(body)).toBe(false);
  expect(isActionWriteReceiptShape(receipt)).toBe(true); expect(isActionWriteReceiptShapeV1(receipt)).toBe(false);
  expect(isActionsCurrentOut(current)).toBe(true);
  expect(isActionRequest({ ...body, extra: true })).toBe(false);
});
it.each(['application', 'document_task'] as const)('rejects an incorrect removed %s snapshot and foreign owner', kind => {
  const { receipt } = removalFixture(kind); const copy = structuredClone(receipt);
  const removed = kind === 'application' ? copy.applied_delta.removed_application : copy.applied_delta.removed_document_task;
  if (!removed) throw new Error('Synthetic removal snapshot missing');
  removed.profile_id = 'B'; expect(isActionWriteReceiptShape(copy)).toBe(false);
  removed.profile_id = 'A'; removed.latest_ref.revision = 3; expect(isActionWriteReceiptShape(copy)).toBe(false);
  expect(isActionWriteReceiptShape({ ...receipt, affected_refs: { ...receipt.affected_refs, application_ids: [], document_task_ids: [] } })).toBe(false);
});
it('requires the removal head and rejects a removed object remaining active', () => {
  const { current } = removalFixture(); const copy = structuredClone(current); if (!copy.state) throw new Error('Synthetic state');
  delete copy.state.head_ref; expect(isActionsCurrentOut(copy)).toBe(false);
  const retained = structuredClone(current); const task = retained.head_receipt?.applied_delta.removed_document_task;
  if (!retained.state || !task) throw new Error('Synthetic snapshot'); retained.state.document_tasks.push(task);
  expect(isActionsCurrentOut(retained)).toBe(false);
});
it('rejects a document edit delta that disagrees with the exact reviewed metadata', () => {
  const { receipt } = editDocumentFixture(); const copy = structuredClone(receipt);
  const task = copy.applied_delta.document_tasks[0]; if (!task) throw new Error('Synthetic task'); task.personal.responsible_actor = 'recommender';
  expect(isActionWriteReceiptShape(copy)).toBe(false);
});
it('rejects future and wrong-kind application context references and accepts context review reasons', () => {
  const { current } = editApplicationFixture(); const app = current.state?.applications[0];
  if (!app || !('context_ref' in app) || !app.context_ref) throw new Error('Synthetic context');
  app.context_ref.revision = 3; expect(isActionsCurrentOut(current)).toBe(false);
  app.context_ref.revision = 2; app.context_ref.kind = 'declare_submission'; expect(isActionsCurrentOut(current)).toBe(false);
  const document = editDocumentFixture().current;
  document.document_report_reviews = [{ task_id: 'task-a', reasons: ['application_context_changed'] }];
  expect(isActionsCurrentOut(document)).toBe(true);
});
''')
put('frontend/src/lib/admissionsActionsRecovery.edits.test.ts','''import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { editApplicationFixture, editDocumentFixture, removalFixture } from '@/test/admissionsEditsFixtures';
import { acknowledgeAdmissionsAction, admissionsActionRetryBody, journalAdmissionsAction, openAdmissionsActionsRecovery, readAdmissionsActionsRecovery,
  validateAdmissionsActionReceipt, validateAdmissionsActionsCurrent, type G3RecoveryResult } from './admissionsActionsRecovery';
function value<T>(result: G3RecoveryResult<T>) { if (!result.ok) throw new Error(result.reason); return result.value; }
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); localStorage.clear(); sessionStorage.clear(); localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo'); });
afterEach(() => { vi.unstubAllGlobals(); });
it.each([editDocumentFixture, editApplicationFixture, () => removalFixture('document_task'), () => removalFixture('application')])('recovers the exact edit/removal body and verifies independent receipt/current hashes', async make => {
  const live = { scope: undefined, profile_id: 'A', case_epoch: 1 };
  const binding = value(openAdmissionsActionsRecovery(undefined, 'A', 1, () => live)); const { body, receipt, current } = make();
  const saved = value(await journalAdmissionsAction(binding, body, 1));
  expect(value(await admissionsActionRetryBody(binding, body.client_write_uuid, saved.raw))).toEqual(body);
  expect(await validateAdmissionsActionReceipt('A', body, receipt)).toBe(true);
  expect(await validateAdmissionsActionsCurrent(current, 'A')).toEqual(current);
  expect(await validateAdmissionsActionsCurrent(current, 'B')).toBeNull();
  expect((await acknowledgeAdmissionsAction(binding, body, receipt)).ok).toBe(true);
  expect(value(await readAdmissionsActionsRecovery(binding)).entries[0]?.descriptor.status).toBe('acknowledged');
});
it('rejects tampered removed snapshots, current head and different original intent', async () => {
  const { body, receipt, current } = removalFixture(); const copy = structuredClone(receipt);
  if (!copy.applied_delta.removed_document_task) throw new Error('Synthetic removed task');
  copy.applied_delta.removed_document_task.personal.label = 'Different removed snapshot';
  expect(await validateAdmissionsActionReceipt('A', body, copy)).toBe(false);
  expect(await validateAdmissionsActionReceipt('A', { ...body, target: { kind: 'document_task', id: 'other-task' } }, receipt)).toBe(false);
  const altered = structuredClone(current); if (!altered.state?.head_ref) throw new Error('Synthetic head'); altered.state.head_ref.kind = 'create_personal_task';
  expect(await validateAdmissionsActionsCurrent(altered, 'A')).toBeNull();
});
''')
p='frontend/src/screens/PersonalDocumentsPanel.test.tsx';t=(pre/p).read_text().replace("name: 'Edit date and notes'","name: 'Edit document details'")
t=t.replace("  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));\n  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'set_personal_details', expected_revision: 1,\n    target: { kind: 'document_task', id: 'task-a' }, details: { due: null, notes: 'My newer draft' } })));", """  fireEvent.click(screen.getByRole('checkbox', { name: /I confirm these personal details/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ schema_version: 'admissions-actions-v2', kind: 'set_personal_details', operation: 'document_metadata', expected_revision: 1,
    target: { kind: 'document_task', id: 'task-a' }, personal: { label: 'Synthetic document task', responsible_actor: 'applicant', depends_on_task_ids: [], details: { due: null, notes: 'My newer draft' } }, confirmed_personal_metadata: true })));""",1)
t+='''
it('edits responsible actor and label without turning a previous report into a new completion', async () => {
  actions.current = acceptedActions().current; render(<PersonalDocumentsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit document details' }));
  fireEvent.change(screen.getByLabelText('Task name'), { target: { value: 'School transcript request' } });
  fireEvent.change(screen.getByLabelText('Responsible'), { target: { value: 'school' } });
  expect(screen.getByRole('button', { name: 'Save on server' })).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /I confirm these personal details/ })); fireEvent.click(screen.getByRole('button', { name: 'Save on server' }));
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ operation: 'document_metadata',
    personal: expect.objectContaining({ label: 'School transcript request', responsible_actor: 'school' }) })));
  expect(vi.mocked(actions.submit).mock.calls[0]?.[0]).not.toHaveProperty('report');
});
it('requires explicit own removal and freezes an unconfirmed removal for original-intent recovery', async () => {
  actions.current = acceptedActions().current; vi.mocked(actions.submit).mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null });
  render(<PersonalDocumentsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Remove personal record' }));
  const save = screen.getByRole('button', { name: 'Save on server' }); expect(save).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /I confirm removal/ })); fireEvent.click(save);
  await waitFor(() => expect(actions.submit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'remove_personal_action', expected_revision: 1,
    target: { kind: 'document_task', id: 'task-a' }, confirmed_personal_removal: true })));
  expect(save).toBeDisabled(); fireEvent.click(save); expect(actions.submit).toHaveBeenCalledOnce();
});
'''
# Actual locale is read below and corrected explicitly before applying proposal.
t=t.replace("getByLabelText('Responsible')", "getByLabelText('Who is responsible')")
put(p,t)
p='frontend/src/screens/ApplicationsPanel.test.tsx';t=(pre/p).read_text();t+='''
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
''';t=t.replace("import { emptyActions }", "import { acceptedActions, emptyActions }",1);put(p,t)
print('External meaningful codec, exact recovery and UI controls prepared; no source/runtime mutation.')
