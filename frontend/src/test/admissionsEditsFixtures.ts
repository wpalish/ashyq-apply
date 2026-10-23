/** Synthetic closed edit/removal wire data signed independently by Node, not native API evidence. */
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
  const previousWire = { profile_id: previous.profile_id, accepted_at: previous.accepted_at, actor: previous.actor };
  const wire: Omit<ActionWriteReceipt, 'receipt_digest'> = { ...previousWire, schema_version: 'admissions-actions-v2', event_id: state.head_event_id,
    kind: body.kind, revision: state.revision, expected_revision: body.expected_revision, client_write_uuid: body.client_write_uuid, request: body,
    canonical_request_digest: fixtureHash({ schema_version: 'g3-action-request-digest-v1', profile_id: 'A', request: body }),
    predecessor_event_id: previous.event_id, before_state_digest: previous.after_state_digest,
    after_state_digest: fixtureHash({ schema_version: 'g3-state-digest-v1', state }), applied_delta: delta,
    affected_refs: { application_ids: [...delta.applications.map(app => app.id), ...(removedApp ? [removedApp.id] : [])],
      document_task_ids: [...delta.document_tasks.map(task => task.id), ...(removedTask ? [removedTask.id] : [])], active_selector_changed: false } };
  const receipt: ActionWriteReceipt = { ...wire, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: wire }) };
  const current: ActionsCurrentOut = { ...emptyActions(), revision: state.revision, state, head_receipt: receipt };
  return { body, state, receipt, current };
}
