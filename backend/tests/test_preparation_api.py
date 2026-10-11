"""Preparation uses owned synthetic cases and migration-backed SQLite/PostgreSQL.

No provider/worker/search calls. TestClient skips lifespan intentionally: these
controls exercise the actual registered HTTP routes without startup job reconciliation.
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    ClaimRow,
    Entitlement,
    Job,
    Order,
    Organization,
    ProgramResultRow,
    ResearchRun,
    StudyAttempt,
    Subscription,
)
from app.models.base import utcnow
from app.preparation.catalogue import CONTENT_VERSION
from app.schemas.claim import Claim
from app.security import DEV_ORGANIZATION_ID
from tests.conftest import configure_from_env


@pytest.fixture(params=["sqlite", "postgres"])
def prep_lab(request, tmp_path, monkeypatch, corpus_dir):
    """Native migrated database; no process-global Settings replacement or startup jobs."""
    from app.config import get_settings
    from app.corpus.demo_profile import DEMO_PROFILE
    from app.db import migrate_to_head

    configure_from_env(
        monkeypatch,
        tmp_path,
        corpus_dir,
        UNIMATCH_PAYMENTS_ENABLED="true",
        UNIMATCH_AUTH_ENABLED="false",
    )
    if request.param == "postgres":
        engine = request.getfixturevalue("pg_engine")
    else:
        url = f"sqlite:///{tmp_path / 'preparation.db'}"
        migrate_to_head(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
    import app.db as db_module
    from app.main import app

    monkeypatch.setattr(db_module, "engine", engine)
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    attempts = []
    native_connect = socket.socket.connect
    native_connect_ex = socket.socket.connect_ex
    native_sendto = socket.socket.sendto

    def connect(sock, address):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            attempts.append("connect")
            raise AssertionError("Preparation tests must not open IP connections")
        return native_connect(sock, address)

    def connect_ex(sock, address):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            attempts.append("connect_ex")
            raise AssertionError("Preparation tests must not open IP connections")
        return native_connect_ex(sock, address)

    def sendto(sock, *args):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            attempts.append("sendto")
            raise AssertionError("Preparation tests must not send IP packets")
        return native_sendto(sock, *args)

    def dns(*_args, **_kwargs):
        attempts.append("getaddrinfo")
        raise AssertionError("Preparation tests have no DNS dependency")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", sendto)
    monkeypatch.setattr(socket, "getaddrinfo", dns)
    client = TestClient(app)
    response = client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json"))
    assert response.status_code == 201
    lab = {
        "client": client,
        "case": response.json()["id"],
        "factory": factory,
        "engine": engine,
        "monkeypatch": monkeypatch,
    }
    try:
        yield lab
    finally:
        client.close()
        get_settings.cache_clear()
        if request.param == "sqlite":
            engine.dispose()
        assert attempts == []


def url(lab, suffix):
    return f"/api/profiles/{lab['case']}/preparation/{suffix}"


def grant(lab, *, status="active", start=None, end=None, quota=0):
    now = utcnow()
    with lab["factory"]() as session:
        row = Subscription(
            organization_id=DEV_ORGANIZATION_ID,
            case_quota=quota,
            duration_days=30,
            status=status,
            starts_at=start if start is not None else now - timedelta(days=1),
            ends_at=end if end is not None else now + timedelta(days=29),
        )
        session.add(row)
        session.commit()
        return row.id


def body(*, lesson="sat-math-1", attempt_id=None):
    questions = {
        "sat-math-1": [("sm-1", "b"), ("sm-2", "a"), ("sm-3", "c")],
        "ielts-reading-1": [("ir-1", "b"), ("ir-2", "c"), ("ir-3", "a")],
        "sat-rw-1": [("sr-1", "b"), ("sr-2", "c"), ("sr-3", "a")],
    }
    return {
        "attempt_id": str(attempt_id or uuid4()),
        "lesson_id": lesson,
        "version": CONTENT_VERSION,
        "answers": [
            {"question_id": question, "choice_id": choice} for question, choice in questions[lesson]
        ],
    }


def full_case(lab):
    with lab["factory"]() as session:
        session.add(
            Entitlement(
                organization_id=DEV_ORGANIZATION_ID, profile_id=lab["case"], kind="case_full"
            )
        )
        session.commit()


def result_with_claim(
    lab,
    *,
    kind="ielts_min_overall",
    value=6.5,
    label="IELTS overall",
    status="GAP",
    claim_status="VERIFIED_CURRENT",
    scope=True,
    stale=False,
    reference="url",
):
    from app.domain.claim_scope import ClaimScope
    from app.schemas.result import RequirementCheck

    with lab["factory"]() as session:
        profile = session.get(ApplicantProfileRow, lab["case"])
        context = profile.payload["context"]
        run = ResearchRun(profile_id=lab["case"], stage="complete", demo_mode=True)
        session.add(run)
        session.flush()
        row = ProgramResultRow(
            run_id=run.id,
            dedupe_key=uuid4().hex,
            university="Synthetic Uni",
            university_key="synthetic-uni",
            country="Synthetic",
            program="BSc",
            eligibility="GAP",
            admissions_fit="INSUFFICIENT_DATA",
            funding_fit="UNKNOWN",
            funding_classification="UNKNOWN",
            payload={},
        )
        session.add(row)
        session.flush()
        claim = Claim(
            claim_type=kind,
            normalized_value=value,
            source_url="https://example.edu/requirements",
            official_domain=True,
            accessed_at=utcnow() - timedelta(days=365 if stale else 0),
            status=claim_status,
            source_specificity="program_intake",
            original_text_excerpt="Synthetic policy: use only in tests.",
            scope=ClaimScope(
                university=row.university,
                programme=row.program,
                degree=context["level"],
                intake=f"{context['intake_term']} {context['intake_year']}",
                nationality=context["citizenship"],
                residency=context["country_of_residence"],
                qualification=context["education_system"],
            )
            if scope
            else None,
        )
        stored = ClaimRow(
            run_id=run.id,
            result_id=row.id,
            claim_type=kind,
            status=claim_status,
            source_url=claim.source_url,
            accessed_at=claim.accessed_at,
            source_specificity="program_intake",
            payload=claim.model_dump(mode="json"),
        )
        session.add(stored)
        session.flush()
        check = RequirementCheck(
            requirement=label,
            published_value=value,
            applicant_value=6,
            status=status,
            explanation="Synthetic preserved gap explanation",
            published_scope="Synthetic international fall intake",
            claim_ids=[stored.id if reference == "id" else claim.source_url],
        )
        row.payload = {"requirement_checks": [check.model_dump(mode="json")]}
        session.commit()
        return row.id, stored.id, check.model_dump(mode="json")


def test_public_catalogue_is_answer_free_and_planned_courses_have_no_lessons(prep_lab):
    response = prep_lab["client"].get("/api/preparation/catalogue")
    assert response.status_code == 200
    catalogue = response.json()
    assert catalogue["version"] == CONTENT_VERSION
    assert len(catalogue["lessons"]) == 3 and len(catalogue["exams"]) == 6
    assert all(
        not exam["track_ids"] for exam in catalogue["exams"] if exam["course_status"] == "planned"
    )
    assert "correct_choice_id" not in response.text and "explanation" not in response.text
    assert "question" not in catalogue["lessons"][0]  # only public metadata


@pytest.mark.parametrize("status", ["active", "exhausted"])
def test_zero_research_quota_does_not_remove_started_term_learning(prep_lab, status):
    sub_id = grant(prep_lab, status=status, quota=0)
    response = prep_lab["client"].get(url(prep_lab, "access"))
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["subscription_id"] == sub_id
    billing = prep_lab["client"].get(
        "/api/billing/entitlements", params={"profile_id": prep_lab["case"]}
    )
    assert billing.status_code == 200
    assert billing.json()["full_access"] is False
    assert billing.json()["preparation_access"] == response.json()
    lesson = prep_lab["client"].get(
        url(prep_lab, "lessons/sat-math-1"), params={"version": CONTENT_VERSION}
    )
    assert lesson.status_code == 200
    assert "correct_choice_id" not in lesson.text and "explanation" not in lesson.text


@pytest.mark.parametrize(
    "mode",
    [
        "none",
        "pending",
        "cancelled",
        "expired",
        "missing_start",
        "missing_end",
        "future_start",
        "past_end",
        "reversed",
    ],
)
def test_invalid_or_unstarted_term_fails_closed_without_mutation(prep_lab, mode):
    if mode != "none":
        sub_id = grant(
            prep_lab, status=mode if mode in {"pending", "cancelled", "expired"} else "active"
        )
        with prep_lab["factory"]() as session:
            subscription = session.get(Subscription, sub_id)
            if mode == "missing_start":
                subscription.starts_at = None
            elif mode == "missing_end":
                subscription.ends_at = None
            elif mode == "future_start":
                subscription.starts_at = utcnow() + timedelta(days=1)
            elif mode == "past_end":
                subscription.ends_at = utcnow() - timedelta(seconds=1)
            elif mode == "reversed":
                subscription.ends_at = subscription.starts_at - timedelta(days=1)
            session.commit()
            before = (
                subscription.status,
                subscription.starts_at,
                subscription.ends_at,
                subscription.case_quota,
            )
    assert prep_lab["client"].get(url(prep_lab, "access")).json()["allowed"] is False
    denial = prep_lab["client"].post(url(prep_lab, "attempts"), json=body())
    assert denial.status_code == 402
    assert denial.json()["detail"]["code"] == "preparation_subscription_required"
    assert prep_lab["client"].get(url(prep_lab, "progress")).json()["attempt_count"] == 0
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 0
        if mode != "none":
            subscription = session.get(Subscription, sub_id)
            assert (
                subscription.status,
                subscription.starts_at,
                subscription.ends_at,
                subscription.case_quota,
            ) == before


def test_development_access_is_explicit_not_a_paid_entitlement(prep_lab):
    from app.config import get_settings

    prep_lab["monkeypatch"].setenv("UNIMATCH_PAYMENTS_ENABLED", "false")
    get_settings.cache_clear()
    access = prep_lab["client"].get(url(prep_lab, "access")).json()
    assert access["allowed"] and access["development_only"]
    assert access["reason"] == "development_mode" and access["subscription_id"] is None


@pytest.mark.parametrize("suffix", ["access", "progress", "plan", "lessons/sat-math-1"])
def test_foreign_and_missing_case_are_indistinguishable_404(prep_lab, suffix):
    with prep_lab["factory"]() as session:
        org = Organization(name="Other", slug=uuid4().hex)
        session.add(org)
        session.flush()
        profile = session.get(ApplicantProfileRow, prep_lab["case"])
        foreign = ApplicantProfileRow(organization_id=org.id, payload=profile.payload)
        session.add(foreign)
        session.commit()
        foreign_id = foreign.id
    for case in (foreign_id, uuid4().hex):
        endpoint = f"/api/profiles/{case}/preparation/{suffix}"
        assert (
            prep_lab["client"].get(endpoint, params={"version": CONTENT_VERSION}).status_code == 404
        )
        assert (
            prep_lab["client"]
            .post(f"/api/profiles/{case}/preparation/attempts", json=body())
            .status_code
            == 404
        )


@pytest.mark.parametrize(
    "invalid",
    [
        "incomplete",
        "duplicate",
        "unknown_question",
        "unknown_choice",
        "old_version",
        "unknown_lesson",
        "bad_uuid",
        "extra_text",
    ],
)
def test_invalid_attempts_reveal_no_answers_and_persist_nothing(prep_lab, invalid):
    grant(prep_lab)
    payload = body()
    if invalid == "incomplete":
        payload["answers"].pop()
    elif invalid == "duplicate":
        payload["answers"][1] = payload["answers"][0]
    elif invalid == "unknown_question":
        payload["answers"][0]["question_id"] = "unknown"
    elif invalid == "unknown_choice":
        payload["answers"][0]["choice_id"] = "unknown"
    elif invalid == "old_version":
        payload["version"] = "unknown-version"
    elif invalid == "unknown_lesson":
        payload["lesson_id"] = "hsk-unpublished"
    elif invalid == "bad_uuid":
        payload["attempt_id"] = "not-a-uuid"
    else:
        payload["essay"] = "Not part of the bounded input contract"
    response = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload)
    assert response.status_code == 422
    assert "correct_choice_id" not in response.text
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 0


@pytest.mark.parametrize("lesson", ["ielts-reading-1", "sat-math-1", "sat-rw-1"])
def test_grading_replay_conflict_and_progress_are_case_scoped(prep_lab, lesson):
    grant(prep_lab)
    payload = body(lesson=lesson)
    response = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload)
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["correct"] == receipt["total"] == 3
    assert all(item["correct"] and item["explanation"] for item in receipt["feedback"])
    assert receipt["profile_id"] == prep_lab["case"]
    assert "band" not in receipt and "official_score" not in receipt
    payload["answers"].reverse()
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json() == receipt
    payload["answers"][0]["choice_id"] = "a" if payload["answers"][0]["choice_id"] != "a" else "b"
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).status_code == 409
    progress = prep_lab["client"].get(url(prep_lab, "progress")).json()
    assert progress["attempt_count"] == 1 and progress["correct"] == progress["answered"] == 3
    assert progress["completed_lesson_ids"] == [lesson] and progress["attempts"] == [receipt]
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 1
        assert session.query(Order).count() == session.query(Entitlement).count() == 0
        assert session.query(ResearchRun).count() == session.query(Job).count() == 0
        assert session.query(Subscription).one().case_quota == 0
        profile = session.get(ApplicantProfileRow, prep_lab["case"])
        original = profile.payload
        assert not any("study" in event.action for event in session.query(AuditEvent).all())
    exported = prep_lab["client"].get(f"/api/profiles/{prep_lab['case']}/export").json()
    assert exported["study_attempts"] == [receipt] and exported["profile"] == original
    assert exported["counts"]["study_attempts"] == 1


def test_wrong_answers_and_history_after_term_end_do_not_become_scores(prep_lab):
    sub_id = grant(prep_lab)
    payload = body()
    payload["answers"][0]["choice_id"] = "a"
    receipt = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json()
    assert receipt["correct"] == 2 and receipt["total"] == 3
    assert receipt["feedback"][0]["correct_choice_id"] == "b"
    with prep_lab["factory"]() as session:
        session.get(Subscription, sub_id).ends_at = utcnow() - timedelta(seconds=1)
        session.commit()
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json() == receipt
    assert prep_lab["client"].get(url(prep_lab, "progress")).json()["attempts"] == [receipt]
    payload["attempt_id"] = str(uuid4())
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).status_code == 402


def test_uuid_may_be_reused_in_a_different_owned_case(prep_lab):
    grant(prep_lab)
    with prep_lab["factory"]() as session:
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        other = ApplicantProfileRow(organization_id=DEV_ORGANIZATION_ID, payload=own.payload)
        session.add(other)
        session.commit()
        other_id = other.id
    payload = body()
    first = prep_lab["client"].post(url(prep_lab, "attempts"), json=payload).json()
    second = (
        prep_lab["client"]
        .post(f"/api/profiles/{other_id}/preparation/attempts", json=payload)
        .json()
    )
    assert first["id"] != second["id"] and first["attempt_id"] == second["attempt_id"]
    assert second["profile_id"] == other_id
    assert prep_lab["client"].get(url(prep_lab, "progress")).json()["attempt_count"] == 1


@pytest.mark.parametrize("reference", ["url", "id"])
def test_plan_preserves_requirement_claim_scope_quote_and_both_reference_forms(prep_lab, reference):
    full_case(prep_lab)
    result_id, claim_id, check = result_with_claim(prep_lab, reference=reference)
    response = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id})
    assert response.status_code == 200
    plan = response.json()
    assert plan["evidence_state"] == "current" and plan["research_access"] is True
    row = plan["checks"][0]
    assert row["requirement_check"] == check and row["claim_ids"] == check["claim_ids"]
    assert row["policy"] == "required" and row["lesson_ids"] == ["ielts-reading-1"]
    assert row["claims"][0]["id"] == claim_id and row["claims"][0]["scope"]["programme"] == "BSc"
    assert row["claims"][0]["original_text_excerpt"] == "Synthetic policy: use only in tests."
    assert row["source_urls"] == ["https://example.edu/requirements"]


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("no_scope", "unknown"),
        ("wrong_scope", "unknown"),
        ("old", "stale"),
        ("conflict", "conflicted"),
        ("profile_changed", "stale"),
        ("unknown_ref", "unknown"),
    ],
)
def test_plan_never_upgrades_unknown_conflicting_or_old_evidence(prep_lab, mode, expected):
    full_case(prep_lab)
    result_id, claim_id, _ = result_with_claim(
        prep_lab,
        scope=mode != "no_scope",
        stale=mode == "old",
        claim_status="CONFLICTING" if mode == "conflict" else "VERIFIED_CURRENT",
    )
    with prep_lab["factory"]() as session:
        if mode == "wrong_scope":
            claim = session.get(ClaimRow, claim_id)
            payload = dict(claim.payload)
            payload["scope"] = {**payload["scope"], "intake": "fall 2026"}
            claim.payload = payload
        elif mode == "profile_changed":
            session.get(ApplicantProfileRow, prep_lab["case"]).updated_at = utcnow() + timedelta(
                seconds=1
            )
        elif mode == "unknown_ref":
            result = session.get(ProgramResultRow, result_id)
            payload = dict(result.payload)
            payload["requirement_checks"] = [
                {**payload["requirement_checks"][0], "claim_ids": ["unresolved-id"]}
            ]
            result.payload = payload
        session.commit()
    plan = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id}).json()
    assert plan["evidence_state"] == expected
    assert plan["checks"][0]["policy"] == "unknown" and plan["checks"][0]["lesson_ids"] == []


def test_locked_result_and_other_case_result_do_not_disclose_evidence(prep_lab):
    result_id, _, _ = result_with_claim(prep_lab)
    response = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id}).json()
    assert response["evidence_state"] == "locked" and response["checks"] == []
    full_case(prep_lab)
    assert prep_lab["client"].get(url(prep_lab, "plan")).json()["evidence_state"] == "unknown"
    with prep_lab["factory"]() as session:
        org = Organization(name="Foreign", slug=uuid4().hex)
        session.add(org)
        session.flush()
        own = session.get(ApplicantProfileRow, prep_lab["case"])
        foreign = ApplicantProfileRow(organization_id=org.id, payload=own.payload)
        session.add(foreign)
        session.flush()
        run = ResearchRun(profile_id=foreign.id)
        session.add(run)
        session.flush()
        result = session.get(ProgramResultRow, result_id)
        result.run_id = run.id
        session.commit()
    assert (
        prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id}).status_code
        == 404
    )


def test_orm_deleting_profile_erases_attempts_even_with_sqlite_foreign_keys_off(prep_lab):
    grant(prep_lab)
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=body()).status_code == 200
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 1
        profile = session.get(ApplicantProfileRow, prep_lab["case"])
        # SQLite engine in this fixture has FK enforcement off (no db.py listener).
        if prep_lab["engine"].dialect.name == "sqlite":
            from sqlalchemy import text

            assert session.scalar(text("PRAGMA foreign_keys")) == 0
        session.delete(profile)
        session.commit()
        assert session.query(StudyAttempt).count() == 0
    assert prep_lab["client"].get(url(prep_lab, "progress")).status_code == 404


def test_migration_schema_and_unique_payload_binding(prep_lab):
    from sqlalchemy.exc import IntegrityError

    grant(prep_lab)
    receipt = prep_lab["client"].post(url(prep_lab, "attempts"), json=body()).json()
    schema = inspect(prep_lab["engine"])
    assert "study_attempts" in schema.get_table_names()
    assert any(
        index["unique"] and index["column_names"] == ["profile_id", "client_attempt_id"]
        for index in schema.get_indexes("study_attempts")
    )
    assert any(
        fk["referred_table"] == "applicant_profiles" and fk["options"].get("ondelete") == "CASCADE"
        for fk in schema.get_foreign_keys("study_attempts")
    )
    with prep_lab["factory"]() as session:
        original = session.get(StudyAttempt, receipt["id"])
        duplicate = StudyAttempt(
            profile_id=original.profile_id,
            client_attempt_id=original.client_attempt_id,
            lesson_id=original.lesson_id,
            content_version=original.content_version,
            request_digest=original.request_digest,
            answers=original.answers,
            feedback=original.feedback,
            correct=original.correct,
            total=original.total,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.query(StudyAttempt).count() == 1


def test_progress_limit_does_not_change_aggregate_or_create_an_official_score(prep_lab):
    grant(prep_lab)
    for _ in range(2):
        assert prep_lab["client"].post(url(prep_lab, "attempts"), json=body()).status_code == 200
    result = prep_lab["client"].get(url(prep_lab, "progress"), params={"limit": 1}).json()
    assert result["attempt_count"] == 2 and result["correct"] == result["answered"] == 6
    assert len(result["attempts"]) == 1 and result["completed_lesson_ids"] == ["sat-math-1"]
    assert prep_lab["client"].get(url(prep_lab, "progress"), params={"limit": 0}).status_code == 422


def test_access_term_has_exact_start_and_end_boundaries_without_retiring_rows(prep_lab):
    from app.payments.preparation import preparation_access

    moment = datetime(2026, 10, 11, tzinfo=UTC)
    sub_id = grant(prep_lab, start=moment, end=moment + timedelta(days=1))
    with prep_lab["factory"]() as session:
        assert preparation_access(session, DEV_ORGANIZATION_ID, now=moment).allowed
        assert not preparation_access(
            session, DEV_ORGANIZATION_ID, now=moment - timedelta(microseconds=1)
        ).allowed
        assert not preparation_access(
            session, DEV_ORGANIZATION_ID, now=moment + timedelta(days=1)
        ).allowed
        subscription = session.get(Subscription, sub_id)
        assert subscription.status == "active" and subscription.case_quota == 0


def test_migration_down_and_up_preserve_existing_owned_profile(prep_lab):
    from alembic import command

    from app.db import _alembic_config, migrate_to_head

    target = prep_lab["engine"].url.render_as_string(hide_password=False)
    config = _alembic_config(target)
    command.downgrade(config, "d8e412c6a901")
    assert "study_attempts" not in inspect(prep_lab["engine"]).get_table_names()
    with prep_lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is not None
    migrate_to_head(target)
    assert "study_attempts" in inspect(prep_lab["engine"]).get_table_names()
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 0
        assert session.get(ApplicantProfileRow, prep_lab["case"]) is not None


def test_catalogue_is_public_but_case_learning_requires_auth_when_enabled(prep_lab):
    from app.config import get_settings

    prep_lab["monkeypatch"].setenv("UNIMATCH_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    assert prep_lab["client"].get("/api/preparation/catalogue").status_code == 200
    assert prep_lab["client"].get(url(prep_lab, "access")).status_code == 401
    assert prep_lab["client"].get(url(prep_lab, "progress")).status_code == 401


def test_foreign_organization_subscription_does_not_grant_learning(prep_lab):
    with prep_lab["factory"]() as session:
        organization = Organization(name="Other subscription", slug=uuid4().hex)
        session.add(organization)
        session.flush()
        session.add(
            Subscription(
                organization_id=organization.id,
                case_quota=None,
                duration_days=30,
                status="active",
                starts_at=utcnow() - timedelta(days=1),
                ends_at=utcnow() + timedelta(days=29),
            )
        )
        session.commit()
    assert prep_lab["client"].get(url(prep_lab, "access")).json()["allowed"] is False


# HTTP provenance controls use only prep_lab's owned synthetic migrated databases.
def test_plan_shared_legacy_page_excludes_nonexam_checks_and_binds_each_exam_component(prep_lab):
    from app.schemas.result import RequirementCheck

    full_case(prep_lab)
    result_id, overall_id, _ = result_with_claim(prep_lab)
    with prep_lab["factory"]() as session:
        template = session.get(ClaimRow, overall_id)
        page = template.source_url
        definitions = [
            ("deadline", "admission_deadline", "2027-12-01"),
            ("gpa", "min_gpa", 3.5),
            ("sat", "sat_min_total", 1300),
            ("sat-policy", "sat_policy", "required"),
            ("accepted", "ielts_accepted_types", ["academic"]),
            ("bands", "ielts_min_subscore", {"reading": 6.5, "writing": 6.5}),
        ]
        ids = {"overall": overall_id}
        originals = {overall_id: dict(template.payload)}
        for key, kind, value in definitions:
            evidence = Claim.model_validate(
                {
                    **template.payload,
                    "claim_type": kind,
                    "normalized_value": value,
                    "original_text_excerpt": f"Synthetic {key} evidence; not an official rule.",
                }
            )
            stored = ClaimRow(
                run_id=template.run_id,
                result_id=result_id,
                claim_type=kind,
                status="VERIFIED_CURRENT",
                source_url=page,
                accessed_at=template.accessed_at,
                source_specificity=template.source_specificity,
                payload=evidence.model_dump(mode="json"),
            )
            session.add(stored)
            session.flush()
            ids[key] = stored.id
            originals[stored.id] = dict(stored.payload)
        check_values = [
            ("Admission deadline", "2027-12-01"),
            ("Minimum GPA", 3.5),
            ("SAT total", 1300),
            ("SAT policy", "required"),
            ("Accepted IELTS test type", ["academic"]),
            ("IELTS overall", 6.5),
            ("IELTS writing", 6.5),
            ("IELTS reading", 6.5),
        ]
        checks = [
            RequirementCheck(
                requirement=label,
                published_value=value,
                applicant_value=6,
                status="PENDING",
                explanation=f"Preserve synthetic {label} check verbatim.",
                published_scope="Synthetic owned programme and intake",
                claim_ids=[page],
            ).model_dump(mode="json")
            for label, value in check_values
        ]
        result = session.get(ProgramResultRow, result_id)
        result.payload = {"requirement_checks": checks}
        session.commit()
        attempts_before = session.query(StudyAttempt).count()
        jobs_before = session.query(Job).count()
    response = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id})
    assert response.status_code == 200
    rows = response.json()["checks"]
    assert [row["requirement_check"] for row in rows] == checks[2:]
    expected_keys = ["sat", "sat-policy", "accepted", "overall", "bands", "bands"]
    assert [[item["id"] for item in row["claims"]] for row in rows] == [
        [ids[key]] for key in expected_keys
    ]
    assert [row["lesson_ids"] for row in rows] == [
        ["sat-math-1", "sat-rw-1"],
        [],
        [],
        ["ielts-reading-1"],
        [],
        ["ielts-reading-1"],
    ]
    assert all(row["evidence_state"] == "current" for row in rows)
    for row in rows:
        assert row["claim_ids"] == [page] and row["source_urls"] == [page]
        evidence = row["claims"][0]
        original = originals[evidence["id"]]
        assert evidence["normalized_value"] == original["normalized_value"]
        assert evidence["original_text_excerpt"] == original["original_text_excerpt"]
        assert evidence["scope"] == original["scope"]
    with prep_lab["factory"]() as session:
        assert session.get(ProgramResultRow, result_id).payload == {"requirement_checks": checks}
        assert session.query(StudyAttempt).count() == attempts_before
        assert session.query(Job).count() == jobs_before
        assert all(session.get(ClaimRow, key).payload == value for key, value in originals.items())


@pytest.mark.parametrize("reference", ["url", "id", "id_and_url"])
def test_plan_shared_page_ambiguity_cannot_upgrade_but_exact_id_keeps_only_its_claim(
    prep_lab, reference
):
    full_case(prep_lab)
    result_id, target_id, original = result_with_claim(prep_lab, reference="id")
    with prep_lab["factory"]() as session:
        target = session.get(ClaimRow, target_id)
        page = target.source_url
        for kind, value in (("ielts_min_overall", 7), ("sat_min_total", 1300)):
            evidence = Claim.model_validate(
                {**target.payload, "claim_type": kind, "normalized_value": value}
            )
            session.add(
                ClaimRow(
                    run_id=target.run_id,
                    result_id=result_id,
                    claim_type=kind,
                    status="VERIFIED_CURRENT",
                    source_url=page,
                    accessed_at=target.accessed_at,
                    source_specificity=target.source_specificity,
                    payload=evidence.model_dump(mode="json"),
                )
            )
        refs = {"url": [page], "id": [target_id], "id_and_url": [target_id, page]}[reference]
        original = {**original, "claim_ids": refs}
        session.get(ProgramResultRow, result_id).payload = {"requirement_checks": [original]}
        session.commit()
    response = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": result_id})
    assert response.status_code == 200
    row = response.json()["checks"][0]
    assert row["requirement_check"] == original and row["claim_ids"] == refs
    if reference == "url":
        assert row["evidence_state"] == "unknown" and row["policy"] == "unknown"
        assert row["claims"] == [] and row["source_urls"] == [] and row["lesson_ids"] == []
    else:
        assert [item["id"] for item in row["claims"]] == [target_id]
        assert row["evidence_state"] == "current" and row["policy"] == "required"
        assert row["source_urls"] == [page] and row["lesson_ids"] == ["ielts-reading-1"]
