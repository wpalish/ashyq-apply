from pathlib import Path
import json
root=Path(__file__).resolve().parent; repo=root.parents[1]/'work/unimatch-calendar-materials'; pre=root/'applications4a-preimages'; out=root/'applications4a-proposal';out.mkdir(exist_ok=False)
def read(p): return (pre/p).read_text()
def save(p,t): q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='backend/app/schemas/admissions_actions.py';t=read(p)
new='''class ManualApplicationTargetV2(Base):
    """Applicant context only; no fabricated programme/award evidence identity."""

    origin: Literal["applicant_entered"] = "applicant_entered"
    result_id: Literal[None] = None
    award_id: Literal[None] = None
    purpose: Literal["admission", "scholarship"]
    university: Label
    programme: EnteredOrUnknownText
    award: EnteredOrUnknownText
    intake: EnteredOrUnknownText
    route: EnteredOrUnknownText
    confirmed_entered_context: Confirmed
    official_verification: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def _award(self) -> Self:
        if self.purpose == "admission" and self.award.state != "unknown":
            raise ValueError("An admission target carries no invented award")
        return self


class CreateManualApplicationV2(Base):
    schema_version: Literal["admissions-actions-v2"]
    kind: Literal["create_application"] = "create_application"
    client_write_uuid: WriteUuid
    expected_revision: ExpectedRevision
    target: ManualApplicationTargetV2
    label: Label
    details: PersonalDetailsV1


'''
t=t.replace('class CreateApplicationV1(CommandBase):',new+'class CreateApplicationV1(CommandBase):',1)
# V2 reuses the unchanged V1 event roles. Only the manual target and outer schema change.
record=t[t.index('class ApplicationRecordV1(Base):'):t.index('class DocumentTaskV1(Base):')].replace('ApplicationRecordV1','ManualApplicationRecordV2').replace('target: ApplicationTargetV1','target: ManualApplicationTargetV2')
state=t[t.index('class CaseActionsStateV1(Base):'):t.index('class EventAffectedRefsV1(Base):')].replace('CaseActionsStateV1','CaseActionsStateV2').replace('Literal["admissions-actions-v1"] = "admissions-actions-v1"','Literal["admissions-actions-v2"] = "admissions-actions-v2"').replace('applications: list[ApplicationRecordV1]','applications: list[ApplicationRecord]')
delta=t[t.index('class AppliedDeltaV1(Base):'):t.index('class ActionWriteReceiptV1(Base):')].replace('AppliedDeltaV1','AppliedDeltaV2').replace('applications: list[ApplicationRecordV1]','applications: list[ApplicationRecord]')
receipt=t[t.index('class ActionWriteReceiptV1(Base):'):t.index('class EventMetadataV1(Base):')].replace('ActionWriteReceiptV1','ActionWriteReceiptV2').replace('Literal["admissions-actions-v1"] = "admissions-actions-v1"','Literal["admissions-actions-v2"] = "admissions-actions-v2"').replace('request: ActionRequestV1','request: ActionRequest').replace('applied_delta: AppliedDeltaV1','applied_delta: AppliedDeltaV2')
block=record+'type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2\ntype ActionRequest = ActionRequestV1 | CreateManualApplicationV2\n\n\n'+state+'type CaseActionsState = CaseActionsStateV1 | CaseActionsStateV2\n\n\n'+delta+receipt+'type ActionWriteReceipt = ActionWriteReceiptV1 | ActionWriteReceiptV2\n\n\n'
t=t.replace('class EventMetadataV1(Base):',block+'class EventMetadataV1(Base):',1)
t=t.replace('application_summaries: list[ApplicationRecordV1]','application_summaries: list[ApplicationRecord]')
t=t.replace('def source_target_ids(state: CaseActionsStateV1)', 'def source_target_ids(state: CaseActionsState)')
t=t.replace('values = [item.target.result_id for item in state.applications]','values = [item.target.result_id for item in state.applications if item.target.result_id is not None]')
t=t.replace('    state: CaseActionsStateV1,\n) -> list[tuple', '    state: CaseActionsState,\n) -> list[tuple')
t=t.replace('request: ActionRequestV1) -> str:', 'request: ActionRequest) -> str:').replace('def state_digest(state: CaseActionsStateV1)', 'def state_digest(state: CaseActionsState)').replace('def receipt_digest(value: ActionWriteReceiptV1)', 'def receipt_digest(value: ActionWriteReceipt)').replace('def delta_affected(delta: AppliedDeltaV1)', 'def delta_affected(delta: AppliedDeltaV1 | AppliedDeltaV2)').replace('def validate_receipt_delta(receipt: ActionWriteReceiptV1)', 'def validate_receipt_delta(receipt: ActionWriteReceipt)')
t=t.replace('applied_records: list[ApplicationRecordV1 | DocumentTaskV1]', 'applied_records: list[ApplicationRecord | DocumentTaskV1]')
t=t.replace('isinstance(request, CreateApplicationV1) and (','isinstance(request, CreateApplicationV1 | CreateManualApplicationV2) and (')
save(p,t)
p='backend/app/domain/admissions_actions.py';t=read(p)
t=t.replace('s.ActionRequestV1','s.ActionRequest').replace('s.ActionWriteReceiptV1 | None','s.ActionWriteReceipt | None').replace('-> s.ActionWriteReceiptV1','-> s.ActionWriteReceipt').replace('list[s.ActionWriteReceiptV1]','list[s.ActionWriteReceipt]').replace('s.CaseActionsStateV1 | None','s.CaseActionsState | None').replace('-> s.CaseActionsStateV1','-> s.CaseActionsState').replace('state: s.CaseActionsStateV1','state: s.CaseActionsState').replace('receipt: s.ActionWriteReceiptV1','receipt: s.ActionWriteReceipt')
# Dedicated union parsers preserve the class-based validator used for every V1 non-union shape.
marker='def actor_reference('
parsers='''def validate_state(value: object) -> s.CaseActionsState:
    try:
        s.finite_wire(value)
        raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return TypeAdapter(s.CaseActionsState).validate_python(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("saved_unreadable") from None


def validate_receipt(value: object) -> s.ActionWriteReceipt:
    try:
        s.finite_wire(value)
        raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return TypeAdapter(s.ActionWriteReceipt).validate_python(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("saved_unreadable") from None


'''
t=t.replace(marker,parsers+marker,1)
import re
t=re.sub(r'validate_model\(s.ActionWriteReceiptV1, ([^\n]+?), "saved_unreadable"\)',r'validate_receipt(\1)',t)
t=re.sub(r'validate_model\(s.CaseActionsStateV1, ([^\n]+?), "saved_unreadable"\)',r'validate_state(\1)',t)
t=t.replace('changed_apps: list[s.ApplicationRecordV1]','changed_apps: list[s.ApplicationRecord]').replace('def application(record_id: str) -> s.ApplicationRecordV1','def application(record_id: str) -> s.ApplicationRecord')
start=t.index('    if isinstance(request, s.CreateApplicationV1):',t.index('def apply_action'))
end=t.index('        if len(applications) >= 20:',start)
t=t[:start]+'''    if isinstance(request, s.CreateApplicationV1 | s.CreateManualApplicationV2):
        if isinstance(request, s.CreateApplicationV1):
            target = _selected(context.profile_id, request.target.result_id, context.target)
            if request.target.award_id is not None:
                if not target.research_access:
                    raise ActionError("source_locked")
                if request.target.award_id not in target.award_ids:
                    raise ActionError("record_not_found")
'''+t[end:]
t=t.replace('''        changed_apps = [
            s.ApplicationRecordV1(''','''        record_class = (
            s.ApplicationRecordV1 if isinstance(request, s.CreateApplicationV1)
            else s.ManualApplicationRecordV2
        )
        changed_apps = [
            record_class(''',1)
# Existing exact declarations/details operate on the exact saved record class, with no fake result.
t=t.replace('s.ApplicationRecordV1,\n                    application(request.target.id),','type(application(request.target.id)),\n                    application(request.target.id),')
t=t.replace('s.ApplicationRecordV1,\n                current_app,','type(current_app),\n                current_app,')
t=t.replace('s.ApplicationRecordV1,\n                application(request.application_id),','type(application(request.application_id)),\n                application(request.application_id),')
t=t.replace('prospective_ids = {item.target.result_id for item in applications}','prospective_ids = {item.target.result_id for item in applications if item.target.result_id is not None}')
t=t.replace('''    state = validate_model(
        s.CaseActionsStateV1,''','''    v2 = isinstance(old, s.CaseActionsStateV2) or isinstance(request, s.CreateManualApplicationV2)
    state = validate_model(
        s.CaseActionsStateV2 if v2 else s.CaseActionsStateV1,''',1)
t=t.replace('''    delta = s.AppliedDeltaV1(''','''    delta = (s.AppliedDeltaV2 if v2 else s.AppliedDeltaV1)(''',1)
t=t.replace('"schema_version": "admissions-actions-v1",\n    }','"schema_version": "admissions-actions-v2" if v2 else "admissions-actions-v1",\n    }',1)
t=t.replace('receipt = validate_model(s.ActionWriteReceiptV1, receipt_wire, "saved_unreadable")','receipt = validate_receipt(receipt_wire)')
t=t.replace('record: s.DocumentTaskV1 | s.ApplicationRecordV1','record: s.DocumentTaskV1 | s.ApplicationRecord').replace('entered = False\n            card_id', 'entered = isinstance(record, s.ManualApplicationRecordV2)\n            card_id')
save(p,t)
p='backend/app/api/routes_admissions_actions.py';t=read(p)
t=t.replace('s.ActionRequestV1','s.ActionRequest').replace('s.ActionWriteReceiptV1','s.ActionWriteReceipt').replace('s.CaseActionsStateV1','s.CaseActionsState')
t=t.replace('d.validate_model(s.ActionWriteReceipt, row.receipt, "saved_unreadable")','d.validate_receipt(row.receipt)').replace('d.validate_model(s.CaseActionsState, row.state, "saved_unreadable")','d.validate_state(row.state)')
t=t.replace('new_application_id=uuid4().hex if isinstance(request, s.CreateApplicationV1) else None,','new_application_id=uuid4().hex\n        if isinstance(request, s.CreateApplicationV1 | s.CreateManualApplicationV2) else None,')
save(p,t)
p='backend/app/models/admissions_actions.py';t=read(p).replace('"schema_version = \'admissions-actions-v1\'",','"schema_version IN (\'admissions-actions-v1\', \'admissions-actions-v2\')",');save(p,t)
print('Four source proposals prepared. Migration and native tests next; no application yet.')
