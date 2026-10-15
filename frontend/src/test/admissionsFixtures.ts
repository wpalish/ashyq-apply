/** Synthetic test-only wire objects, signed by Node SHA256 independently of the browser codec. */
import { createHash } from 'node:crypto';
import type { ActionsCurrentOutV1, ActionWriteReceiptV1, CaseActionsStateV1, CreatePersonalTaskV1, DocumentTaskV1 } from '@/types/admissionsActions';

export const FIXTURE_UUID = '11111111-2222-4333-8444-555555555555';
export function actionBody(uuid = FIXTURE_UUID, revision = 0): CreatePersonalTaskV1 {
  return { schema_version: 'admissions-actions-v1', kind: 'create_personal_task', client_write_uuid: uuid,
    expected_revision: revision, application_id: null, personal: { label: 'Synthetic document task',
      responsible_actor: 'applicant', details: { due: null, notes: 'Synthetic own note' }, depends_on_task_ids: [] } };
}
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (typeof value === 'object' && value !== null) return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, item]) => [key, canonical(item)]));
  return value;
}
export const fixtureHash = (value: unknown) => createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
export function emptyActions(profile = 'A'): ActionsCurrentOutV1 {
  return { profile_id: profile, revision: 0, state: null, head_receipt: null, observed_at: '2026-10-13T10:00:00Z',
    current_source_statuses: [], document_report_reviews: [], action_links: [] };
}
export function acceptedActions(body = actionBody(), profile = 'A', eventId = 'event-a') {
  const revision = body.expected_revision + 1;
  const event = { event_id: eventId, revision, kind: body.kind };
  const actor = { schema_version: 'g3-actor-reference-v1' as const, actor_kind: 'local_development' as const, actor_ref_digest: 'a'.repeat(64) };
  const task: DocumentTaskV1 = { id: 'task-a', profile_id: profile, application_id: null, origin: 'applicant_entered',
    personal: body.personal, binding: null,
    report: { state: 'not_started', entered_at: null, accepted_at: null, actor: null, event_ref: null,
      binding_digest_at_report: null, origin: 'unreported', official_verification: 'not_performed' },
    created_ref: event, latest_ref: event, binding_ref: null };
  const state: CaseActionsStateV1 = { schema_version: 'admissions-actions-v1', profile_id: profile, revision,
    head_event_id: eventId, applications: [], document_tasks: [task], active_preparation: null };
  const request = { ...body, client_write_uuid: body.client_write_uuid.toLowerCase() };
  const wire: Omit<ActionWriteReceiptV1, 'receipt_digest'> = {
    schema_version: 'admissions-actions-v1', event_id: eventId, profile_id: profile, kind: body.kind,
    revision, expected_revision: body.expected_revision, client_write_uuid: request.client_write_uuid, request,
    canonical_request_digest: fixtureHash({ schema_version: 'g3-action-request-digest-v1', profile_id: profile, request }),
    accepted_at: '2026-10-13T10:00:00+00:00', actor,
    predecessor_event_id: body.expected_revision === 0 ? null : 'event-previous',
    before_state_digest: body.expected_revision === 0 ? null : 'b'.repeat(64),
    after_state_digest: fixtureHash({ schema_version: 'g3-state-digest-v1', state }),
    applied_delta: { applications: [], document_tasks: [task], active_preparation: null, corrected_declaration: null,
      previous_binding_digest: null, declaration: null },
    affected_refs: { application_ids: [], document_task_ids: [task.id], active_selector_changed: false },
  };
  const receipt: ActionWriteReceiptV1 = { ...wire, receipt_digest: fixtureHash({ schema_version: 'g3-action-receipt-digest-v1', receipt: wire }) };
  const current: ActionsCurrentOutV1 = { ...emptyActions(profile), revision, state, head_receipt: receipt };
  return { receipt, current, body };
}
