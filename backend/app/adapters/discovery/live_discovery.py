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
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RankingEntry

log = logging.getLogger("unimatch.discovery")

REGISTRY_PATH = Path(__file__).parent / "institution_registry.json"

# --- bounds ---------------------------------------------------------------
#: Sitemap documents read per institution, including nested index children.
MAX_SITEMAP_DOCUMENTS = 12
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

#: Multi-part public suffixes common among universities. Used to work out the
#: registrable domain without depending on the full public suffix list: "same
#: domain" must mean rug.nl and www.rug.nl, not ac.uk and anything under it.
MULTIPART_SUFFIXES = frozenset(
    {
        "ac.uk",
        "ac.nz",
        "ac.jp",
        "ac.kr",
        "ac.at",
        "ac.be",
        "ac.il",
        "ac.in",
        "ac.za",
        "ac.th",
        "ac.id",
        "ac.ir",
        "ac.cy",
        "ac.rs",
        "ac.ma",
        "edu.au",
        "edu.sg",
        "edu.hk",
        "edu.cn",
        "edu.tw",
        "edu.my",
        "edu.pl",
        "edu.tr",
        "edu.mx",
        "edu.br",
        "edu.ar",
        "edu.co",
        "edu.pe",
        "edu.vn",
        "edu.ph",
        "edu.sa",
        "edu.eg",
        "edu.lb",
        "edu.jo",
        "edu.kw",
        "edu.pk",
        "co.uk",
        "org.uk",
        "gov.uk",
        "com.au",
        "net.au",
        "org.au",
        "com.br",
        "com.sg",
        "com.hk",
        "com.tr",
        "com.mx",
        "co.jp",
        "co.nz",
        "co.za",
        "or.jp",
        "ne.jp",
        "go.jp",
        "re.kr",
        "or.kr",
        "go.kr",
    }
)


class PageCategory:
    """What a discovered URL is expected to be. Deliberately a plain namespace
    rather than an enum: this module may not import the classifier's vocabulary,
    and these are *expectations* about a URL, not verdicts about a page."""

    PROGRAM_CATALOG = "program_catalog"
    PROGRAM_PAGE = "program_page"
    ADMISSIONS = "admissions"
    COSTS = "costs"
    SCHOLARSHIPS = "scholarships"
    DOCUMENTS = "documents"

    ALL = (PROGRAM_CATALOG, PROGRAM_PAGE, ADMISSIONS, COSTS, SCHOLARSHIPS, DOCUMENTS)


#: Path and slug signals per category, with a weight. A URL scores against each
#: category and is filed under its best match, if any match at all.
_URL_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    PageCategory.PROGRAM_PAGE: (
        (r"/(bsc|msc|ba|ma|beng|meng|llb|llm)[-/]", 5),
        (r"/(bachelors?|masters?|undergraduate)/[a-z-]{4,}", 5),
        (r"/(programmes?|programs?|degrees?|courses?|studies)/[a-z-]{4,}", 4),
        # The same hyphenated compounds the catalogue rule allows: Vienna
        # publishes at /bachelordiploma-programmes/<programme>, which no rule
        # expecting a bare "/programmes/" segment ever matched.
        (r"/[a-z0-9]+-(programmes?|programs?|degrees?|courses?)/[a-z][a-z0-9-]{3,}", 4),
        (r"/study/[a-z-]{4,}", 3),
        (r"/(opleidingen|studiengang|koulutus|kierunki)/[a-z-]{4,}", 3),
    ),
    PageCategory.PROGRAM_CATALOG: (
        # The segment has to *end* with the listing word, so "degree-programmes"
        # and "degrees-programs" count while "degree-ceremony-photos" and
        # "programme-news" do not. Universities name these pages "degree
        # programmes" far more often than "programmes", and requiring the bare
        # word left the walk stranded on the intermediate page at Vienna,
        # Warsaw and UBC.
        (r"/[a-z0-9-]*(programmes?|programs?|degrees?|courses?|studies)/?$", 5),
        (r"/(bachelors?|masters?|undergraduate|postgraduate)/?$", 5),
        (r"/(study|studies|education)/(programmes?|programs?|degrees?)/?$", 4),
        (r"/(course|programme|program)[-_]?(search|finder|list|catalog(ue)?)", 4),
    ),
    PageCategory.ADMISSIONS: (
        (r"/(admission|admissions|apply|application)", 4),
        (r"/(entry|admission)[-_]requirements", 5),
        (r"/how[-_]to[-_]apply", 5),
        (r"/international[-_]?(students?|applicants?|admissions?)", 3),
        (r"/(toelating|zulassung|haku|rekrutacja)", 3),
    ),
    PageCategory.COSTS: (
        (r"/(tuition|fees?|cost|costs)", 4),
        (r"/tuition[-_]?fees?", 5),
        (r"/cost[-_]of[-_](attendance|living|study)", 5),
        (r"/(collegegeld|studiengebuehren|lukuvuosimaksut|czesne)", 4),
    ),
    PageCategory.SCHOLARSHIPS: (
        (r"/(scholarship|scholarships|bursary|bursaries|grants?)", 4),
        (r"/(financial[-_]aid|funding|fellowships?)", 4),
        (r"/(beurzen|stipendien|apurahat|stypendia)", 4),
    ),
    PageCategory.DOCUMENTS: (
        (r"/(required[-_]documents|documents[-_]required|document[-_]checklist)", 5),
        (r"/(supporting[-_]documents|what[-_]to[-_]submit)", 4),
    ),
}

#: Slug fragments that make a page an event, a newsletter or an announcement
#: whatever path it sits under. The live canary found these *inside* programme
#: paths, where a whole-segment exclusion never sees them: rug.nl returned
#: "bachelor-open-day", "onlinebachelorweek" and "student-for-a-day" as the
#: applicant's three programme pages, and aalto.fi returned two newsletters.
_NOT_A_PAGE_ABOUT_STUDYING = re.compile(
    r"(open[-_]?day|openday|info(rmation)?[-_]?(session|day|evening)|student[-_]for[-_]a[-_]day"
    r"|bachelor[-_]?week|master[-_]?week|onlinebachelor|onlinemaster"
    r"|newsletter|nyhetsbrev|uutiskirje|webinar|open[-_]house|taster"
    r"|campus[-_]?tour|university[-_]?tour|virtual[-_]?tour|webklas|proefstuderen"
    r"|summer[-_]school|orientation|graduation|ceremony)",
    re.IGNORECASE,
)

#: URLs that are never worth fetching, whatever else they score.
_URL_EXCLUSIONS = re.compile(
    r"/(news|nieuws|actueel|press|blog|events?|agenda|calendar|vacature|vacanc"
    r"|jobs?|careers?|alumni|donate|shop|library|contact|privacy|cookie|search"
    r"|login|signin|account|basket|cart|rss|feed|tag|author|archive)(/|$)"
    r"|\.(jpg|jpeg|png|gif|svg|webp|css|js|zip|mp4|mp3|docx?|xlsx?|pptx?)$",
    re.IGNORECASE,
)

#: A programme page for the wrong level is not a match for this applicant.
_DEGREE_SLUGS: dict[str, tuple[str, ...]] = {
    "bachelor": ("bsc", "ba", "beng", "llb", "bachelor", "bachelors", "undergraduate"),
    "master": ("msc", "ma", "meng", "llm", "mba", "master", "masters", "graduate", "postgraduate"),
    "phd": ("phd", "doctoral", "doctorate", "dphil"),
    "foundation": ("foundation", "pre-bachelor", "preparatory"),
}


def registrable_domain(host_or_url: str) -> str:
    """The domain that owns a host, so "same site" is not a guess.

    ``www.rug.nl`` and ``rug.nl`` are the same institution; ``rug.nl`` and
    ``someoneelse.nl`` are not. Multi-part suffixes matter here: naively taking
    the last two labels would make every ``ac.uk`` site look like one domain.

    A full URL is accepted as well as a bare host. Callers hold homepages more
    often than hostnames, and the failure mode of not accepting one is silent:
    every comparison would answer "different institution" and discovery would
    quietly find nothing.
    """
    host = (host_or_url or "").strip().lower().rstrip(".")
    if not host:
        return ""
    if "/" in host or ":" in host:
        host = urlparse(host if "//" in host else f"//{host}").hostname or ""
        if not host:
            return ""
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if ".".join(labels[-2:]) in MULTIPART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def same_institution(url: str, domain: str) -> bool:
    """Whether a URL belongs to the institution that owns ``domain``."""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return bool(host) and registrable_domain(host) == registrable_domain(domain)


#: Query parameters that identify a referral rather than select content.
#: Matched against the parameter name — an earlier version matched the whole
#: "key=value" pair, so "utm_source=x" was kept and the same page was
#: discovered twice under two URLs.
_TRACKING_PARAM = re.compile(
    r"^(utm_[a-z_]*|fbclid|gclid|msclkid|dclid|mc_[a-z]+|ref|referrer|source"
    r"|igshid|_ga|yclid)$",
    re.IGNORECASE,
)


def canonical_url(url: str) -> str:
    """A stable form, so the same page is not discovered twice.

    Drops the fragment and tracking parameters, lowercases the host, removes a
    default port and a trailing slash. Query parameters that select content are
    kept — dropping them would merge genuinely different pages.
    """
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return url.strip()
    if not parts.scheme or not parts.netloc:
        return url.strip()

    host = (parts.hostname or "").lower()
    if parts.port and not (
        (parts.scheme == "http" and parts.port == 80)
        or (parts.scheme == "https" and parts.port == 443)
    ):
        host = f"{host}:{parts.port}"

    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    kept = [
        pair
        for pair in parts.query.split("&")
        if pair and not _TRACKING_PARAM.match(pair.split("=", 1)[0])
    ]
    return urlunparse((parts.scheme, host, path, "", "&".join(sorted(kept)), ""))


#: Paths that are about research rather than about studying a programme. A
#: research group's "BSc and MSc projects" page matched the ``/bsc|msc/`` rule
#: and was offered as the applicant's programme; a degree marker in a slug says
#: nothing about whether the page is a degree.
_NOT_A_PROGRAMME_PATH = re.compile(
    r"/(research|onderzoek|forschung|labs?|groups?|institutes?|centres?|centers?)/"
    r"|(projects?|thesis|theses|guidelines|internships?|vacancies|supervisors?)(/|$)",
    re.IGNORECASE,
)

#: A path segment that makes the page about money rather than about a course.
_FUNDING_SEGMENT = re.compile(
    r"/(scholarships?|bursary|bursaries|grants?|financial[-_]aid|funding|fellowships?"
    r"|beurzen|stipendien|apurahat|stypendia)(/|$)",
    re.IGNORECASE,
)


def score_url(url: str, category: str) -> int:
    """How strongly a URL looks like it belongs to a category. 0 means no."""
    path = (urlparse(url).path or "").lower()
    if _URL_EXCLUSIONS.search(path) or _NOT_A_PAGE_ABOUT_STUDYING.search(path):
        return 0
    if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG) and (
        _FUNDING_SEGMENT.search(path) or _NOT_A_PROGRAMME_PATH.search(path)
    ):
        # NTU offered a scholarship page as the applicant's programme (the
        # "undergraduate" in the path outscored the "scholarships" beside it),
        # and rug.nl offered a research group's "BSc and MSc projects" page.
        # Neither is a programme, whatever else the path says.
        return 0
    return sum(weight for pattern, weight in _URL_SIGNALS[category] if re.search(pattern, path))


def categorise_url(url: str) -> tuple[str | None, int]:
    """The category a URL best fits, and its score."""
    best: tuple[str | None, int] = (None, 0)
    for category in PageCategory.ALL:
        score = score_url(url, category)
        if score > best[1]:
            best = (category, score)
    return best


def matches_field(url: str, fields: list[str]) -> int:
    """Extra weight when a URL names one of the applicant's subjects.

    Weighted heavily on purpose. Every bachelor programme URL on a site scores
    the same on structure, so with a small bonus the three slots went to
    whichever programmes sorted first — Delft answered a computer science
    applicant with aerospace engineering, applied mathematics and applied
    physics. Subject match has to dominate structural match.
    """
    path = (urlparse(url).path or "").lower()
    bonus = 0
    for field_name in fields:
        for word in re.split(r"[^a-z]+", field_name.lower()):
            if len(word) > 3 and word in path:
                bonus += 8
    return bonus


def degree_level_named(url: str) -> str | None:
    """The degree level a URL names in its path, if it names one at all."""
    path = (urlparse(url).path or "").lower()
    for level, slugs in _DEGREE_SLUGS.items():
        if any(re.search(rf"(^|[/-]){re.escape(slug)}([/-]|$)", path) for slug in slugs):
            return level
    return None


#: A path segment that ends with a listing word. UBC's catalogue lives at
#: ``/applying-ubc/how-to-apply/degrees-programs/``, which scores higher as an
#: admissions page than as a catalogue — so whether a page is worth walking for
#: programmes is asked separately from which category it best fits.
_CATALOGUE_PATH = re.compile(
    r"/[a-z0-9-]*(programmes?|programs?|degrees?|courses?|studies)/?$", re.IGNORECASE
)


def looks_like_catalogue(url: str) -> bool:
    """Whether a URL looks like a page that lists programmes."""
    path = urlparse(url).path or ""
    if _URL_EXCLUSIONS.search(path):
        return False
    return bool(_CATALOGUE_PATH.search(path))


def matches_field_text(label: str, fields: list[str]) -> bool:
    """Whether a link's own text names one of the applicant's subjects.

    A catalogue page links to its programmes under the university's own names
    for them, and those names are often nowhere in the URL: Toronto's bachelor
    lead is ``/data-computer-science`` behind the text "Data & Computer
    Science", which no path pattern for "programmes" would ever match.
    """
    words = {w for w in re.split(r"[^a-z]+", label.lower()) if len(w) > 3}
    if not words:
        return False
    for field_name in fields:
        wanted = {w for w in re.split(r"[^a-z]+", field_name.lower()) if len(w) > 3}
        if wanted and wanted <= words:
            return True
    return False


def matches_degree(url: str, degree: str) -> int:
    """Positive when the URL names the right level, negative when it names another."""
    named = degree_level_named(url)
    if named is None:
        return 0
    return 4 if named == str(degree) else -6


def names_other_degree_level(url: str, degree: str) -> bool:
    """Whether a URL names a level the applicant did not ask for.

    Treated as an outright rejection rather than a score penalty. An MSc page
    is not a weak bachelor lead, it is the wrong page, and a subject-name bonus
    ("computer", "science") must not be able to outweigh the level.
    """
    named = degree_level_named(url)
    return named is not None and named != str(degree)


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

        while queue and len(trace.sitemaps_read) < MAX_SITEMAP_DOCUMENTS:
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
            candidate, trace = await self._discover_one(entry, profile)
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

        # 3. Navigation, when sitemaps and seeds did not reach a programme page.
        #    An earlier version fell back only when *nothing at all* was found,
        #    so a registry entry with an admissions seed suppressed the fallback
        #    and the run finished with no programme — which the live canary
        #    showed on six of ten sites.
        if not selected[PageCategory.PROGRAM_PAGE]:
            trace.used_navigation_fallback = True
            await self._navigation_fallback(entry, domain, selected, trace, profile)

        # 4. Confirm the programme candidates by reading them.
        #    URL shape alone cannot tell a programme from an open day: live runs
        #    offered "bachelor-open-day", "campus-tour", "webklassen" and a
        #    student newsletter as programme pages, all sitting under the same
        #    path as the real programmes. The classifier already knows the
        #    difference, so discovery asks it rather than guessing harder.
        await self._confirm_programs(selected, ranked, trace)

        trace.selected = {k: list(v) for k, v in selected.items() if v}
        self._apply(candidate, selected, profile, trace)
        return candidate, trace

    async def _confirm_programs(
        self,
        selected: dict[str, list[str]],
        ranked: dict[str, list[tuple[int, str]]],
        trace: DiscoveryTrace,
    ) -> None:
        """Keep only candidates a read of the page confirms is a programme."""
        queued = [*selected[PageCategory.PROGRAM_PAGE]]
        # Next-best candidates, so rejecting one does not mean finding nothing.
        for _score, url in sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True):
            if url not in queued:
                queued.append(url)

        confirmed: list[str] = []
        for url in queued[:MAX_PROGRAM_CANDIDATES_CHECKED]:
            if len(confirmed) >= MAX_PAGES_PER_CATEGORY:
                break
            result = await self.fetcher.get(url)
            if not result.ok:
                trace.reject(url, f"could not be read ({result.outcome.value})")
                continue
            page = classify_page(url=url, html=result.text)
            if page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM):
                confirmed.append(url)
            else:
                trace.reject(url, f"reads as {page.page_type.value}, not a programme page")

        if confirmed or selected[PageCategory.PROGRAM_PAGE]:
            # Only replace the list when something was actually checked; an
            # unreachable site keeps its leads rather than losing them silently.
            selected[PageCategory.PROGRAM_PAGE] = confirmed

    def _apply(
        self,
        candidate: Candidate,
        selected: dict[str, list[str]],
        profile: ApplicantProfileIn,
        trace: DiscoveryTrace,
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
        candidate.notes = f"Sitemap-first discovery found: {', '.join(found) or 'nothing'}." + (
            f" Not found: {', '.join(missing)}." if missing else ""
        )

    async def _navigation_fallback(
        self,
        entry: dict,
        domain: str,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Walk the catalogue's links, then the homepage's.

        A programme catalogue is the page a university builds precisely to list
        its programmes, so when discovery has one it is a far better place to
        look than the global menu. The homepage is the last resort.
        """
        degree = str(profile.context.level)
        fields = list(profile.context.intended_fields)
        # Catalogues first, deepest lead first; the homepage is the last resort
        # rather than a queue entry. Putting it in the queue let HKU's two
        # Chinese copies of the same catalogue consume the budget before the
        # walk reached the programme list.
        queue = list(selected[PageCategory.PROGRAM_CATALOG][:2])
        walked: set[str] = set()
        homepage_tried = False

        while len(walked) < MAX_FALLBACK_PAGES:
            if selected[PageCategory.PROGRAM_PAGE]:
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
            for url, label in _harvest_links(result.text, result.final_url or start, domain):
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
                    if score <= 0:
                        continue
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


def _harvest_links(html: str, base: str, domain: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
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
