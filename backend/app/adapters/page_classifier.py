"""What kind of page is this?

Every false positive found in the first live run had the same shape: an
extractor ran on a page that could not possibly answer the question it was
asking. A page titled "Check admission requirements | BSc Dutch diploma"
cannot confirm that a computer science bachelor's programme exists; a page
titled "Scholarships" is not a scholarship.

Classification happens once per page, from the URL, the title, the headings and
the body structure. Extractors declare which classes they accept and are not
run otherwise. The classifier is deliberately conservative: when the signals do
not add up it returns UNKNOWN, and UNKNOWN is accepted by nothing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


class PageType(StrEnum):
    PROGRAM_DETAIL = "program_detail"
    PROGRAM_CATALOG = "program_catalog"
    INTAKE_SPECIFIC_PROGRAM = "intake_specific_program"
    GENERAL_ADMISSIONS = "general_admissions"
    COUNTRY_CREDENTIAL_REQUIREMENTS = "country_credential_requirements"
    SCHOLARSHIP_INDEX = "scholarship_index"
    SCHOLARSHIP_AWARD = "scholarship_award"
    SCHOLARSHIP_FAQ = "scholarship_faq"
    COSTS = "costs"
    DOCUMENTS = "documents"
    NEWS = "news"
    NAVIGATION = "navigation"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


#: Page classes each extractor is permitted to run on. Anything else is skipped
#: and reported, never guessed at.
ACCEPTS: dict[str, frozenset[PageType]] = {
    "program_exists": frozenset({PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "requirements": frozenset({
        PageType.PROGRAM_DETAIL,
        PageType.INTAKE_SPECIFIC_PROGRAM,
        PageType.GENERAL_ADMISSIONS,
        PageType.COUNTRY_CREDENTIAL_REQUIREMENTS,
    }),
    "intake": frozenset({PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "costs": frozenset({PageType.COSTS, PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "scholarship_award": frozenset({PageType.SCHOLARSHIP_AWARD}),
    # A fees page often lists the awards alongside the costs; following its
    # links is safe because each target must classify as an award itself.
    "scholarship_links": frozenset({
        PageType.SCHOLARSHIP_INDEX, PageType.SCHOLARSHIP_AWARD, PageType.COSTS,
    }),
    "documents": frozenset({
        PageType.DOCUMENTS,
        PageType.PROGRAM_DETAIL,
        PageType.INTAKE_SPECIFIC_PROGRAM,
        PageType.GENERAL_ADMISSIONS,
        PageType.SCHOLARSHIP_AWARD,
    }),
}


@dataclass(frozen=True)
class PageClassification:
    page_type: PageType
    confidence: float
    signals: list[str] = field(default_factory=list)
    title: str = ""
    #: Present when the page identifies one programme or one award.
    subject: str | None = None
    degree_level: str | None = None
    language_of_instruction: str | None = None
    academic_year: str | None = None

    def accepts(self, extractor: str) -> bool:
        return self.page_type in ACCEPTS.get(extractor, frozenset())


# --- signal vocabularies ---------------------------------------------------

_DEGREE_WORDS: tuple[tuple[str, str], ...] = (
    (r"\bph\.?d\b|\bdoctoral\b|\bdoctorate\b", "phd"),
    (r"\bmaster'?s?\b|\bm\.?sc\b|\bm\.?a\b\.?|\bmphil\b|\bllm\b|\bmba\b", "master"),
    # HBSc and HBA are how Ontario universities write an honours bachelor's
    # degree. A page stating only "HBSc" was read as stating no level at all.
    (
        r"\bbachelor'?s?\b|\bb\.?sc\b|\bb\.?a\b\.?|\bbeng\b|\bllb\b|\bundergraduate\b"
        r"|\bhb\.?sc\b|\bhba\b|\bhonours bachelor\b",
        "bachelor",
    ),
    (r"\bfoundation year\b|\bpre-?bachelor\b", "foundation"),
)
# "explore" and "discover" lead a listing as often as "browse" does, and
# _PLURAL_PROGRAM_HEADING already treated them that way. The two vocabularies
# disagreeing meant "Explore Programs in data & computer science" — a heading
# over a list of five programmes — carried no catalogue signal at all.
_CATALOG = re.compile(
    r"\b(programmes?|programs?|courses?|degrees?|studies)\b.*\b(overview|list|all|browse|find|search|a-?z)\b"
    r"|\b(all|our|browse|find|search|explore|discover)\b.*\b(programmes?|programs?|courses?|degrees?)\b",
    re.IGNORECASE,
)
#: A heading that is a plural category is a listing, never one programme or one
#: award. "Bachelor's programmes" is a catalogue; "BSc Computer Science" is not.
_PLURAL_PROGRAM_HEADING = re.compile(
    r"^\s*((our|all|available|browse|find|search|list of|overview of|explore)\s+)?"
    r"((bachelor'?s?|master'?s?|undergraduate|postgraduate|graduate|phd|doctoral)\s+)?"
    # One qualifier between the level and the listing word. "Bachelor's degree
    # programmes" and "All study programmes" are how a great many universities
    # head a listing, and requiring the two words to be adjacent missed them —
    # so those pages fell through to UNKNOWN and their entries were never read.
    r"((degree|study|taught|research|academic|full-?time|part-?time)\s+)?"
    r"(programmes?|programs?|courses?|degrees?|studies)\s*$",
    re.IGNORECASE,
)
_PLURAL_FUNDING_HEADING = re.compile(
    r"^\s*((our|all|available|list of|overview of|other|external)\s+)?"
    r"(scholarships|funding|financial aid|grants|bursaries|awards|fellowships|stipends"
    r"|prizes and awards|practical matters)"
    # A plural category followed by a scope phrase is still a listing:
    # "Scholarships from other providers", "Grants for international students".
    r"(\s+(and|&|from|for|at|by|in|of|to)\s+.{0,60})?\s*$",
    re.IGNORECASE,
)
_ADMISSIONS = re.compile(
    r"admission requirements|entry requirements|how to apply|application procedure"
    r"|admission and application|apply for admission|entry criteria"
    # A page headed "International admissions" or "Undergraduate admissions" is
    # a general admissions page even though it never says "requirements".
    r"|\b(?:international|undergraduate|graduate|postgraduate|general)\s+admissions?\b"
    r"|\badmissions?\b\s*(?:-|–|\||$)|general entry information",
    re.IGNORECASE,
)
_CREDENTIAL = re.compile(
    r"\b(diploma|qualification|certificate)\b[^.]{0,60}\b(equivalen|recogni|accept|assess)"
    r"|\b(vwo|abitur|attestat|baccalaur|a-?levels?|matura|gaokao|cbse)\b",
    re.IGNORECASE,
)
_SCHOLARSHIP_WORD = re.compile(
    r"scholarship|bursar|grant|fellowship|financial aid|stipend|funding|beurs|stipendium",
    re.IGNORECASE,
)
#: "Recruitment" means students as often as staff on a university site — HKU
#: publishes its joint admission route as the "Undergraduate Recruitment
#: Scheme". Only hiring context makes it irrelevant.
_STAFF_RECRUITMENT = re.compile(
    r"\b(staff|academic|faculty|employee|personnel)\s+recruitment\b"
    r"|\brecruitment\b[^.]{0,40}\b(vacanc\w*|career\w*|jobs?|posts?|hiring)\b"
    r"|\b(vacanc\w*|career\w*|jobs?|hiring)\b[^.]{0,40}\brecruitment\b",
    re.IGNORECASE,
)
_FAQ = re.compile(r"\bf\.?a\.?q\.?\b|frequently asked question", re.IGNORECASE)
_NEWS = re.compile(r"\b(news|press release|announcement|blog|article)\b", re.IGNORECASE)
_IRRELEVANT = re.compile(
    r"\b(vacanc|job openings?|careers? (?:at|portal|site)|staff directory"
    r"|alumni|donate|shop|library catalogue|contact us|privacy (?:policy|statement)"
    r"|cookie|sitemap|nobel prize|erc grant|research (?:prize|award)s?)\b",
    re.IGNORECASE,
)
#: Plurals matter: `\btuition fee\b` does not match "tuition fees", which is how
#: a fees page ended up classified as general admissions.
_COSTS = re.compile(
    r"\b(tuition fees?|registration fees?|enrolment fees?|enrollment fees?"
    r"|cost of attendance|costs? of study|fees? and (?:funding|costs?)"
    r"|tuition and fees?|study costs?|living costs?|statement of fees?"
    r"|fees? overview|what it costs)\b",
    re.IGNORECASE,
)
_DOCUMENTS = re.compile(
    r"\b(required documents|documents you need|document checklist|supporting documents"
    r"|what to submit|upload(?:ing)? documents)\b",
    re.IGNORECASE,
)
#: Sections a programme page has and a listing does not. A catalogue links to
#: curricula; a programme page contains one.
_PROGRAMME_DETAIL_SECTION = re.compile(
    r"\b(curriculum|programme structure|program structure|course structure"
    r"|what you will learn|what to expect from the|study programme|studieprogramma"
    r"|entry requirements|admission requirements|after (?:your |the )?stud(?:y|ies)"
    r"|career prospects|degree awarded|credits?|ects|duration of (?:the )?programme)\b",
    re.IGNORECASE,
)

#: A page has to say something substantive about an award to be an award page.
_AWARD_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("amount", re.compile(r"\b(amount|value|worth|covers?|waiver|per year|per month|% of tuition)\b", re.I)),
    ("coverage", re.compile(r"\b(covers?|coverage|includes?|tuition|housing|accommodation|stipend|living costs)\b", re.I)),
    ("eligibility", re.compile(r"\b(eligib|who can apply|criteria|requirements|open to|restricted to)\b", re.I)),
    ("application", re.compile(r"\b(how to apply|apply for this|nominat|no separate application|separate application)\b", re.I)),
    ("deadline", re.compile(r"\b(deadline|closing date|applications? close|apply by)\b", re.I)),
    ("duration", re.compile(r"\b(renewable|duration|for the duration|years of study|one-?time)\b", re.I)),
)
_ACADEMIC_YEAR = re.compile(r"\b(20\d{2})\s*[/–—-]\s*(\d{2}|20\d{2})\b")
_LANGUAGE = re.compile(
    r"\b(?:taught|instruction|language of instruction)\b[^.]{0,40}?\b(english|dutch|german|french|finnish|polish)\b"
    r"|\b(english|dutch|german|french|finnish|polish)[- ]taught\b",
    re.IGNORECASE,
)

#: URL path fragments that are strong evidence on their own.
_PATH_HINTS: tuple[tuple[re.Pattern[str], PageType], ...] = (
    (re.compile(r"/(news|nieuws|actueel|press)/"), PageType.NEWS),
    (re.compile(r"(careers?|vacanc|jobs?|werken-bij)\."), PageType.IRRELEVANT),
    (re.compile(r"/(vacature|vacancies|jobs|careers)/"), PageType.IRRELEVANT),
)


#: schema.org types that say, in the site's own markup, what this page is.
#: Only trusted from the document's JSON-LD, never from arbitrary page text.
_LD_PROGRAM_TYPES = frozenset({"educationaloccupationalprogram", "course"})
_LD_CATALOG_TYPES = frozenset({"collectionpage", "itemlist", "searchresultspage"})


def structured_page_types(soup: BeautifulSoup | None) -> set[str]:
    """Lower-cased schema.org @type values declared in the page's JSON-LD.

    Read from the whole document, because JSON-LD normally sits in <head>.
    Malformed JSON is ignored rather than raising: this is a signal, not a
    contract, and a broken blob must not cost us the page.
    """
    if soup is None:
        return set()
    found: set[str] = set()

    def collect(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                collect(item)
            return
        if not isinstance(node, dict):
            return
        raw = node.get("@type")
        for value in raw if isinstance(raw, list) else [raw]:
            if isinstance(value, str):
                found.add(value.strip().lower())
        for key in ("@graph", "mainEntity", "hasPart", "about"):
            if key in node:
                collect(node[key])

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            collect(json.loads(script.string or ""))
        except (ValueError, TypeError):
            continue
    return found


#: Wrappers that hold the page's own content rather than the site's furniture.
_MAIN_SELECTORS = ("main", "[role=main]", "#main-content", "#main", "#content", "article")
#: Site chrome. Present on every page, so counting its links made an award page
#: look like an index and an admissions page look like a catalogue.
_CHROME_TAGS = ("nav", "header", "footer", "aside")
_CHROME_HINT = re.compile(
    r"nav|menu|breadcrumb|header|footer|sidebar|skip|cookie|banner|social|share|toolbar",
    re.IGNORECASE,
)


def main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """The page's own content, with the site's navigation removed.

    Every page on a university site carries the same global menu. Reading the
    first <h1> or counting links across the whole document therefore measured
    the site, not the page: a single award page linked to six other awards from
    its menu and was classified as an index.
    """
    working = BeautifulSoup(str(soup), "lxml")
    for tag in working(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    for selector in _MAIN_SELECTORS:
        found = working.select_one(selector)
        if found is not None and len(found.get_text(strip=True)) > 200:
            for tag in found(_CHROME_TAGS):
                tag.decompose()
            return found

    for tag in working(_CHROME_TAGS):
        tag.decompose()
    for tag in working.find_all(attrs={"class": _CHROME_HINT}):
        tag.decompose()
    for tag in working.find_all(attrs={"id": _CHROME_HINT}):
        tag.decompose()
    return working


def classify_page(*, url: str, html: str = "", text: str = "") -> PageClassification:
    """Classify a fetched page. Never raises; unknown is a valid answer."""
    full = BeautifulSoup(html, "lxml") if html else None
    soup = main_content(full) if full is not None else None
    title = _title(full) if full is not None else ""
    headings = _headings(soup) if soup else []
    identity = _identity(soup, title)  # from the content region, not the menu
    body = text or (_text(soup) if soup else "")
    head = " ".join([title, *headings])
    low_head = head.lower()
    low_body = body.lower()
    path = urlparse(url).path.lower()
    host = urlparse(url).netloc.lower()
    signals: list[str] = []

    for pattern, page_type in _PATH_HINTS:
        if pattern.search(host) or pattern.search(path):
            return PageClassification(page_type, 0.85, [f"url matches {pattern.pattern}"], title)

    # --- clearly not about studying here --------------------------------
    off_topic = _IRRELEVANT.search(low_head) or _STAFF_RECRUITMENT.search(low_head)
    if off_topic is not None:
        return PageClassification(
            PageType.IRRELEVANT, 0.8,
            [f"the heading is off-topic: {off_topic.group(0)!r}"], title,
        )

    if _NEWS.search(low_head):
        return PageClassification(PageType.NEWS, 0.75, ["news markers in the title"], title)

    # --- mostly links and little prose ----------------------------------
    if soup is not None and body and len(body) < 1500:
        link_text = sum(len(a.get_text(strip=True)) for a in soup.find_all("a"))
        if link_text / max(len(body), 1) > 0.75:
            signals.append("page is mostly link text")
            return PageClassification(PageType.NAVIGATION, 0.6, signals, title)

    # --- cost pages --------------------------------------------------------
    if _COSTS.search(identity) or _COSTS.search(title.lower()):
        return PageClassification(
            PageType.COSTS, 0.8, ["cost vocabulary in the page heading"], title,
            academic_year=_academic_year(body),
        )

    # --- funding family ---------------------------------------------------
    # A programme page aimed at international applicants almost always carries
    # a "Tuition fees and scholarships" section. Claiming every page whose
    # headings mention funding read Aalto's only bachelor's computing programme
    # as a list of awards, so a page that names one programme in its own
    # heading is left to the programme branch below.
    names_one_programme = bool(_program_name(identity)) and not _PLURAL_FUNDING_HEADING.match(
        identity
    )
    if not names_one_programme and (
        _SCHOLARSHIP_WORD.search(low_head) or "scholarship" in path or "financial-aid" in path
    ):
        if _FAQ.search(low_head):
            return PageClassification(PageType.SCHOLARSHIP_FAQ, 0.9, ["FAQ markers"], title)

        award_links = _award_link_count(soup) if soup else 0
        present = [name for name, pattern in _AWARD_SIGNALS if pattern.search(low_body)]
        named = _award_name(identity)
        plural_index = bool(
            _PLURAL_FUNDING_HEADING.match(identity)
            or re.search(r"\b(overview of|list of|available) (scholarships|funding|grants)\b", low_body)
        )

        # A listing heading, or several links out to named awards, or links out
        # with no award identity of its own.
        if plural_index or award_links >= 2 or (award_links >= 1 and named is None):
            signals += [
                f"{award_links} award links",
                "listing heading" if plural_index else "",
                "no award identity of its own" if named is None else "",
            ]
            return PageClassification(
                PageType.SCHOLARSHIP_INDEX, 0.8, [s for s in signals if s], title
            )
        # A named award plus at least two substantive signals.
        if named and len(present) >= 2:
            return PageClassification(
                PageType.SCHOLARSHIP_AWARD, 0.75 + 0.05 * min(len(present), 4),
                [f"named award {named!r}", f"signals: {', '.join(present)}"],
                title, subject=named,
                degree_level=_degree_level(f"{head} {body[:2500]}"),
                academic_year=_academic_year(body),
            )
        return PageClassification(
            PageType.UNKNOWN, 0.3,
            [f"funding page with {len(present)} substantive signals and no clear award name"],
            title,
        )

    if _DOCUMENTS.search(low_head):
        return PageClassification(PageType.DOCUMENTS, 0.7, ["document checklist heading"], title)

    # --- programme family --------------------------------------------------
    # A programme page is identified before the admissions rules run: a real
    # programme page has an "entry requirements" section, and matching that
    # first classified BSc Computer Science and Engineering as a general
    # admissions page.
    subject = _program_name(identity)
    # Nearest-first. The body of a programme page carries the site's menu of
    # other programmes, so scanning it as one blob returned whichever level
    # appeared earliest: Groningen's bachelor page read as a master's because
    # "master" appears in its navigation before "bachelor" appears in its text.
    degree = _degree_nearest(identity, title, headings, body)
    language = _language(body)
    year = _academic_year(body)

    program_links = _program_link_count(soup, url) if soup else 0
    plural_heading = bool(_PLURAL_PROGRAM_HEADING.match(identity))

    # The subject may be in the heading and the degree somewhere else. Look for
    # the level in the title and the subheadings too, but only for a page whose
    # heading names a subject and which carries the sections a programme page
    # has: that keeps a faculty or department page, which names a subject and
    # nothing else, from being promoted.
    detail_sections = len(set(_PROGRAMME_DETAIL_SECTION.findall(f"{head} {body[:6000]}")))
    if subject is None and _names_a_subject(identity) and detail_sections >= 2:
        level_elsewhere = _degree_level(f"{title} {' '.join(headings[:6])}")
        if level_elsewhere:
            subject = identity
            degree = degree or level_elsewhere
            signals.append(
                f"the heading names a subject and the page states the {level_elsewhere} "
                f"level elsewhere, with {detail_sections} programme sections"
            )
    # `_CATALOG` is matched against each heading on its own. Run against the
    # headings joined into one string its `.*` bridged unrelated headings:
    # "…our three campuses" and a later "explore programs" combined into a
    # catalogue match on a page whose headings say no such thing.
    catalog_heading = next(
        (h for h in [title, *headings] if _CATALOG.search(h.lower())), None
    )
    ld_types = structured_page_types(full)
    ld_program = sorted(ld_types & _LD_PROGRAM_TYPES)
    ld_catalog = sorted(ld_types & _LD_CATALOG_TYPES)

    # The site's own structured data outranks our guesses about its markup.
    if ld_program and subject and not plural_heading:
        signals.append(f"schema.org {', '.join(ld_program)}")
        return _programme_result(
            [*signals, f"single programme {subject!r}"], title, subject,
            degree or "unknown", language, year, confidence=0.9,
        )

    catalogue_reasons = [
        r for r in (
            "plural catalogue heading" if plural_heading else "",
            f"catalogue phrasing in heading {catalog_heading!r}" if catalog_heading else "",
            f"links to {program_links} other programmes" if program_links >= 5 else "",
            f"schema.org {', '.join(ld_catalog)}" if ld_catalog else "",
        ) if r
    ]
    # A page listing this many distinct other programmes is a listing by
    # construction: no single programme needs to link to a dozen siblings. This
    # outranks a programme-shaped heading, so a catalogue titled after one of
    # its entries cannot present itself as that programme.
    #
    # One exception, and it is narrow: a page that names one programme *and*
    # carries that programme's own curriculum sections is that programme, even
    # under a site-wide A-Z menu. Groningen renders 43 other programmes into
    # every programme page's navigation. A catalogue does not carry a
    # curriculum — it links to them — so the sections are what separate the
    # two, not the link count.
    own_programme_page = bool(
        subject and not plural_heading and detail_sections >= MIN_DETAIL_SECTIONS
    )
    if program_links >= MANY_PROGRAMME_LINKS and not own_programme_page:
        return PageClassification(
            PageType.PROGRAM_CATALOG, 0.8,
            [f"links to {program_links} distinct other programmes"], title,
        )

    # A page that names one programme is that programme, even when it links to
    # others; only a page with no single identity is decided by its links.
    if catalogue_reasons and not (subject and degree and not plural_heading):
        return PageClassification(
            PageType.PROGRAM_CATALOG, 0.75, catalogue_reasons, title,
        )

    if not subject:
        if _CREDENTIAL.search(low_head) and _ADMISSIONS.search(low_head):
            return PageClassification(
                PageType.COUNTRY_CREDENTIAL_REQUIREMENTS, 0.75,
                ["admissions page scoped to a diploma type"], title,
            )
        if _ADMISSIONS.search(low_head):
            return PageClassification(
                PageType.GENERAL_ADMISSIONS, 0.8,
                ["admissions phrasing without a single programme identity"], title,
            )

    if subject and degree:
        if program_links:
            signals.append(f"links to {program_links} other programmes, but names only one")
        return _programme_result(
            [*signals, f"single programme {subject!r} at {degree} level"],
            title, subject, degree, language, year,
        )

    if _CREDENTIAL.search(low_head) and _ADMISSIONS.search(low_head):
        return PageClassification(
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS, 0.7,
            ["admissions page scoped to a diploma type"], title,
        )
    if _ADMISSIONS.search(low_head):
        return PageClassification(
            PageType.GENERAL_ADMISSIONS, 0.7, ["admissions phrasing"], title
        )
    cost_mentions = len(_COSTS.findall(low_body))
    if cost_mentions >= 2:
        return PageClassification(
            PageType.COSTS, 0.6, [f"{cost_mentions} cost phrases in the body"], title,
            academic_year=_academic_year(body),
        )

    if _CREDENTIAL.search(low_body[:2000]):
        return PageClassification(
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS, 0.55, ["credential vocabulary"], title
        )

    return PageClassification(PageType.UNKNOWN, 0.2, ["no decisive signals"], title)


# --- helpers ---------------------------------------------------------------


def _programme_result(
    signals: list[str], title: str, subject: str, degree: str,
    language: str | None, year: str | None, confidence: float = 0.75,
) -> PageClassification:
    """One programme page, intake-specific when it names an academic year."""
    signals = [s for s in signals if s.strip()]
    if language:
        signals.append(f"language of instruction: {language}")
    if year:
        return PageClassification(
            PageType.INTAKE_SPECIFIC_PROGRAM, max(confidence, 0.85),
            [*signals, f"academic year {year}"], title,
            subject=subject, degree_level=degree,
            language_of_instruction=language, academic_year=year,
        )
    return PageClassification(
        PageType.PROGRAM_DETAIL, confidence, signals, title,
        subject=subject, degree_level=degree, language_of_instruction=language,
    )


def _title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())[:200]
    h1 = soup.find("h1")
    return " ".join(h1.get_text(" ", strip=True).split())[:200] if h1 else ""


#: Regions every page on a site repeats. Their headings describe the site, not
#: the page, and they come first in document order — so before they were
#: excluded they consumed the leading-heading windows below and the checks that
#: read them saw only navigation. They are also actively misleading: a header
#: that reads "Find the program that's right for you" is catalogue phrasing
#: present verbatim on a catalogue and on a single programme page alike.
_CHROME_REGIONS = ("nav", "header", "footer", "aside")


def _in_chrome(tag) -> bool:
    return any(parent.name in _CHROME_REGIONS for parent in tag.parents)


def _headings(soup: BeautifulSoup) -> list[str]:
    """The page's own headings, in order, with site chrome left out.

    Falls back to every heading when excluding chrome would leave nothing: some
    pages wrap all their content in <header>, and no headings at all is worse
    than headings that need care.
    """
    found = soup.find_all(["h1", "h2"])
    own = [h for h in found if not _in_chrome(h)]
    return [" ".join(h.get_text(" ", strip=True).split()) for h in (own or found)][:12]


def _text(soup: BeautifulSoup) -> str:
    from app.adapters.extraction import html_to_text

    return html_to_text(str(soup))


def _degree_nearest(
    identity: str, title: str, headings: list[str], body: str
) -> str | None:
    """The degree level, taken from the most specific place that states it.

    The page's own heading is the most reliable, then its browser title, then
    its subheadings, and only then the body — which on a university site is
    full of links to programmes at other levels.
    """
    for source in (identity, title, " ".join(headings[:6]), body[:2500]):
        level = _degree_level(source)
        if level:
            return level
    return None


def _degree_level(text: str) -> str | None:
    low = text.lower()
    for pattern, level in _DEGREE_WORDS:
        if re.search(pattern, low):
            return level
    return None


def _language(text: str) -> str | None:
    m = _LANGUAGE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").lower() or None


def _academic_year(text: str) -> str | None:
    m = _ACADEMIC_YEAR.search(text)
    if not m:
        return None
    end = m.group(2)
    return f"{m.group(1)}/{end[-2:]}"


#: Headings that label a section of the site rather than name this page. Aalto
#: heads every programme page "Study options" and puts the programme's name in
#: the browser title and the first content heading; taking the h1 literally
#: gave every one of its programmes the same identity.
_SECTION_LABEL_HEADING = re.compile(
    r"^\s*(study options?|study|studies|education|programmes?|programs?|admissions?"
    r"|apply|application|home|menu|search|overview|courses?|degrees?"
    r"|for (?:prospective )?students?|international students?)\s*$",
    re.IGNORECASE,
)


def _identity(soup: BeautifulSoup | None, title: str) -> str:
    """What the page says it is about.

    Its h1, unless that is a section label — then the browser title before the
    site suffix, and failing that the first content heading that says
    something. A page whose only identity is "Study options" is telling us
    where it sits, not what it is.
    """
    from_title = title.split("|")[0].strip()
    if soup is None:
        return from_title

    h1 = soup.find("h1")
    heading = " ".join(h1.get_text(" ", strip=True).split()) if h1 else ""
    if heading and not _SECTION_LABEL_HEADING.match(heading):
        return heading

    if from_title and not _SECTION_LABEL_HEADING.match(from_title):
        return from_title

    for other in soup.find_all(["h1", "h2"])[:4]:
        text = " ".join(other.get_text(" ", strip=True).split())
        if text and not _SECTION_LABEL_HEADING.match(text):
            return text
    return heading or from_title


#: Words that name a level rather than a subject, stripped when testing
#: whether a heading names an actual programme.
_LEVEL_WORDS_ONLY = re.compile(
    r"\b(bachelor'?s?|master'?s?|undergraduate|postgraduate|graduate|doctoral|doctorate"
    r"|phd|dphil|bsc|msc|ba|ma|beng|meng|llb|llm|mba|foundation|programmes?|programs?"
    r"|degrees?|courses?|studies|hons|honours)\b",
    re.IGNORECASE,
)


#: Nouns that make a heading something other than a programme, however many
#: degree words it carries. A research group's "MSc and BSc projects" page is
#: not a degree.
_NOT_A_PROGRAMME_NOUN = re.compile(
    r"\b(projects?|theses|thesis|vacanc(y|ies)|internships?|placements?|tours?"
    r"|open day|openday|newsletters?|webinars?|events?|stories|experiences?"
    r"|supervisors?|staff|contact|week|fair|webklas\w*|prospectus)\b",
    re.IGNORECASE,
)


#: A heading that describes an offering rather than naming a degree. A
#: programme is named by a noun phrase; "Aalto offers five study options in
#: Science and Technology at Bachelor's level" is a sentence about an offering,
#: and accepting it as a programme is a subject hub read as a degree.
_HEADING_IS_A_SENTENCE = re.compile(
    r"\b(offers?|offering|provides?|includes?|features?|choose|select|explore"
    r"|discover|find|browse|available|welcome|introduc\w+)\b"
    r"|\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(study\s+)?(options?|programmes?|programs?|degrees?|courses?|choices?)\b"
    r"|\ba range of\b",
    re.IGNORECASE,
)


def _names_a_subject(identity: str) -> bool:
    """Whether a heading names a subject at all, level words removed.

    Split out of `_program_name` because the subject and the degree can be
    stated in different places: Groningen heads its computing science page
    "Computing Science" and puts "Bachelor's programme" in the title and the
    first subheading. Requiring both in the H1 rejected a real programme page.
    """
    name = (identity or "").strip()
    if not name or len(name) > 120:
        return False
    if _PLURAL_PROGRAM_HEADING.match(name):
        return False
    if name.endswith("?") or re.match(
        r"^(check|how|what|apply|find|browse|search)\b", name, re.I
    ):
        return False
    if _NOT_A_PROGRAMME_NOUN.search(name):
        return False
    if _SECTION_LABEL_HEADING.match(name):
        return False
    if _HEADING_IS_A_SENTENCE.search(name):
        return False
    without_level = _LEVEL_WORDS_ONLY.sub(" ", name)
    return len(re.sub(r"[^a-z]+", "", without_level.lower())) >= 4


def _program_name(identity: str) -> str | None:
    """The programme a page is about, if it is about exactly one."""
    name = identity
    if not name or len(name) > 120:
        return None
    if _PLURAL_PROGRAM_HEADING.match(name):
        return None
    if not _degree_level(name):
        return None
    # A bare level is not a programme. TU Delft's bachelor catalogue is headed
    # "Bachelors", which carries a degree word and nothing else; without this
    # the catalogue would name itself as a programme called "Bachelors".
    without_level = _LEVEL_WORDS_ONLY.sub(" ", name)
    if len(re.sub(r"[^a-z]+", "", without_level.lower())) < 4:
        return None
    # A heading that is a question or an instruction is not a programme name.
    if name.endswith("?") or re.match(r"^(check|how|what|apply|find|browse|search)\b", name, re.I):
        return None
    # "MSc and BSc projects" carries two degree words and names no programme.
    if _NOT_A_PROGRAMME_NOUN.search(name):
        return None
    # Nor does a sentence: "We offer three bachelor's programmes in engineering"
    # carries a degree word and describes an offering.
    if _HEADING_IS_A_SENTENCE.search(name):
        return None
    return name


def _award_name(identity: str) -> str | None:
    name = identity
    if not name or len(name) > 160:
        return None
    if name.endswith("?") or _FAQ.search(name):
        return None
    # A plural category heading is an index, not an award.
    if _PLURAL_FUNDING_HEADING.match(name) or re.fullmatch(
        r"(admission services|menu.*|search.*)", name.strip(), re.IGNORECASE
    ):
        return None
    if not _SCHOLARSHIP_WORD.search(name) and not re.search(r"\b(award|prize|fund|fellowship)\b", name, re.I):
        return None
    return name


def _award_link_count(soup: BeautifulSoup | None) -> int:
    if soup is None:
        return 0
    return sum(
        1 for a in soup.find_all("a", href=True)
        if _SCHOLARSHIP_WORD.search(a.get_text(" ", strip=True) or "")
        and not _FAQ.search(a.get_text(" ", strip=True) or "")
    )


#: Distinct other-programme links above which a page is a listing whatever its
#: heading says. Measured against real pages: TU Delft's bachelor catalogue
#: links to 14, while its individual programme pages link to 0-8.
MANY_PROGRAMME_LINKS = 12
#: Programme-detail sections a page must carry before its own identity is
#: allowed to outweigh a site-wide menu of other programmes.
MIN_DETAIL_SECTIONS = 3

_PROGRAM_HREF = re.compile(
    r"/(bsc|msc|ba|ma|bachelor|master|programme|program|course)s?/", re.IGNORECASE
)


def _path_key(url: str) -> str:
    """A comparable path: lower-cased, no trailing slash, no query or fragment."""
    try:
        path = urlparse(url).path.lower().rstrip("/")
    except ValueError:
        return ""
    return re.sub(r"/{2,}", "/", path)


#: Link wording that names a section of the current page rather than another
#: programme. TU Delft's BSc Aerospace Engineering page carries eighteen hrefs
#: containing "/bachelors/" — "About the programme", "After your studies",
#: "From application to enrolment", "FAQ's" and fifteen student stories.
#: Counting those classified the programme page as a catalogue of eighteen.
_SECTION_LINK_TEXT = re.compile(
    r"^(about|after|before|during|from|why|how|what|contact|apply|application"
    r"|admission|enrol|entry|faq|frequently|curriculum|programme structure"
    r"|career|student|studies|testimonial|experience|stor(y|ies)|meet|more"
    r"|read|view|see|all|back|next|previous|home|download|watch|listen)\b"
    r"|^\W*$",
    re.IGNORECASE,
)
#: Path segments that mark a sub-page of one programme, not another programme.
_SECTION_PATH = re.compile(
    r"/(student-experiences?|student-stories|testimonials?|faq|frequently-asked"
    r"|about-the-programme|after-your-studies|from-application-to-enrol"
    r"|selection-procedure|open-day|why-)",
    re.IGNORECASE,
)


def _program_link_count(soup: BeautifulSoup | None, page_url: str = "") -> int:
    """How many *other* programmes this page links to.

    What separates a programme page from a catalogue is not how many
    programme-shaped hrefs it carries — both carry many — but what the links
    say. A catalogue's links name subjects ("Applied Mathematics", "Civil
    Engineering"); a programme's links name its own sections ("About the
    programme", "After your studies") and its student stories.

    Descendant-ness deliberately does *not* disqualify a link: a catalogue at
    `/programmes/bachelors` lists `/programmes/bachelors/<subject>`, so
    excluding its own subtree would blind us to exactly the pages that make it
    a catalogue.

    Off-site links are excluded — a share button pointing at a `/sharer/` path
    is not a programme. Targets are deduplicated.
    """
    if soup is None:
        return 0
    own_host = urlparse(page_url).netloc.lower() if page_url else ""
    own = _path_key(page_url)
    targets: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not _PROGRAM_HREF.search(href):
            continue
        absolute = urljoin(page_url, href) if page_url else href
        if own_host and (urlparse(absolute).netloc.lower() or own_host) != own_host:
            continue
        target = _path_key(absolute)
        if not target or target == own:
            continue
        if _SECTION_PATH.search(target):
            continue
        if _SECTION_LINK_TEXT.search(" ".join(anchor.get_text(" ").split())):
            continue
        targets.add(target)
    return len(targets)
