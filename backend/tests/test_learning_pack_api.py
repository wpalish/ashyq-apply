"""Actual registered pack routes with existing isolated native SQLite/PG fixtures."""

from datetime import timedelta
from uuid import uuid4

import pytest

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
from app.models.base import utcnow
from app.preparation.catalogue import CONTENT_VERSION, catalogue
from app.preparation.learning_pack import PACK_VERSION, TRACK_ORDER
from tests.test_learning_pack_domain import EXPECTED_KEYS, SHORT_ID, pack_payload
from tests.test_preparation_api import body, grant, url

pytest_plugins = ("tests.test_preparation_api",)


def payload(lesson_id=SHORT_ID):
    data = pack_payload(lesson_id).model_dump(mode="json")
    data["attempt_id"] = str(uuid4())
    return data


def test_opt_in_catalogue_leaves_default_serialization_exact(prep_lab):
    client = prep_lab["client"]
    expected = catalogue().model_dump(mode="json")
    assert client.get("/api/preparation/catalogue").json() == expected
    assert (
        client.get(
            "/api/preparation/catalogue", params={"catalogue_version": CONTENT_VERSION}
        ).json()
        == expected
    )
    result = client.get("/api/preparation/catalogue", params={"catalogue_version": PACK_VERSION})
    assert result.status_code == 200
    data = result.json()
    assert len(data["lessons"]) == 9 and data["version"] == PACK_VERSION
    assert {track["id"]: tuple(track["lesson_ids"]) for track in data["tracks"]} == TRACK_ORDER
    assert "correct_choice_id" not in result.text and "accepted_answers" not in result.text
    assert (
        client.get(
            "/api/preparation/catalogue", params={"catalogue_version": "unknown"}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("lesson_id", EXPECTED_KEYS)
def test_pack_lesson_grading_progress_export_and_no_score_quota_research_writes(
    prep_lab, lesson_id
):
    sub_id = grant(prep_lab, status="exhausted", quota=0)
    with prep_lab["factory"]() as session:
        profile = session.get(ApplicantProfileRow, prep_lab["case"])
        original, updated = profile.payload, profile.updated_at
    client = prep_lab["client"]
    initial = client.get(url(prep_lab, f"lessons/{lesson_id}"), params={"version": PACK_VERSION})
    assert initial.status_code == 200 and len(initial.json()["questions"]) == 5
    assert (
        "correct_choice_id" not in initial.text
        and "accepted_answers" not in initial.text
        and '"explanation"' not in initial.text
    )
    submitted = payload(lesson_id)
    receipt = client.post(url(prep_lab, "attempts"), json=submitted)
    assert receipt.status_code == 200
    saved = receipt.json()
    assert saved["answers"] == submitted["answers"] and saved["correct"] == saved["total"] == 5
    assert all(item["correct"] and item["explanation"] for item in saved["feedback"])
    assert saved["profile_id"] == prep_lab["case"] and saved["version"] == PACK_VERSION
    progress = client.get(
        url(prep_lab, "progress"), params={"catalogue_version": PACK_VERSION}
    ).json()
    assert progress["completed_lessons"] == [{"lesson_id": lesson_id, "version": PACK_VERSION}]
    assert progress["completed_lesson_ids"] == [lesson_id]
    assert progress["attempts"] == [saved] and progress["correct"] == progress["answered"] == 5
    exported = client.get(f"/api/profiles/{prep_lab['case']}/export").json()
    assert exported["study_attempts"] == [saved] and exported["profile"] == original
    with prep_lab["factory"]() as session:
        profile = session.get(ApplicantProfileRow, prep_lab["case"])
        assert profile.payload == original and profile.updated_at == updated
        assert session.get(Subscription, sub_id).case_quota == 0
        assert (
            session.query(ResearchRun).count()
            == session.query(Job).count()
            == session.query(Order).count()
            == session.query(Entitlement).count()
            == session.query(StudyScheduleRow).count()
            == 0
        )
        assert not any("study" in event.action for event in session.query(AuditEvent).all())


def test_short_normalization_replay_after_expiry_and_conflict_preserves_original_receipt(
    prep_lab,
):
    sub_id = grant(prep_lab)
    data = payload()
    data["answers"][0]["text"] = "DIVIDERS."
    data["answers"][2]["text"] = "sheet"
    data["answers"][3]["text"] = "Briefing  session."
    data["answers"][4]["text"] = "code"
    client = prep_lab["client"]
    result = client.post(url(prep_lab, "attempts"), json=data)
    assert result.status_code == 200
    receipt = result.json()
    assert (
        receipt["correct"] == 5 and receipt["feedback"][3]["selected_text"] == "Briefing  session."
    )
    assert receipt["feedback"][3]["accepted_answers"] == [
        "briefing session",
        "briefing",
        "session",
    ]
    with prep_lab["factory"]() as session:
        session.get(Subscription, sub_id).ends_at = utcnow() - timedelta(seconds=1)
        session.commit()
    data["answers"].reverse()
    assert client.post(url(prep_lab, "attempts"), json=data).json() == receipt
    assert client.get(url(prep_lab, "progress")).json()["attempts"] == [receipt]
    data["answers"][0]["text"] = "download code"
    assert client.post(url(prep_lab, "attempts"), json=data).status_code == 409
    data["attempt_id"] = str(uuid4())
    assert client.post(url(prep_lab, "attempts"), json=data).status_code == 402
    assert (
        client.get(
            url(prep_lab, f"lessons/{SHORT_ID}"), params={"version": PACK_VERSION}
        ).status_code
        == 402
    )
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 1


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "duplicate",
        "unknown_question",
        "wrong_format",
        "both_fields",
        "too_long",
        "wrong_version",
        "unknown_choice",
        "short_for_starter",
    ],
)
def test_invalid_submissions_do_not_store_or_reveal_private_keys(prep_lab, failure):
    grant(prep_lab)
    data = payload()
    if failure == "missing":
        data["answers"].pop()
    elif failure == "duplicate":
        data["answers"][1] = data["answers"][0]
    elif failure == "unknown_question":
        data["answers"][0]["question_id"] = "unknown"
    elif failure == "wrong_format":
        data["answers"][0] = {
            "question_id": data["answers"][0]["question_id"],
            "choice_id": "a",
        }
    elif failure == "both_fields":
        data["answers"][0]["choice_id"] = "a"
    elif failure == "too_long":
        data["answers"][0]["text"] = "x" * 101
    elif failure == "wrong_version":
        data["version"] = CONTENT_VERSION
    elif failure == "unknown_choice":
        data = payload("sat-quadratic-structure-1")
        data["answers"][0]["choice_id"] = "unknown"
    else:
        data = body()
        data["answers"][0] = {"question_id": "sm-1", "text": "b"}
    response = prep_lab["client"].post(url(prep_lab, "attempts"), json=data)
    assert response.status_code == 422
    assert (
        "correct_choice_id" not in response.text
        and "accepted_answers" not in response.text
        and '"explanation"' not in response.text
    )
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 0


@pytest.mark.parametrize(
    "lesson_id,version",
    [("sat-math-1", PACK_VERSION), (SHORT_ID, CONTENT_VERSION), (SHORT_ID, "unknown")],
)
def test_lesson_version_is_bound_independently_of_catalogue(prep_lab, lesson_id, version):
    grant(prep_lab)
    result = prep_lab["client"].get(
        url(prep_lab, f"lessons/{lesson_id}"), params={"version": version}
    )
    assert result.status_code == 422
    assert "accepted_answers" not in result.text and "correct_choice_id" not in result.text


def test_mixed_history_is_raw_and_legacy_top_level_progress_unchanged(prep_lab):
    grant(prep_lab)
    client = prep_lab["client"]
    old = client.post(url(prep_lab, "attempts"), json=body()).json()
    short = payload()
    short["answers"][0]["text"] = "foam dividers"
    new = client.post(url(prep_lab, "attempts"), json=short).json()
    assert new["correct"] == 4
    result = client.get(url(prep_lab, "progress"), params={"limit": 1}).json()
    assert set(result) == {
        "profile_id",
        "attempt_count",
        "correct",
        "answered",
        "completed_lesson_ids",
        "attempts",
    }
    assert result["attempt_count"] == 2 and result["correct"] == 7 and result["answered"] == 8
    assert result["completed_lesson_ids"] == ["sat-math-1"] and result["attempts"] == [new]
    pack = client.get(url(prep_lab, "progress"), params={"catalogue_version": PACK_VERSION}).json()
    assert pack["completed_lessons"] == [
        {"lesson_id": SHORT_ID, "version": PACK_VERSION},
        {"lesson_id": "sat-math-1", "version": CONTENT_VERSION},
    ]
    assert pack["attempts"] == [new, old]
    assert "official_score" not in pack and "mastery" not in pack
    assert (
        client.get(url(prep_lab, "progress"), params={"catalogue_version": "unknown"}).status_code
        == 422
    )


def test_foreign_case_pack_get_post_and_progress_return_404(prep_lab):
    grant(prep_lab)
    foreign_id = uuid4().hex
    with prep_lab["factory"]() as session:
        org = Organization(name="Foreign synthetic curriculum tenant", slug=uuid4().hex)
        session.add(org)
        session.flush()
        original = session.get(ApplicantProfileRow, prep_lab["case"])
        session.add(
            ApplicantProfileRow(id=foreign_id, organization_id=org.id, payload=original.payload)
        )
        session.commit()
    endpoint = f"/api/profiles/{foreign_id}/preparation"
    client = prep_lab["client"]
    assert (
        client.get(endpoint + f"/lessons/{SHORT_ID}", params={"version": PACK_VERSION}).status_code
        == 404
    )
    assert (
        client.get(endpoint + "/progress", params={"catalogue_version": PACK_VERSION}).status_code
        == 404
    )
    assert client.post(endpoint + "/attempts", json=payload()).status_code == 404


def test_new_short_receipts_export_then_orm_delete_with_sqlite_fk_off(prep_lab):
    grant(prep_lab)
    client = prep_lab["client"]
    result = client.post(url(prep_lab, "attempts"), json=payload())
    assert result.status_code == 200
    receipt = result.json()
    assert client.get(f"/api/profiles/{prep_lab['case']}/export").json()["study_attempts"] == [
        receipt
    ]
    if prep_lab["engine"].dialect.name == "sqlite":
        with prep_lab["engine"].connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
    assert client.delete(f"/api/profiles/{prep_lab['case']}").status_code == 204
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == 0
    assert (
        client.get(
            url(prep_lab, "progress"), params={"catalogue_version": PACK_VERSION}
        ).status_code
        == 404
    )


@pytest.mark.parametrize("lesson_id", ["sat-math-1", "sat-quadratic-structure-1", SHORT_ID])
def test_stored_review_uses_exact_version_and_remains_readable_after_expiry(prep_lab, lesson_id):
    sub_id = grant(prep_lab)
    data = body() if lesson_id == "sat-math-1" else payload(lesson_id)
    client = prep_lab["client"]
    submitted = client.post(url(prep_lab, "attempts"), json=data)
    assert submitted.status_code == 200
    receipt = submitted.json()
    with prep_lab["factory"]() as session:
        session.get(Subscription, sub_id).ends_at = utcnow() - timedelta(seconds=1)
        session.commit()
        before = session.query(StudyAttempt).count()
        original = session.get(ApplicantProfileRow, prep_lab["case"]).payload
    result = client.get(url(prep_lab, f"attempts/{data['attempt_id']}/review"))
    assert result.status_code == 200
    review = result.json()
    assert review["attempt"] == receipt
    assert review["lesson"]["id"] == lesson_id and review["lesson"]["version"] == receipt["version"]
    assert len(review["lesson"]["questions"]) == receipt["total"]
    assert not any(
        key in question
        for question in review["lesson"]["questions"]
        for key in ("accepted_answers", "correct_choice_id", "explanation")
    )
    assert "review" in review["notice"]
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).count() == before
        assert session.get(ApplicantProfileRow, prep_lab["case"]).payload == original
        assert session.get(Subscription, sub_id).case_quota == 0
        assert (
            session.query(ResearchRun).count()
            == session.query(Job).count()
            == session.query(StudyScheduleRow).count()
            == 0
        )


def test_unknown_historical_version_returns_only_unchanged_stored_receipt(prep_lab):
    grant(prep_lab)
    client = prep_lab["client"]
    data = payload()
    result = client.post(url(prep_lab, "attempts"), json=data)
    assert result.status_code == 200
    receipt = result.json()
    with prep_lab["factory"]() as session:
        row = session.query(StudyAttempt).one()
        row.content_version = "retired-historical-v1"
        session.commit()
    receipt["version"] = "retired-historical-v1"
    result = client.get(url(prep_lab, f"attempts/{data['attempt_id']}/review"))
    assert result.status_code == 200
    assert result.json()["lesson"] is None
    assert result.json()["attempt"] == receipt
    assert "original lesson version is not available" in result.json()["notice"]
    with prep_lab["factory"]() as session:
        assert session.query(StudyAttempt).one().content_version == "retired-historical-v1"


def test_review_requires_owned_case_and_that_cases_submitted_uuid(prep_lab):
    grant(prep_lab)
    client = prep_lab["client"]
    data = payload()
    assert client.post(url(prep_lab, "attempts"), json=data).status_code == 200
    assert client.get(url(prep_lab, f"attempts/{uuid4()}/review")).status_code == 404
    with prep_lab["factory"]() as session:
        original = session.get(ApplicantProfileRow, prep_lab["case"])
        org = Organization(name="Foreign synthetic review tenant", slug=uuid4().hex)
        session.add(org)
        session.flush()
        foreign_id = uuid4().hex
        same_org_id = uuid4().hex
        session.add(
            ApplicantProfileRow(id=foreign_id, organization_id=org.id, payload=original.payload)
        )
        session.add(
            ApplicantProfileRow(
                id=same_org_id, organization_id=original.organization_id, payload=original.payload
            )
        )
        session.commit()
    for case in (foreign_id, same_org_id):
        assert (
            client.get(
                f"/api/profiles/{case}/preparation/attempts/{data['attempt_id']}/review"
            ).status_code
            == 404
        )
