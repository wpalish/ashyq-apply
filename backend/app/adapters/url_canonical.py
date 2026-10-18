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
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit

from app.domain.claim_verifier import url_matches_domains

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
