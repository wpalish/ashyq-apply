"""Retained product audit regressions using restored native fixtures.

Application imports are deferred to case/helper execution; no standalone
module-level Settings/env override is copied. See origin mapping outside lab.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.test_product_audit_support import (
    ORG,
    OTHER_ORG,
    PROFILE,
    READER,
    SENDER,
)

pytest_plugins = ("tests.test_product_audit_support",)


def as_utc(value: datetime) -> datetime:
    """SQLite stores naive UTC; PostgreSQL returns aware session-zone values."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def paid_order(session, profile_id=PROFILE):
    from app.models.billing import Order

    order = Order(
        organization_id=ORG,
        profile_id=profile_id,
        status="pending",
        amount_kzt=4990,
        external_order_id="synthetic-order",
    )
    session.add(order)
    session.flush()
    return order


@pytest.mark.parametrize(
    ("server_demo", "previous_demo", "universities"),
    [
        (False, False, ["synthetic-u1", "synthetic-u2"]),
        (False, True, None),
        (True, False, None),
        (True, True, []),
    ],
)
def test_payment_preserves_latest_same_profile_mode_and_scope(
    sandbox, server_demo, previous_demo, universities
):
    from app.corpus.demo_profile import DEMO_PROFILE
    from app.models import ApplicantProfileRow, Job, ResearchRun
    from app.payments.service import apply_status

    sandbox.settings.demo_mode = server_demo
    moment = datetime.now(UTC) - timedelta(minutes=5)
    with sandbox.sessions() as session:
        session.add_all(
            [
                ResearchRun(
                    id="o" * 32,
                    profile_id=PROFILE,
                    stage="completed",
                    demo_mode=not previous_demo,
                    university_ids=["obsolete-scope"],
                    created_at=moment,
                ),
                ResearchRun(
                    id="r" * 32,
                    profile_id=PROFILE,
                    stage="completed",
                    demo_mode=previous_demo,
                    university_ids=universities,
                    created_at=moment + timedelta(minutes=1),
                ),
            ]
        )
        another = ApplicantProfileRow(
            organization_id=ORG,
            display_name="Another synthetic applicant",
            payload=DEMO_PROFILE.model_dump(mode="json"),
        )
        session.add(another)
        session.flush()
        session.add(
            ResearchRun(
                profile_id=another.id,
                stage="completed",
                demo_mode=not previous_demo,
                university_ids=["another-profile-scope"],
                created_at=moment + timedelta(minutes=2),
            )
        )
        order = paid_order(session)
        apply_status(session, order, "paid", source="offline-proof")
        session.commit()
        new = (
            session.query(ResearchRun)
            .filter(ResearchRun.profile_id == PROFILE, ResearchRun.stage == "queued")
            .one()
        )
        assert new.demo_mode is previous_demo
        assert new.university_ids == universities
        assert new.access_tier == "full"
        assert session.query(Job).filter(Job.run_id == new.id, Job.kind == "research").count() == 1
        # A replay remains a no-op rather than purchasing another run.
        apply_status(session, order, "paid", source="offline-proof")
        session.commit()
        assert session.query(ResearchRun).filter(ResearchRun.profile_id == PROFILE).count() == 3


@pytest.mark.parametrize("server_demo", [False, True])
def test_payment_without_prior_run_uses_server_mode(sandbox, server_demo):
    from app.models import ResearchRun
    from app.payments.service import apply_status

    sandbox.settings.demo_mode = server_demo
    with sandbox.sessions() as session:
        order = paid_order(session)
        apply_status(session, order, "paid", source="offline-proof")
        session.commit()
        new = session.query(ResearchRun).filter(ResearchRun.profile_id == PROFILE).one()
        assert new.demo_mode is server_demo
        assert new.university_ids is None


def seed_result(sandbox):
    from app.models import ProgramResultRow, ResearchRun
    from app.schemas.result import DocumentChecklist, ProgramResult

    run_id, result_id = "r" * 32, "s" * 32
    result = ProgramResult(
        id=result_id,
        run_id=run_id,
        university="Synthetic University",
        university_id="synthetic-u",
        country="Synthetic Country",
        city="Synthetic City",
        program="Synthetic BSc",
        degree="bachelor",
        intake="fall 2027",
        source_urls=["https://official.example.invalid/evidence"],
        career_notes="Paid career evidence",
        checklist=DocumentChecklist(
            result_id=result_id,
            university="Synthetic University",
            program="Synthetic BSc",
            ordered_steps=["Paid document instruction"],
        ),
    )
    with sandbox.sessions() as session:
        session.add(
            ResearchRun(
                id=run_id, profile_id=PROFILE, stage="awaiting_user_decision", demo_mode=True
            )
        )
        session.flush()
        session.add(
            ProgramResultRow(
                id=result_id,
                run_id=run_id,
                dedupe_key="synthetic-u",
                university=result.university,
                university_key="synthetic-u",
                country=result.country,
                program=result.program,
                eligibility=result.eligibility.value,
                admissions_fit=result.admissions_fit.value,
                funding_fit=result.funding_fit.value,
                funding_classification=result.best_funding_classification.value,
                payload=result.model_dump(mode="json"),
            )
        )
        session.commit()
    return run_id, result_id


@pytest.mark.parametrize("operation", ["notes", "decision"])
@pytest.mark.parametrize("access", ["free", "entitled", "payments_disabled"])
def test_result_mutations_project_access_and_keep_full_stored_evidence(sandbox, operation, access):
    from app.models import ProgramResultRow
    from app.payments.entitlements import grant_case_access

    run_id, result_id = seed_result(sandbox)
    if access == "entitled":
        with sandbox.sessions() as session:
            grant_case_access(session, organization_id=ORG, profile_id=PROFILE, order_id=None)
            session.commit()
    elif access == "payments_disabled":
        sandbox.settings.payments_enabled = False
    base = f"/api/runs/{run_id}/results/{result_id}"
    before_detail = sandbox.client.get(base)
    assert before_detail.status_code == (402 if access == "free" else 200)
    if operation == "notes":
        response = sandbox.client.patch(base + "/notes", json={"notes": "Synthetic reminder"})
    else:
        response = sandbox.client.post(
            base + "/decision", json={"decision": "approved", "notes": "Synthetic reminder"}
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_notes"] == "Synthetic reminder"
    assert body["user_decision"] == ("approved" if operation == "decision" else "undecided")
    if access == "free":
        assert body["source_urls"] == []
        assert body["checklist"] is None
        assert body["career_notes"] == ""
    else:
        assert body["source_urls"] == ["https://official.example.invalid/evidence"]
        assert body["checklist"]["ordered_steps"] == ["Paid document instruction"]
        assert body["career_notes"] == "Paid career evidence"
    with sandbox.sessions() as session:
        stored = session.get(ProgramResultRow, result_id)
        assert stored.payload["source_urls"] == ["https://official.example.invalid/evidence"]
        assert stored.payload["checklist"]["ordered_steps"] == ["Paid document instruction"]
        assert stored.user_notes == "Synthetic reminder"
        assert stored.user_decision == body["user_decision"]
        assert (stored.decided_at is not None) is (operation == "decision")


def test_free_mutation_still_rejects_another_workspace(sandbox):
    from app.models import ProgramResultRow
    from app.security import Principal

    run_id, result_id = seed_result(sandbox)
    old = sandbox.identity["principal"]
    sandbox.identity["principal"] = Principal(
        user_id=old.user_id,
        organization_id=OTHER_ORG,
        email=old.email,
        display_name=old.display_name,
        role="owner",
    )
    response = sandbox.client.patch(
        f"/api/runs/{run_id}/results/{result_id}/notes", json={"notes": "Must not persist"}
    )
    assert response.status_code == 404
    with sandbox.sessions() as session:
        assert session.get(ProgramResultRow, result_id).user_notes == ""


def seed_messages(sandbox, *, reader=READER, sender=SENDER, tied=False, outgoing_first=False):
    from app.models.social import Conversation, DirectMessage

    moment = datetime.now(UTC) - timedelta(minutes=5)
    with sandbox.sessions() as session:
        lower, higher = Conversation.pair(reader, sender)
        conversation = Conversation(
            lower_id=lower, higher_id=higher, last_message_at=moment + timedelta(seconds=3)
        )
        session.add(conversation)
        session.flush()
        if outgoing_first:
            session.add(
                DirectMessage(
                    conversation_id=conversation.id,
                    sender_id=reader,
                    body="Own earlier message",
                    created_at=moment - timedelta(seconds=1),
                )
            )
        for index in range(3):
            session.add(
                DirectMessage(
                    id=f"{index + 1:032d}",
                    conversation_id=conversation.id,
                    sender_id=sender,
                    body=f"Synthetic unread {index}",
                    created_at=moment if tied else moment + timedelta(seconds=index),
                )
            )
        session.commit()
        return conversation.id, moment


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("reader_is_lower", [True, False])
def test_message_pages_mark_only_returned_incoming_messages_read(sandbox, reader_is_lower):
    from app.models.social import Conversation
    from app.security import Principal

    reader, sender = (READER, SENDER) if reader_is_lower else (SENDER, READER)
    old = sandbox.identity["principal"]
    sandbox.identity["principal"] = Principal(
        user_id=reader,
        organization_id=ORG,
        email=old.email,
        display_name=old.display_name,
        role="owner",
    )
    conversation_id, moment = seed_messages(sandbox, reader=reader, sender=sender)
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 3
    first = sandbox.client.get(f"/api/social/messages/{sender}", params={"limit": 1}).json()
    assert len(first["items"]) == 1 and first["next_cursor"]
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 2
    with sandbox.sessions() as session:
        stored = session.get(Conversation, conversation_id).read_at_for(reader)
        assert as_utc(stored) == moment
    last = sandbox.client.get(
        f"/api/social/messages/{sender}", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert len(last["items"]) == 2 and last["next_cursor"] is None
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 0


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_older_message_page_cannot_move_read_watermark_backwards(sandbox):
    from app.models.social import Conversation

    conversation_id, moment = seed_messages(sandbox)
    newer_read = moment + timedelta(seconds=1)
    with sandbox.sessions() as session:
        session.get(Conversation, conversation_id).lower_read_at = newer_read
        session.commit()
    sandbox.client.get(f"/api/social/messages/{SENDER}", params={"limit": 1})
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 1
    with sandbox.sessions() as session:
        assert as_utc(session.get(Conversation, conversation_id).lower_read_at) == newer_read


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_page_with_only_own_message_keeps_incoming_messages_unread(sandbox):
    from app.models.social import Conversation

    conversation_id, _moment = seed_messages(sandbox, outgoing_first=True)
    first = sandbox.client.get(f"/api/social/messages/{SENDER}", params={"limit": 1}).json()
    assert first["items"][0]["mine"] is True
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 3
    with sandbox.sessions() as session:
        assert session.get(Conversation, conversation_id).lower_read_at is None


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_empty_message_page_does_not_mark_existing_messages_read(sandbox):
    from app.api import routes_social
    from app.models.social import Conversation

    conversation_id, moment = seed_messages(sandbox)
    cursor = routes_social._encode_cursor(moment + timedelta(days=1), "f" * 32)
    page = sandbox.client.get(f"/api/social/messages/{SENDER}", params={"cursor": cursor}).json()
    assert page["items"] == []
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 3
    with sandbox.sessions() as session:
        assert session.get(Conversation, conversation_id).lower_read_at is None


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
def test_tied_timestamp_keeps_unseen_group_unread_until_last_page(sandbox):
    seed_messages(sandbox, tied=True)
    cursor = None
    for index in range(3):
        params = {"limit": 1}
        if cursor:
            params["cursor"] = cursor
        page = sandbox.client.get(f"/api/social/messages/{SENDER}", params=params).json()
        assert len(page["items"]) == 1
        cursor = page["next_cursor"]
        assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == (
            3 if index < 2 else 0
        )


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("reader_is_lower", [True, False])
def test_reply_does_not_acknowledge_unloaded_incoming_tail(sandbox, reader_is_lower):
    """GET 20 of 25, reply, then load five: unread must be 5, 5, 0."""
    from app.models.social import Conversation, DirectMessage
    from app.security import Principal

    reader, sender = (READER, SENDER) if reader_is_lower else (SENDER, READER)
    old = sandbox.identity["principal"]
    sandbox.identity["principal"] = Principal(
        user_id=reader,
        organization_id=ORG,
        email=old.email,
        display_name=old.display_name,
        role="owner",
    )
    moment = datetime.now(UTC) - timedelta(minutes=5)
    with sandbox.sessions() as session:
        lower, higher = Conversation.pair(reader, sender)
        conversation = Conversation(
            lower_id=lower, higher_id=higher, last_message_at=moment + timedelta(seconds=24)
        )
        session.add(conversation)
        session.flush()
        conversation_id = conversation.id
        session.add_all(
            [
                DirectMessage(
                    id=f"{index + 1:032d}",
                    conversation_id=conversation_id,
                    sender_id=sender,
                    body=f"Synthetic incoming {index}",
                    created_at=moment + timedelta(seconds=index),
                )
                for index in range(25)
            ]
        )
        session.commit()
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 25
    first_response = sandbox.client.get(f"/api/social/messages/{sender}", params={"limit": 20})
    assert first_response.status_code == 200, first_response.text
    first = first_response.json()
    assert len(first["items"]) == 20 and first["next_cursor"]
    assert all(not row["mine"] for row in first["items"])
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 5
    with sandbox.sessions() as session:
        seen_before = session.get(Conversation, conversation_id).read_at_for(reader)
        assert as_utc(seen_before) == moment + timedelta(seconds=19)
    reply = sandbox.client.post(
        f"/api/social/messages/{sender}", json={"body": "Reply after reading only the first page"}
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["mine"] is True
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 5
    with sandbox.sessions() as session:
        assert session.get(Conversation, conversation_id).read_at_for(reader) == seen_before
    tail_response = sandbox.client.get(
        f"/api/social/messages/{sender}", params={"limit": 20, "cursor": first["next_cursor"]}
    )
    assert tail_response.status_code == 200, tail_response.text
    tail = tail_response.json()
    assert len(tail["items"]) == 6 and tail["next_cursor"] is None
    assert [row["body"] for row in tail["items"] if not row["mine"]] == [
        f"Synthetic incoming {index}" for index in range(20, 25)
    ]
    assert tail["items"][-1]["mine"] is True
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 0
    with sandbox.sessions() as session:
        assert as_utc(
            session.get(Conversation, conversation_id).read_at_for(reader)
        ) == moment + timedelta(seconds=24)


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("reader_is_lower", [True, False])
@pytest.mark.parametrize("later_incoming", [False, True])
def test_mixed_timestamp_tail_acknowledges_only_delivered_incoming(
    sandbox, reader_is_lower, later_incoming
):
    """Own tied rows must neither strand read incoming nor acknowledge unseen incoming."""
    from app.models.social import Conversation, DirectMessage
    from app.security import Principal

    reader, sender = (READER, SENDER) if reader_is_lower else (SENDER, READER)
    old = sandbox.identity["principal"]
    sandbox.identity["principal"] = Principal(
        user_id=reader,
        organization_id=ORG,
        email=old.email,
        display_name=old.display_name,
        role="owner",
    )
    moment = datetime.now(UTC) - timedelta(minutes=5)
    with sandbox.sessions() as session:
        lower, higher = Conversation.pair(reader, sender)
        conversation = Conversation(lower_id=lower, higher_id=higher, last_message_at=moment)
        session.add(conversation)
        session.flush()
        conversation_id = conversation.id
        session.add_all(
            [
                DirectMessage(
                    id="1".zfill(32),
                    conversation_id=conversation_id,
                    sender_id=sender,
                    body="Incoming tied first",
                    created_at=moment,
                ),
                DirectMessage(
                    id="2".zfill(32),
                    conversation_id=conversation_id,
                    sender_id=reader,
                    body="Own tied middle",
                    created_at=moment,
                ),
            ]
        )
        if later_incoming:
            session.add(
                DirectMessage(
                    id="3".zfill(32),
                    conversation_id=conversation_id,
                    sender_id=sender,
                    body="Incoming tied last",
                    created_at=moment,
                )
            )
        session.commit()
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == (
        2 if later_incoming else 1
    )
    first_response = sandbox.client.get(f"/api/social/messages/{sender}", params={"limit": 1})
    assert first_response.status_code == 200, first_response.text
    first = first_response.json()
    assert [row["body"] for row in first["items"]] == ["Incoming tied first"]
    assert first["items"][0]["mine"] is False
    assert first["next_cursor"]
    middle_response = sandbox.client.get(
        f"/api/social/messages/{sender}", params={"limit": 1, "cursor": first["next_cursor"]}
    )
    assert middle_response.status_code == 200, middle_response.text
    middle = middle_response.json()
    assert [row["body"] for row in middle["items"]] == ["Own tied middle"]
    assert middle["items"][0]["mine"] is True
    if later_incoming:
        # A one-row lookahead sees only our own middle row. It cannot justify
        # acknowledging a later incoming row at the same timestamp.
        assert middle["next_cursor"]
        assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 2
        with sandbox.sessions() as session:
            assert session.get(Conversation, conversation_id).read_at_for(reader) is None
        tail_response = sandbox.client.get(
            f"/api/social/messages/{sender}",
            params={"limit": 1, "cursor": middle["next_cursor"]},
        )
        assert tail_response.status_code == 200, tail_response.text
        tail = tail_response.json()
        assert [row["body"] for row in tail["items"]] == ["Incoming tied last"]
        assert tail["items"][0]["mine"] is False
        assert tail["next_cursor"] is None
    else:
        assert middle["next_cursor"] is None
    assert sandbox.client.get("/api/social/messages/unread").json()["unread"] == 0
    with sandbox.sessions() as session:
        assert as_utc(session.get(Conversation, conversation_id).read_at_for(reader)) == moment
