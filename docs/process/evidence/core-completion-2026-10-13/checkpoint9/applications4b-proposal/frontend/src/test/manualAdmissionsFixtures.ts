/** Synthetic V2 records; independently Node-signed, never a native API receipt. */
import { emptyActions, fixtureHash } from './admissionsFixtures';
import type { ActionsCurrentOut, ActionWriteReceipt, CaseActionsState, CreateManualApplicationV2, ManualApplicationRecordV2 } from '@/types/admissionsActions';

export function manualBody(): CreateManualApplicationV2 {
  return { schema_version: 'admissions-actions-v2', kind: 'create_application', client_write_uuid: '22222222-3333-4444-8555-666666666666',
    expected_revision: 0, label: 'Synthetic manual application', details: { due: null, notes: '' },
    target: { origin: 'applicant_entered', result_id: null, award_id: null, purpose: 'admission', university: 'Synthetic own university',
      programme: { state: 'unknown' }, award: { state: 'unknown' }, intake: { state: 'unknown' }, route: { state: 'unknown' },
      confirmed_entered_context: true, official_verification: 'not_performed' } };
}
export function manualFixture(body = manualBody(), profile = 'A') {
  const ref = { event_id: 'manual-event', revision: 1, kind: body.kind };
  const app: ManualApplicationRecordV2 = { id: 'manual-application', profile_id: profile, label: body.label,
    target: body.target, details: body.details, status: 'planning', created_ref: ref, latest_ref: ref, status_ref: null };
  const state: CaseActionsState = { schema_version: 'admissions-actions-v2', profile_id: profile, revision: 1,
    head_event_id: ref.event_id, applications: [app], document_tasks: [], active_preparation: null };
  const wire: Omit<ActionWriteReceipt, 'receipt_digest'> = { schema_version: 'admissions-actions-v2', event_id: ref.event_id,
    profile_id: profile, kind: body.kind, revision: 1, expected_revision: 0, client_write_uuid: body.client_write_uuid, request: body,
    canonical_request_digest: fixtureHash({ schema_version: 'g3-action-request-digest-v1', profile_id: profile, request: body }),
    accepted_at: '2026-10-13T10:00:00+00:00', actor: { schema_version: 'g3-actor-reference-v1', actor_kind: 'local_development', actor_ref_digest: 'a'.repeat(64) },
    predecessor_event_id: null, before_state_digest: null, after_state_digest: fixtureHash({ schema_version: 'g3-state-digest-v1', state }),
    applied_delta: { applications: [app], document_tasks: [], active_preparation: null, corrected_declaration: null, previous_binding_digest: null, declaration: null },
    affected_refs: { application_ids: [app.id], document_task_ids: [], active_selector_changed: false } };
  const receipt: ActionWriteReceipt = { ...wire, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: wire }) };
  const current: ActionsCurrentOut = { ...emptyActions(profile), revision: 1, state, head_receipt: receipt };
  return { body, app, state, receipt, current };
}
