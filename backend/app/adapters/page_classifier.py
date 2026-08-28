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

import re
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse

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
    "scholarship_links": frozenset({PageType.SCHOLARSHIP_INDEX, PageType.SCHOLARSHIP_AWARD}),
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
    (r"\bbachelor'?s?\b|\bb\.?sc\b|\bb\.?a\b\.?|\bbeng\b|\bllb\b|\bundergraduate\b", "bachelor"),
    (r"\bfoundation year\b|\bpre-?bachelor\b", "foundation"),
)
_CATALOG = re.compile(
    r"\b(programmes?|programs?|courses?|degrees?|studies)\b.*\b(overview|list|all|browse|find|search|a-?z)\b"
    r"|\b(all|our|browse|find|search)\b.*\b(programmes?|programs?|courses?|degrees?)\b",
    re.IGNORECASE,
)
#: A heading that is a plural category is a listing, never one programme or one
#: award. "Bachelor's programmes" is a catalogue; "BSc Computer Science" is not.
_PLURAL_PROGRAM_HEADING = re.compile(
    r"^\s*((our|all|browse|find|search|list of|overview of)\s+)?"
    r"((bachelor'?s?|master'?s?|undergraduate|postgraduate|graduate|phd|doctoral)\s+)?"
    r"(programmes?|programs?|courses?|degrees?|studies)\s*$",
    re.IGNORECASE,
)
_PLURAL_FUNDING_HEADING = re.compile(
    r"^\s*((our|all|available|list of|overview of)\s+)?"
    r"(scholarships|funding|financial aid|grants|bursaries|awards|fellowships|stipends"
    r"|prizes and awards|practical matters)"
    r"(\s+(and|&)\s+(funding|fees|grants|tuition fees?))?\s*$",
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
_FAQ = re.compile(r"\bf\.?a\.?q\.?\b|frequently asked question", re.IGNORECASE)
_NEWS = re.compile(r"\b(news|press release|announcement|blog|article)\b", re.IGNORECASE)
_IRRELEVANT = re.compile(
    r"\b(vacanc|job openings?|careers? (?:at|portal|site)|recruitment|staff directory"
    r"|alumni|donate|shop|library catalogue|contact us|privacy (?:policy|statement)"
    r"|cookie|sitemap|nobel prize|erc grant|research (?:prize|award)s?)\b",
    re.IGNORECASE,
)
_COSTS = re.compile(
    r"\b(tuition fee|cost of attendance|fees and (?:funding|costs)|tuition and fees"
    r"|study costs|living costs|statement of fees)\b",
    re.IGNORECASE,
)
_DOCUMENTS = re.compile(
    r"\b(required documents|documents you need|document checklist|supporting documents"
    r"|what to submit|upload(?:ing)? documents)\b",
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


def classify_page(*, url: str, html: str = "", text: str = "") -> PageClassification:
    """Classify a fetched page. Never raises; unknown is a valid answer."""
    soup = BeautifulSoup(html, "lxml") if html else None
    title = _title(soup) if soup else ""
    headings = _headings(soup) if soup else []
    identity = _identity(soup, title)
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
    if _IRRELEVANT.search(low_head):
        return PageClassification(PageType.IRRELEVANT, 0.8, ["title is off-topic"], title)

    if _NEWS.search(low_head):
        return PageClassification(PageType.NEWS, 0.75, ["news markers in the title"], title)

    # --- mostly links and little prose ----------------------------------
    if soup is not None and body and len(body) < 1500:
        link_text = sum(len(a.get_text(strip=True)) for a in soup.find_all("a"))
        if link_text / max(len(body), 1) > 0.75:
            signals.append("page is mostly link text")
            return PageClassification(PageType.NAVIGATION, 0.6, signals, title)

    # --- funding family ---------------------------------------------------
    if _SCHOLARSHIP_WORD.search(low_head) or "scholarship" in path or "financial-aid" in path:
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

    # --- cost pages --------------------------------------------------------
    if _COSTS.search(low_head) or _COSTS.search(low_body[:1500]):
        return PageClassification(
            PageType.COSTS, 0.75, ["cost vocabulary"], title,
            academic_year=_academic_year(body),
        )

    if _DOCUMENTS.search(low_head):
        return PageClassification(PageType.DOCUMENTS, 0.7, ["document checklist heading"], title)

    # --- programme family --------------------------------------------------
    program_links = _program_link_count(soup) if soup else 0
    if _PLURAL_PROGRAM_HEADING.match(identity) or _CATALOG.search(low_head) or program_links >= 5:
        return PageClassification(
            PageType.PROGRAM_CATALOG, 0.75,
            [f"{program_links} programme links", "plural catalogue heading"], title,
        )

    # A programme page is identified before the admissions rules run: a real
    # programme page has an "entry requirements" section, and matching that
    # first classified BSc Computer Science and Engineering as a general
    # admissions page.
    subject = _program_name(identity)
    degree = _degree_level(f"{identity} {body[:2500]}")
    language = _language(body)
    year = _academic_year(body)

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
        signals.append(f"single programme {subject!r} at {degree} level")
        if language:
            signals.append(f"language of instruction: {language}")
        if year:
            signals.append(f"academic year {year}")
            return PageClassification(
                PageType.INTAKE_SPECIFIC_PROGRAM, 0.85, signals, title,
                subject=subject, degree_level=degree,
                language_of_instruction=language, academic_year=year,
            )
        return PageClassification(
            PageType.PROGRAM_DETAIL, 0.75, signals, title,
            subject=subject, degree_level=degree, language_of_instruction=language,
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
    if _CREDENTIAL.search(low_body[:2000]):
        return PageClassification(
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS, 0.55, ["credential vocabulary"], title
        )

    return PageClassification(PageType.UNKNOWN, 0.2, ["no decisive signals"], title)


# --- helpers ---------------------------------------------------------------


def _title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())[:200]
    h1 = soup.find("h1")
    return " ".join(h1.get_text(" ", strip=True).split())[:200] if h1 else ""


def _headings(soup: BeautifulSoup) -> list[str]:
    return [" ".join(h.get_text(" ", strip=True).split()) for h in soup.find_all(["h1", "h2"])][:12]


def _text(soup: BeautifulSoup) -> str:
    from app.adapters.extraction import html_to_text

    return html_to_text(str(soup))


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


def _identity(soup: BeautifulSoup | None, title: str) -> str:
    """What the page says it is about: its h1, else the title before the site suffix."""
    if soup is not None:
        h1 = soup.find("h1")
        if h1:
            return " ".join(h1.get_text(" ", strip=True).split())
    return title.split("|")[0].strip()


def _program_name(identity: str) -> str | None:
    """The programme a page is about, if it is about exactly one."""
    name = identity
    if not name or len(name) > 120:
        return None
    if _PLURAL_PROGRAM_HEADING.match(name):
        return None
    if not _degree_level(name):
        return None
    # A heading that is a question or an instruction is not a programme name.
    if name.endswith("?") or re.match(r"^(check|how|what|apply|find|browse|search)\b", name, re.I):
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


def _program_link_count(soup: BeautifulSoup | None) -> int:
    if soup is None:
        return 0
    return sum(
        1 for a in soup.find_all("a", href=True)
        if re.search(r"/(bsc|msc|ba|ma|bachelor|master|programme|program|course)s?/", a.get("href", ""), re.I)
    )
