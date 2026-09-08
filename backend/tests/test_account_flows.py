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
from app.mail import Message, RecordingSender

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


@pytest.fixture
def mail_sink(auth_client, monkeypatch):
    """auth_client with the route's mail sender bound to a recording sink.

    The reset token must be observable through the delivered letter and
    through nothing else, so this stands in for the user's mailbox at the
    same seam the route itself uses: the module-level ``get_sender`` binding
    in ``app.api.routes_account``. The sender itself is the official test
    sink from ``app.mail``.
    """
    client, settings = auth_client
    sink = RecordingSender()
    import app.api.routes_account as routes_account

    monkeypatch.setattr(routes_account, "get_sender", lambda _settings: sink)
    return client, settings, sink


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


def reset_token_from_letter(message: Message) -> str:
    """The token as the recipient of the letter would read it off the link."""
    link_line = next(line for line in message.body.splitlines() if "token=" in line)
    return link_line.split("token=", 1)[1]


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
            assert (
                session.query(AuthSession)
                .filter(AuthSession.user_id == principal["user_id"])
                .count()
                == 2
            )

        response = client.post(
            "/api/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200

        with SessionLocal() as session:
            assert (
                session.query(AuthSession)
                .filter(AuthSession.user_id == principal["user_id"])
                .count()
                == 1
            ), "the other device must be signed out"

        # The session that made the change still works; the old password does not.
        assert client.get("/api/auth/me").status_code == 200
        assert other.get("/api/auth/me").status_code == 401
        client.post("/api/auth/logout")
        assert (
            client.post(
                "/api/auth/login", json={"email": "changer@example.test", "password": PASSWORD}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login", json={"email": "changer@example.test", "password": NEW_PASSWORD}
            ).status_code
            == 200
        )

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
    def _request_token(self, client: TestClient, sink: RecordingSender, email: str) -> str:
        """Ask for a reset, then read the token off the delivered letter.

        The API answer carries no token in any environment; the letter is the
        only place the recipient ever sees one.
        """
        response = client.post("/api/auth/password/reset-request", json={"email": email})
        assert response.status_code == 202
        assert len(sink.messages) == 1, "one request, one letter"
        return reset_token_from_letter(sink.messages[0])

    def test_a_reset_link_gets_the_account_back(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "forgetful")
        client.post("/api/auth/logout")

        token = self._request_token(client, sink, "forgetful@example.test")
        response = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 200
        assert client.get("/api/auth/me").status_code == 200, "the reset signs the user in"

    def test_a_token_works_once(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "replayer")
        client.post("/api/auth/logout")
        token = self._request_token(client, sink, "replayer@example.test")

        assert (
            client.post(
                "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
            ).status_code
            == 200
        )
        again = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": "yet another one"}
        )
        assert again.status_code == 400
        assert "no longer valid" in again.json()["detail"]

    def test_an_expired_token_is_refused(self, mail_sink):
        from datetime import UTC, datetime, timedelta

        import sqlalchemy as sa

        client, _, sink = mail_sink
        register(client, "slowpoke")
        client.post("/api/auth/logout")
        token = self._request_token(client, sink, "slowpoke@example.test")

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

    def test_someone_elses_token_is_just_a_token(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "victim")
        client.post("/api/auth/logout")
        register(client, "attacker")
        client.post("/api/auth/logout")

        victim_token = self._request_token(client, sink, "victim@example.test")
        # The attacker holds a token: it resets the account it was issued for,
        # and nothing else. Ownership travels with the token, not the request.
        response = client.post(
            "/api/auth/password/reset",
            json={"token": victim_token, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "victim@example.test"

    def test_a_reset_ends_every_existing_session(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "compromised")
        intruder = TestClient(client.app)
        intruder.post(
            "/api/auth/login", json={"email": "compromised@example.test", "password": PASSWORD}
        )
        assert intruder.get("/api/auth/me").status_code == 200

        token = self._request_token(client, sink, "compromised@example.test")
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


class TestResetTokenNeverLeavesTheMailbox:
    """S01: the reset token travels by mail, never in an API response.

    The old behavior appended ``reset_link`` to the 202 body in every
    non-production environment, handing a working single-use token to
    whoever asked — no mailbox required. Whatever the environment, the
    answer stays ``{"detail": ...}`` and the token is observable only in
    the delivered letter.
    """

    @pytest.mark.parametrize("environment", ["development", "staging", "production", "testing"])
    def test_no_environment_puts_the_token_in_the_response(
        self, auth_client, monkeypatch, environment
    ):
        client, settings = auth_client
        register(client, "envprobe")
        client.post("/api/auth/logout")
        monkeypatch.setattr(settings, "environment", environment)

        response = client.post(
            "/api/auth/password/reset-request", json={"email": "envprobe@example.test"}
        )
        assert response.status_code == 202
        body = response.json()
        assert set(body) == {"detail"}, f"[{environment}] response carried {sorted(body)}"
        leaked = [key for key in body if "token" in key.lower() or "link" in key.lower()]
        assert not leaked, f"[{environment}] response carried {leaked}"

    def test_the_letter_delivers_a_working_token(self, mail_sink):
        """The owner, with the mailbox, can complete the reset."""
        client, _, sink = mail_sink
        register(client, "mailbox")
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/password/reset-request", json={"email": "mailbox@example.test"}
        )
        assert response.status_code == 202
        assert set(response.json()) == {"detail"}, "even success keeps the answer neutral"

        assert len(sink.messages) == 1, "one request, one letter"
        letter = sink.messages[0]
        assert letter.to == "mailbox@example.test"
        token = reset_token_from_letter(letter)

        done = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert done.status_code == 200
        assert client.get("/api/auth/me").status_code == 200, "the reset signs the user in"

    def test_a_stranger_gets_no_token_in_the_answer(self, mail_sink):
        """A signed-out stranger asking for the victim's reset sees nothing."""
        client, _, sink = mail_sink
        register(client, "victim")

        stranger = TestClient(client.app)
        response = stranger.post(
            "/api/auth/password/reset-request", json={"email": "victim@example.test"}
        )
        assert response.status_code == 202
        assert set(response.json()) == {"detail"}

        assert len(sink.messages) == 1, "the letter went out"
        assert sink.messages[0].to == "victim@example.test", "to the victim, not the stranger"
        token = reset_token_from_letter(sink.messages[0])
        assert token not in response.text, "the token must not travel in the answer"

    def test_every_address_shape_gets_the_same_neutral_answer(self, mail_sink):
        """Existing, unknown, malformed and inactive read identically."""
        client, _, sink = mail_sink
        register(client, "neutral")
        client.post("/api/auth/logout")
        register(client, "inactive")

        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            dormant = session.query(User).filter(User.email == "inactive@example.test").one()
            dormant.is_active = False
            session.commit()
        client.post("/api/auth/logout")

        shapes = {
            "existing": "neutral@example.test",
            "unknown": "nobody@example.test",
            "malformed": "not-an-email",
            "inactive": "inactive@example.test",
        }
        answers = {}
        for label, email in shapes.items():
            response = client.post("/api/auth/password/reset-request", json={"email": email})
            assert response.status_code == 202, label
            answers[label] = response.json()

        for label, body in answers.items():
            assert set(body) == {"detail"}, f"[{label}] response carried {sorted(body)}"
        assert all(body == answers["existing"] for body in answers.values()), (
            "the four shapes must be indistinguishable"
        )
        assert [letter.to for letter in sink.messages] == ["neutral@example.test"], (
            "only the existing, active account gets a letter"
        )

    def test_a_token_from_the_letter_works_exactly_once(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "once")
        client.post("/api/auth/logout")
        client.post("/api/auth/password/reset-request", json={"email": "once@example.test"})
        token = reset_token_from_letter(sink.messages[0])

        first = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert first.status_code == 200
        again = client.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": "yet another long passphrase"},
        )
        assert again.status_code == 400
        assert "no longer valid" in again.json()["detail"]

    def test_an_expired_letter_is_refused(self, mail_sink, monkeypatch):
        client, settings, sink = mail_sink
        monkeypatch.setattr(settings, "password_reset_ttl_minutes", -1)
        register(client, "expiredletter")
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/password/reset-request", json={"email": "expiredletter@example.test"}
        )
        token = reset_token_from_letter(sink.messages[0])

        response = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400
        assert "no longer valid" in response.json()["detail"]

    def test_a_reset_from_the_letter_ends_every_existing_session(self, mail_sink):
        client, _, sink = mail_sink
        register(client, "revoked")
        intruder = TestClient(client.app)
        intruder.post(
            "/api/auth/login", json={"email": "revoked@example.test", "password": PASSWORD}
        )
        assert intruder.get("/api/auth/me").status_code == 200

        client.post("/api/auth/password/reset-request", json={"email": "revoked@example.test"})
        token = reset_token_from_letter(sink.messages[0])
        done = client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert done.status_code == 200

        assert intruder.get("/api/auth/me").status_code == 401, "old sessions are gone"
        assert client.get("/api/auth/me").status_code == 200
        client.post("/api/auth/logout")
        assert (
            client.post(
                "/api/auth/login", json={"email": "revoked@example.test", "password": NEW_PASSWORD}
            ).status_code
            == 200
        ), "the owner is back in with the new password"


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
        client.post(
            "/api/auth/login", json={"email": "outsider@example.test", "password": PASSWORD}
        )
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
                session.query(AuditEvent).filter(AuditEvent.action == "account_deleted").count()
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
            assert (
                device.post(
                    "/api/auth/login",
                    json={"email": "manydevices@example.test", "password": PASSWORD},
                ).status_code
                == 200
            )

        from app.db import SessionLocal
        from app.models import AuthSession

        with SessionLocal() as session:
            live = (
                session.query(AuthSession)
                .filter(AuthSession.user_id == principal["user_id"])
                .count()
            )
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
        device.post(
            "/api/auth/login", json={"email": "expiring@example.test", "password": PASSWORD}
        )

        with SessionLocal() as session:
            rows = (
                session.query(AuthSession).filter(AuthSession.user_id == principal["user_id"]).all()
            )
        assert len(rows) == 1, "the expired row should not linger"


class TestPasswordHashing:
    def test_a_new_hash_uses_the_configured_cost(self, auth_client):
        client, settings = auth_client
        principal = register(client, "hashed")

        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            stored = session.get(User, principal["user_id"]).password_hash
        assert stored.startswith(f"scrypt${2**settings.password_scrypt_log2}$")

    def test_an_old_weaker_hash_still_verifies(self):
        """Existing accounts must not be locked out by raising the cost."""
        from app.security import hash_password, needs_rehash, verify_password

        legacy = hash_password(PASSWORD, n=2**12)
        assert verify_password(PASSWORD, legacy) is True
        assert needs_rehash(legacy) is True


def _send_through_recording_smtp(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> dict:
    """Deliver one message through SmtpSender over a fake smtplib.SMTP.

    The double matches the constructor shape mail.py actually calls — host
    and port positionally, ``timeout`` by keyword — and records how STARTTLS
    was called. Returns the kwargs of that one call.
    """
    from app import mail as mail_module

    starttls_calls: list[dict] = []

    class RecordingSMTP:
        def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self) -> RecordingSMTP:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def starttls(self, **kwargs: object) -> None:
            starttls_calls.append(kwargs)

        def login(self, username: str, password: str) -> None:
            pass

        def send_message(self, message: object) -> None:
            pass

    monkeypatch.setattr(mail_module.smtplib, "SMTP", RecordingSMTP)
    mail_module.SmtpSender(settings).send(
        Message(to="person@example.test", subject="Reset your password", body="the link")
    )
    assert len(starttls_calls) == 1, (
        f"STARTTLS was called {len(starttls_calls)} times, expected exactly once"
    )
    return starttls_calls[0]


class TestStarttlsUsesAVerifiedTlsContext:
    """S4: STARTTLS must be negotiated with a certificate-verifying context.

    ``starttls()`` without a context makes smtplib build an unverified one:
    the connection is encrypted, but nobody checked who is on the other end,
    so a machine on the path can relay password-reset mail — reset links
    included — through itself.
    """

    def test_starttls_gets_a_verifying_ssl_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import ssl

        settings = Settings(
            demo_mode=True,
            email_sender="smtp",
            smtp_host="smtp.example.test",
            smtp_from="no-reply@example.test",
        )
        starttls_kwargs = _send_through_recording_smtp(monkeypatch, settings)
        context = starttls_kwargs.get("context")
        assert context is not None, "STARTTLS was called without a context"
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_starttls_verification_can_be_disabled_for_a_self_hosted_relay(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import ssl

        settings = Settings(
            demo_mode=True,
            email_sender="smtp",
            smtp_host="smtp.example.test",
            smtp_from="no-reply@example.test",
            # A relay on a trusted internal network may not present a name the
            # public CA system can check. That is a deliberate, explicit opt
            # out — the setting has to exist, and only it may turn this off.
            smtp_tls_verify=False,
        )
        starttls_kwargs = _send_through_recording_smtp(monkeypatch, settings)
        context = starttls_kwargs.get("context")
        assert context is not None, "STARTTLS was called without a context"
        assert context.check_hostname is False
        assert context.verify_mode == ssl.CERT_NONE


class TestLoginRehashesOldCostHashes:
    """S5: a successful login must rewrite a weak-cost hash, and audit it once.

    Old hashes still verify and ``needs_rehash`` exists, but login never
    consults it: an account stored at an old scrypt cost stays there forever,
    and nothing records the upgrade once it happens.
    """

    @staticmethod
    def _store_legacy_hash(user_id: str) -> str:
        from app.db import SessionLocal
        from app.models import User
        from app.security import hash_password

        legacy = hash_password(PASSWORD, n=2**12)
        with SessionLocal() as session:
            stored = session.get(User, user_id)
            assert stored is not None
            stored.password_hash = legacy
            session.commit()
        return legacy

    @staticmethod
    def _stored_hash(user_id: str) -> str:
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            user = session.get(User, user_id)
            assert user is not None
            return user.password_hash

    @staticmethod
    def _rehash_events(user_id: str) -> int:
        from app.db import SessionLocal
        from app.models import AuditEvent

        with SessionLocal() as session:
            return (
                session.query(AuditEvent)
                .filter(
                    AuditEvent.action == "password_rehashed",
                    AuditEvent.entity_id == user_id,
                )
                .count()
            )

    @staticmethod
    def _login(client: TestClient, email: str, password: str = PASSWORD) -> int:
        return client.post(
            "/api/auth/login", json={"email": email, "password": password}
        ).status_code

    def test_login_upgrades_an_old_cost_hash_and_audits_it_once(self, auth_client) -> None:
        from app.security import needs_rehash, verify_password

        client, settings = auth_client
        principal = register(client, "legacy")
        legacy = self._store_legacy_hash(principal["user_id"])
        client.post("/api/auth/logout")

        assert self._login(client, "legacy@example.test") == 200

        stored = self._stored_hash(principal["user_id"])
        assert stored != legacy, "a successful login must rewrite a weak-cost hash"
        assert stored.startswith(f"scrypt${2**settings.password_scrypt_log2}$")
        assert verify_password(PASSWORD, stored)
        assert needs_rehash(stored) is False
        assert self._rehash_events(principal["user_id"]) == 1

        client.post("/api/auth/logout")
        assert self._login(client, "legacy@example.test") == 200
        assert self._stored_hash(principal["user_id"]) == stored, (
            "the second login must not rewrite the hash again"
        )
        assert self._rehash_events(principal["user_id"]) == 1, (
            "the second login must not audit a second rehash"
        )

    def test_a_wrong_password_on_a_legacy_account_rehashes_nothing(self, auth_client) -> None:
        """Only a successful verification earns the rewrite."""
        client, _ = auth_client
        principal = register(client, "guarded")
        legacy = self._store_legacy_hash(principal["user_id"])
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/login",
            json={"email": "guarded@example.test", "password": "a wrong passphrase here"},
        )
        assert response.status_code == 401
        assert self._stored_hash(principal["user_id"]) == legacy
        assert self._rehash_events(principal["user_id"]) == 0

    def test_a_legacy_short_password_login_is_not_broken(self, auth_client) -> None:
        """A pre-rule password under 12 characters must still log in.

        ``hash_password`` refuses anything shorter than 12 characters, so an
        upgrade attempt on such an account cannot succeed. The login itself
        must go through — the stored hash is hand-built here precisely
        because the helper refuses to build it — and no rehash is recorded.
        """
        import hashlib
        import secrets

        from app.db import SessionLocal
        from app.models import User

        client, _ = auth_client
        principal = register(client, "shortlegacy")
        short = "just-short"  # ten characters: verifiable, un-hashable today
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(short.encode(), salt=salt, n=4096, r=8, p=1, dklen=32, maxmem=2**28)
        legacy = f"scrypt$4096$8$1${salt.hex()}${digest.hex()}"

        with SessionLocal() as session:
            stored = session.get(User, principal["user_id"])
            assert stored is not None
            stored.password_hash = legacy
            session.commit()
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/login", json={"email": "shortlegacy@example.test", "password": short}
        )
        assert response.status_code == 200, response.text
        assert self._rehash_events(principal["user_id"]) == 0


class TestProductionRefusesUnverifiedSmtp:
    """Production must not start with STARTTLS certificate checking off.

    A self-hosted relay that no public CA can vouch for is a trusted-network
    arrangement; in production the switch that turns verification off is
    exactly the one an interceptor needs, so startup refuses it.
    """

    def test_production_refuses_to_start_without_smtp_tls_verification(self) -> None:
        from typing import Any

        # The production base the metrics guard tests use: every other
        # production requirement already satisfied, so the only variable
        # under test is the TLS verification switch.
        base: dict[str, Any] = {
            "environment": "production",
            "auth_enabled": True,
            "cookie_secure": True,
            "database_url": "postgresql+psycopg://u:p@db/unimatch",
            "cors_origins": "https://apply.example.com",
            "email_sender": "smtp",
            "smtp_host": "smtp.example.com",
            "public_base_url": "https://apply.example.com",
            "metrics_enabled": True,
            "metrics_token": "a-long-enough-token",
        }
        with pytest.raises(RuntimeError, match="UNIMATCH_SMTP_TLS_VERIFY"):
            Settings(**base, smtp_tls_verify=False).validate_runtime()
        Settings(**base, smtp_tls_verify=True).validate_runtime()
