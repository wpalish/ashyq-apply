"""PD-2: a numeric cache-buster is dropped before the PII guard sees a link (PDF map, ticket 06).

um's fee schedule PDF is linked as ``…/fee.pdf?_t=1761184801`` and ucph's
study regulation as ``…/x.pdf?177667006``. The ``Fetcher``'s PII guard reads
nine digits in a query as a possible passport or card number and refuses
both, every time. The guard is right to be blunt and is not touched here:
the link is canonicalised before it is requested, and only this shape is
dropped —

* a query parameter whose *name* is a known cache-buster (``_t``, ``t``,
  ``ts``, ``v``, ``ver``, ``version``, ``rev``, ``timestamp``, ``cache``,
  ``cb``, ``nocache``) and whose value is purely numeric, or
* a whole query that is one bare number,

on a link whose host is the institution's own registrable domain. A digit
run in the path, in any other parameter, or beside letters reaches the
guard unchanged and is still refused.

Malformed links (2026-10-19). Real pages link hosts that cannot be requested:
usp wrote a host ending in a zero-width space (``https://www.usp.br\\u200b/…``,
httpx raises ``InvalidURL``) and rwth wrote a phone number where a port goes
(``https://host:+49…``, ``urlsplit(...).port`` raises ``ValueError``).
:func:`page_link` is the one rule for a URL taken from page content: invisible
format characters (Unicode ``Cf``) are removed from the host, and an
``http(s)`` URL that still cannot be requested is dropped.
:func:`invalid_url_reason` is the same test for a URL about to be read.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.domain.claim_verifier import url_matches_domains

_WEB_SCHEMES = ("http", "https")


def _scheme(url: str) -> str:
    head, sep, _ = url.partition(":")
    return head.strip().lower() if sep else ""


def strip_invisible_host(url: str) -> str:
    """``url`` with invisible format characters (Unicode ``Cf``) removed from its authority.

    Zero-width space, joiner and non-joiner, BOM, soft hyphen and direction
    marks render as nothing, so a host that carries one is the host the page
    meant. Only the ``//authority`` part is touched; path and query keep theirs.
    """
    scheme_end = url.find("//")
    if scheme_end < 0:
        return url
    start = scheme_end + 2
    end = len(url)
    for stop in "/?#":
        found = url.find(stop, start)
        if found >= 0:
            end = min(end, found)
    authority = url[start:end]
    if all(unicodedata.category(c) != "Cf" for c in authority):
        return url
    cleaned = "".join(c for c in authority if unicodedata.category(c) != "Cf")
    return url[:start] + cleaned + url[end:]


def invalid_url_reason(url: str) -> str | None:
    """Why an ``http(s)`` URL cannot be requested as written, or ``None``.

    Other schemes (``mailto:``, ``tel:``, ``javascript:``, ``fixture://``)
    are not judged here: each caller has its own scheme rule.
    """
    if _scheme(url) not in _WEB_SCHEMES:
        return None
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 - raises ValueError for a non-numeric or out-of-range port
    except ValueError as exc:
        return f"unparseable URL: {exc}"
    host = parts.hostname or ""
    if not host:
        return "URL has no host"
    if any(c.isspace() or c == "%" or unicodedata.category(c)[0] == "C" for c in host):
        return "invalid host"
    try:
        httpx.URL(url)
    except (httpx.InvalidURL, ValueError, UnicodeError) as exc:
        return f"invalid URL: {exc}"
    return None


def page_link(base: str, href: str) -> str | None:
    """An absolute link from page content, or ``None`` when it cannot be requested.

    ``href`` is joined to ``base``, invisible characters are removed from the
    host, and an ``http(s)`` result that is still invalid (a phone number as a
    port, a port past 65535, a space in the host) is dropped. A link in another
    scheme comes back joined and unjudged, for the caller's own scheme rule.
    """
    try:
        url = strip_invisible_host(urljoin(base, href))
    except ValueError:
        return None
    if invalid_url_reason(url) is not None:
        return None
    return url


#: PD-2. Off: every link is requested exactly as it was found.
CACHE_BUSTER_CANONICAL = False

CACHE_BUSTER_NAMES = frozenset(
    {"_t", "t", "ts", "v", "ver", "version", "rev", "timestamp", "cache", "cb", "nocache"}
)


def strip_cache_busters(url: str) -> str:
    """``url`` without its numeric cache-buster parameters (no domain check)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    query = parts.query
    if not query:
        return url
    if query.isdigit():
        kept: list[str] = []
    else:
        kept = []
        for pair in query.split("&"):
            name, sep, value = pair.partition("=")
            if sep and name.lower() in CACHE_BUSTER_NAMES and value.isdigit():
                continue
            kept.append(pair)
        if len(kept) == len(query.split("&")):
            return url
    return urlunsplit(parts._replace(query="&".join(kept)))


def canonical_link(url: str, official_domains: Iterable[str]) -> str:
    """The link to request: cache-busters dropped on the institution's own domain."""
    if not CACHE_BUSTER_CANONICAL or not url_matches_domains(url, official_domains):
        return url
    return strip_cache_busters(url)
