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
import statistics
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from html import unescape as html_unescape
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict
from urllib.parse import unquote, urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from app.adapters import page_classifier as _page_classifier
from app.adapters.base import Candidate, CandidateProgram, PageOutcome
from app.adapters.fetching import Fetcher, FetchResult, same_source_site
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import (
    PageClassification,
    PageType,
    classify_page,
)
from app.adapters.search.ontology import canonical_field, load_ontology, localized_aliases
from app.domain.enums import FetchOutcome
from app.domain.site_identity import hosts_share_site
from app.domain.site_identity import registrable_domain as site_domain
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RankingEntry

if TYPE_CHECKING:  # pragma: no cover - the seam is only needed as an annotation
    from app.adapters.search.base import SearchProvider

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
#: QB-1b: identity-recovery reads left to QB-1's first pass when a programme
#: page was already confirmed before it (walker, registry or sitemap). Recovery
#: then only looks for a twin or sibling of that page; Groningen's ``?lang=en``
#: twin was the first check in every run, and checks 4-8 were staff pages.
PRECONFIRMED_RECOVERY_CHECKS = 3
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
#: Plan rule SO-1 (discovery analysis 2026-10-17 §0 #2, §1.4), off until a
#: paired run passes. Search costs no page read, yet it ran after sitemaps,
#: navigation, confirm and the walker; on a slow host the clock ended first
#: (METU: Crawl-delay 10 s, every read ~10 s, ``search_calls = 0`` in 8/8
#: repetitions). On: search runs before navigation and confirm when sitemaps
#: produced no programme candidate, or when the host is slow — robots.txt asks
#: a crawl delay of at least SLOW_HOST_SECONDS, or the median of the first
#: three reads is at least that long. A slow host also reads at most
#: SLOW_HOST_SITEMAP_DOCUMENTS sitemap documents and skips the walker. Order
#: only: the confirm predicate is unchanged. The trace records ``stage_order``.
#: The benchmark harness flips it per capture (``--cost-aware-search-order``).
COST_AWARE_SEARCH_ORDER = False
#: SO-1: a crawl delay or a median read at least this long makes a host slow.
SLOW_HOST_SECONDS = 5.0
#: SO-1: sitemap documents a slow host is asked for, robots.txt not counted.
SLOW_HOST_SITEMAP_DOCUMENTS = 3
#: SO-1: reads timed for the median.
SLOW_HOST_SAMPLE_READS = 3
#: SO-1's clock, a module attribute so a test can replace it.
_clock = time.monotonic
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
#: Experiment ER-09 (expert trace 2026-10-04), on since paired runs 37240128388
#: and 37242447357 (owner approved 2026-10-05); False turns it off.
#: When the applicant named a subject, the navigation fallback takes a link as
#: a programme lead only if its URL or its own text names that subject.
#: Groningen's bachelor hub links brochures, open days, campus tours and
#: "webklassen" under the same path as its programmes; they filled every
#: programme slot, the confirm stage spent its reads rejecting them, and the
#: run timed out before reaching /bachelors/computing-science.
NAVIGATION_FIELD_LEADS = True
#: Pages walked during the navigation fallback. Universities routinely nest
#: "Degree programmes" -> "Bachelor programmes" -> a programme, so one hop is
#: not enough; an unbounded walk would be a crawl.
MAX_FALLBACK_PAGES = 5

#: Plan rule SM-1 (discovery analysis 2026-10-17 §0 #1, §1.3–§1.5), off until a
#: paired run passes. The sitemap stage read index children in file order under
#: the MAX_SITEMAP_DOCUMENTS cap and probed every conventional location even
#: after one answered: NU's index lists post-sitemap1..24 before its page and
#: sprogram sitemaps, so eleven post sitemaps (75 s) used the cap and the
#: programme sitemap was never read; METU and Charles spent three reads (30 s
#: at Crawl-delay 10) on guaranteed 404s after /sitemap.xml had answered. On:
#: the probing stops at the first conventional location that parses to a
#: sitemap, and an index's children are read programme/study/course/page
#: first and news/post/event last, the last group skipped when the first
#: group alone fills the remaining cap. Read order only — every URL still
#: passes ``keep()`` and the confirm classifier. The benchmark harness flips it
#: per capture (``--sitemap-child-priority``).
SITEMAP_CHILD_PRIORITY = False
#: SM-1: an index child whose name says it lists programmes or static pages.
_SITEMAP_CHILD_FIRST = re.compile(r"program|programme|stud(?:y|ies)|course|degree|page|curricul")
#: SM-1: an index child whose name says it lists dated or taxonomy content.
#: Matched as a whole name token, so ``postgraduate`` is not ``post``.
_SITEMAP_CHILD_LAST = re.compile(
    r"(?<![a-z])(?:posts?|news|events?|announce\w*|blogs?|press|media|calendars?|tags?|authors?)"
    r"(?![a-z])"
)

#: Plan rule LI-1 (discovery analysis 2026-10-17 §0 #4, §1.2, §4 rule 4), off
#: until a paired run passes. URL scoring and field matching were English-only:
#: TUM's sitemap lists only ``/studium/studienangebot/detail/informatik-bachelor-
#: of-science-bsc`` and it scored zero, the page subject "Informatik" was
#: rejected although the ontology records ``informatik`` as computer science,
#: Polimi's ``laurea-magistrale`` was not a degree slug, and nothing followed a
#: local-language page to its English twin. On: (i) ``with_strong_aliases``
#: also returns the ontology's localized aliases (including the entries marked
#: ``"flag": "LOCALIZED_IDENTITY"``), a few local programme-path words score as
#: programme pages, and ``degree_level_named`` knows the local degree words
#: whose level is certain (``_LOCALIZED_DEGREE_SLUGS``); (ii)
#: ``matches_field_text`` accepts a localized alias as the subject under the
#: same filler rule, so "Informatik" is computer science and
#: "Wirtschaftsinformatik" is not; (iii) a programme candidate read on the
#: institution's domain whose ``<html lang>`` is not English and that carries
#: ``<link rel="alternate" hreflang="en…">`` on the same registrable domain has
#: that alternate read once — through the Fetcher, inside the same read cap —
#: and classified like any page, beside the original. The benchmark harness
#: flips it per capture (``--localized-identity``).
#: On since paired runs 39068981447 (cohort, no change) and 39068982766 (dev2:
#: Paris-Saclay's licence informatique page found in every on repetition, never
#: off); owner delegation 2026-10-17. False turns it off.
LOCALIZED_IDENTITY = True
#: Plan rule DI-1 (evidence analysis 2026-10-17 §0 #5, §4 rank 5), off until a
#: paired run passes. Institution identity was one registrable domain, and
#: every official-domain reader — ``same_institution`` here and in the walker
#: (``off_domain``), ``is_official_domain``, ``verification_domains``, topic and
#: award search — rejected a university whose international admissions run on a
#: second one: Tsinghua publishes its deadline, fees and freshman scholarships on
#: ``international.join-tsinghua.edu.cn``, which ``www.tsinghua.edu.cn`` links
#: from its own admissions navigation (3 dev2 questions lost). On: discovery
#: reads the registry homepage once after the sitemaps (the disk cache serves
#: the navigation fallback's read of it), and when the homepage's header or
#: main navigation has links whose text names admissions
#: (``_ADMISSIONS_LINK_TEXT``) pointing to exactly ONE other registrable domain,
#: that domain becomes ``Candidate.extra_domains`` for the rest of the run;
#: every reader accepts it through ``Candidate.official_domains``. Never a known
#: third party (``_ADMISSIONS_HOST_DENYLIST``: application portals, social
#: networks, search engines, shorteners), never a government portal unless the
#: link text names the university; two candidate domains are ambiguous and add
#: none. Pages on the added domain are classified and extracted as usual. The
#: trace records the domain and the link that justified it
#: (``admissions_host``). The benchmark harness flips it per capture
#: (``--admissions-host-from-homepage``). False turns it off.
ADMISSIONS_HOST_FROM_HOMEPAGE = False
#: DI-1: navigation text that names admissions, in English and a few local words.
_ADMISSIONS_LINK_TEXT = re.compile(
    r"\badmissions?\b|\bapply\b|\binternational\s+(?:students?|admissions?)\b"
    r"|\bprospective\s+students?\b|\bundergraduate\s+admissions?\b"
    r"|\badmisi(?:o|ó)n(?:es)?\b|招生|入学",
    re.IGNORECASE,
)
#: DI-1: registrable domains that are never an institution's admissions site.
#: ``google.*`` is matched by its first label, every country suffix included.
_ADMISSIONS_HOST_DENYLIST = frozenset(
    {
        "commonapp.org",
        "uni-assist.de",
        "studyinfo.fi",
        "universityadmissions.se",
        "antagning.se",
        "parcoursup.fr",
        "ucas.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "youtube.com",
        "linkedin.com",
        "wikipedia.org",
        "bit.ly",
    }
)
#: DI-1: host labels that mark a government portal.
_GOVERNMENT_LABELS = frozenset({"gov", "gouv", "gob", "govt", "government"})
#: DI-1: link text that says the page is the university's own admissions.
_NAMES_UNIVERSITY = re.compile(r"universit|institut|college|大学", re.IGNORECASE)
#: DI-1: an ancestor id/class that marks a site header or main navigation.
_NAVIGATION_REGION = re.compile(r"nav|menu|header|masthead|topbar", re.IGNORECASE)
#: DI-1: extra registrable domains one homepage may add.
MAX_EXTRA_DOMAINS = 1

#: LI-1: programme-path words of non-English catalogues, scored like the
#: existing ``opleidingen|studiengang`` rule. Only words that name a study
#: offer: "studienangebot" (de), "studiengaenge" (de, ASCII), "corsi-di-laurea"
#: (it), "carreras"/"grados"/"titulaciones" (es), "formations" (fr),
#: "utbildningar" (sv), "studijni-programy" (cs).
_LOCALIZED_PROGRAM_SIGNALS: tuple[tuple[str, int], ...] = (
    (
        r"/(studienangebot|studiengaenge|studiengange|corsi-di-laurea|corso-di-laurea"
        r"|carreras|grados|titulaciones|formations|utbildningar|studijni-programy)/[a-z-]{4,}",
        3,
    ),
)
#: LI-1: degree words whose level is certain, as URL slugs (accents folded),
#: matched on a segment boundary like ``_DEGREE_SLUGS``. Compounds are checked
#: first, so ``laurea-magistrale`` (master) is never read as ``laurea``
#: (bachelor) and ``yuksek-lisans`` (master) never as ``lisans`` (bachelor).
#: ``on-lisans`` (Turkish associate degree) is removed before matching rather
#: than given a level the enum does not have. ``kandidat`` is a bachelor only
#: in Swedish (a Danish ``kandidat`` is a master's), so it counts only on a
#: ``.se`` host.
_LOCALIZED_DEGREE_COMPOUNDS: tuple[tuple[str, str], ...] = (
    ("master", r"laurea-magistrale"),
    ("master", r"yuksek-?lisans"),
    ("bachelor", r"laurea-triennale"),
)
_LOCALIZED_DEGREE_SLUGS: tuple[tuple[str, str], ...] = (
    ("bachelor", r"laurea"),
    ("bachelor", r"lisans"),
    ("bachelor", r"bakala(?:r|vr|ur)[a-z]*"),
    ("bachelor", r"grado"),
    ("master", r"magist(?:er|r)[a-z]*"),
    ("master", r"mestrado"),
    ("master", r"master-s"),
)
_SWEDISH_KANDIDAT = r"kandidat[a-z]*"
_TURKISH_ASSOCIATE = re.compile(r"(^|[/-])on-?lisans(?=[/-]|$)")

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

#: PG-1 (``page_classifier.PROGRAMME_PAGE_GUARD``) only: research output and
#: article pages the list above misses. TUM/Serper read
#: ``portal.fis.tum.de/en/publications/…`` and ``ed.tum.de/…/news-single-view-
#: start/article/…`` as programme leads; KAIST read a ``/clippings/`` page.
_PG1_URL_EXCLUSIONS = re.compile(
    r"/(publications?|article|clippings)(/|$)|news-single-view", re.IGNORECASE
)


def _url_excluded(path: str) -> bool:
    """Whether a URL path is never worth fetching (PG-1 widens the list)."""
    if _URL_EXCLUSIONS.search(path):
        return True
    return _page_classifier.PROGRAMME_PAGE_GUARD and bool(_PG1_URL_EXCLUSIONS.search(path))


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


def on_institution_site(url: str, domain: str, extra_domains: Sequence[str] = ()) -> bool:
    """``same_institution`` for the domain or any DI-1 admissions domain."""
    return same_institution(url, domain) or any(
        same_institution(url, extra) for extra in extra_domains if extra
    )


def _in_navigation(anchor: Any) -> bool:
    """Whether a link sits in the page's header or main navigation (DI-1)."""
    for parent in anchor.parents:
        name = parent.name
        if name in ("nav", "header"):
            return True
        if name in (None, "[document]", "html", "body"):
            continue
        role = str(parent.get("role") or "").lower()
        if role in ("navigation", "banner", "menubar", "menu"):
            return True
        classes = parent.get("class") or []
        if isinstance(classes, str):
            classes = [classes]
        marks = " ".join([str(parent.get("id") or ""), *map(str, classes)])
        if marks.strip() and _NAVIGATION_REGION.search(marks):
            return True
    return False


def _third_party(registrable: str) -> bool:
    """Whether a registrable domain is on DI-1's never-an-admissions-site list."""
    return registrable in _ADMISSIONS_HOST_DENYLIST or registrable.split(".", 1)[0] == "google"


def admissions_host_from_homepage(html: str, base: str, domain: str) -> dict[str, object]:
    """DI-1: the one other registrable domain a homepage names as its admissions.

    Returns the trace record: ``{"domain", "link", "text"}`` when exactly one
    domain qualifies, ``{"rejected": ..., "domains": [...]}`` when several do,
    and ``{}`` when none does. Only links in the header or main navigation
    count, only when their own text names admissions, never a denylisted third
    party, and a government portal only when the text names the university.
    """
    own = registrable_domain(domain)
    found: dict[str, tuple[str, str]] = {}
    for anchor in parse_html(html).find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        url = urljoin(base, str(anchor["href"])).split("#")[0]
        try:
            parsed = urlparse(url)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not host:
            continue
        registrable = registrable_domain(host)
        if not registrable or registrable == own or same_institution(url, domain):
            continue
        text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:160]
        if not _ADMISSIONS_LINK_TEXT.search(text) or not _in_navigation(anchor):
            continue
        if _third_party(registrable):
            continue
        if _GOVERNMENT_LABELS & set(host.split(".")) and not _NAMES_UNIVERSITY.search(text):
            continue
        found.setdefault(registrable, (canonical_url(url), text))
    if len(found) > MAX_EXTRA_DOMAINS:
        return {"rejected": "ambiguous: several admissions domains", "domains": sorted(found)}
    if not found:
        return {}
    extra, (link, text) = next(iter(found.items()))
    return {"domain": extra, "link": link, "text": text}


#: Query parameters that identify a referral rather than select content.
#: Matched against the parameter name — an earlier version matched the whole
#: "key=value" pair, so "utm_source=x" was kept and the same page was
#: discovered twice under two URLs.
_TRACKING_PARAM = re.compile(
    r"^(utm_[a-z_]*|fbclid|gclid|msclkid|dclid|mc_[a-z]+|ref|referrer|source"
    r"|igshid|_ga|yclid)$",
    re.IGNORECASE,
)


#: Plan rule CU-1, on since paired runs 39067189351 (cohort) and 39067190840
#: (dev2): identical labels, dev2 reads 345/342 -> 326/323; owner delegation
#: 2026-10-17. False turns it off. ``canonical_url``
#: writes ``http://`` of a page on its default port as ``https://``, so the two
#: schemes of one institution page are one URL everywhere the pipeline
#: deduplicates. METU's navigation offered ``http://…/undergraduate-programs``
#: and ``https://…/undergraduate-programs`` and the run read both, 10 s each
#: under Crawl-delay 10. ``navigation.py`` already merged the two locally (see
#: ``scheme_free_identity``); this applies the same identity pipeline-wide and
#: picks the secure scheme as the one to read, the one navigation prefers too.
#: A URL on an explicit non-default port keeps its scheme: ``http://h:8080`` and
#: ``https://h:8080`` are different services.
CANONICAL_HTTP_HTTPS = True


def scheme_free_identity(url: str) -> str:
    """One page's identity regardless of ``http``/``https``: the URL without its scheme."""
    return url.split("://", 1)[-1]


def canonical_url(url: str) -> str:
    """A stable form, so the same page is not discovered twice.

    Drops the fragment and tracking parameters, lowercases the host, removes a
    default port and a trailing slash. Query parameters that select content are
    kept — dropping them would merge genuinely different pages. Under CU-1 an
    ``http`` URL on the default port is written as ``https``.
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
    scheme = parts.scheme
    if CANONICAL_HTTP_HTTPS and scheme == "http" and parts.port in (None, 80):
        scheme = "https"
    return urlunparse((scheme, host, path, "", "&".join(sorted(kept)), ""))


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


#: Plan rule SR-1 (dev3 discovery analysis 2026-10-18, Imperial and UNSW,
#: fix B), off until a paired run passes. ``matches_field`` scored each word
#: of the field as a *substring* of the path, so "science" gave +8 to every
#: ``*-science`` URL ("natural-sciences", "materials-science") while
#: "computer" missed "computing"; Imperial's gold ``/2027/computing-beng``
#: sat at rank 35 of 40 behind two tuition-fee tables and the eight confirm
#: reads (~5.8 s each) went to the wrong pages. With SR-1 on:
#:
#: * the field bonus (8 per word of the requested field) is earned only when
#:   the path carries the field phrase or one of the ontology's strong (or,
#:   under LI-1, localized) aliases as consecutive whole slug words; a
#:   generic word on its own ("science", "engineering") earns nothing;
#: * a path with a fee, tuition, cost or scholarship segment never scores as
#:   a programme page or catalogue;
#: * degree slug tokens (bsc, beng, btech, ba, bs, meng) are title filler.
#:
#: The benchmark harness flips it per capture (``--field-slug-scoring``).
FIELD_SLUG_SCORING = False
#: SR-1: degree tokens that name a form, never a subject.
_DEGREE_SLUG_FILLER = frozenset({"bsc", "beng", "btech", "ba", "bs", "meng"})
#: SR-1: slug words that make a path segment a page about money.
_FEE_SLUG_WORDS = frozenset(
    {"tuition", "fee", "fees", "scholarship", "scholarships", "bursary", "bursaries"}
)
#: SR-1: a segment about costs ("costs", "cost-of-living"), but not a subject
#: that merely contains the word ("cost-engineering").
_COST_SEGMENT = re.compile(r"^(?:costs?|cost[-_]of[-_].*|costs?[-_]and[-_].*)$")


def _is_fee_path(path: str) -> bool:
    """SR-1: whether a path has a fee, tuition, cost or scholarship segment."""
    for segment in path.lower().split("/"):
        if _COST_SEGMENT.match(segment):
            return True
        if _FEE_SLUG_WORDS.intersection(re.split(r"[-_.]+", segment)):
            return True
    return False


def score_url(url: str, category: str) -> int:
    """How strongly a URL looks like it belongs to a category. 0 means no."""
    path = (urlparse(url).path or "").lower()
    if _url_excluded(path) or _NOT_A_PAGE_ABOUT_STUDYING.search(path):
        return 0
    if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG) and (
        _FUNDING_SEGMENT.search(path)
        or _NOT_A_PROGRAMME_PATH.search(path)
        or (FIELD_SLUG_SCORING and _is_fee_path(path))
    ):
        # NTU offered a scholarship page as the applicant's programme (the
        # "undergraduate" in the path outscored the "scholarships" beside it),
        # and rug.nl offered a research group's "BSc and MSc projects" page.
        # Neither is a programme, whatever else the path says.
        return 0
    signals = _URL_SIGNALS[category]
    if LOCALIZED_IDENTITY and category == PageCategory.PROGRAM_PAGE:
        signals = (*signals, *_LOCALIZED_PROGRAM_SIGNALS)
    return sum(weight for pattern, weight in signals if re.search(pattern, path))


#: Plan rule UC-1 (evidence analysis 2026-10-17, §0 cause 4, §4 rank 4): the
#: ``/(bachelors?|masters?|undergraduate)/<slug>`` programme rule filed TCD's
#: ``/courses/undergraduate/fees`` as a programme lead (programme 9 against
#: costs 4), and with no level check on service categories
#: ``/courses/postgraduate/how-to-apply`` became the bachelor applicant's
#: admissions page in 12 of 12 repetitions. With UC-1 on, a URL whose last
#: path segment is a service word (fees, tuition, how-to-apply, apply,
#: admission(s), entry-requirements, scholarships, funding, deadlines, dates)
#: is filed under that service whatever level segment precedes it, and the
#: service categories (admissions, costs, scholarships) get the programme
#: categories' degree guard: a URL, or a navigation link text, naming another
#: level never fills the slot, and one naming the requested level gets the
#: degree bonus. Discovery only picks entry pages; the adapters still classify
#: what they read. Off by default; the benchmark harness flips it per capture
#: (``--service-page-priority``).
SERVICE_PAGE_PRIORITY = False
_SERVICE_SEGMENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (PageCategory.COSTS, re.compile(r"^(?:tuition|fees?|tuition[-_]fees?)$")),
    (
        PageCategory.ADMISSIONS,
        re.compile(
            r"^(?:how[-_]to[-_]apply|apply|admissions?|(?:entry|admission)[-_]requirements"
            r"|(?:application[-_])?deadlines|(?:key[-_])?dates|dates[-_]and[-_]deadlines)$"
        ),
    ),
    (PageCategory.SCHOLARSHIPS, re.compile(r"^(?:scholarships?|funding)$")),
)
SERVICE_CATEGORIES = (PageCategory.ADMISSIONS, PageCategory.COSTS, PageCategory.SCHOLARSHIPS)
#: Link text naming a level other than the requested one (UC-1 navigation guard).
_OTHER_LEVEL_LABEL: dict[str, re.Pattern[str]] = {
    "bachelor": re.compile(
        r"\b(?:msc|master'?s?|phd|doctoral|doctorate|postgraduate|graduate)\b", re.I
    ),
    "master": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|phd|doctoral|doctorate)\b", re.I),
    "phd": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|msc|master'?s?)\b", re.I),
}


def service_category(url: str) -> str | None:
    """UC-1: the service a URL's last path segment names, if it names one."""
    path = (urlparse(url).path or "").lower()
    if _url_excluded(path) or _NOT_A_PAGE_ABOUT_STUDYING.search(path):
        return None
    segments = [s for s in path.split("/") if s]
    if not segments:
        return None
    last = re.sub(r"\.(?:html?|php|aspx?)$", "", segments[-1])
    for category, pattern in _SERVICE_SEGMENTS:
        if pattern.match(last):
            return category
    return None


def label_names_other_level(label: str, degree: str) -> bool:
    """UC-1: whether a link's text names a level the applicant did not ask for."""
    pattern = _OTHER_LEVEL_LABEL.get(str(degree))
    return bool(pattern and pattern.search(label))


def categorise_url(url: str) -> tuple[str | None, int]:
    """The category a URL best fits, and its score."""
    best: tuple[str | None, int] = (None, 0)
    for category in PageCategory.ALL:
        score = score_url(url, category)
        if score > best[1]:
            best = (category, score)
    if SERVICE_PAGE_PRIORITY:
        service = service_category(url)
        if service is not None:
            return service, max(score_url(url, service), 4)
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
    if FIELD_SLUG_SCORING:
        return _field_slug_bonus(path, fields)
    bonus = 0
    for field_name in fields:
        # One field counts once, under whichever of its names the path uses.
        best = 0
        local = {_fold(n) for n in _localized_names(field_name)}
        for name in with_strong_aliases([field_name]):
            if _fold(name) in local:
                # LI-1: a localized alias counts as a whole slug word, so
                # "informatik" scores and "wirtschaftsinformatik" does not.
                best = max(best, 8 * _whole_words_in_path(name, path))
                continue
            words = {w for w in re.split(r"[^a-z]+", name.lower()) if len(w) > 3}
            best = max(best, 8 * sum(1 for w in words if w in path))
        bonus += best
    return bonus


def _field_slug_bonus(path: str, fields: list[str]) -> int:
    """``matches_field`` under SR-1: a whole phrase in the slug, or nothing.

    Each requested field earns 8 per word of its own name, once, when the
    path's slug words carry that name or any of its strong (or localized)
    aliases as consecutive whole words. "computing-beng" therefore counts as
    fully as "computer-science", and "materials-science" not at all.
    """
    slug = _folded_words(unquote(path))
    bonus = 0
    for field_name in fields:
        weight = 8 * max(len(_folded_words(field_name)), 1)
        for name in with_strong_aliases([field_name]):
            if _phrase_in_slug(_folded_words(name), slug):
                bonus += weight
                break
    return bonus


def _phrase_in_slug(phrase: list[str], slug: list[str]) -> bool:
    """SR-1: whether ``phrase`` occurs in ``slug`` as consecutive whole words."""
    if not phrase:
        return False
    width = len(phrase)
    return any(slug[i : i + width] == phrase for i in range(len(slug) - width + 1))


def _whole_words_in_path(name: str, path: str) -> int:
    """How many of a name's words a URL path carries as whole slug words (LI-1)."""
    folded = _fold(unquote(path))
    return sum(
        1
        for w in set(_folded_words(name))
        if re.search(rf"(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])", folded)
    )


def _fold(text: str) -> str:
    """Casefold and strip accents, as the ontology does for lookup (LI-1)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _folded_words(text: str) -> list[str]:
    """Words longer than three letters in any script, accents folded (LI-1)."""
    return [w for w in re.split(r"[\W\d_]+", _fold(text)) if len(w) > 3]


def _localized_names(field_name: str) -> tuple[str, ...]:
    """The ontology's localized aliases of a field while LI-1 is on, else none."""
    if not LOCALIZED_IDENTITY:
        return ()
    return localized_aliases(field_name, include_flagged=True)


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
    Only strong aliases: a related concept is never a match. Under LI-1 the
    localized aliases follow them: a strong alias in another language.
    """
    out: list[str] = []
    for field_name in fields:
        for name in (field_name, *_strong_aliases(field_name), *_localized_names(field_name)):
            if name.lower() not in (o.lower() for o in out):
                out.append(name)
    return out


def degree_level_named(url: str) -> str | None:
    """The degree level a URL names in its path, if it names one at all."""
    path = (urlparse(url).path or "").lower()
    if LOCALIZED_IDENTITY:
        return _localized_degree_level(url, path)
    for level, slugs in _DEGREE_SLUGS.items():
        if any(re.search(rf"(^|[/-]){re.escape(slug)}([/-]|$)", path) for slug in slugs):
            return level
    return None


def _localized_degree_level(url: str, path: str) -> str | None:
    """``degree_level_named`` under LI-1: local degree words join the table."""
    path = _TURKISH_ASSOCIATE.sub(r"\1", _fold(unquote(path)))

    def named(pattern: str) -> bool:
        return re.search(rf"(^|[/-]){pattern}([/-]|$)", path) is not None

    for level, pattern in _LOCALIZED_DEGREE_COMPOUNDS:
        if named(pattern):
            return level
    for level, slugs in _DEGREE_SLUGS.items():
        if any(named(re.escape(slug)) for slug in slugs):
            return level
    for level, pattern in _LOCALIZED_DEGREE_SLUGS:
        if named(pattern):
            return level
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".se") and named(_SWEDISH_KANDIDAT):
        return "bachelor"
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
    return bool(_url_excluded(urlparse(url).path or ""))


def looks_like_catalogue(url: str) -> bool:
    """Whether a URL looks like a page that lists programmes."""
    path = urlparse(url).path or ""
    if _url_excluded(path):
        return False
    return bool(_CATALOGUE_PATH.search(path))


def matches_field_text(label: str, fields: list[str]) -> bool:
    """Whether a link's own text names one of the applicant's subjects.

    A catalogue page links to its programmes under the university's own names
    for them, and those names are often nowhere in the URL: Toronto's bachelor
    lead is ``/data-computer-science`` behind the text "Data & Computer
    Science", which no path pattern for "programmes" would ever match.
    """
    if LOCALIZED_IDENTITY:
        return _matches_field_text_localized(label, fields)
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
        if words - wanted <= _title_filler():
            return True
    return False


def _title_filler() -> frozenset[str]:
    """Title filler words, with SR-1's degree slug tokens while it is on."""
    if FIELD_SLUG_SCORING:
        return _TITLE_FILLER | _DEGREE_SLUG_FILLER
    return _TITLE_FILLER


def _matches_field_text_localized(label: str, fields: list[str]) -> bool:
    """``matches_field_text`` under LI-1: any script, accents folded.

    The same rule, with localized aliases among the names and local level and
    form words among the filler. Words are compared whole, so "Informatik"
    names computer science while "Wirtschaftsinformatik", "Bioinformatik" and
    "Medizininformatik" (one word each) do not, and "Ingegneria Informatica"
    is refused because "ingegneria" names another subject.
    """
    words = set(_folded_words(label))
    if not words:
        return False
    own = {_fold(f) for f in fields}
    filler = _title_filler() | _LOCAL_TITLE_FILLER
    for field_name in with_strong_aliases(fields):
        wanted = set(_folded_words(field_name))
        if not wanted or not wanted <= words:
            continue
        if _fold(field_name) in own:
            return True
        if words - wanted <= filler:
            return True
    return False


#: LI-1: title words that carry a bachelor level or a form in another
#: language, never a subject (accents folded). Master's words are absent on
#: purpose: a title saying "magistrale" is not let through on its subject when
#: the classifier missed its level.
_LOCAL_TITLE_FILLER = frozenset(
    {
        "laurea",
        "triennale",
        "lisans",
        "lisansi",
        "programi",
        "bakalar",
        "bakalarsky",
        "bakalarske",
        "bakalarska",
        "bakalavr",
        "bakalavriat",
        "grado",
        "licence",
        "licenciatura",
        "bachelorstudium",
        "bachelorstudiengang",
        "studiengang",
        "studium",
        "corso",
        "programa",
        "programma",
        "programm",
        "studijni",
        "studijny",
        "kandidatprogram",
        "kandidatprogrammet",
    }
)


def english_alternate(url: str, html: str, domain: str) -> str | None:
    """The English twin a local-language page declares, if LI-1 may follow it.

    ``<link rel="alternate" hreflang="en…" href=…>`` on the same registrable
    domain as the page and the institution, and only when the page's own
    ``<html lang>`` names a language that is not English. A page that states
    no language is not followed: it may already be the English page.
    """
    head = html[:200_000]
    tag = _HTML_TAG.search(head)
    lang = (_attributes(tag.group(0)).get("lang") or "").strip().lower() if tag else ""
    if not lang or lang == "en" or lang.startswith("en-"):
        return None
    here = canonical_url(url)
    for link in _LINK_TAG.findall(head):
        attrs = _attributes(link)
        if "alternate" not in (attrs.get("rel") or "").lower().split():
            continue
        hreflang = (attrs.get("hreflang") or "").strip().lower()
        if not (hreflang == "en" or hreflang.startswith("en-")):
            continue
        href = html_unescape((attrs.get("href") or "").strip())
        if not href:
            continue
        target = canonical_url(urljoin(url, href))
        if target == here or not same_institution(target, domain):
            continue
        if registrable_domain(target) != registrable_domain(url):
            continue
        return target
    return None


_HTML_TAG = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATTRIBUTE = re.compile(r"""([a-zA-Z_:][-\w:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")


def _attributes(tag: str) -> dict[str, str]:
    """A tag's attributes, names lowercased."""
    out: dict[str, str] = {}
    for m in _ATTRIBUTE.finditer(tag):
        value = next((g for g in m.groups()[1:] if g is not None), "")
        out.setdefault(m.group(1).lower(), value)
    return out


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


@dataclass
class _RecoveryState:
    """What identity recovery has read so far, shared across QB-1's two passes.

    One institution's search candidates get MAX_PROGRAM_CANDIDATES_CHECKED
    reads in all, however many provider passes produced them, and a URL the
    first pass already read is never read again. ``max_checks`` lowers that
    cap (QB-1b: a page confirmed before search needs only a twin check).
    """

    visited: set[str] = field(default_factory=set)
    pending: list[str] = field(default_factory=list)
    checked: int = 0
    max_checks: int = MAX_PROGRAM_CANDIDATES_CHECKED


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
    #: Provider queries discovery sent for this institution; later stages
    #: spend only what remains of the per-institution query budget.
    search_queries_sent: int = 0
    search_coverage: dict[str, int] = field(default_factory=dict)
    used_navigation_fallback: bool = False
    #: (url, link text) for leads found by a catalogue's own wording rather
    #: than by the URL, so the report can show what the wording was.
    kept_by_link_text: list[tuple[str, str]] = field(default_factory=list)
    #: The catalogue-walker stage's report. Zeros until (and unless) the stage
    #: runs, so "inactive" and "ran and found nothing" stay distinguishable.
    walker: WalkerTrace = field(default_factory=_walker_trace)
    #: SO-1 only: the discovery stages in the order they ran, and the host
    #: cost that chose it. Empty while the rule is off, and then not serialised.
    stage_order: list[str] = field(default_factory=list)
    host_cost: dict = field(default_factory=dict)
    #: PG-1 only: search leads identity recovery could not read, kept as
    #: diagnostics instead of programme pages. Not serialised while empty.
    unresolved: list[str] = field(default_factory=list)
    #: QB-1 only: provider queries each discovery pass sent ([3] when the first
    #: pass confirmed a programme page, [3, 3] when it did not). Empty while the
    #: rule is off, and then not serialised.
    discovery_query_passes: list[int] = field(default_factory=list)
    #: DI-1 only: the admissions domain the homepage justified (and the link),
    #: or why none was added. Not serialised while empty.
    admissions_host: dict[str, object] = field(default_factory=dict)
    #: DI-1: registrable domains accepted beside ``domain`` for this run.
    extra_domains: list[str] = field(default_factory=list)

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
            **({"stage_order": self.stage_order} if self.stage_order else {}),
            **({"host_cost": self.host_cost} if self.host_cost else {}),
            **({"unresolved": self.unresolved} if self.unresolved else {}),
            **(
                {"discovery_query_passes": self.discovery_query_passes}
                if self.discovery_query_passes
                else {}
            ),
            **({"admissions_host": self.admissions_host} if self.admissions_host else {}),
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
#: Entries whose direct ``loc`` child names a URL. Matched by local name:
#: sites serve the http and the https sitemaps.org namespace, or none (UNSW
#: uses ``https://www.sitemaps.org/...``). Only direct children are taken, so
#: an extension's own ``loc`` (``image:image/image:loc``) is not read as a page.
_SITEMAP_ENTRY_TAGS = ("url", "sitemap")


def _local_name(tag: object) -> str:
    """An element's tag without its ``{namespace}``; '' for comments and PIs."""
    return tag.rpartition("}")[2].lower() if isinstance(tag, str) else ""


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


class HostCost:
    """SO-1: what one host's reads cost so far, to decide the stage order.

    Only the first SLOW_HOST_SAMPLE_READS reads are timed. A crawl delay is
    read from the fetcher's own robots policy, which is also what spaces the
    reads, so the two signals cannot disagree about why a host is slow.
    """

    def __init__(self) -> None:
        self.read_seconds: list[float] = []
        self.crawl_delay: float | None = None

    async def get(self, fetcher: Fetcher, url: str) -> FetchResult:
        started = _clock()
        result = await fetcher.get(url)
        if len(self.read_seconds) < SLOW_HOST_SAMPLE_READS:
            self.read_seconds.append(_clock() - started)
        return result

    async def learn_crawl_delay(self, fetcher: Fetcher, url: str) -> None:
        robots = getattr(fetcher, "robots", None)
        if robots is None:
            return
        try:
            self.crawl_delay = await robots.crawl_delay(url)
        except Exception:  # a robots policy that cannot answer says nothing
            self.crawl_delay = None

    @property
    def median_read_seconds(self) -> float | None:
        # Two reads are enough to judge: with SM-1 a host whose robots.txt
        # names no sitemap and whose /sitemap.xml answers makes only two.
        if len(self.read_seconds) < 2:
            return None
        return float(statistics.median(self.read_seconds))

    @property
    def slow(self) -> bool:
        if self.crawl_delay is not None and self.crawl_delay >= SLOW_HOST_SECONDS:
            return True
        median = self.median_read_seconds
        return median is not None and median >= SLOW_HOST_SECONDS

    def document_cap(self) -> int:
        return SLOW_HOST_SITEMAP_DOCUMENTS if self.slow else MAX_SITEMAP_DOCUMENTS

    def as_dict(self) -> dict:
        median = self.median_read_seconds
        return {
            "crawl_delay": self.crawl_delay,
            "median_read_seconds": None if median is None else round(median, 2),
            "slow": self.slow,
        }


def _child_priority(url: str) -> int:
    """SM-1: 0 for a programme/page sitemap, 2 for a news/post one, else 1.

    Judged on the child's path and query only (TYPO3 names its children
    ``sitemap.xml?sitemap=news``); a programme word wins over a news word.
    """
    parts = urlparse(url)
    name = f"{parts.path} {parts.query}".lower()
    if _SITEMAP_CHILD_FIRST.search(name):
        return 0
    if _SITEMAP_CHILD_LAST.search(name):
        return 2
    return 1


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

    locations = [
        (child.text or "").strip()
        for entry in root.iter()
        if _local_name(entry.tag) in _SITEMAP_ENTRY_TAGS
        for child in entry
        if _local_name(child.tag) == "loc" and (child.text or "").strip()
    ]
    if _local_name(root.tag) == "sitemapindex":
        return locations, []
    return [], locations


def _resolve_loc(base: str, loc: str) -> str:
    """A sitemap ``loc`` made absolute against its document; as-is if malformed."""
    try:
        return urljoin(base, loc)
    except ValueError:
        return loc


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
        cost: HostCost | None = None,
    ) -> list[str]:
        """Page URLs the institution's sitemaps declare, deduplicated.

        ``keep`` decides relevance as each URL is read. Without it every URL is
        kept, which is what the unit tests want but not what a real university
        sitemap can afford: filtering afterwards means the bound falls wherever
        the site happens to have listed its news.
        """
        origin = self._origin(homepage)
        declared = await self._declared_sitemaps(origin, trace, cost)
        if cost is not None:
            await cost.learn_crawl_delay(self.fetcher, homepage)
        queue: list[tuple[str, int]] = [(u, 0) for u in declared]
        #: SM-1: the conventional locations still to probe, dropped once one answers.
        fallbacks: set[str] = set()
        if not queue:
            queue = [(urljoin(origin, path), 0) for path in SITEMAP_FALLBACK_PATHS]
            fallbacks = {canonical_url(u) for u, _ in queue}

        seen_documents: set[str] = set()
        pages: list[str] = []
        seen_pages: set[str] = set()

        attempted_documents = 0
        while queue and attempted_documents < (
            MAX_SITEMAP_DOCUMENTS if cost is None else cost.document_cap()
        ):
            url, depth = queue.pop(0)
            url = canonical_url(url)
            if url in seen_documents or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_documents.add(url)

            if not same_institution(url, domain):
                trace.reject(url, "sitemap is off the institution's domain")
                continue

            attempted_documents += 1
            if url in fallbacks:
                # HS-1: a conventional location is a guess, not a published link.
                mark_guessed = getattr(self.fetcher, "mark_guessed", None)
                if mark_guessed is not None:
                    mark_guessed(url)
            result = await (self.fetcher.get(url) if cost is None else cost.get(self.fetcher, url))
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
            # A ``loc`` may be relative (UiO's index lists ``/sitemap-….xml``);
            # it is resolved against the document it came from, and every
            # domain check below still runs on the joined URL.
            base = result.final_url or url
            children = [_resolve_loc(base, child) for child in children]
            locations = [_resolve_loc(base, location) for location in locations]
            if SITEMAP_CHILD_PRIORITY:
                if url in fallbacks and (children or locations):
                    # One conventional location answered with a sitemap; the
                    # others are guesses that cost a read each.
                    queue = [item for item in queue if canonical_url(item[0]) not in fallbacks]
                    fallbacks = set()
                children = self._prioritised(
                    children,
                    attempted_documents + len(queue),
                    trace,
                    MAX_SITEMAP_DOCUMENTS if cost is None else cost.document_cap(),
                )
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

    @staticmethod
    def _prioritised(
        children: list[str], committed: int, trace: DiscoveryTrace, cap: int
    ) -> list[str]:
        """SM-1: an index's children, programme sitemaps first, news last.

        ``committed`` counts documents already read or queued. When the
        first group alone reaches the cap, the last group is not queued at all.
        """
        ordered = sorted(children, key=_child_priority)  # stable: file order within a group
        first = sum(1 for child in children if _child_priority(child) == 0)
        if first and committed + first >= cap:
            skipped = [child for child in ordered if _child_priority(child) == 2]
            for child in skipped:
                trace.reject(child, "news/post sitemap skipped: programme sitemaps fill the cap")
            ordered = [child for child in ordered if _child_priority(child) != 2]
        return ordered

    async def _declared_sitemaps(
        self, origin: str, trace: DiscoveryTrace, cost: HostCost | None = None
    ) -> list[str]:
        robots_url = urljoin(origin, "/robots.txt")
        result = await (
            self.fetcher.get(robots_url) if cost is None else cost.get(self.fetcher, robots_url)
        )
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
        #: The search provider, resolved once per run. See
        #: :meth:`_search_provider_or_none` for why this is per run and not per
        #: institution.
        self._search_provider: SearchProvider | None = None
        self._search_provider_resolved = False

    def registry(self) -> list[dict]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text())

    def _search_provider_or_none(self) -> SearchProvider | None:
        """The configured provider, or ``None`` when there is none.

        Resolved **once per discovery run**, not once per institution.

        ``get_search_provider`` builds a fresh adapter object on every call, and
        the keyless Exa MCP provider performs its JSON-RPC handshake on first
        use and remembers the session id on the instance. Calling it inside the
        per-institution loop therefore re-handshaked for each of the nineteen
        institutions — nineteen handshakes instead of one — and, because that
        handshake shares the fifteen-second search budget with the first query,
        the first and best-ranked query family was the one that timed out.

        One instance per run keeps the handshake where it belongs: once, before
        the first institution asks anything. A run is also the right scope
        rather than the process, because the provider is built from settings and
        a test that changes settings must still see the change.
        """
        if not self._search_provider_resolved:
            from app.adapters.search import SearchError, get_search_provider

            try:
                self._search_provider = get_search_provider()
            except SearchError:
                self._search_provider = None
            self._search_provider_resolved = True
        return self._search_provider

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
            elif SERVICE_PAGE_PRIORITY and category in SERVICE_CATEGORIES:
                if names_other_degree_level(url, degree):
                    trace.reject(url, f"{category} page names a degree level other than {degree}")
                    return False
                score += matches_degree(url, degree)
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

        cost = HostCost() if COST_AWARE_SEARCH_ORDER else None
        stages = trace.stage_order if cost is not None else []
        stages.extend(["seeds", "sitemaps"] if seeds else ["sitemaps"])
        try:
            await self.sitemaps.collect(entry["homepage"], domain, trace, keep, cost)
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
        if ADMISSIONS_HOST_FROM_HOMEPAGE:
            await self._admissions_host(entry, domain, trace)

        searched_early = False
        slow_host = cost is not None and cost.slow
        if cost is not None:
            trace.host_cost = cost.as_dict()
        if slow_host or (
            (SEARCH_BEFORE_NAVIGATION or cost is not None)
            and not selected[PageCategory.PROGRAM_PAGE]
        ):
            await self._add_search_results(entry, domain, selected, trace, profile)
            searched_early = True
            stages.append("search")
        if not selected[PageCategory.PROGRAM_PAGE]:
            trace.used_navigation_fallback = True
            stages.append("navigation")
            await self._navigation_fallback(entry, domain, selected, trace, profile)

        # 4. Confirm the programme candidates by reading them.
        #    URL shape alone cannot tell a programme from an open day: live runs
        #    offered "bachelor-open-day", "campus-tour", "webklassen" and a
        #    student newsletter as programme pages, all sitting under the same
        #    path as the real programmes. The classifier already knows the
        #    difference, so discovery asks it rather than guessing harder.
        await self._confirm_programs(selected, ranked, trace, profile)
        stages.append("confirm")
        if slow_host:
            # Every catalogue read costs the host's delay; search already ran.
            stages.append("walker_skipped")
        else:
            stages.append("walker")
            await self._walk_catalogs(entry, selected, trace, profile)
        # The walker confirms its own candidates under the T29 contract, which
        # deliberately trusts a university's own catalogue listing — so the
        # snapshot is taken after it, and step 7 judges only what search adds.
        confirmed_so_far = set(selected[PageCategory.PROGRAM_PAGE])

        if not searched_early:
            stages.append("search")
            # Every programme page in the slots by now was read and accepted
            # by the confirm stage or the walker (QB-1 counts them confirmed).
            await self._add_search_results(
                entry, domain, selected, trace, profile, slots_confirmed=True
            )

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
        reads = queued[:MAX_PROGRAM_CANDIDATES_CHECKED]
        position = 0
        while position < len(reads):
            url = reads[position]
            position += 1
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
            if LOCALIZED_IDENTITY:
                reads = self._queue_english_alternate(
                    result.final_url or url,
                    result.text,
                    page,
                    requested_level,
                    trace,
                    reads,
                    position,
                )
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

    @staticmethod
    def _queue_english_alternate(
        url: str,
        html: str,
        page: PageClassification,
        requested_level: str,
        trace: DiscoveryTrace,
        reads: list[str],
        position: int,
    ) -> list[str]:
        """LI-1: put a local-language page's English twin next in the reads.

        The twin takes the next place inside the same read cap, so following it
        costs one read like any candidate; a page of another level is not
        followed, since its twin names that level too.
        """
        if page.degree_level and page.degree_level != requested_level:
            return reads
        twin = english_alternate(url, html, trace.domain)
        if twin is None or twin in reads[:position]:
            return reads
        rest = [u for u in reads[position:] if u != twin]
        trace.errors.append(f"hreflang: reading the English alternate of {url}")
        return [*reads[:position], twin, *rest][:MAX_PROGRAM_CANDIDATES_CHECKED]

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
            extra_domains=trace.extra_domains,
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
        *,
        slots_confirmed: bool = False,
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
        from app.adapters.search import SearchError
        from app.adapters.search import intent as intent_module
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DiscoveryIntent
        from app.adapters.search.retrieval import discover_candidates

        provider = self._search_provider_or_none()
        if provider is None:
            return

        fields = list(profile.context.intended_fields)
        if not fields:
            return
        # Every programme slot is already taken, so the recovery loop below
        # breaks on its first iteration and whatever the provider ranked is
        # discarded unread. Asking anyway is pure cost: measured, six provider
        # calls, one entry-point read and zero pages added when the registry,
        # the sitemaps and the catalogue walker had already filled the three
        # slots. Checking first is exactly equivalent — with no free slot,
        # search cannot contribute a page — and it removes a handshake, six
        # queries and three reads per institution from every such run.
        if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
            trace.search_limitations.append(
                f"Search not run at {entry['name']}: all {MAX_PAGES_PER_CATEGORY} "
                "programme-page slots were already filled by the registry, the "
                "sitemaps and the catalogue walker."
            )
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

        if intent_module.DISCOVERY_QUERY_RESERVE and RECOVER_SEARCH_CANDIDATES:
            await self._search_in_two_passes(
                entry,
                intent,
                provider,
                read,
                selected[PageCategory.PROGRAM_PAGE],
                trace,
                profile,
                slots_confirmed=slots_confirmed,
            )
            return

        try:
            report = await discover_candidates(provider, intent, fetch=read, top_k=10)
        except SearchError as exc:
            trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
            return
        trace.search_queries_sent += len(report.queries_run)

        trace.search_failures.extend(report.failure_diagnostics)
        if report.throttled:
            trace.search_limitations.append(
                f"Search at {entry['name']} stopped: {report.provider} answered "
                "HTTP 429, so the remaining query families were not sent. This "
                "is a quota stop, not a search that found nothing."
            )
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

    async def _search_in_two_passes(
        self,
        entry: dict,
        intent,
        provider,
        read,
        pages: list[str],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        *,
        slots_confirmed: bool,
    ) -> None:
        """QB-1: three query families first; the other three only if nothing was confirmed.

        "Confirmed" is decided here, between the passes, because this is the
        first point that knows it: the first pass's candidates go through
        identity recovery (each read through the Fetcher, classified, and
        accepted by the same predicate as always) before the second pass is
        considered. A programme page counts as confirmed when that recovery
        accepted it, or when it already held a slot as search began *after*
        the confirm stage and the walker (``slots_confirmed``), which accept
        only pages they read. An unread lead never counts. A 429 or a provider
        error in the first pass also ends the search, as it always has.

        The second pass sends only the families the first did not, and opens
        no new navigation entry points: the first pass's hop already read the
        roots, and the per-institution read cap of identity recovery is shared
        by both passes.

        QB-1b: when a programme page is confirmed before the first pass, that
        pass opens no entry points either and recovery reads at most
        PRECONFIRMED_RECOVERY_CHECKS candidates, so the reserved queries are
        not paid for with reads and wall clock the page no longer needs.
        """
        from app.adapters.search import SearchError
        from app.adapters.search import intent as intent_module
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.retrieval import DEFAULT_HOP_ENTRY_POINTS, discover_candidates

        planned = [query.family for query in intent_module.queries_for(intent)]
        first = planned[: intent_module.DISCOVERY_FIRST_PASS_QUERIES]
        rest = planned[len(first) :]
        confirmed = len(pages) if slots_confirmed else 0
        state = _RecoveryState(visited=set(pages))
        first_hop = DEFAULT_HOP_ENTRY_POINTS
        if confirmed:
            first_hop = 0
            state.max_checks = PRECONFIRMED_RECOVERY_CHECKS
            trace.errors.append(
                f"QB-1: first pass capped at {PRECONFIRMED_RECOVERY_CHECKS} checks and no "
                "entry-point hop; a programme page was confirmed before search"
            )
        for number, families in enumerate((first, rest), start=1):
            if not families:
                break
            if number == 2 and confirmed:
                trace.errors.append(
                    f"QB-1: {len(families)} discovery quer{'y' if len(families) == 1 else 'ies'} "
                    "left for topic and award search; a programme page was confirmed after "
                    "the first pass"
                )
                break
            try:
                report = await discover_candidates(
                    provider,
                    intent,
                    query_budget=len(families),
                    only_families=families,
                    fetch=read,
                    hop_entry_points=first_hop if number == 1 else 0,
                    top_k=10,
                )
            except SearchError as exc:
                trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
                break
            trace.search_queries_sent += len(report.queries_run)
            trace.discovery_query_passes.append(len(report.queries_run))
            trace.search_failures.extend(report.failure_diagnostics)
            confirmed += await self._recover_search_pages(
                report.candidates, pages, trace, profile, state=state, final=False
            )
            trace.errors.append(
                f"search identity recovery via {report.provider} (QB-1 pass {number}); "
                f"queries {len(report.queries_run)}, failed {len(report.failed_queries)}, "
                f"rejected {dict(report.rejection_counts)}"
            )
            if report.throttled:
                trace.search_limitations.append(
                    f"Search at {entry['name']} stopped: {report.provider} answered "
                    "HTTP 429, so the remaining query families were not sent. This "
                    "is a quota stop, not a search that found nothing."
                )
                break
        self._settle_pending(pages, trace, state.pending, multi_requested=False)

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
            # Counted before a throttle stop: the queries sent before the 429
            # were spent, and leaving them out understated the run's cost.
            query_count += len(report.queries_run)
            trace.search_queries_sent += len(report.queries_run)
            failed_count += len(report.failed_queries)
            if report.throttled:
                # One rate-limit answer ends the run's searching, not just this
                # subject's: the remaining subjects would each re-send a query
                # into a quota that has already refused.
                trace.search_limitations.append(
                    f"Search at {entry['name']} stopped: {provider.name} answered "
                    "HTTP 429, so the remaining subjects were not searched. This "
                    "is a quota stop, not a search that found nothing."
                )
                break
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

    async def _recover_search_pages(
        self,
        candidates,
        pages,
        trace,
        profile,
        *,
        state: _RecoveryState | None = None,
        final: bool = True,
    ) -> int:
        """Fill programme slots from fetched identities rather than search snippets.

        Existing confirmed catalogue/sitemap pages stay first. A rejected lead
        frees a slot for the next search result. The legacy single-field path
        keeps host failures as unresolved leads; a multi-field result requires
        source-backed field identity before it can become a programme.

        Returns how many pages it confirmed (read and accepted). ``state`` and
        ``final=False`` let QB-1 run it once per provider pass under one read
        cap, settling unread leads only after the last pass.
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
        if state is None:
            state = _RecoveryState()
        state.visited.update(pages)
        pending = state.pending
        queue = list(candidates)
        visited = state.visited
        checked = state.checked
        added = 0
        while queue:
            if len(pages) >= MAX_PAGES_PER_CATEGORY or checked >= state.max_checks:
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
            if LOCALIZED_IDENTITY and not (page.degree_level and page.degree_level != level):
                twin = english_alternate(result.final_url or found.url, result.text, trace.domain)
                if twin is not None and twin not in visited:
                    from app.adapters.search.retrieval import RankedCandidate as _Twin

                    trace.errors.append(f"hreflang: reading the English alternate of {found.url}")
                    queue[:0] = [_Twin(twin, found.title, found.score, "hreflang-alternate")]
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
                    followups = leads[: state.max_checks - checked]
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
        state.checked = checked
        if final:
            self._settle_pending(pages, trace, pending, multi_requested=multi_requested)
        trace.errors.append(f"search identity recovery: checked {checked}, confirmed {added}")
        return added

    @staticmethod
    def _settle_pending(
        pages: list[str], trace: DiscoveryTrace, pending: list[str], *, multi_requested: bool
    ) -> None:
        """What becomes of the search leads identity recovery could not read."""
        # Preserve the legacy single-field lead fallback. In a multi-field
        # run, a search title cannot establish which subject an unreadable
        # page actually covers, so keep the failure only in diagnostics.
        if _page_classifier.PROGRAMME_PAGE_GUARD:
            # PG-1: an unread page is not a programme page. Aalto reported
            # three it never read when its robots.txt was unreachable.
            trace.unresolved.extend(url for url in pending if url not in trace.unresolved)
        elif not pages and not multi_requested:
            pages.extend(pending[:MAX_PAGES_PER_CATEGORY])
        if multi_requested and pending:
            trace.search_limitations.append(
                f"Search coverage limited at {trace.institution}: "
                f"{len(pending)} programme lead(s) could not be read, so their "
                "subjects were not confirmed from the source page."
            )

    def _apply(
        self,
        candidate: Candidate,
        selected: dict[str, list[str]],
        profile: ApplicantProfileIn,
        trace: DiscoveryTrace,
    ) -> None:
        """Attach what was found. A category with nothing stays None."""
        candidate.search_queries_used = trace.search_queries_sent
        candidate.extra_domains = list(trace.extra_domains)
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

    async def _admissions_host(self, entry: dict, domain: str, trace: DiscoveryTrace) -> None:
        """DI-1: read the homepage once and record its one admissions domain."""
        homepage = entry.get("homepage") or ""
        if not homepage or not same_institution(homepage, domain):
            return
        result = await self.fetcher.get(homepage)
        if not result.ok or not same_source_site(homepage, result.final_url or homepage):
            return
        record = admissions_host_from_homepage(result.text, result.final_url or homepage, domain)
        if not record:
            return
        trace.admissions_host = record
        extra = record.get("domain")
        if isinstance(extra, str):
            trace.extra_domains = [extra]

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
            for url, label in _harvest_links(
                result.text, result.final_url or start, domain, trace.extra_domains
            ):
                category, score = categorise_url(url)
                if category is None:
                    # On a catalogue page, a link whose own text names the
                    # applicant's subject is a programme lead even when the URL
                    # says nothing. Still only a lead: the page is fetched and
                    # classified like any other, and a catalogue or a news item
                    # is rejected there.
                    if not (from_catalogue and matches_field_text(label, fields)):
                        continue
                    if _url_excluded(urlparse(url).path or ""):
                        continue
                    category, score = PageCategory.PROGRAM_PAGE, 4
                    trace.kept_by_link_text.append((url, label[:80]))
                if score <= 0:
                    continue
                if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
                    if names_other_degree_level(url, degree):
                        continue
                    field_score = matches_field(url, fields)
                    score += field_score + matches_degree(url, degree)
                    if score <= 0:
                        continue
                    if (
                        NAVIGATION_FIELD_LEADS
                        and category == PageCategory.PROGRAM_PAGE
                        and fields
                        and field_score == 0
                        and not matches_field_text(label, fields)
                        and not looks_like_catalogue(url)
                    ):
                        trace.reject(url, "navigation lead names none of the applicant's subjects")
                        continue
                elif SERVICE_PAGE_PRIORITY and category in SERVICE_CATEGORIES:
                    if names_other_degree_level(url, degree) or label_names_other_level(
                        label, degree
                    ):
                        trace.reject(
                            url, f"{category} page names a degree level other than {degree}"
                        )
                        continue
                    score += matches_degree(url, degree)
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


def _harvest_links(
    html: str, base: str, domain: str, extra_domains: Sequence[str] = ()
) -> list[tuple[str, str]]:
    soup = parse_html(html)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        url = urljoin(base, anchor["href"]).split("#")[0]
        if urlparse(url).scheme not in ("http", "https"):
            continue
        if not on_institution_site(url, domain, extra_domains):
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
