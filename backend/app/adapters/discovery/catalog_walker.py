"""The catalogue walker: reading a programme catalogue the way an applicant does.

The earlier stages read sitemaps and menus. A university's programme catalogue
is a better source than either — it is the page the university builds precisely
to list its programmes — but the navigation fallback only reaches a few links
on it, and a catalogue rendered by JavaScript has no links in its HTTP body at
all. The walker reads the whole catalogue: every link scored against the
applicant's level and subject, and — through :class:`CatalogRenderer` — the
JSON programme list a JS shell fetches from the university's own API.

This module is discovery logic, not infrastructure: no database, no models, no
playwright import of its own (the renderer inherits the browser tier's lazy
one). One walk is bounded the way the rest of discovery is bounded: at most
:data:`WALKER_MAX_CATALOGS` catalogues, the top :data:`WALKER_TOP_N` scored
links of each fetched, every skipped link explained with a frozen outcome so a
run report can say why a programme was not found.

The frozen walker outcome vocabulary (T29 contract): the fetch layer reports
with ``FetchOutcome.value`` verbatim; the walker layer uses ``program_detail``,
``intake_specific_program``, ``not_program_catalog``, ``reads_as_<page_type>``,
``degree_level_mismatch``, ``field_mismatch``, ``off_domain``, ``short_label``,
``excluded_url``, ``walker_budget_exhausted`` and ``js_no_program_list``.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.browser import BrowserFetcher
from app.adapters.discovery.live_discovery import (
    _DEGREE_SLUGS,
    _URL_EXCLUSIONS,
    MAX_LINKS_SCANNED,
    canonical_url,
    matches_degree,
    matches_field,
    matches_field_text,
    names_other_degree_level,
    profile_rejects,
    registrable_domain,
    same_institution,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.offload import off_loop
from app.adapters.page_classifier import (
    PageClassification,
    PageType,
    classify_page,
)

log = logging.getLogger("unimatch.discovery.walker")

#: Catalogue leads actually fetched and read per catalogue. The pipeline reads
#: these pages again anyway and the fetcher caches, so a spent slot is rarely
#: wasted work — but an unbounded walk of a large catalogue would be a crawl.
WALKER_TOP_N = 20

#: Catalogues walked per institution, in discovery's own order of preference.
WALKER_MAX_CATALOGS = 2

#: A label shorter than this cannot say which programme it leads to. "Ask us"
#: and "Learn more" are furniture, not leads.
MIN_LABEL_CHARS = 10

#: A catalogue section that lists this many sibling links under one path is a
#: repeating list — the page's own structure says these are entries of a list.
REPEATING_LIST_MIN_SIBLINGS = 5

#: Bonus weights (the T29 contract's frozen +5/+4/+8/+2 shape).
DEGREE_MARKER_BONUS = 5
SUBJECT_DEGREE_BONUS = 4
FIELD_TEXT_BONUS = 8  # the weight that has to dominate structural agreement
REPEATING_LIST_BONUS = 2

#: Trace caps: the walker reports what it did, never an unbounded log of it.
TRACE_CANDIDATE_CAP = 200
TRACE_OUTCOME_CAP = 200

#: Bounds for reading one JSON catalogue payload.
MAX_JSON_DEPTH = 4
MAX_JSON_ENTRIES = 200

#: Catalogue page classes that prove the page was never a catalogue. Ambiguous
#: answers (UNKNOWN, NAVIGATION) are not proof of anything and stay silent.
_NOT_CATALOGUE_TYPES = frozenset(
    {
        PageType.NEWS,
        PageType.IRRELEVANT,
        PageType.GENERAL_ADMISSIONS,
        PageType.COUNTRY_CREDENTIAL_REQUIREMENTS,
        PageType.SCHOLARSHIP_INDEX,
        PageType.SCHOLARSHIP_AWARD,
        PageType.SCHOLARSHIP_FAQ,
        PageType.COSTS,
        PageType.DOCUMENTS,
    }
)

#: A label that names a degree level — "BSc Computer Science", "Master of
#: Data". The university's own wording says this link is one of its programmes.
SUBJECT_DEGREE = re.compile(
    r"\b(bachelors?|masters?|phd|doctoral|doctorate|b\.?sc|m\.?sc|beng|meng|llb|llm|mba"
    r"|undergraduate|postgraduate|foundation)\b",
    re.IGNORECASE,
)


#: Regex tuples per degree level (bachelor/master/phd/foundation), built from
#: discovery's own slug table. One vocabulary, two uses: live_discovery matches
#: these slugs to reject a wrong-level URL outright; the walker also pays +5
#: for a URL naming a level at all. Built here so the two stay in lockstep.
DEGREE_MARKERS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"(^|[/-])({'|'.join(slugs)})([/-]|$)", re.IGNORECASE), level)
    for level, slugs in _DEGREE_SLUGS.items()
)


@dataclass(frozen=True)
class WalkerLink:
    """One catalogue lead: where it goes, what the page called it, how strong."""

    url: str  # canonical
    label: str
    score: int
    #: "html" (an anchor on the catalogue page) or "json" (an entry of the
    #: page's own JSON programme list).
    source: str


@dataclass
class CatalogWalk:
    """What walking one catalogue page produced."""

    catalogue_url: str
    #: Every scored candidate considered, strongest first (already budget-cut
    #: against nothing — the full list, for the trace).
    candidates: list[WalkerLink] = field(default_factory=list)
    #: Pages read and confirmed as programme pages for this applicant.
    confirmed: list[str] = field(default_factory=list)
    #: (url, frozen outcome) for every link the walk decided something about.
    outcomes: list[tuple[str, str]] = field(default_factory=list)


def _structural_score(url: str, label: str) -> int:
    """A link's strength before the applicant's profile is applied."""
    score = 0
    path = urlparse(url).path or ""
    for pattern, _level in DEGREE_MARKERS:
        if pattern.search(path):
            score += DEGREE_MARKER_BONUS
            break
    if SUBJECT_DEGREE.search(label):
        score += SUBJECT_DEGREE_BONUS
    return score


def extract_links(
    html: str,
    base_url: str,
    domain: str,
    drops: list[tuple[str, str]] | None = None,
) -> list[WalkerLink]:
    """The catalogue's same-domain links, resolved and deduplicated.

    Same semantics as live_discovery's ``_harvest_links`` — same scan bound,
    same scheme and domain gates, same canonicalisation, same label cleanup —
    plus two things the navigation fallback never needed: the link's own text
    is kept with a structural score, and the URLs refused for being off the
    institution's domain are reported through ``drops`` (as ``(url, reason)``
    pairs) so the walk can explain them instead of silently losing them.
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[WalkerLink] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        url = urljoin(base_url, anchor["href"]).split("#")[0]
        if urlparse(url).scheme not in ("http", "https"):
            continue
        if not same_institution(url, domain):
            if drops is not None:
                drops.append((canonical_url(url), "off_domain"))
            continue
        canonical = canonical_url(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:160]
        out.append(
            WalkerLink(
                url=canonical,
                label=label,
                score=_structural_score(canonical, label),
                source="html",
            )
        )
    return out


def parse_catalog_json(body: str, base_url: str = "") -> list[tuple[str, str]]:
    """``(name, url)`` entries of a JSON catalogue payload. Never raises.

    A JS catalogue fetches its programme list from the university's own API —
    usually an array of ``{name, url}`` objects (``title`` accepted for the
    name), sometimes nested a level or two below the top. Anything else —
    analytics, menu flags, broken JSON — yields ``[]`` and the catalogue's
    HTML links drive the walk instead. Depth and entry count are bounded; a
    body that cannot be read is not a failure of the walk.
    """
    try:
        data = json.loads(body)
    except (RecursionError, TypeError, ValueError):
        return []
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(node: object, depth: int) -> None:
        if depth > MAX_JSON_DEPTH or len(entries) >= MAX_JSON_ENTRIES:
            return
        if isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
            return
        if isinstance(node, dict):
            raw_url = node.get("url")
            name = node.get("name") or node.get("title")
            if (
                isinstance(raw_url, str)
                and raw_url.strip()
                and isinstance(name, str)
                and name.strip()
            ):
                url = urljoin(base_url, raw_url.strip()) if base_url else raw_url.strip()
                resolved = canonical_url(url)
                if resolved not in seen and urlparse(resolved).scheme in ("http", "https"):
                    seen.add(resolved)
                    label = re.sub(r"\s+", " ", name.strip())[:160]
                    entries.append((label, resolved))
            for value in node.values():
                visit(value, depth + 1)

    if isinstance(data, list | dict):
        visit(data, 1)
    return entries


def score_link(url: str, label: str, degree: str, fields: list[str]) -> int | None:
    """How strongly one catalogue link could be the applicant's programme.

    ``None`` is a hard reject — the link is never worth a fetch: its URL is on
    the exclusion list, its label is too short to name anything, or the URL
    names a degree level the applicant did not ask for (an MSc link is not a
    weak bachelor lead, it is the wrong page). Otherwise the score adds

    * +5 for a URL that names a degree level at all,
    * +4 for a label that names one (the university calling it a programme),
    * +8 for a label in the applicant's own words for their subject — this
      dominates, exactly as it does in the confirm stage,
    * the URL-level subject and level bonuses discovery already uses.

    The repeating-list bonus is deliberately *not* applied here: sibling
    structure is a property of the catalogue, not of one link, and belongs to
    :meth:`CatalogWalker.walk_catalog`.
    """
    path = urlparse(url).path or ""
    if _URL_EXCLUSIONS.search(path):
        return None
    clean = re.sub(r"\s+", " ", label or "").strip()
    if len(clean) < MIN_LABEL_CHARS:
        return None
    if names_other_degree_level(url, degree):
        return None
    score = 0
    for pattern, _level in DEGREE_MARKERS:
        if pattern.search(path):
            score += DEGREE_MARKER_BONUS
            break
    if SUBJECT_DEGREE.search(clean):
        score += SUBJECT_DEGREE_BONUS
    if fields and matches_field_text(clean, fields):
        score += FIELD_TEXT_BONUS
    score += matches_field(url, fields)
    score += matches_degree(url, degree)
    return score


def _parent_directory(url: str) -> str:
    return (urlparse(url).path or "").rsplit("/", 1)[0]


def _drop_outcome(url: str, label: str) -> str:
    """Which frozen word explains a hard-rejected link."""
    clean = re.sub(r"\s+", " ", label or "").strip()
    if len(clean) < MIN_LABEL_CHARS:
        return "short_label"
    if _URL_EXCLUSIONS.search(urlparse(url).path or ""):
        return "excluded_url"
    return "degree_level_mismatch"


class CatalogRenderer(BrowserFetcher):
    """A browser tier that also keeps the JSON payloads a catalogue fetches.

    A JS catalogue's rendered DOM may be an empty shell; the programme list
    arrives as JSON responses the page fires while loading. Subclassing the
    browser tier keeps every gate it has (robots, route policy, privacy,
    status mapping) and adds one thing: each JSON body received during a
    render is handed to :meth:`_collect` and kept for the walker to parse.
    """

    def __init__(self, fetcher: Fetcher, *, enabled: bool = True) -> None:
        super().__init__(fetcher, enabled=enabled)
        #: (response_url, content_type, body_text) per JSON response seen
        #: during the most recent render.
        self.catalog_payloads: list[tuple[str, str, str]] = []

    def _collect(self, response_url: str, content_type: str, body_text: str) -> None:
        self.catalog_payloads.append((response_url, content_type, body_text))

    async def render(
        self,
        url: str,
        *,
        response_listener: Callable[[str, str, str], None] | None = None,
    ) -> FetchResult:
        # Cleared in place, never rebound: a walker that grabbed the list
        # before the render must see what this render collects.
        self.catalog_payloads.clear()
        # The stash is the point of this subclass; a caller with a listener
        # of its own wins, everything else lands in the stash.
        return await super().render(url, response_listener=response_listener or self._collect)


class CatalogWalker:
    """Walks an institution's catalogue pages for programme leads."""

    def __init__(
        self,
        *,
        fetcher: Fetcher,
        domain: str,
        degree: str,
        fields: list[str],
        page_recorder: Callable[..., object] | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.domain = domain
        self.degree = degree
        self.fields = fields
        self.page_recorder = page_recorder

    async def walk(self, catalogue_urls: list[str]) -> list[CatalogWalk]:
        """Walk at most :data:`WALKER_MAX_CATALOGS` catalogues, in order given."""
        walks: list[CatalogWalk] = []
        for catalogue_url in catalogue_urls[:WALKER_MAX_CATALOGS]:
            try:
                walks.append(await self.walk_catalog(catalogue_url))
            except Exception as exc:  # one broken catalogue must not end discovery
                log.warning(
                    "catalog walk of %s failed: %s: %s",
                    catalogue_url[:120],
                    type(exc).__name__,
                    exc,
                )
        return walks

    async def walk_catalog(self, catalogue_url: str) -> CatalogWalk:
        """Read one catalogue page and fetch its strongest leads.

        The rendered DOM is the truth when a renderer is attached (an HTTP
        body of a JS shell has no links in it); without one, the plain HTTP
        page is all there is. JSON payloads and HTML links are merged — the
        JSON entry wins a canonical-URL tie, because the payload is the
        university's own statement of what its programmes are — and the top
        :data:`WALKER_TOP_N` scored leads are fetched, classified and judged
        by the same applicant predicate the confirm stage uses.
        """
        walk = CatalogWalk(catalogue_url=catalogue_url)
        html, payloads, catalogue_outcome = await self._read_catalogue(catalogue_url)
        if catalogue_outcome is not None:
            walk.outcomes.append((catalogue_url, catalogue_outcome))

        drops: list[tuple[str, str]] = []
        links = (
            await off_loop(extract_links, html, catalogue_url, self.domain, drops) if html else []
        )
        for url, outcome in drops:
            walk.outcomes.append((url, outcome))

        candidates: dict[str, WalkerLink] = {}
        for _response_url, _content_type, body in payloads:
            for name, url in parse_catalog_json(body, base_url=catalogue_url):
                if not same_institution(url, self.domain):
                    walk.outcomes.append((url, "off_domain"))
                    continue
                if url not in candidates:
                    candidates[url] = WalkerLink(url=url, label=name, score=0, source="json")
        for link in links:
            candidates.setdefault(link.url, link)

        if not candidates:
            # Neither the page's JSON nor its HTML offers a single programme
            # lead: say so rather than leaving the walk silently empty.
            walk.outcomes.append((catalogue_url, "js_no_program_list"))
            return walk

        scored = self._score(list(candidates.values()), walk.outcomes)
        walk.candidates = scored

        budget = scored[:WALKER_TOP_N]
        for link in scored[WALKER_TOP_N:]:
            walk.outcomes.append((link.url, "walker_budget_exhausted"))

        for link in budget:
            await self._read_lead(link, walk)
        return walk

    def _score(self, links: list[WalkerLink], outcomes: list[tuple[str, str]]) -> list[WalkerLink]:
        """Apply the frozen scorer plus the repeating-list bonus, strongest first."""
        siblings = Counter(_parent_directory(link.url) for link in links)
        scored: list[WalkerLink] = []
        for link in links:
            base = score_link(link.url, link.label, self.degree, self.fields)
            if base is None:
                outcomes.append((link.url, _drop_outcome(link.url, link.label)))
                continue
            repeating = siblings[_parent_directory(link.url)] >= REPEATING_LIST_MIN_SIBLINGS
            walk = WalkerLink(
                url=link.url,
                label=link.label,
                score=base + (REPEATING_LIST_BONUS if repeating else 0),
                source=link.source,
            )
            scored.append(walk)
        scored.sort(key=lambda link: (-link.score, len(link.url)))
        return scored

    async def _read_lead(self, link: WalkerLink, walk: CatalogWalk) -> None:
        """Fetch, classify and judge one lead; record exactly one outcome."""
        result = await self.fetcher.get(link.url)
        page: PageClassification | None = None
        if result.ok:
            page = await off_loop(classify_page, url=result.final_url or link.url, html=result.text)
        self._record(link.url, result, page)
        if not result.ok:
            walk.outcomes.append((link.url, result.outcome.value))
            return
        assert page is not None
        # The walker asks what the confirm stage asks, minus the subject
        # refinement: a catalogue's own list is the university's statement of
        # what it offers, and subject fit is judged downstream per programme.
        reason = profile_rejects(page, self.degree, [])
        if reason is not None:
            mismatch = page.degree_level and page.degree_level != self.degree
            walk.outcomes.append(
                (
                    link.url,
                    "degree_level_mismatch" if mismatch else f"reads_as_{page.page_type.value}",
                )
            )
            return
        walk.confirmed.append(link.url)
        walk.outcomes.append((link.url, page.page_type.value))

    async def _read_catalogue(
        self, catalogue_url: str
    ) -> tuple[str, list[tuple[str, str, str]], str | None]:
        """The catalogue's HTML, its JSON payloads, and a fetch outcome if it
        could not be read at all.

        A catalogue renderer (found through the fetcher's own
        ``attach_renderer`` seam) renders the shell the browser sees and stashes
        the JSON the page fetched on the side. No renderer, or a failed render,
        falls back to the plain HTTP body.
        """
        renderer = getattr(self.fetcher, "_renderer", None)
        render = getattr(renderer, "render", None)
        payloads = getattr(renderer, "catalog_payloads", None)
        if callable(render) and isinstance(payloads, list):
            try:
                rendered = await render(catalogue_url)
            except Exception as exc:  # a broken tier must not end the walk
                log.warning("catalogue render failed for %s: %s", catalogue_url[:120], exc)
            else:
                if rendered.ok:
                    return rendered.text, list(payloads), None
        result = await self.fetcher.get(catalogue_url)
        if not result.ok:
            return "", [], result.outcome.value
        html = result.text
        page = await off_loop(classify_page, url=result.final_url or catalogue_url, html=html)
        if page.page_type in _NOT_CATALOGUE_TYPES:
            # The page the site offers as a catalogue reads as something else.
            # The walk still reads its links — the cap bounds the cost — but
            # the report says the catalogue was not what it claimed.
            return html, [], "not_program_catalog"
        return html, [], None

    def _record(
        self,
        url: str,
        result: FetchResult,
        page: PageClassification | None,
    ) -> None:
        """Hand one fetched page to the source_pages recorder, if wired in.

        Definitive HTTP errors are fetches too (a 404 is a fact about a page);
        refusals that never got a status — robots, privacy, timeouts — are not
        recorded. A recorder failure is a logging matter, never a discovery
        failure: discovery says where to look, it does not own the ledger.
        """
        if self.page_recorder is None or result.status_code is None:
            return
        record_url = canonical_url(result.final_url or url)
        try:
            self.page_recorder(
                url=record_url,
                registrable_domain=registrable_domain(urlparse(record_url).hostname or ""),
                etag=result.etag or None,
                last_modified_header=result.last_modified or None,
                content_hash=result.content_hash or None,
                http_status=result.status_code,
                page_type=page.page_type.value if page is not None else "unknown",
                institution_key=None,
                fetched_at=result.fetched_at,
            )
        except Exception as exc:
            log.warning("source_pages recording failed for %s: %s", record_url[:120], exc)
