"""Pure closed G3 transitions and supplied-component projections.

No ownership query, clock, ID allocation, file, allocator or network operation lives
here. An integrating caller must establish fresh native ownership and access and
must validate/persist current plus one event atomically before delivering an ACK.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from itertools import pairwise
from typing import Literal, TypeVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, TypeAdapter, model_validator

from app.schemas import admissions_actions as s
from app.schemas.preparation_graph import PreparationGraph

ERRORS: dict[str, tuple[int, str]] = {
    "record_not_found": (404, "Action record not found."),
    "input_invalid": (422, "Check the action request fields."),
    "target_not_selected": (422, "The target is not a currently selected result."),
    "invalid_transition": (
        422,
        "This action requires a reviewed declaration or correction.",
    ),
    "limit_exceeded": (422, "The case action limit would be exceeded."),
    "invalid_link": (422, "This link form is not allowed for an action link."),
    "plan_unavailable": (422, "Select an existing saved preparation plan."),
    "source_locked": (403, "Current source details are unavailable for a new binding."),
    "revision_conflict": (
        409,
        "The case actions changed. Reload and review before saving.",
    ),
    "uuid_conflict": (
        409,
        "This request identifier already represents a different action.",
    ),
    "source_preview_stale": (
        409,
        "The source binding changed. Review a fresh source preview.",
    ),
    "plan_head_changed": (
        409,
        "The saved preparation plan changed. Review its current accepted head.",
    ),
    "legacy_import_changed": (
        409,
        "The captured legacy import inputs changed. Review the import again.",
    ),
    "saved_unreadable": (503, "Saved case actions could not be read safely."),
    "source_unreadable": (503, "The current source binding could not be read safely."),
    "plan_unreadable": (503, "The selected saved plan could not be read safely."),
    "write_unconfirmed": (
        503,
        "The action could not be confirmed. Keep the original request and retry.",
    ),
    "write_session_unavailable": (503, "The action requires a clean request session."),
}


class ActionError(Exception):
    """Safe finite detail; never contains an input value or exception repr."""

    def __init__(self, code: str) -> None:
        self.status, message = ERRORS[code]
        self.detail = {"code": f"admissions_actions_{code}", "message": message}
        super().__init__(message)


M = TypeVar("M", bound=BaseModel)
CHECKLIST_LOCATIONS: tuple[s.ChecklistLocation, ...] = (
    "admission_documents",
    "scholarship_documents",
    "applicant_actions",
    "school_actions",
    "recommender_actions",
    "certification_actions",
)


def validate_model(cls: type[M], value: object, code: str = "input_invalid") -> M:
    try:
        # Even model_construct/model_copy values are raw-checked and revalidated.
        s.finite_wire(value)
        raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return cls.model_validate(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError(code) from None


def validate_request(value: object) -> s.ActionRequestV1:
    try:
        s.finite_wire(value)
        raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return TypeAdapter(s.ActionRequestV1).validate_python(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("input_invalid") from None


def actor_reference(user_id: str, organization_id: str, *, local_development: bool) -> s.ActorRefV1:
    """Exact full IDs, no names/email/FK and no truncated-prefix identity."""
    try:
        user = TypeAdapter(s.ExactId).validate_python(user_id)
        organization = TypeAdapter(s.ExactId).validate_python(organization_id)
        if type(local_development) is not bool:
            raise ValueError("Use an explicit actor origin")
        digest = hashlib.sha256(
            s.canonical_bytes(
                {
                    "schema_version": "g3-actor-reference-v1",
                    "user_id": user,
                    "organization_id": organization,
                }
            )
        ).hexdigest()
        return s.ActorRefV1(
            actor_kind="local_development" if local_development else "authenticated_principal",
            actor_ref_digest=digest,
        )
    except (ValueError, TypeError):
        raise ActionError("input_invalid") from None


class TargetObservationV1(s.Base):
    """Caller-observed owned metadata, not a client grant or eligibility verdict."""

    profile_id: s.ExactId
    result_id: s.ExactId
    state: Literal["selected", "decision_changed", "unavailable"]
    decision: Literal["approved", "maybe", "other", "unknown"]
    research_access: bool
    award_ids: list[s.ReferenceId] = Field(default_factory=list)


class SourceObservationV1(s.Base):
    target: TargetObservationV1
    state: Literal["readable", "unreadable", "locked"]
    preview_digest: s.Digest | None
    selection: s.BindingSelectionV1 | None


class PlanObservationV1(s.Base):
    profile_id: s.ExactId
    state: Literal["readable", "absent", "malformed_legacy", "unreadable"]
    head: s.NativeHeadV1 | None


class LegacyMarkObservationV1(s.Base):
    profile_id: s.ExactId
    snapshot_digest: s.Digest
    mappings: list[s.LegacyImportMappingV1] = Field(min_length=1, max_length=50)


class ActionContextV1(s.Base):
    """Trusted inputs supplied by the future fenced caller, never inferred here."""

    profile_id: s.ExactId
    event_id: s.ExactId
    accepted_at: s.UtcTimestamp
    actor: s.ActorRefV1
    new_application_id: s.ExactId | None = None
    new_task_id: s.ExactId | None = None
    target: TargetObservationV1 | None = None
    source: SourceObservationV1 | None = None
    plan: PlanObservationV1 | None = None
    prior_declaration_receipt: s.ActionWriteReceiptV1 | None = None
    legacy: LegacyMarkObservationV1 | None = None


class ActionTransitionV1(s.Base):
    state: s.CaseActionsStateV1
    receipt: s.ActionWriteReceiptV1


def _replace(cls: type[M], value: M, **changes: object) -> M:
    return validate_model(cls, {**value.model_dump(mode="python"), **changes}, "saved_unreadable")


def _selected(
    profile_id: str, result_id: str, target: TargetObservationV1 | None
) -> TargetObservationV1:
    if (
        target is None
        or target.profile_id != profile_id
        or target.result_id != result_id
        or target.state == "unavailable"
    ):
        raise ActionError("record_not_found")
    if target.state != "selected" or target.decision not in {"approved", "maybe"}:
        raise ActionError("target_not_selected")
    return target


def _source(
    context: ActionContextV1, request: s.BindSourceTaskV1 | s.RebindSourceTaskV1
) -> s.ChecklistBindingReceiptV1:
    observation = context.source
    if observation is None:
        raise ActionError("source_unreadable")
    target = _selected(context.profile_id, request.source.result_id, observation.target)
    if not target.research_access or observation.state == "locked":
        raise ActionError("source_locked")
    if (
        observation.state != "readable"
        or observation.selection is None
        or observation.preview_digest is None
    ):
        raise ActionError("source_unreadable")
    if (
        request.source != observation.selection
        or request.source_preview_digest != observation.preview_digest
    ):
        raise ActionError("source_preview_stale")
    if request.source.award_id is not None and request.source.award_id not in target.award_ids:
        raise ActionError("record_not_found")
    wire = {
        **request.source.model_dump(mode="python"),
        "profile_id": context.profile_id,
        "accepted_at": context.accepted_at,
    }
    wire["binding_digest"] = s.reference_digest("g3-checklist-binding-v1", wire)
    return validate_model(s.ChecklistBindingReceiptV1, wire, "source_unreadable")


def _unreported() -> s.DocumentSelfReportV1:
    return s.DocumentSelfReportV1(
        state="not_started",
        entered_at=None,
        accepted_at=None,
        actor=None,
        event_ref=None,
        binding_digest_at_report=None,
        origin="unreported",
    )


def _report(
    task: s.DocumentTaskV1,
    event: s.EventRefV1,
    context: ActionContextV1,
    state: s.ReportState,
    entered_at: s.DeclaredMomentV1 | None,
    *,
    imported: bool = False,
) -> s.DocumentSelfReportV1:
    return s.DocumentSelfReportV1(
        state=state,
        entered_at=entered_at,
        accepted_at=context.accepted_at,
        actor=context.actor,
        event_ref=event,
        binding_digest_at_report=task.binding.binding_digest if task.binding is not None else None,
        origin="explicit_browser_mark_import" if imported else "applicant_report",
    )


def apply_action(
    previous: object | None, intent: object, trusted_context: object
) -> ActionTransitionV1:
    """Apply one reviewed closed command, with allocated IDs/time supplied explicitly."""
    request = validate_request(intent)
    prior_receipt: s.ActionWriteReceiptV1 | None = None
    if isinstance(request, s.CorrectDeclarationV1):
        # A supplied saved receipt is checked before ordinary context validation,
        # including raw forged instance values; corruption is a safe saved error.
        prior_raw: object = None
        if isinstance(trusted_context, BaseModel):
            prior_raw = trusted_context.__dict__.get("prior_declaration_receipt")
        elif isinstance(trusted_context, dict):
            prior_raw = trusted_context.get("prior_declaration_receipt")
        if prior_raw is not None:
            prior_receipt = validate_model(s.ActionWriteReceiptV1, prior_raw, "saved_unreadable")
    context = validate_model(ActionContextV1, trusted_context)
    old = (
        validate_model(s.CaseActionsStateV1, previous, "saved_unreadable")
        if previous is not None
        else None
    )
    if old is not None and old.profile_id != context.profile_id:
        raise ActionError("record_not_found")
    revision = old.revision if old is not None else 0
    if request.expected_revision != revision:
        raise ActionError("revision_conflict")
    if old is not None and any(
        ref.event_id == context.event_id for ref, _, _ in s.state_references(old)
    ):
        raise ActionError("saved_unreadable")
    applications = list(old.applications) if old is not None else []
    tasks = list(old.document_tasks) if old is not None else []
    selector = old.active_preparation if old is not None else None
    app_by_id = {item.id: item for item in applications}
    task_by_id = {item.id: item for item in tasks}
    event = s.EventRefV1(event_id=context.event_id, revision=revision + 1, kind=request.kind)
    changed_apps: list[s.ApplicationRecordV1] = []
    changed_tasks: list[s.DocumentTaskV1] = []
    changed_selector: s.ActivePreparationSelectionV1 | None = None
    declaration: s.DeclaredSubmissionV1 | s.DeclaredWithdrawalV1 | None = None
    corrected: s.EventRefV1 | None = None
    old_binding: str | None = None

    def application(record_id: str) -> s.ApplicationRecordV1:
        if record_id not in app_by_id:
            raise ActionError("record_not_found")
        return app_by_id[record_id]

    def task(record_id: str) -> s.DocumentTaskV1:
        if record_id not in task_by_id:
            raise ActionError("record_not_found")
        return task_by_id[record_id]

    def submission_refs(value: s.SubmissionInputV1) -> None:
        for record_id in value.document_task_ids:
            task(record_id)  # Mention is own reference only, never a task mutation.

    if isinstance(request, s.CreateApplicationV1):
        target = _selected(context.profile_id, request.target.result_id, context.target)
        if request.target.award_id is not None:
            if not target.research_access:
                raise ActionError("source_locked")
            if request.target.award_id not in target.award_ids:
                raise ActionError("record_not_found")
        if len(applications) >= 20:
            raise ActionError("limit_exceeded")
        if context.new_application_id is None or context.new_application_id in app_by_id:
            raise ActionError("input_invalid")
        changed_apps = [
            s.ApplicationRecordV1(
                id=context.new_application_id,
                profile_id=context.profile_id,
                target=request.target,
                label=request.label,
                details=request.details,
                status="planning",
                created_ref=event,
                latest_ref=event,
                status_ref=None,
            )
        ]
    elif isinstance(request, s.CreatePersonalTaskV1 | s.BindSourceTaskV1):
        if len(tasks) >= 400:
            raise ActionError("limit_exceeded")
        if request.application_id is not None:
            application(request.application_id)
        if context.new_task_id is None or context.new_task_id in task_by_id:
            raise ActionError("input_invalid")
        if any(record_id not in task_by_id for record_id in request.personal.depends_on_task_ids):
            raise ActionError("record_not_found")
        binding = _source(context, request) if isinstance(request, s.BindSourceTaskV1) else None
        changed_tasks = [
            s.DocumentTaskV1(
                id=context.new_task_id,
                profile_id=context.profile_id,
                application_id=request.application_id,
                origin="source_reference" if binding is not None else "applicant_entered",
                personal=request.personal,
                binding=binding,
                report=_unreported(),
                created_ref=event,
                latest_ref=event,
                binding_ref=event if binding is not None else None,
            )
        ]
    elif isinstance(request, s.RebindSourceTaskV1):
        current_task = task(request.task_id)
        old_binding = (
            current_task.binding.binding_digest if current_task.binding is not None else None
        )
        if old_binding != request.expected_binding_digest:
            raise ActionError("source_preview_stale")
        binding = _source(context, request)
        # Preserve original self-report and its accepted old binding, never transfer.
        changed_tasks = [
            _replace(
                s.DocumentTaskV1,
                current_task,
                binding=binding,
                binding_ref=event,
                origin="source_reference",
                latest_ref=event,
            )
        ]
    elif isinstance(request, s.SetDocumentSelfReportV1):
        current_task = task(request.task_id)
        changed_tasks = [
            _replace(
                s.DocumentTaskV1,
                current_task,
                report=_report(
                    current_task,
                    event,
                    context,
                    request.report.state,
                    request.report.entered_at,
                ),
                latest_ref=event,
            )
        ]
    elif isinstance(request, s.SetPersonalDetailsV1):
        if request.target.kind == "application":
            changed_apps = [
                _replace(
                    s.ApplicationRecordV1,
                    application(request.target.id),
                    details=request.details,
                    latest_ref=event,
                )
            ]
        else:
            current_task = task(request.target.id)
            personal = _replace(
                s.PersonalTaskInputV1, current_task.personal, details=request.details
            )
            changed_tasks = [
                _replace(s.DocumentTaskV1, current_task, personal=personal, latest_ref=event)
            ]
    elif isinstance(request, s.SetPlanningStatusV1):
        current_app = application(request.application_id)
        if current_app.status in {"submitted_declared", "withdrawn_declared"}:
            raise ActionError("invalid_transition")
        changed_apps = [
            _replace(
                s.ApplicationRecordV1,
                current_app,
                status=request.status,
                status_ref=event,
                latest_ref=event,
            )
        ]
    elif isinstance(
        request, s.DeclareSubmissionV1 | s.DeclareWithdrawalV1 | s.CorrectDeclarationV1
    ):
        current_app = application(request.application_id)
        replacement: s.CorrectionValue
        if isinstance(request, s.CorrectDeclarationV1):
            prior = prior_receipt
            if (
                prior is None
                or prior.profile_id != context.profile_id
                or prior.event_id != request.prior_declaration.event_id
                or prior.revision != request.prior_declaration.revision
                or prior.kind != request.prior_declaration.kind
                or prior.revision > revision
            ):
                raise ActionError("record_not_found")
            # Full receipt validation established one exact application mutation
            # even when an earlier correction explicitly returned to planning.
            if (
                prior.affected_refs.application_ids != [current_app.id]
                or prior.applied_delta.applications[0].id != current_app.id
            ):
                raise ActionError("invalid_transition")
            corrected = request.prior_declaration
            replacement = request.replacement
        else:
            if isinstance(request, s.DeclareSubmissionV1) and current_app.status in {
                "submitted_declared",
                "withdrawn_declared",
            }:
                raise ActionError("invalid_transition")
            if (
                isinstance(request, s.DeclareWithdrawalV1)
                and current_app.status == "withdrawn_declared"
            ):
                raise ActionError("invalid_transition")
            replacement = (
                s.CorrectedSubmissionV1(submission=request.submission)
                if isinstance(request, s.DeclareSubmissionV1)
                else s.CorrectedWithdrawalV1(withdrawal=request.withdrawal)
            )
        if isinstance(replacement, s.CorrectedSubmissionV1):
            submission_refs(replacement.submission)
            declaration = s.DeclaredSubmissionV1(
                application_id=current_app.id,
                event_ref=event,
                entered=replacement.submission,
                accepted_at=context.accepted_at,
                actor=context.actor,
            )
            status: s.ApplicationStatus = "submitted_declared"
        elif isinstance(replacement, s.CorrectedWithdrawalV1):
            declaration = s.DeclaredWithdrawalV1(
                application_id=current_app.id,
                event_ref=event,
                entered=replacement.withdrawal,
                accepted_at=context.accepted_at,
                actor=context.actor,
            )
            status = "withdrawn_declared"
        else:
            status = replacement.status
        changed_apps = [
            _replace(
                s.ApplicationRecordV1,
                current_app,
                status=status,
                status_ref=event,
                latest_ref=event,
            )
        ]
    elif isinstance(request, s.ImportLegacyMarksV1):
        observed = context.legacy
        if (
            observed is None
            or observed.profile_id != context.profile_id
            or observed.snapshot_digest != request.legacy_snapshot_digest
            or observed.mappings != request.mappings
        ):
            raise ActionError("legacy_import_changed")
        for mapping in request.mappings:
            current_task = task(mapping.task_id)
            current_binding = (
                current_task.binding.binding_digest if current_task.binding is not None else None
            )
            if current_binding != mapping.expected_binding_digest or (
                current_binding is not None and mapping.source_preview_digest is None
            ):
                raise ActionError("legacy_import_changed")
            changed_tasks.append(
                _replace(
                    s.DocumentTaskV1,
                    current_task,
                    report=_report(
                        current_task,
                        event,
                        context,
                        "prepared_reported",
                        request.entered_at,
                        imported=True,
                    ),
                    latest_ref=event,
                )
            )
    else:
        observed_plan = context.plan
        if observed_plan is None or observed_plan.profile_id != context.profile_id:
            raise ActionError("record_not_found")
        if observed_plan.state in {"absent", "malformed_legacy"}:
            raise ActionError("plan_unavailable")
        if observed_plan.state != "readable" or observed_plan.head is None:
            raise ActionError("plan_unreadable")
        if (
            request.observed_head.profile_id != context.profile_id
            or request.observed_head != observed_plan.head
        ):
            raise ActionError("plan_head_changed")
        changed_selector = s.ActivePreparationSelectionV1(
            origin=request.origin,
            policy=request.policy,
            observed_head=request.observed_head,
            event_ref=event,
        )
        selector = changed_selector

    for changed in changed_apps:
        applications = (
            [changed if item.id == changed.id else item for item in applications]
            if changed.id in app_by_id
            else [*applications, changed]
        )
    for changed_task in changed_tasks:
        tasks = (
            [changed_task if item.id == changed_task.id else item for item in tasks]
            if changed_task.id in task_by_id
            else [*tasks, changed_task]
        )
    prospective_ids = {item.target.result_id for item in applications}
    prospective_ids.update(
        item.binding.result_id
        for item in tasks
        if item.binding is not None and item.application_id is None
    )
    if len(prospective_ids) > 20:
        raise ActionError("limit_exceeded")
    state = validate_model(
        s.CaseActionsStateV1,
        {
            "profile_id": context.profile_id,
            "revision": revision + 1,
            "head_event_id": event.event_id,
            "applications": applications,
            "document_tasks": tasks,
            "active_preparation": selector,
        },
        "input_invalid",
    )
    delta = s.AppliedDeltaV1(
        applications=changed_apps,
        document_tasks=changed_tasks,
        active_preparation=changed_selector,
        corrected_declaration=corrected,
        previous_binding_digest=old_binding,
        declaration=declaration,
    )
    receipt_wire = {
        "event_id": event.event_id,
        "profile_id": context.profile_id,
        "kind": request.kind,
        "revision": revision + 1,
        "expected_revision": revision,
        "client_write_uuid": request.client_write_uuid,
        "request": request,
        "canonical_request_digest": s.request_digest(context.profile_id, request),
        "accepted_at": context.accepted_at,
        "actor": context.actor,
        "predecessor_event_id": old.head_event_id if old is not None else None,
        "before_state_digest": s.state_digest(old) if old is not None else None,
        "after_state_digest": s.state_digest(state),
        "applied_delta": delta,
        "affected_refs": s.delta_affected(delta),
        "schema_version": "admissions-actions-v1",
    }
    receipt_wire["receipt_digest"] = hashlib.sha256(
        s.canonical_bytes(
            {"schema_version": "g3-action-receipt-digest-v1", "receipt": receipt_wire}
        )
    ).hexdigest()
    receipt = validate_model(s.ActionWriteReceiptV1, receipt_wire, "saved_unreadable")
    return ActionTransitionV1(state=state, receipt=receipt)


def replay_receipt(profile_id: str, intent: object, original: object) -> s.ActionWriteReceiptV1:
    request = validate_request(intent)
    receipt = validate_model(s.ActionWriteReceiptV1, original, "saved_unreadable")
    if receipt.profile_id != profile_id:
        raise ActionError("record_not_found")
    if (
        receipt.client_write_uuid != request.client_write_uuid
        or receipt.canonical_request_digest != s.request_digest(profile_id, request)
    ):
        raise ActionError("uuid_conflict")
    return receipt  # Original actor/time/head; no new context or source read.


def metadata_batches(state: object) -> list[list[str]]:
    current = validate_model(s.CaseActionsStateV1, state, "saved_unreadable")
    ids = list(
        dict.fromkeys(
            [
                current.head_event_id,
                *(ref.event_id for ref, _, _ in s.state_references(current)),
            ]
        )
    )
    if len(ids) > 1662:
        raise ActionError("saved_unreadable")
    return [ids[index : index + 200] for index in range(0, len(ids), 200)]


def validate_current_snapshot(
    state: object,
    head_receipt: object,
    *,
    profile_id: str,
    row_digest: str,
    row_updated_at: datetime,
    latest_revision: int,
    metadata: list[s.EventMetadataV1],
) -> s.CaseActionsStateV1:
    current = validate_model(s.CaseActionsStateV1, state, "saved_unreadable")
    head = validate_model(s.ActionWriteReceiptV1, head_receipt, "saved_unreadable")
    observed = [validate_model(s.EventMetadataV1, item, "saved_unreadable") for item in metadata]
    if (
        current.profile_id != profile_id
        or head.profile_id != profile_id
        or head.event_id != current.head_event_id
        or head.revision != current.revision
        or latest_revision != current.revision
        or row_digest != s.state_digest(current)
        or head.after_state_digest != row_digest
        or row_updated_at != head.accepted_at
    ):
        raise ActionError("saved_unreadable")
    by_id = {item.event_id: item for item in observed}
    if (
        len(by_id) != len(observed)
        or len(by_id) > 1662
        or len({item.revision for item in observed}) != len(observed)
        or any(item.profile_id != profile_id for item in observed)
    ):
        raise ActionError("saved_unreadable")
    head_meta = s.EventMetadataV1(
        profile_id=profile_id,
        event_id=head.event_id,
        revision=head.revision,
        kind=head.kind,
        accepted_at=head.accepted_at,
        affected_refs=head.affected_refs,
    )
    if head.event_id in by_id and by_id[head.event_id] != head_meta:
        raise ActionError("saved_unreadable")
    by_id[head.event_id] = head_meta
    for ref, association, record_id in s.state_references(current):
        row = by_id.get(ref.event_id)
        if (
            row is None
            or row.profile_id != profile_id
            or row.revision != ref.revision
            or row.kind != ref.kind
            or row.revision > head.revision
        ):
            raise ActionError("saved_unreadable")
        affected = row.affected_refs
        if (
            (association == "application" and record_id not in affected.application_ids)
            or (association == "document_task" and record_id not in affected.document_task_ids)
            or (association == "selector" and not affected.active_selector_changed)
        ):
            raise ActionError("saved_unreadable")
    current_apps = {item.id: item for item in current.applications}
    current_tasks = {item.id: item for item in current.document_tasks}
    if (
        any(current_apps.get(item.id) != item for item in head.applied_delta.applications)
        or any(current_tasks.get(item.id) != item for item in head.applied_delta.document_tasks)
        or (
            head.applied_delta.active_preparation is not None
            and current.active_preparation != head.applied_delta.active_preparation
        )
    ):
        raise ActionError("saved_unreadable")
    return current


def validate_complete_export(
    state: object | None, receipts: list[object], *, profile_id: str
) -> list[s.ActionWriteReceiptV1]:
    history = [
        validate_model(s.ActionWriteReceiptV1, item, "saved_unreadable") for item in receipts
    ]
    if state is None:
        if history:
            raise ActionError("saved_unreadable")
        return []
    current = validate_model(s.CaseActionsStateV1, state, "saved_unreadable")
    if (
        current.profile_id != profile_id
        or not history
        or [item.revision for item in history] != list(range(1, len(history) + 1))
        or any(item.profile_id != profile_id for item in history)
        or len({item.event_id for item in history}) != len(history)
        or len({item.client_write_uuid for item in history}) != len(history)
    ):
        raise ActionError("saved_unreadable")
    for previous, next_receipt in pairwise(history):
        if (
            next_receipt.predecessor_event_id != previous.event_id
            or next_receipt.before_state_digest != previous.after_state_digest
        ):
            raise ActionError("saved_unreadable")
    head = history[-1]
    if (
        head.revision != current.revision
        or head.event_id != current.head_event_id
        or head.after_state_digest != s.state_digest(current)
    ):
        raise ActionError("saved_unreadable")
    metadata = [
        s.EventMetadataV1(
            profile_id=item.profile_id,
            event_id=item.event_id,
            revision=item.revision,
            kind=item.kind,
            accepted_at=item.accepted_at,
            affected_refs=item.affected_refs,
        )
        for item in history
        if item.event_id in {event_id for batch in metadata_batches(current) for event_id in batch}
    ]
    validate_current_snapshot(
        current,
        head,
        profile_id=profile_id,
        row_digest=head.after_state_digest,
        row_updated_at=head.accepted_at,
        latest_revision=head.revision,
        metadata=metadata,
    )
    return history


def report_review_reasons(
    task: object,
) -> list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver"]]:
    value = validate_model(s.DocumentTaskV1, task, "saved_unreadable")
    reasons: list[Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver"]] = []
    binding = value.binding.binding_digest if value.binding is not None else None
    if value.report.origin != "unreported" and value.report.binding_digest_at_report != binding:
        reasons.append("report_refers_to_previous_binding")
    if value.report.state == "not_needed_reported":
        reasons.append("not_needed_is_not_a_waiver")
    return reasons


def _raw_checklist(value: object) -> s.RawDocumentChecklist:
    try:
        raw = s.finite_wire(value)
        checklist = s.RawDocumentChecklist.model_validate_json(s.canonical_bytes(raw), strict=True)
        s.finite_wire(checklist.model_dump(mode="python"))
        return checklist
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("source_unreadable") from None


def _graph(value: object | None, profile_id: str, result_id: str) -> PreparationGraph | None:
    if value is None:
        return None
    try:
        raw = s.finite_wire(value)
        graph = PreparationGraph.model_validate_json(s.canonical_bytes(raw), strict=True)
        s.finite_wire(graph.model_dump(mode="python"))
        if (
            s.finite_wire(graph) != raw
            or graph.profile_id != profile_id
            or result_id not in graph.selected_result_ids
        ):
            raise ValueError("Exact supplied projection required")
        return graph
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ActionError("source_unreadable") from None


def checklist_identity(checklist: object) -> tuple[str, str]:
    parsed = _raw_checklist(checklist)
    raw = parsed.model_dump(mode="python", exclude={"generated_at"})
    return s.reference_digest("g3-checklist-reference-v1", raw), s.reference_digest(
        "g3-procedure-reference-v1", parsed.ordered_steps
    )


def build_binding_selection(
    checklist: object,
    *,
    profile_id: str,
    result_id: str,
    selected_occurrences: list[tuple[s.ChecklistLocation, int]],
    purpose: Literal["admission", "scholarship", "both"],
    award_id: str | None,
    graph: object | None = None,
) -> s.BindingSelectionV1:
    """Hash exact native occurrences. An optional G1 ID is actual and unambiguous."""
    parsed = _raw_checklist(checklist)
    projection = _graph(graph, profile_id, result_id)
    if parsed.result_id != result_id:
        raise ActionError("source_unreadable")
    if not 1 <= len(selected_occurrences) <= 6 or len(
        {location for location, _ in selected_occurrences}
    ) != len(selected_occurrences):
        raise ActionError("input_invalid")
    selected: list[tuple[s.ChecklistLocation, int, s.RawDocumentItem]] = []
    all_occurrences: list[tuple[s.ChecklistLocation, int, s.RawDocumentItem]] = []
    for location in CHECKLIST_LOCATIONS:
        for index, item in enumerate(getattr(parsed, location)):
            all_occurrences.append((location, index, item))
    for location, index in selected_occurrences:
        if location not in CHECKLIST_LOCATIONS or type(index) is not int or index < 0:
            raise ActionError("input_invalid")
        items = getattr(parsed, location)
        if index >= len(items):
            raise ActionError("source_preview_stale")
        selected.append((location, index, items[index]))
    if [location for location, _, _ in selected] != [
        location
        for location in CHECKLIST_LOCATIONS
        if location in {where for where, _, _ in selected}
    ]:
        raise ActionError("input_invalid")
    if any(item.purpose.value != purpose for _, _, item in selected):
        raise ActionError("input_invalid")
    candidates = []
    ambiguous = False
    if projection is not None:
        for action in projection.document_actions:
            if action.result_id != result_id or len(action.source_locations) != len(
                action.original_items
            ):
                continue
            matches: list[tuple[s.ChecklistLocation, int]] = []
            unique_match = True
            for location, original in zip(
                action.source_locations, action.original_items, strict=True
            ):
                indices = [
                    index
                    for where, index, item in all_occurrences
                    if where == location and s.canonical_bytes(item) == s.canonical_bytes(original)
                ]
                if len(indices) != 1:
                    unique_match = False
                    if len(indices) > 1 and any(
                        where == location and index in indices for where, index, _ in selected
                    ):
                        ambiguous = True
                    break
                matches.append((location, indices[0]))
            if unique_match and matches == selected_occurrences:
                candidates.append(action)
    native = candidates[0] if len(candidates) == 1 else None
    if len(candidates) > 1:
        ambiguous = True
    manifests = (
        [item for item in projection.source_manifest if item.result_id == result_id]
        if projection is not None
        else []
    )
    manifest = manifests[0] if len(manifests) == 1 else None
    g1 = None
    if (
        projection is not None
        and native is not None
        and manifest is not None
        and manifest.result_snapshot_digest is not None
        and manifest.authoritative_evidence_digest is not None
    ):
        g1 = s.G1DocumentRefV1(
            action_id=native.id,
            source_fingerprint=projection.source_fingerprint,
            result_snapshot_digest=manifest.result_snapshot_digest,
            authoritative_evidence_digest=manifest.authoritative_evidence_digest,
            resolved_claim_ids=manifest.resolved_claim_ids,
        )
    claim_ids = list(
        dict.fromkeys(claim_id for _, _, item in selected for claim_id in item.claim_ids)
    )
    refs: list[s.RawOccurrenceRefV1] = []
    for location, index, item in selected:
        full = item.model_dump(mode="python")
        semantics = {
            key: value for key, value in full.items() if key not in {"claim_ids", "source_url"}
        }
        proof = {
            "original_claim_ids": item.claim_ids,
            "source_url": {"state": "absent"}
            if item.source_url is None
            else {"state": "present", "value": item.source_url},
            "manifest": manifest,
            "native_proofs": native.proofs if native is not None else [],
            "native_scope": native.scope if native is not None else None,
            "evidence_state": native.evidence_state if native is not None else "unknown",
            "unresolved_reasons": native.unresolved_reasons
            if native is not None
            else ["document_predicate_not_projected"],
            "missing_claim_ids": [
                key
                for key in item.claim_ids
                if native is None or key not in {proof.claim.id for proof in native.proofs}
            ],
        }
        refs.append(
            s.RawOccurrenceRefV1(
                result_id=result_id,
                location=location,
                index=index,
                item_digest=s.reference_digest("g3-item-reference-v1", full),
                item_semantics_digest=s.reference_digest("g3-item-semantics-v1", semantics),
                proof_reference_digest=s.reference_digest("g3-item-proof-reference-v1", proof),
            )
        )
    checklist_digest, procedure_digest = checklist_identity(parsed)
    return validate_model(
        s.BindingSelectionV1,
        {
            "result_id": result_id,
            "purpose": purpose,
            "award_id": award_id,
            "award_relation": "unknown",
            "checklist_digest": checklist_digest,
            "procedure_digest": procedure_digest,
            "occurrences": refs,
            "original_claim_ids": claim_ids,
            "g1_document": g1,
            "g1_relation": "exact_projection"
            if g1 is not None
            else "ambiguous_occurrence"
            if ambiguous
            else "document_predicate_not_projected",
        },
        "source_unreadable",
    )


def compare_binding(
    saved: object, current: object, *, evidence_reasons: list[s.SourceReason]
) -> list[s.SourceReason]:
    old = validate_model(s.ChecklistBindingReceiptV1, saved, "saved_unreadable")
    new = validate_model(s.BindingSelectionV1, current, "source_unreadable")
    if new.result_id != old.result_id or new.purpose != old.purpose or new.award_id != old.award_id:
        raise ActionError("source_unreadable")
    try:
        reasons = TypeAdapter(list[s.SourceReason]).validate_python(evidence_reasons, strict=True)
    except (ValueError, TypeError):
        raise ActionError("source_unreadable") from None
    same_occurrences = [(item.location, item.index) for item in old.occurrences] == [
        (item.location, item.index) for item in new.occurrences
    ]
    same_semantics = same_occurrences and [
        item.item_semantics_digest for item in old.occurrences
    ] == [item.item_semantics_digest for item in new.occurrences]
    same_proof = (
        same_occurrences
        and [item.proof_reference_digest for item in old.occurrences]
        == [item.proof_reference_digest for item in new.occurrences]
        and old.g1_document == new.g1_document
    )
    if not same_semantics:
        reasons.append("item_changed")
    elif not same_proof:
        reasons.append("proof_changed_item_same")
    if old.procedure_digest != new.procedure_digest:
        reasons.append("procedure_order_changed")
    if new.g1_relation != "exact_projection":
        reasons.append(
            "ambiguous_occurrence"
            if new.g1_relation == "ambiguous_occurrence"
            else "document_predicate_not_projected"
        )
    if new.award_id is not None or new.purpose != "admission":
        reasons.append("award_relation_unknown")
    return list(dict.fromkeys(reasons))


def safe_link_literal(raw: object) -> bool:
    return s.safe_link_literal(raw)


def project_action_link(
    raw: object,
    *,
    role: Literal[
        "programme_information",
        "requirements_information",
        "applicant_entered_external",
    ],
    provenance: Literal["current_source", "applicant_entered", "demo", "unknown"],
    authorized_current_source: bool = False,
) -> s.ActionLinkReadV1:
    if (
        (provenance == "current_source" and authorized_current_source is not True)
        or raw is None
        or provenance == "unknown"
    ):
        state: Literal["actionable_unverified", "blocked", "demo_text", "not_available"] = (
            "not_available"
        )
    elif provenance == "demo" or (type(raw) is str and raw.startswith("fixture://")):
        state = "demo_text"
    elif safe_link_literal(raw):
        state = "actionable_unverified"
    else:
        state = "blocked"
    reasons: dict[
        str,
        Literal[
            "informational_unverified",
            "link_form_unavailable",
            "demo_reference",
            "not_available",
        ],
    ] = {
        "not_available": "not_available",
        "demo_text": "demo_reference",
        "blocked": "link_form_unavailable",
        "actionable_unverified": "informational_unverified",
    }
    return s.ActionLinkReadV1(
        role=role,
        provenance=provenance,
        state=state,
        href=raw if state == "actionable_unverified" and isinstance(raw, str) else None,
        reason=reasons[state],
    )


class NativePresenceV1(s.Base):
    """Presence is supplied metadata, not truthiness of a parsed sidecar."""

    g3_readable: bool
    g2_current_present: bool | None
    g2_history_present: bool | None
    legacy_v2_marker_present: bool | None
    legacy_v1_row_present: bool | None


def choose_origin(
    selection: object | None, presence: object
) -> Literal["g2", "legacy_v2", "legacy_v1", "none", "unknown"]:
    observed = validate_model(NativePresenceV1, presence, "plan_unreadable")
    if not observed.g3_readable:
        return "unknown"
    if selection is not None:
        return validate_model(s.ActivePreparationSelectionV1, selection, "saved_unreadable").origin
    if observed.g2_current_present is True or observed.g2_history_present is True:
        return "g2"
    if observed.g2_current_present is None or observed.g2_history_present is None:
        return "unknown"
    if observed.legacy_v2_marker_present is True:
        return "legacy_v2"
    if observed.legacy_v2_marker_present is None:
        return "unknown"
    if observed.legacy_v1_row_present is True:
        return "legacy_v1"
    return "unknown" if observed.legacy_v1_row_present is None else "none"


class TodayComponentsV1(s.Base):
    profile_id: s.ExactId
    as_of: s.UtcTimestamp
    display_timezone: s.IanaZone
    action_state: Literal["readable", "absent", "unavailable"]
    actions: s.CaseActionsStateV1 | None
    action_observed_at: s.UtcTimestamp
    active_plan: s.ActivePreparationReadV1
    preparation_access: s.PreparationAccessReadV1
    source_statuses: list[s.SourceReadStatusV1] = Field(max_length=40)
    initial_component_token: s.Digest
    rechecked_component_token: s.Digest
    research_access_after_recheck: bool

    @model_validator(mode="after")
    def action_presence(self) -> TodayComponentsV1:
        if (self.action_state == "readable") != (self.actions is not None):
            raise ValueError("Only an actually readable aggregate supplies personal state")
        if self.action_state == "unavailable" and (
            self.active_plan.origin != "unknown"
            or self.active_plan.state != "unavailable"
            or self.active_plan.selection_source != "unavailable"
        ):
            raise ValueError("Unreadable G3 cannot authorize a backward default")
        return self


def project_today(components: object) -> s.TodayProjectionV1:
    """One caller-supplied recheck; no reads/allocations/implicit source authority."""
    value = validate_model(TodayComponentsV1, components, "saved_unreadable")
    state = value.actions
    plan = value.active_plan
    if (
        (state is not None and state.profile_id != value.profile_id)
        or (
            plan.current_observed_head is not None
            and plan.current_observed_head.profile_id != value.profile_id
        )
        or (
            plan.selection is not None
            and plan.selection.observed_head.profile_id != value.profile_id
        )
    ):
        raise ActionError("saved_unreadable")
    if state is not None and state.active_preparation != plan.selection:
        raise ActionError("saved_unreadable")
    union = set(s.source_target_ids(state) if state is not None else []) | set(plan.goal_result_ids)
    if (
        len(union) > 40
        or len({item.result_id for item in value.source_statuses}) != len(value.source_statuses)
        or any(item.result_id not in union for item in value.source_statuses)
    ):
        raise ActionError("saved_unreadable")
    mixed = value.initial_component_token != value.rechecked_component_token
    sources = list(value.source_statuses)
    if not value.research_access_after_recheck:
        sources = [
            s.SourceReadStatusV1(
                result_id=item.result_id,
                target_state=item.target_state,
                source_state="research_locked"
                if item.target_state == "eligible"
                else "not_evaluated",
                observed_at=item.observed_at,
                current_digest=None,
                reasons=[],
            )
            for item in sources
        ]
    by_source = {item.result_id: item for item in sources}
    notices: list[s.TodayNoticeV1] = []
    if mixed:
        notices.append(s.TodayNoticeV1(code="mixed_revision"))
    if value.action_state == "unavailable":
        notices.append(s.TodayNoticeV1(code="actions_unavailable"))
    if plan.state == "unavailable":
        notices.append(s.TodayNoticeV1(code="plan_unavailable"))
    elif plan.needs_review:
        notices.append(s.TodayNoticeV1(code="plan_needs_review"))
    if not value.preparation_access.allowed:
        notices.append(s.TodayNoticeV1(code="preparation_locked"))
    personal_cards: list[s.TodayCardV1] = []
    study_cards: list[s.TodayCardV1] = []
    tasks = {task.id: task for task in state.document_tasks} if state is not None else {}

    def dependency_reasons(
        task: s.DocumentTaskV1,
    ) -> list[
        Literal[
            "dependency_missing",
            "dependency_cycle",
            "dependency_not_reported_ready",
            "report_refers_to_previous_binding",
            "not_needed_is_not_a_waiver",
        ]
    ]:
        reasons: list[
            Literal[
                "dependency_missing",
                "dependency_cycle",
                "dependency_not_reported_ready",
                "report_refers_to_previous_binding",
                "not_needed_is_not_a_waiver",
            ]
        ] = list(report_review_reasons(task))
        stack: list[tuple[str, tuple[str, ...]]] = [(task.id, (task.id,))]
        visited: set[str] = set()
        while stack:
            record_id, trail = stack.pop()
            if record_id in visited:
                continue
            visited.add(record_id)
            for dependency_id in tasks[record_id].personal.depends_on_task_ids:
                dependency = tasks.get(dependency_id)
                if dependency is None:
                    reasons.append("dependency_missing")
                elif dependency_id in trail:
                    reasons.append("dependency_cycle")
                else:
                    if dependency.report.state not in {
                        "prepared_reported",
                        "sent_reported",
                        "received_reported",
                    } or report_review_reasons(dependency):
                        reasons.append("dependency_not_reported_ready")
                    stack.append((dependency_id, (*trail, dependency_id)))
        return list(dict.fromkeys(reasons))

    def personal_card(
        record: s.DocumentTaskV1 | s.ApplicationRecordV1,
    ) -> s.TodayCardV1:
        if isinstance(record, s.DocumentTaskV1):
            details = record.personal.details
            result_id: str | None = None
            if record.binding is not None:
                result_id = record.binding.result_id
            elif state is not None:
                for application in state.applications:
                    if application.id == record.application_id:
                        result_id = application.target.result_id
                        break
            reasons = dependency_reasons(record)
            target: s.PersonalActionRef = s.DocumentTaskRefV1(id=record.id)
            record_kind: Literal["personal_document_action", "personal_application_action"] = (
                "personal_document_action"
            )
            entered = record.binding is None
            card_id = f"document:{record.id}"
        else:
            details = record.details
            result_id = record.target.result_id
            reasons = []
            target = s.ApplicationRefV1(id=record.id)
            record_kind = "personal_application_action"
            entered = False
            card_id = f"application:{record.id}"
        due = details.due
        date_read = s.TodayDateReadV1(
            local_date=due.local_date if due is not None else None,
            timezone=due.timezone if due is not None else None,
            certainty="applicant_entered"
            if due is not None and due.timezone is not None
            else "date_only_timezone_unknown"
            if due is not None
            else "unknown",
            comparison_zone=due.timezone
            if due is not None and due.timezone is not None
            else value.display_timezone,
            fallback_display_only=due is not None and due.timezone is None,
        )
        source = by_source.get(result_id) if result_id is not None else None
        if reasons:
            notices.append(s.TodayNoticeV1(code="dependency_review", record_id=record.id))
        if source is not None and source.reasons:
            notices.append(s.TodayNoticeV1(code="source_review", record_id=record.id))
        return s.TodayCardV1(
            id=card_id,
            reason=record_kind,
            target=target,
            target_result_id=result_id,
            date=date_read,
            dependency_reasons=reasons,
            workload_origin="personal_unallocated",
            planned_minutes=None,
            source_state=source.source_state
            if source is not None
            else "applicant_entered"
            if entered
            else "not_evaluated",
            actionable=not mixed,
        )

    if not mixed and state is not None:
        for task in sorted(state.document_tasks, key=lambda item: item.id):
            if task.report.state not in {
                "prepared_reported",
                "sent_reported",
                "received_reported",
                "not_needed_reported",
            } or report_review_reasons(task):
                personal_cards.append(personal_card(task))
        for application in sorted(state.applications, key=lambda item: item.id):
            if application.status in {"planning", "preparing"}:
                personal_cards.append(personal_card(application))
    if not mixed and plan.state in {"available", "needs_review"}:
        workload_origin: Literal["g2", "legacy_v2", "legacy_v1"]
        if plan.origin == "g2":
            workload_origin = "g2"
        elif plan.origin == "legacy_v2":
            workload_origin = "legacy_v2"
        elif plan.origin == "legacy_v1":
            workload_origin = "legacy_v1"
        else:
            raise ActionError("saved_unreadable")
        for action in plan.study_actions:  # Preserve exact native accepted slot order.
            if action.completion == "self_reported_complete":
                continue
            ref = action.ref
            actionable = (
                action.availability == "available"
                and ref is not None
                and (
                    ref.kind == "attempt_review"
                    or (ref.kind == "lesson" and value.preparation_access.allowed)
                )
            )
            study_cards.append(
                s.TodayCardV1(
                    id=action.id,
                    reason="accepted_study_action",
                    target=ref,
                    target_result_id=None,
                    date=s.TodayDateReadV1(
                        local_date=action.local_date,
                        timezone=action.timezone,
                        certainty="applicant_entered",
                        comparison_zone=action.timezone,
                        fallback_display_only=False,
                    ),
                    dependency_reasons=[],
                    workload_origin=workload_origin,
                    planned_minutes=action.planned_minutes,
                    source_state="not_evaluated",
                    actionable=actionable,
                )
            )

    def personal_order(card: s.TodayCardV1) -> tuple[str, str, str]:
        # One shared stable record-ID order, without an entity-category priority.
        target = card.target
        if not isinstance(target, s.ApplicationRefV1 | s.DocumentTaskRefV1):
            raise ActionError("saved_unreadable")
        return target.id, target.kind, card.id

    personal_cards.sort(key=personal_order)

    def card_day(card: s.TodayCardV1) -> date:
        return value.as_of.astimezone(ZoneInfo(card.date.comparison_zone)).date()

    overdue = [
        card
        for card in personal_cards
        if card.date.local_date is not None and card.date.local_date < card_day(card)
    ]
    overdue.sort(key=lambda card: (card.date.local_date, *personal_order(card)))
    current_personal = [card for card in personal_cards if card.date.local_date == card_day(card)]
    current_study = [card for card in study_cards if card.date.local_date == card_day(card)]
    future_study = [
        card
        for card in study_cards
        if card.date.local_date is not None and card.date.local_date > card_day(card)
    ]
    future_personal = [
        card
        for card in personal_cards
        if card.date.local_date is not None and card.date.local_date > card_day(card)
    ]
    # Stable sort retains native study order; study precedes personal on one date.
    future = sorted(
        [*future_study, *future_personal],
        key=lambda card: (
            card.date.local_date,
            0 if card.reason == "accepted_study_action" else 1,
        ),
    )
    undated = [card for card in personal_cards if card.date.local_date is None]
    if not mixed and any(
        card.date.local_date is not None and card.date.local_date < card_day(card)
        for card in study_cards
    ):
        notices.append(s.TodayNoticeV1(code="plan_needs_review"))
    available = plan.state in {"available", "needs_review"} and not mixed
    return s.TodayProjectionV1(
        profile_id=value.profile_id,
        as_of=value.as_of,
        display_timezone=value.display_timezone,
        action_state=value.action_state,
        action_revision=state.revision
        if state is not None
        else 0
        if value.action_state == "absent"
        else None,
        action_digest=s.state_digest(state) if state is not None else None,
        action_observed_at=value.action_observed_at,
        active_plan=plan,
        preparation_access=value.preparation_access,
        current_source_statuses=sources,
        consistency="mixed_revision" if mixed else "component_reads",
        needs_refresh=mixed,
        notices=notices,
        overdue_personal=overdue,
        today_study=current_study,
        today_personal=current_personal,
        future=future,
        undated_personal=undated,
        application_summaries=list(state.applications) if state is not None else [],
        workload="one_selected_plan" if available else "unknown",
        allocated_study_minutes=plan.allocated_minutes if available else None,
    )
