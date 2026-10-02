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
from functools import lru_cache
from pathlib import Path
from typing import TypedDict
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from app.adapters.base import Candidate, CandidateProgram, PageOutcome
from app.adapters.fetching import Fetcher, same_source_site
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import (
    PageClassification,
    PageType,
    classify_page,
)
from app.adapters.search.ontology import canonical_field, load_ontology
from app.domain.enums import FetchOutcome
from app.domain.site_identity import hosts_share_site
from app.domain.site_identity import registrable_domain as site_domain
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
#: Whether step 7 re-judges the programme pages the search provider added.
#: Off: run 35721950650 measured recall 1/10 against 4/10 without it, and
#: precision fell too, so it removed correct pages rather than junk. Turn it
#: on only together with a capture that shows what it does.
CONFIRM_SEARCH_PROGRAMMES = False
#: Bounded content verification with backfill, unlike the older prune-only
#: experiment. Programme variants and unresolved degrees are rejected, and
#: matching catalogue links share the same candidate-read bound.
RECOVER_SEARCH_CANDIDATES = True
#: Whether search runs *before* the navigation fallback, and the fallback is
#: skipped when search found a programme page. Off: appending search after the
#: other generators is the measured default, and interleaving once cost whole
#: cases. Run 26 lost Groningen to ~50 navigation reads of faculty home pages
#: before search found the programme at once; this exists so that trade is
#: measured rather than argued. The benchmark harness flips it per capture.
SEARCH_BEFORE_NAVIGATION = False
#: Experiment ER-04, off until measured: a search candidate on a host that
#: already refused this run's fetcher outright (401/403, robots.txt
#: unreachable, stalled) does not take one of the programme-page slots.
#: The 2026-09-27 Toronto trace spent all three slots on future.utoronto.ca
#: after that host had answered 403 to every read; a reachable campus host
#: was never tried. The benchmark harness flips it per capture.
SKIP_REFUSED_SEARCH_HOSTS = False
#: Experiment ER-07, off until measured: one of the programme-page slots is
#: kept for the best candidate the navigation hop found. Search results fill
#: the others. ER-05 (2026-09-27) found hop candidates are appended after
#: search and never reach a slot, so KAIST's undergraduate-admission page,
#: linked from the department's own navigation, was never opened.
NAVIGATION_SLOT = False
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

#: Historical suffix coverage pinned by test_claim_verifier. Actual host
#: identity now uses the shared bundled PSL, including private hosting suffixes.
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
        "edu.kz",
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
    # One course's page is never a programme: Warsaw's catalogue answered a
    # computer science search with "Introduction to computer science I" (run 54).
    r"|/courses?/(view|details?)(/|$)"
    r"|\.(jpg|jpeg|png|gif|svg|webp|css|js|zip|mp4|mp3|docx?|xlsx?|pptx?)$",
    re.IGNORECASE,
)

#: A programme page for the wrong level is not a match for this applicant.
#: How a catalogue writes a degree level in a URL.
#:
#: The cycle forms matter as much as the words. Warsaw's catalogue writes its
#: bachelor as ``IN/S1-INF`` and its master as ``IN/S2-INF``, and with only the
#: word list a master's page reached the top of a bachelor search — the right
#: fact about the wrong population, which is exactly what the prefilter exists
#: to stop. ``S1``/``S2`` is Bologna cycle numbering, not a Warsaw quirk: it is
#: ``studia pierwszego/drugiego stopnia`` in Polish, ``I``/``II stopnia`` in
#: prose, "first cycle"/"second cycle" in English. A numeric convention defeats
#: a word list wherever it is used.
#:
#: Every slug here is matched on a path-segment boundary by
#: :func:`degree_level_named`, which is what makes a two-character slug like
#: ``s1`` safe to list.
_DEGREE_SLUGS: dict[str, tuple[str, ...]] = {
    "bachelor": (
        "bsc",
        "ba",
        "beng",
        "llb",
        "bachelor",
        "bachelors",
        "undergraduate",
        # Bologna first cycle
        "s1",
        "1st-cycle",
        "first-cycle",
        "i-stopnia",
        "licence",
        "licenciatura",
    ),
    "master": (
        "msc",
        "ma",
        "meng",
        "llm",
        "mba",
        "master",
        "masters",
        "graduate",
        "postgraduate",
        # Bologna second cycle
        "s2",
        "2nd-cycle",
        "second-cycle",
        "ii-stopnia",
        "magister",
        "mastere",
    ),
    "phd": ("phd", "doctoral", "doctorate", "dphil", "s3", "3rd-cycle", "third-cycle"),
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
    return site_domain(host_or_url)


def same_institution(url: str, domain: str) -> bool:
    """Whether a URL belongs to the institution that owns ``domain``."""
    try:
        scheme = urlparse(url).scheme
    except ValueError:
        return False
    if scheme not in ("http", "https"):
        return False
    return hosts_share_site(url, domain)


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
        # One field counts once, under whichever of its names the path uses.
        best = 0
        for name in with_strong_aliases([field_name]):
            words = {w for w in re.split(r"[^a-z]+", name.lower()) if len(w) > 3}
            best = max(best, 8 * sum(1 for w in words if w in path))
        bonus += best
    return bonus


@lru_cache(maxsize=64)
def _strong_aliases(field_name: str) -> tuple[str, ...]:
    key = canonical_field(field_name)
    if key is None:
        return ()
    concept = load_ontology().fields.get(key) or {}
    return tuple(concept.get("strong_aliases") or ())


def with_strong_aliases(fields: list[str]) -> list[str]:
    """The applicant's fields plus the ontology's strong aliases for each.

    Groningen calls its programme "Computing Science"; the ontology records that
    as the same field as "Computer Science", and discovery compared the words
    literally, so the programme page never scored as the applicant's subject.
    Only strong aliases: a related concept is never a match.
    """
    out: list[str] = []
    for field_name in fields:
        for name in (field_name, *_strong_aliases(field_name)):
            if name.lower() not in (o.lower() for o in out):
                out.append(name)
    return out


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


@lru_cache(maxsize=1)
def _registry_hosts_by_domain() -> dict[str, frozenset[str]]:
    """Registrable domain to the hosts this institution's verified seeds name.

    The registry records a homepage and seed URLs per institution, each
    carrying a ``seeds_verified_on`` date: human-checked data about a real
    university. That makes it the sanctioned place for institution-specific
    knowledge — the phase guide allows exactly this and forbids the
    alternative, a rule in code that knows something about one university.

    It answers a question nothing else in the pipeline could: which of an
    institution's many hosts actually publishes its programmes. Toronto's
    seeds name ``future.utoronto.ca``; ``utm.utoronto.ca`` and
    ``utsc.utoronto.ca`` are other campuses and are not named.
    """
    try:
        entries = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a broken registry is a deploy problem
        return {}

    by_domain: dict[str, set[str]] = {}
    for entry in entries:
        urls = [entry.get("homepage") or ""]
        urls += [u for u in (entry.get("seeds") or {}).values() if u]
        hosts = {h for h in (urlparse(u).hostname or "" for u in urls) if h}
        if not hosts:
            continue
        domain = registrable_domain(next(iter(hosts)))
        if domain:
            by_domain.setdefault(domain, set()).update(hosts)
    return {domain: frozenset(hosts) for domain, hosts in by_domain.items()}


def is_seed_host(url: str) -> bool:
    """Whether this URL sits on a host the institution's verified seeds name.

    ``www.`` is ignored on both sides: a registry that records ``www.rug.nl``
    is naming the same host as a search result on ``rug.nl``.
    """
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if not host:
        return False
    named = _registry_hosts_by_domain().get(registrable_domain(host), frozenset())
    return any(host == h.lower().removeprefix("www.") for h in named)


def is_excluded_path(url: str) -> bool:
    """Whether a URL is one of the pages a programme search never wants.

    News, events, vacancies, shops, logins and static media. Public because
    the search package applies the same rule to provider results, and a second
    copy of this list would drift from this one within a release.
    """
    return bool(_URL_EXCLUSIONS.search(urlparse(url).path or ""))


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
    own = {f.lower() for f in fields}
    for field_name in with_strong_aliases(fields):
        wanted = {w for w in re.split(r"[^a-z]+", field_name.lower()) if len(w) > 3}
        if not wanted or not wanted <= words:
            continue
        if field_name.lower() in own:
            return True
        # An alias names the field only when nothing else in the title names
        # another subject: "Informatics" is computer science, "Business
        # Informatics" is not, and "Computing and Data Science" is not
        # "Computing" (run 50, Vienna and HKU).
        if words - wanted <= _TITLE_FILLER:
            return True
    return False


def _distinct_fields(fields: list[str]) -> list[str]:
    """Keep applicant order while avoiding duplicate paid subject searches."""
    distinct: list[str] = []
    seen: set[str] = set()
    for raw in fields:
        field_name = raw.strip()
        key = field_name.casefold()
        if field_name and key not in seen:
            seen.add(key)
            distinct.append(field_name)
    return distinct


def _public_requested_fields(profile: ApplicantProfileIn, trace: DiscoveryTrace) -> list[str]:
    """Use only privacy-validated subjects for page matching and attribution.

    The search intent rejects profile-like text before sending it to a provider.
    The same boundary must hold for sitemap, navigation, and fetched-page
    identity; otherwise a rejected field could still become a claim or trace.
    """
    if trace.public_fields is None:
        from app.adapters.search.intent import _reject_applicant_data

        raw = list(profile.context.intended_fields)
        candidates = _distinct_fields(raw) if len(raw) > 1 else raw
        trace.public_fields = []
        for field_name in candidates:
            try:
                if not field_name.strip():
                    continue
                _reject_applicant_data("field", field_name)
            except ValueError:
                # QueryPrivacyError embeds the raw value. Never log it here.
                continue
            trace.public_fields.append(field_name)
    return trace.public_fields


def _field_named_by_subject(subject: str, fields: list[str]) -> str:
    """Name a requested field only when the fetched page's own subject does."""
    return next(
        (
            field_name
            for field_name in _distinct_fields(fields)
            if matches_field_text(subject, [field_name])
        ),
        "",
    )


#: Words a programme title carries besides its subject: level, form, and the
#: procedure notes Vienna appends ("with entrance exam procedure").
_TITLE_FILLER = frozenset(
    {
        "bachelor",
        "bachelors",
        "master",
        "masters",
        "degree",
        "programme",
        "program",
        "programmes",
        "programs",
        "hons",
        "honours",
        "honors",
        "with",
        "entrance",
        "exam",
        "procedure",
        "undergraduate",
        "study",
        "studies",
        "course",
        "english",
        "taught",
        "full",
        "time",
        "year",
        "years",
        "track",
        "major",
    }
)


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


def profile_rejects(
    page: PageClassification, requested_level: str, fields: list[str]
) -> str | None:
    """Why a fetched page is not this applicant's programme page, or ``None``.

    One predicate, shared by the confirm stage and the catalogue walker: the
    page has to read as a single programme, at the level the applicant asked
    for, in a subject they asked for. The strings are trace copy and are
    pinned by tests — change them only together with the tests.
    """
    if page.page_type not in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM):
        return f"reads as {page.page_type.value}, not a programme page"
    if page.degree_level and page.degree_level != requested_level:
        return f"page names degree level {page.degree_level}, not {requested_level}"
    if not fields:
        return "no privacy-safe requested subject to confirm"
    if not matches_field_text(page.subject or "", fields):
        return f"page subject {page.subject!r} does not match requested fields {fields!r}"
    return None


@dataclass
class DiscoveredUrl:
    url: str
    category: str
    score: int
    #: "manual_seed" | "sitemap" | "navigation"
    provenance: str
    note: str = ""


class WalkerTrace(TypedDict):
    """What the catalogue-walker stage did, as the trace reports it.

    Keys are frozen (T29 contract; T30 reads this): zeros when the walker was
    not triggered, so a report can distinguish "walked and found nothing" from
    "never walked".
    """

    catalogs_walked: int
    candidates: list[dict[str, object]]
    programs_confirmed: int
    outcomes: list[dict[str, str]]


def _walker_trace() -> WalkerTrace:
    return {"catalogs_walked": 0, "candidates": [], "programs_confirmed": 0, "outcomes": []}


#: Records one fetched page's metadata — the SourcePage.record field set, as
#: keyword arguments. Discovery never touches the database itself: it calls
#: this when a recorder is wired in, and what the recorder does with a page is
#: the runner's business (T32 reads these rows for freshness).
type PageRecorder = Callable[..., object]


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
    #: Safe search failures only; informational trace entries stay out of run.errors.
    search_failures: list[str] = field(default_factory=list)
    #: Query/slot limits are research limitations, not vendor outages.
    search_limitations: list[str] = field(default_factory=list)
    #: Fetched official programme subjects, keyed by canonical URL.
    field_sources: dict[str, dict[str, str]] = field(default_factory=dict)
    #: A search query's field for an unreadable lead; never source evidence.
    field_hints: dict[str, str] = field(default_factory=dict)
    #: Validated public fields only; internal, never serialised with the trace.
    public_fields: list[str] | None = None
    #: Subjects assigned a provider query in this run, for coverage accounting.
    queried_fields: list[str] = field(default_factory=list)
    search_coverage: dict[str, int] = field(default_factory=dict)
    used_navigation_fallback: bool = False
    #: (url, link text) for leads found by a catalogue's own wording rather
    #: than by the URL, so the report can show what the wording was.
    kept_by_link_text: list[tuple[str, str]] = field(default_factory=list)
    #: The catalogue-walker stage's report. Zeros until (and unless) the stage
    #: runs, so "inactive" and "ran and found nothing" stay distinguishable.
    walker: WalkerTrace = field(default_factory=_walker_trace)

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
            "search_failures": self.search_failures,
            "search_limitations": self.search_limitations,
            "field_sources": self.field_sources,
            "search_coverage": self.search_coverage,
            "used_navigation_fallback": self.used_navigation_fallback,
            "kept_by_link_text": self.kept_by_link_text,
            "walker": dict(self.walker),
        }


def _remember_field_source(
    trace: DiscoveryTrace,
    *,
    url: str,
    subject: str,
    fields: list[str],
    basis: str,
    source_url: str = "",
) -> None:
    """Retain which official page named the applicant's field."""
    matched = _field_named_by_subject(subject, fields)
    if matched:
        trace.field_sources[canonical_url(url)] = {
            "field": matched,
            "source_url": source_url or url,
            "subject": subject,
            "basis": basis,
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

        attempted_documents = 0
        while queue and attempted_documents < MAX_SITEMAP_DOCUMENTS:
            url, depth = queue.pop(0)
            url = canonical_url(url)
            if url in seen_documents or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_documents.add(url)

            if not same_institution(url, domain):
                trace.reject(url, "sitemap is off the institution's domain")
                continue

            attempted_documents += 1
            result = await self.fetcher.get(url)
            if not result.ok:
                trace.errors.append(f"{url}: {result.outcome.value} — {result.error}"[:300])
                if result.outcome == FetchOutcome.TOO_LARGE:
                    # A site-wide export exceeded the bounded page reader.
                    # More bulk siblings can exhaust the host's time budget
                    # before normal programme pages are tried (live Groningen).
                    trace.errors.append(
                        "Sitemap size budget reached; continuing with targeted discovery."
                    )
                    break
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "sitemap redirected off the institution's site")
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
        robots_url = urljoin(origin, "/robots.txt")
        result = await self.fetcher.get(robots_url)
        if not result.ok:
            trace.errors.append(f"robots.txt unavailable: {result.outcome.value}")
            return []
        if not same_source_site(robots_url, result.final_url or robots_url):
            trace.errors.append("robots.txt redirected off the institution's site")
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

    def __init__(
        self,
        fetcher: Fetcher,
        registry_path: Path | None = None,
        *,
        page_recorder: PageRecorder | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.registry_path = registry_path or REGISTRY_PATH
        self.sitemaps = SitemapReader(fetcher)
        #: Populated per run, so a caller can report why discovery found what it did.
        self.traces: list[DiscoveryTrace] = []
        #: Wired by the runner when fetched pages should feed source_pages
        #: (dormant while None — discovery runs byte-identically without it).
        self.page_recorder = page_recorder
        #: One outcome per walker-touched page, for the run's persisted report.
        self.walker_outcomes: list[PageOutcome] = []

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
        self.walker_outcomes = []
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
        fields = _public_requested_fields(profile, trace)
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
        searched_early = False
        if SEARCH_BEFORE_NAVIGATION and not selected[PageCategory.PROGRAM_PAGE]:
            await self._add_search_results(entry, domain, selected, trace, profile)
            searched_early = True
        if not selected[PageCategory.PROGRAM_PAGE]:
            trace.used_navigation_fallback = True
            await self._navigation_fallback(entry, domain, selected, trace, profile)

        # 4. Confirm the programme candidates by reading them.
        #    URL shape alone cannot tell a programme from an open day: live runs
        #    offered "bachelor-open-day", "campus-tour", "webklassen" and a
        #    student newsletter as programme pages, all sitting under the same
        #    path as the real programmes. The classifier already knows the
        #    difference, so discovery asks it rather than guessing harder.
        await self._confirm_programs(selected, ranked, trace, profile)
        await self._walk_catalogs(entry, selected, trace, profile)
        # The walker confirms its own candidates under the T29 contract, which
        # deliberately trusts a university's own catalogue listing — so the
        # snapshot is taken after it, and step 7 judges only what search adds.
        confirmed_so_far = set(selected[PageCategory.PROGRAM_PAGE])

        if not searched_early:
            await self._add_search_results(entry, domain, selected, trace, profile)

        # 7. Confirm what search added — built, and off until it is measured.
        #    Step 4 runs before search, so a programme page the provider
        #    contributes reaches the candidate unconfirmed. Applying the
        #    step-4 predicate to those pages *looked* obviously right and the
        #    first live run said otherwise: programme-page recall fell 4/10 →
        #    1/10 and precision fell with it, so it cut correct pages and kept
        #    junk. The predicate is wrong for search-sourced pages in a way I
        #    cannot yet name, and a rule that removes evidence has to earn its
        #    place with a number, not an argument.
        if CONFIRM_SEARCH_PROGRAMMES:
            await self._confirm_added_programs(selected, confirmed_so_far, trace, profile)

        trace.selected = {k: list(v) for k, v in selected.items() if v}
        self._apply(candidate, selected, profile, trace)
        return candidate, trace

    async def _confirm_programs(
        self,
        selected: dict[str, list[str]],
        ranked: dict[str, list[tuple[int, str]]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Keep only programme pages that match the requested level and subject."""
        queued = [*selected[PageCategory.PROGRAM_PAGE]]
        # Next-best candidates, so rejecting one does not mean finding nothing.
        for _score, url in sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True):
            if url not in queued:
                queued.append(url)

        confirmed: list[str] = []
        requested_level = str(profile.context.level)
        fields = _public_requested_fields(profile, trace)
        for url in queued[:MAX_PROGRAM_CANDIDATES_CHECKED]:
            if len(confirmed) >= MAX_PAGES_PER_CATEGORY:
                break
            result = await self.fetcher.get(url)
            if not result.ok:
                trace.reject(url, f"could not be read ({result.outcome.value})")
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "programme redirected off the institution's site")
                continue
            page = classify_page(url=result.final_url or url, html=result.text)
            reason = profile_rejects(page, requested_level, fields)
            if reason is not None:
                trace.reject(url, reason)
                continue
            confirmed.append(url)
            if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                _remember_field_source(
                    trace,
                    url=url,
                    subject=page.subject or "",
                    fields=fields,
                    basis="classified_programme_page",
                    source_url=result.final_url or url,
                )

        if confirmed or selected[PageCategory.PROGRAM_PAGE]:
            # Only replace the list when something was actually checked; an
            # unreachable site keeps its leads rather than losing them silently.
            selected[PageCategory.PROGRAM_PAGE] = confirmed

    async def _confirm_added_programs(
        self,
        selected: dict[str, list[str]],
        already_confirmed: set[str],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Apply the step-4 filter to the programme pages search added.

        The same question step 4 asks: does this page describe a programme at
        the requested level in a requested field? A page that cannot be read
        is kept rather than dropped — an unreachable page is not a refusal.

        The catalogue walker's own candidates are not re-judged here; it
        confirms them under the T29 contract, which deliberately trusts a
        university's own catalogue listing.
        """
        newcomers = [
            url for url in selected[PageCategory.PROGRAM_PAGE] if url not in already_confirmed
        ]
        if not newcomers:
            return

        requested_level = str(profile.context.level)
        fields = _public_requested_fields(profile, trace)
        refused: set[str] = set()
        # Anything past the cap stays unconfirmed rather than being dropped:
        # losing a lead unread is the worse failure, and MAX_PAGES_PER_CATEGORY
        # keeps `selected` far below this in practice. If that ever changes,
        # this is the line that decides which way the doubt falls.
        for url in newcomers[:MAX_PROGRAM_CANDIDATES_CHECKED]:
            result = await self.fetcher.get(url)
            if not result.ok:
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "programme redirected off the institution's site")
                refused.add(url)
                trace.field_sources.pop(canonical_url(url), None)
                continue
            page = classify_page(url=result.final_url or url, html=result.text)
            reason = profile_rejects(page, requested_level, fields)
            if reason is not None:
                trace.reject(url, reason)
                refused.add(url)
                trace.field_sources.pop(canonical_url(url), None)
            elif len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                _remember_field_source(
                    trace,
                    url=url,
                    subject=page.subject or "",
                    fields=fields,
                    basis="classified_programme_page",
                    source_url=result.final_url or url,
                )

        if refused:
            selected[PageCategory.PROGRAM_PAGE] = [
                url for url in selected[PageCategory.PROGRAM_PAGE] if url not in refused
            ]

    async def _walk_catalogs(
        self,
        entry: dict,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Read the catalogue itself for the programmes the earlier stages missed.

        The navigation fallback only reaches a few links on a catalogue, and a
        JS-rendered catalogue has no links in its HTTP body at all. The walker
        scores every link the page offers (and the JSON its page fetches, when
        a catalogue renderer is attached) and reads the strongest ones — but
        only when the confirm stage left room, and never beyond the per-category
        cap, so `_apply` sees at most what it always saw.
        """
        # Deferred: catalog_walker imports this module's URL helpers, so the
        # dependency points one way at import time (walker -> discovery).
        from app.adapters.discovery.catalog_walker import (
            TRACE_CANDIDATE_CAP,
            TRACE_OUTCOME_CAP,
            WALKER_MAX_CATALOGS,
            CatalogWalker,
        )

        if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
            return
        catalogues = list(selected[PageCategory.PROGRAM_CATALOG][:WALKER_MAX_CATALOGS])
        if not catalogues and trace.used_navigation_fallback:
            # The navigation fallback owns the homepage: when it ran and found
            # no catalogue anywhere, the homepage is the walk's last root.
            # When the fallback never ran, something was already found and the
            # walk would only repeat its work.
            homepage = entry.get("homepage")
            if homepage:
                catalogues = [homepage]
        if not catalogues:
            return

        walker = CatalogWalker(
            fetcher=self.fetcher,
            domain=trace.domain,
            degree=str(profile.context.level),
            fields=_public_requested_fields(profile, trace),
            page_recorder=self.page_recorder,
        )
        try:
            walks = await walker.walk(catalogues[:WALKER_MAX_CATALOGS])
        except Exception as exc:  # a walker failure must not end discovery
            trace.errors.append(f"catalog walker failed: {type(exc).__name__}: {exc}"[:300])
            return

        for walk in walks:
            trace.walker["catalogs_walked"] += 1
            trace.walker["programs_confirmed"] += len(walk.confirmed)
            for link in walk.candidates:
                if len(trace.walker["candidates"]) >= TRACE_CANDIDATE_CAP:
                    break
                trace.walker["candidates"].append(
                    {
                        "url": link.url,
                        "label": link.label,
                        "score": link.score,
                        "source": link.source,
                    }
                )
            for url, outcome in walk.outcomes:
                if len(trace.walker["outcomes"]) >= TRACE_OUTCOME_CAP:
                    break
                trace.walker["outcomes"].append({"url": url, "outcome": outcome})
                self.walker_outcomes.append(
                    PageOutcome(url=url, category="catalog-walker", detail=outcome)
                )
            for url in walk.confirmed:
                if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
                    break
                if url not in selected[PageCategory.PROGRAM_PAGE]:
                    selected[PageCategory.PROGRAM_PAGE].append(url)
                    if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                        _remember_field_source(
                            trace,
                            url=url,
                            subject=walk.confirmed_subjects.get(url, ""),
                            fields=_public_requested_fields(profile, trace),
                            basis="classified_programme_page",
                        )

    async def _add_search_results(
        self,
        entry: dict,
        domain: str,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Add programme pages a web search found, if one is configured.

        **Dormant unless a provider is set.** `UNIMATCH_SEARCH_PROVIDER`
        defaults to `none`, the factory raises, and this returns having done
        nothing — so a deployment without a key behaves byte-identically to
        before. Same pattern as ``page_recorder`` above.

        **Appended, never interleaved.** Whatever the sitemap and the walker
        found keeps its place; search only adds pages they missed. The
        alternative was measured and cost whole cases; the write-up lives with
        the benchmark tooling, which production deliberately cannot name — a
        guard test rejects any path to it from this package, docstrings
        included.

        A provider failure degrades this run rather than ending it: discovery
        keeps everything the other generators produced.
        """
        from app.adapters.search import SearchError, get_search_provider
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DiscoveryIntent
        from app.adapters.search.retrieval import discover_candidates

        try:
            provider = get_search_provider()
        except SearchError:
            return

        fields = list(profile.context.intended_fields)
        if not fields:
            return
        if len(_distinct_fields(fields)) > 1:
            await self._add_multi_field_search_results(
                entry, domain, selected, trace, profile, provider
            )
            return

        try:
            intent = DiscoveryIntent(
                institution=entry["name"],
                # The institution, not the host its homepage sits on: Warsaw's
                # registry homepage is en.uw.edu.pl and its programme catalogue
                # is informatorects.uw.edu.pl, so a host filter kept search on
                # the news pages (run 53).
                domain=registrable_domain(domain) or domain,
                degree=profile.context.level,
                field=fields[0],
            )
        except ValueError:
            # A registry entry or a field the intent refuses — for instance one
            # carrying something that looks like applicant data. Skip search for
            # this institution rather than sending it.
            trace.errors.append("search skipped: invalid public discovery intent")
            return

        async def read(url: str) -> str:
            # The adapter's own Fetcher, so robots, rate limits, the PII guard
            # and the SSRF protections apply exactly as they do everywhere else.
            result = await self.fetcher.get(url)
            return (
                result.text if result.ok and same_source_site(url, result.final_url or url) else ""
            )

        try:
            report = await discover_candidates(provider, intent, fetch=read, top_k=10)
        except SearchError as exc:
            trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
            return

        trace.search_failures.extend(report.failure_diagnostics)
        pages = selected[PageCategory.PROGRAM_PAGE]
        if RECOVER_SEARCH_CANDIDATES:
            await self._recover_search_pages(report.candidates, pages, trace, profile)
            trace.errors.append(
                f"search identity recovery via {report.provider}; queries {len(report.queries_run)}, "
                f"failed {len(report.failed_queries)}, rejected {dict(report.rejection_counts)}"
            )
            return
        added = 0
        refused = getattr(self.fetcher, "refused_hosts", {})
        skipped: list[str] = []
        navigation = next(
            (c for c in report.candidates if c.provider == "navigation" and c.url not in pages),
            None,
        )
        limit = MAX_PAGES_PER_CATEGORY - (1 if NAVIGATION_SLOT and navigation else 0)
        for found in report.candidates:
            if len(pages) >= limit:
                break
            if found.url in pages:
                continue
            if SKIP_REFUSED_SEARCH_HOSTS and (urlparse(found.url).hostname or "") in refused:
                skipped.append(found.url)
                continue
            pages.append(found.url)
            added += 1
        if NAVIGATION_SLOT and navigation is not None and navigation.url not in pages:
            pages.append(navigation.url)
            added += 1
            trace.errors.append(f"navigation slot: {navigation.url}")
        if skipped:
            trace.errors.append(
                f"search skipped {len(skipped)} candidate(s) on hosts that refused this run: "
                + ", ".join(skipped)[:400]
            )
        # Which pages search offered, so a miss can be told apart from
        # "search never saw the programme" (run 46, Warsaw).
        offered = ", ".join(c.url for c in report.candidates[:5]) or "none"
        trace.errors.append(
            (
                f"search added {added} programme page(s) via {report.provider}"
                if added
                else f"search added nothing via {report.provider}"
            )
            + f"; offered: {offered}"[:600]
            + f"; queries {len(report.queries_run)}, failed {len(report.failed_queries)}"
            + f", rejected {dict(report.rejection_counts)}"[:300]
        )

    async def _add_multi_field_search_results(
        self, entry, domain, selected, trace, profile, provider
    ) -> None:
        """Search distinct subjects under one institution-wide paid/read budget."""
        from app.adapters.search import SearchError
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DEFAULT_QUERY_BUDGET, DiscoveryIntent
        from app.adapters.search.retrieval import DEFAULT_HOP_ENTRY_POINTS, discover_candidates

        fields = _distinct_fields(list(profile.context.intended_fields))
        public_fields = _public_requested_fields(profile, trace)
        skipped = len(fields) - len(public_fields)
        intents = []
        for field_name in public_fields:
            try:
                intents.append(
                    DiscoveryIntent(
                        institution=entry["name"],
                        domain=registrable_domain(domain) or domain,
                        degree=profile.context.level,
                        field=field_name,
                    )
                )
            except ValueError:
                # A registry value can also fail public-query validation;
                # sitemap and catalogue matching still use the safe field.
                continue
        if skipped:
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: {skipped} requested subject(s) "
                "failed query privacy validation and were not searched."
            )
        chosen = intents[:DEFAULT_QUERY_BUDGET]
        trace.queried_fields = [intent.field for intent in chosen]
        if len(intents) > len(chosen):
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: {len(chosen)} of "
                f"{len(fields)} requested subjects were queried; "
                f"{len(intents) - len(chosen)} were not searched because of the "
                "six-query budget. Search remaining subjects in a separate run."
            )
        if len(fields) > MAX_PAGES_PER_CATEGORY:
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: up to "
                f"{MAX_PAGES_PER_CATEGORY} programmes can be shown per university, "
                "so not every requested subject can appear in this run."
            )
        trace.search_coverage = {
            "requested": len(fields),
            "queried": len(chosen),
            "represented": 0,
        }
        if not chosen:
            return

        query_budgets = [1] * len(chosen)
        for slot in range(DEFAULT_QUERY_BUDGET - len(chosen)):
            query_budgets[slot % len(chosen)] += 1
        hop_budgets = [0] * len(chosen)
        for slot in range(DEFAULT_HOP_ENTRY_POINTS):
            hop_budgets[slot % len(chosen)] += 1

        async def read(url: str) -> str:
            result = await self.fetcher.get(url)
            return (
                result.text if result.ok and same_source_site(url, result.final_url or url) else ""
            )

        reports = []
        query_count = 0
        failed_count = 0
        rejection_counts: dict[object, int] = {}
        for intent, query_budget, hop_budget in zip(
            chosen, query_budgets, hop_budgets, strict=True
        ):
            try:
                report = await discover_candidates(
                    provider,
                    intent,
                    query_budget=query_budget,
                    fetch=read,
                    hop_entry_points=hop_budget,
                    top_k=10,
                )
            except SearchError as exc:
                trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
                continue
            reports.append((intent.field, report))
            trace.search_failures.extend(report.failure_diagnostics)
            query_count += len(report.queries_run)
            failed_count += len(report.failed_queries)
            for reason, count in report.rejection_counts.items():
                rejection_counts[reason] = rejection_counts.get(reason, 0) + count

        # A previously confirmed sitemap/walker page already occupies a slot.
        # Give an as-yet-unrepresented field first access to the remaining
        # slots, while keeping each report's own rank order.
        represented_before = {
            trace.field_sources.get(canonical_url(url), {}).get("field", "")
            for url in selected[PageCategory.PROGRAM_PAGE]
        }
        reports.sort(key=lambda item: item[0] in represented_before)

        # Scores are relative to one field's intent, so preserve per-field
        # ranking and take turns rather than comparing scores across fields.
        merged = []
        seen: set[str] = set()
        longest = max((len(report.candidates) for _, report in reports), default=0)
        for rank in range(longest):
            for field_name, report in reports:
                if rank >= len(report.candidates):
                    continue
                found = report.candidates[rank]
                key = canonical_url(found.url)
                if key in seen:
                    continue
                seen.add(key)
                trace.field_hints[key] = field_name
                merged.append(found)

        pages = selected[PageCategory.PROGRAM_PAGE]
        if RECOVER_SEARCH_CANDIDATES:
            await self._recover_search_pages(merged, pages, trace, profile)
            trace.errors.append(
                f"search identity recovery via {provider.name}; queries {query_count}, "
                f"failed {failed_count}, rejected {rejection_counts}"
            )
            return
        added = 0
        refused = getattr(self.fetcher, "refused_hosts", {})
        skipped_hosts: list[str] = []
        navigation = next(
            (c for c in merged if c.provider == "navigation" and c.url not in pages), None
        )
        limit = MAX_PAGES_PER_CATEGORY - (1 if NAVIGATION_SLOT and navigation else 0)
        for found in merged:
            if len(pages) >= limit:
                break
            if found.url in pages:
                continue
            if SKIP_REFUSED_SEARCH_HOSTS and (urlparse(found.url).hostname or "") in refused:
                skipped_hosts.append(found.url)
                continue
            pages.append(found.url)
            added += 1
        if NAVIGATION_SLOT and navigation is not None and navigation.url not in pages:
            pages.append(navigation.url)
            added += 1
            trace.errors.append(f"navigation slot: {navigation.url}")
        if skipped_hosts:
            trace.errors.append(
                f"search skipped {len(skipped_hosts)} candidate(s) on hosts that refused this run: "
                + ", ".join(skipped_hosts)[:400]
            )
        offered = ", ".join(c.url for c in merged[:5]) or "none"
        trace.errors.append(
            f"search added {added} programme page(s) via {provider.name}; offered: {offered}"[:600]
            + f"; queries {query_count}, failed {failed_count}, rejected {rejection_counts}"[:300]
        )

    async def _recover_search_pages(self, candidates, pages, trace, profile) -> None:
        """Fill programme slots from fetched identities rather than search snippets.

        Existing confirmed catalogue/sitemap pages stay first. A rejected lead
        frees a slot for the next search result. The legacy single-field path
        keeps host failures as unresolved leads; a multi-field result requires
        source-backed field identity before it can become a programme.
        """
        from app.adapters.discovery.catalog_walker import extract_links, score_link
        from app.adapters.extraction import html_to_text
        from app.adapters.requirements.web_requirements import (
            _LISTING_PAGE_TYPES,
            _listed_programme,
        )

        fields = _public_requested_fields(profile, trace)
        multi_requested = len(_distinct_fields(list(profile.context.intended_fields))) > 1
        level = str(profile.context.level)
        pending: list[str] = []
        queue = list(candidates)
        visited = set(pages)
        checked = 0
        added = 0
        while queue:
            if len(pages) >= MAX_PAGES_PER_CATEGORY or checked >= MAX_PROGRAM_CANDIDATES_CHECKED:
                break
            found = queue.pop(0)
            if found.url in visited:
                continue
            visited.add(found.url)
            checked += 1
            result = await self.fetcher.get(found.url)
            if not result.ok:
                pending.append(found.url)
                trace.reject(found.url, f"search lead unresolved ({result.outcome.value})")
                continue
            if not same_source_site(found.url, result.final_url or found.url):
                trace.reject(found.url, "search lead redirected off the institution's site")
                continue
            page = classify_page(url=result.final_url or found.url, html=result.text)
            reason = profile_rejects(page, level, fields)
            stated_level = page.degree_level
            matched_subject = page.subject or ""
            basis = "classified_programme_page"
            if reason is not None and page.page_type in _LISTING_PAGE_TYPES:
                if multi_requested:
                    # A search title is an unverified hint. It can name an
                    # unrelated degree on an otherwise official listing.
                    listed = None
                    for field_name in _distinct_fields(fields):
                        program = CandidateProgram(
                            name=field_name,
                            field=field_name,
                            degree=profile.context.level,
                            url=found.url,
                        )
                        candidate_title = _listed_programme(html_to_text(result.text), program)
                        if candidate_title and matches_field_text(candidate_title[0], [field_name]):
                            listed = candidate_title
                            break
                else:
                    program = CandidateProgram(
                        name=found.title,
                        field=fields[0] if fields else "",
                        degree=profile.context.level,
                        url=found.url,
                    )
                    listed = _listed_programme(html_to_text(result.text), program)
                if listed is not None:
                    reason = None
                    stated_level = listed[1]
                    matched_subject = listed[0]
                    basis = "full_degree_title_on_listing"
            if reason is None:
                if stated_level != level:
                    reason = "page does not state the requested degree level"
                variants = re.findall(
                    r"\b(?:teacher (?:education|training)|teaching (?:education|subject)"
                    r"|digital literacy|minor|certificate|speciali[sz]ations?|second major"
                    r"|double degree|final examination|final exam|degree plans?"
                    r"|courses? for teachers?|recommended path|why computer science)\b",
                    (page.subject or "") + " " + urlparse(found.url).path.replace("-", " "),
                    flags=re.I,
                )
                if any(not any(v.lower() in f.lower() for f in fields) for v in variants):
                    reason = (
                        "page names an alternate programme variant not requested: "
                        + ", ".join(variants)
                    )
            if reason is not None:
                trace.reject(found.url, reason)
                if page.page_type in _LISTING_PAGE_TYPES:
                    # A search result can be the catalogue, not its detail
                    # page. Follow its own matching links before trying more
                    # search noise, sharing the same overall read bound.
                    from app.adapters.search.retrieval import RankedCandidate

                    leads = []
                    for link in extract_links(result.text, found.url, trace.domain):
                        value = score_link(link.url, link.label, level, fields)
                        if value is None or not matches_field_text(link.label, fields):
                            continue
                        if link.url not in visited:
                            leads.append(
                                RankedCandidate(link.url, link.label, value, "search-catalogue")
                            )
                    leads.sort(key=lambda lead: (-lead.score, lead.url))
                    followups = leads[: MAX_PROGRAM_CANDIDATES_CHECKED - checked]
                    if multi_requested:
                        # Another requested field's direct search result is
                        # already waiting. Do not let one catalogue's many
                        # links consume the shared read cap ahead of it.
                        queue.extend(followups)
                    else:
                        queue[:0] = followups
                continue
            pages.append(found.url)
            added += 1
            if multi_requested:
                _remember_field_source(
                    trace,
                    url=found.url,
                    subject=matched_subject,
                    fields=fields,
                    basis=basis,
                    source_url=result.final_url or found.url,
                )
        # Preserve the legacy single-field lead fallback. In a multi-field
        # run, a search title cannot establish which subject an unreadable
        # page actually covers, so keep the failure only in diagnostics.
        if not pages and not multi_requested:
            pages.extend(pending[:MAX_PAGES_PER_CATEGORY])
        if multi_requested and pending:
            trace.search_limitations.append(
                f"Search coverage limited at {trace.institution}: "
                f"{len(pending)} programme lead(s) could not be read, so their "
                "subjects were not confirmed from the source page."
            )
        trace.errors.append(f"search identity recovery: checked {checked}, confirmed {added}")

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

        fields = _public_requested_fields(profile, trace)
        for url in selected[PageCategory.PROGRAM_PAGE][:MAX_PAGES_PER_CATEGORY]:
            if profile.context.intended_fields and not fields:
                break
            field_name = fields[0] if fields else ""
            program_name = _program_name_from_url(url, fields, profile.context.level)
            if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                source = trace.field_sources.get(canonical_url(url), {})
                field_name = (
                    source.get("field") or trace.field_hints.get(canonical_url(url)) or field_name
                )
                # A curriculum slug can name its matriculation year rather
                # than its degree. Retain the already fetched programme
                # subject so downstream verification checks the same identity.
                program_name = source.get("subject") or program_name
            candidate.programs.append(
                CandidateProgram(
                    name=program_name,
                    field=field_name,
                    degree=profile.context.level,
                    url=url,
                )
            )
        if trace.search_coverage:
            queried_fields = set(trace.queried_fields)
            represented = {
                trace.field_sources[canonical_url(program.url)]["field"]
                for program in candidate.programs
                if program.url
                and canonical_url(program.url) in trace.field_sources
                and trace.field_sources[canonical_url(program.url)]["field"] in queried_fields
            }
            trace.search_coverage["represented"] = len(represented)
            if len(candidate.programs) >= MAX_PAGES_PER_CATEGORY and len(represented) < min(
                trace.search_coverage["queried"], MAX_PAGES_PER_CATEGORY
            ):
                trace.search_limitations.append(
                    f"Search coverage limited at {trace.institution}: all "
                    f"{MAX_PAGES_PER_CATEGORY} programme slots are filled; "
                    f"only {len(represented)} of {trace.search_coverage['queried']} "
                    "queried subjects have source-confirmed programme pages. "
                    "Search remaining subjects in a separate run."
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
        fields = _public_requested_fields(profile, trace)
        # Catalogues first, deepest lead first; the homepage is the last resort
        # rather than a queue entry. Putting it in the queue let HKU's two
        # Chinese copies of the same catalogue consume the budget before the
        # walk reached the programme list.
        queue = list(selected[PageCategory.PROGRAM_CATALOG][:2])
        walked: set[str] = set()
        scores: dict[str, int] = {}
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
            if not same_source_site(start, result.final_url or start):
                trace.reject(start, "navigation page redirected off the institution's site")
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
                if canonical in selected[category]:
                    continue
                if len(selected[category]) < MAX_PAGES_PER_CATEGORY:
                    selected[category].append(canonical)
                    scores[canonical] = score
                    continue
                # Keep the strongest leads, not the first ones. Vienna's
                # bachelor list names "Bachelor Programmes by Topic", African
                # Studies and Egyptology before Computer Science, and the
                # three slots were gone by the time the applicant's subject
                # came up. Only leads this walk scored can be displaced: a
                # seed or a sitemap pick stays.
                ours = [u for u in selected[category] if u in scores]
                if not ours:
                    continue
                weakest = min(ours, key=lambda u: scores[u])
                if score > scores[weakest]:
                    selected[category][selected[category].index(weakest)] = canonical
                    del scores[weakest]
                    scores[canonical] = score


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
    soup = parse_html(html)
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


def registry_campuses(domain: str) -> dict[str, list[str]]:
    """Campus name to its hosts, for the institution on this registrable domain.

    Verified registry data (``campuses``); empty when the registry records none.
    """
    try:
        entries = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a broken registry is a deploy problem
        return {}
    target = registrable_domain(domain)
    for entry in entries:
        if not entry.get("campuses"):
            continue
        if registrable_domain(urlparse(entry.get("homepage") or "").hostname or "") == target:
            return {c["name"]: list(c["hosts"]) for c in entry["campuses"]}
    return {}
