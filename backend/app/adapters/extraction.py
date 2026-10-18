"""Turning fetched pages into claims.

Extraction is rule-based and conservative: a pattern either matches and yields
a claim carrying the sentence it came from, or it yields nothing. There is no
"best guess" branch. Everything produced here keeps the excerpt that justifies
it, so a user can check the machine's reading against the page.
"""

from __future__ import annotations

import io
import re
from bisect import bisect_left
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Final, Literal, cast
from urllib.parse import urlparse

from app.adapters.html_parse import parse_html
from app.adapters.scope_reader import intake_from_start, population_named
from app.domain.claim_scope import ClaimScope
from app.domain.claim_verifier import (
    OFFICIAL_PUBLIC_TLDS,
    RejectReason,
    VerificationInput,
    registrable_domain,
    states_a_requirement_without_settling_it,
    url_matches_domains,
    verify_claim,
)
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.schemas.claim import Claim

EXCERPT_RADIUS = 160

_WS = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")


def html_to_text(html: str) -> str:
    """Readable text with script/style/nav removed, structure preserved."""
    soup = parse_html(html)
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
    from app.adapters.page_classifier import content_for_reading

    soup = parse_html(html)
    return html_to_text(str(content_for_reading(soup)))


def html_title(html: str) -> str:
    soup = parse_html(html)
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
    """True when this URL is served by the university or an official TLD.

    Only the URL's host decides — the registrable domain of the host is
    compared against the university's domains, never the raw URL string. The
    old substring test accepted ``https://attacker.example/?u=narxoz.kz``
    and ``https://narxoz.kz.attacker.example/`` as official sources; a
    university's name inside a query parameter or a hostile subdomain is a
    spoof, not a source.
    """
    if url_matches_domains(url, university_domains):
        return True
    registrable = registrable_domain(urlparse(url).hostname or "")
    return any(
        registrable == tld or registrable.endswith(f".{tld}") for tld in OFFICIAL_PUBLIC_TLDS
    )


def verification_domains(
    url: str, domain: str | None, extra_domains: Iterable[str] = ()
) -> tuple[str, ...]:
    """The domains a claim's page must belong to, for the verifier.

    Empty for a ``fixture://`` page, which is official by construction and has
    no host to check, and when the candidate names no domain. ``extra_domains``
    are the candidate's DI-1 admissions domains (``Candidate.extra_domains``),
    empty unless that rule found one.
    """
    if not domain or url.startswith("fixture://"):
        return ()
    return (domain, *(d for d in extra_domains if d))


@dataclass(frozen=True, slots=True)
class EnglishHint:
    """EN-2: what the programme page says about which English requirement applies.

    An English page often publishes one row per faculty (UNSW), per entry band
    (TCD "Band B (Standard entry)") or per level (Imperial "Standard" /
    "Higher"). Only the programme page says which one is the programme's; the
    readers pick that row with these, and abstain without them.
    """

    #: Faculty keys (:func:`faculty_key`) the programme page names.
    units: frozenset[str] = frozenset()
    #: The entry band the programme page names, as its letter ("b").
    band: str | None = None
    #: The level word the programme page names ("standard" / "higher").
    level: str | None = None
    #: The requested degree level ("bachelor", "master", ...).
    degree: str | None = None


class ClaimBuilder:
    """Accumulates claims that share one page's provenance.

    The optional verification context (``page_text``, ``page_type``,
    ``allowed_domains``) feeds ``app.domain.claim_verifier``: each added claim
    is checked against the evidence it arrived with, and only checks whose
    context is present are evaluated — a builder without page text never
    rejects for verbatim-ness, one without allowed domains never rejects on
    domain, and so on. A rejected claim is recorded in ``rejected`` as
    ``(claim_type, excerpt, reason)`` and never becomes a Claim; ``add``
    returns None for it.
    """

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
        scope: ClaimScope | None = None,
        page_text: str | None = None,
        page_type: str | None = None,
        allowed_domains: Sequence[str] = (),
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
            # Deliberately whatever the caller passed, ``None`` included: a
            # builder that was given no scope records that nobody read one,
            # which is not the same claim as "the page stated nothing".
            "scope": scope,
        }
        self.claims: list[Claim] = []
        #: TY-1: the year the applicant asked for, apart from the page's own.
        self.requested_academic_year: str | None = None
        #: FE-2: the programme(s) and degree level asked for, apart from the
        #: page's own. Read by the fee readers only; never persisted.
        self.requested_programmes: tuple[str, ...] = ()
        self.requested_degree: str | None = None
        #: EN-2 (``ENGLISH_READERS_V2``): which English row is the programme's,
        #: and the claim types a reader of this page abstained on, so a later
        #: reader of the same page cannot answer them from a row it did not pick.
        self.english_hint: EnglishHint | None = None
        self.english_abstained: set[ClaimType] = set()
        self.rejected: list[tuple[ClaimType, str, RejectReason]] = []
        # Verification context, deliberately outside meta: these feed the
        # verifier only, and a Claim's persisted fields must not change.
        self.page_text = page_text
        self.page_type = page_type
        self.allowed_domains: tuple[str, ...] = tuple(allowed_domains)

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
        population: str | None = None,
        intake: str | None = None,
        degree: str | None = None,
        programme: str | None = None,
        qualification: str | None = None,
        academic_year: str | None = None,
    ) -> Claim | None:
        verdict = verify_claim(
            VerificationInput(
                claim_type=claim_type,
                value=value,
                excerpt=excerpt,
                page_text=self.page_text,
                source_url=cast("str", self.meta["source_url"]),
                page_type=self.page_type,
                official_domain=bool(self.meta["official_domain"]),
                allowed_domains=self.allowed_domains,
                today=cast("datetime", self.meta["accessed_at"]).date(),
            )
        )
        if not verdict.accepted:
            # A rejected verdict always carries its reason (verify_claim's contract).
            self.rejected.append((claim_type, excerpt, cast("RejectReason", verdict.reason)))
            return None
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
        # Phase 3 §10: conditional wording is grounds for escalation, not for a
        # settled requirement. The claim keeps its value and its excerpt — it
        # is still evidence — but it stops being something that can eliminate
        # a university on its own, and it says which word unsettled it.
        hedge = states_a_requirement_without_settling_it(excerpt, value)
        if hedge and (status or default_status) is ClaimStatus.VERIFIED_CURRENT:
            default_status = ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION
            status = None
            notes = (
                f"{notes} " if notes else ""
            ) + f"The page states this conditionally ({hedge!r}); it is not settled."

        meta = dict(self.meta)
        row_scope = {
            k: v
            for k, v in (
                ("population", population),
                ("intake", intake),
                ("degree", degree),
                ("programme", programme),
                ("qualification", qualification),
                ("academic_year", academic_year),
            )
            if v
        }
        if row_scope:
            # One row of a table can say who and when it is for when the page as
            # a whole cannot: "non-EU/EEA students 01 May 2027 01 September
            # 2027" beside two other rows. Only those dimensions change; the
            # rest is still the page's.
            page_scope = cast("ClaimScope | None", meta["scope"]) or ClaimScope()
            meta["scope"] = replace(page_scope, **row_scope)
        claim = Claim(
            claim_type=claim_type,
            normalized_value=value,
            original_text_excerpt=excerpt,
            relevant_section=section,
            confidence=confidence,
            status=status or default_status,
            notes=notes,
            subject_key=subject_key,
            **meta,  # type: ignore[arg-type]
        )
        self.claims.append(claim)
        return claim


# --- Requirement patterns -------------------------------------------------

_IELTS_OVERALL = re.compile(
    r"IELTS[^.\n]{0,80}?(?:overall|minimum|score of|band)[^.\n]{0,30}?(\d(?:\.\d)?)"
    r"|(?:overall|minimum)[^.\n]{0,30}?IELTS[^.\n]{0,30}?(\d(?:\.\d)?)"
    # "IELTS 6.5 overall (or equivalent)": many pages state the keyword after
    # the band. The keyword must follow the number directly, so "IELTS 6.5 in
    # each component" stays a subscore statement, not an overall band.
    r"|IELTS[^\d.\n]{0,20}?(\d(?:\.\d)?)\s*(?:overall|band)"
    # UBC's table: "International English Language Testing System (Academic)
    # 6.5, with no part less than 6.0". The spelled-out name carries the band
    # directly, and the per-part floor that follows is what makes 6.5 the
    # overall one rather than any number near a test name.
    r"|International English Language Testing System\s*(?:\(?academic\)?)?\s*:?\s*"
    r"(\d(?:\.\d)?)(?=,?\s*(?:with\s+)?no\s+(?:part|band|section|component|sub-?score))"
    # Auckland's entry table: "IELTS Academic | International English Language
    # Testing System | Score required | 6.0 | No bands less than 5.5." The cell
    # label "Score required" names the overall band, and the band is the next
    # cell, never the first digit of a longer number or a percentage.
    r"|IELTS[^.\n]{0,80}?\bscore\s+required\b\s*:?\s*(\d(?:\.\d)?)(?![\d%])"
    # UM's list of accepted tests: "MUET 4.0 IELTS (Academic) 5.5 TOEFL iBT
    # (Centre-based) 46". A band written straight after the test's name is its
    # overall score only when the next thing is another test of the list: the
    # entry has nothing after it to make it a per-band floor or a section.
    r"|\bIELTS\s*(?:\(\s*academic\s*\)|academic)?\s*:?\s*(\d(?:\.\d)?)(?![\d%])"
    r"(?=\s*[,;|]?\s*(?:or\s+)?(?:TOEFL|PTE|Pearson|Duolingo|Cambridge|MUET|CAEL|CELPIP"
    r"|Michigan|OET|LanguageCert)\b)",
    re.IGNORECASE,
)
_IELTS_SUB = re.compile(
    # "part" is the certified corpus' own word for UBC: "no part less than
    # 6.0". Missing it dropped the per-section minimum while keeping the
    # overall band — which the phase guide calls the single most common error
    # in this work, because 7.0 overall with 6.0 writing fails a 6.5 per-band
    # rule and the applicant is told they qualify.
    # Plurals too: Auckland's "Overall score of 6.0 and no bands below 5.5"
    # (dev3 run 39080161290) was skipped, and the reader then took the "6" of
    # another test's "no section below 60%". A band is never followed by a
    # further digit or a percent sign.
    r"(?:no\s+(?:individual\s+)?(?:sub-?)?(?:score|band|component|section|part)s?\s+"
    r"(?:below|less\s+than|lower\s+than)|minimum\s+(?:of\s+)?(\d(?:\.\d)?)(?![\d%])\s+in\s+each)"
    r"\s*(\d(?:\.\d)?(?![\d%]))?",
    re.IGNORECASE,
)
#: "Overall 6, Writing 6,speaking 6" — NTU's certified wording, where each
#: section carries its own minimum. The bands are read as a map, because a
#: single floor cannot say that writing is 6 while reading is 6.5, and
#: flattening them to the lowest would be converting a value silently.
#: One sentence that mentions IELTS, so a bare "Writing 6" elsewhere on the
#: page cannot become a band. A full stop ends the sentence only when it is
#: not a decimal point: "[^.]" alone stopped at the 7 of "overall 7.0" and
#: lost every band stated after it.
#: A sentence, for the per-section reading, runs between two terminators: a
#: line break, or a full stop that is not a decimal point ("6.5" stays whole).
#: This used to be one pattern, ``(?:[^.\n]|\.(?=\d))*\bIELTS\b(?:…)*``, whose
#: unanchored leading repetition re-scanned every period-free line from each of
#: its positions: 15 s on a 31k-character Masaryk page, synchronous, so the
#: child's own deadline could not fire. Finding "IELTS" first and widening each
#: hit to its terminators yields the same spans in linear time.
_IELTS_WORD = re.compile(r"\bIELTS\b", re.IGNORECASE)
_IELTS_SENTENCE_END = re.compile(r"\n|\.(?!\d)")
_IELTS_NAMED_BAND = re.compile(
    # A band never runs on into another digit: "Reading: 60" is a PTE score,
    # and reading its first digit as IELTS 6.0 is exactly what UBC's table,
    # with no full stop between the two tests, produced.
    r"\b(listening|reading|writing|speaking)\b\s*[:\-–]?\s*(\d(?:\.\d)?)(?![\d.])",
    re.IGNORECASE,
)
#: Where another test's statement begins, the IELTS one has ended.
_OTHER_TEST = re.compile(
    r"\b(?:PTE|Pearson|TOEFL|Duolingo|Cambridge|CAEL|CELPIP|Michigan)\b", re.IGNORECASE
)

#: Names that start another test's statement inside a TOEFL scan (UM: "78 in
#: TOEFL iBT ... a minimum score of 57 in PTE" read 57, and "60 (IBT) and above
#: in TOEFL; or ... MUET ...; or Score 41 ... in Pearson" read 41).
_NOT_TOEFL = r"(?:PTE|Pearson|IELTS|MUET|Duolingo|Cambridge|CAEL|CELPIP|Michigan|LanguageCert|OET)"
_TOEFL_WORD = re.compile(r"TOEFL", re.IGNORECASE)
_TOEFL = re.compile(rf"TOEFL(?:(?!\b{_NOT_TOEFL}\b)[^.\n]){{0,90}}?(\d{{2,3}})", re.IGNORECASE)
#: The number-first form: "a minimum score of 78 in TOEFL", "60 (IBT) and above in TOEFL".
_TOEFL_NUMBER_FIRST = re.compile(
    r"(?<![\d.])(\d{2,3})\s*(?:\((?:i?BT|internet-based)\)\s*)?(?:and\s+above\s+)?"
    r"(?:in|on|for)\s+(?:the\s+)?TOEFL\Z",
    re.IGNORECASE,
)
#: A number followed by "in PTE" is that test's score, not TOEFL's.
_OTHER_TESTS_SCORE = re.compile(
    rf"\s*(?:\([^)]{{0,20}}\)\s*)?(?:and\s+above\s+)?(?:in|on|for)\s+(?:the\s+)?{_NOT_TOEFL}\b",
    re.IGNORECASE,
)
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
    r"SAT[^.\n]{0,60}?(?:minimum|at least|score of)[^.\n]{0,20}?(\d{3,4})"
    # The number first: "1250 for redesigned SAT" is the certified corpus'
    # wording for NTU, and read as nothing at all. _IELTS_OVERALL already
    # carries a reversed alternative for the same reason. A preposition is
    # required between the two, because a bare "number ... SAT" window read
    # "Room 1250 is where the SAT is sat" and "1250 EUR with their SAT
    # booking" as scores — the forward form has always demanded a qualifier
    # and the reverse must demand one too.
    r"|(\d{3,4})\s*(?:or\s+(?:above|higher|better)\s*)?"
    r"(?:for|on|in)\s+(?:the\s+)?(?:redesigned\s+|new\s+|old\s+)?SAT\b"
    # A label and a dash or colon: NTU's English-proficiency list reads "SAT
    # Total score – 1250" (core-gap analysis 2026-10-18, B1), which neither
    # form above matched. Only a total/composite score label may stand between
    # "SAT" and the separator; a section's score ("SAT: 650 in Math") and a
    # range ("SAT – 1250-1450") are not a minimum total.
    r"|\bSAT(?:\s+(?:total|composite|combined|overall))?(?:\s+score)?\s*[:–—-]\s*(\d{3,4})\b"
    r"(?!\s*(?:[–—-]|to)\s*\d)"
    r"(?!\s*(?:in|on|for)\s+(?:the\s+)?(?:math|reading|writing|evidence|ebrw|each|every|section))",
    re.IGNORECASE,
)
_SUPERSCORE = re.compile(r"(superscor\w+)", re.IGNORECASE)
#: A currency marker must sit directly beside the number. Bare digits are never
#: read as money, which keeps years and scores out of the cost table.
_MONEY = re.compile(
    # A country-prefixed dollar is not a US dollar: "S$6,500" is Singapore's
    # (NTU's living allowance) and was read as USD while the prefix was absent.
    r"(?:(US\$|S\$|HK\$|C\$|CA\$|A\$|AU\$|NZ\$|USD|EUR|€|GBP|£|CAD|AUD|CHF|SEK|NOK|DKK|SGD"
    r"|HKD|NZD|KRW|JPY|KZT|₸|\$)\s*)"
    r"([\d]{1,3}(?:[,\s]\d{3})+|\d{2,7})(?:\.(\d{2}))?"
    r"|([\d]{1,3}(?:[,\s]\d{3})+|\d{2,7})\s*(EUR|USD|GBP|CHF|SEK|NOK|DKK|AUD|CAD|SGD|HKD|NZD|KRW|JPY|KZT|₸)",
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
_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_A_DATE = (
    rf"\d{{1,2}}\s+(?:{_MONTH_NAMES})\s+\d{{4}}"
    rf"|(?:{_MONTH_NAMES})\s+\d{{1,2}},?\s+\d{{4}}"
    r"|\d{4}-\d{2}-\d{2}"
)
#: A window between two dates: "15 October 2026 - 19 March 2027", "… to …".
_DATE_RANGE = re.compile(
    rf"({_A_DATE})\s*(?:[-–—]|to|until)\s*({_A_DATE})",
    re.IGNORECASE,
)
#: One row of a deadline table that names its population: Groningen's
#: "non-EU/EEA students 01 May 2027 01 September 2027". The lookbehind keeps
#: the "EU/EEA" inside "non-EU/EEA" from reading as a second row.
_POPULATION_NAME = r"(?<![\w/-])(non[-\s]?EU(?:\s*/\s*EEA)?|EU\s*/\s*EEA)"
_POPULATION_WORD = re.compile(_POPULATION_NAME, re.IGNORECASE)
_POPULATION_ROW = re.compile(
    _POPULATION_NAME + r"(?:\s+(?:students|applicants|nationals|citizens))?\s*[:\-–]?\s*"
    rf"({_A_DATE})(?:\s+({_A_DATE}))?",
    re.IGNORECASE,
)
_DEADLINE_WORD = re.compile(r"\bdeadlines?\b", re.IGNORECASE)
#: "Application period 2 March to 4 May 2026": the deadline is the period's
#: end. The start often omits its year, so only the end must be a full date.
_APPLICATION_PERIOD = re.compile(
    rf"application period\s*:?\s*\d{{1,2}}\s+(?:{_MONTH_NAMES})(?:\s+\d{{4}})?"
    rf"\s*(?:to|until|[–-])\s*({_A_DATE})",
    re.IGNORECASE,
)
#: Plan rule DL-2 (error analysis 2026-10-05). On by default since 2026-10-05
#: (owner: "Да"): three paired runs on exa_mcp, zero stable losses; NTU's
#: deadline is right with its qualification wherever the page is reached,
#: and the first readers never find it.
#: Three forms the readers above never match, each found on a cohort page:
#: abbreviated months (Aalto "Application period: 7 Jan 2027 – 22 Jan 2027"),
#: a date that comes before its label (UBC "January 15, 2027 (11:59 p.m. PST)
#: Applications due"), and a window table whose catch-all row is the one an
#: unlisted qualification falls under (NTU "All other international
#: qualifications not listed below ... 15 Oct 2026 - 20 Jan 2027").
DEADLINE_V2 = True
_MONTH_ABBREVIATIONS = r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
_ANY_MONTH = rf"(?:{_MONTH_NAMES}|(?:{_MONTH_ABBREVIATIONS})\.?)(?![a-z])"
_A_DATE_V2 = (
    rf"\d{{1,2}}\s+{_ANY_MONTH}\s+\d{{4}}"
    rf"|{_ANY_MONTH}\s+\d{{1,2}},?\s+\d{{4}}"
    r"|\d{4}-\d{2}-\d{2}"
)
_DATE_RANGE_V2 = re.compile(
    rf"({_A_DATE_V2})\s*(?:[-–—]|to|until)\s*({_A_DATE_V2})",
    re.IGNORECASE,
)
_DEADLINE_V2 = re.compile(
    rf"(?:deadline|closes?|apply by|applications? close|due)[^.\n]{{0,60}}?({_A_DATE_V2})",
    re.IGNORECASE,
)
_APPLICATION_PERIOD_V2 = re.compile(
    rf"application period\s*:?\s*\d{{1,2}}\s+{_ANY_MONTH}(?:\s+\d{{4}})?"
    rf"\s*(?:to|until|[–-])\s*({_A_DATE_V2})",
    re.IGNORECASE,
)
#: The label right after the date says it is the application deadline; a
#: scholarship or award deadline written the same way names itself instead.
_DATE_FIRST_DEADLINE = re.compile(
    rf"({_A_DATE_V2})\s*(?:\([^)]{{0,40}}\))?\s*"
    r"(?:applications?\s+(?:are\s+)?due|deadline\s+to\s+apply)([^.\n]{0,120})",
    re.IGNORECASE,
)
_CATCH_ALL_WINDOW = re.compile(
    r"(all other (?:international )?qualifications(?: not listed(?: below)?)?)"
    rf"[^\n]{{0,240}}?({_A_DATE_V2})\s*(?:[-–—]|to|until)\s*({_A_DATE_V2})",
    re.IGNORECASE,
)
_SESSION_START = re.compile(rf"\(\s*({_MONTH_NAMES})\s+(\d{{4}})", re.IGNORECASE)

#: Plan rule DL-3 (Serper run 39058503662, UBC). On since paired run
#: 39063173594 (UBC's wrong deadline gone in every repetition, 0 losses; owner
#: delegation 2026-10-17). False turns it off. https://you.ubc.ca/applying-ubc reads "Deadline November 15,
#: 2026 Apply before 11:59 pm PDT International students: Deadline to apply to
#: UBC and submit an award application if you wish to be considered for the UBC
#: International Major Entrance Scholarship ..." and 2026-11-15 was claimed as
#: the admission deadline; the deadline for September 2027 entry is 2027-01-15
#: ("Applications due"), on /applying-ubc/dates-deadlines/. A date its own
#: sentence makes conditional on an award or scholarship application is not
#: the admission deadline, and is dropped: the scholarship deadline path has no
#: scope or subject to carry the award it is for. An unconditional deadline on
#: the same page is still read.
DEADLINE_AWARD_CONDITION = True
_AWARD_WORD = r"(?:scholarships?|awards?|bursar(?:y|ies)|funding)"
_AWARD_CONDITION = re.compile(
    rf"\bto\s+be\s+considered\s+for\b[^.]{{0,80}}?\b{_AWARD_WORD}\b"
    r"|\b(?:award|scholarship)s?\s+applications?\b"
    r"|\bscholarships?\s+(?:application\s+)?deadlines?\b"
    rf"|\bpriority\s+deadlines?\s+for\s+(?:\w+\s+){{0,2}}?{_AWARD_WORD}\b",
    re.IGNORECASE,
)
#: "11:59 p.m." must not end the date's sentence at its first dot.
_CLOCK_DOTS = re.compile(r"\b([ap])\.\s?m\.", re.IGNORECASE)
_ANY_DATE_V2 = re.compile(_A_DATE_V2, re.IGNORECASE)


def _award_conditional(text: str, start: int, end: int) -> bool:
    """Whether the sentence of the date at ``text[start:end]`` makes it a
    deadline for an award or scholarship application (rule DL-3).

    The sentence is bounded as the deadline readers bound theirs: it ends at
    a full stop, and reaches at most 120 characters either side of the date.
    It also stops at the next and the previous date, so a scholarship
    deadline written beside an admission deadline never taints it.
    """
    flat = _CLOCK_DOTS.sub(lambda m: m.group(0).replace(".", " "), text)
    lo = max(0, start - 120, flat.rfind(".", 0, start) + 1)
    hi = min(len(flat), end + 120)
    stop = flat.find(".", end, hi)
    if stop != -1:
        hi = stop
    for other in _ANY_DATE_V2.finditer(flat, lo, hi):
        if other.end() <= start:
            lo = max(lo, other.end())
        elif other.start() >= end:
            hi = other.start()
            break
    return _AWARD_CONDITION.search(flat, lo, hi) is not None


def _conditional_skip(text: str, match: re.Match[str] | None, group: int) -> bool:
    return (
        DEADLINE_AWARD_CONDITION
        and match is not None
        and _award_conditional(text, match.start(group), match.end(group))
    )


def _first_unconditional(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    """The first match of ``pattern`` whose date (group 1) rule DL-3 keeps."""
    for match in pattern.finditer(text):
        if not _conditional_skip(text, match, 1):
            return match
    return None


#: Plan rule EX-2 (evidence analysis 2026-10-17 §0 #2, §1.2, §4 rank 6), off
#: until a paired run passes. Uppsala's programme page states, per intake,
#: "Study period 31 August 2026–3 June 2029" and "Application deadline
#: 15 April 2026", then the same block for autumn 2027. The several-windows
#: guard above counted the two study periods as two application windows that
#: end on different dates and claimed no deadline at all. On, two changes, both
#: of which only narrow what the deadline readers see: (i) a date range
#: introduced by study-period words (study period, programme runs, start of
#: studies, semester dates, term dates) is not an application window and is
#: not counted; (ii) when the page has explicit per-intake sections — a line
#: that is only "Autumn 2027", "Spring 2028" — and one of them is the
#: requested intake (``ClaimBuilder`` ``intake``), the deadline is read from
#: that section only, as TY-1 does for fee rows. Two application windows that
#: differ still claim nothing; on a sectioned page that has no section for the
#: requested intake (or when no intake was requested) only the text before the
#: first intake heading is read, so another intake's deadline is never claimed.
#: The benchmark harness flips it per capture (``--deadline-window-scope``).
DEADLINE_WINDOW_SCOPE = False
#: EX-2: words that make the date range after them the programme's own dates.
_STUDY_PERIOD_CUE = re.compile(
    r"\b(?:study\s+period|period\s+of\s+study|(?:programme|program|course)\s+runs"
    r"|start\s+of\s+(?:studies|study)|semester\s+dates|term\s+dates)\b",
    re.IGNORECASE,
)
#: EX-2: an application word after the cue gives the range back to the readers.
_APPLICATION_CUE = re.compile(r"\b(?:applica\w*|apply|deadlines?|admission)\b", re.I)
#: EX-2: a line that is only an intake: "Autumn 2027", "Autumn 2027,", "Spring 2028".
_INTAKE_SECTION = re.compile(
    r"^[^\S\n]*(autumn|fall|spring|summer|winter)[^\S\n]+(20\d\d)"
    r"(?:[^\S\n]+(?:semester|term|intake))?[^\S\n]*[,:]?[^\S\n]*$",
    re.IGNORECASE | re.MULTILINE,
)


def _study_period_range(text: str, window: re.Match[str]) -> bool:
    """EX-2: whether a date range is the programme's study period, not a window."""
    before = text[max(0, window.start() - 80) : window.start()]
    cues = list(_STUDY_PERIOD_CUE.finditer(before))
    return bool(cues) and not _APPLICATION_CUE.search(before, cues[-1].end())


def _application_windows(text: str, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    """The date ranges the several-windows guard counts."""
    return [
        m
        for m in pattern.finditer(text)
        if not (_intake_rules_on() and _study_period_range(text, m))
    ]


#: Plan rule DL-5 (core-gap analysis 2026-10-18 §3 change 5), off until a
#: paired run passes; ``--intake-section-deadline`` flips it. It absorbs EX-2
#: rather than repeating it: on, EX-2's two rules apply whatever
#: ``DEADLINE_WINDOW_SCOPE`` says (a study period is never an application
#: window; a page with per-intake sections is read for the requested intake's
#: section only), and four more follow. (a) An intake heading may also be a
#: calendar-year system's "Semester One 2027" / "Semester 2 2027" / "Summer
#: School 2027"; a requested "fall 2027" with no autumn section reads that
#: year's first semester (Auckland: the BSc page's "Semester One 2027" row is
#: the corpus's fall-2027 deadline). (b) "closing date(s)" labels a deadline
#: as "closes" does. (c) A table of intakes under one deadline label
#: ("Application closing dates / Summer School 2027 / 1 December 2026 /
#: Semester One 2027 / 8 December 2026 ...") gives the date on the requested
#: intake's own row. (d) The costs reader sees the same section, so another
#: intake's fee is never claimed and the requested intake's labelled tuition
#: is (Uppsala's "Total tuition fee: SEK 450,000" under Autumn 2027).
INTAKE_SECTION_DEADLINE = False


def _intake_rules_on() -> bool:
    """EX-2's rules: on under EX-2's own flag, or under DL-5, which absorbs it."""
    return DEADLINE_WINDOW_SCOPE or INTAKE_SECTION_DEADLINE


#: DL-5 (a): a line that is only a calendar-year intake: "Semester One 2027",
#: "Semester 2 2027", "Summer School 2027", "2027 Semester One".
_SEMESTER_SECTION = re.compile(
    r"^[^\S\n]*(?:(semester[^\S\n]+(?:one|two|1|2)|summer[^\S\n]+school)[^\S\n]+(20\d\d)"
    r"|(20\d\d)[^\S\n]+(semester[^\S\n]+(?:one|two|1|2)|summer[^\S\n]+school))"
    r"[^\S\n]*[,:]?[^\S\n]*$",
    re.IGNORECASE | re.MULTILINE,
)
_SEMESTER_KEY = {"one": "semester 1", "1": "semester 1", "two": "semester 2", "2": "semester 2"}
#: DL-5 (b): "closing date(s)" names the deadline as "closes" does.
_CLOSING_DATE_V2 = re.compile(
    rf"\bclosing\s+dates?\b[^.\n]{{0,60}}?({_A_DATE_V2})",
    re.IGNORECASE,
)
#: DL-5 (c): the label over a table of intakes says its dates are deadlines.
_INTAKE_TABLE_LABEL = re.compile(
    r"\b(?:deadlines?|closing\s+dates?|applications?\s+close|apply\s+by)\b[^\S\n]*:?[^\S\n]*\Z",
    re.IGNORECASE,
)
#: DL-5 (c): rows of one table of intakes stand at most this far apart.
_INTAKE_ROW_GAP = 80
#: DL-5 (c): a row's date follows its intake directly.
_INTAKE_ROW_DATE = re.compile(rf"[^\S\n]*:?\s{{0,12}}({_A_DATE_V2})", re.IGNORECASE)


def _intake_key(season: str, year: str) -> str:
    season = " ".join(season.lower().split())
    if season.startswith("semester"):
        return f"{_SEMESTER_KEY[season.split()[-1]]} {year}"
    return f"{'fall' if season == 'autumn' else season} {year}"


def _intake_heads(text: str) -> list[tuple[int, int, str]]:
    """Every line that is only an intake, ``(start, end, key)`` in page order."""
    heads = [
        (m.start(), m.end(), _intake_key(m.group(1), m.group(2)))
        for m in _INTAKE_SECTION.finditer(text)
    ]
    if INTAKE_SECTION_DEADLINE:
        for m in _SEMESTER_SECTION.finditer(text):
            season, year = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            heads.append((m.start(), m.end(), _intake_key(season, year)))
        heads.sort()
    return heads


def _wanted_intake(intake: object, keys: set[str]) -> str | None:
    """The section key of the requested intake on a page with these keys."""
    asked = re.search(r"(autumn|fall|spring|summer|winter)\s+(20\d\d)", str(intake or ""), re.I)
    if asked is None:
        return None
    want = _intake_key(asked.group(1), asked.group(2))
    first = f"semester 1 {asked.group(2)}"
    if INTAKE_SECTION_DEADLINE and want not in keys and want.startswith("fall") and first in keys:
        return first  # DL-5 (a): a calendar-year system's year opens with semester one
    return want


def _intake_section(text: str, intake: object) -> tuple[int, int] | None:
    """EX-2: the span the deadline readers may see on a page with per-intake
    sections, or ``None`` when the page has no such sections.

    ``text`` must still carry its line breaks. A page states sections only
    when at least two different intakes head lines of their own; every run of
    text between two such lines belongs to the intake that heads it, and the
    longest run for the requested intake is its section (a tab bar at the top
    of the page repeats each intake name once, with no content under it).
    Without a section for the requested intake, only the text before the
    first intake heading is the page's own for every intake.
    """
    heads = _intake_heads(text)
    keys = {key for _, _, key in heads}
    if len(keys) < 2:
        return None
    want = _wanted_intake(intake, keys)
    if want not in keys:
        return 0, heads[0][0]
    runs: list[tuple[int, int, str]] = []
    for index, (start, _end, key) in enumerate(heads):
        end = heads[index + 1][0] if index + 1 < len(heads) else len(text)
        if runs and runs[-1][2] == key:
            runs[-1] = (runs[-1][0], end, key)
        else:
            runs.append((start, end, key))
    start, end, _ = max((r for r in runs if r[2] == want), key=lambda r: r[1] - r[0])
    return start, end


def _deadline_scope(text: str, lined: str, builder: ClaimBuilder) -> str:
    """The text the deadline readers see: under EX-2 (or DL-5), with everything
    outside the requested intake's section blanked, so every offset still
    points into the page's own text and an excerpt never reaches into another
    intake. DL-5's costs reader sees the same text."""
    section = _intake_section(lined, builder.meta.get("intake")) if _intake_rules_on() else None
    if section is None:
        return text
    lo, hi = section
    return " " * lo + text[lo:hi] + " " * (len(text) - hi)


def _intake_row_deadline(text: str, lined: str, intake: object) -> tuple[str, int, int] | None:
    """DL-5 (c): the date on the requested intake's row of a table of intakes
    whose label names deadlines: ``(raw date, start, end)``, the span running
    from the label to the row's date; ``None`` when the page has no such table.

    The rows are intake headings at most ``_INTAKE_ROW_GAP`` characters apart,
    each followed directly by its own date; the label is the line just before
    the first row. Only the requested intake's row is read, and only when the
    table has exactly one row for it.
    """
    heads = _intake_heads(lined)
    keys = {key for _, _, key in heads}
    want = _wanted_intake(intake, keys)
    if len(keys) < 2 or want not in keys:
        return None
    tables: list[list[tuple[int, int, str]]] = []
    for head in heads:
        if tables and head[0] - tables[-1][-1][0] <= _INTAKE_ROW_GAP:
            tables[-1].append(head)
        else:
            tables.append([head])
    for rows in tables:
        mine = [row for row in rows if row[2] == want]
        if len(rows) < 2 or not mine:
            continue
        if len(mine) > 1:
            return None
        label_end = len(lined[: rows[0][0]].rstrip())
        if not _INTAKE_TABLE_LABEL.search(lined, max(0, label_end - 120), label_end):
            continue
        dated = _INTAKE_ROW_DATE.match(text, mine[0][1])
        if dated is None or _conditional_skip(text, dated, 1):
            return None
        return dated.group(1), lined.rfind("\n", 0, label_end) + 1, dated.end()
    return None


#: Other date columns a deadline table carries beside the deadline itself.
_OTHER_DATE_COLUMN = re.compile(
    r"\b(?:start(?:\s+(?:course|date|of\s+(?:studies|programme)))?|begins?|commencement)\b",
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
    "s$": "SGD",
    "hk$": "HKD",
    "hkd": "HKD",
    "c$": "CAD",
    "ca$": "CAD",
    "a$": "AUD",
    "au$": "AUD",
    "nz$": "NZD",
    "nzd": "NZD",
    "krw": "KRW",
    "jpy": "JPY",
    "kzt": "KZT",
    "₸": "KZT",
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


#: Euro amounts written the continental way: a dot groups thousands and a comma
#: marks cents (Groningen "€ 20.563", Delft "€ 18.750,00"). Without this rule
#: "€ 20.563" reads as 20.56 euros, a tuition fee below the floor.
EURO_GROUPING = False
_EURO_GROUPED = re.compile(
    r"(?:€|EUR)\s*(\d{1,3}(?:\.\d{3})+)(?:,(\d{2}))?(?![\d.,]\d)"
    r"|(\d{1,3}(?:\.\d{3})+)(?:,(\d{2}))?\s*(?:€|EUR)\b",
    re.IGNORECASE,
)


def _euro_grouped(m: re.Match[str]) -> tuple[float, str]:
    whole, cents = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    return float(whole.replace(".", "")) + (float(cents) / 100 if cents else 0.0), "EUR"


def _money_search(text: str) -> re.Match[str] | None:
    """The first money marker, a grouped euro amount included when the rule is on."""
    m = _MONEY.search(text)
    grouped = _EURO_GROUPED.search(text) if EURO_GROUPING else None
    if grouped is not None and (m is None or grouped.start() <= m.start()):
        return grouped
    return m


def parse_money(text: str) -> tuple[float, str] | None:
    m = _MONEY.search(text)
    if EURO_GROUPING:
        grouped = _EURO_GROUPED.search(text)
        if grouped is not None and (m is None or grouped.start() <= m.start()):
            return _euro_grouped(grouped)
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


def _keep(found: list[Claim], claim: Claim | None) -> None:
    """Append the claim unless the builder's verifier rejected it.

    A rejected claim stays recorded in ``builder.rejected`` with its reason;
    it never reaches the result list.
    """
    if claim is not None:
        found.append(claim)


def _named_bands(text: str) -> tuple[int, int, dict[str, float]] | None:
    """Per-section IELTS minimums, when the page names the sections itself.

    Anchored to a sentence that mentions IELTS: "Writing 6" on its own is a
    grade, a room number or a column of something else. Returns the span to
    quote and the bands, or nothing.
    """
    for start, end in _ielts_sentences(text):
        body = text[start:end]
        named = _IELTS_WORD.search(body)
        other = _OTHER_TEST.search(body, named.end()) if named else None
        if other:
            body = body[: other.start()]
        bands = {
            match.group(1).lower(): float(match.group(2))
            for match in _IELTS_NAMED_BAND.finditer(body)
            if 4.0 <= float(match.group(2)) <= 9.0
        }
        if bands:
            return start, end, bands
    return None


def _ielts_sentences(text: str) -> Iterable[tuple[int, int]]:
    """Spans of the sentences that name IELTS, in page order, each once.

    A sentence is the whole run between two terminators (a line break, or a
    full stop not followed by a digit), and a match of "IELTS" inside it is
    widened to that run. The word boundaries around it are judged against the
    whole page, as the old single pattern judged it.
    """
    ends = [m.start() for m in _IELTS_SENTENCE_END.finditer(text)]
    last_end = -1
    for hit in _IELTS_WORD.finditer(text):
        if hit.start() < last_end:
            continue
        # The first terminator at or after the word's end closes the sentence;
        # the one before it opens the sentence, one character after it.
        after = bisect_left(ends, hit.end())
        start = ends[after - 1] + 1 if after else 0
        end = ends[after] if after < len(ends) else len(text)
        last_end = end
        yield start, end


def _population_deadlines(text: str) -> list[tuple[str, str, int, int, str | None]]:
    """One deadline per population row of a deadline table, or none at all.

    Returns ``(population, iso_date, start, end, intake)`` only when the table names at
    least two populations: a single row is not a table, and the page-level
    reading already covers it. The date taken from each row is the one in the
    column the header calls the deadline — "Type of student | Deadline | Start
    course" puts it first, and a header that lists the start first puts it
    second. A header that cannot be read that way yields nothing rather than
    a start date presented as a deadline.
    """
    header = _DEADLINE_WORD.search(text)
    if header is None:
        return []
    rows = [
        m for m in _POPULATION_ROW.finditer(text, header.end()) if m.start() - header.end() < 600
    ]
    if not rows:
        return []
    zone = text[max(0, header.start() - 80) : rows[0].start()]
    # The header cell nearest the rows, not a "Deadlines" title above them:
    # "Deadlines — Start of studies | Deadline" puts the deadline second.
    cells = list(_DEADLINE_WORD.finditer(zone))
    if not cells:
        return []
    deadline_at = cells[-1]
    heading = cells[-2].end() if len(cells) > 1 else 0
    column = sum(
        1 for m in _OTHER_DATE_COLUMN.finditer(zone) if heading <= m.start() < deadline_at.start()
    )
    if column > 1:
        return []
    # A single start column beside the deadline ("Deadline | Start course") is
    # the programme's own start date, stated per row; the owner's decision of
    # 2026-09-23 reads a September–November start as that row's fall intake.
    starts = [m for m in _OTHER_DATE_COLUMN.finditer(zone) if m.start() >= heading]
    out: list[tuple[str, str, int, int, str | None]] = []
    seen: set[str] = set()
    for row in rows:
        population = population_named(row.group(1))
        raw = row.group(2) if column == 0 else row.group(3)
        parsed = parse_date_string(raw) if raw else None
        if population is None or parsed is None or population in seen:
            continue
        if _conditional_skip(text, row, 2 if column == 0 else 3):
            continue
        seen.add(population)
        intake = None
        if len(starts) == 1:
            start_raw = row.group(3) if column == 0 else row.group(2)
            started = parse_date_string(start_raw) if start_raw else None
            if started is not None:
                intake = intake_from_start(started.strftime("%B"), str(started.year))
        out.append((population, parsed.isoformat(), row.start(), row.end(), intake))
    return out if len(out) >= 2 else []


#: A date its own label names the application deadline: Imperial's
#: "Application deadlines – Wednesday 13 January 2027 at 18.00 (UK time)". A
#: late or extended round is not the deadline the applicant is held to. The
#: claim is quoted from the word "deadline", where the generic reader quotes a
#: "The application deadline ... is <date>" sentence from, so its excerpt does
#: not move when this reader finds the same date.
_APPLICATION_DEADLINE_V2 = re.compile(
    rf"(?<!late\s)(?<!extended\s)\bapplication\s+deadlines?\b[^.\n]{{0,40}}?({_A_DATE_V2})",
    re.IGNORECASE,
)
#: A date for an admissions test — its sitting, its booking or its results —
#: is never the application deadline, however it is labelled. Imperial's TMUA
#: block ("Test window 2: 8 January 2027 ... Booking closes: 28 September
#: 2026") was read as the deadline.
_TEST_SITTING_CONTEXT = re.compile(
    r"\b(?:TMUA|UCAT|LNAT|BMAT|ESAT|TSA)\b"
    r"|\btest\s+(?:windows?|dates?|sittings?|centres?|centers?|registration|booking)\b"
    r"|\bsit(?:ting)?\s+(?:the|your|a|an)\s+(?:\w+\s+){0,2}?(?:test|exam)\b"
    r"|\bregist(?:er|ration)\s+for\s+(?:the|your|a|an)\s+(?:\w+\s+){0,2}?(?:test|exam)\b"
    r"|\bbook(?:ing)?\s+(?:for\s+)?(?:the|your|a|an)\s+(?:\w+\s+){0,2}?(?:test|exam)\b"
    r"|\bbookings?\s+(?:closes?|opens?|windows?|deadlines?)\b"
    r"|\bresults?\s+(?:are\s+|will\s+be\s+)?released\b",
    re.IGNORECASE,
)
#: How far before a reader's match its sentence may name the test: a generic
#: "closes"/"due" may sit under the test's own label ("Booking closes"), an
#: "application deadline" label only directly after one ("UCAT application
#: deadline").
_TEST_CONTEXT_LOOKBEHIND = 80
_TEST_LABEL_LOOKBEHIND = 24
_SENTENCE_STOP = re.compile(r"\.(?!\d)")


def _test_sitting_date(text: str, match: re.Match[str], lookbehind: int) -> bool:
    """Whether the date in ``match`` (group 1) belongs to an admissions test.

    The context is the reader's own span up to the date, and at most
    ``lookbehind`` characters before it, never past the previous full stop or
    the previous date: a test named in another sentence, or beside another
    date, does not taint this one.
    """
    flat = _CLOCK_DOTS.sub(lambda m: m.group(0).replace(".", " "), text)
    lo = max(0, match.start() - lookbehind)
    for stop in _SENTENCE_STOP.finditer(flat, lo, match.start()):
        lo = stop.end()
    for other in _ANY_DATE_V2.finditer(flat, lo, match.start()):
        lo = max(lo, other.end())
    return _TEST_SITTING_CONTEXT.search(flat, lo, match.start(1)) is not None


#: A date whose own clause announces that something opens or is published is
#: not a deadline, whatever heading it sits under. Imperial's "UCAS deadlines
#: for 2027 entry 28 April 2026 – UCAS' search tool opens" was read as the
#: deadline. The clause after the date ends at a comma, semicolon, full stop or
#: line break, so "15 January 2027; applications open ..." is still a deadline.
_OPENING_AFTER_DATE = re.compile(
    r"\s*(?:\([^)]{0,40}\)\s*)?[-–—:]?[^,;.\n]{0,40}?"
    r"\b(?:opens?|can\s+be\s+submitted|results?\s+(?:are\s+|will\s+be\s+)?published|released)\b",
    re.IGNORECASE,
)
#: The same, written before the date inside the reader's own span ("the
#: deadline page: applications open on 1 October 2026").
_OPENING_BEFORE_DATE = re.compile(
    r"\b(?:opens?|opening|can\s+be\s+submitted(?:\s+from)?|submitted\s+from"
    r"|results?\s+(?:are\s+|will\s+be\s+)?published)\b[^,;.\n]{0,20}\Z",
    re.IGNORECASE,
)


def _opening_date(text: str, match: re.Match[str]) -> bool:
    """Whether the date in ``match`` (group 1) is an opening or announcement date."""
    if _OPENING_AFTER_DATE.match(text, match.end(1)):
        return True
    if _DATE_RANGE_V2.match(text, match.start(1)) is not None:
        return False  # "from 1 October 2026 until 15 January 2027" ends on the deadline
    return _OPENING_BEFORE_DATE.search(text[match.start() : match.start(1)]) is not None


def _first_admission_date(
    pattern: re.Pattern[str], text: str, lookbehind: int
) -> re.Match[str] | None:
    """The first match of ``pattern`` whose date (group 1) is neither an award
    deadline (rule DL-3, when on), an admissions test's date nor the day
    something opens or is published."""
    for match in pattern.finditer(text):
        if _conditional_skip(text, match, 1):
            continue
        if _test_sitting_date(text, match, lookbehind):
            continue
        if _opening_date(text, match):
            continue
        return match
    return None


def _deadline_v2(text: str) -> tuple[str, int, int, str | None, str | None] | None:
    """The page's application deadline under rule DL-2: ``(raw date, start,
    end, qualification, intake)``, or ``None`` when the page does not say
    which date applies.

    A date labelled "Applications due" wins. Otherwise a single window ends
    on the deadline; several windows that end on different dates name a
    deadline only through their catch-all row, recorded with that row's own
    words as the qualification it is for.
    """
    due = (
        _first_unconditional(_DATE_FIRST_DEADLINE, text)
        if DEADLINE_AWARD_CONDITION
        else _DATE_FIRST_DEADLINE.search(text)
    )
    if due:
        session = _SESSION_START.search(due.group(2))
        intake = intake_from_start(session.group(1), session.group(2)) if session else None
        return due.group(1), due.start(), due.end(), None, intake
    # A catch-all row says whom its window is for even when it is the only
    # window read: NTU's run on 2026-10-05 dated the right day with no
    # qualification because the page's other rows did not reach the reader.
    catch_all = _CATCH_ALL_WINDOW.search(text)
    if catch_all is not None and not _conditional_skip(text, catch_all, 3):
        return catch_all.group(3), catch_all.start(), catch_all.end(), catch_all.group(1), None
    windows = _application_windows(text, _DATE_RANGE_V2)
    if len({m.group(2) for m in windows}) > 1:
        return None
    # A date its label calls the application deadline beats any other
    # "closes"/"due" date, and none of them may be a test's sitting or booking
    # date (Imperial: "Booking closes: 28 September 2026" for the TMUA was read
    # ahead of "Application deadlines – Wednesday 13 January 2027").
    match = (
        _first_admission_date(_APPLICATION_DEADLINE_V2, text, _TEST_LABEL_LOOKBEHIND)
        or _first_admission_date(_DEADLINE_V2, text, _TEST_CONTEXT_LOOKBEHIND)
        or _first_admission_date(_APPLICATION_PERIOD_V2, text, _TEST_CONTEXT_LOOKBEHIND)
        or (
            _first_admission_date(_CLOSING_DATE_V2, text, _TEST_CONTEXT_LOOKBEHIND)
            if INTAKE_SECTION_DEADLINE
            else None
        )
    )
    if match is None:
        return None
    opened = _DATE_RANGE_V2.match(text, match.start(1))
    raw = opened.group(2) if opened is not None else match.group(1)
    start = match.start()
    if match.re is _APPLICATION_DEADLINE_V2:
        start += match.group(0).lower().index("deadline")
    return raw, start, match.end(), None, None


def _toefl_total(text: str) -> tuple[int, int, int] | None:
    """The first TOEFL total stated on the page: (score, start, end).

    "78 in TOEFL" is read before the words after it, and a forward scan never
    crosses into another test's statement or takes a number that is followed by
    "in PTE"; a mention that yields nothing leaves the next one to answer.
    """
    for word in _TOEFL_WORD.finditer(text):
        back = _TOEFL_NUMBER_FIRST.search(text[max(0, word.start() - 40) : word.end()])
        if back:
            start = word.end() - (len(back.string) - back.start())
            return int(back.group(1)), start, word.end()
        forward = _TOEFL.match(text, word.start())
        if forward and not _OTHER_TESTS_SCORE.match(text, forward.end()):
            return int(forward.group(1)), forward.start(), forward.end()
    return None


# --- plan change EN-2 / TF-2: English readers v2 -------------------------------

#: EN-2 (core-gap analysis 2026-10-18, changes 2 and 7). On: the structural
#: reader attributes a table to a test by its column headers or its own label
#: and picks the programme's row (``structured_extraction``); a level layout
#: ("IELTS ... Standard Higher 6.5 overall ... 7.0 overall") is read for the
#: level the programme page names, else abstained on; the TOEFL total skips
#: dates, section scores and scales inside TOEFL's own statement. Off:
#: unchanged.
ENGLISH_READERS_V2 = False

#: A month written as a date's month. Case-sensitive on purpose: "90 may be
#: accepted" is not a date.
_TOEFL_DATE_BEFORE = re.compile(rf"\b(?:{_MONTH_NAMES}|{_MONTH_ABBREVIATIONS})\.?\s*$")
_TOEFL_DATE_AFTER = re.compile(
    rf"\s*(?:st|nd|rd|th)?\s*(?:of\s+)?(?:{_MONTH_NAMES}|(?:{_MONTH_ABBREVIATIONS})\.?)(?![a-z])"
    r"|\s*[/.]\s*\d"
)
#: "20 (scale 0-30)", "20/30": a section score on its own scale.
_TOEFL_SCALE_AFTER = re.compile(
    r"\s*(?:\(\s*(?:on\s+a\s+)?(?:scale|out\s+of)|(?:/|out\s+of)\s*30\b)", re.IGNORECASE
)
#: "21 in each section", "20 in written test": a per-section minimum.
_TOEFL_SECTION_AFTER = re.compile(
    r"\s*(?:points?\s+)?(?:in|on|for)\s+(?:the\s+)?(?:each|every|all|any|writing|reading"
    r"|listening|speaking|written|oral|sections?|sub-?(?:scores?|tests?|sections?)|skills?"
    r"|components?|modules?)\b",
    re.IGNORECASE,
)
_TOEFL_SECTION_BEFORE = re.compile(
    r"\b(?:writing|reading|listening|speaking|sections?|sub-?scores?|components?|skills?)"
    r"\s*(?:score\s*)?(?:of\s*|:\s*|-\s*)?(?:at\s+least\s*|(?:a\s+)?minimum\s*(?:of\s*)?)?$",
    re.IGNORECASE,
)
_TOEFL_RANGE_AFTER = re.compile(r"\s*(?:[-–—]\s*\d|%)")
_TOEFL_RANGE_BEFORE = re.compile(r"\d\s*[-–—]\s*$")
#: A whole two- or three-digit number: never the "202" of "2026" or the "5" of "4.5".
_TOEFL_NUMBER = re.compile(r"(?<![\d.])(\d{2,3})(?:\.0)?(?!\d|\.\d)")
#: "total score of 90", "overall band score of at least 90": the total, named.
_TOEFL_NAMED_TOTAL = re.compile(
    r"\b(?:total|overall)(?:\s+(?:band\s+)?score)?\s*(?:of\s*)?"
    r"(?:at\s+least\s*|(?:a\s+)?minimum\s*(?:of\s*)?)?:?\s*(?<![\d.])(\d{2,3})(?:\.0)?(?!\d|\.\d)",
    re.IGNORECASE,
)
#: TOEFL's own statement: up to 90 characters, never past a full stop (a
#: decimal point is not one: "90.0 Overall"), a line break or another test's
#: name (the window ``_TOEFL`` scans).
_TOEFL_STATEMENT = re.compile(
    rf"(?:(?!\b{_NOT_TOEFL}\b)(?:[^.\n]|\.(?=\d))){{0,90}}", re.IGNORECASE
)


def _toefl_number_is_total(text: str, start: int, end: int) -> bool:
    """False for a number that is a date, a section score, a scale or a range."""
    before = text[max(0, start - 40) : start]
    if _TOEFL_DATE_BEFORE.search(before) or _TOEFL_DATE_AFTER.match(text, end):
        return False
    if _TOEFL_SCALE_AFTER.match(text, end) or _TOEFL_SECTION_AFTER.match(text, end):
        return False
    if _TOEFL_SECTION_BEFORE.search(before) or _TOEFL_RANGE_BEFORE.search(before):
        return False
    if _TOEFL_RANGE_AFTER.match(text, end):
        return False
    return not _OTHER_TESTS_SCORE.match(text, end)


def _toefl_total_v2(text: str) -> tuple[int, int, int] | None:
    """TF-2: the first TOEFL total on the page, past dates and section scores.

    "78 in TOEFL" is read first, as :func:`_toefl_total` reads it. Forward, a
    total the statement names ("total score of 90") wins; else the first number
    that is not a date ("January 21, 2026"), a section score ("20 (scale
    0-30)", "21 in each section") or a range. A number outside 40-120 ends that
    mention, and the next mention answers instead (Delft: "obtained before
    January 21, 2026: A TOEFL iBT with an overall band score of at least 90").
    """
    for word in _TOEFL_WORD.finditer(text):
        back = _TOEFL_NUMBER_FIRST.search(text[max(0, word.start() - 40) : word.end()])
        if back:
            start = word.end() - (len(back.string) - back.start())
            return int(back.group(1)), start, word.end()
        statement = _TOEFL_STATEMENT.match(text, word.end())
        stop = statement.end() if statement else word.end()
        named = _TOEFL_NAMED_TOTAL.search(text, word.end(), stop)
        if (
            named
            and 40 <= int(named.group(1)) <= 120
            and _toefl_number_is_total(text, named.start(1), named.end())
        ):
            return int(named.group(1)), word.start(), named.end()
        for number in _TOEFL_NUMBER.finditer(text, word.end(), stop):
            if not _toefl_number_is_total(text, number.start(1), number.end()):
                continue
            if 40 <= int(number.group(1)) <= 120:
                return int(number.group(1)), word.start(), number.end()
            break
    return None


#: The English level a programme page says applies to it: TCD "required to meet
#: Band B (Standard Entry) English language requirements", Imperial "you must
#: achieve the standard university requirement in the appropriate English
#: language qualification".
_ENGLISH_ENTRY_LEVEL = re.compile(
    r"\b(?:required\s+to\s+(?:meet|achieve|satisfy|have)|(?:must|need\s+to)\s+"
    r"(?:meet|achieve|satisfy|have)|requires?)\s+(?:the\s+)?"
    r"(?:Band\s+(?P<band>[A-E])\b(?:\s*\(\s*(?P<band_level>standard|higher)\s+entry\s*\))?"
    r"|(?P<level>standard|higher)\s+(?:university\s+|English\s+(?:language\s+)?)?"
    r"(?:level|requirements?|entry)\b)",
    re.IGNORECASE,
)
_ENGLISH_WORD = re.compile(r"\bEnglish\b", re.IGNORECASE)
_STATEMENT_END = re.compile(r"\.(?!\d)")


def english_programme_hint(text: str, html: str, degree: str | None = None) -> EnglishHint:
    """EN-2: which English row a programme page says is its own.

    The faculty is :func:`programme_faculty` when the page states one; else
    every unit the page names ("part of the Faculty of Engineering"), which
    only ever narrows a table to the rows it names. A band or level counts only
    from a sentence about English, and only when the page names exactly one.
    """
    flat = for_matching(text)
    bands: set[str] = set()
    levels: set[str] = set()
    for m in _ENGLISH_ENTRY_LEVEL.finditer(flat):
        before = _STATEMENT_END.split(flat[max(0, m.start() - 240) : m.start()])[-1]
        after = _STATEMENT_END.split(flat[m.end() : m.end() + 160])[0]
        if not _ENGLISH_WORD.search(f"{before}{m.group(0)}{after}"):
            continue
        if m.group("band"):
            bands.add(m.group("band").lower())
        level = m.group("band_level") or m.group("level")
        if level:
            levels.add(level.lower())
    unit = programme_faculty(text, html)
    units = (
        frozenset({unit})
        if unit
        else frozenset(k for m in _UNIT_NAME.finditer(text) if (k := faculty_key(m.group(0))))
    )
    return EnglishHint(
        units=units,
        band=next(iter(bands)) if len(bands) == 1 else None,
        level=next(iter(levels)) if len(levels) == 1 else None,
        degree=degree,
    )


#: Imperial's level layout, flattened: "IELTS – Academic (Test-Centre/UKVI
#: SELT/Online) Standard Higher 6.5 overall (minimum 6.0 in all elements) 7.0
#: overall (minimum 6.5 in all elements)". The labels come first, then one
#: band statement per label, in the same order.
_LEVEL_LABEL = r"(?:standard|higher)(?:\s+(?:level|entry|requirements?))?"
_IELTS_LEVEL_HEAD = re.compile(
    rf"\bIELTS\b[^\d.\n]{{0,80}}?\b(?P<labels>{_LEVEL_LABEL}(?:\s+(?:and\s+|or\s+|/\s*)?"
    rf"{_LEVEL_LABEL})+)\s+(?=\d)",
    re.IGNORECASE,
)
_IELTS_LEVEL_VALUE = re.compile(
    r"\s*(\d(?:\.\d)?)\s*overall\b"
    r"(?:\s*\(\s*min(?:imum|\.)?\s*(?:of\s*)?(\d(?:\.\d)?)\s+in\s+(?:each|all|every)"
    r"\s+[\w-]+(?:\s+[\w-]+)?\s*\)"
    r"|\s*,?\s*(?:with\s+)?(\d(?:\.\d)?)\s+in\s+(?:each|all|every)\s+(?:band|section|subtest"
    r"|element|component|skill|module|part)s?\b)?",
    re.IGNORECASE,
)


def _ielts_band(raw: str) -> float | None:
    value = float(raw)
    return value if 4.0 <= value <= 9.0 and (value * 2).is_integer() else None


def _ielts_by_level(
    text: str, hint: EnglishHint | None
) -> tuple[float, float | None, int, int] | Literal[False] | None:
    """EN-2: the IELTS band of the programme's level, from a level layout.

    None when the page has no such layout. False when it has one and the
    programme's level is not known, not among the labels, or the bands do not
    pair with the labels one to one: two bands for two levels are two
    requirements, and taking the first would be choosing one silently.
    """
    head = _IELTS_LEVEL_HEAD.search(text)
    if head is None:
        return None
    labels = [w.lower() for w in re.findall(r"standard|higher", head.group("labels"), re.I)]
    values: list[re.Match[str]] = []
    pos = head.end()
    for _ in labels:
        value = _IELTS_LEVEL_VALUE.match(text, pos)
        if value is None:
            break
        values.append(value)
        pos = value.end()
    wanted = hint.level if hint else None
    if len(values) != len(labels) or len(set(labels)) != len(labels) or wanted not in labels:
        return False
    chosen = values[labels.index(wanted)]
    overall = _ielts_band(chosen.group(1))
    raw_sub = chosen.group(2) or chosen.group(3)
    sub = _ielts_band(raw_sub) if raw_sub else None
    if overall is None or (raw_sub and (sub is None or sub > overall)):
        return False
    return overall, sub, head.start(), chosen.end()


def extract_requirements(text: str, builder: ClaimBuilder) -> list[Claim]:
    """Pull admission requirements out of readable page text."""
    found: list[Claim] = []
    lined = text
    text = for_matching(text)

    # EN-2: a level layout answers IELTS for the programme's level or not at
    # all, and a type a table reader of this page abstained on stays unread.
    abstained = builder.english_abstained if ENGLISH_READERS_V2 else set()
    levelled = _ielts_by_level(text, builder.english_hint) if ENGLISH_READERS_V2 else None
    if levelled:
        overall, sub, start, end = levelled
        for claim_type, band in (
            (ClaimType.IELTS_MIN_OVERALL, overall),
            (ClaimType.IELTS_MIN_SUBSCORE, sub),
        ):
            if band is not None:
                _keep(
                    found,
                    builder.add(
                        claim_type,
                        band,
                        excerpt_around(text, start, end),
                        section="English language requirements",
                    ),
                )
    skip_overall = levelled is not None or ClaimType.IELTS_MIN_OVERALL in abstained
    skip_sub = levelled is not None or ClaimType.IELTS_MIN_SUBSCORE in abstained

    for m in () if skip_overall else _IELTS_OVERALL.finditer(text):
        raw = next((g for g in m.groups() if g), None)
        if raw is None:
            continue
        value = float(raw)
        if not 4.0 <= value <= 9.0:
            continue
        _keep(
            found,
            builder.add(
                ClaimType.IELTS_MIN_OVERALL,
                value,
                excerpt_around(text, m.start(), m.end()),
                section="English language requirements",
            ),
        )
        break

    # Sections named one by one beat a single floor, because they say more:
    # "Writing 6, Speaking 6" is not the same statement as "no band below 6".
    named = None if skip_sub else _named_bands(text)
    if named:
        start, end, bands = named
        _keep(
            found,
            builder.add(
                ClaimType.IELTS_MIN_SUBSCORE,
                bands,
                excerpt_around(text, start, end),
                section="English language requirements",
            ),
        )
    elif not skip_sub:
        for m in _IELTS_SUB.finditer(text):
            raw = m.group(1) or m.group(2)
            if raw is None:
                continue
            value = float(raw)
            if 4.0 <= value <= 9.0:
                _keep(
                    found,
                    builder.add(
                        ClaimType.IELTS_MIN_SUBSCORE,
                        value,
                        excerpt_around(text, m.start(), m.end()),
                        section="English language requirements",
                    ),
                )
                break

    if ClaimType.TOEFL_MIN_TOTAL in abstained:
        toefl = None
    else:
        toefl = _toefl_total_v2(text) if ENGLISH_READERS_V2 else _toefl_total(text)
    if toefl and 40 <= toefl[0] <= 120:
        _keep(
            found,
            builder.add(
                ClaimType.TOEFL_MIN_TOTAL,
                toefl[0],
                excerpt_around(text, toefl[1], toefl[2]),
            ),
        )

    duolingo = None if ClaimType.DUOLINGO_MIN in abstained else _DUOLINGO.search(text)
    if duolingo and 60 <= int(duolingo.group(1)) <= 160:
        _keep(
            found,
            builder.add(
                ClaimType.DUOLINGO_MIN,
                int(duolingo.group(1)),
                excerpt_around(text, duolingo.start(), duolingo.end()),
            ),
        )

    gpa = _GPA.search(text)
    if gpa:
        value, scale = float(gpa.group(1)), float(gpa.group(2))
        # The scale must bound the value, or we have matched two unrelated numbers.
        if 0 < value <= scale <= 100:
            ex = excerpt_around(text, gpa.start(), gpa.end())
            _keep(found, builder.add(ClaimType.MIN_GPA, value, ex))
            _keep(found, builder.add(ClaimType.GPA_SCALE, scale, ex))

    optional = _SAT_OPTIONAL.search(text)
    if optional:
        _keep(
            found,
            builder.add(
                ClaimType.SAT_POLICY,
                optional.group(1),
                excerpt_around(text, optional.start(), optional.end()),
            ),
        )
    else:
        sat_min = _SAT_MIN.search(text)
        # Either alternative may carry the number: "SAT ... 1250" or
        # "1250 ... SAT". Whichever group matched is the score.
        score = next((g for g in (sat_min.groups() if sat_min else ()) if g), None)
        if sat_min and score and 400 <= int(score) <= 1600:
            _keep(
                found,
                builder.add(
                    ClaimType.SAT_MIN_TOTAL,
                    int(score),
                    excerpt_around(text, sat_min.start(), sat_min.end()),
                ),
            )

    superscore = _SUPERSCORE.search(text)
    if superscore:
        _keep(
            found,
            builder.add(
                ClaimType.SUPERSCORE_POLICY,
                superscore.group(1),
                excerpt_around(text, superscore.start(), superscore.end()),
            ),
        )

    # EX-2: the deadline readers see the requested intake's section only.
    dated = _deadline_scope(text, lined, builder)
    rows = _population_deadlines(dated)
    for population, iso, start, end, intake in rows:
        _keep(
            found,
            builder.add(
                ClaimType.ADMISSION_DEADLINE,
                iso,
                excerpt_around(dated, start, end),
                notes="timezone: not stated on page",
                subject_key=population,
                population=population,
                intake=intake,
            ),
        )
    if DEADLINE_V2 and not rows:
        read = _deadline_v2(dated)
        parsed = parse_date_string(read[0]) if read else None
        if read and parsed:
            _raw, start, end, qualification, intake = read
            ex = excerpt_around(dated, start, end)
            _keep(
                found,
                builder.add(
                    ClaimType.ADMISSION_DEADLINE,
                    parsed.isoformat(),
                    ex,
                    notes=f"timezone: {parse_timezone(ex) or 'not stated on page'}",
                    qualification=qualification,
                    intake=intake,
                ),
            )
        row = (
            _intake_row_deadline(text, lined, builder.meta.get("intake"))
            if INTAKE_SECTION_DEADLINE and not (read and parsed)
            else None
        )
        on_row = parse_date_string(row[0]) if row else None
        if row and on_row:
            ex = excerpt_around(text, row[1], row[2])
            _keep(
                found,
                builder.add(
                    ClaimType.ADMISSION_DEADLINE,
                    on_row.isoformat(),
                    ex,
                    notes=f"timezone: {parse_timezone(ex) or 'not stated on page'}; "
                    "DL-5: the requested intake's row of the page's table of intakes",
                ),
            )
    deadline_match = (
        None
        if rows or DEADLINE_V2
        else (
            _first_unconditional(_DEADLINE, dated)
            or _first_unconditional(_APPLICATION_PERIOD, dated)
            if DEADLINE_AWARD_CONDITION
            else (_DEADLINE.search(dated) or _APPLICATION_PERIOD.search(dated))
        )
    )
    deadline_raw = deadline_match.group(1) if deadline_match else None
    if deadline_match:
        # A date that opens a range is a window start, never the deadline
        # (NTU: "Online application 15 October 2026 - 19 March 2027" was read
        # as a 15 October deadline, paired run 37234751647). The window's end
        # is the deadline; when the page states several windows that end on
        # different dates — one per qualification — none is claimed, because
        # nothing here says which one applies to the applicant.
        windows = {m.group(2) for m in _application_windows(dated, _DATE_RANGE)}
        opened = _DATE_RANGE.match(dated, deadline_match.start(1))
        if len(windows) > 1:
            deadline_raw = None
        elif opened is not None:
            deadline_raw = opened.group(2)
    if deadline_match and deadline_raw:
        deadline = parse_date_string(deadline_raw)
        if deadline:
            ex = excerpt_around(dated, deadline_match.start(), deadline_match.end())
            _keep(
                found,
                builder.add(
                    ClaimType.ADMISSION_DEADLINE,
                    deadline.isoformat(),
                    ex,
                    notes=f"timezone: {parse_timezone(ex) or 'not stated on page'}",
                ),
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
            _keep(
                found,
                builder.add(
                    ctype,
                    True,
                    excerpt_around(text, requirement.start(), requirement.end()),
                    confidence=0.7,
                ),
            )

    _keep(found, extract_admission_route(text, builder))
    for claim in extract_intake_terms(text, builder):
        _keep(found, claim)
    return found


_MONTH_SEASON = {
    "august": "fall",
    "september": "fall",
    "october": "fall",
    "january": "spring",
    "february": "spring",
    "march": "spring",
}
#: "Students beginning their studies in September 2027", "Program start Fall
#: 2027", "applying for September 2027 admission". A start cue must sit next to
#: the term; a deadline, a graduation or a fee sentence is never an intake.
_TERM = (
    r"(?:(?P<season>fall|autumn|spring)\s+(?P<sy>20\d\d)"
    r"|(?P<month>august|september|october|january|february|march)\s+(?:\d{1,2},?\s+)?(?P<my>20\d\d))"
)
_START_CUE = (
    r"(?:begin(?:s|ning)?|start(?:s|ing)?|commenc\w*|entering|entry|intake|enrol\w*|"
    r"admission|program(?:me)?\s+start)"
)
_INTAKE_CUE_FIRST = re.compile(rf"\b{_START_CUE}\b[^.\n]{{0,60}}?\b{_TERM}\b", re.I)
_INTAKE_TERM_FIRST = re.compile(rf"\b{_TERM}\s+(?:intake|entry|start)\b", re.I)
_NOT_AN_INTAKE = re.compile(
    r"deadline|due\b|apply by|closes?\b|graduat|convocation|tuition|fee", re.I
)

#: The text just before a date that ends a range: "... to 19 March 2026".
_ENDS_A_RANGE = re.compile(r"(?:\bto|\buntil|\btill|[-–—])\s*(?:\d{1,2}\s+)?$", re.I)


def extract_intake_terms(text: str, builder: ClaimBuilder) -> list[Claim]:
    """Each intake term a page states as a start ("fall 2027"), once each.

    V2-30A's INTAKE_TERM had no reader. Only a stated start counts: a date
    beside "deadline" or "graduation" is a different fact, and a month is
    mapped to a season only where the mapping is unambiguous for an academic
    start (August-October fall, January-March spring).
    """
    flat = for_matching(text)
    out: list[Claim] = []
    seen: set[str] = set()
    matches = sorted(
        [*_INTAKE_CUE_FIRST.finditer(flat), *_INTAKE_TERM_FIRST.finditer(flat)],
        key=lambda m: m.start(),
    )
    for m in matches:
        start, end = _sentence_bounds(text, m.start(), m.end())
        sentence = flat[start:end].strip()
        if _NOT_AN_INTAKE.search(sentence):
            continue
        if m.group("month") and re.search(r"\d", flat[m.start("month") : m.start("my")]):
            # "Beginning January 21, 2026, TOEFL score reports ..." (Groningen):
            # a day names an event; a term of study is a month or a season.
            continue
        term_at = m.start("season") if m.group("season") else m.start("month")
        if _ENDS_A_RANGE.search(flat[max(0, term_at - 24) : term_at]):
            # "Online Application ... to 19 March 2026" closes a window; the
            # end of an application period is not the start of study (NTU).
            continue
        season = (
            m.group("season") or _MONTH_SEASON.get((m.group("month") or "").lower(), "")
        ).lower()
        season = "fall" if season == "autumn" else season
        year = m.group("sy") or m.group("my")
        if not season or not year:
            continue
        value = f"{season} {year}"
        if value in seen:
            continue
        seen.add(value)
        claim = builder.add(ClaimType.INTAKE_TERM, value, sentence, confidence=0.7)
        if claim is not None:
            out.append(claim)
    return out


#: "Admitted without a declared major; the major is chosen later" (V2-30A
#: ADMISSION_ROUTE). The KAIST blind trace of 2026-09-27 found it stated in
#: Korean on a department page; nothing read it. Two shapes, both explicit:
#: admission *without* a major, or a major chosen at a stated later point.
#: "Students may change their major" is neither and must not match.
_UNDECLARED_ADMISSION = re.compile(
    r"(?:"
    r"무학과로?\s*입학"
    r"|전공\s*(?:선택|결정)\s*없이[^.。]{0,40}입학"
    r"|admit\w*\s+(?:as\s+)?(?:an?\s+)?(?:undeclared|undecided)"
    r"|admit\w*[^.]{0,40}\bwithout\s+(?:a\s+)?(?:declared\s+|chosen\s+)?major"
    r"|(?:enter|enrol+|join)\w*[^.]{0,40}\bwithout\s+(?:a\s+)?(?:declared\s+)?major"
    r")",
    re.I,
)
_LATER_MAJOR_CHOICE = re.compile(
    r"(?:"
    r"\d\s*학기\s*(?:때|에|부터)?[^.。]{0,30}전공[^.。]{0,20}선택"
    r"|(?:choose|select|declare)\w*\s+(?:a|their|your)\s+major\s+"
    r"(?:at\s+the\s+end\s+of|after|in)\s+(?:the|their|your)\s+"
    r"(?:first|second|1st|2nd)\s+(?:year|semester)"
    r")",
    re.I,
)


def extract_admission_route(text: str, builder: ClaimBuilder) -> Claim | None:
    """Undergraduates admitted without a declared major, choosing one later.

    One claim per page, quoted from the page's own sentence(s). The value is
    the corpus vocabulary ``undeclared_then_major_selection``; anything less
    explicit than admission-without-major or a dated later choice is left
    UNKNOWN rather than guessed.
    """
    flat = for_matching(text)
    admitted = _UNDECLARED_ADMISSION.search(flat)
    later = _LATER_MAJOR_CHOICE.search(flat)
    if admitted is None and later is None:
        return None
    first = admitted or later
    assert first is not None
    # Bounds on the original text, where a line break still separates a menu
    # item from the sentence; offsets are identical to ``flat``'s.
    start, end = _sentence_bounds(text, first.start(), first.end())
    if admitted is not None and later is not None and later.start() >= end:
        # The dated choice usually follows in the next sentence; quote both.
        _, later_end = _sentence_bounds(text, later.start(), later.end())
        if later_end - start <= 400:
            end = later_end
    excerpt = flat[start:end].strip()
    return builder.add(
        ClaimType.ADMISSION_ROUTE,
        "undeclared_then_major_selection",
        excerpt,
        confidence=0.75 if admitted is not None else 0.65,
    )


_SENTENCE_END = re.compile(r"[.。!?]|\n|\s{2,}")


def _sentence_bounds(text: str, start: int, end: int, limit: int = 200) -> tuple[int, int]:
    """The sentence around ``start:end``: back to the previous full stop or
    blank run, forward to the next, never more than ``limit`` either way. A
    page with no punctuation between its menu and its text (KAIST) would
    otherwise quote the whole menu."""
    lo = max(0, start - limit)
    before = list(_SENTENCE_END.finditer(text, lo, start))
    s = before[-1].end() if before else lo
    after = _SENTENCE_END.search(text, end, min(len(text), end + limit))
    e = after.end() if after else min(len(text), end + limit)
    return s, e


#: A tuition under this amount is a misread window, never a real figure: the
#: 120-character label window routinely swallows a nearby "$50 application
#: fee", and no university charges under $100 a year. The floor applies to
#: TUITION (and the same-window TOTAL_COST_OF_ATTENDANCE); small legitimate
#: numbers keep flowing for the other cost lines and for the application fee
#: itself, which is read by its own extractor.
TUITION_FLOOR_AMOUNT: Final = 100.0

_FLOOR_AT_TUITION: Final[frozenset[ClaimType]] = frozenset(
    {ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE}
)


#: An academic year as fee tables print it: 2027-2028, 2027/28, 2027–28.
_ACADEMIC_YEAR = re.compile(r"\b(20\d{2})\s*[-/–]\s*(?:20)?(\d{2})\b")


#: Plan rule TY-1: a fee table row that prints its academic year ("non-EU/EEA
#: 2027-2028 € 19800") records that year in the claim's scope. Without it the
#: page-wide scope carries no year and a right fee for the right year is
#: scored wrong-scope (Groningen, runs of 2026-10-05). On by default with AY-1
#: since 2026-10-05 (owner: "да").
TUITION_ROW_YEAR = True


def _year_key(text: str) -> str | None:
    m = _ACADEMIC_YEAR.search(text or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def _population_amounts(
    text: str, label: str, academic_year: str | None = None
) -> list[tuple[str, float, str, int, int]]:
    """One fee per population row of a fee table, or none at all.

    ``(population, amount, currency, start, end)`` — only when the table after
    ``label`` names at least two populations, each followed by its own amount
    before the next one begins. The statutory EU/EEA fee and the institutional
    non-EU/EEA fee are different numbers on one page, and the first-match
    reading quoted whichever came first to everybody.

    The label must stand as a word, not inside a link slug: Groningen's
    programme page says ``…/application-enrolment-tuition-fees/…`` in two
    links before its "Tuition fees" table, and the first-match header read the
    link and missed the table (expert trace, 2026-10-04). Every standalone
    occurrence is tried until one yields a table. When a population has one
    row per academic year, the row for ``academic_year`` is kept if present.
    """
    want = _year_key(academic_year or "")
    for header in re.finditer(rf"(?<![\w/-]){label}(?![\w/-])", text, re.IGNORECASE):
        names = [
            m
            for m in _POPULATION_WORD.finditer(text, header.end())
            if m.start() - header.end() < 600
        ]
        rows: dict[str, tuple[str, float, str, int, int]] = {}
        for i, name in enumerate(names):
            stop = names[i + 1].start() if i + 1 < len(names) else len(text)
            segment = text[name.end() : min(stop, name.end() + 120)]
            money = _money_search(segment)
            population = population_named(name.group(0))
            parsed = parse_money(segment[money.start() :]) if money else None
            if money is None or parsed is None or population is None:
                continue
            amount, currency = parsed
            if amount < TUITION_FLOOR_AMOUNT:
                continue
            row = (population, amount, currency, name.start(), name.end() + money.end())
            if population not in rows or (
                want is not None and _year_key(segment[: money.start()]) == want
            ):
                rows[population] = row
        if len(rows) >= 2:
            return list(rows.values())
    return []


#: FE-2 (``--fee-readers-v2``, core-gap analysis 2026-10-18 change 4): the fee
#: words UK and Irish pages use for a fee status. Imperial's programme page
#: prints "Home fee 2027 entry £10,050 per year … Overseas fee 2027 entry
#: £47,800 per year", and neither "Home" nor "Overseas" was a population name,
#: so the page yielded no tuition at all. Off until a paired run shows no new
#: wrong claim.
FEE_READERS_V2 = False

_FEE_STATUS_LABEL = re.compile(
    r"(?<![\w/-])(overseas|international|non[-\s]?EU(?:\s*/\s*EEA)?|home)"
    r"\s+(?:tuition\s+)?(?:fees?|students?|rate)(?![\w/-])",
    re.IGNORECASE,
)
#: Between a fee-status label and its amount only the year it is for may
#: stand: "Overseas fee 2027 entry £47,800", "International fee 2027/28: £X".
_FEE_STATUS_GAP = re.compile(
    r"\s*[:\-–]?\s*(?:(?:for\s+)?(?P<entry>20\d{2})\s+entry"
    r"|(?P<year>20\d{2}\s*[-/–]\s*(?:20)?\d{2}))?\s*[:\-–]?\s*",
    re.IGNORECASE,
)
#: The amount must say it is a year's fee; a module, credit or term price is
#: not the tuition the cost question asks about.
_ANNUAL_AFTER_MONEY = re.compile(
    r"\s*(?:per\s+(?:academic\s+)?year|per\s+annum|a\s+year|/\s*(?:year|yr|annum)"
    r"|annually|p\.\s?a\.)",
    re.IGNORECASE,
)


def fee_status_population(label: str) -> str | None:
    """The population a fee-status word names: Overseas and International are
    the international fee, Home the domestic one, non-EU the non-EU/EEA one
    (the scope reader's own name for it). Anything else names none."""
    word = label.strip().split()[0].casefold() if label.strip() else ""
    if word in {"overseas", "international"}:
        return "international"
    if word == "home":
        return "domestic"
    if re.match(r"non[-\s]?eu", label.strip(), re.IGNORECASE):
        return "non-EU/EEA"
    return None


def _entry_year(entry: str) -> str:
    """ "2027 entry" is the academic year that starts in 2027."""
    return f"{entry}/{(int(entry) + 1) % 100:02d}"


def _fee_page_for_request(builder: ClaimBuilder) -> bool:
    """FE-2: whether this page states fees for the programme or level asked for.

    The page's own title must name the requested programme (Imperial's
    "Computing BEng | Study" for computer science), or the page must read as
    the requested degree level and name no programme. A fee status row on any
    other page is some other course's fee.
    """
    from app.adapters.search.ontology import titles_name_same_programme
    from app.domain.programme_identity import Verdict

    title = str(builder.meta.get("page_title") or "")
    requested = builder.requested_programmes or tuple(
        p for p in (builder.meta.get("program"),) if isinstance(p, str) and p
    )
    if title and any(titles_name_same_programme(title, p) is Verdict.YES for p in requested):
        return True
    scope = builder.meta.get("scope")
    return bool(
        builder.requested_degree
        and isinstance(scope, ClaimScope)
        and scope.degree == builder.requested_degree
        and scope.programme is None
    )


def _fee_status_rows(
    text: str, academic_year: str | None
) -> list[tuple[str, float, str, str | None, int, int]]:
    """``(population, amount, currency, academic_year, start, end)`` per fee status.

    A row is a fee-status label, at most the year it is for, an amount and a
    per-year marker, nothing else in between. A population is claimed only
    when every row the page prints for it (for the requested year, when the
    row names one) states the same amount: two different "Overseas fee"
    amounts on one page are two courses, and the reader cannot tell which.
    """
    want = _year_key(academic_year or "")
    labels = list(_FEE_STATUS_LABEL.finditer(text))
    found: dict[str, list[tuple[float, str, str | None, int, int]]] = {}
    for i, label in enumerate(labels):
        stop = labels[i + 1].start() if i + 1 < len(labels) else len(text)
        segment = text[label.end() : min(stop, label.end() + 80)]
        money = _money_search(segment)
        if money is None:
            continue
        gap = _FEE_STATUS_GAP.fullmatch(segment[: money.start()])
        parsed = parse_money(segment[money.start() :])
        annual = _ANNUAL_AFTER_MONEY.match(segment, money.end())
        population = fee_status_population(label.group(1))
        if gap is None or parsed is None or annual is None or population is None:
            continue
        amount, currency = parsed
        if amount < TUITION_FLOOR_AMOUNT:
            continue
        year = (
            _entry_year(gap.group("entry"))
            if gap.group("entry")
            else _year_key(gap.group("year") or "")
        )
        if want is not None and year is not None and year != want:
            continue
        found.setdefault(population, []).append(
            (amount, currency, year, label.start(), label.end() + annual.end())
        )
    rows = []
    for population, matches in found.items():
        if len({(amount, currency) for amount, currency, *_ in matches}) != 1:
            continue
        amount, currency, year, start, end = matches[0]
        rows.append((population, amount, currency, year, start, end))
    return rows


#: Plan rule DF-1: a fee table whose columns are academic years and whose rows
#: are named tariffs (TU Delft, 2026-10-06: "2026/2027 2027/2028 Institutional
#: rate BSc € 19.906 MSc € 25.633 BSc € 20.563 MSc € 26.479"). Only the tariff
#: names below are read, each to the population the institution's own page
#: defines it for; any other row name is left alone. The column must be the
#: year asked for; no year, no claim. On by default since 2026-10-06 (owner:
#: "да"; run claude-df1-paired-2: Delft tuition a stable gain, zero losses).
FEE_YEAR_COLUMNS = True
_TARIFF_POPULATION = {
    "statutory rate": "EU/EEA",
    "institutional rate": "non-EU/EEA",
}
_YEAR_HEADER = re.compile(r"((?:20\d{2}\s*/\s*20\d{2}\s+){2,})")
_TARIFF_CELL = re.compile(
    r"(?:BSc\s*(?P<bsc>€\s*\d{1,3}(?:[.,]\d{3})+)\s*MSc\s*€\s*\d{1,3}(?:[.,]\d{3})+"
    r"|(?P<single>€\s*\d{1,3}(?:[.,]\d{3})+))\s*"
)


def _euro_amount(raw: str) -> float:
    digits = re.sub(r"[^\d.,]", "", raw)
    return float(re.sub(r"[.,]", "", digits))


def _year_column_fees(
    text: str, want: str | None
) -> list[tuple[str, float, str | None, str, int, int]]:
    """``(population, amount, degree, year, start, end)`` per tariff row."""
    if not want:
        return []
    rows = []
    for header in _YEAR_HEADER.finditer(text):
        years = [_year_key(y) for y in re.findall(r"20\d{2}\s*/\s*20\d{2}", header.group(1))]
        if want not in years:
            continue
        column = years.index(want)
        rest = text[header.end() :]
        label = re.match(r"(statutory rate|institutional rate)\s*", rest, re.I)
        if label is None:
            continue
        position = label.end()
        cells = []
        for _ in years:
            cell = _TARIFF_CELL.match(rest, position)
            if cell is None:
                break
            cells.append(cell)
            position = cell.end()
        if len(cells) != len(years):
            continue
        cell = cells[column]
        raw = cell.group("bsc") or cell.group("single")
        rows.append(
            (
                _TARIFF_POPULATION[label.group(1).lower()],
                _euro_amount(raw),
                "bachelor" if cell.group("bsc") else None,
                want,
                header.start(),
                header.end() + position,
            )
        )
    return rows


def extract_costs(text: str, builder: ClaimBuilder) -> list[Claim]:
    """Pull cost figures out of a fees page."""
    found: list[Claim] = []
    lined = text
    text = for_matching(text)
    # DL-5 (d): on a page with per-intake sections, the requested intake's only.
    sectioned = (
        INTAKE_SECTION_DEADLINE and _intake_section(lined, builder.meta.get("intake")) is not None
    )
    if sectioned:
        text = _deadline_scope(text, lined, builder)
    if FEE_YEAR_COLUMNS:
        want = _year_key(
            cast("str", builder.requested_academic_year or builder.meta.get("academic_year") or "")
        )
        for population, amount, degree, year, start, end in _year_column_fees(text, want):
            _keep(
                found,
                builder.add(
                    ClaimType.TUITION,
                    {"amount": amount, "currency": "EUR"},
                    excerpt_around(text, start, end),
                    section="Fees and costs",
                    subject_key=population,
                    population=population,
                    degree=degree,
                    academic_year=year,
                ),
            )
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
        if ctype is ClaimType.TUITION:
            rows = _population_amounts(
                text,
                label,
                cast(
                    "str | None",
                    (TUITION_ROW_YEAR and builder.requested_academic_year)
                    or builder.meta.get("academic_year"),
                ),
            )
            for population, amount, currency, start, end in rows:
                _keep(
                    found,
                    builder.add(
                        ctype,
                        {"amount": amount, "currency": currency},
                        excerpt_around(text, start, end),
                        section="Fees and costs",
                        subject_key=population,
                        population=population,
                        academic_year=_year_key(text[start:end]) if TUITION_ROW_YEAR else None,
                    ),
                )
            if rows:
                continue
            if FEE_READERS_V2 and _fee_page_for_request(builder):
                status_rows = _fee_status_rows(
                    text,
                    cast(
                        "str | None",
                        builder.requested_academic_year or builder.meta.get("academic_year"),
                    ),
                )
                for population, amount, currency, row_year, start, end in status_rows:
                    _keep(
                        found,
                        builder.add(
                            ctype,
                            {"amount": amount, "currency": currency},
                            excerpt_around(text, start, end),
                            section="Fees and costs",
                            subject_key=population,
                            population=population,
                            academic_year=row_year,
                        ),
                    )
                if status_rows:
                    continue
        m = (
            _section_tuition(text, label)
            if sectioned and ctype is ClaimType.TUITION
            else re.search(rf"{label}[^.\n]{{0,120}}", text, re.IGNORECASE)
        )
        if not m:
            continue
        parsed = parse_money(m.group(0))
        if parsed is None:
            continue
        amount, currency = parsed
        if ctype in _FLOOR_AT_TUITION and amount < TUITION_FLOOR_AMOUNT:
            continue
        _keep(
            found,
            builder.add(
                ctype,
                {"amount": amount, "currency": currency},
                excerpt_around(text, m.start(), m.end()),
                section="Fees and costs",
                notes=_WHOLE_PROGRAMME_NOTE
                if sectioned and ctype is ClaimType.TUITION and _whole_programme_fee(text, m)
                else "",
            ),
        )
    return found


#: DL-5 (d): a fee label's window that names a part of the fee, not the fee.
_FEE_PART = re.compile(r"\b(?:instal+ments?|deposit|application\s+fee|per\s+semester)\b", re.I)
_WHOLE_PROGRAMME_NOTE = (
    "DL-5: the page labels this the total tuition fee in the requested intake's "
    "section, for the whole programme; it is not stated per year"
)


def _section_tuition(text: str, label: str) -> re.Match[str] | None:
    """DL-5 (d): the first tuition label in an intake's section that an amount
    for the fee itself follows. A sentence that only says a fee exists
    ("required to pay application and tuition fees.") and the label of one
    instalment ("First tuition fee instalment: SEK 75,000") are passed over.
    """
    window = re.compile(rf"{label}[^.\n]{{0,120}}", re.IGNORECASE)
    for at in re.finditer(label, text, re.IGNORECASE):
        m = window.match(text, at.start())
        if m is None:
            continue
        money = _money_search(m.group(0))
        if money is None or _FEE_PART.search(m.group(0), 0, money.start()):
            continue
        if _FEE_PART.search(text, max(0, m.start() - 24), m.start()):
            continue
        return m
    return None


def _whole_programme_fee(text: str, m: re.Match[str]) -> bool:
    """DL-5 (d): the label says the amount is the programme's total fee."""
    return re.search(r"\btotal\b", text[max(0, m.start() - 24) : m.start()], re.I) is not None


#: A faculty named the way universities name them; anything else under a
#: "Faculty" label (a person, a staff list) is not the programme's faculty.
_FACULTY_VALUE = re.compile(
    r"^(?:the\s+)?(?:School|Faculty|College|Department|Division|Institute)\s+of\s+\S.{0,78}$", re.I
)
_FACULTY_LABEL = re.compile(r"^(?:faculty|school|offering\s+(?:faculty|school))\s*:?\s*(.*)$", re.I)


def extract_programme_faculty(text: str, builder: ClaimBuilder) -> Claim | None:
    """See :func:`_read_faculty`; the claim names the programme the page confirmed.

    A faculty belongs to the programme whose existence the same page confirmed,
    not to the name the pipeline searched for: run 36460381447 recorded HKU's
    faculty against "Computing And Data Science", master, and scored it wrong.
    """
    confirmed = next(
        (
            c.normalized_value
            for c in reversed(builder.claims)
            if c.claim_type is ClaimType.PROGRAM_EXISTS and isinstance(c.normalized_value, dict)
        ),
        None,
    )
    if confirmed is None:
        return None
    title, level = confirmed.get("program"), confirmed.get("degree")
    saved = builder.meta.get("program")
    if title:
        builder.meta["program"] = title
    try:
        return _read_faculty(
            text, builder, degree=str(level) if level else None, programme=title or None
        )
    finally:
        builder.meta["program"] = saved


def _read_faculty(
    text: str, builder: ClaimBuilder, *, degree: str | None, programme: str | None = None
) -> Claim | None:
    """The faculty a programme page states in a labelled field ("FACULTY" / value).

    Only a label on its own line (or "Faculty: X") counts, and only when the
    page states exactly one such value: a listing that names several faculties
    says nothing about which one teaches the requested programme.
    """
    lines = [line.strip() for line in text.splitlines()]
    values: list[str] = []
    for i, line in enumerate(lines):
        label = _FACULTY_LABEL.match(line)
        if label is None:
            continue
        value = label.group(1).strip()
        if not value:
            value = next((nxt for nxt in lines[i + 1 : i + 3] if nxt), "")
        if _FACULTY_VALUE.match(value) and value not in values:
            values.append(value)
    if len(values) != 1:
        return None
    return builder.add(
        ClaimType.PROGRAM_FACULTY,
        values[0],
        values[0],
        confidence=0.8,
        degree=degree,
        programme=programme,
    )


# --- plan rule FS-1: which faculty a page speaks for ---------------------------

#: "Faculty of X" / "School of X" / "College of X" as a page names its unit;
#: case-sensitive on purpose, so prose ("the faculty of a university") is not one.
_UNIT_NAME = re.compile(
    r"\b(?:Faculty|School|College)\s+of\s+(?:the\s+)?"
    r"([A-Z][\w'’-]*(?:,?\s+(?:and|&|of|for|the|[A-Z][\w'’-]*))*)"
)
#: A labelled value without its "Faculty of" ("Faculty" / "Science and Engineering").
_BARE_UNIT = re.compile(r"^[A-Z][\w'’-]*(?:,?\s+(?:and|&|of|for|the|[A-Z][\w'’-]*)){0,7}$")
_UNIT_HEADING = re.compile(r"^(?:the\s+)?(?:Faculty|School|College)\s+of\s+\S.{0,78}$")
_UNIT_TRAILING = frozenset({"and", "of", "for", "the"})


def faculty_key(name: str) -> str | None:
    """A faculty name reduced for comparison: "Faculty of Economics & Business" → "economics and business"."""
    m = _UNIT_NAME.search(name)
    core = m.group(1) if m else name
    core = re.split(r"\s+Universit", core)[0]
    words = core.replace("&", " and ").lower().split()
    while words and words[-1] in _UNIT_TRAILING:
        words.pop()
    return " ".join(words) or None


def _attr_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value or "")


def page_faculty(html: str) -> str | None:
    """The one faculty a page's breadcrumb, title and H1 name, as a :func:`faculty_key`.

    None when they name none, or more than one: a page whose navigation names
    two units says nothing about which one it speaks for.
    """
    soup = parse_html(html)
    parts: list[str] = []
    for el in soup.find_all(True):
        marks = " ".join(
            _attr_text(el.get(attr)) for attr in ("class", "id", "itemprop", "aria-label")
        )
        if "breadcrumb" in marks.lower():
            # "|" keeps one crumb's name from running into the next one's.
            parts.append(el.get_text("|", strip=True))
    if soup.title and soup.title.string:
        parts.append(str(soup.title.string))
    parts.extend(h.get_text(" ", strip=True) for h in soup.find_all("h1"))
    keys = {
        k for part in parts for m in _UNIT_NAME.finditer(part) if (k := faculty_key(m.group(0)))
    }
    return next(iter(keys)) if len(keys) == 1 else None


def programme_faculty(text: str, html: str) -> str | None:
    """The faculty a programme page names, as a :func:`faculty_key`, or None.

    A labelled field first ("Faculty" / "Faculty of X", the field
    :func:`_read_faculty` reads). A bare value ("Faculty" / "Science and
    Engineering", Groningen) counts only when the page also names "Faculty of
    <value>" elsewhere, so a staff name under a "Faculty" heading never does.
    Then the page's own breadcrumb, title and H1.
    """
    flat = " ".join(text.split())
    lines = [line.strip() for line in text.splitlines()]
    values: set[str] = set()
    for i, line in enumerate(lines):
        label = _FACULTY_LABEL.match(line)
        if label is None:
            continue
        value = label.group(1).strip()
        if not value:
            value = next((nxt for nxt in lines[i + 1 : i + 3] if nxt), "")
        if _UNIT_HEADING.match(value) or (
            _BARE_UNIT.match(value)
            and re.search(rf"\b(?:Faculty|School|College)\s+of\s+{re.escape(value)}\b", flat)
        ):
            key = faculty_key(value)
            if key:
                values.add(key)
    if values:
        return next(iter(values)) if len(values) == 1 else None
    return page_faculty(html) if html else None


def faculty_blocks(text: str) -> list[tuple[str, str]]:
    """A page's per-faculty sections, as (faculty key, section text), or [].

    A section starts at a line that is only a faculty's name and runs to the
    next such line. Fewer than two distinct faculties is not a per-faculty
    page, and [] is returned. Each section text is a slice of ``text``.
    """
    starts: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if _UNIT_HEADING.match(stripped):
            key = faculty_key(stripped)
            if key:
                starts.append((offset, key))
        offset += len(line)
    if len({key for _, key in starts}) < 2:
        return []
    ends = [start for start, _ in starts[1:]] + [len(text)]
    return [(key, text[start:end]) for (start, key), end in zip(starts, ends, strict=True)]
