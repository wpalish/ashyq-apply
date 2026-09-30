"""Deterministic host identity using the bundled public and private suffix list.

The extractor never updates its list over the network or writes a user cache.
The same host rules must be used for discovery, redirects and claim provenance.
"""

from __future__ import annotations

import ipaddress

import httpx
import tldextract

_SUFFIXES = tldextract.TLDExtract(
    suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True
)
_RESERVED_TEST_SUFFIXES = frozenset({"example", "test", "invalid"})


def canonical_host(host_or_url: str) -> str:
    """Return the ASCII host that HTTPX would request, or fail closed."""
    raw = (host_or_url or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"
    elif "://" not in raw:
        raw = f"https://{raw}"
    try:
        return httpx.URL(raw).raw_host.decode("ascii").lower().rstrip(".")
    except (ValueError, UnicodeError):
        return ""


def registrable_domain(host_or_url: str) -> str:
    """Return the tenant-aware site key, including private PSL suffixes."""
    host = canonical_host(host_or_url)
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return host
    parts = _SUFFIXES(host)
    if parts.suffix:
        return parts.top_domain_under_public_suffix
    labels = host.split(".")
    if len(labels) > 1 and labels[-1] in _RESERVED_TEST_SUFFIXES:
        return ".".join(labels[-2:])
    # Unknown suffix: accepting siblings would grant a whole unregistered
    # namespace to a site. Exact-host matching remains possible.
    return host


def hosts_share_site(left: str, right: str) -> bool:
    """Compare parsed host identities, never path/query text."""
    first = canonical_host(left)
    last = canonical_host(right)
    if not first or not last:
        return False
    if first == last:
        return True
    try:
        first_ip = ipaddress.ip_address(first)
    except ValueError:
        first_ip = None
    try:
        last_ip = ipaddress.ip_address(last)
    except ValueError:
        last_ip = None
    if first_ip is not None or last_ip is not None:
        return first_ip is not None and first_ip == last_ip
    first_site = registrable_domain(first)
    last_site = registrable_domain(last)
    return bool(first_site and last_site) and first_site == last_site
