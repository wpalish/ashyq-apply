"""Find the search a university already offers its own visitors.

Three of the ten benchmark cases retrieved no candidates at all, and several of
those sites have a working programme search on their front page. Using it is
cheaper and more accurate than any external index: the site knows its own
catalogue.

This module only *detects*. It reads a page that has already been fetched and
reports which search surface it exposes, with provenance. Fetching the surface
stays with ``Fetcher``, so robots, rate limits, the PII guard and the SSRF
protections are untouched by anything here.

The phase guide's §7 rules are enforced rather than described:

* **Passive before active.** A surface observed in a browser network log
  outranks one inferred from markup, and nothing here probes an endpoint to
  see whether it exists. Guessing URLs against a university is exactly the
  behaviour a site owner would call scanning.
* **Only the site's own endpoints.** Anything on another registrable domain is
  discarded, using the same comparison discovery uses.
* **No credential is ever read.** Algolia and Elastic publish a search-only key
  in page JavaScript. This records that the surface needs one and stores
  nothing: a key in a repository is a key in a repository, whatever its scope.
* **Nothing authenticated or administrative**, however convenient it looks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.adapters.discovery.live_discovery import same_institution

#: Most bytes worth reading from a search response. A catalogue JSON that
#: exceeds this is a paginated feed being served whole, and reading it all is
#: how a discovery run turns into a download.
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

#: Most pages to walk from one surface. §7: bound pagination. Without a bound,
#: a catalogue with an off-by-one "next" link is an infinite crawl.
MAX_PAGES = 5


class SiteSearchKind(StrEnum):
    HTML_FORM = "html_form"
    JSON_ENDPOINT = "json_endpoint"
    WORDPRESS_REST = "wordpress_rest"
    DRUPAL_VIEWS = "drupal_views"
    ALGOLIA = "algolia"
    ELASTIC = "elastic"
    SOLR = "solr"
    GRAPHQL = "graphql"
    CUSTOM_CATALOGUE = "custom_catalogue"


class Provenance(StrEnum):
    """How the surface was found. Ordered: passive evidence is worth more."""

    #: Seen in a browser network log — the site itself called it.
    NETWORK_LOG = "network_log"
    #: Declared in the markup: a form action, a link rel, a script src.
    MARKUP = "markup"


#: Surfaces whose request needs a key published in page JavaScript. Detected
#: and reported; the key is never read, stored or logged.
NEEDS_CREDENTIALS = frozenset({SiteSearchKind.ALGOLIA, SiteSearchKind.ELASTIC})

#: Paths that are somebody's account or admin area, not a public search.
_PRIVATE_PATH = re.compile(
    r"/(wp-admin|admin|administrator|login|signin|sso|auth|oauth|account|user/\d+"
    r"|dashboard|manage|internal|private)(/|$)",
    re.IGNORECASE,
)

_ENDPOINT_PATTERNS: tuple[tuple[re.Pattern[str], SiteSearchKind], ...] = (
    (re.compile(r"/wp-json/wp/v2/", re.IGNORECASE), SiteSearchKind.WORDPRESS_REST),
    (re.compile(r"/jsonapi/|/views/ajax|/api/views/", re.IGNORECASE), SiteSearchKind.DRUPAL_VIEWS),
    (re.compile(r"\.algolia(net|\.net|\.com)|/1/indexes/", re.IGNORECASE), SiteSearchKind.ALGOLIA),
    (re.compile(r"/_search(\?|$)|/_msearch", re.IGNORECASE), SiteSearchKind.ELASTIC),
    (re.compile(r"/solr/|/select\?.*\bwt=", re.IGNORECASE), SiteSearchKind.SOLR),
    (re.compile(r"/graphql(\?|/|$)", re.IGNORECASE), SiteSearchKind.GRAPHQL),
    (
        re.compile(r"/(programmes?|programs?|courses?|studies)[^?]*\.json", re.IGNORECASE),
        SiteSearchKind.CUSTOM_CATALOGUE,
    ),
    (
        re.compile(r"/api/.*\b(search|programmes?|programs?|courses?)\b", re.IGNORECASE),
        SiteSearchKind.JSON_ENDPOINT,
    ),
)

#: The query parameter a surface takes, by kind. Where a form declares its own,
#: the form wins — this is only the fallback.
_DEFAULT_QUERY_PARAM = {
    SiteSearchKind.WORDPRESS_REST: "search",
    SiteSearchKind.DRUPAL_VIEWS: "search",
    SiteSearchKind.ALGOLIA: "query",
    SiteSearchKind.ELASTIC: "q",
    SiteSearchKind.SOLR: "q",
    SiteSearchKind.GRAPHQL: "query",
    SiteSearchKind.JSON_ENDPOINT: "q",
    SiteSearchKind.CUSTOM_CATALOGUE: "q",
    SiteSearchKind.HTML_FORM: "q",
}

_FORM = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""(\w[\w:-]*)\s*=\s*["']([^"']*)["']""")
_SEARCH_INPUT = re.compile(r"""<input\b[^>]*\bname\s*=\s*["']([^"']+)["'][^>]*>""", re.IGNORECASE)
_SCRIPT_URL = re.compile(r"""["'](https?://[^"'\s]+|/[^"'\s]+)["']""")


@dataclass(frozen=True, slots=True)
class SiteSearchSurface:
    """A public search the site offers, and how we came to know about it."""

    kind: SiteSearchKind
    endpoint: str
    query_param: str
    provenance: Provenance
    detected_at: datetime
    #: A short quote of what gave it away. Provenance a reviewer can check.
    evidence: str = ""

    @property
    def requires_credentials(self) -> bool:
        """Whether a request needs a key this module deliberately does not read."""
        return self.kind in NEEDS_CREDENTIALS

    @property
    def usable_without_owner_review(self) -> bool:
        """A surface we may call as an ordinary visitor would, with no key."""
        return not self.requires_credentials


def _is_public(url: str, domain: str) -> bool:
    if _PRIVATE_PATH.search(urlsplit(url).path or ""):
        return False
    return same_institution(url, domain)


def _classify(url: str) -> SiteSearchKind | None:
    for pattern, kind in _ENDPOINT_PATTERNS:
        if pattern.search(url):
            return kind
    return None


def _form_surfaces(html: str, base_url: str, domain: str, now: datetime) -> list[SiteSearchSurface]:
    surfaces: list[SiteSearchSurface] = []
    for match in _FORM.finditer(html):
        tag = match.group(0)
        attrs = {k.lower(): v for k, v in _ATTR.findall(tag)}
        action = attrs.get("action", "")
        if not action:
            continue
        url = urljoin(base_url, action)
        if not _is_public(url, domain):
            continue

        tail = html[match.end() : match.end() + 2000]
        names = _SEARCH_INPUT.findall(tail)
        param = next(
            (n for n in names if n.lower() in ("q", "query", "s", "search", "keywords", "term")),
            None,
        )
        if param is None and "search" not in (action + tag).lower():
            # A form with no recognisable search field and no search-looking
            # action is a newsletter signup or a language switcher.
            continue

        kind = _classify(url) or SiteSearchKind.HTML_FORM
        surfaces.append(
            SiteSearchSurface(
                kind=kind,
                endpoint=url,
                query_param=param or _DEFAULT_QUERY_PARAM[kind],
                provenance=Provenance.MARKUP,
                detected_at=now,
                evidence=tag[:200],
            )
        )
    return surfaces


def detect_surfaces(
    html: str,
    base_url: str,
    *,
    network_urls: tuple[str, ...] = (),
    now: datetime | None = None,
) -> tuple[SiteSearchSurface, ...]:
    """Every public search surface this page reveals, passive evidence first.

    ``network_urls`` are requests the site's own pages made, as a browser
    network log recorded them. They are the better evidence — the site called
    them, so they exist and are meant to be called — and they are reported
    before anything inferred from markup.
    """
    now = now or datetime.now(UTC)
    domain = urlsplit(base_url).hostname or base_url

    surfaces: list[SiteSearchSurface] = []
    for url in network_urls:
        if not _is_public(url, domain):
            continue
        kind = _classify(url)
        if kind is None:
            continue
        observed = dict(parse_qsl(urlsplit(url).query))
        param = next(
            (k for k in observed if k.lower() in ("q", "query", "s", "search", "keywords")),
            _DEFAULT_QUERY_PARAM[kind],
        )
        surfaces.append(
            SiteSearchSurface(
                kind=kind,
                endpoint=url,
                query_param=param,
                provenance=Provenance.NETWORK_LOG,
                detected_at=now,
                evidence="observed in the site's own network activity",
            )
        )

    surfaces += _form_surfaces(html, base_url, domain, now)

    for match in _SCRIPT_URL.finditer(html):
        url = urljoin(base_url, match.group(1))
        kind = _classify(url)
        if kind is None or not _is_public(url, domain):
            continue
        surfaces.append(
            SiteSearchSurface(
                kind=kind,
                endpoint=url,
                query_param=_DEFAULT_QUERY_PARAM[kind],
                provenance=Provenance.MARKUP,
                detected_at=now,
                evidence=match.group(0)[:200],
            )
        )

    # One endpoint, reported once, keeping the strongest provenance. Network
    # evidence was appended first, so the first occurrence is the best one.
    seen: set[str] = set()
    unique = []
    for surface in surfaces:
        if surface.endpoint in seen:
            continue
        seen.add(surface.endpoint)
        unique.append(surface)
    return tuple(unique)


def search_url(surface: SiteSearchSurface, query: str, *, page: int = 1) -> str:
    """The URL to request this surface with, with pagination bounded.

    Existing query parameters on the endpoint are kept — a catalogue endpoint
    often carries the filter that makes it a catalogue — and the search term
    replaces only its own parameter.
    """
    if not query.strip():
        raise ValueError("A site search needs a query")
    if not 1 <= page <= MAX_PAGES:
        raise ValueError(
            f"page must be between 1 and {MAX_PAGES} (§7 bounds pagination), got {page}"
        )

    parts = urlsplit(surface.endpoint)
    params = [(k, v) for k, v in parse_qsl(parts.query) if k != surface.query_param]
    params.append((surface.query_param, query))
    if page > 1:
        params.append(("page", str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ""))
