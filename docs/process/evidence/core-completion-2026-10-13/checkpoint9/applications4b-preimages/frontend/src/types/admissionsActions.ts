/** The frozen G3 wire. Reports and declarations do not certify university receipt. */
import type { GraphChecklistLocation, LearningTaskRef } from '@/types';

export type ActionCommandKind = 'create_application' | 'create_personal_task' | 'bind_source_task'
  | 'rebind_source_task' | 'set_document_self_report' | 'set_personal_details' | 'set_planning_status'
  | 'declare_submission' | 'declare_withdrawal' | 'correct_declaration' | 'import_legacy_marks'
  | 'select_active_preparation';
export type DocumentReportState = 'not_started' | 'in_progress' | 'prepared_reported' | 'sent_reported'
  | 'received_reported' | 'not_needed_reported';
export type ApplicationStatus = 'planning' | 'preparing' | 'submitted_declared' | 'withdrawn_declared';
export type ResponsibleActor = 'applicant' | 'school' | 'recommender' | 'third_party';
export interface ActionEventRefV1 { event_id: string; revision: number; kind: ActionCommandKind }
export interface ActionActorRefV1 {
  schema_version: 'g3-actor-reference-v1'; actor_kind: 'authenticated_principal' | 'local_development'; actor_ref_digest: string;
}
export type EnteredOrUnknownText = { state: 'applicant_entered'; value: string } | { state: 'unknown' };
export interface ApplicationTargetV1 {
  result_id: string; purpose: 'admission' | 'scholarship'; award_id: string | null;
  intake: EnteredOrUnknownText; route: EnteredOrUnknownText; confirmed_entered_context: true;
}
export interface EnteredDueDateV1 {
  origin: 'applicant_entered'; local_date: string; timezone: string | null; official_deadline: false;
}
export interface DeclaredMomentV1 {
  local_date: string; local_time: string | null; timezone: string | null; origin: 'applicant_entered';
}
export interface ActionPersonalDetailsV1 { due: EnteredDueDateV1 | null; notes: string }
export interface PersonalTaskInputV1 {
  label: string; responsible_actor: ResponsibleActor; details: ActionPersonalDetailsV1; depends_on_task_ids: string[];
}
export interface RawOccurrenceRefV1 {
  result_id: string; location: GraphChecklistLocation; index: number;
  item_digest: string; item_semantics_digest: string; proof_reference_digest: string;
}
export interface G1DocumentRefV1 {
  action_id: string; source_fingerprint: string; result_snapshot_digest: string;
  authoritative_evidence_digest: string; resolved_claim_ids: string[];
}
export interface BindingSelectionV1 {
  result_id: string; purpose: 'admission' | 'scholarship' | 'both'; award_id: string | null;
  award_relation: 'unknown'; checklist_digest: string; procedure_digest: string; occurrences: RawOccurrenceRefV1[];
  original_claim_ids: string[]; g1_document: G1DocumentRefV1 | null;
  g1_relation: 'exact_projection' | 'ambiguous_occurrence' | 'document_predicate_not_projected';
}
export interface ChecklistBindingReceiptV1 extends BindingSelectionV1 {
  profile_id: string; accepted_at: string; binding_digest: string;
}
export interface SelfReportInputV1 {
  state: DocumentReportState; entered_at: DeclaredMomentV1 | null; confirmed_personal_report: true;
}
export interface DocumentSelfReportV1 {
  state: DocumentReportState; entered_at: DeclaredMomentV1 | null; accepted_at: string | null;
  actor: ActionActorRefV1 | null; event_ref: ActionEventRefV1 | null; binding_digest_at_report: string | null;
  origin: 'unreported' | 'applicant_report' | 'explicit_browser_mark_import'; official_verification: 'not_performed';
}
export interface SubmissionInputV1 {
  entered_at: DeclaredMomentV1; channel: string; reference: string; document_task_ids: string[];
  confirmed_applicant_declaration: true;
}
export interface WithdrawalInputV1 {
  entered_at: DeclaredMomentV1 | null; notes: string; confirmed_applicant_declaration: true;
}
export interface DeclaredSubmissionV1 {
  kind: 'applicant_declared_submission'; application_id: string; event_ref: ActionEventRefV1;
  entered: SubmissionInputV1; accepted_at: string; actor: ActionActorRefV1;
  receipt_origin: 'applicant'; official_verification: 'not_performed';
}
export interface DeclaredWithdrawalV1 {
  kind: 'applicant_declared_withdrawal'; application_id: string; event_ref: ActionEventRefV1;
  entered: WithdrawalInputV1; accepted_at: string; actor: ActionActorRefV1;
  receipt_origin: 'applicant'; official_verification: 'not_performed';
}
export interface G2HeadV1 {
  origin: 'g2'; profile_id: string; native_schema_version: 'shared-route-v1'; revision: number;
  client_write_uuid: string; snapshot_digest: string; allocation_digest: string; accepted_at: string;
}
export interface LegacyV2HeadV1 {
  origin: 'legacy_v2'; profile_id: string; native_schema_version: 'schedule-v2'; revision: number;
  persisted_sidecar_digest: string; draft_fingerprint: string; legacy_fingerprint: string; observed_structural_fingerprint: string;
}
export interface LegacyV1HeadV1 {
  origin: 'legacy_v1'; profile_id: string; native_schema_version: 'schedule-v1'; revision: number;
  saved_settings_digest: string; settings_fingerprint: string;
}
export type NativeHeadV1 = G2HeadV1 | LegacyV2HeadV1 | LegacyV1HeadV1;
export interface ActivePreparationSelectionV1 {
  origin: 'g2' | 'legacy_v2' | 'legacy_v1'; policy: 'follow_current_accepted';
  observed_head: NativeHeadV1; event_ref: ActionEventRefV1;
}
interface CommandBaseV1 {
  schema_version: 'admissions-actions-v1'; client_write_uuid: string; expected_revision: number;
}
export interface CreateApplicationV1 extends CommandBaseV1 {
  kind: 'create_application'; target: ApplicationTargetV1; label: string; details: ActionPersonalDetailsV1;
}
export interface CreatePersonalTaskV1 extends CommandBaseV1 {
  kind: 'create_personal_task'; application_id: string | null; personal: PersonalTaskInputV1;
}
export interface BindSourceTaskV1 extends CommandBaseV1 {
  kind: 'bind_source_task'; application_id: string | null; source: BindingSelectionV1;
  source_preview_digest: string; personal: PersonalTaskInputV1;
}
export interface RebindSourceTaskV1 extends CommandBaseV1 {
  kind: 'rebind_source_task'; task_id: string; expected_binding_digest: string | null;
  source: BindingSelectionV1; source_preview_digest: string;
}
export type PersonalActionRefV1 = { kind: 'application'; id: string } | { kind: 'document_task'; id: string };
export interface SetDocumentSelfReportV1 extends CommandBaseV1 {
  kind: 'set_document_self_report'; task_id: string; report: SelfReportInputV1;
}
export interface SetPersonalDetailsV1 extends CommandBaseV1 {
  kind: 'set_personal_details'; target: PersonalActionRefV1; details: ActionPersonalDetailsV1;
}
export interface SetPlanningStatusV1 extends CommandBaseV1 {
  kind: 'set_planning_status'; application_id: string; status: 'planning' | 'preparing';
}
export interface DeclareSubmissionV1 extends CommandBaseV1 {
  kind: 'declare_submission'; application_id: string; submission: SubmissionInputV1;
}
export interface DeclareWithdrawalV1 extends CommandBaseV1 {
  kind: 'declare_withdrawal'; application_id: string; withdrawal: WithdrawalInputV1;
}
export type CorrectionValueV1 = { kind: 'submission'; submission: SubmissionInputV1 }
  | { kind: 'withdrawal'; withdrawal: WithdrawalInputV1 } | { kind: 'planning'; status: 'planning' | 'preparing' };
export interface CorrectDeclarationV1 extends CommandBaseV1 {
  kind: 'correct_declaration'; application_id: string; prior_declaration: ActionEventRefV1;
  replacement: CorrectionValueV1; confirmed_correction: true;
}
export interface LegacyImportMappingV1 {
  task_id: string; legacy_key_digest: string; expected_binding_digest: string | null; source_preview_digest: string | null;
  legacy_value: true; confirmed_prepared_report: true; source_version: 'unknown'; original_reported_at: null;
}
export interface ImportLegacyMarksV1 extends CommandBaseV1 {
  kind: 'import_legacy_marks'; legacy_snapshot_digest: string; mappings: LegacyImportMappingV1[];
  entered_at: DeclaredMomentV1 | null;
}
export interface SelectActivePreparationV1 extends CommandBaseV1 {
  kind: 'select_active_preparation'; origin: 'g2' | 'legacy_v2' | 'legacy_v1';
  policy: 'follow_current_accepted'; observed_head: NativeHeadV1;
}
export type ActionRequestV1 = CreateApplicationV1 | CreatePersonalTaskV1 | BindSourceTaskV1 | RebindSourceTaskV1
  | SetDocumentSelfReportV1 | SetPersonalDetailsV1 | SetPlanningStatusV1 | DeclareSubmissionV1
  | DeclareWithdrawalV1 | CorrectDeclarationV1 | ImportLegacyMarksV1 | SelectActivePreparationV1;
export interface ApplicationRecordV1 {
  id: string; profile_id: string; target: ApplicationTargetV1; label: string; details: ActionPersonalDetailsV1;
  status: ApplicationStatus; created_ref: ActionEventRefV1; latest_ref: ActionEventRefV1; status_ref: ActionEventRefV1 | null;
}
export interface DocumentTaskV1 {
  id: string; profile_id: string; application_id: string | null; origin: 'applicant_entered' | 'source_reference';
  personal: PersonalTaskInputV1; binding: ChecklistBindingReceiptV1 | null; report: DocumentSelfReportV1;
  created_ref: ActionEventRefV1; latest_ref: ActionEventRefV1; binding_ref: ActionEventRefV1 | null;
}
export interface CaseActionsStateV1 {
  schema_version: 'admissions-actions-v1'; profile_id: string; revision: number; head_event_id: string;
  applications: ApplicationRecordV1[]; document_tasks: DocumentTaskV1[]; active_preparation: ActivePreparationSelectionV1 | null;
}
export interface EventAffectedRefsV1 {
  application_ids: string[]; document_task_ids: string[]; active_selector_changed: boolean;
}
export interface AppliedDeltaV1 {
  applications: ApplicationRecordV1[]; document_tasks: DocumentTaskV1[]; active_preparation: ActivePreparationSelectionV1 | null;
  corrected_declaration: ActionEventRefV1 | null; previous_binding_digest: string | null;
  declaration: DeclaredSubmissionV1 | DeclaredWithdrawalV1 | null;
}
export interface ActionWriteReceiptV1 {
  schema_version: 'admissions-actions-v1'; event_id: string; profile_id: string; kind: ActionCommandKind;
  revision: number; expected_revision: number; client_write_uuid: string; request: ActionRequestV1;
  canonical_request_digest: string; accepted_at: string; actor: ActionActorRefV1; predecessor_event_id: string | null;
  before_state_digest: string | null; after_state_digest: string; applied_delta: AppliedDeltaV1;
  affected_refs: EventAffectedRefsV1; receipt_digest: string;
}
export type SourceReasonV1 = 'stale' | 'scope_unknown' | 'scope_mismatch' | 'conflict' | 'ambiguous_occurrence'
  | 'proof_changed_item_same' | 'item_changed' | 'procedure_order_changed' | 'award_relation_unknown'
  | 'document_predicate_not_projected' | 'proof_unresolved';
export interface SourceReadStatusV1 {
  result_id: string; target_state: 'eligible' | 'decision_changed' | 'result_unavailable';
  source_state: 'not_evaluated' | 'research_locked' | 'current_reference' | 'source_changed' | 'evidence_unknown';
  observed_at: string; current_digest: string | null; reasons: SourceReasonV1[];
}
export interface ActionLinkReadV1 {
  role: 'programme_information' | 'requirements_information' | 'applicant_entered_external';
  provenance: 'current_source' | 'applicant_entered' | 'demo' | 'unknown'; destination_verification: 'not_performed';
  state: 'actionable_unverified' | 'blocked' | 'demo_text' | 'not_available'; href: string | null;
  reason: 'informational_unverified' | 'link_form_unavailable' | 'demo_reference' | 'not_available';
}
export interface DocumentReportReviewV1 {
  task_id: string; reasons: ('report_refers_to_previous_binding' | 'not_needed_is_not_a_waiver')[];
}
export interface ResultActionLinksV1 {
  result_id: string; programme_information: ActionLinkReadV1; requirements_information: ActionLinkReadV1;
}
export interface ActionsCurrentOutV1 {
  profile_id: string; revision: number; state: CaseActionsStateV1 | null; head_receipt: ActionWriteReceiptV1 | null;
  observed_at: string; current_source_statuses: SourceReadStatusV1[];
  document_report_reviews: DocumentReportReviewV1[]; action_links: ResultActionLinksV1[];
}
export interface ActionsHistoryOutV1 {
  profile_id: string; events: ActionWriteReceiptV1[]; next_after_revision: number | null; source_evaluation: 'not_evaluated';
}
export interface OccurrenceSelectionInV1 { location: GraphChecklistLocation; index: number }
export interface SourceBindingPreviewInV1 {
  result_id: string; purpose: 'admission' | 'scholarship' | 'both'; award_id: string | null; occurrences: OccurrenceSelectionInV1[];
}
export interface SourceBindingPreviewOutV1 {
  profile_id: string; result_id: string; selection: BindingSelectionV1; source_preview_digest: string;
  source_status: SourceReadStatusV1; observed_at: string;
}
export interface LegacyImportPreviewInV1 {
  expected_revision: number; legacy_snapshot_digest: string; mappings: LegacyImportMappingV1[];
}
export interface LegacyImportPreviewOutV1 {
  profile_id: string; revision: number; legacy_snapshot_digest: string; mappings: LegacyImportMappingV1[]; observed_at: string;
}
export interface StudyActionReadV1 {
  id: string; local_date: string; timezone: string; ref: LearningTaskRef | null; planned_minutes: number;
  availability: 'available' | 'unavailable' | 'unsupported'; completion: 'not_projected' | 'self_reported_complete';
}
export interface ActivePreparationReadV1 {
  origin: 'none' | 'g2' | 'legacy_v2' | 'legacy_v1' | 'unknown';
  selection_source: 'accepted_g3_event' | 'derived_backward_default' | 'unavailable';
  state: 'available' | 'needs_review' | 'unavailable' | 'absent'; selection: ActivePreparationSelectionV1 | null;
  current_observed_head: NativeHeadV1 | null; observed_at: string; goal_result_ids: string[];
  study_actions: StudyActionReadV1[]; allocated_minutes: number | null; needs_review: boolean;
}
export interface PreparationAccessReadV1 {
  allowed: boolean; reason: 'active' | 'expired' | 'not_started' | 'unavailable' | 'development';
  starts_at: string | null; ends_at: string | null; development_only: boolean; observed_at: string;
}
export interface TodayDateReadV1 {
  local_date: string | null; timezone: string | null;
  certainty: 'applicant_entered' | 'date_only_timezone_unknown' | 'source_date_only' | 'previous_cycle' | 'unknown';
  comparison_zone: string; fallback_display_only: boolean; official_closure: 'not_assessed';
}
export interface TodayCardV1 {
  id: string; reason: 'personal_document_action' | 'personal_application_action' | 'accepted_study_action';
  target: PersonalActionRefV1 | LearningTaskRef | null; target_result_id: string | null; date: TodayDateReadV1;
  dependency_reasons: ('dependency_missing' | 'dependency_cycle' | 'dependency_not_reported_ready'
    | 'report_refers_to_previous_binding' | 'not_needed_is_not_a_waiver')[];
  workload_origin: 'g2' | 'legacy_v2' | 'legacy_v1' | 'personal_unallocated'; planned_minutes: number | null;
  source_state: 'applicant_entered' | SourceReadStatusV1['source_state']; actionable: boolean;
}
export interface TodayNoticeV1 {
  code: 'mixed_revision' | 'actions_unavailable' | 'plan_unavailable' | 'plan_needs_review'
    | 'preparation_locked' | 'source_review' | 'dependency_review'; record_id: string | null;
}
export interface TodayProjectionV1 {
  schema_version: 'admissions-today-v1'; profile_id: string; as_of: string; display_timezone: string;
  action_state: 'readable' | 'absent' | 'unavailable'; action_revision: number | null; action_digest: string | null;
  action_observed_at: string; active_plan: ActivePreparationReadV1; preparation_access: PreparationAccessReadV1;
  current_source_statuses: SourceReadStatusV1[]; consistency: 'component_reads' | 'mixed_revision'; needs_refresh: boolean;
  notices: TodayNoticeV1[]; overdue_personal: TodayCardV1[]; today_study: TodayCardV1[]; today_personal: TodayCardV1[];
  future: TodayCardV1[]; undated_personal: TodayCardV1[]; application_summaries: ApplicationRecordV1[];
  workload: 'one_selected_plan' | 'unknown'; allocated_study_minutes: number | null;
  personal_minutes: 'not_estimated'; readiness: 'not_assessed';
}

export const ACTION_EXPECTED_REVISION_MAX = 2147483646;
export const ACTION_REVISION_MAX = 2147483647;
export const ACTION_COMMAND_KINDS: readonly ActionCommandKind[] = [
  'create_application', 'create_personal_task', 'bind_source_task', 'rebind_source_task', 'set_document_self_report',
  'set_personal_details', 'set_planning_status', 'declare_submission', 'declare_withdrawal', 'correct_declaration',
  'import_legacy_marks', 'select_active_preparation',
];
const locations: readonly GraphChecklistLocation[] = ['admission_documents', 'scholarship_documents', 'applicant_actions',
  'school_actions', 'recommender_actions', 'certification_actions'];
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const fields = (v: Record<string, unknown>, names: readonly string[]) => names.length === Object.keys(v).length
  && names.every(k => Object.hasOwn(v, k));
const integer = (v: unknown, min: number, max: number): v is number => typeof v === 'number'
  && Number.isSafeInteger(v) && v >= min && v <= max;
const text = (v: unknown, max: number, min = 0): v is string => typeof v === 'string' && Array.from(v).length >= min && Array.from(v).length <= max;
const exact = (v: unknown, max = 32): v is string => text(v, max, 1) && v === v.trim() && !Array.from(v).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127);
const digest = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === 'string'
  && /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(v);
const nullable = (v: unknown, check: (value: unknown) => boolean) => v === null || check(v);
const list = (v: unknown, check: (value: unknown) => boolean, min: number, max: number): v is unknown[] =>
  Array.isArray(v) && Array.from(v).length >= min && Array.from(v).length <= max && v.every(value => check(value));
const uniqueList = (v: unknown, check: (value: unknown) => boolean, max: number): v is unknown[] =>
  list(v, check, 0, max) && new Set(v).size === v.length;
const date = (v: unknown): v is string => typeof v === 'string' && /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v)
  && Number(v.slice(0, 4)) >= 1 && !Number.isNaN(Date.parse(`${v}T00:00:00Z`))
  && new Date(`${v}T00:00:00Z`).toISOString().slice(0, 10) === v;
const zone = (v: unknown): v is string => {
  if (!text(v, 80, 1)) return false;
  try { new Intl.DateTimeFormat('en', { timeZone: v }); return true; } catch { return false; }
};
const utc = (v: unknown): v is string => typeof v === 'string'
  && /^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?(?:Z|\+00:00)$/.test(v) && date(v.slice(0, 10)) && !Number.isNaN(Date.parse(v));
const enteredText = (v: unknown) => object(v) && ((v.state === 'unknown' && fields(v, ['state']))
  || (v.state === 'applicant_entered' && fields(v, ['state', 'value']) && text(v.value, 200, 1)));
const moment = (v: unknown) => object(v) && fields(v, ['local_date', 'local_time', 'timezone', 'origin'])
  && date(v.local_date) && nullable(v.local_time, x => typeof x === 'string' && /^(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?$/.test(x))
  && nullable(v.timezone, zone) && v.origin === 'applicant_entered';
const details = (v: unknown) => object(v) && fields(v, ['due', 'notes']) && text(v.notes, 2000)
  && nullable(v.due, x => object(x) && fields(x, ['origin', 'local_date', 'timezone', 'official_deadline'])
    && x.origin === 'applicant_entered' && date(x.local_date) && nullable(x.timezone, zone) && x.official_deadline === false);
const personal = (v: unknown) => object(v) && fields(v, ['label', 'responsible_actor', 'details', 'depends_on_task_ids'])
  && text(v.label, 200, 1) && typeof v.responsible_actor === 'string' && ['applicant', 'school', 'recommender', 'third_party'].includes(v.responsible_actor)
  && details(v.details) && uniqueList(v.depends_on_task_ids, exact, 400);
const submission = (v: unknown) => object(v) && fields(v, ['entered_at', 'channel', 'reference', 'document_task_ids', 'confirmed_applicant_declaration'])
  && moment(v.entered_at) && text(v.channel, 200, 1) && text(v.reference, 2000)
  && uniqueList(v.document_task_ids, exact, 400) && v.confirmed_applicant_declaration === true;
const withdrawal = (v: unknown) => object(v) && fields(v, ['entered_at', 'notes', 'confirmed_applicant_declaration'])
  && nullable(v.entered_at, moment) && text(v.notes, 2000) && v.confirmed_applicant_declaration === true;
const event = (v: unknown) => object(v) && fields(v, ['event_id', 'revision', 'kind']) && exact(v.event_id)
  && integer(v.revision, 1, ACTION_REVISION_MAX) && ACTION_COMMAND_KINDS.some(k => k === v.kind);
const actionRef = (v: unknown) => object(v) && fields(v, ['kind', 'id']) && exact(v.id)
  && (v.kind === 'application' || v.kind === 'document_task');
const target = (v: unknown) => object(v) && fields(v, ['result_id', 'purpose', 'award_id', 'intake', 'route', 'confirmed_entered_context'])
  && exact(v.result_id) && (v.purpose === 'admission' || v.purpose === 'scholarship') && nullable(v.award_id, x => exact(x, 200))
  && (v.purpose === 'scholarship') === (v.award_id !== null) && enteredText(v.intake) && enteredText(v.route)
  && v.confirmed_entered_context === true;
export function isBindingSelectionV1(v: unknown): v is BindingSelectionV1 {
  if (!object(v) || !fields(v, ['result_id', 'purpose', 'award_id', 'award_relation', 'checklist_digest', 'procedure_digest',
    'occurrences', 'original_claim_ids', 'g1_document', 'g1_relation']) || !exact(v.result_id)
    || !['admission', 'scholarship', 'both'].some(x => x === v.purpose) || !nullable(v.award_id, x => exact(x, 200))
    || (v.purpose === 'admission' && v.award_id !== null) || v.award_relation !== 'unknown'
    || !digest(v.checklist_digest) || !digest(v.procedure_digest) || !uniqueList(v.original_claim_ids, x => exact(x, 200), 4000)
    || !list(v.occurrences, x => object(x) && fields(x, ['result_id', 'location', 'index', 'item_digest', 'item_semantics_digest', 'proof_reference_digest'])
      && x.result_id === v.result_id && locations.some(k => k === x.location) && integer(x.index, 0, Number.MAX_SAFE_INTEGER)
      && digest(x.item_digest) && digest(x.item_semantics_digest) && digest(x.proof_reference_digest), 1, 6)) return false;
  if (new Set(v.occurrences.map(x => object(x) ? x.location : null)).size !== v.occurrences.length) return false;
  if (!['exact_projection', 'ambiguous_occurrence', 'document_predicate_not_projected'].some(x => x === v.g1_relation)
    || (v.g1_relation === 'exact_projection') !== (v.g1_document !== null)) return false;
  return v.g1_document === null || (object(v.g1_document) && fields(v.g1_document, ['action_id', 'source_fingerprint',
    'result_snapshot_digest', 'authoritative_evidence_digest', 'resolved_claim_ids']) && exact(v.g1_document.action_id, 200)
    && digest(v.g1_document.source_fingerprint) && digest(v.g1_document.result_snapshot_digest)
    && digest(v.g1_document.authoritative_evidence_digest) && uniqueList(v.g1_document.resolved_claim_ids, exact, 4000));
}
export function isNativeHeadV1(v: unknown): v is NativeHeadV1 {
  if (!object(v) || !exact(v.profile_id) || !integer(v.revision, 1, ACTION_REVISION_MAX)) return false;
  if (v.origin === 'g2') return fields(v, ['origin', 'profile_id', 'native_schema_version', 'revision', 'client_write_uuid', 'snapshot_digest', 'allocation_digest', 'accepted_at'])
    && v.native_schema_version === 'shared-route-v1' && uuid(v.client_write_uuid) && digest(v.snapshot_digest) && digest(v.allocation_digest) && utc(v.accepted_at);
  if (v.origin === 'legacy_v2') return fields(v, ['origin', 'profile_id', 'native_schema_version', 'revision', 'persisted_sidecar_digest', 'draft_fingerprint', 'legacy_fingerprint', 'observed_structural_fingerprint'])
    && v.native_schema_version === 'schedule-v2' && digest(v.persisted_sidecar_digest) && digest(v.draft_fingerprint)
    && digest(v.legacy_fingerprint) && digest(v.observed_structural_fingerprint);
  return v.origin === 'legacy_v1' && fields(v, ['origin', 'profile_id', 'native_schema_version', 'revision', 'saved_settings_digest', 'settings_fingerprint'])
    && v.native_schema_version === 'schedule-v1' && digest(v.saved_settings_digest) && digest(v.settings_fingerprint);
}
/** Only typed G2 UUID/UTC fields normalize; six microsecond digits remain significant. */
function nativeHeadUtc(value: string): string {
  return value.replace(/^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,6}))?(?:Z|\+00:00)$/,
    (_match, instant: string, fraction: string | undefined) => {
      const micros = fraction?.padEnd(6, '0');
      return `${instant}${micros && /[1-9]/.test(micros) ? `.${micros}` : ''}+00:00`;
    });
}
function sameNativeHead(value: unknown, request: NativeHeadV1): boolean {
  if (!isNativeHeadV1(value) || value.origin !== request.origin || value.profile_id !== request.profile_id
    || value.native_schema_version !== request.native_schema_version || value.revision !== request.revision) return false;
  if (value.origin === 'g2' && request.origin === 'g2') return value.client_write_uuid.toLowerCase() === request.client_write_uuid.toLowerCase()
    && value.snapshot_digest === request.snapshot_digest && value.allocation_digest === request.allocation_digest
    && nativeHeadUtc(value.accepted_at) === nativeHeadUtc(request.accepted_at);
  if (value.origin === 'legacy_v2' && request.origin === 'legacy_v2') return value.persisted_sidecar_digest === request.persisted_sidecar_digest
    && value.draft_fingerprint === request.draft_fingerprint && value.legacy_fingerprint === request.legacy_fingerprint
    && value.observed_structural_fingerprint === request.observed_structural_fingerprint;
  return value.origin === 'legacy_v1' && request.origin === 'legacy_v1'
    && value.saved_settings_digest === request.saved_settings_digest && value.settings_fingerprint === request.settings_fingerprint;
}
const mapping = (v: unknown) => object(v) && fields(v, ['task_id', 'legacy_key_digest', 'expected_binding_digest', 'source_preview_digest',
  'legacy_value', 'confirmed_prepared_report', 'source_version', 'original_reported_at']) && exact(v.task_id) && digest(v.legacy_key_digest)
  && nullable(v.expected_binding_digest, digest) && nullable(v.source_preview_digest, digest) && v.legacy_value === true
  && v.confirmed_prepared_report === true && v.source_version === 'unknown' && v.original_reported_at === null;
export function isActionRequestV1(v: unknown): v is ActionRequestV1 {
  if (!object(v) || v.schema_version !== 'admissions-actions-v1' || !uuid(v.client_write_uuid)
    || !integer(v.expected_revision, 0, ACTION_EXPECTED_REVISION_MAX)) return false;
  const base = ['schema_version', 'client_write_uuid', 'expected_revision', 'kind'];
  switch (v.kind) {
    case 'create_application': return fields(v, [...base, 'target', 'label', 'details']) && target(v.target) && text(v.label, 200, 1) && details(v.details);
    case 'create_personal_task': return fields(v, [...base, 'application_id', 'personal']) && nullable(v.application_id, exact) && personal(v.personal);
    case 'bind_source_task': return fields(v, [...base, 'application_id', 'source', 'source_preview_digest', 'personal']) && nullable(v.application_id, exact)
      && isBindingSelectionV1(v.source) && digest(v.source_preview_digest) && personal(v.personal);
    case 'rebind_source_task': return fields(v, [...base, 'task_id', 'expected_binding_digest', 'source', 'source_preview_digest'])
      && exact(v.task_id) && nullable(v.expected_binding_digest, digest) && isBindingSelectionV1(v.source) && digest(v.source_preview_digest);
    case 'set_document_self_report': return fields(v, [...base, 'task_id', 'report']) && exact(v.task_id) && object(v.report)
      && fields(v.report, ['state', 'entered_at', 'confirmed_personal_report'])
      && typeof v.report.state === 'string' && ['not_started', 'in_progress', 'prepared_reported', 'sent_reported', 'received_reported', 'not_needed_reported'].includes(v.report.state)
      && nullable(v.report.entered_at, moment) && v.report.confirmed_personal_report === true;
    case 'set_personal_details': return fields(v, [...base, 'target', 'details']) && actionRef(v.target) && details(v.details);
    case 'set_planning_status': return fields(v, [...base, 'application_id', 'status']) && exact(v.application_id) && (v.status === 'planning' || v.status === 'preparing');
    case 'declare_submission': return fields(v, [...base, 'application_id', 'submission']) && exact(v.application_id) && submission(v.submission);
    case 'declare_withdrawal': return fields(v, [...base, 'application_id', 'withdrawal']) && exact(v.application_id) && withdrawal(v.withdrawal);
    case 'correct_declaration': return fields(v, [...base, 'application_id', 'prior_declaration', 'replacement', 'confirmed_correction'])
      && exact(v.application_id) && event(v.prior_declaration) && object(v.prior_declaration)
      && typeof v.prior_declaration.kind === 'string' && ['declare_submission', 'declare_withdrawal', 'correct_declaration'].includes(v.prior_declaration.kind)
      && typeof v.prior_declaration.revision === 'number' && v.prior_declaration.revision <= v.expected_revision
      && v.confirmed_correction === true && object(v.replacement)
      && ((v.replacement.kind === 'submission' && fields(v.replacement, ['kind', 'submission']) && submission(v.replacement.submission))
        || (v.replacement.kind === 'withdrawal' && fields(v.replacement, ['kind', 'withdrawal']) && withdrawal(v.replacement.withdrawal))
        || (v.replacement.kind === 'planning' && fields(v.replacement, ['kind', 'status']) && (v.replacement.status === 'planning' || v.replacement.status === 'preparing')));
    case 'import_legacy_marks': return fields(v, [...base, 'legacy_snapshot_digest', 'mappings', 'entered_at']) && digest(v.legacy_snapshot_digest)
      && nullable(v.entered_at, moment) && list(v.mappings, mapping, 1, 50)
      && new Set(v.mappings.map(x => object(x) ? x.task_id : null)).size === v.mappings.length
      && new Set(v.mappings.map(x => object(x) ? x.legacy_key_digest : null)).size === v.mappings.length;
    case 'select_active_preparation': return fields(v, [...base, 'origin', 'policy', 'observed_head']) && v.policy === 'follow_current_accepted'
      && isNativeHeadV1(v.observed_head) && v.origin === v.observed_head.origin;
    default: return false;
  }
}

const actor = (v: unknown) => object(v) && fields(v, ['schema_version', 'actor_kind', 'actor_ref_digest'])
  && v.schema_version === 'g3-actor-reference-v1' && (v.actor_kind === 'authenticated_principal' || v.actor_kind === 'local_development')
  && digest(v.actor_ref_digest);
const selection = (v: unknown) => object(v) && fields(v, ['origin', 'policy', 'observed_head', 'event_ref'])
  && v.policy === 'follow_current_accepted' && isNativeHeadV1(v.observed_head) && v.origin === v.observed_head.origin
  && event(v.event_ref) && object(v.event_ref) && v.event_ref.kind === 'select_active_preparation';
const report = (v: unknown) => {
  if (!object(v) || !fields(v, ['state', 'entered_at', 'accepted_at', 'actor', 'event_ref', 'binding_digest_at_report', 'origin', 'official_verification'])
    || typeof v.state !== 'string' || !['not_started', 'in_progress', 'prepared_reported', 'sent_reported', 'received_reported', 'not_needed_reported'].includes(v.state)
    || !nullable(v.entered_at, moment) || !nullable(v.accepted_at, utc) || !nullable(v.actor, actor)
    || !nullable(v.event_ref, event) || !nullable(v.binding_digest_at_report, digest) || v.official_verification !== 'not_performed') return false;
  if (v.origin === 'unreported') return v.state === 'not_started' && v.entered_at === null && v.accepted_at === null
    && v.actor === null && v.event_ref === null && v.binding_digest_at_report === null;
  if (v.accepted_at === null || v.actor === null || !object(v.event_ref)) return false;
  return (v.origin === 'applicant_report' && v.event_ref.kind === 'set_document_self_report')
    || (v.origin === 'explicit_browser_mark_import' && v.state === 'prepared_reported' && v.event_ref.kind === 'import_legacy_marks');
};
const bindingReceipt = (v: unknown) => {
  if (!object(v) || !exact(v.profile_id) || !utc(v.accepted_at) || !digest(v.binding_digest)) return false;
  const { profile_id: profile, accepted_at: time, binding_digest: identity, ...reference } = v;
  return !!profile && !!time && !!identity && isBindingSelectionV1(reference);
};
const applicationRecord = (v: unknown) => object(v) && fields(v, ['id', 'profile_id', 'target', 'label', 'details', 'status', 'created_ref', 'latest_ref', 'status_ref'])
  && exact(v.id) && exact(v.profile_id) && target(v.target) && text(v.label, 200, 1) && details(v.details)
  && typeof v.status === 'string' && ['planning', 'preparing', 'submitted_declared', 'withdrawn_declared'].includes(v.status)
  && event(v.created_ref) && event(v.latest_ref) && nullable(v.status_ref, event);
const taskRecord = (v: unknown) => object(v) && fields(v, ['id', 'profile_id', 'application_id', 'origin', 'personal', 'binding', 'report', 'created_ref', 'latest_ref', 'binding_ref'])
  && exact(v.id) && exact(v.profile_id) && nullable(v.application_id, exact) && personal(v.personal) && report(v.report)
  && event(v.created_ref) && event(v.latest_ref) && nullable(v.binding_ref, event)
  && ((v.binding === null && v.binding_ref === null && v.origin === 'applicant_entered')
    || (bindingReceipt(v.binding) && v.binding_ref !== null && v.origin === 'source_reference'));
const declaration = (v: unknown) => {
  if (!object(v) || !fields(v, ['kind', 'application_id', 'event_ref', 'entered', 'accepted_at', 'actor', 'receipt_origin', 'official_verification'])
    || !exact(v.application_id) || !event(v.event_ref) || !utc(v.accepted_at) || !actor(v.actor)
    || v.receipt_origin !== 'applicant' || v.official_verification !== 'not_performed') return false;
  return (v.kind === 'applicant_declared_submission' && submission(v.entered))
    || (v.kind === 'applicant_declared_withdrawal' && withdrawal(v.entered));
};
/** Closed wire shape only. Hashes and exact intent ownership are checked by the recovery caller. */
export function isActionWriteReceiptShapeV1(v: unknown): v is ActionWriteReceiptV1 {
  if (!object(v) || !fields(v, ['schema_version', 'event_id', 'profile_id', 'kind', 'revision', 'expected_revision', 'client_write_uuid',
    'request', 'canonical_request_digest', 'accepted_at', 'actor', 'predecessor_event_id', 'before_state_digest', 'after_state_digest',
    'applied_delta', 'affected_refs', 'receipt_digest']) || v.schema_version !== 'admissions-actions-v1'
    || !exact(v.event_id) || !exact(v.profile_id) || !isActionRequestV1(v.request) || v.kind !== v.request.kind
    || v.client_write_uuid !== v.request.client_write_uuid.toLowerCase() || v.expected_revision !== v.request.expected_revision
    || v.revision !== v.request.expected_revision + 1 || !integer(v.revision, 1, ACTION_REVISION_MAX)
    || !digest(v.canonical_request_digest) || !utc(v.accepted_at) || !actor(v.actor)
    || !digest(v.after_state_digest) || !digest(v.receipt_digest) || !object(v.applied_delta) || !object(v.affected_refs)) return false;
  if (v.expected_revision === 0 ? v.predecessor_event_id !== null || v.before_state_digest !== null
    : !exact(v.predecessor_event_id) || !digest(v.before_state_digest)) return false;
  const delta = v.applied_delta; const affected = v.affected_refs;
  if (!fields(delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])
    || !list(delta.applications, applicationRecord, 0, 20) || !list(delta.document_tasks, taskRecord, 0, 50)
    || !nullable(delta.active_preparation, selection) || !nullable(delta.corrected_declaration, event)
    || !nullable(delta.previous_binding_digest, digest) || !nullable(delta.declaration, declaration)
    || !fields(affected, ['application_ids', 'document_task_ids', 'active_selector_changed'])
    || !uniqueList(affected.application_ids, exact, 20) || !uniqueList(affected.document_task_ids, exact, 400)
    || typeof affected.active_selector_changed !== 'boolean') return false;
  const apps = delta.applications; const tasks = delta.document_tasks;
  const recordMatches = (item: unknown) => object(item) && item.profile_id === v.profile_id && object(item.latest_ref)
    && item.latest_ref.event_id === v.event_id && item.latest_ref.revision === v.revision && item.latest_ref.kind === v.kind;
  if (!apps.every(recordMatches) || !tasks.every(recordMatches)
    || JSON.stringify(apps.map(item => object(item) ? item.id : null)) !== JSON.stringify(affected.application_ids)
    || JSON.stringify(tasks.map(item => object(item) ? item.id : null)) !== JSON.stringify(affected.document_task_ids)
    || affected.active_selector_changed !== (delta.active_preparation !== null)) return false;
  const request = v.request;
  if (request.kind === 'select_active_preparation') return apps.length === 0 && tasks.length === 0 && object(delta.active_preparation)
    && object(delta.active_preparation.event_ref) && delta.active_preparation.event_ref.event_id === v.event_id
    && delta.active_preparation.event_ref.revision === v.revision && sameNativeHead(delta.active_preparation.observed_head, request.observed_head);
  if (delta.active_preparation !== null) return false;
  if (request.kind === 'set_personal_details') return request.target.kind === 'application'
    ? apps.length === 1 && tasks.length === 0 && object(apps[0]) && apps[0].id === request.target.id
    : tasks.length === 1 && apps.length === 0 && object(tasks[0]) && tasks[0].id === request.target.id;
  if (['create_personal_task', 'bind_source_task', 'rebind_source_task', 'set_document_self_report', 'import_legacy_marks'].includes(request.kind)) {
    if (apps.length !== 0 || tasks.length !== (request.kind === 'import_legacy_marks' ? request.mappings.length : 1)) return false;
    if (request.kind === 'rebind_source_task' || request.kind === 'set_document_self_report') return object(tasks[0]) && tasks[0].id === request.task_id;
    if (request.kind === 'import_legacy_marks') return JSON.stringify(tasks.map(item => object(item) ? item.id : null))
      === JSON.stringify(request.mappings.map(item => item.task_id));
    if (request.kind === 'create_personal_task') return object(tasks[0]) && tasks[0].binding === null
      && tasks[0].binding_ref === null && tasks[0].origin === 'applicant_entered';
    return true;
  }
  return apps.length === 1 && tasks.length === 0 && (request.kind === 'create_application'
    || ('application_id' in request && object(apps[0]) && apps[0].id === request.application_id));
}

const oneOf = (v: unknown, choices: readonly string[]): v is string => typeof v === 'string' && choices.includes(v);
const sourceReason = (v: unknown) => typeof v === 'string' && ['stale', 'scope_unknown', 'scope_mismatch', 'conflict',
  'ambiguous_occurrence', 'proof_changed_item_same', 'item_changed', 'procedure_order_changed', 'award_relation_unknown',
  'document_predicate_not_projected', 'proof_unresolved'].includes(v);
const sourceRead = (v: unknown) => object(v) && fields(v, ['result_id', 'target_state', 'source_state', 'observed_at', 'current_digest', 'reasons'])
  && exact(v.result_id) && oneOf(v.target_state, ['eligible', 'decision_changed', 'result_unavailable'])
  && oneOf(v.source_state, ['not_evaluated', 'research_locked', 'current_reference', 'source_changed', 'evidence_unknown'])
  && utc(v.observed_at) && nullable(v.current_digest, digest) && list(v.reasons, sourceReason, 0, 20);
const linkRead = (v: unknown) => object(v) && fields(v, ['role', 'provenance', 'destination_verification', 'state', 'href', 'reason'])
  && oneOf(v.role, ['programme_information', 'requirements_information', 'applicant_entered_external'])
  && oneOf(v.provenance, ['current_source', 'applicant_entered', 'demo', 'unknown'])
  && v.destination_verification === 'not_performed'
  && oneOf(v.state, ['actionable_unverified', 'blocked', 'demo_text', 'not_available'])
  && nullable(v.href, value => text(value, 2048, 1))
  && oneOf(v.reason, ['informational_unverified', 'link_form_unavailable', 'demo_reference', 'not_available'])
  && (v.state === 'actionable_unverified' ? v.href !== null : v.href === null);
const actionLinks = (v: unknown) => object(v) && fields(v, ['result_id', 'programme_information', 'requirements_information'])
  && exact(v.result_id) && linkRead(v.programme_information) && linkRead(v.requirements_information);
const reportReview = (v: unknown) => object(v) && fields(v, ['task_id', 'reasons']) && exact(v.task_id)
  && uniqueList(v.reasons, value => value === 'report_refers_to_previous_binding' || value === 'not_needed_is_not_a_waiver', 2);

/** Native current projection shape, ownership and head ordering; digest verified separately. */
export function isActionsCurrentOutV1(v: unknown): v is ActionsCurrentOutV1 {
  if (!object(v) || !fields(v, ['profile_id', 'revision', 'state', 'head_receipt', 'observed_at', 'current_source_statuses', 'document_report_reviews', 'action_links'])
    || !exact(v.profile_id) || !integer(v.revision, 0, ACTION_REVISION_MAX) || !utc(v.observed_at)
    || !list(v.current_source_statuses, sourceRead, 0, 20) || !list(v.document_report_reviews, reportReview, 0, 400)
    || !list(v.action_links, actionLinks, 0, 20)) return false;
  if (v.state === null || v.head_receipt === null) return v.state === null && v.head_receipt === null && v.revision === 0
    && v.current_source_statuses.length === 0 && v.document_report_reviews.length === 0 && v.action_links.length === 0;
  const state = v.state;
  if (!object(state) || !fields(state, ['schema_version', 'profile_id', 'revision', 'head_event_id', 'applications', 'document_tasks', 'active_preparation'])
    || state.schema_version !== 'admissions-actions-v1' || state.profile_id !== v.profile_id || state.revision !== v.revision
    || !list(state.applications, applicationRecord, 0, 20) || !list(state.document_tasks, taskRecord, 0, 400)
    || !nullable(state.active_preparation, selection) || !isActionWriteReceiptShapeV1(v.head_receipt)
    || v.head_receipt.profile_id !== v.profile_id || v.head_receipt.revision !== v.revision
    || state.head_event_id !== v.head_receipt.event_id) return false;
  const apps = state.applications; const tasks = state.document_tasks; const revision = v.revision;
  const records = [...apps, ...tasks];
  if (new Set(apps.map(item => object(item) ? item.id : null)).size !== apps.length
    || new Set(tasks.map(item => object(item) ? item.id : null)).size !== tasks.length
    || !records.every(item => object(item) && item.profile_id === v.profile_id && object(item.latest_ref)
      && typeof item.latest_ref.revision === 'number' && item.latest_ref.revision <= revision)) return false;
  for (const item of tasks) {
    if (!object(item)) return false;
    if (item.application_id !== null) {
      const app = apps.find(candidate => object(candidate) && candidate.id === item.application_id);
      if (!object(app) || !object(app.target)) return false;
      if (item.binding !== null && (!object(item.binding) || item.binding.result_id !== app.target.result_id)) return false;
    }
    if (item.binding !== null && (!object(item.binding) || item.binding.profile_id !== v.profile_id)) return false;
  }
  if (state.active_preparation !== null && (!object(state.active_preparation) || !object(state.active_preparation.observed_head)
    || state.active_preparation.observed_head.profile_id !== v.profile_id)) return false;
  return new Set(v.current_source_statuses.map(item => object(item) ? item.result_id : null)).size === v.current_source_statuses.length
    && new Set(v.action_links.map(item => object(item) ? item.result_id : null)).size === v.action_links.length;
}

export function isActionsHistoryOutV1(v: unknown): v is ActionsHistoryOutV1 {
  if (!object(v) || !fields(v, ['profile_id', 'events', 'next_after_revision', 'source_evaluation'])
    || !exact(v.profile_id) || v.source_evaluation !== 'not_evaluated'
    || !list(v.events, isActionWriteReceiptShapeV1, 0, 100)) return false;
  let revision = 0;
  for (const item of v.events) {
    if (!isActionWriteReceiptShapeV1(item) || item.profile_id !== v.profile_id || item.revision <= revision) return false;
    revision = item.revision;
  }
  return v.next_after_revision === null || (v.events.length > 0 && v.next_after_revision === revision);
}

export function isSourceBindingPreviewOutV1(v: unknown): v is SourceBindingPreviewOutV1 {
  return object(v) && fields(v, ['profile_id', 'result_id', 'selection', 'source_preview_digest', 'source_status', 'observed_at'])
    && exact(v.profile_id) && exact(v.result_id) && isBindingSelectionV1(v.selection)
    && v.selection.result_id === v.result_id && digest(v.source_preview_digest)
    && sourceRead(v.source_status) && object(v.source_status) && v.source_status.result_id === v.result_id && utc(v.observed_at);
}
export function isLegacyImportPreviewOutV1(v: unknown): v is LegacyImportPreviewOutV1 {
  return object(v) && fields(v, ['profile_id', 'revision', 'legacy_snapshot_digest', 'mappings', 'observed_at'])
    && exact(v.profile_id) && integer(v.revision, 0, ACTION_REVISION_MAX) && digest(v.legacy_snapshot_digest)
    && list(v.mappings, mapping, 1, 50) && utc(v.observed_at)
    && new Set(v.mappings.map(item => object(item) ? item.task_id : null)).size === v.mappings.length
    && new Set(v.mappings.map(item => object(item) ? item.legacy_key_digest : null)).size === v.mappings.length;
}
