"""Uploading a picture, and getting it back.

The byte-level rules are pinned in `test_avatar_bytes.py`. What is checked here
is the part a person touches: that a bad file is refused with a reason, that
the picture comes back from our own origin, and that it obeys the same rules as
everything else in this module — you must have joined, and a block hides it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.avatar import MAX_AVATAR_BYTES
from tests.test_avatar_bytes import jpeg_with_exif, png_with_text


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=100,
        social_rate_limit_per_minute=200,
        database_url=f"sqlite:///{tmp_path / 'avatars.db'}",
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


def join_as(client: TestClient, slug: str) -> str:
    registered = client.post("/api/auth/register", json={
        "email": f"{slug}@example.test",
        "password": f"correct horse battery {slug}",
        "display_name": slug.title(),
        "organization_name": f"{slug.title()} Workspace",
    })
    assert registered.status_code == 201, registered.text
    client.put("/api/social/me", json={
        "status": None, "target_city": "", "target_major": "", "bio": "",
        "universities": [], "dm_policy": "anyone",
    }).raise_for_status()
    return registered.json()["user_id"]


def upload(client: TestClient, data: bytes, name: str = "me.jpg", kind: str = "image/jpeg"):
    return client.put("/api/social/me/avatar", files={"file": (name, data, kind)})


class TestUploading:
    def test_a_picture_can_be_set_and_read_back(self, client):
        me = join_as(client, "photogenic")
        assert upload(client, jpeg_with_exif()).status_code == 204

        got = client.get(f"/api/social/avatars/{me}")
        assert got.status_code == 200
        assert got.headers["content-type"].startswith("image/jpeg")
        assert got.content.startswith(b"\xff\xd8")

    def test_the_stored_picture_has_had_its_metadata_removed(self, client):
        """The end-to-end version of the rule: what is served carries no EXIF."""
        me = join_as(client, "careful-one")
        upload(client, jpeg_with_exif())

        served = client.get(f"/api/social/avatars/{me}").content
        assert b"Exif" not in served
        assert b"a fake EXIF payload" not in served

    def test_a_png_works_too(self, client):
        me = join_as(client, "screenshotter")
        assert upload(client, png_with_text(), "shot.png", "image/png").status_code == 204
        assert client.get(f"/api/social/avatars/{me}").headers["content-type"].startswith(
            "image/png"
        )

    def test_the_bytes_decide_the_format_not_the_header(self, client):
        """An SVG announced as a PNG is still an SVG, and is refused."""
        join_as(client, "sneaky")
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        refused = upload(client, svg, "avatar.png", "image/png")
        assert refused.status_code == 400
        assert "JPEG or a PNG" in refused.json()["detail"]

    def test_an_over_large_picture_is_refused_by_size(self, client):
        join_as(client, "generous")
        # Valid magic bytes, far too many of them.
        too_big = b"\xff\xd8\xff" + b"\x00" * (MAX_AVATAR_BYTES + 10)
        assert upload(client, too_big).status_code == 413

    def test_an_empty_file_is_refused(self, client):
        join_as(client, "empty-handed")
        assert upload(client, b"").status_code == 400

    def test_uploading_twice_replaces_rather_than_duplicates(self, client):
        me = join_as(client, "changeable")
        upload(client, jpeg_with_exif())
        assert upload(client, png_with_text(), "shot.png", "image/png").status_code == 204
        assert client.get(f"/api/social/avatars/{me}").headers["content-type"].startswith(
            "image/png"
        )

    def test_a_picture_needs_a_profile_first(self, client):
        """Same rule as posting: joining is what publishes anything about you."""
        client.post("/api/auth/register", json={
            "email": "lurker@example.test",
            "password": "correct horse battery lurker",
            "display_name": "Lurker",
            "organization_name": "Lurker Workspace",
        }).raise_for_status()
        assert upload(client, jpeg_with_exif()).status_code == 409


class TestReadingSomeoneElses:
    def test_no_picture_is_a_404_rather_than_a_placeholder(self, client):
        me = join_as(client, "plain")
        assert client.get(f"/api/social/avatars/{me}").status_code == 404

    def test_removing_your_picture_puts_it_back_to_none(self, client):
        me = join_as(client, "changed-mind")
        upload(client, jpeg_with_exif())
        assert client.delete("/api/social/me/avatar").status_code == 204
        assert client.get(f"/api/social/avatars/{me}").status_code == 404

    def test_a_blocked_person_cannot_fetch_your_picture(self, client):
        subject = join_as(client, "blocker")
        upload(client, jpeg_with_exif())
        client.post("/api/auth/logout")

        other = join_as(client, "blocked-one")
        assert client.get(f"/api/social/avatars/{subject}").status_code == 200
        client.post("/api/auth/logout")

        client.post("/api/auth/login", json={
            "email": "blocker@example.test", "password": "correct horse battery blocker",
        }).raise_for_status()
        client.post(f"/api/social/blocks/{other}").raise_for_status()
        client.post("/api/auth/logout")

        client.post("/api/auth/login", json={
            "email": "blocked-one@example.test", "password": "correct horse battery blocked-one",
        }).raise_for_status()
        assert client.get(f"/api/social/avatars/{subject}").status_code == 404

    def test_the_picture_is_not_public(self, client):
        me = join_as(client, "private-face")
        upload(client, jpeg_with_exif())
        client.post("/api/auth/logout")
        assert client.get(f"/api/social/avatars/{me}").status_code == 401

    def test_leaving_the_community_takes_the_picture(self, client):
        me = join_as(client, "departing")
        upload(client, jpeg_with_exif())
        assert client.delete("/api/social/me").status_code == 204
        # Still signed in, and there is nothing of them left to fetch.
        assert client.get(f"/api/social/avatars/{me}").status_code == 404
