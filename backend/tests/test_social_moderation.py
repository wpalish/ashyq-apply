"""Blocking, reporting, and the queue a moderator works from.

Two tools, in the order they matter.

**Blocking is a decision.** It works at the moment it is needed, without asking
anybody, and it is enforced in both directions: a blocked person cannot write,
cannot reply, and does not appear — and neither does the blocker to them,
because a one-way silence tells the blocked person they were blocked, which is
its own kind of contact.

**Reporting is a request.** It goes to whoever the deployment names as a
moderator, and the queue keeps enough of the content to be reviewed after the
content is gone.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=100,
        social_rate_limit_per_minute=200,
        moderator_emails="keeper@example.test",
        database_url=f"sqlite:///{tmp_path / 'moderation.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
    )
    settings.ensure_dirs()

    import app.config as config_module
    import app.db as db_module
    import app.main as main_module
    import app.security as security_module
    from app.api import routes_auth

    original_get_settings = config_module.get_settings
    original_get_settings.cache_clear()
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    monkeypatch.setattr(security_module, "get_settings", lambda: settings)
    monkeypatch.setattr(routes_auth, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "_limiter", main_module.FixedWindowLimiter())

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    with TestClient(main_module.app) as c:
        yield c
    original_get_settings.cache_clear()


def join_as(client: TestClient, slug: str, **profile) -> str:
    registered = client.post(
        "/api/auth/register",
        json={
            "email": f"{slug}@example.test",
            "password": f"correct horse battery {slug}",
            "display_name": slug.title(),
            "organization_name": f"{slug.title()} Workspace",
        },
    )
    assert registered.status_code == 201, registered.text
    payload = {
        "status": None, "target_city": "Astana", "target_major": "", "bio": "",
        "universities": [], "dm_policy": "anyone",
    }
    payload.update(profile)
    assert client.put("/api/social/me", json=payload).status_code == 200
    return registered.json()["user_id"]


def sign_in(client: TestClient, slug: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": f"{slug}@example.test", "password": f"correct horse battery {slug}"},
    )
    assert response.status_code == 200, response.text


class TestBlocking:
    def test_a_block_stops_messages_in_both_directions(self, client):
        quiet = join_as(client, "quiet-one")
        client.post("/api/auth/logout")
        loud = join_as(client, "loud-one")
        # They were talking before the block.
        assert client.post(f"/api/social/messages/{quiet}", json={"body": "Привет"}).status_code == 201
        client.post("/api/auth/logout")

        sign_in(client, "quiet-one")
        assert client.post(f"/api/social/blocks/{loud}").status_code == 204
        # The blocker cannot write either: a block ends the conversation, it is
        # not a mute that leaves them able to keep talking.
        assert client.post(f"/api/social/messages/{loud}", json={"body": "..."}).status_code == 403
        client.post("/api/auth/logout")

        sign_in(client, "loud-one")
        refused = client.post(f"/api/social/messages/{quiet}", json={"body": "Ещё раз"})
        assert refused.status_code == 403

    def test_a_blocked_person_cannot_answer_your_posts(self, client):
        author = join_as(client, "author-one")
        post = client.post("/api/social/posts", json={"body": "Мой вопрос"})
        assert post.status_code == 201
        client.post("/api/auth/logout")

        heckler = join_as(client, "heckler")
        client.post("/api/auth/logout")

        sign_in(client, "author-one")
        assert client.post(f"/api/social/blocks/{heckler}").status_code == 204
        client.post("/api/auth/logout")

        sign_in(client, "heckler")
        refused = client.post(
            f"/api/social/posts/{post.json()['id']}/replies", json={"body": "Опять я"}
        )
        assert refused.status_code == 403
        assert author  # the post's author is who the block protects

    def test_neither_side_sees_the_other_in_the_feed_or_in_discover(self, client):
        join_as(client, "seen-one")
        client.post("/api/social/posts", json={"body": "Пост от первого"})
        client.post("/api/auth/logout")

        other = join_as(client, "unseen-one")
        client.post("/api/social/posts", json={"body": "Пост от второго"})
        assert client.post("/api/auth/logout").status_code == 204

        sign_in(client, "seen-one")
        assert len(client.get("/api/social/feed").json()["items"]) == 2
        assert client.post(f"/api/social/blocks/{other}").status_code == 204

        bodies = [item["body"] for item in client.get("/api/social/feed").json()["items"]]
        assert bodies == ["Пост от первого"]
        names = [p["display_name"] for p in client.get("/api/social/people").json()["items"]]
        assert names == ["Seen-One"]

        # And symmetrically for the person who was blocked, who is never told.
        client.post("/api/auth/logout")
        sign_in(client, "unseen-one")
        bodies = [item["body"] for item in client.get("/api/social/feed").json()["items"]]
        assert bodies == ["Пост от второго"]

    def test_unblocking_puts_everything_back(self, client):
        join_as(client, "forgiving")
        client.post("/api/auth/logout")
        other = join_as(client, "forgiven")
        client.post("/api/social/posts", json={"body": "Пост"})
        client.post("/api/auth/logout")

        sign_in(client, "forgiving")
        client.post(f"/api/social/blocks/{other}")
        assert client.get("/api/social/feed").json()["items"] == []

        assert client.delete(f"/api/social/blocks/{other}").status_code == 204
        assert len(client.get("/api/social/feed").json()["items"]) == 1

    def test_the_list_of_people_you_blocked_is_yours_to_read(self, client):
        join_as(client, "keeper-of-list")
        client.post("/api/auth/logout")
        other = join_as(client, "listed")
        client.post("/api/auth/logout")

        sign_in(client, "keeper-of-list")
        client.post(f"/api/social/blocks/{other}")
        blocked = client.get("/api/social/blocks").json()["items"]
        assert [person["display_name"] for person in blocked] == ["Listed"]

    def test_blocking_twice_is_not_an_error(self, client):
        join_as(client, "steady")
        client.post("/api/auth/logout")
        other = join_as(client, "target")
        client.post("/api/auth/logout")

        sign_in(client, "steady")
        assert client.post(f"/api/social/blocks/{other}").status_code == 204
        assert client.post(f"/api/social/blocks/{other}").status_code == 204

    def test_you_cannot_block_yourself(self, client):
        me = join_as(client, "alone")
        assert client.post(f"/api/social/blocks/{me}").status_code == 400


class TestReporting:
    def _a_post_to_report(self, client) -> str:
        join_as(client, "poster")
        post = client.post("/api/social/posts", json={"body": "Спорное утверждение про KBTU"})
        assert post.status_code == 201
        client.post("/api/auth/logout")
        join_as(client, "reader")
        return post.json()["id"]

    def test_reporting_a_post_files_it_with_its_words_kept(self, client):
        post_id = self._a_post_to_report(client)

        filed = client.post("/api/social/reports", json={
            "subject_type": "post",
            "subject_id": post_id,
            "reason": "misleading_advice",
            "note": "На сайте написано другое.",
        })
        assert filed.status_code == 201, filed.text
        client.post("/api/auth/logout")

        sign_in_as_moderator(client)
        queue = client.get("/api/social/moderation/reports").json()["items"]
        assert len(queue) == 1
        assert queue[0]["reason"] == "misleading_advice"
        assert queue[0]["status"] == "open"
        # The excerpt is what makes the queue reviewable after a deletion.
        assert "Спорное утверждение" in queue[0]["excerpt"]
        assert queue[0]["reporter"]["display_name"] == "Reader"

    def test_the_same_person_cannot_report_the_same_thing_twice(self, client):
        post_id = self._a_post_to_report(client)
        body = {"subject_type": "post", "subject_id": post_id, "reason": "spam", "note": ""}

        assert client.post("/api/social/reports", json=body).status_code == 201
        assert client.post("/api/social/reports", json=body).status_code == 409

    def test_a_reason_the_product_does_not_define_is_refused(self, client):
        post_id = self._a_post_to_report(client)
        refused = client.post("/api/social/reports", json={
            "subject_type": "post", "subject_id": post_id, "reason": "i-dont-like-it", "note": "",
        })
        assert refused.status_code == 422

    def test_reporting_something_that_does_not_exist_is_a_404(self, client):
        join_as(client, "confused")
        response = client.post("/api/social/reports", json={
            "subject_type": "post", "subject_id": "deadbeef", "reason": "spam", "note": "",
        })
        assert response.status_code == 404

    def test_a_person_can_be_reported_not_only_their_words(self, client):
        subject = join_as(client, "impersonator", bio="Я приёмная комиссия KBTU")
        client.post("/api/auth/logout")
        join_as(client, "noticer")

        filed = client.post("/api/social/reports", json={
            "subject_type": "profile",
            "subject_id": subject,
            "reason": "impersonation",
            "note": "Выдаёт себя за приёмную комиссию.",
        })
        assert filed.status_code == 201
        client.post("/api/auth/logout")

        sign_in_as_moderator(client)
        assert client.get("/api/social/moderation/reports").json()["items"][0]["subject_type"] == (
            "profile"
        )


class TestTheQueue:
    def _one_open_report(self, client) -> tuple[str, str]:
        join_as(client, "writer2")
        post = client.post("/api/social/posts", json={"body": "Пост, на который пожалуются"})
        client.post("/api/auth/logout")
        join_as(client, "reporter2")
        client.post("/api/social/reports", json={
            "subject_type": "post", "subject_id": post.json()["id"],
            "reason": "harassment", "note": "",
        }).raise_for_status()
        client.post("/api/auth/logout")
        return post.json()["id"], "writer2"

    def test_only_a_named_moderator_can_read_the_queue(self, client):
        self._one_open_report(client)
        sign_in(client, "reporter2")
        assert client.get("/api/social/moderation/reports").status_code == 403

        sign_in_as_moderator(client)
        assert client.get("/api/social/moderation/reports").status_code == 200

    def test_removing_content_deletes_it_and_closes_the_report(self, client):
        post_id, _ = self._one_open_report(client)
        sign_in_as_moderator(client)
        report = client.get("/api/social/moderation/reports").json()["items"][0]

        resolved = client.post(
            f"/api/social/moderation/reports/{report['id']}",
            json={"action": "remove", "note": "Нарушает правила."},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["status"] == "actioned"

        # The post is gone, and the queue no longer offers it as open work.
        assert client.get(f"/api/social/posts/{post_id}").status_code == 404
        assert client.get("/api/social/moderation/reports").json()["items"] == []

    def test_a_dismissed_report_is_closed_and_the_content_stays(self, client):
        post_id, _ = self._one_open_report(client)
        sign_in_as_moderator(client)
        report = client.get("/api/social/moderation/reports").json()["items"][0]

        client.post(
            f"/api/social/moderation/reports/{report['id']}",
            json={"action": "dismiss", "note": "Ничего страшного."},
        ).raise_for_status()

        assert client.get(f"/api/social/posts/{post_id}").status_code == 200
        closed = client.get("/api/social/moderation/reports?status=dismissed").json()["items"]
        assert closed[0]["resolved_by"] == "keeper@example.test"
        assert closed[0]["resolution_note"] == "Ничего страшного."

    def test_a_report_survives_the_thing_it_was_about(self, client):
        """The author deleting their own post must not erase the record."""
        post_id, author = self._one_open_report(client)
        sign_in(client, author)
        assert client.delete(f"/api/social/posts/{post_id}").status_code == 204
        client.post("/api/auth/logout")

        sign_in_as_moderator(client)
        report = client.get("/api/social/moderation/reports").json()["items"][0]
        assert "Пост, на который пожалуются" in report["excerpt"]
        # And acting on it says what happened rather than failing.
        resolved = client.post(
            f"/api/social/moderation/reports/{report['id']}",
            json={"action": "remove", "note": ""},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "actioned"

    def test_resolving_twice_is_refused(self, client):
        self._one_open_report(client)
        sign_in_as_moderator(client)
        report = client.get("/api/social/moderation/reports").json()["items"][0]
        body = {"action": "dismiss", "note": ""}

        assert client.post(f"/api/social/moderation/reports/{report['id']}", json=body).status_code == 200
        assert client.post(f"/api/social/moderation/reports/{report['id']}", json=body).status_code == 409

    def test_a_removal_leaves_a_record_behind(self, client):
        """Deleting somebody else's words is not a traceless act."""
        post_id, _ = self._one_open_report(client)
        sign_in_as_moderator(client)
        report = client.get("/api/social/moderation/reports").json()["items"][0]
        client.post(
            f"/api/social/moderation/reports/{report['id']}",
            json={"action": "remove", "note": "Удалено."},
        ).raise_for_status()

        closed = client.get("/api/social/moderation/reports?status=actioned").json()["items"][0]
        assert closed["resolved_by"] == "keeper@example.test"
        assert closed["resolution_note"] == "Удалено."
        assert closed["subject_id"] == post_id


def sign_in_as_moderator(client: TestClient) -> None:
    """The one account the settings name. Registered on first use."""
    existing = client.post(
        "/api/auth/login",
        json={"email": "keeper@example.test", "password": "correct horse battery keeper"},
    )
    if existing.status_code == 200:
        return
    registered = client.post(
        "/api/auth/register",
        json={
            "email": "keeper@example.test",
            "password": "correct horse battery keeper",
            "display_name": "Keeper",
            "organization_name": "Keeper Workspace",
        },
    )
    assert registered.status_code == 201, registered.text
