"""G3 HTTP controls on the native migrated SQLite/private PostgreSQL lab.

All identities, checklist contents and applicant declarations are synthetic.
These controls exercise the actual transport and stored rows, not a substitute
guard, allocator or mocked transition. Their external author has not imported,
collected or run this source. Writer races have a separate additive test file.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, event

from app.domain import admissions_actions as d
from app.models import (
    AuthSession,
    Entitlement,
    OrganizationMembership,
    ProgramResultRow,
    ResearchRun,
    Subscription,
    User,
)
from app.models.admissions_actions import AdmissionsActionsCurrentRow, AdmissionsActionsEventRow
from app.models.base import utcnow
from app.schemas import admissions_actions as s
from app.schemas.result import DocumentChecklist, DocumentItem, Scholarship
from app.security import DEV_ORGANIZATION_ID, DEV_USER_ID, token_hash
from app.settings import get_settings
from tests.test_admissions_actions_concurrency import (
    create_profile_only,
    current_values,
    event_values,
    native_snapshot,
    stored,
    wire_values,
)
from tests.test_preparation_api import full_case, grant
from tests.test_preparation_graph_api import _capture, _foreign_case, _selected
from tests.test_preparation_write_concurrency import enable_native_auth
from tests.test_shared_route_api import assert_no_dml, assert_no_premium_reads
from tests.test_study_schedule_api import write as write_schedule

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")

PRIVATE_MARKER = "SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO"
SOURCE_MARKER = "SYNTHETIC_SOURCE_BODY_DO_NOT_COPY"
CURRENT_KEYS = {
    "profile_id", "revision", "state", "head_receipt", "observed_at",
    "current_source_statuses", "document_report_reviews", "action_links",
}


def endpoint(lab, case=None):
    return f"/api/profiles/{case or lab['case']}/admissions-actions"


def command(kind, revision=0, *, write_uuid=None, **fields):
    return {
        "kind": kind,
        "expected_revision": revision,
        "client_write_uuid": write_uuid or str(uuid4()),
        **fields,
    }


def details(*, due=None, notes="Synthetic personal note"):
    return {"due": due, "notes": notes}


def personal(*, label="Synthetic applicant task", due=None, dependencies=None):
    return {
        "label": label,
        "responsible_actor": "applicant",
        "details": details(due=due),
        "depends_on_task_ids": list(dependencies or []),
    }


def target(result_id):
    return {
        "result_id": result_id, "purpose": "admission", "award_id": None,
        "intake": {"state": "unknown"},
        "route": {"state": "applicant_entered", "value": "Synthetic reviewed route"},
        "confirmed_entered_context": True,
    }


def accepted(lab, payload):
    response = lab["client"].post(endpoint(lab) + "/commands", json=payload)
    assert response.status_code == 200, response.text
    value = response.json()
    receipt = s.ActionWriteReceiptV1.model_validate(value)
    assert set(value) == set(s.ActionWriteReceiptV1.model_fields)
    assert receipt.profile_id == lab["case"]
    assert receipt.request == d.validate_request(payload)
    assert receipt.receipt_digest == s.receipt_digest(receipt)
    assert receipt.canonical_request_digest == s.request_digest(lab["case"], receipt.request)
    row = next(item for item in stored(lab)["events"] if item["id"] == receipt.event_id)
    assert row == wire_values(event_values(receipt))
    assert s.canonical_bytes(row["receipt"]) == s.canonical_bytes(value)
    return value


def current(lab):
    response = lab["client"].get(endpoint(lab))
    assert response.status_code == 200, response.text
    value = response.json()
    assert set(value) == CURRENT_KEYS
    assert value["profile_id"] == lab["case"]
    if value["state"] is not None:
        state = s.CaseActionsStateV1.model_validate(value["state"])
        head = s.ActionWriteReceiptV1.model_validate(value["head_receipt"])
        assert value["revision"] == state.revision == head.revision
        assert head.after_state_digest == s.state_digest(state)
    return value


def safe_error(response, code):
    status, message = d.ERRORS[code]
    assert response.status_code == status, response.text
    assert response.json() == {
        "detail": {"code": "admissions_actions_" + code, "message": message}
    }
    assert PRIVATE_MARKER not in response.text and SOURCE_MARKER not in response.text


def seed_source(lab, *, duplicates=False, scholarship=False):
    """Actual own decision column and raw checklist; no official proof is asserted."""
    with lab["factory"]() as session:
        entitlement_exists = session.query(Entitlement).filter_by(
            organization_id=DEV_ORGANIZATION_ID, profile_id=lab["case"], kind="case_full",
        ).first() is not None
    if not entitlement_exists:
        full_case(lab)
    result_id, _, _ = _selected(lab)
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        # Native fixture starts in demo mode. This remains synthetic data, but
        # sets the real column false to exercise the non-demo lexical URL role.
        session.get(ResearchRun, row.run_id).demo_mode = False
        item = DocumentItem(
            name="Synthetic transcript", purpose="scholarship" if scholarship else "admission",
            owner="applicant", prompt_text=SOURCE_MARKER,
            source_url="https://example.edu/synthetic-checklist", claim_ids=[],
        ).model_dump(mode="json")
        raw = DocumentChecklist(
            result_id=row.id, university=row.university, program=row.program,
            generated_at=utcnow(), ordered_steps=[SOURCE_MARKER], completeness="partial",
        ).model_dump(mode="json")
        location = "scholarship_documents" if scholarship else "admission_documents"
        raw[location] = [item, deepcopy(item)] if duplicates else [item]
        row.checklist = raw
        payload = deepcopy(row.payload)
        payload["program_url"] = "https://example.edu/synthetic-programme"
        if scholarship:
            payload["scholarships"] = [
                Scholarship(id="synthetic-award", name="Synthetic unknown award").model_dump(mode="json")
            ]
        row.payload = payload
        assert row.user_decision == "approved" and payload["user_decision"] == "rejected"
        session.commit()
    return result_id


def preview_source(lab, result_id, *, index=0, scholarship=False):
    body = {
        "result_id": result_id, "purpose": "scholarship" if scholarship else "admission",
        "award_id": "synthetic-award" if scholarship else None,
        "occurrences": [{
            "location": "scholarship_documents" if scholarship else "admission_documents",
            "index": index,
        }],
    }
    response = lab["client"].post(endpoint(lab) + "/preview", json=body)
    assert response.status_code == 200, response.text
    value = response.json()
    assert set(value) == {
        "profile_id", "result_id", "selection", "source_preview_digest", "source_status", "observed_at",
    }
    s.BindingSelectionV1.model_validate(value["selection"])
    s.SourceReadStatusV1.model_validate(value["source_status"])
    assert SOURCE_MARKER not in response.text
    return value


def bind(lab, preview, *, revision=0, application_id=None):
    return accepted(lab, command(
        "bind_source_task", revision, application_id=application_id,
        source=preview["selection"], source_preview_digest=preview["source_preview_digest"],
        personal=personal(),
    ))


def new_personal(lab, *, revision=0, **fields):
    return accepted(lab, command(
        "create_personal_task", revision, application_id=None, personal=personal(**fields),
    ))


@contextmanager
def interleave_once(lab, predicate, callback):
    """A real second transaction after a selected SQL read, not a mocked read result."""
    evidence = {"fired": False, "statement": None, "callback_result": None}

    def after(_connection, _cursor, statement, _params, _context, _many):
        if not evidence["fired"] and predicate(" ".join(statement.lower().split())):
            evidence["fired"] = True
            evidence["statement"] = statement
            evidence["callback_result"] = callback()

    event.listen(lab["engine"], "after_cursor_execute", after)
    try:
        yield evidence
    finally:
        event.remove(lab["engine"], "after_cursor_execute", after)


@contextmanager
def interleave_after_full_event_list(lab, callback):
    """Commit after full event loading, immediately before the final scalar read."""
    evidence = {"full_list_query": False, "fired": False, "callback_result": None}

    def after(_connection, _cursor, statement, _params, _context, _many):
        q = " ".join(statement.lower().split())
        if "from admissions_actions_events" in q and "order by" in q and "limit" not in q:
            evidence["full_list_query"] = True

    def before(_connection, _cursor, statement, _params, _context, _many):
        q = " ".join(statement.lower().split())
        if (evidence["full_list_query"] and not evidence["fired"]
                and q.startswith("select") and "admissions_actions_current" in q):
            evidence["fired"] = True
            evidence["callback_result"] = callback()

    event.listen(lab["engine"], "after_cursor_execute", after)
    event.listen(lab["engine"], "before_cursor_execute", before)
    try:
        yield evidence
    finally:
        event.remove(lab["engine"], "after_cursor_execute", after)
        event.remove(lab["engine"], "before_cursor_execute", before)


def test_genuine_empty_reads_are_owned_without_backfill_or_premium_reads(shared_route_lab):
    lab = shared_route_lab
    before = native_snapshot(lab), stored(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200, response.text
    view = response.json()
    assert set(view) == CURRENT_KEYS
    assert view["revision"] == 0 and view["state"] is None and view["head_receipt"] is None
    assert view["current_source_statuses"] == view["document_report_reviews"] == view["action_links"] == []
    assert_no_dml(sql)
    assert_no_premium_reads(sql)
    history = lab["client"].get(endpoint(lab) + "/events").json()
    assert history == {
        "profile_id": lab["case"], "events": [], "next_after_revision": None,
        "source_evaluation": "not_evaluated",
    }
    assert (native_snapshot(lab), stored(lab)) == before


def test_owner_precedes_uuid_event_and_source_queries(shared_route_lab):
    lab = shared_route_lab
    original = new_personal(lab)
    foreign = _foreign_case(lab)
    for case in (foreign, uuid4().hex):
        for suffix, method, body in (
            ("/commands", "POST", original["request"]),
            ("/events/" + original["event_id"], "GET", None),
            ("/preview", "POST", {
                "result_id": uuid4().hex, "purpose": "admission", "award_id": None,
                "occurrences": [{"location": "admission_documents", "index": 0}],
            }),
        ):
            response, sql = _capture(lab, lambda: lab["client"].request(
                method, endpoint(lab, case) + suffix, json=body,
            ))
            assert response.status_code == 404
            assert not any(re.search(r"\bfrom\s+(admissions_actions_events|program_results)\b", q, re.I) for q in sql)
    missing = lab["client"].get(endpoint(lab) + "/events/" + uuid4().hex)
    other = create_profile_only(lab)
    theirs = new_personal(other)
    foreign_event = lab["client"].get(endpoint(lab) + "/events/" + theirs["event_id"])
    assert missing.status_code == foreign_event.status_code == 404
    assert missing.json() == foreign_event.json()


def test_all_closed_commands_return_persisted_ack_and_keep_native_rows_exact(shared_route_lab):
    lab = shared_route_lab
    grant(lab)
    result_id = seed_source(lab)
    assert write_schedule(lab).status_code == 200
    source = preview_source(lab, result_id)
    native = native_snapshot(lab)
    receipts = []

    def save(kind, **fields):
        value = accepted(lab, command(kind, len(receipts), **fields))
        receipts.append(value)
        assert native_snapshot(lab) == native
        return value

    application = save("create_application", target=target(result_id), label="Synthetic application", details=details())
    app_id = application["applied_delta"]["applications"][0]["id"]
    entered = save("create_personal_task", application_id=app_id, personal=personal())
    entered_id = entered["applied_delta"]["document_tasks"][0]["id"]
    bound = save("bind_source_task", application_id=app_id, source=source["selection"],
                 source_preview_digest=source["source_preview_digest"], personal=personal())
    task_id = bound["applied_delta"]["document_tasks"][0]["id"]
    report = save("set_document_self_report", task_id=task_id, report={
        "state": "prepared_reported", "entered_at": None, "confirmed_personal_report": True,
    })
    reported = deepcopy(report["applied_delta"]["document_tasks"][0]["report"])
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        raw = deepcopy(row.checklist)
        raw["ordered_steps"].append("Synthetic later procedure")
        row.checklist = raw
        session.commit()
    native = native_snapshot(lab)
    revised_source = preview_source(lab, result_id)
    rebound = save("rebind_source_task", task_id=task_id,
        expected_binding_digest=bound["applied_delta"]["document_tasks"][0]["binding"]["binding_digest"],
        source=revised_source["selection"], source_preview_digest=revised_source["source_preview_digest"])
    assert rebound["applied_delta"]["document_tasks"][0]["report"] == reported
    assert {"task_id": task_id, "reasons": ["report_refers_to_previous_binding"]} in current(lab)["document_report_reviews"]
    save("set_personal_details", target={"kind": "application", "id": app_id}, details=details(notes="Synthetic edited note"))
    save("set_planning_status", application_id=app_id, status="preparing")
    task_before = next(t for t in current(lab)["state"]["document_tasks"] if t["id"] == task_id)
    submitted = save("declare_submission", application_id=app_id, submission={
        "entered_at": {"local_date": utcnow().date().isoformat(), "local_time": None, "timezone": None},
        "channel": "Synthetic applicant entered channel", "document_task_ids": [task_id],
        "confirmed_applicant_declaration": True,
    })
    assert submitted["affected_refs"]["document_task_ids"] == []
    assert next(t for t in current(lab)["state"]["document_tasks"] if t["id"] == task_id) == task_before
    save("declare_withdrawal", application_id=app_id, withdrawal={
        "entered_at": None, "notes": "Synthetic withdrawal", "confirmed_applicant_declaration": True,
    })
    save("correct_declaration", application_id=app_id, prior_declaration={
        "event_id": submitted["event_id"], "revision": submitted["revision"], "kind": submitted["kind"],
    }, replacement={"kind": "planning", "status": "preparing"}, confirmed_correction=True)
    mapping = {
        "task_id": entered_id, "legacy_key_digest": "a" * 64,
        "expected_binding_digest": None, "source_preview_digest": None,
        "legacy_value": True, "confirmed_prepared_report": True,
        "source_version": "unknown", "original_reported_at": None,
    }
    imported_input = {"expected_revision": len(receipts), "legacy_snapshot_digest": "b" * 64, "mappings": [mapping]}
    unchanged = stored(lab)
    proposed, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/import-preview", json=imported_input))
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["mappings"] == [mapping]
    assert proposed.json()["legacy_snapshot_digest"] == "b" * 64
    assert_no_dml(sql)
    assert stored(lab) == unchanged
    save("import_legacy_marks", legacy_snapshot_digest="b" * 64, mappings=[mapping], entered_at=None)
    today = lab["client"].get(f"/api/profiles/{lab['case']}/today").json()
    head = today["active_plan"]["current_observed_head"]
    assert head["origin"] == "legacy_v1"
    save("select_active_preparation", origin="legacy_v1", policy="follow_current_accepted", observed_head=head)
    assert len(receipts) == 12 and len({r["kind"] for r in receipts}) == 12
    assert current(lab)["head_receipt"] == receipts[-1]
    for receipt in receipts:
        response = lab["client"].get(endpoint(lab) + "/events/" + receipt["event_id"])
        assert response.status_code == 200 and response.json() == receipt
    history = lab["client"].get(endpoint(lab) + "/events?limit=100").json()
    assert history["events"] == receipts and history["next_after_revision"] is None
    assert history["source_evaluation"] == "not_evaluated"


def test_replay_is_immutable_before_changed_member_source_expiry_and_corrupt_current(shared_route_lab):
    lab = shared_route_lab
    grant(lab)
    source_id = seed_source(lab)
    preview = preview_source(lab, source_id)
    original = bind(lab, preview)
    original_bytes = s.canonical_bytes(original)
    enable_native_auth(lab)
    raw_cookie = "synthetic-new-member-" + uuid4().hex
    with lab["factory"]() as session:
        user = User(email="synthetic-member-" + uuid4().hex + "@example.test", is_active=True,
                    password_hash=session.get(User, DEV_USER_ID).password_hash)
        session.add(user)
        session.flush()
        session.add(OrganizationMembership(user_id=user.id, organization_id=DEV_ORGANIZATION_ID, role="member"))
        session.add(AuthSession(user_id=user.id, organization_id=DEV_ORGANIZATION_ID,
            token_hash=token_hash(raw_cookie), expires_at=utcnow() + timedelta(days=1),
            last_seen_at=utcnow() - timedelta(minutes=1)))
        row = session.get(ProgramResultRow, source_id)
        row.user_decision = "rejected"
        row.checklist = {"synthetic_unreadable": SOURCE_MARKER}
        session.execute(delete(Entitlement).where(Entitlement.profile_id == lab["case"]))
        for term in session.query(Subscription).all():
            term.ends_at = utcnow() - timedelta(days=1)
        state = session.get(AdmissionsActionsCurrentRow, lab["case"])
        state.state_digest = "0" * 64
        session.commit()
    lab["client"].cookies.set(get_settings().session_cookie_name, raw_cookie)
    before = native_snapshot(lab), stored(lab)
    replay, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/commands", json=original["request"]))
    assert replay.status_code == 200 and s.canonical_bytes(replay.json()) == original_bytes
    assert_no_premium_reads(sql)
    assert not any("from admissions_actions_current" in q.lower() for q in sql)
    changed = deepcopy(original["request"])
    changed["personal"]["label"] = "Synthetic changed intent"
    safe_error(lab["client"].post(endpoint(lab) + "/commands", json=changed), "uuid_conflict")
    safe_error(lab["client"].get(endpoint(lab)), "saved_unreadable")
    safe_error(lab["client"].post(endpoint(lab) + "/commands", json=command(
        "create_personal_task", 1, application_id=None, personal=personal(),
    )), "saved_unreadable")
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize("variant", ["kind", "extra", "boolean_revision", "string_revision", "uuid", "nonfinite"])
def test_router_validation_is_fixed_safe_error_without_input_echo(shared_route_lab, variant):
    lab = shared_route_lab
    payload = command("create_personal_task", application_id=None, personal=personal(label=PRIVATE_MARKER))
    if variant == "kind":
        payload["kind"] = PRIVATE_MARKER
    elif variant == "extra":
        payload["actor"] = {"raw_email": PRIVATE_MARKER}
    elif variant == "boolean_revision":
        payload["expected_revision"] = False
    elif variant == "string_revision":
        payload["expected_revision"] = "0"
    elif variant == "uuid":
        payload["client_write_uuid"] = PRIVATE_MARKER
    else:
        payload["personal"]["details"]["notes"] = float("nan")
    before = native_snapshot(lab), stored(lab)
    response = lab["client"].post(endpoint(lab) + "/commands", content=json.dumps(payload), headers={"content-type": "application/json"})
    safe_error(response, "input_invalid")
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "after_revision=-1", "after_revision=2147483648", "limit=" + PRIVATE_MARKER])
def test_history_query_bounds_do_not_echo_or_write(shared_route_lab, query):
    lab = shared_route_lab
    before = stored(lab)
    safe_error(lab["client"].get(endpoint(lab) + "/events?" + query), "input_invalid")
    assert stored(lab) == before


def test_raw_duplicate_scope_omission_award_unknown_and_locked_redaction(shared_route_lab):
    lab = shared_route_lab
    result_id = seed_source(lab, duplicates=True)
    native = native_snapshot(lab), stored(lab)
    first = preview_source(lab, result_id, index=0)
    second = preview_source(lab, result_id, index=1)
    assert first["selection"]["occurrences"][0]["index"] == 0
    assert second["selection"]["occurrences"][0]["index"] == 1
    assert first["source_preview_digest"] != second["source_preview_digest"]
    assert first["selection"]["g1_relation"] == second["selection"]["g1_relation"] == "ambiguous_occurrence"
    assert first["selection"]["g1_document"] is None
    assert (native_snapshot(lab), stored(lab)) == native
    # Unrecorded scope stays absent; a recorded empty scope is not universal.
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        raw = deepcopy(row.checklist)
        assert "scope" not in raw["admission_documents"][0]
        raw["admission_documents"][0]["scope"] = {}
        row.checklist = raw
        session.commit()
    recorded_empty = preview_source(lab, result_id)
    assert recorded_empty["selection"]["occurrences"][0]["item_digest"] != first["selection"]["occurrences"][0]["item_digest"]
    award_result = seed_source(lab, scholarship=True)
    award = preview_source(lab, award_result, scholarship=True)
    assert award["selection"]["award_id"] == "synthetic-award"
    assert award["selection"]["award_relation"] == "unknown"
    bound = bind(lab, recorded_empty)
    with lab["factory"]() as session:
        session.execute(delete(Entitlement).where(Entitlement.profile_id == lab["case"]))
        session.commit()
    before = native_snapshot(lab), stored(lab)
    view, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert view.status_code == 200, view.text
    status = view.json()["current_source_statuses"][0]
    assert status["source_state"] == "research_locked" and status["current_digest"] is None and status["reasons"] == []
    assert SOURCE_MARKER not in view.text
    for pair in view.json()["action_links"]:
        assert pair["programme_information"]["href"] is None
        assert pair["requirements_information"]["href"] is None
    assert_no_premium_reads(sql)
    preview_body = {
        "result_id": result_id, "purpose": "admission", "award_id": None,
        "occurrences": [{"location": "admission_documents", "index": 0}],
    }
    denial, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/preview", json=preview_body))
    safe_error(denial, "source_locked")
    assert_no_premium_reads(sql)
    assert (native_snapshot(lab), stored(lab)) == before
    # Existing personal reporting remains usable under the same source lock.
    task_id = bound["applied_delta"]["document_tasks"][0]["id"]
    response, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/commands", json=command(
        "set_document_self_report", 1, task_id=task_id,
        report={"state": "prepared_reported", "entered_at": None, "confirmed_personal_report": True},
    )))
    assert response.status_code == 200, response.text
    assert_no_premium_reads(sql)
    assert native_snapshot(lab) == before[0]


def test_source_preview_and_import_are_strict_and_source_change_refuses_binding(shared_route_lab):
    lab = shared_route_lab
    source_id = seed_source(lab)
    source = preview_source(lab, source_id)
    for index in (True, "0", -1):
        response = lab["client"].post(endpoint(lab) + "/preview", json={
            "result_id": source_id, "purpose": "admission", "award_id": None,
            "occurrences": [{"location": "admission_documents", "index": index}],
        })
        safe_error(response, "input_invalid")
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, source_id)
        raw = deepcopy(row.checklist)
        raw["ordered_steps"].append("Synthetic changed source")
        row.checklist = raw
        session.commit()
    before = stored(lab), native_snapshot(lab)
    response = lab["client"].post(endpoint(lab) + "/commands", json=command(
        "bind_source_task", application_id=None, source=source["selection"],
        source_preview_digest=source["source_preview_digest"], personal=personal(),
    ))
    safe_error(response, "source_preview_stale")
    assert (stored(lab), native_snapshot(lab)) == before
    chosen = new_personal(lab)
    mapping = {
        "task_id": chosen["applied_delta"]["document_tasks"][0]["id"],
        "legacy_key_digest": "c" * 64, "expected_binding_digest": None,
        "source_preview_digest": None, "legacy_value": True,
        "confirmed_prepared_report": True, "source_version": "unknown", "original_reported_at": None,
    }
    for changed_mapping in ({**mapping, "source_version": PRIVATE_MARKER}, {**mapping, "task_id": uuid4().hex}):
        response = lab["client"].post(endpoint(lab) + "/import-preview", json={
            "expected_revision": 1, "legacy_snapshot_digest": "d" * 64, "mappings": [changed_mapping],
        })
        safe_error(response, "input_invalid" if changed_mapping["source_version"] != "unknown" else "record_not_found")


@pytest.mark.parametrize("variant", [
    "current_digest", "current_revision", "current_time", "current_only", "history_only",
    "missing_head", "head_kind", "head_uuid", "head_request_digest", "head_receipt_digest",
    "head_time", "head_affected", "head_body", "older_affected",
])
def test_current_and_copied_header_corruption_fail_without_reset_or_repair(shared_route_lab, variant):
    lab = shared_route_lab
    first = new_personal(lab)
    task_id = first["applied_delta"]["document_tasks"][0]["id"]
    head = accepted(lab, command("set_personal_details", 1,
        target={"kind": "document_task", "id": task_id}, details=details(notes="Synthetic second revision")))
    with lab["factory"]() as session:
        row = session.get(AdmissionsActionsCurrentRow, lab["case"])
        event_row = session.get(AdmissionsActionsEventRow, head["event_id"])
        if variant == "current_digest":
            row.state_digest = "0" * 64
        elif variant == "current_revision":
            row.revision = 3
        elif variant == "current_time":
            row.updated_at = utcnow() + timedelta(days=1)
        elif variant == "current_only":
            session.execute(delete(AdmissionsActionsEventRow).where(AdmissionsActionsEventRow.profile_id == lab["case"]))
        elif variant == "history_only":
            session.delete(row)
        elif variant == "missing_head":
            session.delete(event_row)
        elif variant == "head_kind":
            event_row.kind = "create_personal_task"
        elif variant == "head_uuid":
            event_row.client_write_uuid = str(uuid4())
        elif variant == "head_request_digest":
            event_row.request_digest = "0" * 64
        elif variant == "head_receipt_digest":
            event_row.receipt_digest = "0" * 64
        elif variant == "head_time":
            event_row.accepted_at = utcnow() + timedelta(days=1)
        elif variant == "head_affected":
            event_row.affected_refs = {"application_ids": [], "document_task_ids": [], "active_selector_changed": False}
        elif variant == "head_body":
            event_row.receipt = {"synthetic_unreadable": PRIVATE_MARKER}
        else:
            old = session.get(AdmissionsActionsEventRow, first["event_id"])
            old.affected_refs = {"application_ids": [], "document_task_ids": [], "active_selector_changed": False}
        session.commit()
    before = stored(lab), native_snapshot(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    safe_error(response, "saved_unreadable")
    assert_no_dml(sql)
    safe_error(lab["client"].get(f"/api/profiles/{lab['case']}/export"), "saved_unreadable")
    assert (stored(lab), native_snapshot(lab)) == before


def test_old_metadata_is_not_claimed_as_old_body_validation(shared_route_lab):
    lab = shared_route_lab
    first = new_personal(lab)
    task_id = first["applied_delta"]["document_tasks"][0]["id"]
    second = accepted(lab, command("set_personal_details", 1,
        target={"kind": "document_task", "id": task_id}, details=details()))
    with lab["factory"]() as session:
        session.get(AdmissionsActionsEventRow, first["event_id"]).receipt = {"synthetic_unreadable": PRIVATE_MARKER}
        session.commit()
    before = stored(lab), native_snapshot(lab)
    assert current(lab)["head_receipt"] == second
    safe_error(lab["client"].get(endpoint(lab) + "/events/" + first["event_id"]), "saved_unreadable")
    safe_error(lab["client"].get(endpoint(lab) + "/events?limit=100"), "saved_unreadable")
    safe_error(lab["client"].get(f"/api/profiles/{lab['case']}/export"), "saved_unreadable")
    assert (stored(lab), native_snapshot(lab)) == before


def maximal_metadata_fixture(lab):
    """Synthetic certified metadata, deliberately unreadable historical bodies.

    A fully typed current and real pure head receipt exercise the actual current
    loader's finite association checks. This is not a complete valid history or
    a claim that a metadata read certifies old receipt bodies.
    """
    result_id = seed_source(lab)
    bound = bind(lab, preview_source(lab, result_id))
    actor = s.ActorRefV1.model_validate(bound["actor"])
    base = utcnow() - timedelta(days=2)
    binding = deepcopy(bound["applied_delta"]["document_tasks"][0]["binding"])
    binding["accepted_at"] = base.isoformat()
    binding["binding_digest"] = s.reference_digest("g3-checklist-binding-v1", {
        key: value for key, value in binding.items() if key != "binding_digest"
    })
    s.ChecklistBindingReceiptV1.model_validate(binding)
    metadata = []

    def reference(kind, *, application_id=None, task_id=None):
        revision = len(metadata) + 1
        ref = {"event_id": uuid4().hex, "revision": revision, "kind": kind}
        metadata.append(s.EventMetadataV1.model_validate({
            **ref, "profile_id": lab["case"], "accepted_at": base + timedelta(seconds=revision),
            "affected_refs": {
                "application_ids": [] if application_id is None else [application_id],
                "document_task_ids": [] if task_id is None else [task_id],
                "active_selector_changed": False,
            },
        }))
        return ref

    applications = []
    for index in range(20):
        app_id = uuid4().hex
        created = reference("create_application", application_id=app_id)
        status = reference("set_planning_status", application_id=app_id)
        latest = reference("set_personal_details", application_id=app_id)
        applications.append({
            "id": app_id, "profile_id": lab["case"], "target": target(result_id),
            "label": f"Synthetic metadata application {index}", "details": details(),
            "status": "preparing", "created_ref": created, "status_ref": status, "latest_ref": latest,
        })
    tasks = []
    for index in range(399):
        task_id = uuid4().hex
        created = reference("bind_source_task", task_id=task_id)
        binding_ref = reference("rebind_source_task", task_id=task_id)
        report_ref = reference("set_document_self_report", task_id=task_id)
        latest = reference("set_personal_details", task_id=task_id)
        tasks.append({
            "id": task_id, "profile_id": lab["case"], "application_id": applications[0]["id"],
            "origin": "source_reference", "personal": personal(label=f"Synthetic metadata task {index}"),
            "binding": binding, "created_ref": created, "binding_ref": binding_ref, "latest_ref": latest,
            "report": {
                "state": "prepared_reported", "entered_at": None,
                "accepted_at": base + timedelta(seconds=report_ref["revision"]), "actor": actor,
                "event_ref": report_ref, "binding_digest_at_report": binding["binding_digest"],
                "origin": "applicant_report", "official_verification": "not_performed",
            },
        })
    state = s.CaseActionsStateV1.model_validate({
        "profile_id": lab["case"], "revision": len(metadata), "head_event_id": metadata[-1].event_id,
        "applications": applications, "document_tasks": tasks, "active_preparation": None,
    })
    # Only this last body's validity is certified by the fixture.
    transition = d.apply_action(state, command("create_personal_task", state.revision,
        application_id=None, personal=personal()), d.ActionContextV1(
        profile_id=lab["case"], event_id=uuid4().hex,
        accepted_at=base + timedelta(seconds=state.revision + 1), actor=actor, new_task_id=uuid4().hex,
    ))
    with lab["factory"]() as session:
        session.execute(delete(AdmissionsActionsCurrentRow).where(AdmissionsActionsCurrentRow.profile_id == lab["case"]))
        session.execute(delete(AdmissionsActionsEventRow).where(AdmissionsActionsEventRow.profile_id == lab["case"]))
        for item in metadata:
            session.add(AdmissionsActionsEventRow(
                id=item.event_id, profile_id=lab["case"], revision=item.revision,
                schema_version="admissions-actions-v1", kind=item.kind, client_write_uuid=str(uuid4()),
                request_digest="a" * 64, receipt_digest="b" * 64, accepted_at=item.accepted_at,
                affected_refs=item.affected_refs.model_dump(mode="json"),
                receipt={"synthetic_unreadable_old_body": True},
            ))
        session.add(AdmissionsActionsCurrentRow(**current_values(transition)))
        session.add(AdmissionsActionsEventRow(**event_values(transition.receipt)))
        session.commit()
    return transition, metadata


def test_maximum_current_references_use_at_most_nine_two_hundred_metadata_batches(shared_route_lab):
    lab = shared_route_lab
    transition, metadata = maximal_metadata_fixture(lab)
    batches = d.metadata_batches(transition.state)
    assert len(batches) == 9 and max(map(len, batches)) == 200
    assert sum(map(len, batches)) == 1657
    before = stored(lab), native_snapshot(lab)
    parameters = []

    def capture(_connection, _cursor, statement, params, _context, _many):
        q = " ".join(statement.lower().split())
        if "from admissions_actions_events" in q and re.search(r"admissions_actions_events\.id in\s*\(", q):
            parameters.append((q, deepcopy(params)))

    event.listen(lab["engine"], "before_cursor_execute", capture)
    try:
        view = current(lab)
    finally:
        event.remove(lab["engine"], "before_cursor_execute", capture)
    assert view["state"] == transition.state.model_dump(mode="json")
    assert view["head_receipt"] == transition.receipt.model_dump(mode="json")
    assert len(parameters) == 9
    for sql, params in parameters:
        columns = re.split(r"\bfrom\b", sql, maxsplit=1)[0]
        assert "admissions_actions_events.receipt" not in columns
        values = list(params.values()) if isinstance(params, dict) else list(params)
        selected_ids = [v for v in values if isinstance(v, str) and v in {m.event_id for m in metadata} | {transition.receipt.event_id}]
        assert 1 <= len(selected_ids) <= 200
    safe_error(lab["client"].get(endpoint(lab) + "/events/" + metadata[0].event_id), "saved_unreadable")
    safe_error(lab["client"].get(f"/api/profiles/{lab['case']}/export"), "saved_unreadable")
    assert (stored(lab), native_snapshot(lab)) == before


def test_bound_legacy_import_needs_fresh_authorized_source_token_but_personal_import_is_free(shared_route_lab):
    lab = shared_route_lab
    source_id = seed_source(lab)
    preview = preview_source(lab, source_id)
    bound = bind(lab, preview)
    task = bound["applied_delta"]["document_tasks"][0]
    mapping = {
        "task_id": task["id"], "legacy_key_digest": "e" * 64,
        "expected_binding_digest": task["binding"]["binding_digest"],
        "source_preview_digest": preview["source_preview_digest"], "legacy_value": True,
        "confirmed_prepared_report": True, "source_version": "unknown", "original_reported_at": None,
    }
    preview_body = {"expected_revision": 1, "legacy_snapshot_digest": "f" * 64, "mappings": [mapping]}
    before = native_snapshot(lab), stored(lab)
    response = lab["client"].post(endpoint(lab) + "/import-preview", json=preview_body)
    assert response.status_code == 200, response.text
    assert response.json()["mappings"] == [mapping]
    assert (native_snapshot(lab), stored(lab)) == before
    for token in (None, "0" * 64):
        invalid = deepcopy(preview_body)
        invalid["mappings"][0]["source_preview_digest"] = token
        safe_error(lab["client"].post(endpoint(lab) + "/import-preview", json=invalid), "legacy_import_changed")
    imported = accepted(lab, command("import_legacy_marks", 1,
        legacy_snapshot_digest="f" * 64, mappings=[mapping], entered_at=None))
    with lab["factory"]() as session:
        session.execute(delete(Entitlement).where(Entitlement.profile_id == lab["case"]))
        session.commit()
    preview_body["expected_revision"] = 2
    response, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/import-preview", json=preview_body))
    safe_error(response, "source_locked")
    assert_no_premium_reads(sql)
    response, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/commands", json=command(
        "import_legacy_marks", 2, legacy_snapshot_digest="f" * 64, mappings=[mapping], entered_at=None)))
    safe_error(response, "source_locked")
    assert_no_premium_reads(sql)
    replay = lab["client"].post(endpoint(lab) + "/commands", json=imported["request"])
    assert replay.status_code == 200 and replay.json() == imported
    personal_receipt = new_personal(lab, revision=2)
    personal_mapping = {**mapping,
        "task_id": personal_receipt["applied_delta"]["document_tasks"][0]["id"],
        "legacy_key_digest": "1" * 64, "expected_binding_digest": None, "source_preview_digest": None,
    }
    response, sql = _capture(lab, lambda: lab["client"].post(endpoint(lab) + "/commands", json=command(
        "import_legacy_marks", 3, legacy_snapshot_digest="2" * 64, mappings=[personal_mapping], entered_at=None)))
    assert response.status_code == 200, response.text
    assert_no_premium_reads(sql)


def test_correction_reads_exact_old_own_declaration_and_never_borrows_an_application(shared_route_lab):
    lab = shared_route_lab
    result_id = seed_source(lab)
    first = accepted(lab, command("create_application", target=target(result_id), label="Synthetic first", details=details()))
    first_id = first["applied_delta"]["applications"][0]["id"]
    second = accepted(lab, command("create_application", 1, target=target(result_id), label="Synthetic second", details=details()))
    second_id = second["applied_delta"]["applications"][0]["id"]
    declared = accepted(lab, command("declare_submission", 2, application_id=first_id, submission={
        "entered_at": {"local_date": utcnow().date().isoformat(), "local_time": None, "timezone": None},
        "channel": "Synthetic entered channel", "confirmed_applicant_declaration": True,
    }))
    ref = {"event_id": declared["event_id"], "revision": declared["revision"], "kind": declared["kind"]}
    request = command("correct_declaration", 3, application_id=second_id, prior_declaration=ref,
        replacement={"kind": "planning", "status": "preparing"}, confirmed_correction=True)
    before = stored(lab), native_snapshot(lab)
    safe_error(lab["client"].post(endpoint(lab) + "/commands", json=request), "invalid_transition")
    assert (stored(lab), native_snapshot(lab)) == before
    request["application_id"] = first_id
    corrected = accepted(lab, request)
    assert corrected["applied_delta"]["corrected_declaration"] == ref
    exact = lab["client"].get(endpoint(lab) + "/events/" + declared["event_id"])
    assert exact.status_code == 200 and exact.json() == declared
    exported = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert exported.status_code == 200, exported.text
    assert exported.json()["admissions_actions"]["submission_declarations"] == [declared]
    assert exported.json()["counts"]["admissions_submission_declarations"] == 1


@pytest.mark.parametrize("raw_url,expected_state", [
    ("https://example.edu/synthetic-programme", "actionable_unverified"),
    ("https://example.edu/synthetic-programme?token=" + PRIVATE_MARKER, "blocked"),
    ("javascript:" + PRIVATE_MARKER, "blocked"),
    ("http://127.0.0.1/" + PRIVATE_MARKER, "blocked"),
])
def test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms(shared_route_lab, raw_url, expected_state):
    lab = shared_route_lab
    result_id = seed_source(lab)
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        payload = deepcopy(row.payload)
        payload["program_url"] = raw_url
        row.payload = payload
        session.commit()
    accepted(lab, command("create_application", target=target(result_id), label="Synthetic link review", details=details()))
    before = native_snapshot(lab), stored(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200, response.text
    link = response.json()["action_links"][0]["programme_information"]
    assert link["role"] == "programme_information"
    assert link["destination_verification"] == "not_performed"
    assert link["state"] == expected_state
    assert link["href"] == (raw_url if expected_state == "actionable_unverified" else None)
    assert PRIVATE_MARKER not in response.text
    assert_no_dml(sql)
    assert (native_snapshot(lab), stored(lab)) == before


def populated_history(lab, count=103):
    first = new_personal(lab)
    task_id = first["applied_delta"]["document_tasks"][0]["id"]
    receipts = [first]
    for revision in range(1, count):
        receipts.append(accepted(lab, command("set_personal_details", revision,
            target={"kind": "document_task", "id": task_id}, details=details(notes=f"Synthetic note {revision}"))))
    return receipts


def test_history_cursor_exact_event_and_full_export_above_page_limit(shared_route_lab):
    lab = shared_route_lab
    initial_export = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert initial_export.status_code == 200, initial_export.text
    baseline = initial_export.json()
    native = native_snapshot(lab)
    receipts = populated_history(lab)
    for offset, limit in ((0, 20), (0, 100), (20, 100), (100, 100), (103, 100)):
        response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab) + f"/events?after_revision={offset}&limit={limit}"))
        assert response.status_code == 200, response.text
        page = response.json()
        expected = receipts[offset:offset + limit]
        assert page["events"] == expected
        assert page["next_after_revision"] == (expected[-1]["revision"] if offset + limit < len(receipts) else None)
        assert page["source_evaluation"] == "not_evaluated"
        assert_no_dml(sql)
        assert_no_premium_reads(sql)
        selects = [q.lower() for q in sql if "from admissions_actions_events" in q.lower()]
        assert len(selects) == 1 and "limit" in selects[0]
    exact, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab) + "/events/" + receipts[0]["event_id"]))
    assert exact.status_code == 200 and exact.json() == receipts[0]
    assert_no_premium_reads(sql)
    exported = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert exported.status_code == 200, exported.text
    value = exported.json()
    assert value["admissions_actions"] == {
        "current": current(lab)["state"], "events": receipts, "submission_declarations": [],
    }
    assert value["counts"]["admissions_action_current"] == 1
    assert value["counts"]["admissions_action_events"] == len(receipts)
    assert value["counts"]["admissions_submission_declarations"] == 0
    for key in baseline:
        if key not in {"counts", "note", "admissions_actions"}:
            assert value[key] == baseline[key]
    for key, count in baseline["counts"].items():
        if not key.startswith("admissions_"):
            assert value["counts"][key] == count
    assert native_snapshot(lab) == native


def test_export_rechecks_observed_head_after_loading_all_events(shared_route_lab):
    lab = shared_route_lab
    receipts = populated_history(lab, 101)
    task_id = receipts[0]["applied_delta"]["document_tasks"][0]["id"]
    payload = command("set_personal_details", len(receipts),
        target={"kind": "document_task", "id": task_id}, details=details(notes="Synthetic concurrent export write"))
    native = native_snapshot(lab)
    # The old full event list and current state are individually coherent.
    # A real accepted write after the list query must invalidate the export.
    with interleave_after_full_event_list(lab,
        lambda: lab["client"].post(endpoint(lab) + "/commands", json=payload)) as race:
        response = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert race["fired"] and race["callback_result"].status_code == 200
    safe_error(response, "saved_unreadable")
    assert stored(lab)["current"]["revision"] == 102
    assert len(stored(lab)["events"]) == 102
    assert native_snapshot(lab) == native


def test_database_nonzero_timezone_is_same_canonical_instant(shared_route_lab):
    lab = shared_route_lab
    original = new_personal(lab)

    def set_zone(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET TIME ZONE 'Asia/Almaty'")
        cursor.close()

    postgres = lab["engine"].dialect.name == "postgresql"
    if postgres:
        event.listen(lab["engine"], "connect", set_zone)
        lab["engine"].dispose()
    try:
        before = native_snapshot(lab), stored(lab)
        view = current(lab)
        assert view["head_receipt"] == original
        assert datetime.fromisoformat(view["head_receipt"]["accepted_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)
        exact = lab["client"].get(endpoint(lab) + "/events/" + original["event_id"])
        assert exact.status_code == 200 and exact.json() == original
        replay = lab["client"].post(endpoint(lab) + "/commands", json=original["request"])
        assert replay.status_code == 200 and replay.json() == original
        assert (native_snapshot(lab), stored(lab)) == before
    finally:
        if postgres:
            event.remove(lab["engine"], "connect", set_zone)
            lab["engine"].dispose()
