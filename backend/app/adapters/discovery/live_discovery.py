"""Live candidate discovery against real university websites.

Discovery is **sitemap-first**. A university's own sitemap is a machine-readable
statement of what it publishes, which is a far better guide than guessing at
navigation: the previous heuristic followed the global menu and reached landing
pages, so live runs confirmed almost nothing.

The order is:

1. **Manual seeds** from the registry, where a human has verified which page is
   the programme catalogue, the admissions page, the fee page and so on.
2. **Sitemaps**, found through robots.txt hints and the conventional locations,
   including sitemap indexes and gzipped sitemaps.
3. **Navigation**, only as a fallback when neither produced anything.

Two rules hold throughout, and the tests pin both:

* A manual seed says *where to look*. It is never itself evidence of a
  requirement — the page still has to be fetched and classified, and the
  classifier decides. A seed that turns out to be a landing page yields
  nothing.
* Nothing off the institution's own registrable domain is followed.

Everything is bounded: how many sitemaps are read, how many URLs are kept, how
large a sitemap may be. Discovery on a large university site must not become a
crawl of it.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from app.adapters.base import Candidate, CandidateProgram

# Re-exported so the adapter, the canary and the tests keep one import site.
# The rules themselves live in `url_signals`, which touches nothing.
from app.adapters.discovery.url_signals import (  # noqa: F401
    _CATALOGUE_PATH,
    _FUNDING_SEGMENT,
    _INDEX_SEGMENT,
    _NOT_A_PAGE_ABOUT_STUDYING,
    _NOT_A_PROGRAMME_PATH,
    _TRACKING_PARAM,
    _URL_EXCLUSIONS,
    PageCategory,
    canonical_url,
    categorise_url,
    degree_level_named,
    degree_levels_named,
    looks_like_catalogue,
    matches_degree,
    matches_field,
    matches_field_text,
    names_other_degree_level,
    registrable_domain,
    same_institution,
    score_url,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RankingEntry

log = logging.getLogger("unimatch.discovery")

REGISTRY_PATH = Path(__file__).parent / "institution_registry.json"

# --- bounds ---------------------------------------------------------------
#: Sitemap documents read per institution, including nested index children.
#: A sitemap index declares a finite list, and reading one costs a single fetch,
#: so this is generous: at 12 Aalto's index was cut off after 55,000 of its
#: 58,000 URLs and the document holding its programme pages was never opened.
#: The real limit on work is MAX_SITEMAP_URLS below.
MAX_SITEMAP_DOCUMENTS = 40
#: URLs read from all sitemaps combined. Scanning is cheap — the documents are
#: already fetched — so this is generous.
MAX_SITEMAP_URLS = 200_000
#: Candidate URLs *kept* per category. The live canary caught the reason these
#: are separate: with one combined bound, rug.nl filled the budget with 20,000
#: news articles from a research institute and the sitemap walk stopped before
#: reaching a single programme page. Relevance has to be decided per URL as it
#: is read, not after a prefix of the site has been collected.
MAX_CANDIDATES_PER_CATEGORY = 40
#: How deep a sitemap index may nest before we stop following it.
MAX_SITEMAP_DEPTH = 3
#: Candidate pages actually fetched per category.
MAX_PAGES_PER_CATEGORY = 3
#: Links scanned on a page during the navigation fallback.
MAX_LINKS_SCANNED = 400
#: Programme candidates fetched and classified before giving up on finding a
#: real programme page. Costs little: the pipeline fetches these pages anyway
#: and the fetcher caches, so a confirmed candidate is free downstream.
MAX_PROGRAM_CANDIDATES_CHECKED = 8
#: Extra weight for a catalogue entry whose own wording names the applicant's
#: subject. Large on purpose: on a catalogue every entry is structurally
#: identical, so the wording is the only thing that separates them.
SUBJECT_IN_LINK_TEXT_BONUS = 12
#: Catalogue pages re-read through the browser per institution. A render is
#: slow and heavy, so it is spent only where a static read demonstrably
#: failed to show any programme at all.
MAX_RENDERED_CATALOGUES = 2
#: How many times a candidate that turns out to be a catalogue may hand back
#: the programmes it lists. Bounds a chain of indexes that never ends in a
#: programme.
MAX_CATALOGUE_EXPANSIONS = 4
#: Pages walked during the navigation fallback. Universities routinely nest
#: "Degree programmes" -> "Bachelor programmes" -> a programme, so one hop is
#: not enough; an unbounded walk would be a crawl.
MAX_FALLBACK_PAGES = 5

#: Conventional sitemap locations, tried when robots.txt names none.
SITEMAP_FALLBACK_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap/sitemap.xml",
)




@dataclass
class DiscoveredUrl:
    url: str
    category: str
    score: int
    #: "manual_seed" | "sitemap" | "navigation"
    provenance: str
    note: str = ""


@dataclass
class DiscoveryTrace:
    """Why each institution produced what it did.

    Recorded per run so a discovery that found nothing can say which step
    failed, rather than leaving the user with an empty list.
    """

    institution: str
    domain: str
    sitemaps_declared: list[str] = field(default_factory=list)
    sitemaps_read: list[str] = field(default_factory=list)
    sitemap_urls_seen: int = 0
    sitemap_urls_kept: int = 0
    manual_seeds: dict[str, str] = field(default_factory=dict)
    selected: dict[str, list[str]] = field(default_factory=dict)
    rejected: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    used_navigation_fallback: bool = False
    #: (url, link text) for leads found by a catalogue's own wording rather
    #: than by the URL, so the report can show what the wording was.
    kept_by_link_text: list[tuple[str, str]] = field(default_factory=list)
    #: url -> relevance score, so candidates are read best-first and the report
    #: can show why one page was preferred over another.
    relevance: dict[str, int] = field(default_factory=dict)
    #: (url, subject, page type) for each candidate a read of the page confirmed.
    confirmed_programs: list[tuple[str, str, str]] = field(default_factory=list)
    #: (url, links before rendering, links after) for each browser escalation.
    rendered: list[tuple[str, int, int]] = field(default_factory=list)

    def reject(self, url: str, reason: str) -> None:
        # Bounded: a large sitemap would otherwise produce a huge trace.
        if len(self.rejected) < 200:
            self.rejected.append((url, reason))

    def as_dict(self) -> dict:
        return {
            "institution": self.institution,
            "domain": self.domain,
            "sitemaps_declared": self.sitemaps_declared,
            "sitemaps_read": self.sitemaps_read,
            "sitemap_urls_seen": self.sitemap_urls_seen,
            "sitemap_urls_kept": self.sitemap_urls_kept,
            "manual_seeds": self.manual_seeds,
            "selected": self.selected,
            "rejected_sample": self.rejected[:40],
            "rejected_total": len(self.rejected),
            "errors": self.errors,
            "used_navigation_fallback": self.used_navigation_fallback,
            "kept_by_link_text": self.kept_by_link_text,
            "confirmed_programs": self.confirmed_programs,
            "rendered_catalogues": self.rendered,
            "relevance": dict(sorted(
                self.relevance.items(), key=lambda kv: -kv[1])[:40]),
        }


# --- sitemaps -------------------------------------------------------------

_SITEMAP_DIRECTIVE = re.compile(r"^\s*sitemap:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_XML_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap_directives(robots_text: str) -> list[str]:
    """Sitemap: lines from robots.txt. A site telling us where to look."""
    return [m.group(1).strip() for m in _SITEMAP_DIRECTIVE.finditer(robots_text or "")]


def decode_sitemap(body: bytes, url: str) -> str:
    """Sitemap text, transparently un-gzipping when needed.

    Gzipped sitemaps are common and are not always served with a content
    encoding that the HTTP layer will undo, so the magic number is checked.
    """
    if body[:2] == b"\x1f\x8b" or url.lower().endswith(".gz"):
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError) as exc:
            log.info("could not gunzip %s: %s", url, exc)
            return ""
    return body.decode("utf-8", errors="replace")


def parse_sitemap(text: str) -> tuple[list[str], list[str]]:
    """Return (child sitemap URLs, page URLs) from one sitemap document."""
    if not text.strip():
        return [], []
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        # Some sites serve a plain-text list of URLs. Accept that too.
        lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("http")]
        return [], lines[:MAX_SITEMAP_URLS]

    tag = root.tag.lower()
    locations = [
        (el.text or "").strip()
        for el in root.iter()
        if el.tag in (f"{_XML_NS}loc", "loc") and (el.text or "").strip()
    ]
    if "sitemapindex" in tag:
        return locations, []
    return [], locations


class SitemapReader:
    """Reads an institution's sitemaps, within bounds."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def collect(
        self,
        homepage: str,
        domain: str,
        trace: DiscoveryTrace,
        keep: Callable[[str], bool] | None = None,
    ) -> list[str]:
        """Page URLs the institution's sitemaps declare, deduplicated.

        ``keep`` decides relevance as each URL is read. Without it every URL is
        kept, which is what the unit tests want but not what a real university
        sitemap can afford: filtering afterwards means the bound falls wherever
        the site happens to have listed its news.
        """
        origin = self._origin(homepage)
        declared = await self._declared_sitemaps(origin, trace)
        queue: list[tuple[str, int]] = [(u, 0) for u in declared]
        if not queue:
            queue = [(urljoin(origin, path), 0) for path in SITEMAP_FALLBACK_PATHS]

        seen_documents: set[str] = set()
        pages: list[str] = []
        seen_pages: set[str] = set()

        while queue:
            if len(trace.sitemaps_read) >= MAX_SITEMAP_DOCUMENTS:
                # Never silently. A truncated sitemap means part of the site was
                # not looked at, and a run that does not say so reads as a run
                # that found nothing there.
                trace.errors.append(
                    f"stopped after {MAX_SITEMAP_DOCUMENTS} sitemap documents with "
                    f"{len(queue)} still queued; part of the site was not read"
                )
                break
            url, depth = queue.pop(0)
            url = canonical_url(url)
            if url in seen_documents or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_documents.add(url)

            if not same_institution(url, domain):
                trace.reject(url, "sitemap is off the institution's domain")
                continue

            result = await self.fetcher.get(url)
            if not result.ok:
                trace.errors.append(f"{url}: {result.outcome.value} — {result.error}"[:300])
                continue
            trace.sitemaps_read.append(url)

            children, locations = parse_sitemap(decode_sitemap(result.content, url))
            for child in children:
                queue.append((child, depth + 1))
            for location in locations:
                trace.sitemap_urls_seen += 1
                canonical = canonical_url(location)
                if canonical in seen_pages:
                    continue
                if not same_institution(canonical, domain):
                    trace.reject(canonical, "off the institution's domain")
                    continue
                seen_pages.add(canonical)
                if keep is not None and not keep(canonical):
                    continue
                pages.append(canonical)
                if trace.sitemap_urls_seen >= MAX_SITEMAP_URLS:
                    trace.errors.append(
                        f"stopped after reading {MAX_SITEMAP_URLS:,} sitemap URLs; "
                        "the sitemap is larger than we read"
                    )
                    trace.sitemap_urls_kept = len(pages)
                    return pages

        trace.sitemap_urls_kept = len(pages)
        return pages

    async def _declared_sitemaps(self, origin: str, trace: DiscoveryTrace) -> list[str]:
        result = await self.fetcher.get(urljoin(origin, "/robots.txt"))
        if not result.ok:
            trace.errors.append(f"robots.txt unavailable: {result.outcome.value}")
            return []
        declared = parse_sitemap_directives(result.text)
        trace.sitemaps_declared = declared
        return declared

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlparse(url)
        return f"{parts.scheme}://{parts.netloc}"


# --- the adapter ----------------------------------------------------------


class LiveDiscoveryAdapter:
    """Finds official pages for an institution, sitemap-first."""

    name = "live-sitemap-discovery"

    def __init__(self, fetcher: Fetcher, registry_path: Path | None = None) -> None:
        self.fetcher = fetcher
        self.registry_path = registry_path or REGISTRY_PATH
        self.sitemaps = SitemapReader(fetcher)
        #: Populated per run, so a caller can report why discovery found what it did.
        self.traces: list[DiscoveryTrace] = []

    def registry(self) -> list[dict]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text())

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        prefs = profile.preferences
        excluded = {c.lower() for c in prefs.excluded_countries}
        preferred = {c.lower() for c in prefs.preferred_countries}

        entries = [e for e in self.registry() if e["country"].lower() not in excluded]
        if preferred:
            entries.sort(key=lambda e: 0 if e["country"].lower() in preferred else 1)
        entries = entries[:limit]

        self.traces = []
        out: list[Candidate] = []
        for entry in entries:
            # One institution must not be able to end the research for the
            # rest. A holdout run died on the second of six and reported the
            # remaining four as NOT_ATTEMPTED, which reads as a finding about
            # those universities when it was a finding about one page on
            # another site.
            try:
                candidate, trace = await self._discover_one(entry, profile)
            except Exception as exc:  # reported below, never silent
                trace = DiscoveryTrace(institution=entry["name"], domain=domain_of(entry))
                trace.errors.append(f"discovery failed: {type(exc).__name__}: {exc}")
                candidate = Candidate(
                    name=entry["name"],
                    country=entry["country"],
                    city=entry.get("city", ""),
                    domain=domain_of(entry),
                    discovery_source="registry",
                    notes=f"Discovery failed for this institution: {exc}",
                )
            self.traces.append(trace)
            out.append(candidate)
        return out

    async def _discover_one(
        self, entry: dict, profile: ApplicantProfileIn
    ) -> tuple[Candidate, DiscoveryTrace]:
        domain = urlparse(entry["homepage"]).netloc
        trace = DiscoveryTrace(institution=entry["name"], domain=domain)

        candidate = Candidate(
            name=entry["name"],
            country=entry["country"],
            city=entry.get("city", ""),
            domain=domain,
            attributes=entry.get("attributes", {}),
            rankings=[RankingEntry(**r) for r in entry.get("rankings", [])],
            discovery_source=f"{self.name} -> {entry['homepage']}",
        )

        # 1. Manual seeds. A human has verified which page is which. This says
        #    where to look; it is not itself evidence of anything on the page.
        seeds = {k: v for k, v in (entry.get("seeds") or {}).items() if v}
        trace.manual_seeds = dict(seeds)
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        for category, url in seeds.items():
            if category not in selected:
                trace.reject(url, f"unknown seed category {category!r}")
                continue
            if not same_institution(url, domain):
                trace.reject(url, "manual seed is off the institution's domain")
                continue
            selected[category].append(canonical_url(url))

        # 2. Sitemaps. Relevance is decided as each URL is read, not after the
        #    whole sitemap is collected: a university publishes far more news
        #    than programmes, and a bound applied to raw URLs stops in the news.
        ranked: dict[str, list[tuple[int, str]]] = {c: [] for c in PageCategory.ALL}
        fields = list(profile.context.intended_fields)
        degree = str(profile.context.level)

        def keep(url: str) -> bool:
            category, score = categorise_url(url)
            if category is None:
                return False
            if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
                if names_other_degree_level(url, degree):
                    trace.reject(url, f"names a degree level other than {degree}")
                    return False
                score += matches_field(url, fields) + matches_degree(url, degree)
            if score <= 0:
                trace.reject(url, "scored zero for every category")
                return False
            if len(ranked[category]) >= MAX_CANDIDATES_PER_CATEGORY:
                # Keep the best, not the first: a later URL may outrank the
                # weakest one already held.
                weakest = min(ranked[category])
                if score <= weakest[0]:
                    return False
                ranked[category].remove(weakest)
            ranked[category].append((score, url))
            trace.relevance[url] = max(trace.relevance.get(url, 0), score)
            return True

        try:
            await self.sitemaps.collect(entry["homepage"], domain, trace, keep)
        except Exception as exc:  # a malformed sitemap must not end the run
            trace.errors.append(f"sitemap discovery failed: {type(exc).__name__}: {exc}")

        for category, scored in ranked.items():
            scored.sort(key=lambda pair: (-pair[0], len(pair[1])))
            for _score, url in scored:
                if len(selected[category]) >= MAX_PAGES_PER_CATEGORY:
                    break
                if url not in selected[category]:
                    selected[category].append(url)

        # 3. Confirm what we have, then widen the search only while the
        #    applicant's own subject is still unaccounted for.
        #
        #    Both halves of that sentence were defects. Confirmation used to run
        #    last, so unread guesses decided whether to search further; and the
        #    catalogue walk was gated on finding *no* programme at all, so TU
        #    Delft — whose sitemap yields aerospace, mathematics and physics —
        #    never walked the catalogue that lists its computer science degree.
        #    Finding three programmes the applicant did not ask about is not a
        #    reason to stop looking for the one they did.
        fields = list(profile.context.intended_fields)
        await self._confirm_programs(
            selected, ranked, trace, profile=profile, domain=domain
        )

        if not _satisfies_field(selected[PageCategory.PROGRAM_PAGE], fields):
            trace.used_navigation_fallback = True
            before = set(selected[PageCategory.PROGRAM_PAGE])
            await self._navigation_fallback(entry, domain, selected, trace, profile, ranked)
            if set(selected[PageCategory.PROGRAM_PAGE]) != before:
                # The walk proposed new candidates; they are guesses until read.
                await self._confirm_programs(
                    selected, ranked, trace, keep=before, profile=profile,
                    domain=domain,
                )

        trace.selected = {k: list(v) for k, v in selected.items() if v}
        self._apply(candidate, selected, profile, trace)
        return candidate, trace

    async def _confirm_programs(
        self,
        selected: dict[str, list[str]],
        ranked: dict[str, list[tuple[int, str]]],
        trace: DiscoveryTrace,
        keep: set[str] | None = None,
        profile: ApplicantProfileIn | None = None,
        domain: str = "",
    ) -> None:
        """Keep only candidates a read of the page confirms is a programme.

        Candidates are read in relevance order, so the applicant's own subject
        is checked before an unrelated programme spends the budget. ``keep``
        holds pages confirmed on an earlier pass, which are not re-fetched.

        A candidate that turns out to be a catalogue hands back the programmes
        it lists. Groningen's bachelor listing links to faculty and subject
        sub-indexes, and reading each one, rejecting it, and discarding the
        page spent the whole budget on indexes while the computing science
        degree sat one link inside them. The page is already fetched and
        classified; harvesting it costs nothing more.
        """
        fields = list(profile.context.intended_fields) if profile else []
        degree = str(profile.context.level) if profile else ""

        already = set(keep or ())
        queued = [u for u in selected[PageCategory.PROGRAM_PAGE] if u not in already]
        # Next-best candidates, so rejecting one does not mean finding nothing.
        for _score, url in sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True):
            if url not in queued and url not in already:
                queued.append(url)
        queued.sort(key=lambda u: -trace.relevance.get(u, 0))

        confirmed: list[str] = list(already)
        checked = 0
        seen: set[str] = set(queued)
        expansions = 0
        while queued:
            if len(confirmed) >= MAX_PAGES_PER_CATEGORY:
                break
            if checked >= MAX_PROGRAM_CANDIDATES_CHECKED:
                trace.errors.append(
                    f"stopped after reading {checked} programme candidates; "
                    "others were left unchecked rather than guessed at"
                )
                break
            url = queued.pop(0)
            checked += 1
            result = await self.fetcher.get(url)
            if not result.ok:
                trace.reject(url, f"could not be read ({result.outcome.value})")
                continue
            page = classify_page(url=url, html=result.text)
            if page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM):
                confirmed.append(url)
                trace.confirmed_programs.append((url, page.subject or "", page.page_type.value))
                continue

            trace.reject(url, f"reads as {page.page_type.value}, not a programme page")
            if (
                page.page_type is PageType.PROGRAM_CATALOG
                and expansions < MAX_CATALOGUE_EXPANSIONS
                and domain
            ):
                expansions += 1
                fresh = self._programmes_listed_on(
                    result.text, result.final_url or url, domain, fields, degree, trace
                )
                added = [u for u in fresh if u not in seen]
                seen.update(added)
                # Best-first again, so the applicant's subject leads.
                queued = sorted(
                    [*queued, *added], key=lambda u: -trace.relevance.get(u, 0)
                )
                if added:
                    trace.errors.append(
                        f"{url} reads as a catalogue; followed {len(added)} "
                        "programme links it lists"
                    )

        if confirmed or selected[PageCategory.PROGRAM_PAGE]:
            # Only replace the list when something was actually checked; an
            # unreachable site keeps its leads rather than losing them silently.
            selected[PageCategory.PROGRAM_PAGE] = confirmed

    def _programmes_listed_on(
        self, html: str, base: str, domain: str,
        fields: list[str], degree: str, trace: DiscoveryTrace,
    ) -> list[str]:
        """Programme links a catalogue page lists, scored for this applicant."""
        found: list[str] = []
        for url, label in _harvest_links(html, base, domain):
            canonical = canonical_url(url)
            category, score = categorise_url(canonical)
            if category != PageCategory.PROGRAM_PAGE:
                continue
            if names_other_degree_level(canonical, degree):
                continue
            score += matches_field(canonical, fields) + matches_degree(canonical, degree)
            if matches_field_text(label, fields):
                score += SUBJECT_IN_LINK_TEXT_BONUS
                trace.kept_by_link_text.append((canonical, label[:80]))
            if score <= 0:
                continue
            trace.relevance[canonical] = max(trace.relevance.get(canonical, 0), score)
            found.append(canonical)
        return found

    def _apply(
        self, candidate: Candidate, selected: dict[str, list[str]],
        profile: ApplicantProfileIn, trace: DiscoveryTrace,
    ) -> None:
        """Attach what was found. A category with nothing stays None."""
        candidate.admissions_url = _first(selected[PageCategory.ADMISSIONS])
        candidate.costs_url = _first(selected[PageCategory.COSTS])
        candidate.scholarships_url = _first(selected[PageCategory.SCHOLARSHIPS])

        fields = list(profile.context.intended_fields)
        for url in selected[PageCategory.PROGRAM_PAGE][:MAX_PAGES_PER_CATEGORY]:
            candidate.programs.append(
                CandidateProgram(
                    name=_program_name_from_url(url, fields, profile.context.level),
                    field=fields[0] if fields else "",
                    degree=profile.context.level,
                    url=url,
                )
            )
        # A catalogue is a lead, not a programme. It is offered only when no
        # programme page was found, and downstream classification will reject it
        # as a source of requirements — which is the correct outcome.
        if not candidate.programs and selected[PageCategory.PROGRAM_CATALOG]:
            trace.errors.append(
                "no programme page was found; only a catalogue, which cannot confirm a programme"
            )

        found = [c for c in PageCategory.ALL if selected[c]]
        missing = [c for c in PageCategory.ALL if not selected[c]]
        candidate.notes = (
            f"Sitemap-first discovery found: {', '.join(found) or 'nothing'}."
            + (f" Not found: {', '.join(missing)}." if missing else "")
        )

    async def _navigation_fallback(
        self, entry: dict, domain: str, selected: dict[str, list[str]],
        trace: DiscoveryTrace, profile: ApplicantProfileIn,
        ranked: dict[str, list[tuple[int, str]]] | None = None,
    ) -> None:
        """Walk the catalogue's links, then the homepage's.

        A programme catalogue is the page a university builds precisely to list
        its programmes, so when discovery has one it is a far better place to
        look than the global menu. The homepage is the last resort.
        """
        degree = str(profile.context.level)
        fields = list(profile.context.intended_fields)
        ranked = ranked if ranked is not None else {c: [] for c in PageCategory.ALL}
        # Catalogues first, deepest lead first; the homepage is the last resort
        # rather than a queue entry. Putting it in the queue let HKU's two
        # Chinese copies of the same catalogue consume the budget before the
        # walk reached the programme list.
        # Catalogues first, then the admissions hub. A university with no
        # catalogue — KAIST publishes none — fell straight through to the
        # homepage, while its international admissions page, already selected
        # and fetched, linked to the cost of attendance, the scholarship and
        # the documents to submit. An admissions hub is where fees, funding and
        # paperwork are gathered; it is worth walking for the reason a
        # catalogue is.
        queue = list(selected[PageCategory.PROGRAM_CATALOG][:2])
        if not queue:
            # Only when there is no catalogue at all. Queueing the admissions
            # hub alongside catalogues spent the same fixed budget on it and
            # displaced the catalogue walk: Uppsala stopped reaching the
            # programmes it had been finding, and Vienna stopped reaching a
            # funding page. A university with a catalogue is already being
            # read the best way there is.
            queue = list(selected[PageCategory.ADMISSIONS][:2])
        walked: set[str] = set()
        homepage_tried = False
        rendered_catalogues = 0

        while len(walked) < MAX_FALLBACK_PAGES:
            # Stop once the applicant's subject is actually accounted for, not
            # merely once some programme has been found.
            if _satisfies_field(selected[PageCategory.PROGRAM_PAGE], fields):
                break
            if not queue:
                if homepage_tried:
                    break
                homepage_tried = True
                queue.append(entry["homepage"])
            start = queue.pop(0)
            if start in walked:
                continue
            walked.add(start)
            result = await self.fetcher.get(start)
            if not result.ok:
                trace.errors.append(
                    f"navigation fallback: {start} unreachable ({result.outcome.value})"
                )
                continue
            from_catalogue = start in selected[PageCategory.PROGRAM_CATALOG]
            links = _harvest_links(result.text, result.final_url or start, domain)

            # A catalogue that shows no programme at all in its served HTML is
            # building its list in the browser. UBC, Warsaw and HKU all serve a
            # hundred-odd links and not one programme. Reading the page as a
            # browser would is the difference between "it is not there" and "we
            # did not look"; it is bounded, and only spent on this case.
            if (
                from_catalogue
                and rendered_catalogues < MAX_RENDERED_CATALOGUES
                and not catalogue_shows_subject(links, fields, degree)
            ):
                rendered_catalogues += 1
                rendered = await self.fetcher.render(start)
                if rendered.ok:
                    grown = _harvest_links(rendered.text, rendered.final_url or start, domain)
                    trace.rendered.append((start, len(links), len(grown)))
                    if len(grown) > len(links):
                        links = grown
                else:
                    trace.errors.append(
                        f"catalogue {start} showed no programmes and could not be "
                        f"rendered ({rendered.outcome.value})"
                    )

            for url, label in links:
                category, score = categorise_url(url)
                if category is None:
                    # On a catalogue page, a link whose own text names the
                    # applicant's subject is a programme lead even when the URL
                    # says nothing. Still only a lead: the page is fetched and
                    # classified like any other, and a catalogue or a news item
                    # is rejected there.
                    if not (from_catalogue and matches_field_text(label, fields)):
                        continue
                    if _URL_EXCLUSIONS.search(urlparse(url).path or ""):
                        continue
                    category, score = PageCategory.PROGRAM_PAGE, 4
                    trace.kept_by_link_text.append((url, label[:80]))
                if score <= 0:
                    continue
                if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
                    if names_other_degree_level(url, degree):
                        continue
                    score += matches_field(url, fields) + matches_degree(url, degree)
                    # A catalogue's entry that names the subject in its own
                    # wording is the strongest lead on the page. Vienna listed
                    # "African Studies" first and filled every slot with it,
                    # because only the URL was consulted and every entry scored
                    # the same.
                    if from_catalogue and matches_field_text(label, fields):
                        score += SUBJECT_IN_LINK_TEXT_BONUS
                        trace.kept_by_link_text.append((url, label[:80]))
                    if score <= 0:
                        continue
                    trace.relevance[canonical_url(url)] = max(
                        trace.relevance.get(canonical_url(url), 0), score
                    )
                    if category == PageCategory.PROGRAM_PAGE:
                        # Programme leads go to the ranked pool, not straight
                        # into the three slots. Confirmation reads them
                        # best-first, so a relevant page found late still beats
                        # an irrelevant one found early.
                        ranked[PageCategory.PROGRAM_PAGE].append(
                            (score, canonical_url(url))
                        )
                canonical = canonical_url(url)
                if (
                    looks_like_catalogue(canonical)
                    and canonical not in walked
                    and canonical not in queue
                    and canonical != canonical_url(start)
                ):
                    # "Degree programmes" often lists "Bachelor programmes"
                    # rather than the programmes themselves. Follow one more
                    # hop rather than stopping at the intermediate page, and go
                    # depth-first: a page below the current one is a more
                    # specific lead than another page beside it.
                    if canonical.startswith(canonical_url(start)):
                        queue.insert(0, canonical)
                    else:
                        queue.append(canonical)
                if (
                    len(selected[category]) < MAX_PAGES_PER_CATEGORY
                    and canonical not in selected[category]
                ):
                    selected[category].append(canonical)


def catalogue_shows_subject(
    links: list[tuple[str, str]], fields: list[str], degree: str,
) -> bool:
    """Whether a catalogue's links already reach the applicant's subject.

    Asked before deciding to re-read the page through the browser. The first
    version asked only whether the page carried *any* programme-shaped link,
    which is a different and much weaker question: Groningen's bachelor
    catalogue carries fourteen, none of them a programme and none of them
    computing, so the render never fired and the subject was never found.
    """
    if not fields:
        return any(categorise_url(u)[0] == PageCategory.PROGRAM_PAGE for u, _ in links)
    for url, label in links:
        if names_other_degree_level(url, degree):
            continue
        if matches_field_text(label, fields) or matches_field(url, fields):
            return True
    return False


def _satisfies_field(urls: list[str], fields: list[str]) -> bool:
    """Whether any confirmed programme is plausibly the subject asked for.

    With no stated field every programme counts, so a profile that names no
    subject does not send the crawler round the whole catalogue.
    """
    wanted = [w for f in fields for w in re.split(r"[^a-z]+", f.lower()) if len(w) > 3]
    if not wanted:
        return bool(urls)
    return any(all(w in url.lower() for w in wanted) for url in urls)


def _first(urls: list[str]) -> str | None:
    return urls[0] if urls else None


def _program_name_from_url(url: str, fields: list[str], degree: object) -> str:
    """A readable placeholder name from the URL's last segment.

    Deliberately not treated as the programme's real name: the programme page
    itself supplies that, and the classifier checks it against what was asked
    for. This is only what discovery calls the lead until then.
    """
    slug = (urlparse(url).path or "").rstrip("/").rsplit("/", 1)[-1]
    words = [w for w in re.split(r"[-_]+", slug) if w and not w.isdigit()]
    if not words:
        return f"{fields[0] if fields else 'programme'} ({degree})"
    return " ".join(words).replace(".html", "").strip().title()


def domain_of(entry: dict) -> str:
    return urlparse(entry.get("homepage", "")).netloc


def _harvest_links(html: str, base: str, domain: str) -> list[tuple[str, str]]:
    """Every same-institution link on a page.

    Parsing is guarded because pages on the public web are not always
    well-formed: one page in a holdout run carried markup that made lxml raise
    `ValueError` from inside its own namespace handling, and the exception rose
    all the way out of the run. A page that cannot be parsed is a page with no
    links — that is a fact about the page, not a reason to stop researching.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # any parser failure means "no links here"
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        url = urljoin(base, anchor["href"]).split("#")[0]
        if urlparse(url).scheme not in ("http", "https"):
            continue
        if not same_institution(url, domain):
            continue
        canonical = canonical_url(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:160]
        out.append((canonical, label))
    return out
