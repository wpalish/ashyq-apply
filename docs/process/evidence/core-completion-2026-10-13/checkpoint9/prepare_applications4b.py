from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent;repo=root.parents[1]/'work/unimatch-calendar-materials';out=root/'applications4b-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/types/admissionsActions.ts','frontend/src/lib/admissionsActionsRecovery.ts','frontend/src/lib/useAdmissionsActions.ts','frontend/src/api/client.ts','frontend/src/components/AdmissionsRecoveryPanel.tsx','frontend/src/screens/ApplicationsPanel.tsx','frontend/src/screens/ApplicationsPanel.test.tsx','frontend/src/screens/ApprovedScreen.tsx','frontend/src/App.tsx','frontend/src/types/admissionsActions.manual.test.ts','frontend/src/lib/admissionsActionsRecovery.manual.test.ts','frontend/src/test/manualAdmissionsFixtures.ts','frontend/src/lib/i18n.ts']
rows={}
for p in paths:
 f=repo/p;rows[p]=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
 if f.exists():q=root/'applications4b-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(f.read_bytes())
(root/'APPLICATIONS_4B_PREPARATION.json').write_text(json.dumps({'baseline':'b4377de3','status':'EXTERNAL_PROPOSAL_ONLY_NOT_GRANTED_OR_APPLIED','paths':rows,'scope':'Typed explicit V1/V2 G3 transport/recovery preserving all old V1 guards, journal envelope/cap/hash namespaces; manual result null never journal result ref. Applications create from exact own selected result or explicit manual context; statuses/declaration/correction/history/forms through existing commands; source links only native safe read; ENRUkk, plan/documents reachable with saved profile and no research. No dispatch on load or new library/provider/prod/main action.'},indent=2)+'\n')
def get(p):return (repo/p).read_text()
def save(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='frontend/src/types/admissionsActions.ts';t=get(p)
new='''/** Explicit manual G3 V2 context. The frozen V1 target remains closed. */
export interface ManualApplicationTargetV2 {
  origin: 'applicant_entered'; result_id: null; award_id: null; purpose: 'admission' | 'scholarship';
  university: string; programme: EnteredOrUnknownText; award: EnteredOrUnknownText;
  intake: EnteredOrUnknownText; route: EnteredOrUnknownText; confirmed_entered_context: true;
  official_verification: 'not_performed';
}
export interface CreateManualApplicationV2 {
  schema_version: 'admissions-actions-v2'; kind: 'create_application'; client_write_uuid: string;
  expected_revision: number; target: ManualApplicationTargetV2; label: string; details: ActionPersonalDetailsV1;
}
export type ActionRequest = ActionRequestV1 | CreateManualApplicationV2;
export interface ManualApplicationRecordV2 extends Omit<ApplicationRecordV1, 'target'> { target: ManualApplicationTargetV2 }
export type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2;
export interface CaseActionsState extends Omit<CaseActionsStateV1, 'schema_version' | 'applications'> {
  schema_version: 'admissions-actions-v1' | 'admissions-actions-v2'; applications: ApplicationRecord[];
}
export interface AppliedDelta extends Omit<AppliedDeltaV1, 'applications'> { applications: ApplicationRecord[] }
export interface ActionWriteReceipt extends Omit<ActionWriteReceiptV1, 'schema_version' | 'request' | 'applied_delta'> {
  schema_version: 'admissions-actions-v1' | 'admissions-actions-v2'; request: ActionRequest; applied_delta: AppliedDelta;
}
export interface ActionsCurrentOut extends Omit<ActionsCurrentOutV1, 'state' | 'head_receipt'> {
  state: CaseActionsState | null; head_receipt: ActionWriteReceipt | null;
}
export interface ActionsHistoryOut extends Omit<ActionsHistoryOutV1, 'events'> { events: ActionWriteReceipt[] }

'''
t=t.replace('export type SourceReasonV1',new+'export type SourceReasonV1',1).replace('application_summaries: ApplicationRecordV1[]','application_summaries: ApplicationRecord[]')
manual='''export function isManualApplicationTargetV2(v: unknown): v is ManualApplicationTargetV2 {
  return object(v) && fields(v, ['origin', 'result_id', 'award_id', 'purpose', 'university', 'programme', 'award',
    'intake', 'route', 'confirmed_entered_context', 'official_verification']) && v.origin === 'applicant_entered'
    && v.result_id === null && v.award_id === null && (v.purpose === 'admission' || v.purpose === 'scholarship')
    && text(v.university, 200, 1) && enteredText(v.programme) && enteredText(v.award) && enteredText(v.intake)
    && enteredText(v.route) && v.confirmed_entered_context === true && v.official_verification === 'not_performed'
    && (v.purpose === 'scholarship' || (object(v.award) && v.award.state === 'unknown'));
}
export function isActionRequest(v: unknown): v is ActionRequest {
  return isActionRequestV1(v) || (object(v) && fields(v, ['schema_version', 'client_write_uuid', 'expected_revision',
    'kind', 'target', 'label', 'details']) && v.schema_version === 'admissions-actions-v2' && v.kind === 'create_application'
    && uuid(v.client_write_uuid) && integer(v.expected_revision, 0, ACTION_EXPECTED_REVISION_MAX)
    && isManualApplicationTargetV2(v.target) && text(v.label, 200, 1) && details(v.details));
}
const manualApplicationRecord = (v: unknown) => object(v) && fields(v, ['id', 'profile_id', 'target', 'label', 'details', 'status', 'created_ref', 'latest_ref', 'status_ref'])
  && exact(v.id) && exact(v.profile_id) && isManualApplicationTargetV2(v.target) && text(v.label, 200, 1) && details(v.details)
  && typeof v.status === 'string' && ['planning', 'preparing', 'submitted_declared', 'withdrawn_declared'].includes(v.status)
  && event(v.created_ref) && event(v.latest_ref) && nullable(v.status_ref, event);
const anyApplicationRecord = (v: unknown) => applicationRecord(v) || manualApplicationRecord(v);
function sameEntered(a: EnteredOrUnknownText, b: EnteredOrUnknownText): boolean {
  return a.state === b.state && (a.state === 'unknown' || (b.state === 'applicant_entered' && a.value === b.value));
}
function sameManualTarget(a: ManualApplicationTargetV2, b: ManualApplicationTargetV2): boolean {
  return a.university === b.university && a.purpose === b.purpose && sameEntered(a.programme, b.programme)
    && sameEntered(a.award, b.award) && sameEntered(a.intake, b.intake) && sameEntered(a.route, b.route);
}
'''
# Preserve original frozen guards byte-for-byte; generic guards are additive and remain closed by schema.
start=t.index('export function isActionWriteReceiptShapeV1(');end=t.index('\nconst oneOf =',start)
receipt=t[start:end].replace('isActionWriteReceiptShapeV1','isActionWriteReceiptShape').replace('v is ActionWriteReceiptV1','v is ActionWriteReceipt').replace("v.schema_version !== 'admissions-actions-v1'","(v.schema_version !== 'admissions-actions-v1' && v.schema_version !== 'admissions-actions-v2')").replace('!isActionRequestV1(v.request)','!isActionRequest(v.request)').replace('!list(delta.applications, applicationRecord, 0, 20)',"!list(delta.applications, v.schema_version === 'admissions-actions-v1' ? applicationRecord : anyApplicationRecord, 0, 20)")
receipt=receipt.replace('  const request = v.request;', '''  const request = v.request;
  if (v.schema_version === 'admissions-actions-v1' && request.schema_version !== 'admissions-actions-v1') return false;
  if (request.schema_version === 'admissions-actions-v2') {
    if (apps.length !== 1 || !object(apps[0]) || !isManualApplicationTargetV2(apps[0].target)
      || !sameManualTarget(request.target, apps[0].target) || apps[0].label !== request.label
      || JSON.stringify(apps[0].details) !== JSON.stringify(request.details)) return false;
  }''')
start=t.index('export function isActionsCurrentOutV1(');end=t.index('\nexport function isActionsHistoryOutV1',start)
current=t[start:end].replace('isActionsCurrentOutV1','isActionsCurrentOut').replace('v is ActionsCurrentOutV1','v is ActionsCurrentOut').replace("state.schema_version !== 'admissions-actions-v1'","(state.schema_version !== 'admissions-actions-v1' && state.schema_version !== 'admissions-actions-v2')").replace('!list(state.applications, applicationRecord, 0, 20)',"!list(state.applications, state.schema_version === 'admissions-actions-v1' ? applicationRecord : anyApplicationRecord, 0, 20)").replace('isActionWriteReceiptShapeV1','isActionWriteReceiptShape').replace('|| state.head_event_id !== v.head_receipt.event_id)', '|| state.head_event_id !== v.head_receipt.event_id || state.schema_version !== v.head_receipt.schema_version)')
start=t.index('export function isActionsHistoryOutV1(');end=t.index('\nexport function isSourceBindingPreviewOutV1',start)
history=t[start:end].replace('isActionsHistoryOutV1','isActionsHistoryOut').replace('v is ActionsHistoryOutV1','v is ActionsHistoryOut').replace('isActionWriteReceiptShapeV1','isActionWriteReceiptShape')
t += '\n'+manual+'\n'+receipt+'\n'+current+'\n'+history
save(p,t)
for p in ['frontend/src/lib/admissionsActionsRecovery.ts','frontend/src/lib/useAdmissionsActions.ts','frontend/src/api/client.ts','frontend/src/components/AdmissionsRecoveryPanel.tsx']:
 t=get(p)
 for old,newname in [('isActionRequestV1','isActionRequest'),('isActionWriteReceiptShapeV1','isActionWriteReceiptShape'),('isActionsCurrentOutV1','isActionsCurrentOut'),('isActionsHistoryOutV1','isActionsHistoryOut'),('ActionRequestV1','ActionRequest'),('ActionWriteReceiptV1','ActionWriteReceipt'),('ActionsCurrentOutV1','ActionsCurrentOut'),('ActionsHistoryOutV1','ActionsHistoryOut')]: t=t.replace(old,newname)
 if p.endswith('admissionsActionsRecovery.ts'):
  t=t.replace("if (body.kind === 'create_application') results.push(body.target.result_id);","if (body.kind === 'create_application' && body.target.result_id !== null) results.push(body.target.result_id);")
  t=t.replace("receipt.schema_version !== 'admissions-actions-v1'", "(receipt.schema_version !== 'admissions-actions-v1' && receipt.schema_version !== 'admissions-actions-v2')")
 save(p,t)
print('Five external transport/type proposals prepared; no primary/lab mutation during backend gate.')
