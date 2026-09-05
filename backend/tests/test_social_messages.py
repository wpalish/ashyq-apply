"""Private conversations, and the rule about who may start one.

The product has no follow graph, so "mutual follows" cannot be the rule here.
What it does have is a public thread the two people were both in — one of them
answered the other where everyone could see it — and that is the default
signal. The other two settings are the honest ends of the range: anyone, or
nobody.

The default is the narrow one. These users are school leavers, some of them
minors, and every profile is visible across the whole service; an inbox open
to strangers is a choice, not a starting position.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.social import MESSAGE_MAX_CHARS


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=100,
        social_rate_limit_per_minute=200,
        database_url=f"sqlite:///{tmp_path / 'messages.db'}",
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
    """Register, join the community, and return the new user's id."""
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
    payload = {"status": None, "target_city": "", "target_major": "", "bio": "", "universities": []}
    payload.update(profile)
    saved = client.put("/api/social/me", json=payload)
    assert saved.status_code == 200, saved.text
    return registered.json()["user_id"]


def sign_in(client: TestClient, slug: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": f"{slug}@example.test", "password": f"correct horse battery {slug}"},
    )
    assert response.status_code == 200, response.text


def talk_in_public(client: TestClient, asker: str, answerer: str) -> None:
    """Have `answerer` reply to a post by `asker`, which is the THREADS signal."""
    sign_in(client, asker)
    post = client.post("/api/social/posts", json={"body": "Открытый вопрос"})
    assert post.status_code == 201, post.text
    client.post("/api/auth/logout")

    sign_in(client, answerer)
    reply = client.post(
        f"/api/social/posts/{post.json()['id']}/replies", json={"body": "Публичный ответ"}
    )
    assert reply.status_code == 201, reply.text
    client.post("/api/auth/logout")


class TestWhoMayWriteFirst:
    def test_a_new_profile_starts_on_the_narrow_policy(self, client):
        join_as(client, "fresh")
        assert client.get("/api/social/me").json()["profile"]["dm_policy"] == "threads"

    def test_a_stranger_cannot_open_a_conversation_by_default(self, client):
        listener = join_as(client, "listener")
        client.post("/api/auth/logout")
        join_as(client, "stranger")

        blocked = client.post(f"/api/social/messages/{listener}", json={"body": "Привет"})
        assert blocked.status_code == 403
        assert "answered" in blocked.json()["detail"]

    def test_answering_someone_in_public_opens_the_door(self, client):
        asker = join_as(client, "asker")
        client.post("/api/auth/logout")
        answerer = join_as(client, "answerer")
        client.post("/api/auth/logout")
        talk_in_public(client, "asker", "answerer")

        # The person who answered may now write privately...
        sign_in(client, "answerer")
        assert client.post(f"/api/social/messages/{asker}", json={"body": "Могу помочь"}).status_code == 201
        client.post("/api/auth/logout")

        # ...and so may the person whose post was answered.
        sign_in(client, "asker")
        assert client.post(f"/api/social/messages/{answerer}", json={"body": "Спасибо!"}).status_code == 201

    def test_anyone_means_anyone(self, client):
        open_person = join_as(client, "open-person", dm_policy="anyone")
        client.post("/api/auth/logout")
        join_as(client, "some-stranger")

        assert client.post(
            f"/api/social/messages/{open_person}", json={"body": "Здравствуйте"}
        ).status_code == 201

    def test_nobody_means_nobody_even_after_a_public_thread(self, client):
        join_as(client, "quiet", dm_policy="nobody")
        client.post("/api/auth/logout")
        join_as(client, "persistent")
        client.post("/api/auth/logout")
        talk_in_public(client, "quiet", "persistent")

        quiet_id = None
        sign_in(client, "persistent")
        for person in client.get("/api/social/people").json()["items"]:
            if person["display_name"] == "Quiet":
                quiet_id = person["user_id"]
        assert quiet_id is not None

        refused = client.post(f"/api/social/messages/{quiet_id}", json={"body": "Ну пожалуйста"})
        assert refused.status_code == 403

    def test_the_policy_only_guards_the_first_message(self, client):
        """Closing your inbox does not silence a conversation you already have."""
        host = join_as(client, "host2", dm_policy="anyone")
        client.post("/api/auth/logout")
        guest = join_as(client, "guest2")
        client.post(f"/api/social/messages/{host}", json={"body": "Первое сообщение"})
        client.post("/api/auth/logout")

        sign_in(client, "host2")
        client.put(
            "/api/social/me",
            json={
                "status": None, "target_city": "", "target_major": "", "bio": "",
                "universities": [], "dm_policy": "nobody",
            },
        )
        # The existing thread still works, in both directions.
        assert client.post(f"/api/social/messages/{guest}", json={"body": "Отвечаю"}).status_code == 201
        client.post("/api/auth/logout")
        sign_in(client, "guest2")
        assert client.post(f"/api/social/messages/{host}", json={"body": "И я"}).status_code == 201

    def test_a_policy_the_product_does_not_define_is_refused(self, client):
        join_as(client, "creative")
        response = client.put(
            "/api/social/me",
            json={
                "status": None, "target_city": "", "target_major": "", "bio": "",
                "universities": [], "dm_policy": "friends-of-friends",
            },
        )
        assert response.status_code == 422

    def test_you_cannot_message_someone_who_never_joined(self, client):
        registered = client.post(
            "/api/auth/register",
            json={
                "email": "lurker@example.test",
                "password": "correct horse battery lurker",
                "display_name": "Lurker",
                "organization_name": "Lurker Workspace",
            },
        )
        lurker = registered.json()["user_id"]
        client.post("/api/auth/logout")
        join_as(client, "writer", dm_policy="anyone")

        assert client.post(f"/api/social/messages/{lurker}", json={"body": "Эй"}).status_code == 404

    def test_you_cannot_message_yourself(self, client):
        me = join_as(client, "solo", dm_policy="anyone")
        assert client.post(f"/api/social/messages/{me}", json={"body": "Заметка"}).status_code == 400


class TestTheConversation:
    def _pair(self, client) -> tuple[str, str]:
        first = join_as(client, "ainur", dm_policy="anyone")
        client.post("/api/auth/logout")
        second = join_as(client, "bolat", dm_policy="anyone")
        return first, second

    def test_a_conversation_reads_oldest_first_and_both_sides_see_it(self, client):
        ainur, _ = self._pair(client)
        client.post(f"/api/social/messages/{ainur}", json={"body": "Первое"})
        client.post(f"/api/social/messages/{ainur}", json={"body": "Второе"})
        client.post("/api/auth/logout")

        sign_in(client, "ainur")
        thread = client.get("/api/social/messages/" + _id_of(client, "Bolat")).json()
        assert [m["body"] for m in thread["items"]] == ["Первое", "Второе"]
        assert [m["mine"] for m in thread["items"]] == [False, False]

    def test_writing_twice_does_not_create_two_conversations(self, client):
        ainur, _ = self._pair(client)
        client.post(f"/api/social/messages/{ainur}", json={"body": "Раз"})
        client.post(f"/api/social/messages/{ainur}", json={"body": "Два"})

        assert len(client.get("/api/social/messages").json()["items"]) == 1

    def test_the_list_shows_the_other_person_and_the_last_line(self, client):
        ainur, _ = self._pair(client)
        client.post(f"/api/social/messages/{ainur}", json={"body": "Последнее слово"})

        conversation = client.get("/api/social/messages").json()["items"][0]
        assert conversation["person"]["display_name"] == "Ainur"
        assert conversation["last_message"] == "Последнее слово"
        assert conversation["unread"] == 0  # my own message is not unread to me

    def test_unread_counts_what_the_other_side_sent_since_you_looked(self, client):
        ainur, bolat = self._pair(client)
        client.post(f"/api/social/messages/{ainur}", json={"body": "Один"})
        client.post(f"/api/social/messages/{ainur}", json={"body": "Два"})
        client.post("/api/auth/logout")

        sign_in(client, "ainur")
        assert client.get("/api/social/messages").json()["items"][0]["unread"] == 2
        assert client.get("/api/social/messages/unread").json() == {"unread": 2}

        # Opening the conversation is what marks it read.
        client.get(f"/api/social/messages/{bolat}")
        assert client.get("/api/social/messages").json()["items"][0]["unread"] == 0
        assert client.get("/api/social/messages/unread").json() == {"unread": 0}

    def test_an_empty_or_over_long_message_is_refused(self, client):
        ainur, _ = self._pair(client)
        assert client.post(f"/api/social/messages/{ainur}", json={"body": "   "}).status_code == 422
        long_body = "x" * (MESSAGE_MAX_CHARS + 1)
        assert client.post(
            f"/api/social/messages/{ainur}", json={"body": long_body}
        ).status_code == 422

    def test_the_inbox_is_closed_to_strangers(self, client):
        assert client.get("/api/social/messages").status_code == 401

    def test_leaving_does_not_delete_the_other_persons_copy(self, client):
        """A conversation belongs to two people.

        Leaving erases what you published — profile, posts, replies — because
        that was addressed to everyone. A private thread was addressed to one
        person, and taking it away would delete their record of a conversation
        they were half of. What leaving does end is being reachable: with no
        profile there is nobody to write to.
        """
        ainur, _ = self._pair(client)
        client.post(f"/api/social/messages/{ainur}", json={"body": "До свидания"})
        bolat = client.get("/api/social/me").json()["profile"]["user_id"]

        assert client.delete("/api/social/me").status_code == 204
        client.post("/api/auth/logout")

        sign_in(client, "ainur")
        conversation = client.get("/api/social/messages").json()["items"][0]
        assert conversation["last_message"] == "До свидания"
        # The card falls back to the account name; nothing published survives.
        assert conversation["person"]["display_name"] == "Bolat"
        assert conversation["person"]["universities"] == []
        # ...and they cannot be written to any more.
        assert client.post(f"/api/social/messages/{bolat}", json={"body": "Ау"}).status_code == 404


def _id_of(client: TestClient, display_name: str) -> str:
    for person in client.get("/api/social/people").json()["items"]:
        if person["display_name"] == display_name:
            return person["user_id"]
    raise AssertionError(f"{display_name} is not in Discover")
