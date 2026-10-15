"""Finite pure G3 controls. Every case/actor/document/plan is synthetic.

No database, app startup, provider, real university, clock or saved private input.
These proposed tests have not been collected or executed by their author.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain import admissions_actions as d
from app.domain.claim_scope import ClaimScope, RequestedScope
from app.domain.enums import UserDecision
from app.domain.preparation_graph import ProgrammeEvidence, build_preparation_graph
from app.schemas import admissions_actions as s
from app.schemas.claim import ClaimOut
from app.schemas.preparation_graph import PreparationGraphRequest
from app.schemas.result import DocumentChecklist, DocumentItem

AT = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
PROFILE = "case-synthetic"
DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def uuid(index: int) -> str:
    return str(UUID(int=index))


def details(due: str | None = None, zone: str | None = "Asia/Almaty") -> dict:
    return {
        "due": None if due is None else {"local_date": due, "timezone": zone},
        "notes": "entered synthetic note",
    }


def personal(label: str = "Entered transcript", **updates) -> dict:
    return {
        "label": label,
        "responsible_actor": "applicant",
        "details": details(),
        "depends_on_task_ids": [],
        **updates,
    }


def target(result: str = "r-a", *, award: str | None = None) -> dict:
    return {
        "result_id": result,
        "purpose": "scholarship" if award is not None else "admission",
        "award_id": award,
        "intake": {"state": "unknown"},
        "route": {"state": "applicant_entered", "value": "entered route"},
        "confirmed_entered_context": True,
    }


def request(kind: str, revision: int = 0, index: int = 1, **fields) -> dict:
    return {
        "kind": kind,
        "client_write_uuid": uuid(index),
        "expected_revision": revision,
        **fields,
    }


def context(index: int, **fields) -> d.ActionContextV1:
    data = {
        "profile_id": PROFILE,
        "event_id": f"event-{index}",
        "accepted_at": AT,
        "actor": d.actor_reference(
            "user-aaaaaaaa-full", "org-synthetic", local_development=False
        ),
        "new_application_id": f"app-{index}",
        "new_task_id": f"task-{index}",
        **fields,
    }
    return d.ActionContextV1.model_validate(data)


def observation(
    result: str = "r-a", *, research: bool = True, **fields
) -> d.TargetObservationV1:
    return d.TargetObservationV1(
        profile_id=PROFILE,
        result_id=result,
        state="selected",
        decision="approved",
        research_access=research,
        award_ids=["award-a"],
        **fields,
    )


def application():
    return d.apply_action(
        None,
        request(
            "create_application", target=target(), label="Entered A", details=details()
        ),
        context(1, target=observation()),
    )


def task_after(transition, index: int = 2, **fields):
    return d.apply_action(
        transition.state,
        request(
            "create_personal_task",
            transition.state.revision,
            index,
            application_id=transition.state.applications[0].id,
            personal=personal(**fields),
        ),
        context(index),
    )


def item(**updates) -> dict:
    return {
        "name": "Synthetic transcript",
        "purpose": "admission",
        "owner": "applicant",
        "source_url": "https://example.edu/public/transcript",
        **updates,
    }


def checklist(**updates) -> dict:
    return {
        "result_id": "r-a",
        "university": "Synthetic",
        "program": "Programme A",
        "admission_documents": [item()],
        "ordered_steps": ["Original A", "Original B"],
        "completeness": "partial",
        **updates,
    }


def source_binding(raw: dict | None = None, *, occurrences=None, graph=None):
    return d.build_binding_selection(
        raw if raw is not None else checklist(),
        profile_id=PROFILE,
        result_id="r-a",
        selected_occurrences=occurrences or [("admission_documents", 0)],
        purpose="admission",
        award_id=None,
        graph=graph,
    )


def source_context(index: int, binding, **fields):
    return context(
        index,
        source=d.SourceObservationV1(
            target=observation(),
            state="readable",
            selection=binding,
            preview_digest=DIGEST,
        ),
        **fields,
    )


def binding_after(transition, index: int = 2, *, binding=None, application_id=None):
    current = binding if binding is not None else source_binding()
    return d.apply_action(
        transition.state,
        request(
            "bind_source_task",
            transition.state.revision,
            index,
            application_id=application_id,
            source=current.model_dump(mode="python"),
            source_preview_digest=DIGEST,
            personal=personal(),
        ),
        source_context(index, current),
    )


def report_after(transition, index: int, *, state: str = "prepared_reported"):
    task_id = transition.state.document_tasks[-1].id
    return d.apply_action(
        transition.state,
        request(
            "set_document_self_report",
            transition.state.revision,
            index,
            task_id=task_id,
            report={
                "state": state,
                "entered_at": None,
                "confirmed_personal_report": True,
            },
        ),
        context(index),
    )


def safe_error(code: str, callback) -> d.ActionError:
    with pytest.raises(d.ActionError) as caught:
        callback()
    assert caught.value.detail == {
        "code": f"admissions_actions_{code}",
        "message": d.ERRORS[code][1],
    }
    assert caught.value.status == d.ERRORS[code][0]
    return caught.value


def metadata(receipt):
    return s.EventMetadataV1(
        profile_id=receipt.profile_id,
        event_id=receipt.event_id,
        revision=receipt.revision,
        kind=receipt.kind,
        accepted_at=receipt.accepted_at,
        affected_refs=receipt.affected_refs,
    )


def graph_for(raw, *, claims=()):
    native = DocumentChecklist.model_validate(raw)
    row = ProgrammeEvidence(
        profile_id=PROFILE,
        result_id="r-a",
        run_id="run-synthetic",
        user_decision=UserDecision.APPROVED,
        university="Synthetic",
        programme="Programme A",
        research_access=True,
        requested_scope=RequestedScope(university="Synthetic", programme="Programme A"),
        checklist=native,
        claims=claims,
    )
    return build_preparation_graph(
        PROFILE, PreparationGraphRequest(selected_result_ids=["r-a"]), (row,)
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_original_nonfinite_values_never_launder_through_json_or_forged_typed_instance(
    value,
):
    raw = request(
        "create_personal_task",
        application_id=None,
        personal=personal(details={"due": None, "notes": value}),
    )
    safe_error("input_invalid", lambda: d.validate_request(raw))
    forged = s.CreatePersonalTaskV1.model_construct(**raw)
    safe_error("input_invalid", lambda: d.validate_request(forged))
    native = DocumentItem.model_construct(**item(max_file_size_mb=value))
    safe_error(
        "source_unreadable",
        lambda: d.checklist_identity(checklist(admission_documents=[native])),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_revision", True),
        ("expected_revision", "0"),
        ("client_write_uuid", "1"),
        ("client_write_uuid", "AAAAAAAA000000000000000000000001"),
        ("official_verified", True),
        ("actor", {"actor_ref_digest": DIGEST}),
        ("extra", {}),
    ],
)
def test_closed_client_request_does_not_coerce_or_accept_server_fields(field, value):
    raw = request("create_personal_task", application_id=None, personal=personal())
    raw[field] = value
    safe_error("input_invalid", lambda: d.validate_request(raw))


def test_native_uppercase_uuid_is_the_same_canonical_intent_digest_and_original_replay():
    lower_uuid = "a1b2c3d4-5e6f-789a-bcde-f0123456789a"
    lower = request("create_personal_task", application_id=None, personal=personal())
    lower["client_write_uuid"] = lower_uuid
    upper = {**copy.deepcopy(lower), "client_write_uuid": lower_uuid.upper()}
    typed_lower = d.validate_request(lower)
    typed_upper = d.validate_request(upper)
    assert typed_lower == typed_upper
    assert typed_upper.model_dump(mode="json")["client_write_uuid"] == lower_uuid
    assert (
        lower["client_write_uuid"] == lower_uuid
        and upper["client_write_uuid"] == lower_uuid.upper()
    )
    literal_digest = hashlib.sha256(
        json.dumps(
            {
                "schema_version": "g3-action-request-digest-v1",
                "profile_id": PROFILE,
                "request": typed_lower.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert s.request_digest(PROFILE, typed_lower) == literal_digest
    assert s.request_digest(PROFILE, typed_upper) == literal_digest
    accepted_lower = d.apply_action(None, lower, context(1))
    accepted_upper = d.apply_action(None, upper, context(1))
    assert accepted_lower == accepted_upper
    assert accepted_upper.receipt.canonical_request_digest == literal_digest
    assert (
        d.replay_receipt(PROFILE, lower, accepted_upper.receipt)
        == accepted_upper.receipt
    )
    assert (
        d.replay_receipt(PROFILE, upper, accepted_lower.receipt)
        == accepted_lower.receipt
    )


@pytest.mark.parametrize(
    "raw", ["2026-02-30", "12/10/2026", "2026-10-12 ", 1791792000, True]
)
def test_entered_dates_are_literal_valid_calendar_dates(raw):
    safe_error(
        "input_invalid",
        lambda: d.validate_request(
            request(
                "create_personal_task",
                application_id=None,
                personal=personal(details=details(raw)),
            )
        ),
    )


@pytest.mark.parametrize("confirmation", [1, "true", False, None])
def test_confirmation_is_literal_boolean_true(confirmation):
    entered = target()
    entered["confirmed_entered_context"] = confirmation
    safe_error(
        "input_invalid",
        lambda: d.validate_request(
            request("create_application", target=entered, label="A", details=details())
        ),
    )


def test_event_ref_has_exact_three_fields_and_no_receipt_hash_cycle():
    first = application()
    ref = first.state.applications[0].created_ref
    assert ref.model_dump() == {
        "event_id": "event-1",
        "revision": 1,
        "kind": "create_application",
    }
    with pytest.raises(ValidationError):
        s.EventRefV1.model_validate({**ref.model_dump(), "receipt_digest": DIGEST})
    state_wire = first.state.model_dump(mode="json")
    assert "receipt_digest" not in json.dumps(state_wire)
    literal_state = hashlib.sha256(
        json.dumps(
            {"schema_version": "g3-state-digest-v1", "state": state_wire},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert first.receipt.after_state_digest == literal_state
    assert first.receipt.revision == 1 and first.receipt.expected_revision == 0
    assert (
        first.receipt.predecessor_event_id is None
        and first.receipt.before_state_digest is None
    )


def test_full_actor_ids_not_display_prefixes_define_actor_reference():
    a = d.actor_reference("12345678-user-a", "org-a", local_development=False)
    b = d.actor_reference("12345678-user-b", "org-a", local_development=False)
    c = d.actor_reference("12345678-user-a", "org-b", local_development=False)
    assert len({a.actor_ref_digest, b.actor_ref_digest, c.actor_ref_digest}) == 3
    literal = hashlib.sha256(
        b'{"organization_id":"org-a","schema_version":"g3-actor-reference-v1","user_id":"12345678-user-a"}'
    ).hexdigest()
    assert a.actor_ref_digest == literal
    assert "12345678-user-a" not in a.model_dump_json()


def test_replay_keeps_original_actor_and_ack_independent_of_mutable_source_context():
    first = application()
    wire_before = first.receipt.model_dump(mode="json")
    replay = d.replay_receipt(PROFILE, first.receipt.request, first.receipt)
    assert replay.model_dump(mode="json") == wire_before
    safe_error(
        "record_not_found",
        lambda: d.replay_receipt("foreign-case", first.receipt.request, first.receipt),
    )
    changed = first.receipt.request.model_dump(mode="python")
    changed["label"] = "Different intent"
    safe_error(
        "uuid_conflict", lambda: d.replay_receipt(PROFILE, changed, first.receipt)
    )


def test_existing_personal_updates_require_no_target_source_plan_or_entitlement_observation():
    first = task_after(application())
    snapshot = first.state.model_dump(mode="json")
    updated = report_after(first, 3)
    assert updated.state.document_tasks[0].report.state == "prepared_reported"
    assert (
        updated.state.document_tasks[0].report.official_verification == "not_performed"
    )
    assert first.state.model_dump(mode="json") == snapshot
    bad = request(
        "set_document_self_report",
        updated.state.revision,
        4,
        task_id="foreign-task",
        report={
            "state": "sent_reported",
            "entered_at": None,
            "confirmed_personal_report": True,
        },
    )
    safe_error(
        "record_not_found", lambda: d.apply_action(updated.state, bad, context(4))
    )


def test_creation_scholarship_requires_exact_own_award_after_source_guard():
    intent = request(
        "create_application",
        target=target(award="award-a"),
        label="A",
        details=details(),
    )
    safe_error(
        "source_locked",
        lambda: d.apply_action(
            None, intent, context(1, target=observation(research=False))
        ),
    )
    wrong = observation().model_copy(update={"award_ids": ["different-award"]})
    safe_error(
        "record_not_found",
        lambda: d.apply_action(None, intent, context(1, target=wrong)),
    )
    good = d.apply_action(None, intent, context(1, target=observation()))
    assert good.state.applications[0].target.award_id == "award-a"


def test_target_intake_route_award_are_immutable_in_every_closed_personal_command():
    first = application()
    entered_target = first.state.applications[0].target.model_dump(mode="json")
    second = d.apply_action(
        first.state,
        request(
            "set_personal_details",
            1,
            2,
            target={"kind": "application", "id": "app-1"},
            details=details("2027-01-03", None),
        ),
        context(2),
    )
    assert second.state.applications[0].target.model_dump(mode="json") == entered_target
    mutation = request(
        "set_personal_details",
        2,
        3,
        target={"kind": "application", "id": "app-1", "result_id": "r-b"},
        details=details(),
    )
    safe_error(
        "input_invalid", lambda: d.apply_action(second.state, mutation, context(3))
    )


def test_submission_is_applicant_declaration_and_mentioned_tasks_are_not_mutated():
    first = task_after(application())
    task_before = first.state.document_tasks[0].model_dump(mode="json")
    intent = request(
        "declare_submission",
        2,
        3,
        application_id="app-1",
        submission={
            "entered_at": {
                "local_date": "2026-10-11",
                "local_time": None,
                "timezone": None,
            },
            "channel": "entered portal",
            "document_task_ids": ["task-2"],
            "confirmed_applicant_declaration": True,
        },
    )
    submitted = d.apply_action(first.state, intent, context(3))
    assert (
        submitted.receipt.applied_delta.declaration.kind
        == "applicant_declared_submission"
    )
    assert submitted.receipt.applied_delta.declaration.receipt_origin == "applicant"
    assert (
        submitted.receipt.applied_delta.declaration.official_verification
        == "not_performed"
    )
    assert submitted.state.document_tasks[0].model_dump(mode="json") == task_before
    assert submitted.receipt.affected_refs.document_task_ids == []
    assert submitted.receipt.affected_refs.application_ids == ["app-1"]
    safe_error(
        "invalid_transition",
        lambda: d.apply_action(
            submitted.state,
            request(
                "set_planning_status", 3, 4, application_id="app-1", status="planning"
            ),
            context(4),
        ),
    )


def test_withdrawal_retains_submission_history_and_correction_requires_exact_loaded_own_receipt():
    first = application()
    submitted = d.apply_action(
        first.state,
        request(
            "declare_submission",
            1,
            2,
            application_id="app-1",
            submission={
                "entered_at": {
                    "local_date": "2026-10-11",
                    "local_time": "09:30",
                    "timezone": "Asia/Almaty",
                },
                "channel": "entered",
                "confirmed_applicant_declaration": True,
            },
        ),
        context(2),
    )
    before = submitted.receipt.model_dump(mode="json")
    withdrawn = d.apply_action(
        submitted.state,
        request(
            "declare_withdrawal",
            2,
            3,
            application_id="app-1",
            withdrawal={"entered_at": None, "confirmed_applicant_declaration": True},
        ),
        context(3),
    )
    assert submitted.receipt.model_dump(mode="json") == before
    assert withdrawn.state.applications[0].status == "withdrawn_declared"
    assert set(withdrawn.state.applications[0].model_dump()) == {
        "id",
        "profile_id",
        "target",
        "label",
        "details",
        "status",
        "created_ref",
        "latest_ref",
        "status_ref",
    }
    intent = request(
        "correct_declaration",
        3,
        4,
        application_id="app-1",
        prior_declaration=withdrawn.state.applications[0].status_ref.model_dump(),
        replacement={"kind": "planning", "status": "preparing"},
        confirmed_correction=True,
    )
    safe_error(
        "record_not_found", lambda: d.apply_action(withdrawn.state, intent, context(4))
    )
    safe_error(
        "record_not_found",
        lambda: d.apply_action(
            withdrawn.state,
            intent,
            context(4, prior_declaration_receipt=submitted.receipt),
        ),
    )
    corrected = d.apply_action(
        withdrawn.state, intent, context(4, prior_declaration_receipt=withdrawn.receipt)
    )
    assert corrected.state.applications[0].status == "preparing"
    assert corrected.receipt.applied_delta.corrected_declaration.event_id == "event-3"
    assert (
        d.validate_complete_export(
            corrected.state,
            [first.receipt, submitted.receipt, withdrawn.receipt, corrected.receipt],
            profile_id=PROFILE,
        )[1].model_dump(mode="json")
        == before
    )


def test_a_prior_own_planning_correction_can_itself_be_corrected_without_rewriting_history():
    first = application()
    submitted = d.apply_action(
        first.state,
        request(
            "declare_submission",
            1,
            2,
            application_id="app-1",
            submission={
                "entered_at": {
                    "local_date": "2026-10-11",
                    "local_time": None,
                    "timezone": None,
                },
                "channel": "first entered channel",
                "confirmed_applicant_declaration": True,
            },
        ),
        context(2),
    )
    corrected = d.apply_action(
        submitted.state,
        request(
            "correct_declaration",
            2,
            3,
            application_id="app-1",
            prior_declaration=submitted.state.applications[0].status_ref.model_dump(),
            replacement={"kind": "planning", "status": "preparing"},
            confirmed_correction=True,
        ),
        context(3, prior_declaration_receipt=submitted.receipt),
    )
    assert corrected.receipt.applied_delta.declaration is None
    assert corrected.receipt.affected_refs.application_ids == ["app-1"]
    before = [
        value.receipt.model_dump(mode="json") for value in (first, submitted, corrected)
    ]
    prior_ref = corrected.state.applications[0].status_ref.model_dump()
    recorrected = d.apply_action(
        corrected.state,
        request(
            "correct_declaration",
            3,
            4,
            application_id="app-1",
            prior_declaration=prior_ref,
            replacement={
                "kind": "submission",
                "submission": {
                    "entered_at": {
                        "local_date": "2026-10-12",
                        "local_time": None,
                        "timezone": None,
                    },
                    "channel": "corrected entered channel",
                    "confirmed_applicant_declaration": True,
                },
            },
            confirmed_correction=True,
        ),
        context(4, prior_declaration_receipt=corrected.receipt),
    )
    declaration = recorrected.receipt.applied_delta.declaration
    assert declaration is not None
    assert declaration.kind == "applicant_declared_submission"
    assert declaration.entered.channel == "corrected entered channel"
    assert (
        declaration.receipt_origin == "applicant"
        and declaration.official_verification == "not_performed"
    )
    assert recorrected.receipt.applied_delta.corrected_declaration.event_id == "event-3"
    assert recorrected.state.applications[0].status == "submitted_declared"
    # The accepted contract permits any exact prior own declaration, not only
    # the newest status ref. A new CAS event retains that explicit old reference.
    again = d.apply_action(
        recorrected.state,
        request(
            "correct_declaration",
            4,
            5,
            application_id="app-1",
            prior_declaration=prior_ref,
            replacement={"kind": "planning", "status": "planning"},
            confirmed_correction=True,
        ),
        context(5, prior_declaration_receipt=corrected.receipt),
    )
    assert again.state.applications[0].status == "planning"
    assert again.receipt.applied_delta.declaration is None
    assert again.receipt.applied_delta.corrected_declaration.event_id == "event-3"
    history = [
        first.receipt,
        submitted.receipt,
        corrected.receipt,
        recorrected.receipt,
        again.receipt,
    ]
    assert [
        value.model_dump(mode="json")
        for value in d.validate_complete_export(
            again.state, history, profile_id=PROFILE
        )[:3]
    ] == before
    assert [
        value.receipt.model_dump(mode="json") for value in (first, submitted, corrected)
    ] == before


def test_correction_distinguishes_a_wrong_own_application_from_missing_or_foreign_receipts():
    first = application()
    other = d.apply_action(
        first.state,
        request(
            "create_application",
            1,
            2,
            target=target("r-b"),
            label="Entered B",
            details=details(),
        ),
        context(2, target=observation("r-b")),
    )
    submitted = d.apply_action(
        other.state,
        request(
            "declare_submission",
            2,
            3,
            application_id="app-1",
            submission={
                "entered_at": {
                    "local_date": "2026-10-11",
                    "local_time": None,
                    "timezone": None,
                },
                "channel": "entered",
                "confirmed_applicant_declaration": True,
            },
        ),
        context(3),
    )
    intent = request(
        "correct_declaration",
        3,
        4,
        application_id="app-2",
        prior_declaration=submitted.state.applications[0].status_ref.model_dump(),
        replacement={"kind": "planning", "status": "planning"},
        confirmed_correction=True,
    )
    own = safe_error(
        "invalid_transition",
        lambda: d.apply_action(
            submitted.state,
            intent,
            context(4, prior_declaration_receipt=submitted.receipt),
        ),
    )
    assert own.status == 422
    missing = safe_error(
        "record_not_found", lambda: d.apply_action(submitted.state, intent, context(4))
    )
    foreign_target = observation().model_copy(update={"profile_id": "case-foreign"})
    foreign = d.apply_action(
        None,
        request(
            "create_application",
            index=10,
            target=target(),
            label="Foreign entered A",
            details=details(),
        ),
        context(10, profile_id="case-foreign", target=foreign_target),
    )
    foreign_submission = d.apply_action(
        foreign.state,
        request(
            "declare_submission",
            1,
            11,
            application_id="app-10",
            submission={
                "entered_at": {
                    "local_date": "2026-10-11",
                    "local_time": None,
                    "timezone": None,
                },
                "channel": "foreign entered",
                "confirmed_applicant_declaration": True,
            },
        ),
        context(11, profile_id="case-foreign"),
    )
    foreign_intent = {
        **intent,
        "prior_declaration": foreign_submission.state.applications[
            0
        ].status_ref.model_dump(),
    }
    hidden = safe_error(
        "record_not_found",
        lambda: d.apply_action(
            submitted.state,
            foreign_intent,
            context(4, prior_declaration_receipt=foreign_submission.receipt),
        ),
    )
    assert hidden.detail == missing.detail and hidden.status == missing.status == 404


@pytest.mark.parametrize(
    "corruption", ["self_hash", "affected_application", "forged_nonfinite"]
)
def test_corrupted_saved_prior_correction_receipts_are_safe_503_not_client_errors(
    corruption,
):
    first = application()
    submitted = d.apply_action(
        first.state,
        request(
            "declare_submission",
            1,
            2,
            application_id="app-1",
            submission={
                "entered_at": {
                    "local_date": "2026-10-11",
                    "local_time": None,
                    "timezone": None,
                },
                "channel": "PRIVATE entered",
                "confirmed_applicant_declaration": True,
            },
        ),
        context(2),
    )
    original = submitted.receipt.model_dump(mode="json")
    prior = submitted.receipt.model_dump(mode="python")
    if corruption == "self_hash":
        prior["receipt_digest"] = OTHER_DIGEST
    elif corruption == "affected_application":
        prior["affected_refs"]["application_ids"] = ["app-other"]
    else:
        prior = submitted.receipt.model_copy(
            update={
                "actor": submitted.receipt.actor.model_copy(
                    update={"actor_ref_digest": float("nan")}
                )
            }
        )
    raw_context = context(3).model_dump(mode="python")
    raw_context["prior_declaration_receipt"] = prior
    intent = request(
        "correct_declaration",
        2,
        3,
        application_id="app-1",
        prior_declaration=submitted.state.applications[0].status_ref.model_dump(),
        replacement={"kind": "planning", "status": "planning"},
        confirmed_correction=True,
    )
    failure = safe_error(
        "saved_unreadable", lambda: d.apply_action(submitted.state, intent, raw_context)
    )
    assert failure.status == 503 and "PRIVATE" not in str(failure.detail)
    assert submitted.receipt.model_dump(mode="json") == original


def test_rebind_keeps_durable_id_and_original_report_with_separate_previous_binding_annotation():
    first = binding_after(application())
    reported = report_after(first, 3)
    report_wire = reported.state.document_tasks[0].report.model_dump(mode="json")
    replacement = source_binding(checklist(admission_documents=[item(word_limit=300)]))
    task = reported.state.document_tasks[0]
    rebound = d.apply_action(
        reported.state,
        request(
            "rebind_source_task",
            3,
            4,
            task_id=task.id,
            expected_binding_digest=task.binding.binding_digest,
            source=replacement.model_dump(mode="python"),
            source_preview_digest=DIGEST,
        ),
        source_context(4, replacement),
    )
    current = rebound.state.document_tasks[0]
    assert (
        current.id == task.id and current.report.model_dump(mode="json") == report_wire
    )
    assert d.report_review_reasons(current) == ["report_refers_to_previous_binding"]
    explicit = report_after(rebound, 5)
    assert d.report_review_reasons(explicit.state.document_tasks[0]) == []
    assert (
        explicit.state.document_tasks[0].report.binding_digest_at_report
        == current.binding.binding_digest
    )


def test_unbound_report_is_not_transferred_when_first_binding_is_explicitly_added():
    first = report_after(task_after(application()), 3)
    binding = source_binding()
    current = first.state.document_tasks[0]
    rebound = d.apply_action(
        first.state,
        request(
            "rebind_source_task",
            3,
            4,
            task_id=current.id,
            expected_binding_digest=None,
            source=binding.model_dump(mode="python"),
            source_preview_digest=DIGEST,
        ),
        source_context(4, binding),
    )
    assert rebound.state.document_tasks[0].report.binding_digest_at_report is None
    assert d.report_review_reasons(rebound.state.document_tasks[0]) == [
        "report_refers_to_previous_binding"
    ]


def test_explicit_import_is_all_or_nothing_exact_snapshot_and_does_not_clear_native_marks():
    first = task_after(application())
    mapping = {
        "task_id": "task-2",
        "legacy_key_digest": DIGEST,
        "expected_binding_digest": None,
        "source_preview_digest": None,
        "legacy_value": True,
        "confirmed_prepared_report": True,
    }
    raw = request(
        "import_legacy_marks",
        2,
        3,
        legacy_snapshot_digest=DIGEST,
        mappings=[mapping],
        entered_at=None,
    )
    observed = d.LegacyMarkObservationV1.model_validate(
        {"profile_id": PROFILE, "snapshot_digest": DIGEST, "mappings": [mapping]}
    )
    imported = d.apply_action(first.state, raw, context(3, legacy=observed))
    assert (
        imported.state.document_tasks[0].report.origin == "explicit_browser_mark_import"
    )
    assert imported.receipt.request.mappings[0].source_version == "unknown"
    assert imported.receipt.request.mappings[0].original_reported_at is None
    assert observed.model_dump(mode="json")["mappings"][0]["legacy_value"] is True
    altered = copy.deepcopy(raw)
    altered["legacy_snapshot_digest"] = OTHER_DIGEST
    safe_error(
        "legacy_import_changed",
        lambda: d.apply_action(first.state, altered, context(3, legacy=observed)),
    )
    assert first.state.document_tasks[0].report.origin == "unreported"


def test_current_head_and_affected_roles_cannot_be_satisfied_by_merely_mentioned_record():
    first = task_after(application())
    accepted = d.validate_current_snapshot(
        first.state,
        first.receipt,
        profile_id=PROFILE,
        row_digest=first.receipt.after_state_digest,
        row_updated_at=AT,
        latest_revision=2,
        metadata=[metadata(application().receipt)],
    )
    assert accepted == first.state
    foreign_meta = metadata(application().receipt).model_copy(
        update={"profile_id": "foreign"}
    )
    safe_error(
        "saved_unreadable",
        lambda: d.validate_current_snapshot(
            first.state,
            first.receipt,
            profile_id=PROFILE,
            row_digest=first.receipt.after_state_digest,
            row_updated_at=AT,
            latest_revision=2,
            metadata=[foreign_meta],
        ),
    )
    wrong_affected = metadata(application().receipt).model_copy(
        update={
            "affected_refs": s.EventAffectedRefsV1(
                application_ids=[], document_task_ids=[], active_selector_changed=False
            )
        }
    )
    safe_error(
        "saved_unreadable",
        lambda: d.validate_current_snapshot(
            first.state,
            first.receipt,
            profile_id=PROFILE,
            row_digest=first.receipt.after_state_digest,
            row_updated_at=AT,
            latest_revision=2,
            metadata=[wrong_affected],
        ),
    )
    safe_error(
        "saved_unreadable",
        lambda: d.validate_current_snapshot(
            first.state,
            first.receipt,
            profile_id=PROFILE,
            row_digest=first.receipt.after_state_digest,
            row_updated_at=AT,
            latest_revision=3,
            metadata=[metadata(application().receipt)],
        ),
    )


def test_rehashed_outer_state_does_not_replace_authoritative_head_delta():
    first = application()
    changed = first.state.model_dump(mode="python")
    changed["applications"][0]["label"] = "Locally tampered"
    forged = s.CaseActionsStateV1.model_validate(changed)
    safe_error(
        "saved_unreadable",
        lambda: d.validate_current_snapshot(
            forged,
            first.receipt,
            profile_id=PROFILE,
            row_digest=s.state_digest(forged),
            row_updated_at=AT,
            latest_revision=1,
            metadata=[],
        ),
    )
    broken = first.receipt.model_dump(mode="python")
    broken["applied_delta"]["applications"][0]["target"]["result_id"] = "unreviewed"
    broken["receipt_digest"] = DIGEST
    safe_error(
        "saved_unreadable",
        lambda: d.replay_receipt(PROFILE, first.receipt.request, broken),
    )


def test_complete_export_detects_missing_current_and_interleaving_new_head():
    first = application()
    second = task_after(first)
    safe_error(
        "saved_unreadable",
        lambda: d.validate_complete_export(None, [first.receipt], profile_id=PROFILE),
    )
    safe_error(
        "saved_unreadable",
        lambda: d.validate_complete_export(
            first.state, [first.receipt, second.receipt], profile_id=PROFILE
        ),
    )
    safe_error(
        "saved_unreadable",
        lambda: d.validate_complete_export(
            second.state, [second.receipt], profile_id=PROFILE
        ),
    )
    assert d.validate_complete_export(None, [], profile_id=PROFILE) == []


def test_caps_are_current_records_and_distinct_source_union_not_history_size():
    transition = None
    for index in range(1, 21):
        transition = d.apply_action(
            transition.state if transition is not None else None,
            request(
                "create_application",
                index - 1,
                index,
                target=target(f"r-{index}"),
                label=f"A{index}",
                details=details(),
            ),
            context(index, target=observation(f"r-{index}")),
        )
    assert len(s.source_target_ids(transition.state)) == 20
    safe_error(
        "limit_exceeded",
        lambda: d.apply_action(
            transition.state,
            request(
                "create_application",
                20,
                21,
                target=target("r-extra"),
                label="extra",
                details=details(),
            ),
            context(21, target=observation("r-extra")),
        ),
    )
    raw = checklist(result_id="r-1")
    binding = d.build_binding_selection(
        raw,
        profile_id=PROFILE,
        result_id="r-1",
        selected_occurrences=[("admission_documents", 0)],
        purpose="admission",
        award_id=None,
    )
    allowed = d.apply_action(
        transition.state,
        request(
            "bind_source_task",
            20,
            21,
            application_id=None,
            source=binding.model_dump(mode="python"),
            source_preview_digest=DIGEST,
            personal=personal(),
        ),
        context(
            21,
            source=d.SourceObservationV1(
                target=observation("r-1"),
                state="readable",
                preview_digest=DIGEST,
                selection=binding,
            ),
        ),
    )
    assert len(s.source_target_ids(allowed.state)) == 20
    raw_extra = checklist(result_id="r-extra")
    extra = d.build_binding_selection(
        raw_extra,
        profile_id=PROFILE,
        result_id="r-extra",
        selected_occurrences=[("admission_documents", 0)],
        purpose="admission",
        award_id=None,
    )
    safe_error(
        "limit_exceeded",
        lambda: d.apply_action(
            allowed.state,
            request(
                "rebind_source_task",
                21,
                22,
                task_id="task-21",
                expected_binding_digest=allowed.state.document_tasks[
                    0
                ].binding.binding_digest,
                source=extra.model_dump(mode="python"),
                source_preview_digest=DIGEST,
            ),
            context(
                22,
                source=d.SourceObservationV1(
                    target=observation("r-extra"),
                    state="readable",
                    preview_digest=DIGEST,
                    selection=extra,
                ),
            ),
        ),
    )


def test_four_hundred_task_cap_and_fifty_explicit_mapping_cap_are_literal():
    first = task_after(application())
    template = first.state.document_tasks[0].model_dump(mode="python")
    raw = first.state.model_dump(mode="python")
    raw["document_tasks"] = [
        {**copy.deepcopy(template), "id": f"task-cap-{index}"} for index in range(400)
    ]
    at_cap = s.CaseActionsStateV1.model_validate(raw)
    safe_error(
        "limit_exceeded",
        lambda: d.apply_action(
            at_cap,
            request(
                "create_personal_task", 2, 3, application_id=None, personal=personal()
            ),
            context(3),
        ),
    )
    mapping = {
        "task_id": "task-0",
        "legacy_key_digest": DIGEST,
        "expected_binding_digest": None,
        "source_preview_digest": None,
        "legacy_value": True,
        "confirmed_prepared_report": True,
    }
    mappings = [
        {**mapping, "task_id": f"task-{index}", "legacy_key_digest": f"{index:064x}"}
        for index in range(51)
    ]
    safe_error(
        "input_invalid",
        lambda: d.validate_request(
            request(
                "import_legacy_marks",
                mappings=mappings,
                legacy_snapshot_digest=DIGEST,
                entered_at=None,
            )
        ),
    )


def test_at_cap_metadata_reads_use_at_most_nine_batches_of_two_hundred_exact_ids():
    first = task_after(application())
    raw = first.state.model_dump(mode="python")
    raw["revision"] = 2000
    raw["head_event_id"] = "head-2000"
    application_template = first.state.applications[0].model_dump(mode="python")
    raw["applications"] = []
    for index in range(20):
        value = copy.deepcopy(application_template)
        value.update(
            id=f"app-cap-{index}",
            created_ref={
                "event_id": f"app-created-{index}",
                "revision": index * 3 + 1,
                "kind": "create_application",
            },
            status_ref={
                "event_id": f"app-status-{index}",
                "revision": index * 3 + 2,
                "kind": "set_planning_status",
            },
            latest_ref={
                "event_id": f"app-latest-{index}",
                "revision": index * 3 + 3,
                "kind": "set_personal_details",
            },
        )
        raw["applications"].append(value)
    template = first.state.document_tasks[0].model_dump(mode="python")
    bound = (
        binding_after(application())
        .state.document_tasks[0]
        .binding.model_dump(mode="python")
    )
    raw["document_tasks"] = []
    for index in range(400):
        value = copy.deepcopy(template)
        value.update(
            id=f"task-{index}",
            application_id=None,
            origin="source_reference",
            binding=copy.deepcopy(bound),
            created_ref={
                "event_id": f"created-{index}",
                "revision": 61 + index * 4,
                "kind": "bind_source_task",
            },
            binding_ref={
                "event_id": f"bound-{index}",
                "revision": 62 + index * 4,
                "kind": "rebind_source_task",
            },
            latest_ref={
                "event_id": "head-2000" if index == 399 else f"latest-{index}",
                "revision": 2000 if index == 399 else 64 + index * 4,
                "kind": "set_personal_details",
            },
        )
        value["report"] = {
            "state": "prepared_reported",
            "entered_at": None,
            "accepted_at": AT,
            "actor": context(1).actor.model_dump(),
            "event_ref": {
                "event_id": f"report-{index}",
                "revision": 63 + index * 4,
                "kind": "set_document_self_report",
            },
            "binding_digest_at_report": bound["binding_digest"],
            "origin": "applicant_report",
        }
        raw["document_tasks"].append(value)
    raw["active_preparation"] = {
        "origin": "g2",
        "policy": "follow_current_accepted",
        "observed_head": head().model_dump(mode="python"),
        "event_ref": {
            "event_id": "selector-1661",
            "revision": 1661,
            "kind": "select_active_preparation",
        },
    }
    batches = d.metadata_batches(raw)
    assert len(batches) <= 9 and max(map(len, batches)) <= 200
    flattened = [item for batch in batches for item in batch]
    assert len(flattened) == len(set(flattened)) == 1661
    assert len(batches) == 9 and len(batches[-1]) == 61
    assert "report-399" in flattened and "head-2000" in flattened


def test_six_ordered_lists_duplicate_indices_and_native_scope_omission_are_proof_identity():
    raw = checklist(
        admission_documents=[item(), item()],
        applicant_actions=[item()],
        ordered_steps=["A", "B"],
    )
    first = source_binding(raw)
    second = source_binding(raw, occurrences=[("admission_documents", 1)])
    assert first.occurrences[0].index == 0 and second.occurrences[0].index == 1
    assert first.occurrences[0].item_digest == second.occurrences[0].item_digest
    reversed_steps = checklist(
        admission_documents=[item(), item()],
        applicant_actions=[item()],
        ordered_steps=["B", "A"],
    )
    assert d.checklist_identity(raw)[0] != d.checklist_identity(reversed_steps)[0]
    assert "scope" not in s.RawDocumentChecklist.model_validate_json(
        json.dumps(raw)
    ).admission_documents[0].model_dump(mode="json")
    for location in d.CHECKLIST_LOCATIONS:
        changed = copy.deepcopy(raw)
        changed[location] = [item(name=f"Different {location}")]
        assert d.checklist_identity(changed)[0] != d.checklist_identity(raw)[0]
    stamped = copy.deepcopy(raw)
    stamped["generated_at"] = "2026-11-01T00:00:00Z"
    assert d.checklist_identity(stamped) == d.checklist_identity(raw)


def test_present_raw_url_bytes_change_proof_not_semantics_and_never_enter_binding_ack():
    absent_item = item()
    absent_item.pop("source_url")
    absent = source_binding(checklist(admission_documents=[absent_item]))
    null = source_binding(checklist(admission_documents=[item(source_url=None)]))
    normal = source_binding(
        checklist(admission_documents=[item(source_url="https://example.edu/public")])
    )
    unsafe_literal = " https://example.edu/auth?token=PRIVATE_TOKEN "
    blocked = source_binding(
        checklist(admission_documents=[item(source_url=unsafe_literal)])
    )
    assert absent.occurrences[0] == null.occurrences[0]
    assert (
        normal.occurrences[0].item_semantics_digest
        == blocked.occurrences[0].item_semantics_digest
    )
    assert (
        normal.occurrences[0].proof_reference_digest
        != blocked.occurrences[0].proof_reference_digest
    )
    first = binding_after(application(), binding=normal)
    assert "PRIVATE_TOKEN" not in first.receipt.model_dump_json()
    reasons = d.compare_binding(
        first.state.document_tasks[0].binding,
        blocked,
        evidence_reasons=["stale", "scope_unknown", "conflict"],
    )
    assert reasons[:4] == [
        "stale",
        "scope_unknown",
        "conflict",
        "proof_changed_item_same",
    ]
    assert (
        d.project_action_link(
            unsafe_literal,
            role="requirements_information",
            provenance="current_source",
            authorized_current_source=True,
        ).href
        is None
    )


def test_original_claim_order_scope_and_procedure_are_independent_identity_axes():
    raw = checklist(admission_documents=[item(claim_ids=["claim-a", "claim-b"])])
    initial = source_binding(raw)
    first = binding_after(application(), binding=initial)
    changed = source_binding(
        checklist(
            admission_documents=[item(claim_ids=["claim-b", "claim-a"])],
            ordered_steps=["Original B", "Original A"],
        )
    )
    reasons = d.compare_binding(
        first.state.document_tasks[0].binding, changed, evidence_reasons=[]
    )
    assert (
        "proof_changed_item_same" in reasons
        and "procedure_order_changed" in reasons
        and "item_changed" not in reasons
    )
    constraint = source_binding(checklist(admission_documents=[item(word_limit=250)]))
    assert "item_changed" in d.compare_binding(
        first.state.document_tasks[0].binding, constraint, evidence_reasons=[]
    )


def test_real_native_cross_list_projection_must_cover_all_original_occurrences():
    scope = ClaimScope(university="Synthetic", programme="Programme A")
    raw = checklist(
        admission_documents=[item(scope=scope)], applicant_actions=[item(scope=scope)]
    )
    graph = graph_for(raw)
    unique = source_binding(
        raw,
        occurrences=[("admission_documents", 0), ("applicant_actions", 0)],
        graph=graph,
    )
    assert unique.g1_relation == "exact_projection"
    assert unique.g1_document.action_id == graph.document_actions[0].id
    assert [ref.location for ref in unique.occurrences] == [
        "admission_documents",
        "applicant_actions",
    ]
    partial = source_binding(raw, graph=graph)
    assert (
        partial.g1_document is None
        and partial.g1_relation == "document_predicate_not_projected"
    )


def test_same_list_duplicate_native_nodes_do_not_guess_numeric_occurrence_by_name_or_hash():
    raw = checklist(admission_documents=[item(), item()])
    graph = graph_for(raw)
    for index in (0, 1):
        binding = source_binding(
            raw, occurrences=[("admission_documents", index)], graph=graph
        )
        assert (
            binding.g1_document is None
            and binding.g1_relation == "ambiguous_occurrence"
        )
        assert binding.occurrences[0].index == index


def test_actual_native_proof_change_is_hashed_without_copying_source_body_or_claiming_current_validity():
    scope = ClaimScope(university="Synthetic", programme="Programme A")
    raw = checklist(
        admission_documents=[item(scope=scope, claim_ids=["claim-synthetic"])]
    )
    claim = ClaimOut.model_validate(
        {
            "id": "claim-synthetic",
            "claim_type": "required_document",
            "normalized_value": "Transcript",
            "source_url": "https://example.edu/public/transcript",
            "official_domain": True,
            "accessed_at": AT,
            "status": "VERIFIED_CURRENT",
            "source_specificity": "program_intake",
            "original_text_excerpt": "Synthetic exact quotation not to be copied into G3",
            "scope": scope,
        }
    )
    initial = source_binding(raw, graph=graph_for(raw, claims=(claim,)))
    changed_claim = claim.model_copy(update={"is_stale": True, "age_days": 300})
    changed = source_binding(raw, graph=graph_for(raw, claims=(changed_claim,)))
    assert (
        initial.occurrences[0].item_semantics_digest
        == changed.occurrences[0].item_semantics_digest
    )
    assert (
        initial.occurrences[0].proof_reference_digest
        != changed.occurrences[0].proof_reference_digest
    )
    first = binding_after(application(), binding=initial)
    reasons = d.compare_binding(
        first.state.document_tasks[0].binding,
        changed,
        evidence_reasons=["stale", "scope_unknown"],
    )
    assert (
        "proof_changed_item_same" in reasons
        and "stale" in reasons
        and "scope_unknown" in reasons
    )
    assert "Synthetic exact quotation" not in first.receipt.model_dump_json()
    graph = graph_for(raw, claims=(claim,))
    forged_claim = claim.model_copy(update={"normalized_value": float("nan")})
    native_action = graph.document_actions[0]
    forged_proof = native_action.proofs[0].model_copy(update={"claim": forged_claim})
    forged_graph = graph.model_copy(
        update={
            "document_actions": [
                native_action.model_copy(update={"proofs": [forged_proof]})
            ]
        }
    )
    safe_error("source_unreadable", lambda: source_binding(raw, graph=forged_graph))


def test_scholarship_purpose_does_not_establish_named_award_document_validity():
    raw = checklist(
        admission_documents=[], scholarship_documents=[item(purpose="scholarship")]
    )
    binding = d.build_binding_selection(
        raw,
        profile_id=PROFILE,
        result_id="r-a",
        selected_occurrences=[("scholarship_documents", 0)],
        purpose="scholarship",
        award_id="award-a",
    )
    assert binding.award_relation == "unknown" and binding.g1_document is None
    transition = d.apply_action(
        None,
        request(
            "bind_source_task",
            application_id=None,
            source=binding.model_dump(mode="python"),
            source_preview_digest=DIGEST,
            personal=personal(),
        ),
        source_context(1, binding),
    )
    assert "award_relation_unknown" in d.compare_binding(
        transition.state.document_tasks[0].binding, binding, evidence_reasons=[]
    )


def test_personal_planning_status_and_document_details_have_only_their_own_mutation_refs():
    first = task_after(application())
    changed = d.apply_action(
        first.state,
        request(
            "set_planning_status", 2, 3, application_id="app-1", status="preparing"
        ),
        context(3),
    )
    assert changed.state.applications[0].status == "preparing"
    assert changed.receipt.affected_refs.document_task_ids == []
    edited = d.apply_action(
        changed.state,
        request(
            "set_personal_details",
            3,
            4,
            target={"kind": "document_task", "id": "task-2"},
            details=details("2026-10-20", None),
        ),
        context(4),
    )
    assert edited.state.document_tasks[0].personal.details.due.local_date == date(
        2026, 10, 20
    )
    assert edited.state.document_tasks[0].report == first.state.document_tasks[0].report
    assert edited.receipt.affected_refs.application_ids == []


def test_closed_action_link_output_rejects_tampered_token_href_even_when_other_fields_match():
    public = d.project_action_link(
        "https://example.edu/public",
        role="requirements_information",
        provenance="current_source",
        authorized_current_source=True,
    )
    with pytest.raises(ValidationError):
        s.ActionLinkReadV1.model_validate(
            {**public.model_dump(), "href": "https://example.edu/auth?token=PRIVATE"}
        )


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.edu/public",
        "HTTP://EXAMPLE.EDU:80/programme",
        "https://xn--e1afmkfd.edu/path",
        "https://example.edu:443/a%20b",
    ],
)
def test_lexical_public_actions_are_only_unverified_informational_links(raw):
    result = d.project_action_link(
        raw,
        role="programme_information",
        provenance="current_source",
        authorized_current_source=True,
    )
    if "%20" in raw:
        assert result.state == "blocked"  # Embedded decoded whitespace is conservative.
    else:
        assert result.state == "actionable_unverified" and result.href == raw
        assert result.destination_verification == "not_performed"


@pytest.mark.parametrize(
    "raw",
    [
        "https://0x7f.0x0.0x0.0x1/",
        "https://0177.0.0.1/",
        "https://2130706433/",
        "http://127.0.0.1/",
        "https://[::1]/",
        "https://localhost/",
        "https://u.local/",
        "https://u.internal/",
        "https://u.test/",
        "https://u.example/",
        "https://u.onion/",
        "https://éxample.edu/",
        "https://user:secret@example.edu/",
        "https://%65xample.edu/",
        "https://example.edu./",
        "https://example.edu:444/",
        "https://example.edu:0443/",
        "https://example.edu/?",
        "https://example.edu/#",
        "https://example.edu/token?secret=x",
        "https://example.edu/%6cogin",
        "https://example.edu/a%2Fb",
        "https://example.edu/%00",
        "https://example.edu/%5csecret",
        "https://example.edu/%zz",
        "https://example.edu/auth_token=SECRET",
        "https://example.edu/prefix-token=PRIVATE",
        "https://example.edu/prefix-%74oken=PRIVATE",
        "https://example.edu/prefix-token%3DPRIVATE",
        "https://example.edu/prefix-%74oken%3DPRIVATE",
        "https://example.edu/name-access_token%3DPRIVATE",
        "https://example.edu/path;token=SECRET",
        " https://example.edu/public",
        "/relative",
        "javascript:SECRET",
    ],
)
def test_blocked_links_emit_no_raw_literal_or_clickable_fallback(raw):
    result = d.project_action_link(
        raw,
        role="requirements_information",
        provenance="current_source",
        authorized_current_source=True,
    )
    assert result.state == "blocked" and result.href is None
    assert raw not in result.model_dump_json()
    assert "SECRET" not in result.model_dump_json()


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.edu/prefix-token=PRIVATE",
        "https://example.edu/prefix-%74oken%3DPRIVATE",
    ],
)
def test_embedded_token_literals_affect_original_proof_but_never_action_href_or_ack(
    raw,
):
    public = source_binding()
    private = source_binding(checklist(admission_documents=[item(source_url=raw)]))
    assert (
        public.occurrences[0].item_semantics_digest
        == private.occurrences[0].item_semantics_digest
    )
    assert (
        public.occurrences[0].proof_reference_digest
        != private.occurrences[0].proof_reference_digest
    )
    accepted = binding_after(application(), binding=private)
    assert (
        raw not in accepted.receipt.model_dump_json()
        and "PRIVATE" not in accepted.receipt.model_dump_json()
    )
    link = d.project_action_link(
        raw,
        role="requirements_information",
        provenance="current_source",
        authorized_current_source=True,
    )
    assert (
        link.state == "blocked"
        and link.href is None
        and raw not in link.model_dump_json()
    )
    with pytest.raises(ValidationError):
        s.ActionLinkReadV1.model_validate(
            {
                "role": "requirements_information",
                "provenance": "current_source",
                "destination_verification": "not_performed",
                "state": "actionable_unverified",
                "href": raw,
                "reason": "informational_unverified",
            }
        )
    # Do not silently second-decode a literal: the closed rule decodes exactly
    # once, and makes no promise about a destination's later interpretation.
    once_only = d.project_action_link(
        "https://example.edu/%256cogin",
        role="requirements_information",
        provenance="current_source",
        authorized_current_source=True,
    )
    assert (
        once_only.state == "actionable_unverified"
        and once_only.destination_verification == "not_performed"
    )


def test_locked_link_and_source_envelope_expose_no_new_presence_hash_or_reason():
    link = d.project_action_link(
        "https://example.edu/token?secret=PRIVATE",
        role="requirements_information",
        provenance="current_source",
        authorized_current_source=False,
    )
    assert (
        link.state == "not_available"
        and link.reason == "not_available"
        and link.href is None
    )
    source = s.SourceReadStatusV1(
        result_id="r-a",
        target_state="eligible",
        source_state="research_locked",
        observed_at=AT,
        current_digest=None,
        reasons=[],
    )
    assert source.current_digest is None and source.reasons == []
    with pytest.raises(ValidationError):
        s.SourceReadStatusV1.model_validate(
            {**source.model_dump(), "current_digest": DIGEST}
        )
    assert (
        d.project_action_link(
            "fixture://synthetic/demo", role="programme_information", provenance="demo"
        ).state
        == "demo_text"
    )


def head(origin: str = "g2", revision: int = 1):
    if origin == "g2":
        return s.G2HeadV1(
            profile_id=PROFILE,
            revision=revision,
            client_write_uuid=UUID(uuid(101)),
            snapshot_digest=DIGEST,
            allocation_digest=OTHER_DIGEST,
            accepted_at=AT,
        )
    if origin == "legacy_v2":
        return s.LegacyV2HeadV1(
            profile_id=PROFILE,
            revision=revision,
            persisted_sidecar_digest=DIGEST,
            draft_fingerprint=OTHER_DIGEST,
            legacy_fingerprint=DIGEST,
            observed_structural_fingerprint=OTHER_DIGEST,
        )
    return s.LegacyV1HeadV1(
        profile_id=PROFILE,
        revision=revision,
        saved_settings_digest=DIGEST,
        settings_fingerprint=OTHER_DIGEST,
    )


@pytest.mark.parametrize("origin", ["g2", "legacy_v2", "legacy_v1"])
def test_selector_uses_exact_native_observed_head_and_replay_is_original_after_advance(
    origin,
):
    native = head(origin)
    intent = request(
        "select_active_preparation",
        origin=origin,
        policy="follow_current_accepted",
        observed_head=native.model_dump(mode="python"),
    )
    selected = d.apply_action(
        None,
        intent,
        context(
            1,
            plan=d.PlanObservationV1(profile_id=PROFILE, state="readable", head=native),
        ),
    )
    assert selected.state.active_preparation.observed_head == native
    assert selected.receipt.affected_refs.active_selector_changed is True
    assert d.replay_receipt(PROFILE, intent, selected.receipt) == selected.receipt
    advanced = head(origin, 2)
    safe_error(
        "plan_head_changed",
        lambda: d.apply_action(
            None,
            intent,
            context(
                1,
                plan=d.PlanObservationV1(
                    profile_id=PROFILE, state="readable", head=advanced
                ),
            ),
        ),
    )
    bad = {**intent, "origin": "none", "observed_head": None}
    safe_error("input_invalid", lambda: d.validate_request(bad))


@pytest.mark.parametrize(
    "g2_current,g2_history,v2,v1,expected",
    [
        (False, True, True, True, "g2"),
        (True, False, True, True, "g2"),
        (False, False, True, True, "legacy_v2"),
        (False, False, False, True, "legacy_v1"),
        (False, False, False, False, "none"),
        (None, False, True, True, "unknown"),
        (False, False, None, True, "unknown"),
    ],
)
def test_derived_origin_uses_recorded_presence_and_never_corruption_fallback(
    g2_current, g2_history, v2, v1, expected
):
    presence = d.NativePresenceV1(
        g3_readable=True,
        g2_current_present=g2_current,
        g2_history_present=g2_history,
        legacy_v2_marker_present=v2,
        legacy_v1_row_present=v1,
    )
    assert d.choose_origin(None, presence) == expected
    assert (
        d.choose_origin(None, presence.model_copy(update={"g3_readable": False}))
        == "unknown"
    )


def active_plan(*, selection=None, actions=None, goals=None, unavailable=False):
    actions = actions or []
    native = head("g2", 2)
    return s.ActivePreparationReadV1(
        origin="g2",
        selection_source="accepted_g3_event"
        if selection is not None
        else "derived_backward_default",
        state="unavailable" if unavailable else "available",
        selection=selection,
        current_observed_head=None if unavailable else native,
        observed_at=AT,
        goal_result_ids=goals or [],
        study_actions=[] if unavailable else actions,
        allocated_minutes=None
        if unavailable
        else sum(item.planned_minutes for item in actions),
        needs_review=unavailable,
    )


def study(key: str, when: str, *, review=False):
    ref = (
        {
            "kind": "attempt_review",
            "id": f"attempt:{uuid(150)}",
            "attempt_id": uuid(150),
            "lesson_id": "ielts-reading-main-idea",
            "content_version": "1",
        }
        if review
        else {
            "kind": "lesson",
            "id": "lesson:ielts-reading-main-idea:1",
            "lesson_id": "ielts-reading-main-idea",
            "content_version": "1",
        }
    )
    return s.StudyActionReadV1.model_validate_json(
        json.dumps(
            {
                "id": key,
                "local_date": when,
                "timezone": "Asia/Almaty",
                "ref": ref,
                "planned_minutes": 20,
                "availability": "available",
                "completion": "not_projected",
            }
        ),
        strict=True,
    )


def today_input(state, *, plan=None, expired=False, **fields):
    return d.TodayComponentsV1(
        profile_id=PROFILE,
        as_of=AT,
        display_timezone="Asia/Almaty",
        action_state="readable" if state is not None else "absent",
        actions=state,
        action_observed_at=AT,
        active_plan=plan or active_plan(),
        preparation_access=s.PreparationAccessReadV1(
            allowed=not expired,
            reason="expired" if expired else "active",
            starts_at=datetime(2026, 10, 1, tzinfo=UTC),
            ends_at=datetime(2026, 10, 11 if expired else 31, tzinfo=UTC),
            development_only=False,
            observed_at=AT,
        ),
        source_statuses=[],
        initial_component_token=DIGEST,
        rechecked_component_token=DIGEST,
        research_access_after_recheck=True,
        **fields,
    )


def test_today_preserves_one_accepted_slot_order_and_unknown_document_workload():
    first = task_after(application(), details=details("2026-10-12", None))
    plan = active_plan(
        actions=[
            study("study-b", "2026-10-12"),
            study("study-a", "2026-10-12"),
            study("future-b", "2026-10-13"),
            study("future-a", "2026-10-13"),
        ]
    )
    result = d.project_today(today_input(first.state, plan=plan))
    assert [card.id for card in result.today_study] == ["study-b", "study-a"]
    assert [card.id for card in result.future] == ["future-b", "future-a"]
    assert result.today_personal[0].planned_minutes is None
    assert result.today_personal[0].date.fallback_display_only is True
    assert result.today_personal[0].date.official_closure == "not_assessed"
    assert (
        result.allocated_study_minutes == 80
        and result.personal_minutes == "not_estimated"
    )
    assert result.readiness == "not_assessed"


def test_today_selected_plan_failure_preserves_personal_actions_and_unknown_workload():
    first = task_after(application())
    result = d.project_today(
        today_input(first.state, plan=active_plan(unavailable=True), expired=True)
    )
    assert result.active_plan.origin == "g2" and result.workload == "unknown"
    assert result.allocated_study_minutes is None and result.today_study == []
    assert {card.id for card in result.undated_personal} == {
        "application:app-1",
        "document:task-2",
    }
    assert all(card.actionable for card in result.undated_personal)


def test_today_expiry_blocks_new_lesson_but_keeps_exact_own_review_target_readable():
    plan = active_plan(
        actions=[
            study("lesson", "2026-10-12"),
            study("review", "2026-10-12", review=True),
        ]
    )
    result = d.project_today(today_input(application().state, plan=plan, expired=True))
    assert [card.actionable for card in result.today_study] == [False, True]
    assert result.today_study[1].target.id == f"attempt:{uuid(150)}"
    forged = plan.model_dump(mode="python")
    forged["study_actions"][0]["ref"]["id"] = "lesson:guessed:1"
    safe_error(
        "saved_unreadable",
        lambda: d.project_today(
            {
                **today_input(application().state).model_dump(mode="python"),
                "active_plan": forged,
            }
        ),
    )


def test_today_one_recheck_withholds_mixed_actions_and_revoked_source_details():
    first = binding_after(application())
    source = s.SourceReadStatusV1(
        result_id="r-a",
        target_state="eligible",
        source_state="current_reference",
        observed_at=AT,
        current_digest=DIGEST,
        reasons=["scope_unknown"],
    )
    raw = today_input(first.state).model_dump(mode="python")
    raw.update(
        source_statuses=[source],
        rechecked_component_token=OTHER_DIGEST,
        research_access_after_recheck=False,
    )
    result = d.project_today(raw)
    assert result.consistency == "mixed_revision" and result.needs_refresh is True
    assert (
        result.today_study
        == result.today_personal
        == result.future
        == result.undated_personal
        == []
    )
    assert result.application_summaries == first.state.applications
    assert result.current_source_statuses[0].source_state == "research_locked"
    assert (
        result.current_source_statuses[0].current_digest is None
        and result.current_source_statuses[0].reasons == []
    )


def test_today_separate_twenty_source_and_twenty_native_goal_sets_allow_forty_union():
    first = application()
    raw = first.state.model_dump(mode="python")
    template = raw["applications"][0]
    raw["applications"] = [
        {
            **copy.deepcopy(template),
            "id": f"app-{index}",
            "target": target(f"g3-{index}"),
        }
        for index in range(20)
    ]
    state = s.CaseActionsStateV1.model_validate(raw)
    plan = active_plan(goals=[f"g2-{index}" for index in range(20)])
    result = d.project_today(today_input(state, plan=plan))
    assert (
        len(result.application_summaries) == 20
        and len(result.active_plan.goal_result_ids) == 20
    )
    assert (
        result.workload == "one_selected_plan"
    )  # Empty known accepted ledger is zero.


def test_date_only_due_and_dst_day_use_explicit_zones_without_official_urgency():
    first = task_after(application(), details=details("2026-11-01", "America/New_York"))
    raw = today_input(first.state).model_dump(mode="python")
    raw.update(
        as_of=datetime(2026, 11, 1, 4, 30, tzinfo=UTC),
        display_timezone="America/New_York",
    )
    result = d.project_today(raw)
    assert result.today_personal[0].date.local_date == date(2026, 11, 1)
    assert result.today_personal[0].date.official_closure == "not_assessed"
    assert result.overdue_personal == []


def test_unreadable_g3_today_is_unavailable_not_revision_zero_or_legacy_fallback():
    unknown = s.ActivePreparationReadV1(
        origin="unknown",
        selection_source="unavailable",
        state="unavailable",
        selection=None,
        current_observed_head=None,
        observed_at=AT,
        goal_result_ids=[],
        study_actions=[],
        allocated_minutes=None,
        needs_review=True,
    )
    raw = today_input(None, plan=unknown).model_dump(mode="python")
    raw["action_state"] = "unavailable"
    result = d.project_today(raw)
    assert result.action_state == "unavailable" and result.action_revision is None
    assert result.active_plan.origin == "unknown" and result.workload == "unknown"
    assert "actions_unavailable" in [notice.code for notice in result.notices]
    raw["active_plan"] = active_plan().model_dump(mode="python")
    safe_error("saved_unreadable", lambda: d.project_today(raw))


def test_personal_creation_rehashed_receipt_cannot_inject_an_earlier_reviewed_source_binding():
    bound = binding_after(application())
    accepted = d.apply_action(
        bound.state,
        request("create_personal_task", 2, 3, application_id=None, personal=personal()),
        context(3),
    )
    original = accepted.receipt.model_dump(mode="json")
    assert (
        d.replay_receipt(PROFILE, bound.receipt.request, bound.receipt) == bound.receipt
    )
    assert (
        d.replay_receipt(PROFILE, accepted.receipt.request, accepted.receipt)
        == accepted.receipt
    )
    forged = copy.deepcopy(original)
    earlier = bound.state.document_tasks[0].model_dump(mode="json")
    created = forged["applied_delta"]["document_tasks"][0]
    created.update(
        binding=earlier["binding"],
        binding_ref=earlier["binding_ref"],
        origin="source_reference",
    )
    # This copied old binding is otherwise a structurally valid own task; the
    # rejected shape is the personal-command-to-delta semantic contradiction.
    assert s.DocumentTaskV1.model_validate_json(json.dumps(created)).binding is not None
    unsigned = {key: value for key, value in forged.items() if key != "receipt_digest"}
    forged["receipt_digest"] = hashlib.sha256(
        json.dumps(
            {"schema_version": "g3-action-receipt-digest-v1", "receipt": unsigned},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    safe_error(
        "saved_unreadable",
        lambda: d.replay_receipt(PROFILE, accepted.receipt.request, forged),
    )
    assert accepted.receipt.model_dump(mode="json") == original


@pytest.mark.parametrize("application_id,task_id", [("a", "z"), ("z", "a")])
@pytest.mark.parametrize(
    "due,partition",
    [
        (None, "undated_personal"),
        ("2026-10-11", "overdue_personal"),
        ("2026-10-12", "today_personal"),
        ("2026-10-13", "future"),
    ],
)
def test_today_combined_personal_record_ids_are_stable_across_entity_types(
    application_id, task_id, due, partition
):
    entered_details = details(due)
    first = d.apply_action(
        None,
        request(
            "create_application",
            target=target(),
            label="Entered A",
            details=entered_details,
        ),
        context(1, new_application_id=application_id, target=observation()),
    )
    second = d.apply_action(
        first.state,
        request(
            "create_personal_task",
            1,
            2,
            application_id=application_id,
            personal=personal(details=entered_details),
        ),
        context(2, new_task_id=task_id),
    )
    result = d.project_today(today_input(second.state))
    cards = getattr(result, partition)
    assert [card.target.id for card in cards] == ["a", "z"]
    assert {card.target.kind for card in cards} == {"application", "document_task"}
    assert all(card.planned_minutes is None for card in cards)


def test_today_future_preserves_study_before_stable_personal_actions_on_equal_dates():
    first = d.apply_action(
        None,
        request(
            "create_application",
            target=target(),
            label="Entered A",
            details=details("2026-10-13"),
        ),
        context(1, new_application_id="a", target=observation()),
    )
    second = d.apply_action(
        first.state,
        request(
            "create_personal_task",
            1,
            2,
            application_id="a",
            personal=personal(details=details("2026-10-13")),
        ),
        context(2, new_task_id="z"),
    )
    plan = active_plan(
        actions=[study("study-z", "2026-10-13"), study("study-a", "2026-10-13")]
    )
    result = d.project_today(today_input(second.state, plan=plan))
    assert [card.id for card in result.future] == [
        "study-z",
        "study-a",
        "application:a",
        "document:z",
    ]
    assert result.allocated_study_minutes == 40
