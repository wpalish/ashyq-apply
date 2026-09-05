"""Turning fetched pages into claims.

Extraction is rule-based and conservative: a pattern either matches and yields
a claim carrying the sentence it came from, or it yields nothing. There is no
"best guess" branch. Everything produced here keeps the excerpt that justifies
it, so a user can check the machine's reading against the page.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime

from bs4 import BeautifulSoup

from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.schemas.claim import Claim

EXCERPT_RADIUS = 160

_WS = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")


def html_to_text(html: str) -> str:
    """Readable text with script/style/nav removed, structure preserved."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "footer", "header"]):
        # Keep short nav-ish blocks: deadlines often live in a sidebar.
        if len(tag.get_text(strip=True)) > 800:
            tag.decompose()
    text = soup.get_text("\n")
    text = _WS.sub(" ", text)
    return _BLANKS.sub("\n\n", text).strip()


def readable_text(html: str) -> str:
    """Page text with the site's navigation removed.

    Extractors and excerpts must work from the page's own content. Reading the
    whole document made evidence quotes read "Activate high contrast To main
    content Students & Education Programmes...", and put every degree word in
    the global menu into the page's apparent vocabulary.
    """
    from app.adapters.page_classifier import main_content

    soup = BeautifulSoup(html, "lxml")
    return html_to_text(str(main_content(soup)))


def html_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:200]
    h1 = soup.find("h1")
    return h1.get_text(strip=True)[:200] if h1 else ""


def pdf_to_text(data: bytes, max_pages: int = 40) -> str:
    """Extract text from an official handbook or fee schedule."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:max_pages]
        return _BLANKS.sub("\n\n", "\n".join((p.extract_text() or "") for p in pages)).strip()
    except Exception:  # pragma: no cover - malformed PDFs are common
        return ""


def for_matching(text: str) -> str:
    """Newlines to spaces, character-for-character.

    Requirement sentences routinely wrap mid-clause ("IELTS Academic score with
    an\noverall band of 6.5"). Patterns use ``[^.\n]`` to stay inside one
    sentence, which would otherwise break on the wrap. Replacing newlines with
    spaces keeps every offset identical, so excerpts still line up with the
    original text.
    """
    return text.replace("\n", " ").replace("\r", " ")


def excerpt_around(text: str, start: int, end: int, radius: int = EXCERPT_RADIUS) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    snippet = text[lo:hi].strip().replace("\n", " ")
    return _WS.sub(" ", snippet)


def is_official_domain(url: str, university_domains: Iterable[str] = ()) -> bool:
    low = url.lower()
    if any(d.lower() in low for d in university_domains if d):
        return True
    return any(
        f".{tld}/" in low or low.rstrip("/").endswith(f".{tld}")
        for tld in ("edu", "ac.uk", "edu.au", "gov", "gov.uk", "ac.nz", "edu.sg")
    )


class ClaimBuilder:
    """Accumulates claims that share one page's provenance."""

    def __init__(
        self,
        *,
        source_url: str,
        page_title: str = "",
        specificity: SourceSpecificity = SourceSpecificity.UNKNOWN,
        program: str | None = None,
        intake: str | None = None,
        academic_year: str | None = None,
        official_domain: bool = False,
        extraction_method: str = "html_rule",
        accessed_at: datetime | None = None,
    ) -> None:
        self.meta: dict[str, object] = {
            "source_url": source_url,
            "page_title": page_title,
            "source_specificity": specificity,
            "program": program,
            "intake": intake,
            "academic_year": academic_year,
            "official_domain": official_domain,
            "extraction_method": extraction_method,
            "accessed_at": accessed_at or datetime.now(UTC),
        }
        self.claims: list[Claim] = []

    def add(
        self,
        claim_type: ClaimType,
        value: object,
        excerpt: str,
        *,
        confidence: float = 0.8,
        section: str = "",
        status: ClaimStatus | None = None,
        notes: str = "",
        subject_key: str | None = None,
    ) -> Claim:
        # Only an official page can produce a "current" claim; anything else
        # stays unverified until a human or a better source confirms it.
        default_status = (
            ClaimStatus.VERIFIED_CURRENT
            if self.meta["official_domain"]
            and self.meta["source_specificity"]
            in (
                SourceSpecificity.PROGRAM_INTAKE,
                SourceSpecificity.PROGRAM,
                SourceSpecificity.UNIVERSITY_ADMISSIONS,
                SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
                SourceSpecificity.GOVERNMENT,
                SourceSpecificity.APPLICATION_PORTAL,
            )
            else ClaimStatus.UNVERIFIED
        )
        claim = Claim(
            claim_type=claim_type,
            normalized_value=value,
            original_text_excerpt=excerpt,
            relevant_section=section,
            confidence=confidence,
            status=status or default_status,
            notes=notes,
            subject_key=subject_key,
            **self.meta,  # type: ignore[arg-type]
        )
        self.claims.append(claim)
        return claim


# --- Requirement patterns -------------------------------------------------

_IELTS_OVERALL = re.compile(
    r"IELTS[^.\n]{0,80}?(?:overall|minimum|score of|band)[^.\n]{0,30}?(\d(?:\.\d)?)"
    r"|(?:overall|minimum)[^.\n]{0,30}?IELTS[^.\n]{0,30}?(\d(?:\.\d)?)",
    re.IGNORECASE,
)
_IELTS_SUB = re.compile(
    r"(?:no\s+(?:individual\s+)?(?:sub-?)?(?:score|band|component|section)\s+"
    r"(?:below|less\s+than|lower\s+than)|minimum\s+(?:of\s+)?(\d(?:\.\d)?)\s+in\s+each)"
    r"\s*(\d(?:\.\d)?)?",
    re.IGNORECASE,
)
_TOEFL = re.compile(r"TOEFL[^.\n]{0,90}?(\d{2,3})", re.IGNORECASE)
_DUOLINGO = re.compile(r"Duolingo[^.\n]{0,90}?(\d{2,3})", re.IGNORECASE)
_GPA = re.compile(
    r"(?:minimum|at least|GPA of|grade point average of)[^.\n]{0,40}?(\d(?:\.\d{1,2})?)\s*"
    r"(?:/|out of|on a[n]?\s*)\s*(\d(?:\.\d)?)\s*(?:scale|point)?",
    re.IGNORECASE,
)
_SAT_OPTIONAL = re.compile(
    r"(test[- ]optional|test[- ]blind|SAT[^.\n]{0,40}(?:not required|optional))", re.IGNORECASE
)
_SAT_MIN = re.compile(
    r"SAT[^.\n]{0,60}?(?:minimum|at least|score of)[^.\n]{0,20}?(\d{3,4})", re.IGNORECASE
)
_SUPERSCORE = re.compile(r"(superscor\w+)", re.IGNORECASE)
#: A currency marker must sit directly beside the number. Bare digits are never
#: read as money, which keeps years and scores out of the cost table.
_MONEY = re.compile(
    r"(?:(US\$|USD|EUR|€|GBP|£|CAD|AUD|CHF|SEK|NOK|DKK|SGD|JPY|\$)\s*)"
    r"([\d]{1,3}(?:[,\s]\d{3})+|\d{2,7})(?:\.(\d{2}))?"
    r"|([\d]{1,3}(?:[,\s]\d{3})+|\d{2,7})\s*(EUR|USD|GBP|CHF|SEK|NOK|DKK|AUD|CAD|SGD|JPY)",
    re.IGNORECASE,
)
_PERCENT_TUITION = re.compile(r"(\d{1,3})\s*%\s*(?:of\s+)?(?:the\s+)?tuition", re.IGNORECASE)
_DEADLINE = re.compile(
    r"(?:deadline|closes?|apply by|applications? close|due)[^.\n]{0,60}?"
    r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
    r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
#: An explicit list. A catch-all like [A-Z]{2,4}T matched the word "SAT" in a
#: sentence about standardised tests and reported it as the deadline's timezone.
#: Inventing a timezone is worse than reporting none.
_TZ = re.compile(
    r"\b(UTC|GMT|BST|WET|WEST|CET|CEST|EET|EEST|MSK|"
    r"AST|EST|EDT|CST|CDT|MST|MDT|PST|PDT|AKST|HST|"
    r"AEST|AEDT|ACST|ACDT|AWST|NZST|NZDT|"
    r"IST|SGT|HKT|JST|KST|ICT|PKT|GST|SAST|BRT|ART|CLT)\b"
)

_CURRENCY_SYMBOLS = {
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "cad": "CAD",
    "aud": "AUD",
    "chf": "CHF",
    "sek": "SEK",
    "nok": "NOK",
    "dkk": "DKK",
    "sgd": "SGD",
    "jpy": "JPY",
}
_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        1,
    )
}


def parse_money(text: str) -> tuple[float, str] | None:
    m = _MONEY.search(text)
    if not m:
        return None
    if m.group(2):
        raw, cur = m.group(2), (m.group(1) or "").lower()
    else:
        raw, cur = m.group(4), (m.group(5) or "").lower()
    if not raw:
        return None
    amount = float(re.sub(r"[,\s]", "", raw))
    if m.group(3):
        amount += float(m.group(3)) / 100
    return amount, _CURRENCY_SYMBOLS.get(cur, "USD")


def parse_deadline(text: str) -> date | None:
    m = _DEADLINE.search(text)
    if not m:
        return None
    return parse_date_string(m.group(1))


def parse_date_string(raw: str) -> date | None:
    raw = raw.strip().rstrip(".")
    for fmt in ("%d %B %Y", "%B %d, %Y", "%B %d %Y", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw)
    if m and m.group(2).lower() in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def parse_timezone(text: str) -> str | None:
    m = _TZ.search(text)
    return m.group(1) if m else None


def extract_requirements(text: str, builder: ClaimBuilder) -> list[Claim]:
    """Pull admission requirements out of readable page text."""
    found: list[Claim] = []
    text = for_matching(text)

    for m in _IELTS_OVERALL.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw is None:
            continue
        value = float(raw)
        if not 4.0 <= value <= 9.0:
            continue
        found.append(
            builder.add(
                ClaimType.IELTS_MIN_OVERALL,
                value,
                excerpt_around(text, m.start(), m.end()),
                section="English language requirements",
            )
        )
        break

    for m in _IELTS_SUB.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw is None:
            continue
        value = float(raw)
        if 4.0 <= value <= 9.0:
            found.append(
                builder.add(
                    ClaimType.IELTS_MIN_SUBSCORE,
                    value,
                    excerpt_around(text, m.start(), m.end()),
                    section="English language requirements",
                )
            )
            break

    toefl = _TOEFL.search(text)
    if toefl and 40 <= int(toefl.group(1)) <= 120:
        found.append(
            builder.add(
                ClaimType.TOEFL_MIN_TOTAL,
                int(toefl.group(1)),
                excerpt_around(text, toefl.start(), toefl.end()),
            )
        )

    duolingo = _DUOLINGO.search(text)
    if duolingo and 60 <= int(duolingo.group(1)) <= 160:
        found.append(
            builder.add(
                ClaimType.DUOLINGO_MIN,
                int(duolingo.group(1)),
                excerpt_around(text, duolingo.start(), duolingo.end()),
            )
        )

    gpa = _GPA.search(text)
    if gpa:
        value, scale = float(gpa.group(1)), float(gpa.group(2))
        # The scale must bound the value, or we have matched two unrelated numbers.
        if 0 < value <= scale <= 100:
            ex = excerpt_around(text, gpa.start(), gpa.end())
            found.append(builder.add(ClaimType.MIN_GPA, value, ex))
            found.append(builder.add(ClaimType.GPA_SCALE, scale, ex))

    optional = _SAT_OPTIONAL.search(text)
    if optional:
        found.append(
            builder.add(
                ClaimType.SAT_POLICY,
                optional.group(1),
                excerpt_around(text, optional.start(), optional.end()),
            )
        )
    else:
        sat_min = _SAT_MIN.search(text)
        if sat_min and 400 <= int(sat_min.group(1)) <= 1600:
            found.append(
                builder.add(
                    ClaimType.SAT_MIN_TOTAL,
                    int(sat_min.group(1)),
                    excerpt_around(text, sat_min.start(), sat_min.end()),
                )
            )

    superscore = _SUPERSCORE.search(text)
    if superscore:
        found.append(
            builder.add(
                ClaimType.SUPERSCORE_POLICY,
                superscore.group(1),
                excerpt_around(text, superscore.start(), superscore.end()),
            )
        )

    deadline_match = _DEADLINE.search(text)
    if deadline_match:
        deadline = parse_date_string(deadline_match.group(1))
        if deadline:
            ex = excerpt_around(text, deadline_match.start(), deadline_match.end())
            found.append(
                builder.add(
                    ClaimType.ADMISSION_DEADLINE,
                    deadline.isoformat(),
                    ex,
                    notes=f"timezone: {parse_timezone(ex) or 'not stated on page'}",
                )
            )

    for pattern, ctype in (
        (r"portfolio", ClaimType.PORTFOLIO_REQUIRED),
        (r"interview", ClaimType.INTERVIEW_REQUIRED),
        (r"entrance (?:exam|examination|test)", ClaimType.ENTRANCE_EXAM_REQUIRED),
        (
            r"(?:WES|ECE|credential evaluation|course-by-course evaluation)",
            ClaimType.CREDENTIAL_EVALUATION_REQUIRED,
        ),
    ):
        requirement = re.search(
            rf"{pattern}[^.\n]{{0,60}}(?:required|must|mandatory)"
            rf"|(?:required|must submit)[^.\n]{{0,40}}{pattern}",
            text,
            re.IGNORECASE,
        )
        if requirement:
            found.append(
                builder.add(
                    ctype,
                    True,
                    excerpt_around(text, requirement.start(), requirement.end()),
                    confidence=0.7,
                )
            )

    return found


def extract_costs(text: str, builder: ClaimBuilder) -> list[Claim]:
    """Pull cost figures out of a fees page."""
    found: list[Claim] = []
    text = for_matching(text)
    patterns = (
        (ClaimType.TUITION, r"(?:tuition|tuition fee|programme fee|course fee)"),
        (ClaimType.HOUSING_COST, r"(?:housing|accommodation|residence|room)"),
        (ClaimType.MEALS_COST, r"(?:meal plan|meals|board|food)"),
        (ClaimType.HEALTH_INSURANCE_COST, r"(?:health insurance|medical insurance)"),
        (ClaimType.BOOKS_COST, r"(?:books|books and supplies|study materials)"),
        (
            ClaimType.MANDATORY_FEES,
            r"(?:mandatory fees|student fees|university fees|administrative fee)",
        ),
        (
            ClaimType.TOTAL_COST_OF_ATTENDANCE,
            r"(?:total cost of attendance|estimated total cost|total estimated cost)",
        ),
    )
    for ctype, label in patterns:
        m = re.search(rf"{label}[^.\n]{{0,120}}", text, re.IGNORECASE)
        if not m:
            continue
        parsed = parse_money(m.group(0))
        if parsed is None:
            continue
        amount, currency = parsed
        found.append(
            builder.add(
                ctype,
                {"amount": amount, "currency": currency},
                excerpt_around(text, m.start(), m.end()),
                section="Fees and costs",
            )
        )
    return found
