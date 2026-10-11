"""Owned opt-in snapshots, migrations, unchanged legacy receipts and no GET writes."""

import re
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier, Event, Lock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, text

from app.models import (
    ApplicantProfileRow,
    Organization,
    StudyAttempt,
    StudyScheduleRow,
    Subscription,
)
from app.models.base import ensure_utc, utcnow
from tests.test_preparation_api import body, grant, url
from tests.test_study_schedule_api import settings, unchanged_inputs, write

pytest_plugins = ("tests.test_preparation_api",)


def endpoint(lab, case=None):
    return f"/api/profiles/{case or lab['case']}/preparation/schedule/learning-path"


def preview(lab, revision):
    response = lab["client"].post(endpoint(lab) + "/preview", json={"expected_revision": revision})
    assert response.status_code == 200, response.text
    return response.json()


def save(lab, view):
    return lab["client"].put(
        endpoint(lab),
        json={
            "expected_revision": view["revision"],
            "legacy_fingerprint": view["legacy_fingerprint"],
            "draft": view["learning_path"]["draft"],
        },
    )


def test_preview_no_write_opt_in_preserves_legacy_json_ticks_and_source_inputs(prep_lab):
    grant(prep_lab, status="exhausted")
    legacy = write(prep_lab).json()
    marked = deepcopy(legacy["settings"])
    marked["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
    legacy = write(prep_lab, revision=1, plan=marked).json()
    before = unchanged_inputs(prep_lab)
    empty = prep_lab["client"].get(endpoint(prep_lab)).json()
    assert empty["learning_path"] is None and empty["revision"] == 2
    proposed = preview(prep_lab, 2)
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == legacy
    assert prep_lab["client"].get(endpoint(prep_lab)).json() == empty
    accepted = save(prep_lab, proposed)
    assert accepted.status_code == 200, accepted.text
    current = accepted.json()
    assert current["revision"] == 3
    assert current["learning_path"]["legacy_settings"] == marked
    assert all(not task["completed"] for task in current["learning_path"]["schedule"]["tasks"])
    legacy_after = prep_lab["client"].get(url(prep_lab, "schedule")).json()
    assert legacy_after["settings"] == marked and legacy_after["schedule"] == legacy["schedule"]
    assert set(legacy_after) == set(legacy)
    assert prep_lab["client"].get(endpoint(prep_lab)).json() == current
    assert unchanged_inputs(prep_lab) == before
    assert save(prep_lab, proposed).status_code == 409


def test_structural_legacy_edit_keeps_snapshot_and_requires_explicit_review(prep_lab):
    grant(prep_lab)
    write(prep_lab)
    old = save(prep_lab, preview(prep_lab, 1)).json()
    changed = settings()
    changed["weekly_minutes"] += 60
    assert write(prep_lab, revision=2, plan=changed).status_code == 200
    new = prep_lab["client"].get(endpoint(prep_lab)).json()
    assert new["needs_review"] and new["learning_path"] == old["learning_path"]
    assert save(prep_lab, old).status_code == 409


def test_owned_review_beyond_progress_limit_expired_read_and_same_uuid_receipt(prep_lab):
    sub = grant(prep_lab)
    write(prep_lab)
    payload = body(lesson="ielts-reading-1")
    saved = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json()
    proposed = preview(prep_lab, 1)
    reviews = proposed["learning_path"]["draft"]["plan"]["reviews"]
    assert reviews[0]["attempt_id"] == payload["attempt_id"]
    assert save(prep_lab, proposed).status_code == 200
    frozen = prep_lab["client"].get(endpoint(prep_lab)).json()
    for _ in range(21):
        assert prep_lab["client"].post(url(prep_lab, "attempts"), json=body()).status_code == 200
    review = prep_lab["client"].get(url(prep_lab, f"attempts/{payload['attempt_id']}/review"))
    assert review.status_code == 200 and review.json()["attempt"] == saved
    with prep_lab["factory"]() as session:
        session.get(Subscription, sub).ends_at = utcnow() - timedelta(days=1)
        session.commit()
    assert prep_lab["client"].get(endpoint(prep_lab)).json() == frozen
    assert (
        prep_lab["client"].get(url(prep_lab, f"attempts/{payload['attempt_id']}/review")).json()
        == review.json()
    )
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json() == saved
    assert save(prep_lab, proposed).status_code == 402
    assert (
        prep_lab["client"]
        .post(endpoint(prep_lab) + "/preview", json={"expected_revision": 2})
        .status_code
        == 402
    )


def test_foreign_case_and_tampered_reference_disclose_no_private_review(prep_lab):
    grant(prep_lab)
    write(prep_lab)
    with prep_lab["factory"]() as session:
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        org = Organization(name="Other synthetic tenant", slug=uuid4().hex)
        session.add(org)
        session.flush()
        foreign = ApplicantProfileRow(organization_id=org.id, payload=deepcopy(own.payload))
        session.add(foreign)
        session.commit()
        foreign_id = foreign.id
    for case in [foreign_id, uuid4().hex]:
        assert prep_lab["client"].get(endpoint(prep_lab, case)).status_code == 404
        assert (
            prep_lab["client"]
            .post(endpoint(prep_lab, case) + "/preview", json={"expected_revision": 1})
            .status_code
            == 404
        )
    proposed = preview(prep_lab, 1)
    unit = proposed["learning_path"]["draft"]["plan"]["lessons"][0]["ref"]
    fake = str(uuid4())
    proposed["learning_path"]["draft"]["plan"]["reviews"] = [
        {
            "kind": "attempt_review",
            "id": f"attempt:{fake}",
            "attempt_id": fake,
            "lesson_id": unit["lesson_id"],
            "content_version": unit["content_version"],
        }
    ]
    denied = save(prep_lab, proposed)
    assert denied.status_code == 422 and "feedback" not in denied.text
    assert prep_lab["client"].get(endpoint(prep_lab)).json()["learning_path"] is None


def test_nullable_migration_round_trip_preserves_original_calendar_and_attempts(prep_lab):
    from alembic import command

    from app.db import _alembic_config

    grant(prep_lab)
    write(prep_lab)
    payload = body()
    receipt = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json()
    engine = prep_lab["engine"]
    with engine.connect() as connection:
        before = connection.execute(
            text("SELECT id, settings, revision FROM study_schedules")
        ).all()
    config = _alembic_config(prep_lab["engine"].url.render_as_string(hide_password=False))
    command.downgrade(config, "a9e5c14d2021")
    assert "learning_path" not in {
        c["name"] for c in inspect(engine).get_columns("study_schedules")
    }
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT id, settings, revision FROM study_schedules")).all()
            == before
        )
        assert (
            connection.execute(text("SELECT learning_path FROM study_schedules")).scalar() is None
        )
    assert (
        prep_lab["client"]
        .get(url(prep_lab, f"attempts/{payload['attempt_id']}/review"))
        .json()["attempt"]
        == receipt
    )


def test_unknown_content_version_and_preview_identity_are_not_substituted(prep_lab):
    grant(prep_lab)
    write(prep_lab)
    proposed = preview(prep_lab, 1)
    broken = deepcopy(proposed)
    broken["learning_path"]["draft"]["plan"]["lessons"][0]["ref"]["content_version"] = "missing-v99"
    assert save(prep_lab, broken).status_code == 422
    broken = deepcopy(proposed)
    broken["learning_path"]["draft"]["fingerprint"] = "0" * 64
    assert save(prep_lab, broken).status_code == 422
    assert prep_lab["client"].get(endpoint(prep_lab)).json()["learning_path"] is None


def test_daily_read_keeps_exact_dates_refs_and_draft_but_refreshes_baseline_age(
    prep_lab, monkeypatch
):
    import app.api.routes_preparation as routes

    grant(prep_lab)
    write(prep_lab)
    saved = save(prep_lab, preview(prep_lab, 1)).json()
    old_path = saved["learning_path"]
    assert not old_path["schedule"]["diagnostic_required"]
    with prep_lab["factory"]() as session:
        original = deepcopy(
            session.execute(text("SELECT learning_path FROM study_schedules")).scalar()
        )
    now = utcnow() + timedelta(days=32)
    monkeypatch.setattr(routes, "utcnow", lambda: now)
    read = prep_lab["client"].get(endpoint(prep_lab)).json()
    assert read["revision"] == saved["revision"] and not read["needs_review"]
    path = read["learning_path"]
    assert path["draft"] == old_path["draft"]
    assert path["schedule"]["diagnostic_required"]
    assert [(t["id"], t["due_on"], t["learning_ref"]) for t in path["schedule"]["tasks"]] == [
        (t["id"], t["due_on"], t["learning_ref"]) for t in old_path["schedule"]["tasks"]
    ]
    with prep_lab["factory"]() as session:
        assert (
            session.execute(text("SELECT learning_path FROM study_schedules")).scalar() == original
        )
    assert save(prep_lab, preview(prep_lab, saved["revision"])).status_code == 200
    assert save(prep_lab, saved).status_code == 409


def test_missing_saved_version_is_unavailable_without_mutating_frozen_identity(
    prep_lab, monkeypatch
):
    import app.api.routes_preparation as routes

    grant(prep_lab)
    write(prep_lab)
    saved = save(prep_lab, preview(prep_lab, 1)).json()
    original = routes.lesson_dispatch
    pinned = saved["learning_path"]["draft"]["plan"]["lessons"][0]["ref"]

    def unavailable(lesson_id, version):
        if (lesson_id, version) == (pinned["lesson_id"], pinned["content_version"]):
            raise ValueError("Synthetic retired version metadata is unavailable")
        return original(lesson_id, version)

    monkeypatch.setattr(routes, "lesson_dispatch", unavailable)
    read = prep_lab["client"].get(endpoint(prep_lab)).json()
    assert read["learning_path"]["draft"] == saved["learning_path"]["draft"]
    tasks = [t for t in read["learning_path"]["schedule"]["tasks"] if t["learning_ref"] == pinned]
    assert tasks and all(
        t["availability"] == "unavailable" and t["unavailable_reason"] == "version_unavailable"
        for t in tasks
    )


def test_lesson_submission_projection_shows_latest_own_exact_receipt_and_keeps_old_review(prep_lab):
    grant(prep_lab)
    write(prep_lab)
    old_payload = body(lesson="ielts-reading-1")
    old = prep_lab["client"].post(url(prep_lab, "attempts"), json=old_payload).json()
    save(prep_lab, preview(prep_lab, 1))
    new_payload = body(lesson="ielts-reading-1")
    latest = prep_lab["client"].post(url(prep_lab, "attempts"), json=new_payload).json()
    read = prep_lab["client"].get(endpoint(prep_lab)).json()
    tasks = [
        t
        for t in read["learning_path"]["schedule"]["tasks"]
        if t["learning_ref"]
        and t["learning_ref"]["kind"] == "lesson"
        and t["learning_ref"]["lesson_id"] == "ielts-reading-1"
    ]
    assert tasks and all(t["submitted_attempt_id"] == latest["attempt_id"] for t in tasks)
    assert (
        prep_lab["client"]
        .get(url(prep_lab, f"attempts/{old_payload['attempt_id']}/review"))
        .json()["attempt"]
        == old
    )
    assert any(
        ref["attempt_id"] == old["attempt_id"]
        for ref in read["learning_path"]["draft"]["plan"]["reviews"]
    )


def _sidecar_stored_calendar(lab):
    with lab["factory"]() as session:
        row = session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one()
        created = ensure_utc(row.created_at)
        updated = ensure_utc(row.updated_at)
        assert created is not None and updated is not None
        return {
            "id": row.id,
            "revision": row.revision,
            "settings": deepcopy(row.settings),
            "learning_path": deepcopy(row.learning_path),
            "created_at": created.isoformat(),
            "updated_at": updated.isoformat(),
            "updated_at_wire": row.updated_at.isoformat(),
        }


def _sidecar_create_filled_calendar(lab):
    response = write(lab)
    assert response.status_code == 200, response.text
    legacy = response.json()
    marked = deepcopy(legacy["settings"])
    marked["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
    response = write(lab, revision=1, plan=marked)
    assert response.status_code == 200, response.text
    response = save(lab, preview(lab, 2))
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == 3
    return marked


def test_export_omits_null_sidecar_and_preserves_exact_saved_snapshot(prep_lab):
    grant(prep_lab)
    response = write(prep_lab)
    assert response.status_code == 200, response.text
    raw_legacy = _sidecar_stored_calendar(prep_lab)
    response = prep_lab["client"].get(f"/api/profiles/{prep_lab['case']}/export")
    assert response.status_code == 200, response.text
    legacy_export = response.json()["study_schedules"][0]
    assert set(legacy_export) == {"revision", "settings", "updated_at"}
    assert legacy_export == {
        "revision": raw_legacy["revision"],
        "settings": raw_legacy["settings"],
        "updated_at": raw_legacy["updated_at_wire"],
    }
    assert raw_legacy["learning_path"] is None
    assert _sidecar_stored_calendar(prep_lab) == raw_legacy

    marked = deepcopy(response.json()["study_schedules"][0]["settings"])
    legacy = prep_lab["client"].get(url(prep_lab, "schedule")).json()
    marked["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
    assert write(prep_lab, revision=1, plan=marked).status_code == 200
    payload = body(lesson="ielts-reading-1")
    response = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload)
    assert response.status_code == 200, response.text
    attempt = response.json()
    proposed = preview(prep_lab, 2)
    assert (
        proposed["learning_path"]["draft"]["plan"]["reviews"][0]["attempt_id"]
        == payload["attempt_id"]
    )
    response = save(prep_lab, proposed)
    assert response.status_code == 200, response.text
    raw = _sidecar_stored_calendar(prep_lab)
    inputs = unchanged_inputs(prep_lab)
    assert raw["settings"] == raw["learning_path"]["legacy_settings"] == marked

    # A DTO may derive today's display state; export must retain the stored JSON.
    assert prep_lab["client"].get(endpoint(prep_lab)).status_code == 200
    response = prep_lab["client"].get(f"/api/profiles/{prep_lab['case']}/export")
    assert response.status_code == 200, response.text
    exported = response.json()
    assert exported["profile"] == inputs["profile"]
    assert exported["counts"]["study_schedules"] == 1
    assert exported["counts"]["study_attempts"] == 1
    assert exported["study_attempts"] == [attempt]
    assert exported["study_schedules"] == [
        {
            "revision": raw["revision"],
            "settings": raw["settings"],
            "learning_path": raw["learning_path"],
            "updated_at": raw["updated_at_wire"],
        }
    ]
    assert _sidecar_stored_calendar(prep_lab) == raw
    assert unchanged_inputs(prep_lab) == inputs


def test_delete_filled_sidecar_and_attempts_preserves_other_owned_case(prep_lab):
    grant(prep_lab)
    _sidecar_create_filled_calendar(prep_lab)
    deleted_attempt = body(lesson="ielts-reading-1")
    assert (
        prep_lab["client"].post(url(prep_lab, "attempts"), json=deleted_attempt).status_code == 200
    )
    # Include the saved review reference in the row being deleted.
    assert save(prep_lab, preview(prep_lab, 3)).status_code == 200
    deleted_row = _sidecar_stored_calendar(prep_lab)

    with prep_lab["factory"]() as session:
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        other_payload = deepcopy(own.payload)
    other_payload["display_name"] = "Synthetic sibling case"
    response = prep_lab["client"].post("/api/profiles", json=other_payload)
    assert response.status_code == 201, response.text
    other = {**prep_lab, "case": response.json()["id"]}
    _sidecar_create_filled_calendar(other)
    other_attempt = body(lesson="ielts-reading-1")
    response = other["client"].post(url(other, "attempts"), json=other_attempt)
    assert response.status_code == 200, response.text
    other_receipt = response.json()
    assert save(other, preview(other, 3)).status_code == 200
    other_row = _sidecar_stored_calendar(other)
    response = other["client"].get(f"/api/profiles/{other['case']}/export")
    assert response.status_code == 200, response.text
    other_export = response.json()

    with prep_lab["factory"]() as session:
        if prep_lab["engine"].dialect.name == "sqlite":
            # The existing fixture deliberately proves ORM cascade without FK enforcement.
            assert session.scalar(text("PRAGMA foreign_keys")) == 0
    response = prep_lab["client"].delete(f"/api/profiles/{prep_lab['case']}")
    assert response.status_code == 204, response.text
    with prep_lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is None
        assert session.get(StudyScheduleRow, deleted_row["id"]) is None
        assert session.query(StudyScheduleRow).filter_by(profile_id=prep_lab["case"]).count() == 0
        assert session.query(StudyAttempt).filter_by(profile_id=prep_lab["case"]).count() == 0
        assert session.query(StudyScheduleRow).count() == 1
        assert session.query(StudyAttempt).filter_by(profile_id=other["case"]).count() == 1
    for path in [
        url(prep_lab, "schedule"),
        endpoint(prep_lab),
        url(prep_lab, f"attempts/{deleted_attempt['attempt_id']}/review"),
        f"/api/profiles/{prep_lab['case']}/export",
    ]:
        assert prep_lab["client"].get(path).status_code == 404
    assert _sidecar_stored_calendar(other) == other_row
    response = other["client"].get(f"/api/profiles/{other['case']}/export")
    assert response.status_code == 200, response.text
    assert response.json() == other_export
    response = other["client"].get(url(other, f"attempts/{other_attempt['attempt_id']}/review"))
    assert response.status_code == 200, response.text
    assert response.json()["attempt"] == other_receipt


@pytest.mark.parametrize("winner", ["legacy", "learning"])
def test_two_http_writers_share_real_cas_and_preserve_other_json(prep_lab, monkeypatch, winner):
    from app.api import routes_preparation
    from app.main import app

    instant = utcnow()
    monkeypatch.setattr(routes_preparation, "utcnow", lambda: instant)
    grant(prep_lab)
    marked = _sidecar_create_filled_calendar(prep_lab)
    before = _sidecar_stored_calendar(prep_lab)
    assert before["settings"]["completed_task_ids"]
    payload = body(lesson="ielts-reading-1")
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).status_code == 200
    proposed = preview(prep_lab, before["revision"])
    assert (
        proposed["learning_path"]["draft"]["plan"]["reviews"][0]["attempt_id"]
        == payload["attempt_id"]
    )
    assert proposed["learning_path"]["draft"] != before["learning_path"]["draft"]
    changed = deepcopy(marked)
    changed["weekly_minutes"] += 60
    changed["completed_task_ids"] = []  # Explicit reset for the new structure's task IDs.
    inputs = unchanged_inputs(prep_lab)
    requests = {
        "legacy": (
            url(prep_lab, "schedule"),
            {
                "expected_revision": before["revision"],
                "settings": changed,
            },
        ),
        "learning": (
            endpoint(prep_lab),
            {
                "expected_revision": proposed["revision"],
                "legacy_fingerprint": proposed["legacy_fingerprint"],
                "draft": proposed["learning_path"]["draft"],
            },
        ),
    }
    arrived = Barrier(2, timeout=5)
    winner_finished = Event()
    mutex = Lock()
    seen = []

    def before_update(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.lower().replace('"', "").split())
        if not sql.startswith("update study_schedules set "):
            return
        assignments = sql.partition(" where ")[0]
        role = "learning" if re.search(r"\blearning_path\s*=", assignments) else "legacy"
        with mutex:
            seen.append((role, id(conn.connection.driver_connection)))
        # Both routes have validated the same old revision before either SQL write.
        # Do not synchronize AFTER execution: SQLite's writer would hold the lock.
        arrived.wait()
        if role != winner:
            assert winner_finished.wait(timeout=10), "winner did not finish its HTTP request"

    def submit(role):
        client = TestClient(app)  # No context manager: do not run app lifespan/start workers.
        try:
            path, payload = requests[role]
            response = client.put(path, json=payload)
            return response.status_code, response.json()
        finally:
            if role == winner:
                winner_finished.set()
            client.close()

    event.listen(prep_lab["engine"], "before_cursor_execute", before_update)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {role: pool.submit(submit, role) for role in requests}
            outcomes = {role: future.result(timeout=15) for role, future in futures.items()}
    finally:
        event.remove(prep_lab["engine"], "before_cursor_execute", before_update)

    loser = "learning" if winner == "legacy" else "legacy"
    assert outcomes[winner][0] == 200, outcomes
    assert outcomes[loser][0] == 409, outcomes
    assert sorted(role for role, _ in seen) == ["learning", "legacy"]
    assert len({connection for _, connection in seen}) == 2
    after = _sidecar_stored_calendar(prep_lab)
    assert after["id"] == before["id"] and after["created_at"] == before["created_at"]
    assert after["revision"] == before["revision"] + 1
    assert outcomes[winner][1]["revision"] == after["revision"]
    if winner == "legacy":
        assert after["settings"] == changed == outcomes[winner][1]["settings"]
        assert after["learning_path"] == before["learning_path"]
        assert prep_lab["client"].get(endpoint(prep_lab)).json()["needs_review"] is True
    else:
        assert after["settings"] == marked == before["settings"]
        assert after["learning_path"] == proposed["learning_path"]
        current = prep_lab["client"].get(endpoint(prep_lab)).json()
        assert outcomes[winner][1]["learning_path"] == current["learning_path"]
        exact_tasks = [
            task
            for task in current["learning_path"]["schedule"]["tasks"]
            if task["learning_ref"]
            and task["learning_ref"]["kind"] == "lesson"
            and task["learning_ref"]["lesson_id"] == payload["lesson_id"]
            and task["learning_ref"]["content_version"] == payload["content_version"]
        ]
        assert exact_tasks and all(
            task["submitted_attempt_id"] == payload["attempt_id"] for task in exact_tasks
        )
        assert after["learning_path"]["draft"] == proposed["learning_path"]["draft"]
        assert after["learning_path"]["legacy_settings"] == marked
        assert prep_lab["client"].get(endpoint(prep_lab)).json()["needs_review"] is False
    assert unchanged_inputs(prep_lab) == inputs
