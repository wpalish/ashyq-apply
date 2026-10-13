"""Native own metadata/context/removal history. All input and identities synthetic."""

from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.domain import admissions_actions as d
from app.schemas import admissions_actions as s
from tests.test_admissions_actions import context
from tests.test_admissions_actions_api import (
    accepted,
    command,
    details,
    endpoint,
    personal,
    preview_source,
    safe_error,
    seed_source,
    target,
)
from tests.test_admissions_actions_concurrency import migrate, stored
from tests.test_manual_admissions_actions import manual, post, read
from tests.test_preparation_graph_api import _foreign_case, _selected

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")


def metadata(task_id, revision, *, application_id=None, value=None):
    return command(
        "set_personal_details",
        revision,
        schema_version="admissions-actions-v2",
        operation="document_metadata",
        target={"kind": "document_task", "id": task_id},
        application_id=application_id,
        personal=value or personal(),
        confirmed_personal_metadata=True,
    )


def change_context(app_id, revision, application_target, *, label="Synthetic updated application"):
    return command(
        "set_personal_details",
        revision,
        schema_version="admissions-actions-v2",
        operation="application_context",
        target={"kind": "application", "id": app_id},
        application_target=application_target,
        label=label,
        details=details(),
        confirmed_personal_context=True,
    )


def remove(kind, record_id, revision):
    return command(
        "remove_personal_action",
        revision,
        schema_version="admissions-actions-v2",
        target={"kind": kind, "id": record_id},
        confirmed_personal_removal=True,
    )


def test_pure_last_removal_has_own_head_and_original_receipt_replay():
    first_body = command("create_personal_task", application_id=None, personal=personal())
    first = d.apply_action(None, first_body, context(1))
    body = remove("document_task", first.state.document_tasks[0].id, 1)
    second = d.apply_action(first.state, body, context(2))
    assert isinstance(second.state, s.EditedCaseActionsStateV2)
    assert second.state.applications == second.state.document_tasks == []
    assert second.state.head_ref.kind == "remove_personal_action"
    assert second.receipt.applied_delta.removed_document_task == first.state.document_tasks[0]
    assert second.receipt.before_state_digest == s.state_digest(first.state)
    assert d.replay_receipt("case-synthetic", body, second.receipt) == second.receipt
    assert d.validate_complete_export(
        second.state, [first.receipt, second.receipt], profile_id="case-synthetic"
    ) == [first.receipt, second.receipt]


def test_native_metadata_context_review_detach_remove_empty_current_history_export(
    shared_route_lab,
):
    lab = shared_route_lab
    first = post(lab, manual())
    app_id = first["applied_delta"]["applications"][0]["id"]
    created = post(
        lab, command("create_personal_task", 1, application_id=app_id, personal=personal())
    )
    task_id = created["applied_delta"]["document_tasks"][0]["id"]
    reported = post(
        lab,
        command(
            "set_document_self_report",
            2,
            task_id=task_id,
            report={
                "state": "prepared_reported",
                "entered_at": None,
                "confirmed_personal_report": True,
            },
        ),
    )
    task = reported["applied_delta"]["document_tasks"][0]
    revised_personal = deepcopy(task["personal"])
    revised_personal.update(label="Synthetic renamed transcript", responsible_actor="school")
    edited = post(lab, metadata(task_id, 3, application_id=app_id, value=revised_personal))
    after_task = edited["applied_delta"]["document_tasks"][0]
    assert after_task["id"] == task_id and after_task["created_ref"] == task["created_ref"]
    assert after_task["report"] == task["report"] and after_task["binding"] == task["binding"]
    new_target = deepcopy(first["request"]["target"])
    new_target["intake"] = {"state": "applicant_entered", "value": "Synthetic different intake"}
    context_receipt = post(lab, change_context(app_id, 4, new_target))
    current = read(lab)
    assert current["document_report_reviews"] == [
        {"task_id": task_id, "reasons": ["application_context_changed"]}
    ]
    assert current["state"]["document_tasks"][0]["report"] == task["report"]
    assert (
        current["state"]["applications"][0]["context_ref"]["event_id"]
        == context_receipt["event_id"]
    )
    today = lab["client"].get(f"/api/profiles/{lab['case']}/today")
    assert today.status_code == 200, today.text
    cards = (
        today.json()["undated_personal"]
        + today.json()["future"]
        + today.json()["today_personal"]
        + today.json()["overdue_personal"]
    )
    card = next(item for item in cards if item["target"]["id"] == task_id)
    assert "application_context_changed" in card["dependency_reasons"]
    before = stored(lab)
    safe_error(
        lab["client"].post(endpoint(lab) + "/commands", json=remove("application", app_id, 5)),
        "linked_documents",
    )
    assert stored(lab) == before
    detached = post(lab, metadata(task_id, 5, value=revised_personal))
    removed_app = post(lab, remove("application", app_id, 6))
    removed_task = post(lab, remove("document_task", task_id, 7))
    assert removed_task["applied_delta"]["removed_document_task"]["report"] == task["report"]
    final = read(lab)
    assert (
        final["revision"] == 8
        and final["state"]["applications"] == final["state"]["document_tasks"] == []
    )
    receipts = [
        first,
        created,
        reported,
        edited,
        context_receipt,
        detached,
        removed_app,
        removed_task,
    ]
    assert post(lab, removed_task["request"]) == removed_task
    assert post(lab, first["request"]) == first
    assert lab["client"].get(endpoint(lab) + "/events").json()["events"] == receipts
    exported = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert exported.status_code == 200, exported.text
    assert exported.json()["admissions_actions"]["current"] == final["state"]
    assert exported.json()["admissions_actions"]["events"] == receipts
    assert len(stored(lab)["events"]) == 8


def test_native_context_keeps_old_binding_and_report_until_explicit_compatible_rebind(
    shared_route_lab,
):
    lab = shared_route_lab
    result_a = seed_source(lab)
    result_b, _, _ = _selected(lab, decision="maybe", value=7.0)
    first = accepted(
        lab,
        command(
            "create_application",
            target=target(result_a),
            label="Synthetic source application",
            details=details(),
        ),
    )
    app_id = first["applied_delta"]["applications"][0]["id"]
    preview = preview_source(lab, result_a)
    linked = accepted(
        lab,
        command(
            "bind_source_task",
            1,
            application_id=app_id,
            source=preview["selection"],
            source_preview_digest=preview["source_preview_digest"],
            personal=personal(),
        ),
    )
    task_id = linked["applied_delta"]["document_tasks"][0]["id"]
    report = post(
        lab,
        command(
            "set_document_self_report",
            2,
            task_id=task_id,
            report={
                "state": "prepared_reported",
                "entered_at": None,
                "confirmed_personal_report": True,
            },
        ),
    )
    old_task = report["applied_delta"]["document_tasks"][0]
    moved = post(lab, change_context(app_id, 3, target(result_b)))
    current = read(lab)
    assert current["state"]["document_tasks"][0]["binding"] == old_task["binding"]
    assert current["state"]["document_tasks"][0]["report"] == old_task["report"]
    assert "application_context_changed" in current["document_report_reviews"][0]["reasons"]
    assert {item["result_id"] for item in current["current_source_statuses"]} == {
        result_a,
        result_b,
    }
    assert moved["applied_delta"]["applications"][0]["target"]["result_id"] == result_b
    # An unrelated metadata edit cannot silently link this retained old binding to another target.
    other = post(lab, manual(4))
    other_id = other["applied_delta"]["applications"][0]["id"]
    safe_error(
        lab["client"].post(
            endpoint(lab) + "/commands", json=metadata(task_id, 5, application_id=other_id)
        ),
        "invalid_transition",
    )


def test_native_declared_target_is_not_silently_moved_by_context_edit(shared_route_lab):
    lab = shared_route_lab
    first = post(lab, manual())
    app_id = first["applied_delta"]["applications"][0]["id"]
    declared = post(
        lab,
        command(
            "declare_submission",
            1,
            application_id=app_id,
            submission={
                "entered_at": {"local_date": "2026-10-10", "local_time": None, "timezone": None},
                "channel": "Synthetic own portal statement",
                "reference": "",
                "document_task_ids": [],
                "confirmed_applicant_declaration": True,
            },
        ),
    )
    changed = deepcopy(first["request"]["target"])
    changed["university"] = "Synthetic another university"
    before = stored(lab)
    safe_error(
        lab["client"].post(endpoint(lab) + "/commands", json=change_context(app_id, 2, changed)),
        "declared_context_locked",
    )
    assert stored(lab) == before
    renamed = post(lab, change_context(app_id, 2, first["request"]["target"]))
    app = renamed["applied_delta"]["applications"][0]
    assert (
        app["status"] == "submitted_declared"
        and app["status_ref"]["event_id"] == declared["event_id"]
    )
    assert app["context_ref"] is None


@pytest.mark.parametrize(
    "failure", ["foreign_record", "foreign_dependency", "self_dependency", "unconfirmed", "stale"]
)
def test_native_metadata_failures_have_no_mutation(shared_route_lab, failure):
    lab = shared_route_lab
    created = accepted(
        lab, command("create_personal_task", application_id=None, personal=personal())
    )
    task_id = created["applied_delta"]["document_tasks"][0]["id"]
    body = metadata(task_id, 1)
    code = "record_not_found"
    if failure == "foreign_record":
        body["target"]["id"] = uuid4().hex
    elif failure == "foreign_dependency":
        body["personal"]["depends_on_task_ids"] = [uuid4().hex]
    elif failure == "self_dependency":
        body["personal"]["depends_on_task_ids"] = [task_id]
        code = "input_invalid"
    elif failure == "unconfirmed":
        body["confirmed_personal_metadata"] = False
        code = "input_invalid"
    else:
        body["expected_revision"] = 0
        code = "revision_conflict"
    before = stored(lab)
    safe_error(lab["client"].post(endpoint(lab) + "/commands", json=body), code)
    assert stored(lab) == before
    foreign = _foreign_case(lab)
    assert (
        lab["client"]
        .post(endpoint(lab, foreign) + "/commands", json=metadata(task_id, 1))
        .status_code
        == 404
    )


def test_native_removed_dependency_is_visible_and_personal_ids_not_reused(shared_route_lab):
    lab = shared_route_lab
    first = accepted(lab, command("create_personal_task", application_id=None, personal=personal()))
    first_id = first["applied_delta"]["document_tasks"][0]["id"]
    second = accepted(
        lab,
        command(
            "create_personal_task",
            1,
            application_id=None,
            personal=personal(dependencies=[first_id]),
        ),
    )
    second_id = second["applied_delta"]["document_tasks"][0]["id"]
    removed = post(lab, remove("document_task", first_id, 2))
    safe_error(
        lab["client"].post(endpoint(lab) + "/commands", json=remove("document_task", first_id, 3)),
        "record_not_found",
    )
    assert post(lab, removed["request"]) == removed
    today = lab["client"].get(f"/api/profiles/{lab['case']}/today")
    assert today.status_code == 200, today.text
    card = next(
        item for item in today.json()["undated_personal"] if item["target"]["id"] == second_id
    )
    assert "dependency_missing" in card["dependency_reasons"]
    new = post(lab, command("create_personal_task", 3, application_id=None, personal=personal()))
    assert new["applied_delta"]["document_tasks"][0]["id"] not in {first_id, second_id}


def test_native_migration_retains_old_v2_and_refuses_extended_rollback(shared_route_lab):
    lab = shared_route_lab
    old = post(lab, manual())
    before = stored(lab)
    migrate(lab, "f9c83e902026", downgrade=True)
    migrate(lab, "a0d94e902027")
    assert stored(lab) == before
    assert post(lab, old["request"]) == old
    app_id = old["applied_delta"]["applications"][0]["id"]
    post(lab, remove("application", app_id, 1))
    after = stored(lab)
    with pytest.raises(RuntimeError, match="schema rollback refused"):
        migrate(lab, "f9c83e902026", downgrade=True)
    assert stored(lab) == after
    assert len(inspect(lab["engine"]).get_check_constraints("admissions_actions_events")) == 3


def test_pure_original_v1_class_remains_closed_to_extended_removal_request():
    body = remove("document_task", "synthetic-task", 1)
    assert isinstance(d.validate_request(body), s.RemovePersonalActionV2)
    body["schema_version"] = "admissions-actions-v1"
    with pytest.raises(d.ActionError):
        d.validate_request(body)
