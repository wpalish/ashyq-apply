"""Every tenant-scoped route, checked against a second tenant.

`test_security.py` probes a hand-written list, which is only as good as
whoever remembered to extend it. This module derives the route set from the
application's own OpenAPI schema, so a route added next year either gets a
cross-tenant probe or fails this suite.
"""

from __future__ import annotations

import copy

import pytest

from app.corpus.demo_profile import DEMO_PROFILE
from tests.test_security import auth_client, register  # noqa: F401  (fixture import)

#: Every route carrying a resource identifier, with the body it needs and the
#: statuses that count as "refused". 404 is the expected answer: a 403 would
#: confirm that the identifier exists.
PROBES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/api/profiles/{profile_id}", ""),
    ("PUT", "/api/profiles/{profile_id}", "profile"),
    ("DELETE", "/api/profiles/{profile_id}", ""),
    ("GET", "/api/profiles/{profile_id}/export", ""),
    ("GET", "/api/profiles/{profile_id}/validation", ""),
    ("GET", "/api/runs/{run_id}", ""),
    ("POST", "/api/runs/{run_id}/cancel", ""),
    ("POST", "/api/runs/{run_id}/retry", ""),
    ("POST", "/api/runs/{run_id}/collect-documents", ""),
    ("GET", "/api/runs/{run_id}/results", ""),
    ("GET", "/api/runs/{run_id}/results/{result_id}", ""),
    ("POST", "/api/runs/{run_id}/results/{result_id}/decision", "decision"),
    ("GET", "/api/runs/{run_id}/summary", ""),
    ("GET", "/api/runs/{run_id}/claims", ""),
    ("GET", "/api/runs/{run_id}/conflicts", ""),
    ("GET", "/api/runs/{run_id}/questions", ""),
    ("GET", "/api/runs/{run_id}/export.{fmt}", ""),
)

REFUSED = {401, 403, 404, 422}


def parameterised_routes() -> set[tuple[str, str]]:
    from app.main import app

    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() not in ("HEAD", "OPTIONS") and "{" in path
    }


@pytest.fixture
def two_tenants(auth_client):  # noqa: F811
    """Alice owns a profile, a run and a result. Bob owns nothing."""
    client, _ = auth_client
    alice = register(client, "iso-a")
    payload = copy.deepcopy(DEMO_PROFILE.model_dump(mode="json"))
    created = client.post("/api/profiles", json=payload)
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]
    run = client.post("/api/runs", json={"profile_id": profile_id, "demo_mode": True})
    assert run.status_code == 202, run.text
    run_id = run.json()["id"]

    # Use a real result id when the demo run produced one, so the result-level
    # routes are probed against something that exists rather than a fiction.
    from app.db import SessionLocal
    from app.models import ProgramResultRow

    with SessionLocal() as session:
        row = (
            session.query(ProgramResultRow)
            .filter(ProgramResultRow.run_id == run_id)
            .first()
        )
        result_id = row.id if row is not None else "0" * 32

    assert client.post("/api/auth/logout").status_code == 204
    bob = register(client, "iso-b")
    assert bob["organization_id"] != alice["organization_id"]
    return client, payload, {
        "profile_id": profile_id, "run_id": run_id,
        "result_id": result_id, "fmt": "json",
    }


class TestTheProbeSetMatchesTheApplication:
    def test_no_parameterised_route_is_left_unprobed(self):
        """The test that survives the next feature.

        A new endpoint carrying a resource id has to be given a cross-tenant
        probe here, or this fails with its name.
        """
        missing = parameterised_routes() - {(m, p) for m, p, _ in PROBES}
        assert not missing, (
            "these routes carry a resource id and no cross-tenant probe:\n  "
            + "\n  ".join(f"{m} {p}" for m, p in sorted(missing))
        )

    def test_no_probe_points_at_a_route_that_no_longer_exists(self):
        stale = {(m, p) for m, p, _ in PROBES} - parameterised_routes()
        assert not stale, (
            "these probes no longer match a route:\n  "
            + "\n  ".join(f"{m} {p}" for m, p in sorted(stale))
        )


class TestCrossTenantAccessIsRefused:
    def test_no_route_leaks_another_tenants_resource(self, two_tenants):
        client, payload, ids = two_tenants
        bodies = {
            "profile": payload,
            "decision": {"decision": "approved", "reason": "probe"},
            "": None,
        }
        failures = []
        for method, template, body_kind in PROBES:
            path = template.format(**ids)
            body = bodies[body_kind]
            response = client.request(
                method, path, **({"json": body} if body is not None else {})
            )
            if response.status_code not in REFUSED:
                failures.append(f"{method} {path} -> {response.status_code} {response.text[:80]}")
        assert not failures, (
            "cross-tenant access was not refused:\n  " + "\n  ".join(failures)
        )

    def test_a_refusal_does_not_reveal_that_the_identifier_exists(self, two_tenants):
        """404, never 403: a 403 confirms the identifier is real."""
        client, _, ids = two_tenants
        real = client.get(f"/api/profiles/{ids['profile_id']}")
        invented = client.get("/api/profiles/" + "0" * 32)
        assert real.status_code == invented.status_code == 404
        assert real.json() == invented.json()

    def test_listing_endpoints_show_nothing_of_the_other_tenant(self, two_tenants):
        client, _, _ = two_tenants
        for path in ("/api/profiles", "/api/runs", "/api/cases", "/api/audit"):
            assert client.get(path).json() == [], path


class TestSessionLifetime:
    def test_a_logged_out_session_cannot_be_replayed(self, auth_client):  # noqa: F811
        client, _ = auth_client
        register(client, "replay")
        cookie = client.cookies.get("unimatch_session")
        assert cookie
        client.post("/api/auth/logout")
        client.cookies.set("unimatch_session", cookie)
        assert client.get("/api/profiles").status_code == 401

    def test_a_deleted_users_session_stops_working(self, auth_client):  # noqa: F811
        client, _ = auth_client
        principal = register(client, "deleted-user")
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            session.delete(session.get(User, principal["user_id"]))
            session.commit()
        assert client.get("/api/profiles").status_code == 401

    def test_an_invented_session_token_is_rejected(self, auth_client):  # noqa: F811
        client, _ = auth_client
        client.cookies.set("unimatch_session", "a" * 64)
        assert client.get("/api/profiles").status_code == 401
