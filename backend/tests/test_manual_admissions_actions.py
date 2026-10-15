"""Native G3 V1/V2 compatibility, manual context and ownership controls.

All cases are synthetic; no research/provider/network operation is permitted.
"""

from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect

from app.domain import admissions_actions as d
from app.schemas import admissions_actions as s
from tests.test_admissions_actions import context, details
from tests.test_admissions_actions_api import (
    accepted,
    command,
    endpoint,
    personal,
    safe_error,
    seed_source,
    target,
)
from tests.test_admissions_actions_concurrency import migrate, stored
from tests.test_preparation_graph_api import _foreign_case

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")


def manual(revision=0, **changes):
    return command(
        "create_application",
        revision,
        schema_version="admissions-actions-v2",
        target={
            "university": "Synthetic manually entered university",
            "programme": {"state": "unknown"},
            "award": {"state": "unknown"},
            "purpose": "admission",
            "intake": {"state": "applicant_entered", "value": "Synthetic 2027 intake"},
            "route": {"state": "unknown"},
            "confirmed_entered_context": True,
        },
        label="Synthetic manual application",
        details=details("2027-01-15"),
        **changes,
    )


def post(lab, body):
    response = lab["client"].post(endpoint(lab) + "/commands", json=body)
    assert response.status_code == 200, response.text
    receipt = d.validate_receipt(response.json())
    assert receipt.profile_id == lab["case"]
    assert receipt.request == d.validate_request(body)
    assert receipt.receipt_digest == s.receipt_digest(receipt)
    return response.json()


def read(lab):
    response = lab["client"].get(endpoint(lab))
    assert response.status_code == 200, response.text
    value = response.json()
    state = d.validate_state(value["state"])
    assert value["head_receipt"]["after_state_digest"] == s.state_digest(state)
    return value


def test_manual_pure_target_has_no_evidence_identity_or_verification():
    body = manual()
    transition = d.apply_action(None, body, context(1))
    record = transition.state.applications[0]
    assert isinstance(transition.state, s.CaseActionsStateV2)
    assert isinstance(record, s.ManualApplicationRecordV2)
    assert record.target.result_id is None and record.target.award_id is None
    assert record.target.programme.state == "unknown"
    assert record.target.official_verification == "not_performed"
    assert s.source_target_ids(transition.state) == []
    assert d.replay_receipt("case-synthetic", body, transition.receipt) == transition.receipt
    with pytest.raises(ValidationError):
        s.ActionWriteReceiptV1.model_validate(transition.receipt.model_dump(mode="json"))
    with pytest.raises(ValidationError):
        s.ApplicationTargetV1.model_validate(record.target.model_dump(mode="json"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("result_id", "synthetic-foreign-result"),
        ("award_id", "synthetic-award-reference"),
        ("official_verification", "performed"),
        ("confirmed_entered_context", False),
        ("university", ""),
        ("university", 123),
        ("programme", {"state": "verified", "value": "Synthetic programme"}),
        ("award", {"state": "applicant_entered", "value": "Synthetic admission award"}),
    ],
)
def test_manual_target_rejects_forged_or_unconfirmed_context(field, value):
    body = manual()
    body["target"][field] = value
    with pytest.raises(d.ActionError) as failure:
        d.validate_request(body)
    assert failure.value.detail["code"] == "admissions_actions_input_invalid"


def test_manual_requires_explicit_version_and_keeps_closed_v1():
    body = manual()
    body.pop("schema_version")
    with pytest.raises(d.ActionError):
        d.validate_request(body)
    body["schema_version"] = "admissions-actions-v1"
    with pytest.raises(d.ActionError):
        d.validate_request(body)
    body["schema_version"] = "admissions-actions-v2"
    body["target"]["purpose"] = "scholarship"
    body["target"]["award"] = {
        "state": "applicant_entered",
        "value": "Synthetic named award",
    }
    assert isinstance(d.validate_request(body), s.CreateManualApplicationV2)


def test_native_manual_without_research_current_today_history_export_delete(
    shared_route_lab,
):
    lab = shared_route_lab
    queried = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        queried.append(statement.lower())

    event.listen(lab["engine"], "before_cursor_execute", capture)
    try:
        first = post(lab, manual())
        value = read(lab)
        today = lab["client"].get(f"/api/profiles/{lab['case']}/today")
        assert today.status_code == 200, today.text
    finally:
        event.remove(lab["engine"], "before_cursor_execute", capture)
    assert not any("from program_results" in sql or "from claims" in sql for sql in queried)
    assert value["current_source_statuses"] == value["action_links"] == []
    summary = today.json()["application_summaries"][0]
    assert summary == value["state"]["applications"][0]
    cards = (
        today.json()["future"] + today.json()["today_personal"] + today.json()["overdue_personal"]
    )
    card = next(item for item in cards if item["target"]["id"] == summary["id"])
    assert card["target_result_id"] is None and card["source_state"] == "applicant_entered"
    replay = post(lab, first["request"])
    assert replay == first and len(stored(lab)["events"]) == 1
    history = lab["client"].get(endpoint(lab) + "/events").json()
    assert history["events"] == [first]
    export = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert export.status_code == 200, export.text
    assert export.json()["admissions_actions"]["current"] == value["state"]
    assert export.json()["admissions_actions"]["events"] == [first]
    response = lab["client"].delete(f"/api/profiles/{lab['case']}")
    assert response.status_code == 204, response.text
    assert stored(lab) == {"current": None, "events": []}


def test_native_mixed_history_original_v1_replay_and_manual_declaration_correction(
    shared_route_lab,
):
    lab = shared_route_lab
    result_id = seed_source(lab)
    first = accepted(
        lab,
        command(
            "create_application",
            target=target(result_id),
            label="Synthetic evidence application",
            details=details(),
        ),
    )
    second = post(lab, manual(1))
    app_id = second["applied_delta"]["applications"][0]["id"]
    third = post(
        lab,
        command("create_personal_task", 2, application_id=app_id, personal=personal()),
    )
    task_id = third["applied_delta"]["document_tasks"][0]["id"]
    submission = post(
        lab,
        command(
            "declare_submission",
            3,
            application_id=app_id,
            submission={
                "entered_at": {
                    "local_date": "2026-10-10",
                    "local_time": None,
                    "timezone": None,
                },
                "channel": "Synthetic applicant declaration",
                "reference": "",
                "document_task_ids": [task_id],
                "confirmed_applicant_declaration": True,
            },
        ),
    )
    correction = post(
        lab,
        command(
            "correct_declaration",
            4,
            application_id=app_id,
            prior_declaration={
                "event_id": submission["event_id"],
                "revision": 4,
                "kind": "declare_submission",
            },
            replacement={"kind": "planning", "status": "preparing"},
            confirmed_correction=True,
        ),
    )
    latest = post(
        lab,
        command(
            "set_personal_details",
            5,
            target={"kind": "application", "id": app_id},
            details=details("2027-02-01", "America/New_York"),
        ),
    )
    receipts = [first, second, third, submission, correction, latest]
    assert post(lab, first["request"]) == first
    assert first["schema_version"] == "admissions-actions-v1"
    assert all(item["schema_version"] == "admissions-actions-v2" for item in receipts[1:])
    assert third["request"]["schema_version"] == "admissions-actions-v1"
    state = read(lab)["state"]
    assert len(state["applications"]) == 2
    assert state["applications"][1]["status"] == "preparing"
    assert (
        state["applications"][1]["target"]["university"]
        == second["request"]["target"]["university"]
    )
    assert lab["client"].get(endpoint(lab) + "/events").json()["events"] == receipts
    export = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert export.status_code == 200, export.text
    assert export.json()["admissions_actions"]["events"] == receipts
    # The existing export preserves the entire accepted event, not only its declaration delta.
    assert export.json()["admissions_actions"]["submission_declarations"] == [submission]
    assert submission["applied_delta"]["declaration"]["official_verification"] == "not_performed"


def test_native_manual_cas_uuid_foreign_and_corrupt_receipt(shared_route_lab):
    lab = shared_route_lab
    body = manual()
    first = post(lab, body)
    before = stored(lab)
    altered = deepcopy(first["request"])
    altered["label"] = "Synthetic changed UUID body"
    safe_error(lab["client"].post(endpoint(lab) + "/commands", json=altered), "uuid_conflict")
    safe_error(
        lab["client"].post(endpoint(lab) + "/commands", json=manual()),
        "revision_conflict",
    )
    foreign = _foreign_case(lab)
    foreign_response = lab["client"].post(endpoint(lab, foreign) + "/commands", json=manual())
    assert foreign_response.status_code == 404
    app_id = first["applied_delta"]["applications"][0]["id"]
    safe_error(
        lab["client"].post(
            endpoint(lab) + "/commands",
            json=command("set_planning_status", 1, application_id=uuid4().hex, status="preparing"),
        ),
        "record_not_found",
    )
    assert stored(lab) == before
    forged = deepcopy(first)
    forged["applied_delta"]["applications"][0]["id"] = app_id + "x"
    with pytest.raises(d.ActionError):
        d.validate_receipt(forged)


def test_native_migration_preserves_v1_rows_and_refuses_lossy_v2_downgrade(
    shared_route_lab,
):
    lab = shared_route_lab
    first = accepted(lab, command("create_personal_task", application_id=None, personal=personal()))
    before = stored(lab)
    migrate(lab, "e8b72e902025", downgrade=True)
    migrate(lab, "f9c83e902026")
    assert stored(lab) == before
    assert accepted(lab, first["request"]) == first
    post(lab, manual(1))
    newer = stored(lab)
    with pytest.raises(RuntimeError, match="schema rollback refused"):
        migrate(lab, "e8b72e902025", downgrade=True)
    assert stored(lab) == newer
    assert len(inspect(lab["engine"]).get_check_constraints("admissions_actions_events")) == 3


def test_manual_application_limit_is_same_twenty_total():
    state = None
    for index in range(1, 21):
        body = manual(index - 1)
        state = d.apply_action(state, body, context(index)).state
    with pytest.raises(d.ActionError) as failure:
        d.apply_action(state, manual(20), context(21))
    assert failure.value.detail["code"] == "admissions_actions_limit_exceeded"


def test_v2_receipt_rejects_different_target_even_with_recomputed_self_hash():
    transition = d.apply_action(None, manual(), context(1))
    forged = transition.receipt.model_dump(mode="python")
    forged["applied_delta"]["applications"][0]["target"]["university"] = (
        "Synthetic other university"
    )
    forged["receipt_digest"] = s.reference_digest(
        "g3-action-receipt-digest-v1",
        {"receipt": {k: v for k, v in forged.items() if k != "receipt_digest"}},
    )
    with pytest.raises(d.ActionError):
        d.validate_receipt(forged)
