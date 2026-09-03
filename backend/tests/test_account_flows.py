"""The account flows that did not exist.

Before this there was no way to change a password, no way back in after losing
one, no way to leave, and no way to reach a second workspace. Each test below
is one of those, plus the negative case that makes it safe.
"""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.corpus.demo_profile import DEMO_PROFILE

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a different long passphrase"


@pytest.fixture
def auth_client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=20,
        run_rate_limit_per_minute=20,
        # Hashing a hundred throwaway passwords at the production cost buys
        # nothing; the parameters travel in the hash, so both are verifiable.
        password_scrypt_log2=14,
        database_url=f"sqlite:///{tmp_path / 'account.db'}",
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
    from app.api import routes_account, routes_auth

    original_get_settings = config_module.get_settings
    original_get_settings.cache_clear()
    for module in (config_module, security_module, routes_auth, routes_account):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "_limiter", main_module.FixedWindowLimiter())

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    with TestClient(main_module.app) as client:
        yield client, settings
    original_get_settings.cache_clear()


def register(client: TestClient, suffix: str, password: str = PASSWORD) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"{suffix}@example.test",
            "password": password,
            "display_name": suffix.title(),
            "organization_name": f"{suffix.title()} Workspace",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestPasswordChange:
    def test_changing_the_password_revokes_every_other_session(self, auth_client):
        client, _ = auth_client
        principal = register(client, "changer")

        from app.db import SessionLocal
        from app.models import AuthSession

        # A second device, signed in at the same time.
        other = TestClient(client.app)
        other.post("/api/auth/login", json={"email": "changer@example.test", "password": PASSWORD})
        with SessionLocal() as session:
            assert session.query(AuthSession).filter(
                AuthSession.user_id == principal["user_id"]
            ).count() == 2

        response = client.post(
            "/api/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200

        with SessionLocal() as session:
            assert session.query(AuthSession).filter(
                AuthSession.user_id == principal["user_id"]
            ).count() == 1, "the other device must be signed out"

        # The session that made the change still works; the old password does not.
        assert client.get("/api/auth/me").status_code == 200
        assert other.get("/api/auth/me").status_code == 401
        client.post("/api/auth/logout")
        assert client.post(
            "/api/auth/login", json={"email": "changer@example.test", "password": PASSWORD}
        ).status_code == 401
        assert client.post(
            "/api/auth/login", json={"email": "changer@example.test", "password": NEW_PASSWORD}
        ).status_code == 200

    def test_the_current_password_is_required(self, auth_client):
        client, _ = auth_client
        register(client, "wrongpass")
        response = client.post(
            "/api/auth/password",
            json={"current_password": "not the password", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert "not correct" in response.json()["detail"]

    def test_a_short_new_password_is_refused(self, auth_client):
        client, _ = auth_client
        register(client, "shortpass")
        response = client.post(
            "/api/auth/password", json={"current_password": PASSWORD, "new_password": "short"}
        )
        assert response.status_code == 422


class TestPasswordReset:
    def _request_link(self, client, email: str) -> str:
        response = client.post("/api/auth/password/reset-request", json={"email": email})
        assert response.status_code == 202
        return response.json()["reset_link"]

    def test_a_reset_link_gets_the_account_back(self, auth_client):
        client, _ = auth_client
        register(client, "forgetful")
        client.post("/api/auth/logout")

        token = self._request_link(client, "forgetful@example.test").split("token=")[1]
        response = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 200
        assert client.get("/api/auth/me").status_code == 200, "the reset signs the user in"

    def test_a_token_works_once(self, auth_client):
        client, _ = auth_client
        register(client, "replayer")
        client.post("/api/auth/logout")
        token = self._request_link(client, "replayer@example.test").split("token=")[1]

        assert client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        ).status_code == 200
        again = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": "yet another one"}
        )
        assert again.status_code == 400
        assert "no longer valid" in again.json()["detail"]

    def test_an_expired_token_is_refused(self, auth_client):
        from datetime import UTC, datetime, timedelta

        import sqlalchemy as sa

        client, _ = auth_client
        register(client, "slowpoke")
        client.post("/api/auth/logout")
        token = self._request_link(client, "slowpoke@example.test").split("token=")[1]

        from app.db import SessionLocal
        from app.models import PasswordResetToken

        with SessionLocal() as session:
            session.execute(
                sa.update(PasswordResetToken).values(
                    expires_at=datetime.now(UTC) - timedelta(minutes=1)
                )
            )
            session.commit()

        response = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400

    def test_someone_elses_token_is_just_a_token(self, auth_client):
        client, _ = auth_client
        register(client, "victim")
        client.post("/api/auth/logout")
        register(client, "attacker")
        client.post("/api/auth/logout")

        victim_token = self._request_link(client, "victim@example.test").split("token=")[1]
        # The attacker holds a token: it resets the account it was issued for,
        # and nothing else. Ownership travels with the token, not the request.
        response = client.post(
            "/api/auth/password/reset",
            json={"token": victim_token, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "victim@example.test"

    def test_a_reset_ends_every_existing_session(self, auth_client):
        client, _ = auth_client
        register(client, "compromised")
        intruder = TestClient(client.app)
        intruder.post(
            "/api/auth/login", json={"email": "compromised@example.test", "password": PASSWORD}
        )
        assert intruder.get("/api/auth/me").status_code == 200

        token = self._request_link(client, "compromised@example.test").split("token=")[1]
        client.post("/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD})

        assert intruder.get("/api/auth/me").status_code == 401

    def test_an_unknown_address_gets_the_same_answer(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/api/auth/password/reset-request", json={"email": "nobody@example.test"}
        )
        assert response.status_code == 202
        assert "If that email has an account" in response.json()["detail"]
        assert "reset_link" not in response.json(), "no link for an address with no account"

    def test_production_never_returns_the_link_in_the_response(self, auth_client, monkeypatch):
        client, settings = auth_client
        register(client, "prod-user")
        client.post("/api/auth/logout")
        monkeypatch.setattr(settings, "environment", "production")

        body = client.post(
            "/api/auth/password/reset-request", json={"email": "prod-user@example.test"}
        ).json()
        assert "reset_link" not in body


class TestWorkspaceSwitching:
    def test_the_current_workspace_is_listed_and_switchable(self, auth_client):
        client, _ = auth_client
        first = register(client, "multi")

        # A second workspace, joined directly: registration only ever makes one.
        from app.db import SessionLocal
        from app.models import Organization, OrganizationMembership

        with SessionLocal() as session:
            org = Organization(name="Second Workspace", slug="second-workspace")
            session.add(org)
            session.flush()
            session.add(
                OrganizationMembership(
                    user_id=first["user_id"], organization_id=org.id, role="owner"
                )
            )
            session.commit()
            second_id = org.id

        listed = client.get("/api/auth/organizations").json()
        assert {o["id"] for o in listed} == {first["organization_id"], second_id}
        assert [o["current"] for o in listed if o["id"] == first["organization_id"]] == [True]

        switched = client.post(
            "/api/auth/session/organization", json={"organization_id": second_id}
        )
        assert switched.status_code == 200
        assert switched.json()["organization_id"] == second_id
        assert client.get("/api/auth/me").json()["organization_id"] == second_id

    def test_switching_changes_which_cases_are_visible(self, auth_client):
        client, _ = auth_client
        principal = register(client, "scoped")
        client.post("/api/profiles", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json")))
        assert len(client.get("/api/profiles").json()) == 1

        from app.db import SessionLocal
        from app.models import Organization, OrganizationMembership

        with SessionLocal() as session:
            org = Organization(name="Empty Workspace", slug="empty-workspace")
            session.add(org)
            session.flush()
            session.add(
                OrganizationMembership(
                    user_id=principal["user_id"], organization_id=org.id, role="owner"
                )
            )
            session.commit()
            empty_id = org.id

        client.post("/api/auth/session/organization", json={"organization_id": empty_id})
        assert client.get("/api/profiles").json() == [], "tenant scope follows the session"

    def test_a_workspace_the_user_is_not_in_is_not_even_confirmed(self, auth_client):
        client, _ = auth_client
        register(client, "outsider")
        client.post("/api/auth/logout")
        stranger = register(client, "insider")

        client.post("/api/auth/logout")
        client.post("/api/auth/login", json={"email": "outsider@example.test", "password": PASSWORD})
        response = client.post(
            "/api/auth/session/organization",
            json={"organization_id": stranger["organization_id"]},
        )
        assert response.status_code == 404


class TestAccountDeletion:
    def test_deleting_an_account_takes_its_workspace_and_cases_with_it(self, auth_client):
        client, _ = auth_client
        principal = register(client, "leaver")
        client.post("/api/profiles", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json")))

        refused = client.post("/api/auth/me/delete", json={"password": PASSWORD})
        assert refused.status_code == 409, "data must not be destroyed without a second yes"

        response = client.post(
            "/api/auth/me/delete", json={"password": PASSWORD, "confirm_delete_data": True}
        )
        assert response.status_code == 204

        from app.db import SessionLocal
        from app.models import ApplicantProfileRow, AuditEvent, Organization, User

        with SessionLocal() as session:
            assert session.get(User, principal["user_id"]) is None
            assert session.get(Organization, principal["organization_id"]) is None
            assert session.query(ApplicantProfileRow).count() == 0
            # The record of the deletion survives the thing it describes.
            assert (
                session.query(AuditEvent)
                .filter(AuditEvent.action == "account_deleted")
                .count()
                == 1
            )

        assert client.get("/api/auth/me").status_code == 401

    def test_the_password_is_required_to_delete(self, auth_client):
        client, _ = auth_client
        register(client, "careful")
        response = client.post("/api/auth/me/delete", json={"password": "not it"})
        assert response.status_code == 400
        assert client.get("/api/auth/me").status_code == 200

    def test_a_shared_workspace_survives_one_member_leaving(self, auth_client):
        client, _ = auth_client
        owner = register(client, "stayer")
        client.post("/api/auth/logout")
        guest = register(client, "goer")

        from app.db import SessionLocal
        from app.models import Organization, OrganizationMembership

        with SessionLocal() as session:
            session.add(
                OrganizationMembership(
                    user_id=guest["user_id"],
                    organization_id=owner["organization_id"],
                    role="owner",
                )
            )
            session.commit()

        assert client.post("/api/auth/me/delete", json={"password": PASSWORD}).status_code == 204
        with SessionLocal() as session:
            assert session.get(Organization, owner["organization_id"]) is not None


class TestSessionHygiene:
    def test_sessions_are_capped_and_the_oldest_goes_first(self, auth_client, monkeypatch):
        client, settings = auth_client
        principal = register(client, "manydevices")
        monkeypatch.setattr(settings, "max_sessions_per_user", 3)

        for _ in range(5):
            device = TestClient(client.app)
            assert device.post(
                "/api/auth/login",
                json={"email": "manydevices@example.test", "password": PASSWORD},
            ).status_code == 200

        from app.db import SessionLocal
        from app.models import AuthSession

        with SessionLocal() as session:
            live = session.query(AuthSession).filter(
                AuthSession.user_id == principal["user_id"]
            ).count()
        assert live <= 3, f"{live} sessions survived a cap of 3"

    def test_an_expired_session_is_cleaned_up_on_the_next_login(self, auth_client):
        from datetime import UTC, datetime, timedelta

        import sqlalchemy as sa

        client, _ = auth_client
        principal = register(client, "expiring")

        from app.db import SessionLocal
        from app.models import AuthSession

        with SessionLocal() as session:
            session.execute(
                sa.update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(days=1))
            )
            session.commit()

        device = TestClient(client.app)
        device.post("/api/auth/login", json={"email": "expiring@example.test", "password": PASSWORD})

        with SessionLocal() as session:
            rows = session.query(AuthSession).filter(
                AuthSession.user_id == principal["user_id"]
            ).all()
        assert len(rows) == 1, "the expired row should not linger"


class TestPasswordHashing:
    def test_a_new_hash_uses_the_configured_cost(self, auth_client):
        client, settings = auth_client
        principal = register(client, "hashed")

        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            stored = session.get(User, principal["user_id"]).password_hash
        assert stored.startswith(f"scrypt${2 ** settings.password_scrypt_log2}$")

    def test_an_old_weaker_hash_still_verifies(self):
        """Existing accounts must not be locked out by raising the cost."""
        from app.security import hash_password, needs_rehash, verify_password

        legacy = hash_password(PASSWORD, n=2**12)
        assert verify_password(PASSWORD, legacy) is True
        assert needs_rehash(legacy) is True
