"""Where the crawler is allowed to connect.

The crawler follows URLs found on third-party pages, so every one of them is
attacker-influenced. Without this module it reached ``127.0.0.1``, ``localhost``
and ``192.168.1.1``; the cloud metadata endpoint was "blocked" only because it
happened to time out, which on a cloud host it would not.

The policy is deny-by-default and applies identically to the HTTP tier, the
robots.txt fetch and the Playwright tier.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

log = logging.getLogger("unimatch.netpolicy")

ALLOWED_SCHEMES = frozenset({"http", "https"})
#: Anything else is almost certainly an attempt to reach an internal service.
ALLOWED_PORTS = frozenset({80, 443, 8080, 8443})

#: Ranges `ipaddress` does not already classify, or classifies too loosely.
_EXTRA_BLOCKED = (
    ipaddress.ip_network("169.254.0.0/16"),  # link-local, incl. cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),  # carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
    ipaddress.ip_network("fd00::/8"),  # unique local addresses
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),  # NAT64
    ipaddress.ip_network("2002::/16"),  # 6to4
)

#: Hostnames that resolve to the host itself on most systems, blocked by name
#: as well as by address so a resolver quirk cannot slip one past.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata",
        "metadata.google.internal",
        "instance-data",
    }
)

MAX_REDIRECTS = 5


class BlockedRequest(ValueError):
    """The policy refuses this URL. The message says which rule and why."""


@dataclass(frozen=True)
class ResolvedTarget:
    url: str
    scheme: str
    host: str
    port: int
    #: Every address the host resolved to. All of them are validated: a name
    #: answering with one public and one private address must not be allowed.
    addresses: tuple[str, ...]

    @property
    def pinned_address(self) -> str:
        return self.addresses[0]


def is_blocked_address(address: str) -> tuple[bool, str]:
    """Whether an IP is somewhere the crawler must never reach."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True, f"{address!r} is not a valid IP address"

    # An IPv4 address wrapped in IPv6 is still that IPv4 address.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    for attribute, reason in (
        ("is_loopback", "loopback"),
        ("is_private", "a private network"),
        ("is_link_local", "link-local"),
        ("is_multicast", "multicast"),
        ("is_reserved", "reserved"),
        ("is_unspecified", "the unspecified address"),
    ):
        if getattr(ip, attribute, False):
            return True, f"{ip} is {reason}"

    for network in _EXTRA_BLOCKED:
        if ip.version == network.version and ip in network:
            return True, f"{ip} is inside the blocked range {network}"

    return False, ""


def resolve_target(url: str, *, resolver=None) -> ResolvedTarget:
    """Validate a URL and resolve it, or raise BlockedRequest.

    Resolution happens here, before any connection, and *every* address the
    name returns is checked. Validating only the first would let a name
    answering with one public and one private address through.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise BlockedRequest(
            f"Refusing {parsed.scheme or 'schemeless'} URL: only http and https are allowed."
        )
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise BlockedRequest(f"Refusing {url!r}: no host.")
    if parsed.username is not None or parsed.password is not None:
        raise BlockedRequest("Refusing URL credentials: crawler requests never authenticate.")
    if host in _BLOCKED_HOSTNAMES:
        raise BlockedRequest(f"Refusing {host!r}: it names the local host.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise BlockedRequest(f"Refusing port {port}: only {sorted(ALLOWED_PORTS)} are allowed.")

    # A literal address needs no lookup, but still needs checking.
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        addresses = _resolve(host, port, resolver)

    for address in addresses:
        blocked, reason = is_blocked_address(address)
        if blocked:
            raise BlockedRequest(f"Refusing {host!r}: it resolves to {reason}.")

    return ResolvedTarget(url, parsed.scheme, host, port, tuple(addresses))


def _resolve(host: str, port: int, resolver=None) -> list[str]:
    lookup = resolver or socket.getaddrinfo
    try:
        infos = lookup(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise BlockedRequest(f"Refusing {host!r}: it does not resolve ({exc}).") from exc
    addresses = [info[4][0] for info in infos]
    if not addresses:
        raise BlockedRequest(f"Refusing {host!r}: it resolves to nothing.")
    return addresses


def check_url(url: str, *, resolver=None) -> ResolvedTarget:
    """Public entry point. Raises BlockedRequest, or returns the target."""
    target = resolve_target(url, resolver=resolver)
    log.debug("allowing %s -> %s", url[:120], target.addresses)
    return target


def is_allowed(url: str, *, resolver=None) -> tuple[bool, str]:
    """Non-raising form, for callers that report rather than abort."""
    try:
        check_url(url, resolver=resolver)
    except BlockedRequest as exc:
        return False, str(exc)
    return True, ""
