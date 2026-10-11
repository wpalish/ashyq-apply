"""Retained blocked-content and document-admission controls, migrated DBs."""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest

from tests.test_product_audit_backend import seed_result
from tests.test_product_audit_support import (
    ORG,
    PROFILE,
    READER,
    SENDER,
)

pytest_plugins = ("tests.test_product_audit_support",)

THIRD = "3" * 32
POST = "b" * 32
THIRD_POST = "c" * 32


def seed_blocked_community(sandbox, *, viewer_blocks):
    from app.models import User
    from app.models.social import Block, Post, PostReply, SocialProfile, SocialProfileUniversity

    moment = datetime.now(UTC) - timedelta(minutes=5)
    with sandbox.sessions() as session:
        session.add(
            User(
                id=THIRD,
                email="synthetic-third@example.invalid",
                display_name="Third",
                password_hash="disabled",
            )
        )
        session.flush()
        session.add(SocialProfile(user_id=THIRD))
        target = session.get(SocialProfile, SENDER)
        target.bio = "Sensitive current biography"
        target.target_city = "Sensitive current city"
        target.universities.append(SocialProfileUniversity(name="Sensitive current university"))
        session.get(User, SENDER).display_name = "Sensitive current name"
        session.add_all(
            [
                Post(
                    id=POST,
                    author_id=SENDER,
                    body="Blocked author's current post",
                    created_at=moment,
                ),
                Post(
                    id=THIRD_POST,
                    author_id=THIRD,
                    body="Third person's post",
                    created_at=moment + timedelta(seconds=1),
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                PostReply(
                    id="a" * 32,
                    author_id=THIRD,
                    post_id=THIRD_POST,
                    body="First visible reply",
                    created_at=moment + timedelta(seconds=2),
                ),
                PostReply(
                    id="b" * 32,
                    author_id=SENDER,
                    post_id=THIRD_POST,
                    body="Hidden blocked reply",
                    created_at=moment + timedelta(seconds=3),
                ),
                PostReply(
                    id="c" * 32,
                    author_id=READER,
                    post_id=THIRD_POST,
                    body="Last visible reply",
                    created_at=moment + timedelta(seconds=4),
                ),
            ]
        )
        session.add(
            Block(
                blocker_id=READER if viewer_blocks else SENDER,
                blocked_id=SENDER if viewer_blocks else READER,
            )
        )
        session.commit()


@pytest.mark.parametrize("viewer_blocks", [False, True])
def test_block_hides_saved_post_links_and_reply_access(sandbox, viewer_blocks):
    seed_blocked_community(sandbox, viewer_blocks=viewer_blocks)
    assert sandbox.client.get(f"/api/social/people/{SENDER}").status_code == 404
    feed = sandbox.client.get("/api/social/feed").json()["items"]
    assert SENDER not in [row["author"]["user_id"] for row in feed]
    assert sandbox.client.get(f"/api/social/posts/{POST}").status_code == 404
    assert sandbox.client.get(f"/api/social/posts/{POST}/replies").status_code == 404
    direct = sandbox.client.get(f"/api/social/posts/{THIRD_POST}").json()
    assert direct["reply_count"] == 2
    assert next(row for row in feed if row["id"] == THIRD_POST)["reply_count"] == 2
    thread = sandbox.client.get(f"/api/social/posts/{THIRD_POST}/replies").json()
    assert [row["body"] for row in thread["items"]] == ["First visible reply", "Last visible reply"]


@pytest.mark.parametrize("viewer_blocks", [False, True])
def test_blocked_person_without_conversation_has_no_message_profile_card(sandbox, viewer_blocks):
    seed_blocked_community(sandbox, viewer_blocks=viewer_blocks)
    response = sandbox.client.get(f"/api/social/messages/{SENDER}")
    assert response.status_code == 404
    assert "Sensitive current" not in response.text


@pytest.mark.parametrize("viewer_blocks", [False, True])
def test_existing_blocked_conversation_keeps_history_with_neutral_card(sandbox, viewer_blocks):
    from app.models.social import Conversation, DirectMessage

    seed_blocked_community(sandbox, viewer_blocks=viewer_blocks)
    with sandbox.sessions() as session:
        conversation = Conversation(lower_id=READER, higher_id=SENDER)
        session.add(conversation)
        session.flush()
        session.add(
            DirectMessage(
                conversation_id=conversation.id, sender_id=SENDER, body="Historical private message"
            )
        )
        session.commit()
    response = sandbox.client.get(f"/api/social/messages/{SENDER}")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["body"] == "Historical private message"
    assert body["person"]["user_id"] == SENDER
    assert body["person"]["display_name"] == "Unavailable applicant"
    assert body["person"]["bio"] == ""
    assert body["person"]["target_city"] == ""
    assert body["person"]["universities"] == []
    assert body["person"]["dm_policy"] == "nobody"
    listing = sandbox.client.get("/api/social/messages")
    assert listing.status_code == 200
    assert "Sensitive current" not in listing.text
    assert listing.json()["items"][0]["last_message"] == "Historical private message"
    assert (
        sandbox.client.post(
            f"/api/social/messages/{SENDER}", json={"body": "Must not send"}
        ).status_code
        == 403
    )


def test_hidden_reply_does_not_break_visible_thread_pagination(sandbox):
    seed_blocked_community(sandbox, viewer_blocks=True)
    first = sandbox.client.get(
        f"/api/social/posts/{THIRD_POST}/replies", params={"limit": 1}
    ).json()
    assert first["items"][0]["body"] == "First visible reply" and first["next_cursor"]
    last = sandbox.client.get(
        f"/api/social/posts/{THIRD_POST}/replies",
        params={"limit": 1, "cursor": first["next_cursor"]},
    ).json()
    assert last["items"][0]["body"] == "Last visible reply"
    assert last["next_cursor"] is None


def test_unblock_restores_ordinary_cards_posts_and_reply_counts(sandbox):
    seed_blocked_community(sandbox, viewer_blocks=True)
    assert sandbox.client.get(f"/api/social/posts/{POST}").status_code == 404
    assert sandbox.client.delete(f"/api/social/blocks/{SENDER}").status_code == 204
    assert sandbox.client.get(f"/api/social/posts/{POST}").status_code == 200
    assert (
        sandbox.client.get(f"/api/social/messages/{SENDER}").json()["person"]["bio"]
        == "Sensitive current biography"
    )
    assert sandbox.client.get(f"/api/social/posts/{THIRD_POST}").json()["reply_count"] == 3


def test_nonmember_without_conversation_has_no_account_card(sandbox):
    from app.models.social import SocialProfile

    with sandbox.sessions() as session:
        session.delete(session.get(SocialProfile, SENDER))
        session.commit()
    response = sandbox.client.get(f"/api/social/messages/{SENDER}")
    assert response.status_code == 404


@pytest.mark.parametrize("viewer_blocks", [False, True])
def test_blocked_content_reports_keep_moderator_evidence_but_redact_receipts(
    sandbox, monkeypatch, viewer_blocks
):
    from app.models.social import ContentReport

    seed_blocked_community(sandbox, viewer_blocks=viewer_blocks)
    targets = [("post", POST), ("reply", "b" * 32), ("profile", SENDER)]
    for kind, subject_id in targets:
        response = sandbox.client.post(
            "/api/social/reports",
            json={"subject_type": kind, "subject_id": subject_id, "reason": "harassment"},
        )
        assert response.status_code == 201, response.text
        receipt = response.json()
        assert receipt["subject_type"] == kind and receipt["subject_id"] == subject_id
        assert receipt["subject_author"] is None
        assert receipt["excerpt"] == ""
    with sandbox.sessions() as session:
        stored = session.query(ContentReport).all()
        assert len(stored) == 3
        assert all(report.excerpt and report.subject_author_id == SENDER for report in stored)
    monkeypatch.setattr(
        sandbox.settings, "moderator_user_ids", sandbox.identity["principal"].user_id
    )
    moderator = sandbox.client.get("/api/social/moderation/reports")
    assert moderator.status_code == 200
    assert len(moderator.json()["items"]) == 3
    assert all(
        report["excerpt"] and report["subject_author"]["display_name"] == "Sensitive current name"
        for report in moderator.json()["items"]
    )


def seed_document_attempt(sandbox, *, status="cancelled"):
    from app.models import Job, ProgramResultRow, ResearchRun
    from app.payments.entitlements import grant_case_access

    run_id, result_id = seed_result(sandbox)
    digest = hashlib.sha256(result_id.encode()).hexdigest()[:16]
    key = f"documents:{run_id}:{digest}"
    now = datetime.now(UTC)
    with sandbox.sessions() as session:
        row = session.get(ProgramResultRow, result_id)
        row.user_decision = "approved"
        payload = dict(row.payload)
        payload["user_decision"] = "approved"
        row.payload = payload
        run = session.get(ResearchRun, run_id)
        run.cancelled = status in {"cancelled", "dead", "running"}
        grant_case_access(session, organization_id=ORG, profile_id=PROFILE, order_id=None)
        job = Job(
            id="j" * 32,
            kind="documents",
            run_id=run_id,
            idempotency_key=key,
            status=status,
            available_at=now - timedelta(seconds=1),
            attempts=3 if status == "dead" else 1,
            max_attempts=3,
            cancel_requested=status in {"cancelled", "running"},
            worker_id="old-worker" if status == "running" else None,
            lease_expires_at=now + timedelta(minutes=5) if status == "running" else None,
            finished_at=now if status in {"cancelled", "dead", "succeeded"} else None,
            last_error="Original exhausted error" if status == "dead" else "",
        )
        session.add(job)
        session.commit()
        original = {
            "status": job.status,
            "attempts": job.attempts,
            "cancel_requested": job.cancel_requested,
            "worker_id": job.worker_id,
            "last_error": job.last_error,
        }
    return run_id, result_id, key, original


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("status", ["cancelled", "dead"])
def test_terminal_documents_restart_as_one_runnable_fresh_job(sandbox, status):
    from app.jobs.store import JobStore
    from app.models import Job

    run_id, _, key, original = seed_document_attempt(sandbox, status=status)
    response = sandbox.client.post(f"/api/runs/{run_id}/collect-documents")
    assert response.status_code == 202, response.text
    assert response.json()["job_status"] == "queued"
    assert response.json()["cancelled"] is False
    again = sandbox.client.post(f"/api/runs/{run_id}/collect-documents")
    assert again.status_code == 202 and again.json()["job_id"] == response.json()["job_id"]
    with sandbox.sessions() as session:
        jobs = session.query(Job).filter(Job.run_id == run_id, Job.kind == "documents").all()
        assert len(jobs) == 2
        old = session.get(Job, "j" * 32)
        assert {name: getattr(old, name) for name in original} == original
        new = next(job for job in jobs if job.id != old.id)
        assert new.idempotency_key == key + ":retry:1"
        assert new.cancel_requested is False and new.attempts == 0
        assert new.worker_id is None and new.lease_expires_at is None
        claimed = JobStore(session).claim(worker_id="new-worker")
        assert claimed is not None and claimed.id == new.id and claimed.attempts == 1


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("status", ["queued", "running", "succeeded"])
def test_active_or_successful_document_job_is_retained(sandbox, status):
    from app.models import Job, ResearchRun

    run_id, _, _, original = seed_document_attempt(sandbox, status=status)
    response = sandbox.client.post(f"/api/runs/{run_id}/collect-documents")
    assert response.status_code == 202 and response.json()["job_id"] == "j" * 32
    assert response.json()["job_status"] == status
    with sandbox.sessions() as session:
        assert session.query(Job).filter(Job.run_id == run_id, Job.kind == "documents").count() == 1
        old = session.get(Job, "j" * 32)
        assert {name: getattr(old, name) for name in original} == original
        if status == "running":
            assert session.get(ResearchRun, run_id).cancelled is True


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_second_terminal_document_attempt_gets_next_generation(sandbox):
    from app.models import Job

    run_id, _, key, _ = seed_document_attempt(sandbox)
    first = sandbox.client.post(f"/api/runs/{run_id}/collect-documents").json()
    assert first["job_status"] == "queued"
    with sandbox.sessions() as session:
        new = session.get(Job, first["job_id"])
        new.status = "dead"
        new.last_error = "Retry exhausted"
        session.commit()
    second = sandbox.client.post(f"/api/runs/{run_id}/collect-documents").json()
    assert second["job_status"] == "queued" and second["job_id"] != first["job_id"]
    with sandbox.sessions() as session:
        assert session.get(Job, second["job_id"]).idempotency_key == key + ":retry:2"


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_old_document_worker_cannot_write_or_complete_new_attempt(sandbox):
    from app.corpus.demo_profile import DEMO_PROFILE
    from app.jobs.store import JobStore
    from app.models import Job, ResearchRun
    from app.pipeline.runner import LeaseLost, ResearchRunner, RunCancelled
    from app.schemas.profile import ApplicantProfileIn

    run_id, _, _, _ = seed_document_attempt(sandbox, status="dead")
    response = sandbox.client.post(f"/api/runs/{run_id}/collect-documents").json()
    assert response["job_status"] == "queued"
    with sandbox.sessions() as session:
        claimed = JobStore(session).claim(worker_id="new-worker")
        assert claimed.id == response["job_id"]
        session.commit()
        old_store = JobStore(session, worker_id="old-worker")
        assert old_store.heartbeat("j" * 32, lease_token=3) is False
        assert old_store.complete("j" * 32, lease_token=3) is False
        run = session.get(ResearchRun, run_id)
        runner = ResearchRunner(
            session,
            run,
            ApplicantProfileIn.model_validate(DEMO_PROFILE.model_dump(mode="json")),
            sandbox.settings,
            job_id="j" * 32,
            worker_id="old-worker",
            lease_token=3,
        )
        with pytest.raises((LeaseLost, RunCancelled)):
            runner._check_cancelled()
        # The actual checkpoint must roll back pending progress, not merely
        # fail a read-only ownership pre-check.
        run.pages_checked = 123456
        with pytest.raises(LeaseLost):
            runner._save()
        assert session.get(ResearchRun, run_id).pages_checked == 0
        assert session.get(Job, claimed.id).status == "running"
        assert session.get(Job, claimed.id).worker_id == "new-worker"
        assert session.get(Job, "j" * 32).status == "dead"


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_parallel_document_restart_requests_admit_one_new_generation(sandbox, monkeypatch):
    from app.api import routes_research
    from app.models import Job

    run_id, _, _, _ = seed_document_attempt(sandbox, status="cancelled")
    rendezvous = Barrier(2)
    native_owned = routes_research.owned_run

    def simultaneous_owned(*args, **kwargs):
        row = native_owned(*args, **kwargs)
        rendezvous.wait(timeout=10)
        return row

    monkeypatch.setattr(routes_research, "owned_run", simultaneous_owned)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: sandbox.client.post(f"/api/runs/{run_id}/collect-documents"), range(2)
            )
        )
    assert [response.status_code for response in responses] == [202, 202]
    assert all(response.json()["job_status"] == "queued" for response in responses)
    assert len({response.json()["job_id"] for response in responses}) == 1
    with sandbox.sessions() as session:
        assert session.query(Job).filter(Job.run_id == run_id, Job.kind == "documents").count() == 2


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_document_restart_without_approvals_creates_no_job(sandbox):
    from app.models import Job, ProgramResultRow, ResearchRun

    run_id, result_id, _, _ = seed_document_attempt(sandbox)
    with sandbox.sessions() as session:
        session.get(ProgramResultRow, result_id).user_decision = "undecided"
        session.commit()
    response = sandbox.client.post(f"/api/runs/{run_id}/collect-documents")
    assert response.status_code == 400
    with sandbox.sessions() as session:
        assert session.query(Job).filter(Job.run_id == run_id).count() == 1
        assert session.get(ResearchRun, run_id).cancelled is True


@pytest.mark.parametrize("sandbox", ["postgres"], indirect=True)
def test_postgres_admission_waits_for_owned_run_row_lock(sandbox):
    """Observe a real PG lock wait, then release and verify admission."""
    from sqlalchemy import text, update

    from app.jobs.store import JobStore
    from app.models import Job, ResearchRun

    run_id, _, key, _ = seed_document_attempt(sandbox, status="cancelled")
    locker = sandbox.sessions()
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        locker.execute(
            update(ResearchRun)
            .where(ResearchRun.id == run_id)
            .values(updated_at=ResearchRun.updated_at)
        )
        locker_pid = locker.execute(text("SELECT pg_backend_pid()")).scalar()
        future = pool.submit(sandbox.client.post, f"/api/runs/{run_id}/collect-documents")
        deadline = time.monotonic() + 5
        blocked = None
        while time.monotonic() < deadline:
            with sandbox.sessions() as monitor:
                candidates = (
                    monitor.execute(
                        text("""
                    SELECT pid, wait_event_type, pg_blocking_pids(pid) AS blockers
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND wait_event_type = 'Lock'
                      AND query LIKE '%UPDATE research_runs%'
                """)
                    )
                    .mappings()
                    .all()
                )
            blocked = next((dict(row) for row in candidates if locker_pid in row["blockers"]), None)
            if blocked:
                break
            if future.done():
                pytest.fail("Admission returned before the held row lock was released")
            time.sleep(0.025)
        assert blocked is not None, "Did not observe PG row lock contention"
        assert not future.done()
        sandbox.observations.append(
            {"control": "owned-run UPDATE lock", "locker_pid": locker_pid, **blocked}
        )
        locker.commit()
        response = future.result(timeout=10)
        assert response.status_code == 202, response.text
        assert response.json()["job_status"] == "queued"
        with sandbox.sessions() as session:
            jobs = session.query(Job).filter(Job.run_id == run_id, Job.kind == "documents").all()
            assert len(jobs) == 2
            new = session.get(Job, response.json()["job_id"])
            assert new.idempotency_key == key + ":retry:1"
            claimed = JobStore(session).claim(worker_id="lock-control-worker")
            assert claimed is not None and claimed.id == new.id
    finally:
        locker.rollback()
        locker.close()
        pool.shutdown(wait=True)
