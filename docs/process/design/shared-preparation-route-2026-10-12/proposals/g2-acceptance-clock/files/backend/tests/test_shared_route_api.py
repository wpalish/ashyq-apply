"""Proposed native G2 contracts. EXTERNAL / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.

Reuse the approved migrated preparation lab and its no-IP/no-DNS guard. These
are personal planning/receipt controls, never official admissions/score proof.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event, inspect

from app.models import (
    ApplicantProfileRow,
    ClaimRow,
    Entitlement,
    ProgramResultRow,
    ResearchRun,
    StudyAttempt,
    StudyScheduleRow,
    Subscription,
)
from app.models.base import utcnow
from app.models.shared_route import SharedRouteCurrentRow, SharedRouteHistoryRow
from tests.test_preparation_api import body, full_case, grant, url
from tests.test_preparation_graph_api import _capture, _foreign_case, _selected, _snapshot
from tests.test_study_schedule_api import unchanged_inputs, write

pytest_plugins = ("tests.test_preparation_api",)


@pytest.fixture
def shared_route_lab(prep_lab):
    """Same approved fixture, with the native SQLite connection policy explicit."""
    engine = prep_lab["engine"]
    if engine.dialect.name != "sqlite":
        yield prep_lab
        return

    def pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    event.listen(engine, "connect", pragmas)
    # prep_lab has finished/closed its setup request and database sessions.
    # Reopen its file-backed DB with the same relevant policy as app.db.
    engine.dispose()
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() == 15000
        yield prep_lab
    finally:
        event.remove(engine, "connect", pragmas)
        engine.dispose()


def endpoint(lab, case=None):
    return f"/api/profiles/{case or lab['case']}/preparation/shared-route"


def route_input(lab, *, result_ids=None, weekly_minutes=60, own_reviews=None):
    if result_ids is None:
        first, _, _ = _selected(lab)
        second, _, _ = _selected(lab, decision="maybe", value=7.0)
        result_ids = [second, first]  # Deliberately distinct, older runs, explicit order.
    today = utcnow().date()
    return {
        "selected_result_ids": list(result_ids),
        "starts_on": today.isoformat(),
        "timezone": "UTC",
        "study_days": [0, 1, 2, 3, 4, 5, 6],
        "shared_weekly_minutes": weekly_minutes,
        "exam_choices": [
            {
                "exam": exam,
                "priority": priority,
                "first_exam_on": (today + timedelta(days=60 + priority)).isoformat(),
                "retake_on": None,
                "certificate_deadline": (today + timedelta(days=90)).isoformat(),
                "result_wait_days": 3,
                "delivery_days": 1,
                "safety_days": 1,
                "personal_targets": {"overall": 8.0} if priority == 0 else {"total": 1500},
                "confirmed_exam_dates_and_buffers": True,
            }
            for priority, exam in enumerate(("ielts_academic", "digital_sat"))
        ],
        "own_reviews": list(own_reviews or []),
        "confirmed_shared_planning_inputs": True,
    }


def preview(lab, applicant_input, revision=0):
    response = lab["client"].post(
        endpoint(lab) + "/preview",
        json={"applicant_input": applicant_input, "expected_revision": revision},
    )
    assert response.status_code == 200, response.text
    return response.json()


def command(applicant_input, proposed, *, write_uuid=None):
    return {
        "applicant_input": deepcopy(applicant_input),
        "expected_revision": proposed["expected_shared_revision"],
        "client_write_uuid": str(write_uuid or uuid4()),
        "preview_fingerprint": proposed["preview_fingerprint"],
        "source_fingerprint": proposed["source_fingerprint"],
        "legacy_anchor": deepcopy(proposed["legacy_anchor"]),
        "planned_on": proposed["planned_on"],
    }


def save(lab, payload):
    return lab["client"].put(endpoint(lab), json=payload)


def accepted(lab, applicant_input, revision=0, *, write_uuid=None):
    proposed = preview(lab, applicant_input, revision)
    payload = command(applicant_input, proposed, write_uuid=write_uuid)
    response = save(lab, payload)
    assert response.status_code == 200, response.text
    return payload, response.json()


def stored_routes(lab):
    with lab["factory"]() as session:
        current = session.get(SharedRouteCurrentRow, lab["case"])
        history = (
            session.query(SharedRouteHistoryRow)
            .filter_by(profile_id=lab["case"])
            .order_by(SharedRouteHistoryRow.revision)
            .all()
        )
        return {
            "current": None
            if current is None
            else {
                "revision": current.revision,
                "snapshot": deepcopy(current.snapshot),
                "digest": current.digest,
            },
            "history": [
                {
                    "revision": row.revision,
                    "uuid": row.client_write_uuid,
                    "digest": row.request_digest,
                    "receipt": deepcopy(row.receipt),
                }
                for row in history
            ],
        }


def own_review(payload, *, exam="ielts_academic", version=None):
    return {
        "ref": {
            "kind": "attempt_review",
            "id": f"attempt:{payload['attempt_id']}",
            "attempt_id": payload["attempt_id"],
            "lesson_id": payload["lesson_id"],
            "content_version": version or payload["version"],
        },
        "exam": exam,
        "planned_minutes": 30,
    }


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def assert_no_dml(statements):
    assert not any(re.match(r"\s*(insert|update|delete)\b", sql, re.I) for sql in statements)


def assert_no_premium_reads(statements):
    for sql in statements:
        lowered = sql.lower().replace('"', "")
        if not lowered.lstrip().startswith("select"):
            continue
        columns = re.split(r"\bfrom\b", lowered, maxsplit=1)[0]
        assert not re.search(r"program_results\.(payload|checklist|university|program)\b", columns)
        assert not re.search(r"\bfrom\s+(claims|conflicts)\b", lowered)


@contextmanager
def reject_history_insert(lab):
    """A real isolated-DB constraint failure, not a mocked exception/commit."""
    engine = lab["engine"]
    sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as connection:
        if sqlite:
            connection.exec_driver_sql(
                "CREATE TRIGGER g2_reject_history BEFORE INSERT ON shared_route_history "
                "BEGIN SELECT RAISE(ABORT, 'synthetic history rejection'); END"
            )
        else:
            connection.exec_driver_sql(
                "CREATE FUNCTION g2_reject_history_fn() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic history rejection' USING ERRCODE='23514'; END $$"
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER g2_reject_history BEFORE INSERT ON shared_route_history "
                "FOR EACH ROW EXECUTE FUNCTION g2_reject_history_fn()"
            )
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER IF EXISTS g2_reject_history"
                if sqlite
                else "DROP TRIGGER IF EXISTS g2_reject_history ON shared_route_history"
            )
            if not sqlite:
                connection.exec_driver_sql("DROP FUNCTION IF EXISTS g2_reject_history_fn()")


def test_empty_owned_read_has_no_term_gate_no_backfill_and_no_dml(shared_route_lab):
    lab = shared_route_lab
    before = _snapshot(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200
    assert response.json() == {"profile_id": lab["case"], "revision": 0, "view": None}
    assert_no_dml(sql)
    assert _snapshot(lab) == before


def test_unsaved_preview_keeps_order_one_budget_and_leaves_all_native_tables_exact(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab, status="exhausted", quota=0)
    full_case(lab)
    value = route_input(lab)
    before = _snapshot(lab)
    proposed = preview(lab, value)
    assert proposed["saved"] is False and proposed["expected_shared_revision"] == 0
    assert (
        proposed["requested_result_ids"]
        == proposed["selected_result_ids"]
        == value["selected_result_ids"]
    )
    assert proposed["selection_source"] == "server_verified_owned_explicit"
    assert proposed["legacy_anchor"] == {
        "technical_revision": 0,
        "structural_fingerprint": None,
        "imported_learning_refs_fingerprint": None,
    }
    allocation = proposed["allocation"]
    assert (
        allocation["readiness"] == "not_assessed"
        and allocation["programme_applicability"] == "unknown"
    )
    assert len(allocation["lessons"]) == 9
    for week in allocation["capacity"]:
        assert week["weekly_budget_minutes"] == value["shared_weekly_minutes"]
        assert week["allocated_minutes"] <= value["shared_weekly_minutes"]
    days = Counter()
    for slot in allocation["slots"]:
        days[slot["local_date"]] += slot["planned_minutes"]
        assert slot["completion"] == "not_projected" and slot["origin"] == "personal_practice"
    assert max(days.values()) <= 180
    assert _snapshot(lab) == before


def test_new_write_returns_only_immutable_ack_and_one_matching_history_without_other_writes(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab, status="exhausted", quota=0)
    full_case(lab)
    value = route_input(lab)
    before = unchanged_inputs(lab)
    payload, receipt = accepted(lab, value)
    assert receipt["revision"] == 1 and receipt["expected_revision"] == 0
    assert receipt["selected_result_ids"] == value["selected_result_ids"]
    assert receipt["client_write_uuid"] == payload["client_write_uuid"]
    assert receipt["applicant_input"] == {"schema_version": "shared-route-v1", **value}
    assert {"view", "current_status", "visible_evidence", "needs_review"}.isdisjoint(receipt)
    assert {
        "claims",
        "claim_ids",
        "university",
        "programme",
        "source_excerpt",
        "checklist",
    }.isdisjoint(receipt)
    assert receipt["snapshot_digest"] == digest(
        {k: v for k, v in receipt.items() if k != "snapshot_digest"}
    )
    state = stored_routes(lab)
    assert state["current"] == {
        "revision": 1,
        "snapshot": receipt,
        "digest": receipt["snapshot_digest"],
    }
    assert state["history"] == [
        {
            "revision": 1,
            "uuid": payload["client_write_uuid"],
            "digest": receipt["canonical_request_digest"],
            "receipt": receipt,
        }
    ]
    assert lab["client"].get(endpoint(lab)).json()["view"]["receipt"] == receipt
    assert lab["client"].get(endpoint(lab) + "/revisions/1").json()["receipt"] == receipt
    assert unchanged_inputs(lab) == before
    with lab["factory"]() as session:
        assert session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).count() == 0


def test_canonical_uuid_replay_survives_expiry_research_lock_and_legacy_tick_exactly(
    shared_route_lab,
):
    lab = shared_route_lab
    sub = grant(lab)
    full_case(lab)
    legacy = write(lab).json()
    review_payload = body(lesson="ielts-reading-1")
    review_response = lab["client"].post(url(lab, "attempts"), json=review_payload)
    assert review_response.status_code == 200
    value = route_input(lab, own_reviews=[own_review(review_payload)])
    payload, receipt = accepted(lab, value)
    marked = deepcopy(legacy["settings"])
    marked["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
    assert write(lab, revision=1, plan=marked).status_code == 200
    with lab["factory"]() as session:
        session.get(Subscription, sub).ends_at = utcnow() - timedelta(days=1)
        session.query(Entitlement).filter_by(profile_id=lab["case"]).delete()
        session.commit()
    before = _snapshot(lab)
    reordered = dict(reversed(list(payload.items())))
    reordered["client_write_uuid"] = payload["client_write_uuid"].upper()
    reordered["applicant_input"] = deepcopy(payload["applicant_input"])
    reordered["applicant_input"]["study_days"].reverse()
    response, sql = _capture(lab, lambda: save(lab, reordered))
    assert response.status_code == 200 and response.json() == receipt
    assert_no_dml(sql)
    assert_no_premium_reads(sql)
    assert _snapshot(lab) == before
    current = lab["client"].get(endpoint(lab)).json()["view"]
    assert current["receipt"] == receipt and current["visible_evidence"] == []
    assert current["current_status"]["preparation_access"] == "expired"
    assert current["current_status"]["legacy_structure"] == "unchanged"
    assert [g["state"] for g in current["current_status"]["goal_statuses"]] == [
        "research_locked"
    ] * 2
    review_response, review_sql = _capture(
        lab, lambda: lab["client"].get(url(lab, f"attempts/{review_payload['attempt_id']}/review"))
    )
    assert review_response.status_code == 200
    assert review_response.json()["attempt"]["attempt_id"] == review_payload["attempt_id"]
    assert_no_dml(review_sql)
    lesson_response = lab["client"].get(url(lab, "lessons/ielts-reading-1"))
    assert lesson_response.status_code == 402
    assert _snapshot(lab) == before
    changed = deepcopy(payload)
    changed["applicant_input"]["shared_weekly_minutes"] += 30
    assert save(lab, changed).status_code == 409  # UUID conflict precedes expired new-write gate.
    changed["client_write_uuid"] = str(uuid4())
    assert save(lab, changed).status_code == 402
    assert stored_routes(lab)["current"]["snapshot"] == receipt


@pytest.mark.parametrize(
    "variant",
    [
        "compact_uuid",
        "extra_authoritative_output",
        "duplicate_ids",
        "whitespace_id",
        "false_confirmation",
    ],
)
def test_wire_rejects_noncanonical_shape_without_a_partial_save(shared_route_lab, variant):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    proposed = preview(lab, value)
    payload = command(value, proposed)
    if variant == "compact_uuid":
        payload["client_write_uuid"] = uuid4().hex
    elif variant == "extra_authoritative_output":
        payload["allocation"] = proposed["allocation"]
    elif variant == "duplicate_ids":
        payload["applicant_input"]["selected_result_ids"] *= 2
    elif variant == "whitespace_id":
        payload["applicant_input"]["selected_result_ids"][0] += " "
    else:
        payload["applicant_input"]["confirmed_shared_planning_inputs"] = False
    before = _snapshot(lab)
    assert save(lab, payload).status_code == 422
    assert _snapshot(lab) == before


def test_owner_precedes_uuid_history_and_selection_queries_for_foreign_or_missing_case(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    payload, _ = accepted(lab, value)
    foreign = _foreign_case(lab)
    for case in (foreign, uuid4().hex):
        path = endpoint(lab, case)
        callbacks = [
            lambda path=path: lab["client"].get(path),
            lambda path=path: lab["client"].get(path + "/revisions/1"),
            lambda path=path: lab["client"].put(path, json=payload),
            lambda path=path: lab["client"].post(
                path + "/preview", json={"applicant_input": value, "expected_revision": 0}
            ),
        ]
        for callback in callbacks:
            response, sql = _capture(lab, callback)
            assert response.status_code == 404 and response.json() == {
                "detail": "Applicant case not found"
            }
            assert not any(
                re.search(
                    r"\b(shared_route_current|shared_route_history|program_results|claims|conflicts)\b",
                    statement,
                    re.I,
                )
                for statement in sql
            )


@pytest.mark.parametrize("variant", ["missing", "foreign", "rejected", "undecided"])
def test_new_whole_selection_refuses_invalid_goal_without_premium_partial_body(
    shared_route_lab, variant
):
    lab = shared_route_lab
    grant(lab)
    full_case(lab)
    value = route_input(lab)
    other = value["selected_result_ids"][1]
    foreign = _foreign_case(lab) if variant == "foreign" else None
    if variant == "missing":
        value["selected_result_ids"][1] = uuid4().hex
    else:
        with lab["factory"]() as session:
            row = session.get(ProgramResultRow, other)
            if variant == "foreign":
                session.get(ResearchRun, row.run_id).profile_id = foreign
            else:
                row.user_decision = variant
            session.commit()
    before = _snapshot(lab)
    response = lab["client"].post(
        endpoint(lab) + "/preview", json={"applicant_input": value, "expected_revision": 0}
    )
    assert response.status_code == (404 if variant in {"missing", "foreign"} else 422)
    assert "Synthetic Uni" not in response.text and "Synthetic policy" not in response.text
    assert _snapshot(lab) == before


@pytest.mark.parametrize("variant", ["missing", "foreign", "malformed"])
def test_saved_read_keeps_all_ids_and_receipt_when_one_rejected_and_another_unavailable(
    shared_route_lab, variant
):
    lab = shared_route_lab
    grant(lab)
    full_case(lab)
    value = route_input(lab)
    _, receipt = accepted(lab, value)
    foreign = _foreign_case(lab) if variant == "foreign" else None
    with lab["factory"]() as session:
        first, second = [session.get(ProgramResultRow, key) for key in value["selected_result_ids"]]
        first.user_decision = "rejected"
        if variant == "missing":
            session.delete(second)
        elif variant == "foreign":
            session.get(ResearchRun, second.run_id).profile_id = foreign
        else:
            second.payload = {"requirement_checks": "PRIVATE-MALFORMED"}
        session.commit()
    before = _snapshot(lab)
    for path in (endpoint(lab), endpoint(lab) + "/revisions/1"):
        response = lab["client"].get(path)
        assert response.status_code == 200 and "PRIVATE-MALFORMED" not in response.text
        view = response.json()["view"] if path == endpoint(lab) else response.json()
        assert view["receipt"] == receipt
        statuses = view["current_status"]["goal_statuses"]
        assert [g["result_id"] for g in statuses] == value["selected_result_ids"]
        assert statuses[0] == {
            "result_id": value["selected_result_ids"][0],
            "state": "decision_changed",
            "safe_reason_code": "decision_changed",
        }
        assert statuses[1]["state"] == (
            "evidence_unknown" if variant == "malformed" else "result_unavailable"
        )
        assert view["current_status"]["needs_review"] is True
    assert _snapshot(lab) == before


def test_locked_new_personal_route_and_later_history_never_load_or_store_premium_payload(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    with lab["factory"]() as session:
        for row in session.query(ProgramResultRow).all():
            row.university = "PRIVATE-UNIVERSITY"
            row.program = "PRIVATE-PROGRAMME"
            row.payload = {"requirement_checks": "PRIVATE-PAYLOAD"}
        for row in session.query(ClaimRow).all():
            row.payload = {"PRIVATE-CLAIM": True}
        session.commit()
    proposed, sql = _capture(
        lab,
        lambda: lab["client"].post(
            endpoint(lab) + "/preview", json={"applicant_input": value, "expected_revision": 0}
        ),
    )
    assert proposed.status_code == 200 and "PRIVATE-" not in proposed.text
    assert_no_premium_reads(sql)
    payload = command(value, proposed.json())
    response, sql = _capture(lab, lambda: save(lab, payload))
    assert response.status_code == 200 and "PRIVATE-" not in response.text
    assert_no_premium_reads(sql)
    receipt = response.json()
    assert [item["reference_digest"] for item in receipt["source_reference_digests"]] == [
        None,
        None,
    ]
    assert receipt["allocation"]["programme_applicability"] == "unknown"
    for path in (endpoint(lab), endpoint(lab) + "/revisions/1"):
        response, sql = _capture(lab, lambda path=path: lab["client"].get(path))
        assert response.status_code == 200 and "PRIVATE-" not in response.text
        assert_no_dml(sql)
        assert_no_premium_reads(sql)
        view = response.json()["view"] if path == endpoint(lab) else response.json()
        assert view["receipt"] == receipt and view["visible_evidence"] == []
    assert "PRIVATE-" not in json.dumps(stored_routes(lab))


@pytest.mark.parametrize(
    "mutation",
    ["action_id", "weekday", "budget", "catalogue_availability", "goal_order", "premium_extra"],
)
def test_full_inner_receipt_corruption_is_not_accepted_by_outer_rehash_or_repaired_on_get(
    shared_route_lab, mutation
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    _, receipt = accepted(lab, value)
    corrupt = deepcopy(receipt)
    if mutation == "action_id":
        corrupt["allocation"]["slots"][0]["action_id"] = "0" * 64
    elif mutation == "weekday":
        corrupt["applicant_input"]["study_days"] = [0]
    elif mutation == "budget":
        corrupt["applicant_input"]["shared_weekly_minutes"] += 30
    elif mutation == "catalogue_availability":
        corrupt["catalogue_snapshot"]["lessons"][0]["available"] = False
    elif mutation == "goal_order":
        corrupt["source_reference_digests"].reverse()
    else:
        corrupt["claims"] = ["PRIVATE-CORRUPT-CLAIM"]
    corrupt["snapshot_digest"] = digest(
        {k: v for k, v in corrupt.items() if k != "snapshot_digest"}
    )
    with lab["factory"]() as session:
        current = session.get(SharedRouteCurrentRow, lab["case"])
        current.snapshot = deepcopy(corrupt)
        current.digest = corrupt["snapshot_digest"]
        history = (
            session.query(SharedRouteHistoryRow).filter_by(profile_id=lab["case"], revision=1).one()
        )
        history.receipt = deepcopy(corrupt)
        session.commit()
    before = _snapshot(lab)
    for path in (endpoint(lab), endpoint(lab) + "/revisions/1"):
        response, sql = _capture(lab, lambda path=path: lab["client"].get(path))
        assert response.status_code == 503 and "PRIVATE-CORRUPT" not in response.text
        assert_no_dml(sql)
    assert _snapshot(lab) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "absent_current_with_history",
        "current_behind_latest",
        "missing_matching_history",
        "current_digest",
        "current_time",
        "history_uuid",
        "history_digest",
        "history_time",
        "history_origin",
    ],
)
def test_pointer_and_column_mismatch_never_reset_case_revision_or_silently_omit_export(
    shared_route_lab, mutation
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    _, first = accepted(lab, value)
    if mutation == "current_behind_latest":
        changed = deepcopy(value)
        changed["shared_weekly_minutes"] += 30
        accepted(lab, changed, 1)
    with lab["factory"]() as session:
        current = session.get(SharedRouteCurrentRow, lab["case"])
        history = (
            session.query(SharedRouteHistoryRow).filter_by(profile_id=lab["case"], revision=1).one()
        )
        if mutation == "absent_current_with_history":
            session.delete(current)
        elif mutation == "current_behind_latest":
            current.snapshot = deepcopy(first)
            current.digest = first["snapshot_digest"]
            current.revision = 1
            current.updated_at = datetime.fromisoformat(first["accepted_at"])
        elif mutation == "missing_matching_history":
            session.delete(history)
        elif mutation == "current_digest":
            current.digest = "0" * 64
        elif mutation == "current_time":
            current.updated_at += timedelta(seconds=1)
        elif mutation == "history_uuid":
            history.client_write_uuid = str(uuid4())
        elif mutation == "history_digest":
            history.request_digest = "0" * 64
        elif mutation == "history_time":
            history.accepted_at += timedelta(seconds=1)
        else:
            history.origin = "PRIVATE-CORRUPT-ORIGIN"
        session.commit()
    before = _snapshot(lab)
    callbacks = [
        lambda: lab["client"].get(endpoint(lab)),
        lambda: lab["client"].post(
            endpoint(lab) + "/preview", json={"applicant_input": value, "expected_revision": 0}
        ),
        lambda: lab["client"].get(f"/api/profiles/{lab['case']}/export"),
    ]
    for callback in callbacks:
        response, statements = _capture(lab, callback)
        assert response.status_code == 503, response.text
        assert "PRIVATE-CORRUPT" not in response.text
        assert response.json()["detail"]["code"] == "shared_route_saved_unreadable"
        assert_no_dml(statements)
    assert _snapshot(lab) == before


def test_cross_local_midnight_refuses_old_preview_without_any_shared_or_legacy_write(
    shared_route_lab, monkeypatch
):
    import app.api.routes_shared_route as routes

    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    value["timezone"] = "Asia/Almaty"
    local = utcnow().astimezone(ZoneInfo(value["timezone"]))
    before_midnight = local.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(UTC)
    after_midnight = before_midnight + timedelta(seconds=2)
    monkeypatch.setattr(routes, "utcnow", lambda: before_midnight)
    payload = command(value, preview(lab, value))
    before = _snapshot(lab)
    times = iter((before_midnight, before_midnight, after_midnight))
    monkeypatch.setattr(routes, "utcnow", lambda: next(times))
    response, statements = _capture(lab, lambda: save(lab, payload))
    assert (
        response.status_code == 409
        and response.json()["detail"]["code"] == "shared_route_preview_stale"
    )
    assert_no_dml(statements)
    assert _snapshot(lab) == before


@pytest.mark.parametrize("boundary", ["local_midnight", "term_expiry"])
def test_terminal_subscription_select_cannot_accept_an_old_day_or_elapsed_term(
    shared_route_lab, monkeypatch, boundary
):
    import app.api.routes_shared_route as routes

    lab = shared_route_lab
    value = route_input(lab)
    value["timezone"] = "Asia/Almaty"
    local = utcnow().astimezone(ZoneInfo(value["timezone"]))
    if boundary == "local_midnight":
        start = local.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(UTC)
        term_end = start + timedelta(days=1)
    else:
        start = local.replace(hour=12, minute=0, second=0, microsecond=0).astimezone(UTC)
        term_end = start + timedelta(seconds=1)
    after_select = start + timedelta(seconds=2)
    grant(lab, start=start - timedelta(days=1), end=term_end)
    clock = {"now": start}
    monkeypatch.setattr(routes, "utcnow", lambda: clock["now"])
    payload = command(value, preview(lab, value))
    before = _snapshot(lab)
    subscription_selects = []

    def advance_after_term_select(_connection, _cursor, statement, _params, _context, _many):
        sql = " ".join(statement.lower().replace('"', "").split())
        if not sql.startswith("select") or not re.search(
            r"\bfrom\s+(?:[a-z_][a-z_0-9]*\.)?subscriptions\b", sql
        ):
            return
        subscription_selects.append(sql)
        # The command's first read validates its recomputed preview. The second
        # is the actual final native term SELECT, not a mocked gate or fake DTO.
        if len(subscription_selects) == 2:
            clock["now"] = after_select

    event.listen(lab["engine"], "after_cursor_execute", advance_after_term_select)
    try:
        response, statements = _capture(lab, lambda: save(lab, payload))
    finally:
        event.remove(lab["engine"], "after_cursor_execute", advance_after_term_select)
    assert len(subscription_selects) == 2  # No second terminal query or retry loop.
    assert clock["now"] == after_select
    status, code = (
        (409, "shared_route_preview_stale")
        if boundary == "local_midnight"
        else (402, "preparation_subscription_required")
    )
    assert response.status_code == status and response.json()["detail"]["code"] == code
    assert_no_dml(statements)
    assert _snapshot(lab) == before


@pytest.mark.parametrize("mode", ["tick", "structural", "v2"])
def test_legacy_interleaving_invalidates_unaccepted_preview_but_only_structure_changes_saved_status(
    shared_route_lab, mode
):
    from tests.test_learning_schedule_api import preview as learning_preview
    from tests.test_learning_schedule_api import save as learning_save

    lab = shared_route_lab
    grant(lab)
    legacy = write(lab).json()
    value = route_input(lab)
    proposed = preview(lab, value)
    payload = command(value, proposed)
    if mode == "v2":
        assert learning_save(lab, learning_preview(lab, 1)).status_code == 200
    else:
        changed = deepcopy(legacy["settings"])
        if mode == "tick":
            changed["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
        else:
            changed["weekly_minutes"] += 60
        assert write(lab, revision=1, plan=changed).status_code == 200
    assert save(lab, payload).status_code == 409
    assert stored_routes(lab) == {"current": None, "history": []}
    _, receipt = accepted(lab, value)
    legacy = lab["client"].get(url(lab, "schedule")).json()
    changed = deepcopy(legacy["settings"])
    if mode == "structural":
        changed["weekly_minutes"] += 60
        changed["completed_task_ids"] = []
        assert write(lab, revision=legacy["revision"], plan=changed).status_code == 200
    elif mode == "v2":
        assert learning_save(lab, learning_preview(lab, legacy["revision"])).status_code == 200
    else:
        changed["completed_task_ids"] = []
        assert write(lab, revision=legacy["revision"], plan=changed).status_code == 200
    current = lab["client"].get(endpoint(lab)).json()["view"]
    assert current["receipt"] == receipt
    assert current["current_status"]["legacy_structure"] == (
        "changed" if mode == "structural" else "unchanged"
    )
    assert current["current_status"]["imported_refs"] == "not_used"
    assert all(
        slot["completion"] == "not_projected" for slot in current["receipt"]["allocation"]["slots"]
    )


def test_source_change_is_per_goal_review_not_reallocation_or_automatic_admission_target(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    full_case(lab)
    value = route_input(lab)
    payload, receipt = accepted(lab, value)
    with lab["factory"]() as session:
        row = session.query(ClaimRow).filter_by(result_id=value["selected_result_ids"][0]).one()
        row.payload = {**row.payload, "normalized_value": 8.5}
        session.commit()
    before = _snapshot(lab)
    view = lab["client"].get(endpoint(lab)).json()["view"]
    assert view["receipt"] == receipt
    assert [item["state"] for item in view["current_status"]["goal_statuses"]] == [
        "source_changed",
        "eligible",
    ]
    assert view["current_status"]["needs_review"] is True
    assert view["receipt"]["allocation"]["programme_applicability"] == "unknown"
    assert view["receipt"]["applicant_input"]["exam_choices"][0]["personal_targets"] == {
        "overall": 8.0
    }
    assert save(lab, payload).json() == receipt
    new_payload = deepcopy(payload)
    new_payload["client_write_uuid"] = str(uuid4())
    new_payload["expected_revision"] = 1
    assert save(lab, new_payload).status_code == 409
    assert _snapshot(lab) == before


def test_exact_old_own_review_is_importable_beyond_latest_progress_and_retired_association_is_not_guessed(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    payload = body(lesson="ielts-reading-1")
    response = lab["client"].post(url(lab, "attempts"), json=payload)
    assert response.status_code == 200
    for _ in range(21):
        assert lab["client"].post(url(lab, "attempts"), json=body()).status_code == 200
    value = route_input(lab, own_reviews=[own_review(payload)])
    proposed = preview(lab, value)
    actions = [*proposed["allocation"]["slots"], *proposed["allocation"]["unallocated"]]
    assert [a["ref"]["attempt_id"] for a in actions if a["ref"]["kind"] == "attempt_review"] == [
        payload["attempt_id"]
    ]
    _, receipt = accepted(lab, value)
    with lab["factory"]() as session:
        attempt = (
            session.query(StudyAttempt)
            .filter_by(profile_id=lab["case"], client_attempt_id=payload["attempt_id"])
            .one()
        )
        attempt.content_version = "retired-synthetic-v0"
        session.commit()
    review = lab["client"].get(url(lab, f"attempts/{payload['attempt_id']}/review"))
    assert review.status_code == 200 and review.json()["lesson"] is None
    retired_value = route_input(
        lab,
        result_ids=value["selected_result_ids"],
        own_reviews=[own_review(payload, version="retired-synthetic-v0")],
    )
    before = _snapshot(lab)
    denied = lab["client"].post(
        endpoint(lab) + "/preview", json={"applicant_input": retired_value, "expected_revision": 1}
    )
    assert denied.status_code == 422 and "review_exam_unestablished" in denied.text
    current = lab["client"].get(endpoint(lab)).json()["view"]
    assert current["receipt"] == receipt
    assert _snapshot(lab) == before


def test_migration_adds_no_backfill_and_round_trip_preserves_legacy_calendar_attempts_and_profile(
    shared_route_lab,
):
    from alembic import command as migration

    from app.db import _alembic_config
    from tests.test_learning_schedule_api import preview as learning_preview
    from tests.test_learning_schedule_api import save as learning_save

    lab = shared_route_lab
    grant(lab)
    assert write(lab).status_code == 200
    assert learning_save(lab, learning_preview(lab, 1)).status_code == 200
    payload = body()
    attempt = lab["client"].post(url(lab, "attempts"), json=payload).json()
    legacy = lab["client"].get(url(lab, "schedule")).json()
    before = unchanged_inputs(lab)
    config = _alembic_config(lab["engine"].url.render_as_string(hide_password=False))
    migration.downgrade(config, "b5c81d9e2022")
    assert {"shared_route_current", "shared_route_history"}.isdisjoint(
        inspect(lab["engine"]).get_table_names()
    )
    migration.upgrade(config, "head")
    assert lab["client"].get(url(lab, "schedule")).json() == legacy
    assert (
        lab["client"].get(url(lab, f"attempts/{payload['attempt_id']}/review")).json()["attempt"]
        == attempt
    )
    assert stored_routes(lab) == {"current": None, "history": []}
    assert unchanged_inputs(lab) == before
    for table in ("shared_route_current", "shared_route_history"):
        foreign_keys = inspect(lab["engine"]).get_foreign_keys(table)
        assert any(
            fk["referred_table"] == "applicant_profiles"
            and fk["options"].get("ondelete") == "CASCADE"
            for fk in foreign_keys
        )


@pytest.mark.parametrize("existing", [False, True])
def test_real_history_insert_failure_rolls_back_current_creation_or_update_atomically(
    shared_route_lab, existing
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    if existing:
        accepted(lab, value)
    proposed = preview(lab, value, int(existing))
    payload = command(value, proposed)
    before = _snapshot(lab)
    with reject_history_insert(lab):
        response, sql = _capture(lab, lambda: save(lab, payload))
    assert response.status_code in {409, 503}, response.text
    assert "synthetic history rejection" not in response.text
    writes = [
        statement.lower() for statement in sql if re.match(r"\s*(insert|update)\b", statement, re.I)
    ]
    current_index = next(
        i for i, statement in enumerate(writes) if "shared_route_current" in statement
    )
    history_index = next(
        i for i, statement in enumerate(writes) if "shared_route_history" in statement
    )
    assert current_index < history_index  # The failure actually follows current SQL.
    assert _snapshot(lab) == before  # Fresh native sessions, not the failed identity map.
    response = save(lab, payload)
    assert response.status_code == 200 and response.json()["revision"] == int(existing) + 1
    assert len(stored_routes(lab)["history"]) == int(existing) + 1


def test_case_scoped_uuid_and_complete_additive_export_delete_preserve_sibling_receipts(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    with lab["factory"]() as session:
        own_payload = deepcopy(session.get(ApplicantProfileRow, lab["case"]).payload)
    response = lab["client"].post("/api/profiles", json=own_payload)
    assert response.status_code == 201
    other = {**lab, "case": response.json()["id"]}
    shared_uuid = str(uuid4())
    value = route_input(lab)
    _, first = accepted(lab, value, write_uuid=shared_uuid)
    other_value = route_input(other)
    _, other_receipt = accepted(other, other_value, write_uuid=shared_uuid)
    changed = deepcopy(value)
    changed["shared_weekly_minutes"] += 30
    _, second = accepted(lab, changed, 1)
    before = stored_routes(lab)
    exported = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert exported.status_code == 200, exported.text
    data = exported.json()
    assert data["shared_route_current"] == second
    assert data["shared_route_history"] == [first, second]
    assert data["counts"]["shared_route_current"] == 1
    assert data["counts"]["shared_route_history"] == 2
    assert stored_routes(lab) == before
    other_export = other["client"].get(f"/api/profiles/{other['case']}/export").json()
    assert other_export["shared_route_current"] == other_receipt
    other_stored = stored_routes(other)
    assert write(lab).status_code == 200
    payload = body()
    assert lab["client"].post(url(lab, "attempts"), json=payload).status_code == 200
    assert lab["client"].delete(f"/api/profiles/{lab['case']}").status_code == 204
    assert stored_routes(lab) == {"current": None, "history": []}
    for path in (
        endpoint(lab),
        endpoint(lab) + "/revisions/1",
        f"/api/profiles/{lab['case']}/export",
        url(lab, "schedule"),
        url(lab, f"attempts/{payload['attempt_id']}/review"),
    ):
        assert lab["client"].get(path).status_code == 404
    assert stored_routes(other) == other_stored
    assert other["client"].get(f"/api/profiles/{other['case']}/export").json() == other_export


@pytest.mark.parametrize("variant", ["missing", "other_case", "wrong_version", "wrong_exam"])
def test_review_import_checks_exact_case_receipt_version_and_registry_exam_without_feedback_leak(
    shared_route_lab, variant
):
    lab = shared_route_lab
    grant(lab)
    payload = body(lesson="ielts-reading-1")
    if variant == "other_case":
        with lab["factory"]() as session:
            own = deepcopy(session.get(ApplicantProfileRow, lab["case"]).payload)
        other = lab["client"].post("/api/profiles", json=own).json()["id"]
        assert (
            lab["client"]
            .post(f"/api/profiles/{other}/preparation/attempts", json=payload)
            .status_code
            == 200
        )
    elif variant != "missing":
        assert lab["client"].post(url(lab, "attempts"), json=payload).status_code == 200
    ref = own_review(payload)
    if variant == "wrong_version":
        ref["ref"]["content_version"] = "wrong-synthetic-version"
    if variant == "wrong_exam":
        ref["exam"] = "digital_sat"
    value = route_input(lab, own_reviews=[ref])
    before = _snapshot(lab)
    response = lab["client"].post(
        endpoint(lab) + "/preview", json={"applicant_input": value, "expected_revision": 0}
    )
    assert response.status_code == (404 if variant in {"missing", "other_case"} else 422)
    assert "feedback" not in response.text and "correct" not in response.text
    assert _snapshot(lab) == before
