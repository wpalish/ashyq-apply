"""Owned opt-in snapshots, migrations, unchanged legacy receipts and no GET writes."""

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import inspect, text

from app.models import ApplicantProfileRow, Organization, Subscription
from app.models.base import utcnow
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
