from pathlib import Path
root=Path(__file__).resolve().parent;pre=root/'applications4c-preimages';out=root/'applications4c-proposal'
def get(p):return (pre/p).read_text()
def save(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='backend/app/domain/admissions_actions.py';t=get(p)
t=t.replace('    "invalid_link":', '    "linked_documents": (422, "Detach or remove linked document tasks before removing this personal application."),\n    "declared_context_locked": (422, "A declared submission or withdrawal retains its target. Create a separate application, or explicitly correct the declaration first."),\n    "invalid_link":',1)
marker='def actor_reference('
helper='''def validate_event_metadata(value: object) -> s.EventMetadata:
    try:
        s.finite_wire(value)
        raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return TypeAdapter(s.EventMetadata).validate_python(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("saved_unreadable") from None


def reference_limit(state: s.CaseActionsState) -> int:
    return 1682 if isinstance(state, s.EditedCaseActionsStateV2) else 1662


'''
t=t.replace(marker,helper+marker,1)
t=t.replace('''    if isinstance(value, s.ManualApplicationRecordV2):''','''    if isinstance(value, s.ContextApplicationRecordV2):
        return _replace(s.ContextApplicationRecordV2, value, **changes)
    if isinstance(value, s.ManualApplicationRecordV2):''',1)
t=t.replace('''    event = s.EventRefV1(event_id=context.event_id, revision=revision + 1, kind=request.kind)''','''    event = s.EventRefV1(event_id=context.event_id, revision=revision + 1, kind=request.kind) if not isinstance(request, s.RemovePersonalActionV2) else None
    head_ref = s.EventRefV2(event_id=context.event_id, revision=revision + 1, kind=request.kind)
    removed_application: s.ApplicationRecord | None = None
    removed_task: s.DocumentTaskV1 | None = None''',1)
# Handle removal without weakening original event roles.
t=t.replace('''    if isinstance(request, s.CreateApplicationV1 | s.CreateManualApplicationV2):''','''    if isinstance(request, s.RemovePersonalActionV2):
        if request.target.kind == "application":
            removed_application = application(request.target.id)
            if any(item.application_id == request.target.id for item in tasks):
                raise ActionError("linked_documents")
            applications = [item for item in applications if item.id != request.target.id]
        else:
            removed_task = task(request.target.id)
            tasks = [item for item in tasks if item.id != request.target.id]
    elif isinstance(request, s.CreateApplicationV1 | s.CreateManualApplicationV2):''',1)
start=t.index('    elif isinstance(request, s.SetPersonalDetailsV1):',t.index('def apply_action'))
commands='''    elif isinstance(request, s.SetDocumentMetadataV2):
        current_task = task(request.target.id)
        if request.application_id is not None:
            application(request.application_id)
        if any(item not in task_by_id for item in request.personal.depends_on_task_ids):
            raise ActionError("record_not_found")
        changed_tasks = [_replace(s.DocumentTaskV1, current_task, personal=request.personal,
            application_id=request.application_id, latest_ref=event)]
    elif isinstance(request, s.SetApplicationContextV2):
        current_app = application(request.target.id)
        if isinstance(request.application_target, s.ApplicationTargetV1):
            target = _selected(context.profile_id, request.application_target.result_id, context.target)
            if request.application_target.award_id is not None:
                if not target.research_access:
                    raise ActionError("source_locked")
                if request.application_target.award_id not in target.award_ids:
                    raise ActionError("record_not_found")
        changed_context = current_app.target != request.application_target
        if changed_context and current_app.status in {"submitted_declared", "withdrawn_declared"}:
            raise ActionError("declared_context_locked")
        changed_apps = [s.ContextApplicationRecordV2.model_validate({
            **current_app.model_dump(mode="python"),
            "target": request.application_target, "label": request.label, "details": request.details,
            "latest_ref": event, "context_ref": event if changed_context else (
                current_app.context_ref if isinstance(current_app, s.ContextApplicationRecordV2) else None
            ),
        })]
'''
t=t[:start]+commands+t[start:]
# Exactly one explicit head represents a removal; old request/ref bodies stay unchanged.
t=t.replace('''        "head_event_id": event.event_id,''','''        "head_event_id": head_ref.event_id,''',1)
t=t.replace('''    v2 = isinstance(old, s.CaseActionsStateV2) or isinstance(request, s.CreateManualApplicationV2)''','''    edited = isinstance(old, s.EditedCaseActionsStateV2) or isinstance(request, s.SetDocumentMetadataV2 | s.SetApplicationContextV2 | s.RemovePersonalActionV2)
    v2 = edited or isinstance(old, s.CaseActionsStateV2) or isinstance(request, s.CreateManualApplicationV2)''',1)
t=t.replace('''    state = (
        validate_model(s.CaseActionsStateV2, state_wire)''','''    if edited:
        state_wire["head_ref"] = head_ref
    state = (
        validate_model(s.EditedCaseActionsStateV2, state_wire) if edited else
        validate_model(s.CaseActionsStateV2, state_wire)''',1)
t=t.replace('''    delta = (
        validate_model(s.AppliedDeltaV2, delta_wire)''','''    if edited:
        delta_wire["removed_application"] = removed_application
        delta_wire["removed_document_task"] = removed_task
    delta = (
        validate_model(s.EditedAppliedDeltaV2, delta_wire) if edited else
        validate_model(s.AppliedDeltaV2, delta_wire)''',1)
t=t.replace('''        "event_id": event.event_id,''','''        "event_id": head_ref.event_id,''',1)
t=t.replace('if len(ids) > 1662:', 'if len(ids) > reference_limit(current):',1)
t=t.replace('metadata: list[s.EventMetadataV1]', 'metadata: list[s.EventMetadata]')
t=t.replace('observed = [validate_model(s.EventMetadataV1, item, "saved_unreadable") for item in metadata]', 'observed = [validate_event_metadata(item) for item in metadata]',1)
t=t.replace('or len(by_id) > 1662', 'or len(by_id) > reference_limit(current)',1)
t=t.replace('head_meta = s.EventMetadataV1(', 'head_meta = s.EventMetadataV2(',1)
# Compare metadata models by canonical values, not Python model classes.
t=t.replace('if head.event_id in by_id and by_id[head.event_id] != head_meta:', 'if head.event_id in by_id and by_id[head.event_id].model_dump(mode="python") != head_meta.model_dump(mode="python"):',1)
t=t.replace('''    return current


def validate_complete_export''','''    if isinstance(head.applied_delta, s.EditedAppliedDeltaV2):
        removed_app = head.applied_delta.removed_application
        removed_task = head.applied_delta.removed_document_task
        if (removed_app is not None and removed_app.id in current_apps) or (removed_task is not None and removed_task.id in current_tasks):
            raise ActionError("saved_unreadable")
    return current


def validate_complete_export''',1)
t=t.replace('''        s.EventMetadataV1(
            profile_id=item.profile_id,''','''        s.EventMetadataV2(
            profile_id=item.profile_id,''',1)
# Optional supplied aggregate only. No I/O and no rewritten report.
start=t.index('def report_review_reasons(');end=t.index('\ndef _raw_checklist',start)
review='''def report_review_reasons(
    task: object, applications: list[s.ApplicationRecord] | None = None,
) -> list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver", "application_context_changed"]]:
    value = validate_model(s.DocumentTaskV1, task, "saved_unreadable")
    reasons: list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver", "application_context_changed"]] = []
    binding = value.binding.binding_digest if value.binding is not None else None
    if value.report.origin != "unreported" and value.report.binding_digest_at_report != binding:
        reasons.append("report_refers_to_previous_binding")
    if value.report.state == "not_needed_reported":
        reasons.append("not_needed_is_not_a_waiver")
    app = next((item for item in applications or [] if item.id == value.application_id), None)
    if isinstance(app, s.ContextApplicationRecordV2) and app.context_ref is not None:
        context_revision = app.context_ref.revision
        binding_review = value.binding is not None and (
            value.binding.result_id != app.target.result_id or value.binding.award_id != app.target.award_id
            or value.binding.purpose not in {app.target.purpose, "both"}
            or value.binding_ref is None or value.binding_ref.revision <= context_revision
        )
        report_review = value.report.origin != "unreported" and (
            value.report.event_ref is None or value.report.event_ref.revision <= context_revision
        )
        if binding_review or report_review:
            reasons.append("application_context_changed")
    return reasons

'''
t=t[:start]+review+t[end:]
t=t.replace('reasons = report_review_reasons(task)', 'reasons = report_review_reasons(task, state.applications if state is not None else None)')
t=t.replace('or report_review_reasons(task):','or report_review_reasons(task, state.applications):')
# The dependency reason literals in the local planner need the additive read reason.
t=t.replace('"not_needed_is_not_a_waiver",\n        ]', '"not_needed_is_not_a_waiver",\n            "application_context_changed",\n        ]')
save(p,t)
p='backend/app/api/routes_admissions_actions.py';t=get(p).replace('reasons: list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver"]]','reasons: list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver", "application_context_changed"]]',1)
t=t.replace('metadata: list[s.EventMetadataV1]','metadata: list[s.EventMetadata]')
t=t.replace('''d.validate_model(
                    s.EventMetadataV1,''','''d.validate_event_metadata(''',1)
# The metadata parser has no code positional arg.
start=t.index('metadata.append(');end=t.index('    current = d.validate_current_snapshot',start)
block=t[start:end].replace('                    "saved_unreadable",\n','');t=t[:start]+block+t[end:]
t=t.replace('request: s.CreateApplicationV1,\n) -> d.TargetObservationV1:', 'request: s.CreateApplicationV1 | s.SetApplicationContextV2,\n) -> d.TargetObservationV1:',1)
start=t.index('def _application_target(');end=t.index('\ndef _legacy_observation',start)
block=t[start:end];block=block.replace('    target = _selected_target(', '''    selected_target = request.target if isinstance(request, s.CreateApplicationV1) else request.application_target
    if not isinstance(selected_target, s.ApplicationTargetV1):
        raise d.ActionError("input_invalid")
    target = _selected_target(''',1).replace('request.target.result_id','selected_target.result_id').replace('request.target.award_id','selected_target.award_id');t=t[:start]+block+t[end:]
start=t.index('def _write_source_ids(');end=t.index('\ndef _write_context',start)
block=t[start:end].replace('    if isinstance(request, s.CreateApplicationV1):','''    if isinstance(request, s.SetApplicationContextV2):
        target = request.application_target
        return ([target.result_id], target.award_id is not None) if isinstance(target, s.ApplicationTargetV1) else ([], False)
    if isinstance(request, s.CreateApplicationV1):''',1);t=t[:start]+block+t[end:]
t=t.replace('''    if isinstance(request, s.CreateApplicationV1):
        target = _application_target(session, profile_id, principal, request)''','''    if isinstance(request, s.CreateApplicationV1) or (isinstance(request, s.SetApplicationContextV2) and isinstance(request.application_target, s.ApplicationTargetV1)):
        target = _application_target(session, profile_id, principal, request)''',1)
t=t.replace('d.report_review_reasons(task)', 'd.report_review_reasons(task, current.state.applications)')
save(p,t)
print('Domain/API companion proposals prepared; no source applied. Static narrowing and native controls still pending.')
