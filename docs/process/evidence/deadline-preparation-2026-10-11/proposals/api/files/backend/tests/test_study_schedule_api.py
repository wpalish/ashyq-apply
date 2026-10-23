"""Applicant-entered calendars: native owned HTTP routes and migrated databases.

Reuse the preparation lab's synthetic identities, SQLite/private PostgreSQL,
native migrations, no-lifespan TestClient and outbound-network refusals. These
controls do not book an exam, search, grade an official test or predict a score.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    Entitlement,
    Job,
    Order,
    Organization,
    ResearchRun,
    StudyAttempt,
    StudyScheduleRow,
    Subscription,
)
from app.models.base import ensure_utc, utcnow
from tests.test_preparation_api import grant, url

pytest_plugins = ("tests.test_preparation_api",)


def settings():
    today = utcnow().date()
    return {
        "exam": "ielts_academic",
        "starts_on": today.isoformat(),
        "certificate_deadline": (today + timedelta(days=90)).isoformat(),
        "first_exam_on": (today + timedelta(days=60)).isoformat(),
        "retake_on": None,
        "result_wait_days": 5,
        "delivery_days": 2,
        "safety_days": 7,
        "timezone": "UTC",
        "weekly_minutes": 240,
        "study_days": [0, 1, 2, 3, 4],
        "target_scores": {
            "overall": 7,
            "listening": 6.5,
            "reading": 6.5,
            "writing": 6.5,
            "speaking": 6.5,
        },
        "baseline_scores": {
            "overall": 6,
            "listening": 6,
            "reading": 6,
            "writing": 6,
            "speaking": 6,
        },
        "baseline_on": today.isoformat(),
        "confirmed_planning_dates": True,
        "completed_task_ids": [],
    }


def write(lab, *, revision=0, plan=None, case=None):
    endpoint = (
        url(lab, "schedule") if case is None else f"/api/profiles/{case}/preparation/schedule"
    )
    return lab["client"].put(
        endpoint,
        json={"expected_revision": revision, "settings": settings() if plan is None else plan},
    )


def unchanged_inputs(lab):
    """Read only the synthetic applicant and research/payment state relevant here."""
    with lab["factory"]() as session:
        profile = session.get(ApplicantProfileRow, lab["case"])
        return {
            "profile": deepcopy(profile.payload),
            "updated_at": ensure_utc(profile.updated_at),
            "subscriptions": [
                (
                    row.id,
                    row.status,
                    row.case_quota,
                    ensure_utc(row.starts_at),
                    ensure_utc(row.ends_at),
                    ensure_utc(row.updated_at),
                )
                for row in session.query(Subscription).order_by(Subscription.id).all()
            ],
            "counts": {
                model.__tablename__: session.query(model).count()
                for model in (ResearchRun, Job, Order, Entitlement, StudyAttempt, AuditEvent)
            },
        }


def test_empty_schedule_read_is_owned_history_without_a_subscription_or_insert(prep_lab):
    before = unchanged_inputs(prep_lab)
    response = prep_lab["client"].get(url(prep_lab, "schedule"))
    assert response.status_code == 200
    assert response.json() == {
        "profile_id": prep_lab["case"],
        "revision": 0,
        "settings": None,
        "schedule": None,
        "updated_at": None,
    }
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 0
    assert unchanged_inputs(prep_lab) == before


def test_foreign_and_missing_schedule_get_and_put_are_indistinguishable_404(prep_lab):
    grant(prep_lab)
    with prep_lab["factory"]() as session:
        organization = Organization(name="Other synthetic tenant", slug=uuid4().hex)
        session.add(organization)
        session.flush()
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        foreign = ApplicantProfileRow(
            organization_id=organization.id, payload=deepcopy(own.payload)
        )
        session.add(foreign)
        session.commit()
        foreign_id = foreign.id
    before = unchanged_inputs(prep_lab)
    for case in (foreign_id, uuid4().hex):
        endpoint = f"/api/profiles/{case}/preparation/schedule"
        assert prep_lab["client"].get(endpoint).status_code == 404
        assert write(prep_lab, case=case).status_code == 404
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 0
    assert unchanged_inputs(prep_lab) == before


def test_owned_cases_have_independent_calendars_and_revisions(prep_lab):
    grant(prep_lab)
    with prep_lab["factory"]() as session:
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        other = ApplicantProfileRow(
            organization_id=own.organization_id, payload=deepcopy(own.payload)
        )
        session.add(other)
        session.commit()
        other_id = other.id
    first_settings = settings()
    first = write(prep_lab, plan=first_settings)
    assert first.status_code == 200 and first.json()["revision"] == 1
    other_endpoint = f"/api/profiles/{other_id}/preparation/schedule"
    empty = prep_lab["client"].get(other_endpoint)
    assert empty.status_code == 200 and empty.json()["revision"] == 0
    assert empty.json()["settings"] is None
    second_settings = settings()
    second_settings["weekly_minutes"] = 300
    second = write(prep_lab, plan=second_settings, case=other_id)
    assert second.status_code == 200 and second.json()["revision"] == 1
    assert second.json()["profile_id"] == other_id
    assert second.json()["settings"]["weekly_minutes"] == 300
    own_response = prep_lab["client"].get(url(prep_lab, "schedule"))
    assert own_response.status_code == 200 and own_response.json()["revision"] == 1
    assert own_response.json()["settings"] == first_settings
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 2


@pytest.mark.parametrize("status", ["active", "exhausted"])
def test_started_term_with_zero_quota_saves_without_mutating_official_or_research_state(
    prep_lab, status
):
    grant(prep_lab, status=status, quota=0)
    before = unchanged_inputs(prep_lab)
    plan = settings()
    saved = write(prep_lab, plan=plan)
    assert saved.status_code == 200
    receipt = saved.json()
    assert receipt["profile_id"] == prep_lab["case"] and receipt["revision"] == 1
    assert receipt["settings"] == plan and receipt["updated_at"] is not None
    assert receipt["schedule"]["readiness"] == "not_assessed"
    assert "official_score" not in receipt["schedule"]
    assert "admission_probability" not in receipt["schedule"]
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == receipt
    assert unchanged_inputs(prep_lab) == before


@pytest.mark.parametrize(
    "mode", ["none", "expired", "future", "pending", "cancelled", "no_start", "no_end"]
)
def test_no_eligible_term_denies_new_schedule_but_allows_read_without_state_changes(prep_lab, mode):
    if mode != "none":
        sub_id = grant(prep_lab)
        with prep_lab["factory"]() as session:
            subscription = session.get(Subscription, sub_id)
            if mode == "expired":
                subscription.ends_at = utcnow() - timedelta(days=1)
            elif mode == "future":
                subscription.starts_at = utcnow() + timedelta(days=1)
            elif mode in {"pending", "cancelled"}:
                subscription.status = mode
            elif mode == "no_start":
                subscription.starts_at = None
            else:
                subscription.ends_at = None
            session.commit()
    before = unchanged_inputs(prep_lab)
    denied = write(prep_lab)
    assert denied.status_code == 402
    assert denied.json()["detail"]["code"] == "preparation_subscription_required"
    read = prep_lab["client"].get(url(prep_lab, "schedule"))
    assert read.status_code == 200 and read.json()["revision"] == 0
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 0
    assert unchanged_inputs(prep_lab) == before


def test_expired_term_retains_saved_history_and_denies_revision_write(prep_lab):
    sub_id = grant(prep_lab)
    saved = write(prep_lab)
    assert saved.status_code == 200
    receipt = saved.json()
    with prep_lab["factory"]() as session:
        session.get(Subscription, sub_id).ends_at = utcnow() - timedelta(seconds=1)
        session.commit()
    before = unchanged_inputs(prep_lab)
    read = prep_lab["client"].get(url(prep_lab, "schedule"))
    assert read.status_code == 200 and read.json() == receipt
    edited = deepcopy(receipt["settings"])
    edited["weekly_minutes"] = 300
    assert write(prep_lab, revision=1, plan=edited).status_code == 402
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == receipt
    assert unchanged_inputs(prep_lab) == before


def test_real_revision_create_update_and_stale_writes_preserve_canonical_calendar(prep_lab):
    grant(prep_lab)
    initial = settings()
    created = write(prep_lab, plan=initial)
    assert created.status_code == 200
    first = created.json()
    assert first["revision"] == 1
    changed = deepcopy(initial)
    changed["weekly_minutes"] = 300
    assert write(prep_lab, plan=changed).status_code == 409  # creation retry cannot overwrite
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == first
    old_completion = deepcopy(changed)
    old_completion["completed_task_ids"] = [first["schedule"]["tasks"][0]["id"]]
    assert write(prep_lab, revision=1, plan=old_completion).status_code == 422
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == first
    updated = write(prep_lab, revision=1, plan=changed)
    assert updated.status_code == 200
    second = updated.json()
    assert second["revision"] == 2 and second["settings"] == changed
    task_id = second["schedule"]["tasks"][0]["id"]
    marked = deepcopy(changed)
    marked["completed_task_ids"] = [task_id]
    completion = write(prep_lab, revision=2, plan=marked)
    assert completion.status_code == 200
    third = completion.json()
    assert third["revision"] == 3 and third["settings"] == marked
    completed = [task for task in third["schedule"]["tasks"] if task["id"] == task_id]
    assert len(completed) == 1 and completed[0]["completed"] is True
    assert write(prep_lab, revision=1, plan=initial).status_code == 409
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json() == third
    with prep_lab["factory"]() as session:
        row = session.query(StudyScheduleRow).one()
        assert row.revision == 3 and row.settings == marked


@pytest.mark.parametrize("invalid", ["future_baseline", "unknown_completion"])
def test_invalid_future_diagnostic_or_unknown_completion_returns_422_without_writes(
    prep_lab, invalid
):
    grant(prep_lab)
    before = unchanged_inputs(prep_lab)
    plan = settings()
    if invalid == "future_baseline":
        plan["baseline_on"] = (utcnow().date() + timedelta(days=10)).isoformat()
    else:
        plan["completed_task_ids"] = [f"unrelated-calendar-{uuid4().hex}"]
    rejected = write(prep_lab, plan=plan)
    assert rejected.status_code == 422
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 0
    assert unchanged_inputs(prep_lab) == before


def test_personal_calendar_exports_exact_settings_without_changing_academics(prep_lab):
    grant(prep_lab)
    before = unchanged_inputs(prep_lab)
    saved = write(prep_lab)
    assert saved.status_code == 200
    receipt = saved.json()
    exported = prep_lab["client"].get(f"/api/profiles/{prep_lab['case']}/export")
    assert exported.status_code == 200
    document = exported.json()
    assert document["profile"] == before["profile"]
    assert document["counts"]["study_schedules"] == 1
    assert len(document["study_schedules"]) == 1
    calendar = document["study_schedules"][0]
    assert calendar["revision"] == receipt["revision"]
    assert calendar["settings"] == receipt["settings"]
    assert calendar["updated_at"] is not None
    assert unchanged_inputs(prep_lab) == before


def test_profile_http_delete_erases_calendar_even_with_sqlite_foreign_keys_off(prep_lab):
    grant(prep_lab)
    assert write(prep_lab).status_code == 200
    with prep_lab["factory"]() as session:
        assert session.query(StudyScheduleRow).count() == 1
        if prep_lab["engine"].dialect.name == "sqlite":
            assert session.scalar(text("PRAGMA foreign_keys")) == 0
    deleted = prep_lab["client"].delete(f"/api/profiles/{prep_lab['case']}")
    assert deleted.status_code == 204
    with prep_lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is None
        assert session.query(StudyScheduleRow).count() == 0
    assert prep_lab["client"].get(url(prep_lab, "schedule")).status_code == 404


def test_migrated_calendar_has_unique_owned_foreign_key_and_positive_revision(prep_lab):
    schema = inspect(prep_lab["engine"])
    assert "study_schedules" in schema.get_table_names()
    columns = {column["name"] for column in schema.get_columns("study_schedules")}
    assert {"id", "created_at", "updated_at", "profile_id", "revision", "settings"} <= columns
    assert any(
        constraint["column_names"] == ["profile_id"]
        for constraint in schema.get_unique_constraints("study_schedules")
    )
    assert any(
        foreign_key["constrained_columns"] == ["profile_id"]
        and foreign_key["referred_table"] == "applicant_profiles"
        and foreign_key["options"].get("ondelete") == "CASCADE"
        for foreign_key in schema.get_foreign_keys("study_schedules")
    )
    assert any(
        constraint["name"] == "ck_study_schedules_revision"
        for constraint in schema.get_check_constraints("study_schedules")
    )


def test_real_migration_down_up_removes_only_calendar_and_preserves_existing_case(prep_lab):
    from alembic import command

    from app.db import _alembic_config, migrate_to_head

    grant(prep_lab)
    assert write(prep_lab).status_code == 200
    target = prep_lab["engine"].url.render_as_string(hide_password=False)
    command.downgrade(_alembic_config(target), "f1a2b3c4d511")
    assert "study_schedules" not in inspect(prep_lab["engine"]).get_table_names()
    assert "study_attempts" in inspect(prep_lab["engine"]).get_table_names()
    with prep_lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is not None
    migrate_to_head(target)
    assert "study_schedules" in inspect(prep_lab["engine"]).get_table_names()
    with prep_lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is not None
        assert session.query(StudyScheduleRow).count() == 0
    assert prep_lab["client"].get(url(prep_lab, "schedule")).json()["revision"] == 0
