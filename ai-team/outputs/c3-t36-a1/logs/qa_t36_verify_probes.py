"""T36 VERIFY_CANDIDATE adversarial probes for client_address (function-level).

Run from the verification worktree backend/ with its venv. Builds synthetic
starlette Requests (no server, no network) and checks last-hop semantics on
pathological X-Forwarded-For values, plus the trust=False and no-client paths.
"""

from __future__ import annotations

import sys

from starlette.requests import Request

sys.path.insert(0, ".")
from app.main import client_address, settings  # noqa: E402

PEER = "203.0.113.7"
failures: list[str] = []


def probe(xff: str | None, trust: bool = True, peer: str | None = PEER) -> str:
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": b"",
        "client": (peer, 54321) if peer else None,
    }
    saved = settings.trust_proxy_headers
    settings.trust_proxy_headers = trust
    try:
        return client_address(Request(scope))
    finally:
        settings.trust_proxy_headers = saved


def expect(label: str, got: str, want: str) -> None:
    status = "PASS" if got == want else "FAIL"
    if got != want:
        failures.append(label)
    print(f"[{status}] {label}: got={got!r} want={want!r}")


# 1. Trailing commas / blank entries / extra spaces.
expect("trailing comma+blanks", probe("1.2.3.4, , 5.6.7.8,"), "5.6.7.8")
expect("only blanks and commas", probe(" , , "), PEER)
expect("spaces around hops", probe("  1.2.3.4 ,  9.8.7.6  "), "9.8.7.6")

# 2. nginx appends the real client: spoofed single hop + appended peer.
expect("spoof+appended real client", probe("9.9.9.9, " + PEER), PEER)
expect("multi-spoof+appended real", probe("1.1.1.1, 2.2.2.2, " + PEER), PEER)

# 3. IPv6 forms.
expect("ipv6 last hop", probe("1.2.3.4, 2001:db8::1"), "2001:db8::1")
expect("ipv6 alone", probe("::1"), "::1")
expect("ipv6 bracket-port form", probe("1.2.3.4, [2001:db8::2]:443"), "[2001:db8::2]:443")

# 4. trust=False: XFF ignored entirely, socket peer charged.
expect(
    "trust=false ignores XFF",
    probe("1.2.3.4, 5.6.7.8", trust=False),
    PEER,
)
expect(
    "trust=false ignores spoofed last hop",
    probe("5.6.7.8", trust=False),
    PEER,
)

# 5. Empty/absent XFF at trust=true.
expect("absent header", probe(None), PEER)
expect("empty header", probe(""), PEER)

# 6. No client in scope at all.
expect("no client, no xff", probe(None, peer=None), "unknown")
expect("no client, blank xff", probe("  ", peer=None), "unknown")

print()
if failures:
    print(f"ADVERSARIAL_PROBES: {len(failures)} FAILED -> {failures}")
    sys.exit(1)
print("ADVERSARIAL_PROBES: ALL PASS")
