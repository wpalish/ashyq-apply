"""A health endpoint is something other systems probe.

`HEAD /api/health` answered 405. The container healthcheck uses GET so nothing
was broken, but HEAD is what a good deal of uptime monitoring sends by default,
and an endpoint whose entire purpose is being probed should answer the probe.

Found by the smoke test dying on `curl -fsSI` — a HEAD request — with exit 22,
which until an ERR trap was added reported only "Process completed with exit
code 22".
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_health_answers_the_probe(client: TestClient, method: str):
    assert client.request(method, "/api/health").status_code == 200


def test_head_carries_the_same_security_headers_as_get(client: TestClient):
    """A monitor that only ever sends HEAD should still see the headers a
    browser would, or the check is measuring a different response."""
    head = client.request("HEAD", "/api/health").headers
    get = client.get("/api/health").headers
    for header in ("x-content-type-options", "x-frame-options", "referrer-policy"):
        assert head.get(header) == get.get(header), header


def test_head_returns_no_body(client: TestClient):
    """What makes it a HEAD."""
    assert client.request("HEAD", "/api/health").content == b""
