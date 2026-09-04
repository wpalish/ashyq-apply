"""The social API: joining, posting, threads, the feed and Discover.

The contract these tests hold, beyond the obvious:

* joining is an act, not a side effect of registering — nobody appears in
  Discover until they put a profile there;
* Discover crosses organizations on purpose, and carries nothing but what its
  owner typed. The applicant case stays behind the tenant boundary;
* the feed is newest-first and paginates on a cursor that cannot skip a post or
  show one twice, even when two posts share a timestamp.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.social import BIO_MAX_CHARS, POST_MAX_CHARS


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=100,
        social_rate_limit_per_minute=200,
        database_url=f"sqlite:///{tmp_path / 'social-api.db'}",
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


def register(client: TestClient, suffix: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"{suffix}@example.test",
            "password": f"correct horse battery {suffix}",
            "display_name": suffix.title(),
            "organization_name": f"{suffix.title()} Workspace",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, suffix: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": f"{suffix}@example.test", "password": f"correct horse battery {suffix}"},
    )
    assert response.status_code == 200, response.text


def join(client: TestClient, **profile) -> dict:
    payload = {
        "status": "waitlist",
        "target_city": "Astana",
        "target_major": "Computer Science",
        "bio": "",
        "universities": [],
    }
    payload.update(profile)
    response = client.put("/api/social/me", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def post(client: TestClient, body: str) -> dict:
    response = client.post("/api/social/posts", json={"body": body})
    assert response.status_code == 201, response.text
    return response.json()


class TestJoining:
    def test_registering_does_not_put_anyone_in_discover(self, client):
        register(client, "aigerim")

        assert client.get("/api/social/me").json() == {"joined": False, "profile": None}
        assert client.get("/api/social/people").json()["items"] == []

    def test_joining_creates_the_profile_and_lists_the_person(self, client):
        register(client, "dias")
        join(client, status="accepted", universities=["KBTU", "Nazarbayev University"])

        me = client.get("/api/social/me").json()
        assert me["joined"] is True
        assert me["profile"]["status"] == "accepted"
        assert me["profile"]["universities"] == ["KBTU", "Nazarbayev University"]

        people = client.get("/api/social/people").json()["items"]
        assert [person["display_name"] for person in people] == ["Dias"]

    def test_joining_twice_updates_rather_than_duplicates(self, client):
        register(client, "madina")
        join(client, target_city="Astana")
        join(client, target_city="Almaty", universities=["KBTU"])

        profile = client.get("/api/social/me").json()["profile"]
        assert profile["target_city"] == "Almaty"
        assert profile["universities"] == ["KBTU"]
        assert len(client.get("/api/social/people").json()["items"]) == 1

    def test_a_status_the_product_does_not_define_is_refused(self, client):
        register(client, "timur")
        assert client.put("/api/social/me", json={"status": "admitted"}).status_code == 422

    def test_a_status_may_be_left_unstated(self, client):
        register(client, "alua")
        join(client, status=None)
        assert client.get("/api/social/me").json()["profile"]["status"] is None

    def test_an_over_long_bio_is_refused(self, client):
        register(client, "bekzat")
        response = client.put("/api/social/me", json={"bio": "x" * (BIO_MAX_CHARS + 1)})
        assert response.status_code == 422

    def test_the_social_api_is_closed_to_strangers(self, client):
        assert client.get("/api/social/people").status_code == 401
        assert client.get("/api/social/feed").status_code == 401
        assert client.post("/api/social/posts", json={"body": "hi"}).status_code == 401


class TestPosting:
    def test_a_post_carries_its_author_and_the_tags_in_its_body(self, client):
        register(client, "ayana")
        join(client)
        created = post(client, "Кто подаётся в #KBTU и живёт в #Astana?")

        assert created["author"]["display_name"] == "Ayana"
        assert created["tags"] == ["KBTU", "Astana"]
        assert created["reply_count"] == 0

    def test_posting_requires_joining_first(self, client):
        register(client, "nurlan")
        response = client.post("/api/social/posts", json={"body": "Всем привет"})
        assert response.status_code == 409
        assert client.get("/api/social/feed").json()["items"] == []

    def test_a_blank_post_is_refused(self, client):
        register(client, "saltanat")
        join(client)
        assert client.post("/api/social/posts", json={"body": "   "}).status_code == 422

    def test_an_over_long_post_is_refused(self, client):
        register(client, "gulnara")
        join(client)
        body = "x" * (POST_MAX_CHARS + 1)
        assert client.post("/api/social/posts", json={"body": body}).status_code == 422


class TestFeed:
    def test_the_feed_is_newest_first(self, client):
        register(client, "arman")
        join(client)
        for text in ("первый", "второй", "третий"):
            post(client, text)

        bodies = [item["body"] for item in client.get("/api/social/feed").json()["items"]]
        assert bodies == ["третий", "второй", "первый"]

    def test_paging_never_skips_or_repeats_a_post(self, client):
        register(client, "zhanel")
        join(client)
        # Written in one loop, so several share a timestamp to the second and
        # the cursor has to break the tie on something else.
        for index in range(7):
            post(client, f"пост {index}")

        seen: list[str] = []
        cursor = None
        for _ in range(4):
            params = {"limit": 2}
            if cursor:
                params["cursor"] = cursor
            page = client.get("/api/social/feed", params=params).json()
            seen.extend(item["id"] for item in page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break

        assert len(seen) == 7
        assert len(set(seen)) == 7
        assert cursor is None

    def test_the_feed_can_be_narrowed_to_one_tag(self, client):
        register(client, "aliya")
        join(client)
        post(client, "вопрос про #KBTU")
        post(client, "вопрос про #NU")

        items = client.get("/api/social/feed", params={"tag": "kbtu"}).json()["items"]
        assert [item["body"] for item in items] == ["вопрос про #KBTU"]

    def test_a_tag_search_accepts_the_hash_and_any_casing(self, client):
        register(client, "damir")
        join(client)
        post(client, "еду в #KBTU")

        # Someone pasting the tag straight out of a post gets the hash with it.
        assert client.get("/api/social/feed", params={"tag": "#kbtu"}).json()["items"]
        assert client.get("/api/social/feed", params={"tag": " KBTU "}).json()["items"]

    def test_the_feed_can_be_narrowed_to_people_going_to_one_city(self, client):
        register(client, "askar")
        join(client, target_city="Astana")
        post(client, "из Астаны")
        client.post("/api/auth/logout")

        register(client, "aisulu")
        join(client, target_city="Almaty")
        post(client, "из Алматы")

        items = client.get("/api/social/feed", params={"city": "astana"}).json()["items"]
        assert [item["body"] for item in items] == ["из Астаны"]

    def test_a_profile_page_asks_the_feed_for_one_author(self, client):
        register(client, "kanat")
        join(client)
        post(client, "мой пост")
        author_id = client.get("/api/social/me").json()["profile"]["user_id"]
        client.post("/api/auth/logout")

        register(client, "meruert")
        join(client)
        post(client, "чужой пост")

        items = client.get("/api/social/feed", params={"author": author_id}).json()["items"]
        assert [item["body"] for item in items] == ["мой пост"]


class TestThreads:
    def test_a_reply_appears_under_its_post_and_is_counted(self, client):
        register(client, "asker")
        join(client)
        created = post(client, "Какой минимальный IELTS в KBTU?")
        client.post("/api/auth/logout")

        register(client, "zarina")
        join(client, status="accepted")
        reply = client.post(
            f"/api/social/posts/{created['id']}/replies", json={"body": "6.0 overall."}
        )
        assert reply.status_code == 201, reply.text
        assert reply.json()["author"]["status"] == "accepted"

        thread = client.get(f"/api/social/posts/{created['id']}/replies").json()
        assert [item["body"] for item in thread["items"]] == ["6.0 overall."]
        assert client.get("/api/social/feed").json()["items"][0]["reply_count"] == 1

    def test_a_thread_reads_oldest_first(self, client):
        register(client, "yerlan")
        join(client)
        created = post(client, "вопрос")
        for text in ("раз", "два", "три"):
            client.post(f"/api/social/posts/{created['id']}/replies", json={"body": text})

        thread = client.get(f"/api/social/posts/{created['id']}/replies").json()
        assert [item["body"] for item in thread["items"]] == ["раз", "два", "три"]

    def test_replies_never_leak_into_the_feed(self, client):
        register(client, "symbat")
        join(client)
        created = post(client, "вопрос")
        client.post(f"/api/social/posts/{created['id']}/replies", json={"body": "ответ"})

        assert [item["body"] for item in client.get("/api/social/feed").json()["items"]] == [
            "вопрос"
        ]

    def test_replying_to_a_post_that_does_not_exist_is_a_404(self, client):
        register(client, "rustem")
        join(client)
        response = client.post("/api/social/posts/deadbeef/replies", json={"body": "ответ"})
        assert response.status_code == 404


class TestDiscover:
    def _two_applicants(self, client) -> None:
        register(client, "kbtu-person")
        join(
            client,
            status="accepted",
            target_city="Astana",
            target_major="Computer Science",
            universities=["KBTU"],
        )
        client.post("/api/auth/logout")
        register(client, "almaty-person")
        join(
            client,
            status="waitlist",
            target_city="Almaty",
            target_major="Economics",
            universities=["KIMEP"],
        )

    def test_filtering_by_city(self, client):
        self._two_applicants(client)
        items = client.get("/api/social/people", params={"city": "Astana"}).json()["items"]
        assert [person["target_city"] for person in items] == ["Astana"]

    def test_filtering_by_status(self, client):
        self._two_applicants(client)
        items = client.get("/api/social/people", params={"status": "accepted"}).json()["items"]
        assert [person["status"] for person in items] == ["accepted"]

    def test_filtering_by_major(self, client):
        self._two_applicants(client)
        items = client.get("/api/social/people", params={"major": "economics"}).json()["items"]
        assert [person["target_major"] for person in items] == ["Economics"]

    def test_filtering_by_university_ignores_how_it_was_written(self, client):
        self._two_applicants(client)
        items = client.get("/api/social/people", params={"university": "k.b.t.u."}).json()["items"]
        assert [person["universities"] for person in items] == [["KBTU"]]

    def test_filters_combine(self, client):
        self._two_applicants(client)
        params = {"city": "Astana", "status": "waitlist"}
        assert client.get("/api/social/people", params=params).json()["items"] == []

    def test_a_card_opens_a_profile(self, client):
        self._two_applicants(client)
        card = client.get("/api/social/people", params={"city": "Astana"}).json()["items"][0]

        person = client.get(f"/api/social/people/{card['user_id']}").json()
        assert person["display_name"] == "Kbtu-Person"
        assert person["universities"] == ["KBTU"]

    def test_a_registered_account_that_never_joined_is_not_a_person_here(self, client):
        private = register(client, "private-person")
        client.post("/api/auth/logout")
        register(client, "curious")
        join(client)

        # The account exists and can log in. It is simply not in the community.
        assert client.get(f"/api/social/people/{private['user_id']}").status_code == 404
        assert client.get("/api/social/people/nobody").status_code == 404

        listed = client.get("/api/social/people").json()["items"]
        assert [person["display_name"] for person in listed] == ["Curious"]


class TestTheTenantBoundary:
    """Discover crosses organizations. Nothing else does."""

    def test_people_from_different_workspaces_can_find_each_other(self, client):
        first = register(client, "workspace-one")
        join(client, target_city="Astana")
        client.post("/api/auth/logout")
        second = register(client, "workspace-two")
        join(client, target_city="Astana")

        assert first["organization_id"] != second["organization_id"]
        items = client.get("/api/social/people", params={"city": "Astana"}).json()["items"]
        assert len(items) == 2

    def test_a_social_profile_exposes_nothing_from_the_applicant_case(self, client):
        register(client, "case-owner")
        join(client, bio="Готовлюсь к SAT.")
        owner = client.get("/api/social/me").json()["profile"]["user_id"]
        client.post("/api/auth/logout")

        register(client, "stranger")
        join(client)
        person = client.get(f"/api/social/people/{owner}").json()

        assert set(person) == {
            "user_id",
            "display_name",
            "status",
            "target_city",
            "target_major",
            "universities",
            "bio",
        }
        # No email, no organization, and nothing that names a case or a run.
        assert "email" not in person
        assert "organization_id" not in person

    def test_a_shared_feed_does_not_widen_the_applicant_case_boundary(self, client):
        import copy

        from app.corpus.demo_profile import DEMO_PROFILE

        register(client, "tenant-a")
        join(client)
        created = client.post(
            "/api/profiles", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
        )
        assert created.status_code == 201
        case_id = created.json()["id"]
        client.post("/api/auth/logout")

        register(client, "tenant-b")
        join(client)

        # Tenant B sees tenant A in Discover — that is the point of the module.
        assert len(client.get("/api/social/people").json()["items"]) == 2
        # ...and still cannot see, name or open their applicant case.
        assert client.get("/api/cases").json() == []
        assert client.get("/api/profiles").json() == []
        assert client.get(f"/api/profiles/{case_id}").status_code == 404
