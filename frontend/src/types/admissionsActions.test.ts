import { acceptedActions, emptyActions } from '@/test/admissionsFixtures';
import { describe, expect, it } from 'vitest';
import {
  ACTION_COMMAND_KINDS, ACTION_EXPECTED_REVISION_MAX, ACTION_REVISION_MAX, isActionRequestV1, isNativeHeadV1, isActionsCurrentOutV1, isActionsHistoryOutV1,
  type ActionRequestV1, type BindingSelectionV1, type LegacyImportMappingV1,
} from './admissionsActions';

const uuid = '11111111-2222-4333-8444-555555555555';
const digest = 'a'.repeat(64);
const base = { schema_version: 'admissions-actions-v1' as const, client_write_uuid: uuid, expected_revision: 3 };
const details = { due: null, notes: '  Жеке жазба / личная заметка  ' };
const personal = { label: '  Prepare résumé  ', responsible_actor: 'applicant' as const, details, depends_on_task_ids: [] };
const moment = { local_date: '2026-10-12', local_time: null, timezone: null, origin: 'applicant_entered' as const };
const submission = { entered_at: moment, channel: 'University portal', reference: 'Personal reference', document_task_ids: ['task-a'], confirmed_applicant_declaration: true as const };
const withdrawal = { entered_at: null, notes: '', confirmed_applicant_declaration: true as const };
const source: BindingSelectionV1 = {
  result_id: 'result-a', purpose: 'admission', award_id: null, award_relation: 'unknown', checklist_digest: digest,
  procedure_digest: digest, occurrences: [{ result_id: 'result-a', location: 'admission_documents', index: 0,
    item_digest: digest, item_semantics_digest: digest, proof_reference_digest: digest }], original_claim_ids: [],
  g1_document: null, g1_relation: 'document_predicate_not_projected',
};
const mapping: LegacyImportMappingV1 = { task_id: 'task-a', legacy_key_digest: digest, expected_binding_digest: null,
  source_preview_digest: null, legacy_value: true, confirmed_prepared_report: true, source_version: 'unknown', original_reported_at: null };
const commands: ActionRequestV1[] = [
  { ...base, kind: 'create_application', target: { result_id: 'result-a', purpose: 'admission', award_id: null,
    intake: { state: 'unknown' }, route: { state: 'applicant_entered', value: '  Applicant entered route  ' }, confirmed_entered_context: true }, label: 'Synthetic application', details },
  { ...base, kind: 'create_personal_task', application_id: null, personal },
  { ...base, kind: 'bind_source_task', application_id: null, source, source_preview_digest: digest, personal },
  { ...base, kind: 'rebind_source_task', task_id: 'task-a', expected_binding_digest: null, source, source_preview_digest: digest },
  { ...base, kind: 'set_document_self_report', task_id: 'task-a', report: { state: 'prepared_reported', entered_at: moment, confirmed_personal_report: true } },
  { ...base, kind: 'set_personal_details', target: { kind: 'document_task', id: 'task-a' }, details },
  { ...base, kind: 'set_planning_status', application_id: 'app-a', status: 'preparing' },
  { ...base, kind: 'declare_submission', application_id: 'app-a', submission },
  { ...base, kind: 'declare_withdrawal', application_id: 'app-a', withdrawal },
  { ...base, kind: 'correct_declaration', application_id: 'app-a', prior_declaration: { event_id: 'event-a', revision: 2, kind: 'declare_submission' },
    replacement: { kind: 'planning', status: 'planning' }, confirmed_correction: true },
  { ...base, kind: 'import_legacy_marks', legacy_snapshot_digest: digest, mappings: [mapping], entered_at: null },
  { ...base, kind: 'select_active_preparation', origin: 'g2', policy: 'follow_current_accepted', observed_head: {
    origin: 'g2', profile_id: 'case-a', native_schema_version: 'shared-route-v1', revision: 2, client_write_uuid: uuid,
    snapshot_digest: digest, allocation_digest: digest, accepted_at: '2026-10-12T00:00:00Z' } },
];

describe('G3 closed twelve personal command forms', () => {
  it('covers exactly the frozen twelve kinds without a replacement-state or none command', () => {
    expect(commands.map(command => command.kind)).toEqual(ACTION_COMMAND_KINDS);
    expect(isActionRequestV1({ ...base, kind: 'replace_state', state: {} })).toBe(false);
    expect(isActionRequestV1({ ...base, kind: 'select_active_preparation', origin: 'none', policy: 'follow_current_accepted', observed_head: null })).toBe(false);
  });
  it.each(commands.map(command => [command.kind, command] as const))('%s preserves valid original input without trimming or inventing fields', (_kind, command) => {
    const before = JSON.stringify(command);
    expect(isActionRequestV1(command)).toBe(true); expect(JSON.stringify(command)).toBe(before);
  });
  it.each(commands.map(command => [command.kind, command] as const))('%s rejects forged authority, nonfinite CAS, coercion and bad UUID', (_kind, command) => {
    expect(isActionRequestV1({ ...command, actor: { user_id: 'forged' } })).toBe(false);
    expect(isActionRequestV1({ ...command, expected_revision: Infinity })).toBe(false);
    expect(isActionRequestV1({ ...command, expected_revision: true })).toBe(false);
    expect(isActionRequestV1({ ...command, expected_revision: ACTION_REVISION_MAX })).toBe(false);
    expect(isActionRequestV1({ ...command, client_write_uuid: 'uuid invented from a label' })).toBe(false);
  });
  it('keeps read revision maximum distinct from writable predecessor maximum', () => {
    expect(ACTION_EXPECTED_REVISION_MAX + 1).toBe(ACTION_REVISION_MAX);
    expect(isActionRequestV1({ ...commands[1], expected_revision: ACTION_EXPECTED_REVISION_MAX })).toBe(true);
    expect(isNativeHeadV1({ origin: 'legacy_v1', profile_id: 'case-a', native_schema_version: 'schedule-v1',
      revision: ACTION_REVISION_MAX, saved_settings_digest: digest, settings_fingerprint: digest })).toBe(true);
  });
  it('accepts meaningful spaces and non-ASCII personal content but refuses non-exact identities', () => {
    expect(isActionRequestV1({ ...commands[1], personal: { ...personal, label: '😀'.repeat(200) } })).toBe(true);
    expect(isActionRequestV1({ ...commands[1], personal: { ...personal, label: '😀'.repeat(201) } })).toBe(false);
    expect(isActionRequestV1({ ...commands[1], application_id: ' app-a ' })).toBe(false);
    expect(isActionRequestV1({ ...commands[1], personal: { ...personal, depends_on_task_ids: ['task-a', 'task-a'] } })).toBe(false);
  });
  it('requires personal confirmations and real entered dates without manufacturing official deadlines', () => {
    expect(isActionRequestV1({ ...commands[4], report: { state: 'prepared_reported', entered_at: moment, confirmed_personal_report: false } })).toBe(false);
    expect(isActionRequestV1({ ...commands[5], details: { notes: '', due: { origin: 'applicant_entered', local_date: '2026-02-30', timezone: 'UTC', official_deadline: false } } })).toBe(false);
    expect(isActionRequestV1({ ...commands[5], details: { notes: '', due: { origin: 'applicant_entered', local_date: '2026-10-12', timezone: null, official_deadline: true } } })).toBe(false);
    expect(isActionRequestV1({ ...commands[7], submission: { ...submission, entered_at: { ...moment, local_time: '24:00' } } })).toBe(false);
  });
  it('retains raw occurrence indices, exact result identity and separate source-preview token', () => {
    expect(isActionRequestV1({ ...commands[2], source: { ...source, occurrences: [{ ...source.occurrences[0], result_id: 'result-b' }] } })).toBe(false);
    expect(isActionRequestV1({ ...commands[2], source: { ...source, occurrences: [source.occurrences[0], source.occurrences[0]] } })).toBe(false);
    expect(isActionRequestV1({ ...commands[2], source: { ...source, g1_relation: 'exact_projection', g1_document: null } })).toBe(false);
    expect(isActionRequestV1({ ...commands[2], source_preview_digest: null })).toBe(false);
  });
  it('never treats a legacy false mark, guessed version or guessed historical date as an import', () => {
    expect(isActionRequestV1({ ...commands[10], mappings: [{ ...mapping, legacy_value: false }] })).toBe(false);
    expect(isActionRequestV1({ ...commands[10], mappings: [{ ...mapping, source_version: 'guessed-version' }] })).toBe(false);
    expect(isActionRequestV1({ ...commands[10], mappings: [{ ...mapping, original_reported_at: '2026-01-01' }] })).toBe(false);
    expect(isActionRequestV1({ ...commands[10], mappings: [mapping, mapping] })).toBe(false);
    expect(isActionRequestV1({ ...commands[10], mappings: Array.from({ length: 51 }, (_, index) => ({ ...mapping, task_id: `task-${index}`, legacy_key_digest: index.toString(16).padStart(64, '0') })) })).toBe(false);
  });
  it('does not retarget a selected native origin or correct an unrelated/future event', () => {
    expect(isActionRequestV1({ ...commands[11], origin: 'legacy_v1' })).toBe(false);
    expect(isActionRequestV1({ ...commands[9], prior_declaration: { event_id: 'event-a', revision: 4, kind: 'declare_submission' } })).toBe(false);
    expect(isActionRequestV1({ ...commands[9], prior_declaration: { event_id: 'event-a', revision: 2, kind: 'set_document_self_report' } })).toBe(false);
  });
});

describe('finite G3 enum scalar boundary repair', () => {
  it.each(['array', 'object', 'boolean'])('refuses %s values instead of coercing command actor/report/declaration enums', shape => {
    const invalid = (valid: string): unknown => shape === 'array' ? [valid] : shape === 'object' ? { value: valid } : true;
    expect(isActionRequestV1({ ...commands[1], personal: { ...personal, responsible_actor: invalid('applicant') } })).toBe(false);
    expect(isActionRequestV1({ ...commands[4], report: { state: invalid('prepared_reported'), entered_at: moment, confirmed_personal_report: true } })).toBe(false);
    expect(isActionRequestV1({ ...commands[9], prior_declaration: { event_id: 'event-a', revision: 2, kind: invalid('declare_submission') } })).toBe(false);
  });
});

// New readers keep the native current/history ownership and head shape explicit.


it('accepts native absent/current projections and ascending own history', () => {
  const fixture = acceptedActions(); expect(isActionsCurrentOutV1(emptyActions())).toBe(true);
  expect(isActionsCurrentOutV1(fixture.current)).toBe(true);
  expect(isActionsHistoryOutV1({ profile_id: 'A', events: [fixture.receipt], next_after_revision: 1, source_evaluation: 'not_evaluated' })).toBe(true);
});
it.each(['head_case', 'head_revision', 'head_id', 'task_owner', 'extra', 'array'])('rejects an inconsistent %s current projection', problem => {
  const fixture = acceptedActions(); const raw = structuredClone(fixture.current);
  if (!raw.head_receipt || !raw.state) throw new Error('Synthetic current fixture');
  if (problem === 'head_case') raw.head_receipt.profile_id = 'foreign';
  if (problem === 'head_revision') raw.head_receipt.revision += 1;
  if (problem === 'head_id') raw.state.head_event_id = 'another';
  if (problem === 'task_owner') { const task = raw.state.document_tasks[0]; if (task) task.profile_id = 'foreign'; }
  expect(isActionsCurrentOutV1(problem === 'extra' ? { ...raw, extra: true } : problem === 'array' ? [] : raw)).toBe(false);
});
it('does not treat malformed empty/current or foreign/duplicated history as a valid read', () => {
  expect(isActionsCurrentOutV1({ ...emptyActions(), revision: 1 })).toBe(false);
  const fixture = acceptedActions();
  expect(isActionsHistoryOutV1({ profile_id: 'B', events: [fixture.receipt], next_after_revision: null, source_evaluation: 'not_evaluated' })).toBe(false);
  expect(isActionsHistoryOutV1({ profile_id: 'A', events: [fixture.receipt, fixture.receipt], next_after_revision: null, source_evaluation: 'not_evaluated' })).toBe(false);
});
