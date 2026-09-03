"""Authentication, tenant isolation, headers and abuse controls."""

from __future__ import annotations

import asyncio
import copy

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.corpus.demo_profile import DEMO_PROFILE


@pytest.fixture
def auth_client(tmp_path, monkeypatch, corpus_dir):
    settings = Settings(
        demo_mode=True,
        environment="development",
        auth_enabled=True,
        auth_registration_enabled=True,
        auth_rate_limit_per_minute=20,
        run_rate_limit_per_minute=20,
        # The deployed stack always sits behind nginx or Fly, so that is the
        # configuration worth testing.
        trust_proxy_headers=True,
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
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

    with TestClient(main_module.app) as client:
        yield client, settings
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


class TestAuthentication:
    def test_private_routes_require_a_session(self, auth_client):
        client, _ = auth_client
        response = client.get("/api/profiles")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required."

    def test_registration_uses_an_opaque_httponly_cookie(self, auth_client):
        client, _ = auth_client
        register(client, "alice")
        cookie = client.cookies.get("unimatch_session")
        assert cookie and "." not in cookie  # opaque, not a JWT carrying claims
        header = client.post("/api/auth/logout").headers.get("set-cookie", "").lower()
        assert "httponly" in header
        assert "samesite=strict" in header

    def test_passwords_are_not_stored_verbatim(self, auth_client):
        client, _ = auth_client
        principal = register(client, "hashcheck")
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            row = session.get(User, principal["user_id"])
            assert row is not None
            assert row.password_hash.startswith("scrypt$")
            assert "correct horse" not in row.password_hash


class TestTenantIsolation:
    def test_every_case_and_run_endpoint_hides_another_tenants_ids(self, auth_client):
        client, _ = auth_client
        alice = register(client, "tenant-a")
        profile_payload = copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
        created = client.post("/api/profiles", json=profile_payload)
        assert created.status_code == 201
        profile_id = created.json()["id"]
        run = client.post("/api/runs", json={"profile_id": profile_id, "demo_mode": True})
        assert run.status_code == 202
        run_id = run.json()["id"]

        assert client.post("/api/auth/logout").status_code == 204
        bob = register(client, "tenant-b")
        assert bob["organization_id"] != alice["organization_id"]

        probes = [
            ("GET", f"/api/profiles/{profile_id}"),
            ("PUT", f"/api/profiles/{profile_id}"),
            ("DELETE", f"/api/profiles/{profile_id}"),
            ("GET", f"/api/profiles/{profile_id}/export"),
            ("GET", f"/api/runs/{run_id}"),
            ("POST", f"/api/runs/{run_id}/cancel"),
            ("POST", f"/api/runs/{run_id}/retry"),
            ("POST", f"/api/runs/{run_id}/collect-documents"),
            ("GET", f"/api/runs/{run_id}/results"),
            ("GET", f"/api/runs/{run_id}/claims"),
            ("GET", f"/api/runs/{run_id}/conflicts"),
            ("GET", f"/api/runs/{run_id}/questions"),
            ("GET", f"/api/runs/{run_id}/export.json"),
        ]
        for method, path in probes:
            kwargs = {"json": profile_payload} if method == "PUT" else {}
            response = client.request(method, path, **kwargs)
            assert response.status_code == 404, (method, path, response.text)

        assert client.get("/api/profiles").json() == []
        assert client.get("/api/runs").json() == []
        assert client.get("/api/cases").json() == []
        assert client.get("/api/audit").json() == []

    def test_another_tenant_cannot_read_or_decide_a_result_row(self, auth_client):
        """A result id is the last thing that leaked.

        Every other route resolved the run through owned_run; the two result
        routes took the id at face value, so an authenticated stranger could
        approve or reject rows on someone else's shortlist.
        """
        from tests.test_api import drain_queue

        client, _ = auth_client
        register(client, "result-owner")
        profile = client.post(
            "/api/profiles", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
        ).json()
        run = client.post("/api/runs", json={"profile_id": profile["id"], "demo_mode": True}).json()
        assert asyncio.run(drain_queue()) == 1
        results = client.get(f"/api/runs/{run['id']}/results").json()
        assert results, "the demo run must produce rows for this test to mean anything"
        result_id = results[0]["id"]

        assert client.post("/api/auth/logout").status_code == 204
        register(client, "result-stranger")

        assert client.get(f"/api/runs/{run['id']}/results/{result_id}").status_code == 404
        decision = client.post(
            f"/api/runs/{run['id']}/results/{result_id}/decision",
            json={"decision": "rejected", "reason": "not mine to reject"},
        )
        assert decision.status_code == 404, decision.text

        # And the row is untouched: the owner still sees no decision on it.
        assert client.post("/api/auth/logout").status_code == 204
        client.post(
            "/api/auth/login",
            json={
                "email": "result-owner@example.test",
                "password": "correct horse battery result-owner",
            },
        )
        owner_view = client.get(f"/api/runs/{run['id']}/results/{result_id}").json()
        assert owner_view["user_decision"] == "undecided"


class TestAbuseLimits:
    """Limits must bind the abuser, not everyone behind the same proxy.

    In production uvicorn sits behind nginx or Fly's edge, so request.client
    is the proxy for every user. Keying the limiter on it turned a 10/min
    login limit into a global one: one script locked out the whole product.
    """

    def test_two_clients_behind_one_proxy_get_their_own_budget(self, auth_client):
        client, settings = auth_client
        register(client, "proxy-abuser")
        client.post("/api/auth/logout")
        register(client, "proxy-bystander")
        client.post("/api/auth/logout")

        for _ in range(settings.auth_rate_limit_per_minute):
            client.post(
                "/api/auth/login",
                json={"email": "proxy-abuser@example.test", "password": "wrong password here"},
                headers={"X-Forwarded-For": "203.0.113.7"},
            )
        exhausted = client.post(
            "/api/auth/login",
            json={"email": "proxy-abuser@example.test", "password": "wrong password here"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )
        assert exhausted.status_code == 429
        assert "Too many requests" in exhausted.json()["detail"], "the address limit must fire"

        # Another user, same proxy, different address: unaffected.
        bystander = client.post(
            "/api/auth/login",
            json={
                "email": "proxy-bystander@example.test",
                "password": "correct horse battery proxy-bystander",
            },
            headers={"X-Forwarded-For": "198.51.100.4"},
        )
        assert bystander.status_code == 200, "one abuser must not spend everyone else's budget"

    def test_an_email_cannot_be_pounded_from_a_fresh_address_each_time(self, auth_client):
        client, settings = auth_client
        register(client, "target")
        client.post("/api/auth/logout")

        attempts = [
            client.post(
                "/api/auth/login",
                json={"email": "target@example.test", "password": "wrong password entirely"},
                headers={"X-Forwarded-For": f"198.51.100.{i + 1}"},
            )
            for i in range(settings.auth_rate_limit_per_minute + 1)
        ]
        assert attempts[-1].status_code == 429, "per-email limit must survive IP rotation"

    def test_an_unknown_email_costs_the_same_work_as_a_known_one(self, auth_client, monkeypatch):
        """Skipping the hash for an unknown email leaks which emails exist."""
        client, _ = auth_client
        register(client, "known")
        client.post("/api/auth/logout")

        import app.api.routes_auth as routes_auth

        calls: list[str] = []
        real_verify = routes_auth.verify_password

        def counting_verify(password: str, encoded: str) -> bool:
            calls.append(encoded)
            return real_verify(password, encoded)

        monkeypatch.setattr(routes_auth, "verify_password", counting_verify)

        unknown = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.test", "password": "correct horse battery known"},
        )
        assert unknown.status_code == 401
        assert unknown.json()["detail"] == "Invalid email or password."
        assert len(calls) == 1, "a password check must run even when the account does not exist"


class TestRequestSecurity:
    def test_security_headers_are_on_success_and_error_responses(self, auth_client):
        client, _ = auth_client
        for response in (client.get("/api/health"), client.get("/api/profiles")):
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert "camera=()" in response.headers["permissions-policy"]

    def test_cross_site_mutation_is_refused(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/api/auth/login",
            headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"},
            json={"email": "nobody@example.test", "password": "not-the-password"},
        )
        assert response.status_code == 403
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_auth_rate_limit_returns_retry_after_and_security_headers(self, auth_client):
        client, settings = auth_client
        for _ in range(settings.auth_rate_limit_per_minute):
            assert (
                client.post(
                    "/api/auth/login",
                    json={"email": "nobody@example.test", "password": "not-the-password"},
                ).status_code
                == 401
            )
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.test", "password": "not-the-password"},
        )
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        assert response.headers["x-frame-options"] == "DENY"

    def test_openapi_marks_tenant_routes_as_cookie_secured(self, auth_client):
        client, _ = auth_client
        schema = client.get("/openapi.json").json()
        assert "APIKeyCookie" in schema["components"]["securitySchemes"]
        assert schema["paths"]["/api/profiles"]["get"]["security"]


def test_production_refuses_to_start_without_authentication(tmp_path):
    settings = Settings(
        environment="production",
        auth_enabled=False,
        database_url=f"sqlite:///{tmp_path / 'unsafe.db'}",
    )
    with pytest.raises(RuntimeError, match="AUTH_ENABLED"):
        settings.validate_runtime()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"database_url": "sqlite:////tmp/not-production.db"}, "PostgreSQL"),
        ({"cors_origins": "http://example.test"}, "HTTPS origins"),
        ({"cors_origins": "*"}, "HTTPS origins"),
    ],
)
def test_production_refuses_other_unsafe_defaults(overrides, message):
    values = {
        "environment": "production",
        "auth_enabled": True,
        "cookie_secure": True,
        "database_url": "postgresql+psycopg://user:pass@db/app",
        "cors_origins": "https://apply.example.test",
        **overrides,
    }
    with pytest.raises(RuntimeError, match=message):
        Settings(**values).validate_runtime()


class TestErrorsAndHeaders:
    def test_an_internal_value_error_is_a_500_without_its_text(self, auth_client, monkeypatch):
        """A global ValueError->400 handler masked bugs as client errors.

        It also handed the caller whatever the exception happened to say, which
        in this codebase includes internal currency and parsing detail.
        """
        from fastapi.testclient import TestClient

        import app.api.routes_profile as routes_profile
        import app.main as main_module

        client, _ = auth_client
        register(client, "error-paths")

        def explode(*_args, **_kwargs):
            raise ValueError("internal detail: rate table row 17 is malformed")

        monkeypatch.setattr(routes_profile, "validate_profile", explode)
        with TestClient(main_module.app, raise_server_exceptions=False) as raw:
            raw.cookies.update(client.cookies)
            response = raw.post(
                "/api/profiles/validate", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
            )

        assert response.status_code == 500
        assert "rate table row 17" not in response.text

    def test_a_bad_email_is_still_a_readable_400(self, auth_client):
        """Removing the handler must not turn a typo into a server error."""
        client, _ = auth_client
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "correct horse battery staple",
                "display_name": "Typo",
                "organization_name": "Typo",
            },
        )
        assert response.status_code == 400
        assert "valid email" in response.json()["detail"]

    def test_the_export_filename_cannot_be_injected(self, auth_client):
        from tests.test_api import drain_queue

        client, _ = auth_client
        register(client, "export-header")
        profile = client.post(
            "/api/profiles", json=copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
        ).json()
        run = client.post("/api/runs", json={"profile_id": profile["id"], "demo_mode": True}).json()
        assert asyncio.run(drain_queue()) == 1

        hostile = client.get(
            f"/api/runs/{run['id']}/export.csv",
            params={"decision": 'approved" ; x-injected="1'},
        )
        assert hostile.status_code == 400
        assert "Unknown decision filter" in hostile.json()["detail"]

        crlf = client.get(
            f"/api/runs/{run['id']}/export.csv", params={"decision": "approved\r\nX-Evil: 1"}
        )
        assert crlf.status_code == 400

        good = client.get(f"/api/runs/{run['id']}/export.csv", params={"decision": "approved"})
        assert good.status_code == 200
        disposition = good.headers["content-disposition"]
        assert disposition == 'attachment; filename="ashyq-{}-approved.csv"'.format(run["id"][:8])
