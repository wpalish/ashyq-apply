from pathlib import Path
root=Path(__file__).resolve().parent;pre=root/'applications4c-preimages';out=root/'applications4c-proposal';out.mkdir(exist_ok=False)
def get(path):return (pre/path).read_text()
def save(path,text):p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
p='backend/app/schemas/admissions_actions.py';t=get(p)
commands='''class SetDocumentMetadataV2(Base):
    schema_version: Literal["admissions-actions-v2"]
    kind: Literal["set_personal_details"] = "set_personal_details"
    client_write_uuid: WriteUuid
    expected_revision: ExpectedRevision
    operation: Literal["document_metadata"] = "document_metadata"
    target: DocumentTaskRefV1
    personal: PersonalTaskInputV1
    application_id: ExactId | None
    confirmed_personal_metadata: Confirmed


class SetApplicationContextV2(Base):
    schema_version: Literal["admissions-actions-v2"]
    kind: Literal["set_personal_details"] = "set_personal_details"
    client_write_uuid: WriteUuid
    expected_revision: ExpectedRevision
    operation: Literal["application_context"] = "application_context"
    target: ApplicationRefV1
    application_target: ApplicationTargetV1 | ManualApplicationTargetV2
    label: Label
    details: PersonalDetailsV1
    confirmed_personal_context: Confirmed


CommandKindV2 = CommandKind | Literal["remove_personal_action"]


class EventRefV2(Base):
    event_id: ExactId
    revision: Revision
    kind: CommandKindV2


class RemovePersonalActionV2(Base):
    schema_version: Literal["admissions-actions-v2"]
    kind: Literal["remove_personal_action"] = "remove_personal_action"
    client_write_uuid: WriteUuid
    expected_revision: ExpectedRevision
    target: PersonalActionRef
    confirmed_personal_removal: Confirmed


'''
t=t.replace('class ApplicationRecordV1(Base):',commands+'class ApplicationRecordV1(Base):',1)
# The context variant retains every original record role plus its explicit context-change ref.
record=t[t.index('class ManualApplicationRecordV2(Base):'):t.index('type ApplicationRecord =')]
record=record.replace('ManualApplicationRecordV2','ContextApplicationRecordV2').replace('target: ManualApplicationTargetV2','target: ApplicationTargetV1 | ManualApplicationTargetV2').replace('    status_ref: EventRefV1 | None','    status_ref: EventRefV1 | None\n    context_ref: EventRefV1 | None',1)
record=record.replace('        return self\n','''        if self.context_ref is not None:
            role(self.context_ref, {"set_personal_details"})
            if not self.created_ref.revision < self.context_ref.revision <= self.latest_ref.revision:
                raise ValueError("A context change retains its exact event order")
        return self
''',1)
t=t.replace('type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2',record+'type ApplicationRecord = ApplicationRecordV1 | ManualApplicationRecordV2 | ContextApplicationRecordV2',1)
t=t.replace('type ActionRequest = ActionRequestV1 | CreateManualApplicationV2','type ActionRequest = ActionRequestV1 | CreateManualApplicationV2 | SetDocumentMetadataV2 | SetApplicationContextV2 | RemovePersonalActionV2',1)
state=t[t.index('class CaseActionsStateV2(Base):'):t.index('type CaseActionsState =')].replace('CaseActionsStateV2','EditedCaseActionsStateV2').replace('    head_event_id: ExactId','    head_event_id: ExactId\n    head_ref: EventRefV2',1)
state=state.replace('                    raise ValueError("A source task cannot retarget its application")','''                    if (not isinstance(own_application, ContextApplicationRecordV2)
                        or own_application.context_ref is None or task.binding_ref is None
                        or own_application.context_ref.revision <= task.binding_ref.revision):
                        raise ValueError("A mismatched retained binding needs a later own context change")''',1)
state=state.replace('        unique([item.id for item in self.applications])','''        if self.head_ref.event_id != self.head_event_id or self.head_ref.revision != self.revision:
            raise ValueError("The explicit own mutation head agrees with the current header")
        unique([item.id for item in self.applications])''',1)
t=t.replace('type CaseActionsState = CaseActionsStateV1 | CaseActionsStateV2',state+'type CaseActionsState = CaseActionsStateV1 | CaseActionsStateV2 | EditedCaseActionsStateV2',1)
delta='''class EditedAppliedDeltaV2(Base):
    applications: list[ApplicationRecord] = Field(max_length=20)
    document_tasks: list[DocumentTaskV1] = Field(max_length=50)
    active_preparation: ActivePreparationSelectionV1 | None
    corrected_declaration: EventRefV1 | None = None
    previous_binding_digest: Digest | None = None
    declaration: DeclaredSubmissionV1 | DeclaredWithdrawalV1 | None = None
    removed_application: ApplicationRecord | None
    removed_document_task: DocumentTaskV1 | None


'''
receipt=t[t.index('class ActionWriteReceiptV2(Base):'):t.index('type ActionWriteReceipt =')].replace('ActionWriteReceiptV2','EditedActionWriteReceiptV2').replace('    kind: CommandKind','    kind: CommandKindV2',1).replace('    applied_delta: AppliedDeltaV2','    applied_delta: EditedAppliedDeltaV2',1)
# Old declarations/details still use unchanged V1 event roles; deletion is separate.
t=t.replace('type ActionWriteReceipt = ActionWriteReceiptV1 | ActionWriteReceiptV2',delta+receipt+'type ActionWriteReceipt = ActionWriteReceiptV1 | ActionWriteReceiptV2 | EditedActionWriteReceiptV2',1)
metadata='''class EventMetadataV2(Base):
    profile_id: ExactId
    event_id: ExactId
    revision: Revision
    kind: CommandKindV2
    accepted_at: UtcTimestamp
    affected_refs: EventAffectedRefsV1


type EventMetadata = EventMetadataV1 | EventMetadataV2


'''
t=t.replace('SourceReason = Literal[',metadata+'SourceReason = Literal[',1)
# Only additive read-projection reasons change; signed V1 class bodies remain intact.
t=t.replace('"report_refers_to_previous_binding",\n            "not_needed_is_not_a_waiver",','"report_refers_to_previous_binding",\n            "not_needed_is_not_a_waiver",\n            "application_context_changed",',1)
start=t.index('def source_target_ids(');end=t.index('\ndef state_references',start)
block=t[start:end].replace('if item.application_id is None and item.binding is not None','if item.binding is not None and (item.application_id is None or isinstance(state, EditedCaseActionsStateV2))');t=t[:start]+block+t[end:]
start=t.index('def state_references(');end=t.index('\ndef request_digest',start)
block=t[start:end].replace('EventRefV1, Literal["application", "document_task", "selector"]','EventRefV1 | EventRefV2, Literal["application", "document_task", "selector", "head"]')
block=block.replace('    for task in state.document_tasks:', '''        if isinstance(item, ContextApplicationRecordV2) and item.context_ref is not None:
            refs.append((item.context_ref, "application", item.id))
    for task in state.document_tasks:''',1).replace('    return refs','    if isinstance(state, EditedCaseActionsStateV2):\n        refs.append((state.head_ref, "head", None))\n    return refs',1)
t=t[:start]+block+t[end:]
t=t.replace('def delta_affected(delta: AppliedDeltaV1 | AppliedDeltaV2)', 'def delta_affected(delta: AppliedDeltaV1 | AppliedDeltaV2 | EditedAppliedDeltaV2)').replace('application_ids=[item.id for item in delta.applications],', '''application_ids=[item.id for item in delta.applications] + (
            [delta.removed_application.id] if isinstance(delta, EditedAppliedDeltaV2)
            and delta.removed_application is not None else []
        ),''',1).replace('document_task_ids=[item.id for item in delta.document_tasks],','''document_task_ids=[item.id for item in delta.document_tasks] + (
            [delta.removed_document_task.id] if isinstance(delta, EditedAppliedDeltaV2)
            and delta.removed_document_task is not None else []
        ),''',1)
t=t.replace('''    event = EventRefV1(event_id=receipt.event_id, revision=receipt.revision, kind=receipt.kind)
    if receipt.affected_refs''','''    if isinstance(request, RemovePersonalActionV2):
        validate_removal_delta(receipt)
        return
    event = EventRefV1(event_id=receipt.event_id, revision=receipt.revision, kind=request.kind)
    if isinstance(delta, EditedAppliedDeltaV2) and (delta.removed_application is not None or delta.removed_document_task is not None):
        raise ValueError("Only removal carries a removed snapshot")
    if receipt.affected_refs''',1)
t=t.replace('    if request.kind != "correct_declaration" and delta.corrected_declaration is not None:', '''    if isinstance(request, SetDocumentMetadataV2 | SetApplicationContextV2):
        records = delta.document_tasks if isinstance(request, SetDocumentMetadataV2) else delta.applications
        others = delta.applications if isinstance(request, SetDocumentMetadataV2) else delta.document_tasks
        if len(records) != 1 or others or delta.active_preparation is not None or records[0].id != request.target.id:
            raise ValueError("Metadata changes only its exact own record")
        if isinstance(request, SetDocumentMetadataV2):
            task = delta.document_tasks[0]
            if task.personal != request.personal or task.application_id != request.application_id:
                raise ValueError("Document metadata retains every exact entered field")
        else:
            app = delta.applications[0]
            if (not isinstance(app, ContextApplicationRecordV2) or app.target != request.application_target
                or app.label != request.label or app.details != request.details):
                raise ValueError("Context retains its exact reviewed input")
    if request.kind != "correct_declaration" and delta.corrected_declaration is not None:''',1)
helper='''def validate_removal_delta(receipt: ActionWriteReceipt) -> None:
    request, delta = receipt.request, receipt.applied_delta
    if not isinstance(request, RemovePersonalActionV2) or not isinstance(delta, EditedAppliedDeltaV2):
        raise ValueError("Removal requires an explicit V2 mutation delta")
    if (delta.applications or delta.document_tasks or delta.active_preparation is not None
        or delta.corrected_declaration is not None or delta.previous_binding_digest is not None
        or delta.declaration is not None or receipt.affected_refs != delta_affected(delta)):
        raise ValueError("Removal mutates only the requested current record")
    removed = delta.removed_application if request.target.kind == "application" else delta.removed_document_task
    other = delta.removed_document_task if request.target.kind == "application" else delta.removed_application
    if (removed is None or other is not None or removed.id != request.target.id
        or removed.profile_id != receipt.profile_id or removed.latest_ref.revision > receipt.expected_revision):
        raise ValueError("Removed snapshots retain their exact own pre-mutation record")


'''
t=t.replace('PRIVATE_SEGMENTS = frozenset(',helper+'PRIVATE_SEGMENTS = frozenset(',1)
save(p,t)
print('Closed schema companion proposal prepared; domain/routes/migration/tests not yet prepared or applied.')
