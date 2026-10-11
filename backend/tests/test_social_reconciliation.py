"""Proposed controls for immutable moderator IDs plus blocked report evidence."""

from __future__ import annotations

import pytest

from tests.test_product_audit_social_documents import POST, seed_blocked_community
from tests.test_product_audit_support import READER, SENDER

pytest_plugins = ("tests.test_product_audit_support",)


@pytest.mark.parametrize("sandbox", ["sqlite", "postgres"], indirect=True)
@pytest.mark.parametrize("viewer_blocks", [False, True])
def test_blocked_report_evidence_requires_provisioned_id_and_is_not_stored(
    sandbox, monkeypatch, viewer_blocks
):
    from app.models.social import ContentReport, Post

    seed_blocked_community(sandbox, viewer_blocks=viewer_blocks)
    principal = sandbox.identity["principal"]
    assert principal.user_id == READER and principal.role == "owner"
    # Matching email plus tenant owner is not a deployment moderation grant.
    # A different allowed user ID also must not authorize this reporter.
    monkeypatch.setattr(sandbox.settings, "moderator_emails", principal.email)
    monkeypatch.setattr(sandbox.settings, "moderator_user_ids", f" , {SENDER}, , ")
    hidden = sandbox.client.get(f"/api/social/posts/{POST}")
    assert hidden.status_code == 404
    assert hidden.headers["cache-control"] == "no-store"
    targets = [("post", POST), ("reply", "b" * 32), ("profile", SENDER)]
    receipts = []
    for kind, subject_id in targets:
        response = sandbox.client.post(
            "/api/social/reports",
            json={"subject_type": kind, "subject_id": subject_id, "reason": "harassment"},
        )
        assert response.status_code == 201, response.text
        assert response.headers["cache-control"] == "no-store"
        receipt = response.json()
        assert receipt["subject_type"] == kind and receipt["subject_id"] == subject_id
        assert receipt["subject_author"] is None and receipt["excerpt"] == ""
        receipts.append(receipt)
    denied_queue = sandbox.client.get("/api/social/moderation/reports")
    assert denied_queue.status_code == 403, denied_queue.text
    assert denied_queue.headers["cache-control"] == "no-store"
    denied_remove = sandbox.client.post(
        f"/api/social/moderation/reports/{receipts[0]['id']}",
        json={"action": "remove", "note": "Email claim must not authorize removal"},
    )
    assert denied_remove.status_code == 403, denied_remove.text
    assert denied_remove.headers["cache-control"] == "no-store"
    with sandbox.sessions() as session:
        assert session.get(Post, POST) is not None
        retained = session.query(ContentReport).all()
        assert len(retained) == 3
        assert all(row.excerpt and row.subject_author_id == SENDER for row in retained)
        assert all(
            row.status == "open" and row.resolved_at is None and row.resolved_by is None
            for row in retained
        )
    # Only this exact immutable ID grants moderation. The legacy email is now
    # deliberately empty, and ordinary blocked routes remain unavailable.
    monkeypatch.setattr(sandbox.settings, "moderator_user_ids", f" , {principal.user_id}, , ")
    monkeypatch.setattr(sandbox.settings, "moderator_emails", "")
    queue = sandbox.client.get("/api/social/moderation/reports")
    assert queue.status_code == 200, queue.text
    assert queue.headers["cache-control"] == "no-store"
    assert {row["id"] for row in queue.json()["items"]} == {row["id"] for row in receipts}
    assert all(
        row["excerpt"] and row["subject_author"]["display_name"] == "Sensitive current name"
        for row in queue.json()["items"]
    )
    assert sandbox.client.get(f"/api/social/posts/{POST}").status_code == 404
    assert sandbox.client.get(f"/api/social/people/{SENDER}").status_code == 404
    removed = sandbox.client.post(
        f"/api/social/moderation/reports/{receipts[0]['id']}",
        json={"action": "remove", "note": "Trusted ID reviews preserved blocked evidence"},
    )
    assert removed.status_code == 200, removed.text
    assert removed.headers["cache-control"] == "no-store"
    assert removed.json()["status"] == "actioned" and removed.json()["excerpt"]
    with sandbox.sessions() as session:
        assert session.get(Post, POST) is None
        stored = session.get(ContentReport, receipts[0]["id"])
        assert stored.status == "actioned" and stored.resolved_at is not None
        assert stored.resolved_by == principal.email
    # Removing the ID immediately revokes queue access despite the same email.
    monkeypatch.setattr(sandbox.settings, "moderator_user_ids", "")
    monkeypatch.setattr(sandbox.settings, "moderator_emails", principal.email)
    revoked = sandbox.client.get("/api/social/moderation/reports")
    assert revoked.status_code == 403
    assert revoked.headers["cache-control"] == "no-store"
