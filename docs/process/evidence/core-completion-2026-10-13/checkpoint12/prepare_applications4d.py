from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent;repo=root.parents[1]/'work/unimatch-calendar-materials';out=root/'applications4d-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/types/admissionsActions.ts','frontend/src/types/admissionsActions.edits.test.ts','frontend/src/lib/admissionsActionsRecovery.ts','frontend/src/lib/admissionsActionsRecovery.edits.test.ts','frontend/src/test/admissionsEditsFixtures.ts','frontend/src/screens/PersonalDocumentsPanel.tsx','frontend/src/screens/PersonalDocumentsPanel.test.tsx','frontend/src/screens/ApplicationsPanel.tsx','frontend/src/screens/ApplicationsPanel.test.tsx','frontend/src/components/AdmissionsRecoveryPanel.tsx','frontend/src/lib/i18n.ts'];rows={}
for p in paths:
 f=repo/p;raw=f.read_bytes() if f.exists() else None;rows[p]=hashlib.sha256(raw).hexdigest() if raw is not None else None
 if raw is not None:q=root/'applications4d-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(root/'APPLICATIONS_4D_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_PROPOSAL_ONLY_NOT_APPLIED_OR_GRANTED','paths':rows,'baseline':'9e41e0b3','scope':'Closed V2 metadata/context/remove codec and unchanged original-body journal/64; edit/delete forms and history snapshots with explicit personal action/retained binding warnings; current head_ref and context-review projection. Preserve frozen V1 guards and original manual V2 forms. Actual backend/native frozen4c running, no source/runtime mutation.'},indent=2)+'\n')
def get(p):return (repo/p).read_text()
def save(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='frontend/src/types/admissionsActions.ts';t=get(p)
new='''export type ActionCommandKindV2 = ActionCommandKind | 'remove_personal_action';
export interface ActionEventRefV2 extends Omit<ActionEventRefV1, 'kind'> { kind: ActionCommandKindV2 }
export interface SetDocumentMetadataV2 {
  schema_version: 'admissions-actions-v2'; kind: 'set_personal_details'; operation: 'document_metadata';
  client_write_uuid: string; expected_revision: number; target: Extract<PersonalActionRefV1, { kind: 'document_task' }>;
  personal: PersonalTaskInputV1; application_id: string | null; confirmed_personal_metadata: true;
}
export interface SetApplicationContextV2 {
  schema_version: 'admissions-actions-v2'; kind: 'set_personal_details'; operation: 'application_context';
  client_write_uuid: string; expected_revision: number; target: Extract<PersonalActionRefV1, { kind: 'application' }>;
  application_target: ApplicationTargetV1 | ManualApplicationTargetV2; label: string; details: ActionPersonalDetailsV1;
  confirmed_personal_context: true;
}
export interface RemovePersonalActionV2 {
  schema_version: 'admissions-actions-v2'; kind: 'remove_personal_action'; client_write_uuid: string;
  expected_revision: number; target: PersonalActionRefV1; confirmed_personal_removal: true;
}
export interface ContextApplicationRecordV2 extends Omit<ApplicationRecordV1, 'target'> {
  target: ApplicationTargetV1 | ManualApplicationTargetV2; context_ref: ActionEventRefV1 | null;
}
'''
t=t.replace('export type ActionRequest = ActionRequestV1 | CreateManualApplicationV2;',new+'export type ActionRequest = ActionRequestV1 | CreateManualApplicationV2 | SetDocumentMetadataV2 | SetApplicationContextV2 | RemovePersonalActionV2;',1)
t=t.replace('export type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2;', 'export type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2 | ContextApplicationRecordV2;',1)
t=t.replace("schema_version: 'admissions-actions-v1' | 'admissions-actions-v2'; applications: ApplicationRecord[];", "schema_version: 'admissions-actions-v1' | 'admissions-actions-v2'; applications: ApplicationRecord[]; head_ref?: ActionEventRefV2;",1)
t=t.replace("export interface AppliedDelta extends Omit<AppliedDeltaV1, 'applications'> { applications: ApplicationRecord[] }", "export interface AppliedDelta extends Omit<AppliedDeltaV1, 'applications'> { applications: ApplicationRecord[]; removed_application?: ApplicationRecord | null; removed_document_task?: DocumentTaskV1 | null }")
t=t.replace("Omit<ActionWriteReceiptV1, 'schema_version' | 'request' | 'applied_delta'>", "Omit<ActionWriteReceiptV1, 'schema_version' | 'request' | 'applied_delta' | 'kind'>",1).replace("request: ActionRequest; applied_delta: AppliedDelta;", "request: ActionRequest; applied_delta: AppliedDelta; kind: ActionCommandKindV2;",1)
t=t.replace("Omit<ActionsCurrentOutV1, 'state' | 'head_receipt'>", "Omit<ActionsCurrentOutV1, 'state' | 'head_receipt' | 'document_report_reviews'>",1).replace('state: CaseActionsState | null; head_receipt: ActionWriteReceipt | null;',"state: CaseActionsState | null; head_receipt: ActionWriteReceipt | null; document_report_reviews: { task_id: string; reasons: (DocumentReportReviewV1['reasons'][number] | 'application_context_changed')[] }[];",1)
# Add the read-only Today reason; original signed record/reference guards remain closed.
t=t.replace("| 'report_refers_to_previous_binding' | 'not_needed_is_not_a_waiver')[];", "| 'report_refers_to_previous_binding' | 'not_needed_is_not_a_waiver' | 'application_context_changed')[];",1)
start=t.index('export function isActionRequest(v:');end=t.index('\nconst manualApplicationRecord',start)
t=t[:start]+'''export function isActionRequest(v: unknown): v is ActionRequest {
  if (isActionRequestV1(v)) return true;
  if (!object(v) || v.schema_version !== 'admissions-actions-v2' || !uuid(v.client_write_uuid)
    || !integer(v.expected_revision, 0, ACTION_EXPECTED_REVISION_MAX)) return false;
  const base = ['schema_version', 'client_write_uuid', 'expected_revision', 'kind'];
  if (v.kind === 'create_application') return fields(v, [...base, 'target', 'label', 'details'])
    && isManualApplicationTargetV2(v.target) && text(v.label, 200, 1) && details(v.details);
  if (v.kind === 'remove_personal_action') return fields(v, [...base, 'target', 'confirmed_personal_removal'])
    && actionRef(v.target) && v.confirmed_personal_removal === true;
  if (v.kind !== 'set_personal_details' || !actionRef(v.target) || !object(v.target)) return false;
  if (v.operation === 'document_metadata') return fields(v, [...base, 'operation', 'target', 'personal', 'application_id', 'confirmed_personal_metadata'])
    && v.target.kind === 'document_task' && personal(v.personal) && nullable(v.application_id, exact) && v.confirmed_personal_metadata === true;
  return v.operation === 'application_context' && fields(v, [...base, 'operation', 'target', 'application_target', 'label', 'details', 'confirmed_personal_context'])
    && v.target.kind === 'application' && (target(v.application_target) || isManualApplicationTargetV2(v.application_target))
    && text(v.label, 200, 1) && details(v.details) && v.confirmed_personal_context === true;
}
'''+t[end:]
t=t.replace('const anyApplicationRecord = (v: unknown) => applicationRecord(v) || manualApplicationRecord(v);','''const contextApplicationRecord = (v: unknown) => {
  if (!object(v) || !Object.hasOwn(v, 'context_ref') || !nullable(v.context_ref, event)) return false;
  if (object(v.context_ref) && v.context_ref.kind !== 'set_personal_details') return false;
  const { context_ref: context, ...record } = v;
  return (context === null || object(context)) && (applicationRecord(record) || manualApplicationRecord(record));
};
const anyApplicationRecord = (v: unknown) => applicationRecord(v) || manualApplicationRecord(v) || contextApplicationRecord(v);
const eventV2 = (v: unknown) => event(v) || (object(v) && fields(v, ['event_id', 'revision', 'kind']) && exact(v.event_id)
  && integer(v.revision, 1, ACTION_REVISION_MAX) && v.kind === 'remove_personal_action');
const reportReviewV2 = (v: unknown) => reportReview(v) || (object(v) && fields(v, ['task_id', 'reasons']) && exact(v.task_id)
  && uniqueList(v.reasons, value => value === 'application_context_changed' || value === 'report_refers_to_previous_binding' || value === 'not_needed_is_not_a_waiver', 3));''',1)
# Generic receipt permits exactly old delta6 or new delta8; old frozen guard is untouched.
start=t.index('export function isActionWriteReceiptShape(v:');end=t.index('\nexport function isActionsCurrentOut(v:',start);block=t[start:end]
block=block.replace("!fields(delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])", "!(fields(delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])\n      || (v.schema_version === 'admissions-actions-v2' && fields(delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration', 'removed_application', 'removed_document_task'])\n        && nullable(delta.removed_application, anyApplicationRecord) && nullable(delta.removed_document_task, taskRecord)))")
block=block.replace('  const recordMatches =', '''  const removedApp = delta.removed_application ?? null; const removedTask = delta.removed_document_task ?? null;
  if (v.request.kind === 'remove_personal_action') {
    const requested = v.request.target.kind === 'application' ? removedApp : removedTask;
    const other = v.request.target.kind === 'application' ? removedTask : removedApp;
    return v.schema_version === 'admissions-actions-v2' && object(requested) && other === null
      && requested.id === v.request.target.id && requested.profile_id === v.profile_id && object(requested.latest_ref)
      && typeof requested.latest_ref.revision === 'number' && requested.latest_ref.revision <= v.expected_revision
      && apps.length === 0 && tasks.length === 0 && delta.active_preparation === null && delta.corrected_declaration === null
      && delta.previous_binding_digest === null && delta.declaration === null && affected.active_selector_changed === false
      && JSON.stringify(affected.application_ids) === JSON.stringify(v.request.target.kind === 'application' ? [requested.id] : [])
      && JSON.stringify(affected.document_task_ids) === JSON.stringify(v.request.target.kind === 'document_task' ? [requested.id] : []);
  }
  if (removedApp !== null || removedTask !== null) return false;
  const recordMatches =''',1)
block=block.replace("if (request.schema_version === 'admissions-actions-v2') {", "if (request.schema_version === 'admissions-actions-v2' && request.kind === 'create_application') {",1)
block=block.replace("  if (request.kind === 'select_active_preparation')", '''  if (request.schema_version === 'admissions-actions-v2' && request.kind === 'set_personal_details') {
    if (request.operation === 'document_metadata') {
      const task = tasks[0];
      if (apps.length !== 0 || tasks.length !== 1 || !object(task) || !object(task.personal) || task.id !== request.target.id
        || task.application_id !== request.application_id || task.personal.label !== request.personal.label
        || task.personal.responsible_actor !== request.personal.responsible_actor || !samePersonalDetails(task.personal.details, request.personal.details)
        || JSON.stringify(task.personal.depends_on_task_ids) !== JSON.stringify(request.personal.depends_on_task_ids)) return false;
    } else {
      const app = apps[0];
      if (tasks.length !== 0 || apps.length !== 1 || !object(app) || !contextApplicationRecord(app) || app.id !== request.target.id
        || app.label !== request.label || !samePersonalDetails(app.details, request.details)
        || !sameTarget(app.target, request.application_target)) return false;
    }
  }
  if (request.kind === 'select_active_preparation')''',1)
t=t[:start]+block+t[end:]
helper='''function sameTarget(actual: unknown, expected: ApplicationTargetV1 | ManualApplicationTargetV2): boolean {
  if (expected.result_id === null) return isManualApplicationTargetV2(actual) && sameManualTarget(actual, expected);
  return object(actual) && target(actual) && actual.result_id === expected.result_id && actual.purpose === expected.purpose
    && actual.award_id === expected.award_id && object(actual.intake) && object(actual.route)
    && sameEntered(actual.intake as EnteredOrUnknownText, expected.intake) && sameEntered(actual.route as EnteredOrUnknownText, expected.route);
}
'''
t=t.replace('export function isActionWriteReceiptShape(v:',helper+'export function isActionWriteReceiptShape(v:',1)
start=t.index('export function isActionsCurrentOut(v:');end=t.index('\nexport function isActionsHistoryOut(v:',start);block=t[start:end]
block=block.replace('!list(v.document_report_reviews, reportReview, 0, 400)', '!list(v.document_report_reviews, reportReviewV2, 0, 400)',1)
block=block.replace("!fields(state, ['schema_version', 'profile_id', 'revision', 'head_event_id', 'applications', 'document_tasks', 'active_preparation'])", "!(fields(state, ['schema_version', 'profile_id', 'revision', 'head_event_id', 'applications', 'document_tasks', 'active_preparation'])\n      || (state.schema_version === 'admissions-actions-v2' && fields(state, ['schema_version', 'profile_id', 'revision', 'head_event_id', 'applications', 'document_tasks', 'active_preparation', 'head_ref'])\n        && eventV2(state.head_ref) && object(state.head_ref) && state.head_ref.event_id === state.head_event_id && state.head_ref.revision === state.revision))",1)
old="      if (item.binding !== null && (!object(item.binding) || item.binding.result_id !== app.target.result_id)) return false;"
new="""      if (item.binding !== null && (!object(item.binding) || item.binding.result_id !== app.target.result_id)) {
        if (!Object.hasOwn(state, 'head_ref') || !object(app.context_ref) || !object(item.binding_ref)
          || typeof app.context_ref.revision !== 'number' || typeof item.binding_ref.revision !== 'number'
          || app.context_ref.revision <= item.binding_ref.revision) return false;
      }"""
assert old in block;block=block.replace(old,new,1);t=t[:start]+block+t[end:]
save(p,t)
p='frontend/src/lib/admissionsActionsRecovery.ts';t=get(p).replace('type ActionCommandKind,','type ActionCommandKindV2,',1).replace('kind: ActionCommandKind;', 'kind: ActionCommandKindV2;',1).replace("'correct_declaration', 'import_legacy_marks', 'select_active_preparation'].includes(v.kind)","'correct_declaration', 'import_legacy_marks', 'select_active_preparation', 'remove_personal_action'].includes(v.kind)",1)
t=t.replace("if (body.kind === 'set_personal_details') (body.target.kind === 'application' ? applications : tasks).push(body.target.id);", "if (body.kind === 'set_personal_details' || body.kind === 'remove_personal_action') (body.target.kind === 'application' ? applications : tasks).push(body.target.id);",1)
t=t.replace("if (body.kind === 'create_application' && body.target.result_id !== null) results.push(body.target.result_id);", "if (body.kind === 'create_application' && body.target.result_id !== null) results.push(body.target.result_id);\n  if (body.kind === 'set_personal_details' && body.schema_version === 'admissions-actions-v2' && body.operation === 'application_context' && body.application_target.result_id !== null) results.push(body.application_target.result_id);",1)
old="return fields(receipt.applied_delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])"
new="return (fields(receipt.applied_delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])\n    || (receipt.schema_version === 'admissions-actions-v2' && fields(receipt.applied_delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration', 'removed_application', 'removed_document_task'])))"
assert old in t;t=t.replace(old,new,1)
# Explicit UTC normalization of retained removed snapshots without adding absent old fields.
marker='      active_preparation: delta.active_preparation'
t=t.replace(marker,"""      ...('removed_document_task' in delta ? { removed_document_task: delta.removed_document_task == null ? null : {
        ...delta.removed_document_task,
        binding: delta.removed_document_task.binding === null ? null : { ...delta.removed_document_task.binding, accepted_at: canonicalUtc(delta.removed_document_task.binding.accepted_at) },
        report: { ...delta.removed_document_task.report, accepted_at: delta.removed_document_task.report.accepted_at === null ? null : canonicalUtc(delta.removed_document_task.report.accepted_at) },
      } } : {}),
"""+marker,1)
save(p,t)
p='frontend/src/components/AdmissionsRecoveryPanel.tsx';t=get(p).replace("correct_declaration: 'actions.correctDeclaration',", "remove_personal_action: 'actions.removePersonal', correct_declaration: 'actions.correctDeclaration',",1);save(p,t)
print('External closed V2 edit/removal/context codec proposals prepared; primary/lab untouched during full gate.')
