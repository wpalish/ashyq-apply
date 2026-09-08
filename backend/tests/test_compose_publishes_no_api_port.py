"""The compose stack must not publish the API port to the host (S6).

The stack runs with UNIMATCH_TRUST_PROXY_HEADERS=true, so abuse limits
charge the X-Forwarded-For hop — a header only nginx (the `web` service)
is supposed to set. A host-published 8099 hands every direct client that
power: it invents a fresh address per request and each per-address limit
resets on every call. The API must therefore only *expose* 8099 on the
compose network and let web proxy to it.

The inspection is static on purpose: parsing the committed compose state is
the contract, and no docker daemon is needed (or allowed) for that.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # runtime dep, stubs not vendored

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_compose.sh"
API_PORT = "8099"
#: Host addresses that other machines cannot reach.
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _compose_api() -> dict:
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    return compose["services"]["api"]


def _publishes_api_port_publicly(entry: object) -> bool:
    """True if one `ports` entry publishes 8099 beyond the loopback interface.

    A missing host address means every interface, which is exactly the
    exposure the stack must not have while it trusts proxy headers.
    """
    if isinstance(entry, dict):
        target = str(entry.get("target", "")).removesuffix("/tcp")
        if target != API_PORT:
            return False
        published = entry.get("published")
        if not published:
            return False  # expose-style dict or an explicit published: false
        host = entry.get("host_ip")
        return host is None or str(host).strip("[]").lower() not in _LOOPBACK
    # String form. Shell-style defaults carry a colon ("${API_PORT:-8099}"),
    # so substitute them away before splitting.
    text = re.sub(r"\$\{[^}]*\}", "substituted", str(entry).strip())
    parts = text.split(":")
    if len(parts) < 2:
        return False  # a bare container port publishes nothing
    container = parts[-1].removesuffix("/tcp")
    if container != API_PORT:
        return False
    if len(parts) == 2:
        return True  # host port only: bound on every interface
    host = parts[0].strip("[]").lower()
    return host not in _LOOPBACK


def test_the_api_service_does_not_publish_its_port_to_the_host():
    api = _compose_api()
    published_publicly = [
        entry for entry in (api.get("ports") or []) if _publishes_api_port_publicly(entry)
    ]
    assert not published_publicly, (
        "the api service publishes 8099 to a host interface while the stack "
        "sets UNIMATCH_TRUST_PROXY_HEADERS=true: a direct client spoofs "
        "X-Forwarded-For and every per-address abuse limit resets per request; "
        f"offending entries: {published_publicly}"
    )


def test_the_api_port_stays_reachable_on_the_compose_network():
    exposed = {str(port).removesuffix("/tcp") for port in (_compose_api().get("expose") or [])}
    assert API_PORT in exposed, (
        "web (nginx) still needs 8099 on the compose network; keep it reachable "
        "with expose instead of a published ports mapping"
    )


def test_verify_compose_script_is_present_for_release_gating():
    assert VERIFY_SCRIPT.is_file(), (
        "verify_compose.sh is the release gate the publication check belongs in"
    )
