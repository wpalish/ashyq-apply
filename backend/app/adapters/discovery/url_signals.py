"""What a URL looks like, before anything is fetched.

Pure functions, moved out of `live_discovery` unchanged. Nothing here touches
the network, the filesystem or a run's state: given a URL and an applicant's
subject and level, each answers one question about the URL's shape.

Keeping them apart matters because they are the part that is cheap to test
exhaustively and expensive to get wrong. Every rule here was added in response
to a real page — a research group's "BSc and MSc projects", a campus tour under
a programme path, an A-Z index shaped like a programme — and the comments say
which.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from publicsuffixlist import PublicSuffixList

#: The Public Suffix List, bundled offline by `publicsuffixlist`. A hand-built
#: table shipped here before and was necessarily incomplete: any institution
#: under a suffix it did not list was treated as a different domain, so its own
#: pages were skipped. The package carries a dated PSL snapshot and performs no
#: network access at runtime, which matters for a crawler.
_PSL = PublicSuffixList()


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
        # Universities do not agree on what to call the folder programmes
        # live in. Aalto publishes every one under "/study-options/", and
        # neither the folder nor its contents scored anything.
        (r"/study-(options?|programmes?|programs?|opportunities|choices?)/[a-z][a-z0-9-]{3,}", 4),
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
        (r"/study-(options?|programmes?|programs?|opportunities|choices?)/?$", 5),
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
    # A segment that *is* one of these words. "articles" is here because Cape
    # Town files its news under /articles, and one of those articles —
    # "…exciting-joint-degree-programmes" — was selected as a programme
    # catalogue on the strength of its slug.
    r"/(news|nieuws|actueel|press|blog|articles?|stories|events?|agenda|calendar"
    r"|vacature|vacanc|jobs?|careers?|alumni|donate|shop|library|contact|privacy"
    r"|cookie|login|signin|account|basket|cart|rss|feed|tag|author|archive)(/|$)"
    # Search endpoints, whoever provides them: /search, /google-search,
    # /site-search. UCT's is the middle one, which the bare word missed.
    # "programme-search" and "course-search" are the opposite thing — a
    # finder *for* programmes, and a legitimate catalogue — so they are
    # excluded from the exclusion.
    r"|/(?!(?:programmes?|programs?|courses?|degrees?|study|studies)-)"
    r"([a-z0-9]+-)?search(/|$|\?)"
    # A date-stamped segment is a publication, whatever folder holds it. No
    # programme page is named after the day it was written.
    r"|/\d{4}-\d{2}-\d{2}[-/]"
    r"|\.(jpg|jpeg|png|gif|svg|webp|css|js|zip|mp4|mp3|docx?|xlsx?|pptx?)$",
    re.IGNORECASE,
)

#: A programme page for the wrong level is not a match for this applicant.
_DEGREE_SLUGS: dict[str, tuple[str, ...]] = {
    "bachelor": ("bsc", "ba", "beng", "llb", "bachelor", "bachelors", "undergraduate"),
    "master": ("msc", "ma", "meng", "llm", "mba", "master", "masters", "graduate",
               "postgraduate"),
    "phd": ("phd", "doctoral", "doctorate", "dphil"),
    "foundation": ("foundation", "pre-bachelor", "preparatory"),
}


def registrable_domain(host_or_url: str) -> str:
    """The domain that owns a host, per the Public Suffix List.

    ``www.rug.nl`` and ``rug.nl`` are the same institution; ``rug.nl`` and
    ``someoneelse.nl`` are not, and ``ox.ac.uk`` and ``cam.ac.uk`` are two
    institutions rather than one ``ac.uk``.

    A full URL is accepted as well as a bare host. Callers hold homepages more
    often than hostnames, and the failure mode of not accepting one is silent:
    every comparison would answer "different institution" and discovery would
    quietly find nothing.
    """
    value = (host_or_url or "").strip().lower().rstrip(".")
    if not value:
        return ""
    if "/" in value or ":" in value:
        try:
            value = urlparse(value if "//" in value else f"//{value}").hostname or ""
        except ValueError:
            # "https://[bad::ipv6/x" raises here rather than at the parse.
            return ""
        if not value:
            return ""
    if _CONTROL_CHARACTERS.search(value):
        return ""
    return _PSL.privatesuffix(value) or value


def same_institution(url: str, domain: str) -> bool:
    """Whether a URL belongs to the institution that owns ``domain``.

    This is the check that keeps a fetch on the university's own site, so it
    answers False for anything it cannot read rather than guessing. A URL with
    no parseable host has no domain to compare, and treating "unparseable" as
    "probably fine" is how a crawler ends up somewhere it was never allowed.
    """
    if url_problem(url) is not None:
        return False
    host = urlparse(url).hostname or ""
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



#: Longer than any real university URL, and long enough that a generated or
#: hostile one is obvious. Bounded because these strings are canonicalised,
#: compared, stored in traces and read by people.
MAX_URL_LENGTH = 2048

#: Only these are fetched. `javascript:`, `data:` and `file:` appear in real
#: pages and none of them is a page on a university's website.
FETCHABLE_SCHEMES = frozenset({"http", "https"})

#: A host may not contain them, and `urlsplit` does not reject them: a NUL
#: became a space and `exa\x00mple.edu` was accepted as `exa mple.edu`, a host
#: that does not exist. Control characters in a host are also how request
#: smuggling starts, so they are refused rather than cleaned.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x20\x7f]")


def url_problem(url: str) -> str | None:
    """Why this URL cannot be used, or None if it can.

    One boundary for every way a string off a web page can fail to be a URL.
    `urlparse` is deceptive here: it accepts almost anything and defers the
    failure to `parts.port` and `parts.hostname`, which are properties that
    raise `ValueError` when read. Guarding the parse alone — which is what the
    code did — guards nothing:

        canonical_url("https://example.edu:bad/x")
        ValueError: Port could not be cast to integer value as 'bad'

    One `<a href>` like that on one page was enough to end the research for
    every institution left in the run.

    The reason is short and never quotes the URL back: traces are stored and
    read by people, and a 9,000-character string from someone else's page is
    neither useful nor safe to repeat.
    """
    if not url or not url.strip():
        return "empty"
    raw = url.strip()
    if len(raw) > MAX_URL_LENGTH:
        return f"longer than {MAX_URL_LENGTH} characters"
    if _CONTROL_CHARACTERS.search(raw):
        return "contains a control character"

    try:
        parts = urlparse(raw)
    except ValueError:
        return "not parseable as a URL"

    if parts.scheme.lower() not in FETCHABLE_SCHEMES:
        return f"scheme {parts.scheme.lower()[:20]!r} is not fetchable"

    # Reading these is where the deferred failures surface.
    try:
        host = parts.hostname
        port = parts.port
    except ValueError:
        return "host or port is malformed"

    if not host:
        return "no host"
    if port is not None and not (0 < port <= 65535):
        return "port out of range"
    return None


def is_usable(url: str) -> bool:
    """Whether this URL is worth doing anything with at all."""
    return url_problem(url) is None


def canonical_url(url: str) -> str:
    """A stable form, so the same page is not discovered twice.

    Drops the fragment and tracking parameters, lowercases the host, removes a
    default port and a trailing slash. Query parameters that select content are
    kept — dropping them would merge genuinely different pages.
    """
    if url_problem(url) is not None:
        # Nothing usable to canonicalise. Returning the input unchanged would
        # hand a caller a string that looks like a URL and is not one.
        return ""

    parts = urlparse(url.strip())
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and not (
        (parts.scheme == "http" and port == 80)
        or (parts.scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    kept = [
        pair for pair in parts.query.split("&")
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
    """How strongly a URL looks like it belongs to a category. 0 means no.

    A URL that cannot be used scores nothing, whatever its path spells. There
    is no point ranking a link that will never be fetched, and scoring it would
    let it displace a real candidate from a bounded shortlist.
    """
    if url_problem(url) is not None:
        return 0
    path = (urlparse(url).path or "").lower()
    # Exclusions first: "/library/search" ends in an index word and is still a
    # library. Recognising the index shape before ruling the page out entirely
    # turned every site search into a programme catalogue.
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
    if _INDEX_SEGMENT.search(path):
        # "/bachelors/alphabet" has a programme's shape and is a listing. It
        # is scored as the catalogue it is, so the walk follows it rather
        # than dropping it: Groningen's computing science degree is
        # reachable only through that A-Z page.
        return 5 if category == PageCategory.PROGRAM_CATALOG else 0
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


def degree_levels_named(url: str) -> set[str]:
    """Every degree level a URL names in its path.

    A set, not the first match: Europe is full of combined programmes, and
    Aalto's computer engineering page is at
    `.../computer-engineering-bachelor-of-science-and-master-of-science`.
    Returning whichever level came first in the table rejected it as the wrong
    level for whichever applicant was asking.
    """
    path = (urlparse(url).path or "").lower()
    return {
        level
        for level, slugs in _DEGREE_SLUGS.items()
        if any(re.search(rf"(^|[/-]){re.escape(slug)}([/-]|$)", path) for slug in slugs)
    }


def degree_level_named(url: str) -> str | None:
    """One level a URL names, for scoring. Prefers none over an arbitrary pick."""
    named = degree_levels_named(url)
    return next(iter(named)) if len(named) == 1 else None


#: Last path segments that make a page an index of programmes rather than one
#: of them. Universities publish an A-Z, a by-subject view and an
#: English-taught view of the same catalogue, and Groningen's computing science
#: degree is reachable only through the first of those. None of these words is
#: a subject, so a real programme slug cannot be caught by them.
_INDEX_SEGMENT = re.compile(
    r"/(alphabet|a-?z|by-?subject|by-?faculty|by-?field|by-?language|by-?level"
    r"|in-?english|all|list|listing|index|overview|finder|search|browse"
    r"|[a-z-]*-(finder|search|overview|list|index)|full-?list)/?$",
    re.IGNORECASE,
)

#: A path segment that ends with a listing word. UBC's catalogue lives at
#: ``/applying-ubc/how-to-apply/degrees-programs/``, which scores higher as an
#: admissions page than as a catalogue — so whether a page is worth walking for
#: programmes is asked separately from which category it best fits.
_CATALOGUE_PATH = re.compile(
    r"/[a-z0-9-]*(programmes?|programs?|degrees?|courses?|studies)/?$"
    # The folder a site keeps its programmes in is a listing page. Written
    # separately from the suffix rule above because "study-options" ends in a
    # word that is not itself a listing word.
    r"|/study-(options?|programmes?|programs?|opportunities|choices?)/?$",
    re.IGNORECASE,
)


def looks_like_catalogue(url: str) -> bool:
    """Whether a URL looks like a page that lists programmes."""
    path = urlparse(url).path or ""
    if _URL_EXCLUSIONS.search(path):
        return False
    return bool(_CATALOGUE_PATH.search(path) or _INDEX_SEGMENT.search(path))


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
    named = degree_levels_named(url)
    if not named:
        return 0
    return 4 if str(degree) in named else -6


def names_other_degree_level(url: str, degree: str) -> bool:
    """Whether a URL names *only* levels the applicant did not ask for.

    Treated as an outright rejection rather than a score penalty. An MSc page
    is not a weak bachelor lead, it is the wrong page, and a subject-name bonus
    ("computer", "science") must not be able to outweigh the level.

    A URL naming both levels names the applicant's, so it is not rejected.
    """
    named = degree_levels_named(url)
    return bool(named) and str(degree) not in named
