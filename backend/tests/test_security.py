"""Authentication, tenant isolation, headers and abuse controls."""

from __future__ import annotations

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
            assert client.post(
                "/api/auth/login",
                json={"email": "nobody@example.test", "password": "not-the-password"},
            ).status_code == 401
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


class TestProductionOnlyHeaders:
    """HSTS is set only in production over HTTPS, and nothing tested that.

    Sending `Strict-Transport-Security` over plain HTTP in development would be
    wrong, so its absence there is correct — which means the header that
    actually matters had no cover at all.

    `_secure` is exercised directly rather than through a booted production
    app: production configuration refuses to start without PostgreSQL, which is
    its own correct fail-closed guard and not the subject here.
    """

    @staticmethod
    def headers_for(**overrides):
        from fastapi import Response

        import app.main as main_module
        from app.config import Settings

        base = {
            "environment": "production",
            "cookie_secure": True,
            "demo_mode": False,
            "auth_enabled": True,
            "database_url": "postgresql+psycopg://u:p@db:5432/x",
        }
        base.update(overrides)
        original = main_module.settings
        main_module.settings = Settings(**base)
        try:
            return dict(main_module._secure(Response()).headers)
        finally:
            main_module.settings = original

    def test_hsts_is_sent_in_production_over_https(self):
        value = self.headers_for().get("strict-transport-security")
        assert value, "no HSTS header in production"
        assert "max-age=" in value
        assert int(value.split("max-age=")[1].split(";")[0]) >= 31536000
        assert "includeSubDomains" in value

    def test_hsts_is_not_sent_in_development(self):
        """Announcing HTTPS-only over plain localhost HTTP would be wrong."""
        assert "strict-transport-security" not in self.headers_for(
            environment="development", cookie_secure=False,
            database_url="sqlite:///./x.sqlite3",
        )

    def test_hsts_is_not_sent_when_cookies_are_not_secure(self):
        """Announcing HTTPS-only while issuing insecure cookies is incoherent."""
        assert "strict-transport-security" not in self.headers_for(cookie_secure=False)

    def test_the_other_headers_are_present_in_production_too(self):
        headers = self.headers_for()
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert "content-security-policy" in headers
        assert "referrer-policy" in headers
        assert headers["cross-origin-opener-policy"] == "same-origin"
