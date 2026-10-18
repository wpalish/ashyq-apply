"""Admission requirements from official pages.

Two guards separate this from the version that produced live false positives:

* the page is classified first, and each extractor runs only on page classes
  that could actually answer its question;
* a positive claim needs positive evidence. The absence of "applications are
  closed" is not evidence that an intake is open.

URL-scheme agnostic on purpose: the same adapter reads a bundled ``fixture://``
page and a live university page, so demo mode rehearses the real path.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from urllib.parse import urlparse

from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.discovery.live_discovery import (
    degree_level_named,
    matches_field_text,
    names_other_degree_level,
)
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import (
    ClaimBuilder,
    excerpt_around,
    extract_admission_route,
    extract_costs,
    extract_programme_faculty,
    extract_requirements,
    faculty_blocks,
    for_matching,
    html_title,
    is_official_domain,
    page_faculty,
    pdf_to_text,
    programme_faculty,
    readable_text,
    verification_domains,
)
from app.adapters.fetching import Fetcher, same_source_site
from app.adapters.matching import degree_matches, program_matches
from app.adapters.page_classifier import (
    PageType,
    classify_page,
    degree_level_of,
    full_degree_titles,
)
from app.adapters.scope_reader import read_scope
from app.adapters.search.ontology import titles_name_same_programme
from app.adapters.structured_extraction import extract_table_requirements
from app.domain.claim_scope import ClaimScope
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import ClaimType, FetchOutcome, SourceSpecificity
from app.domain.programme_identity import Verdict
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim

#: An intake is open only when a page says so. Each pattern must capture the
#: sentence it matched, which becomes the claim's excerpt.
_INTAKE_OPEN_EVIDENCE: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "application window",
        re.compile(
            r"[^.]*\bapplications?\b[^.]{0,80}\b(?:open|opens|opened|will open)\b[^.]{0,80}\.", re.I
        ),
    ),
    (
        "currently accepting",
        re.compile(
            r"[^.]*\b(?:now accepting|currently accepting|accepting applications|applications are open)\b[^.]{0,80}\.",
            re.I,
        ),
    ),
    (
        "apply now for cycle",
        re.compile(r"[^.]*\bapply (?:now|online|here)\b[^.]{0,80}\b(20\d{2})\b[^.]{0,60}\.", re.I),
    ),
)
_INTAKE_CLOSED_EVIDENCE = re.compile(
    r"[^.]*\b(?:applications? (?:are |is )?closed|no longer accepting|admissions? (?:are |is )?closed"
    r"|intake (?:is )?closed|not accepting applications)\b[^.]{0,80}\.",
    re.I,
)
#: A sentence that settles whether the English test can be skipped. Broad on
#: purpose about *how* it is phrased and narrow about *what* it is about: the
#: `_MENTIONS_ENGLISH` check below is what keeps a fee waiver out.
_ENGLISH_WAIVER = re.compile(
    r"[^.]*\b(exempt(?:ed|ions?)?|waive(?:d|s|r|rs)?|not required to (?:submit|provide|take)"
    r"|do(?:es)? not need to (?:submit|provide|take))\b[^.]*\.",
    re.IGNORECASE,
)
#: The denial, which must be its own pattern. Reusing the fee-waiver negation
#: read "you do not need to submit IELTS if..." — a waiver in plain words — as
#: a refusal of one, which is the most expensive way to be wrong here.
_NO_ENGLISH_WAIVER = re.compile(
    r"\bno\s+(?:waivers?|exemptions?)\b"
    r"|\b(?:waivers?|exemptions?)\s+(?:are|is)\s+not\s+(?:granted|available|possible|offered)"
    r"|\bcannot\s+be\s+waived\b"
    r"|\bis\s+required\s+of\s+all\s+applicants\b",
    re.IGNORECASE,
)
_MENTIONS_ENGLISH = re.compile(
    r"\b(english|ielts|toefl|duolingo|pte|language (?:test|requirement|proficiency))\b",
    re.IGNORECASE,
)


#: A "fee waiver" line only yields a claim when the page actually settles the
#: question. Negation is positive evidence of absence and is claimed as False;
#: a line that merely mentions waivers settles nothing — unknown stays
#: unknown, never a confident True.
_WAIVER_NEGATION = re.compile(
    r"\b(no|not|never|neither|nor|without|cannot|can'?t|won'?t|isn'?t|aren'?t"
    r"|doesn'?t|don'?t|unavailable)\b",
    re.IGNORECASE,
)
_WAIVER_OFFERED = re.compile(r"\b(available|offered|granted|waive[ds]?|waiving)\b", re.IGNORECASE)


#: Experiment ER-08 (expert trace 2026-10-04), on since the 10-case paired run
#: 37279746829 (owner approved 2026-10-05); False turns it off.
#: After a programme page is known, one public query per topic finds the
#: official page that publishes it. Groningen, NTU and HKU each answered the
#: English, fee and deadline questions on pages this adapter never opened,
#: and each was the top same-institution result of one query.
TOPIC_SEARCH = True
#: Topic name to the public query; only the institution name is filled in.
#: Plan rule TS-2: a failed topic query no longer ends topic search for the
#: institution; the next topic is still asked (NTU, run claude-sr1-paired-1:
#: two of four repetitions lost all three topics to one failed query).
TOPIC_SEARCH_CONTINUE = False
#: Plan rule FS-1: a page reached by topic search, or by a lead from one, is a
#: university-level source and may speak for another faculty (Groningen,
#: QB-1 run: the Faculty of Economics and Business "Apply for a Bachelor" page
#: gave IELTS 6.0 to Computing Science, a Faculty of Science and Engineering
#: programme at 6.5). When the page's breadcrumb, title or H1 names a faculty
#: and the programme page named another, the page yields no requirement
#: claims; on a page with one section per faculty, IELTS is read only from the
#: section that names the programme or its faculty. Unknown faculty → as before.
#: On with QB-1 since the same paired runs (no wrong claim from another
#: faculty's page in any arm); owner delegation 2026-10-17. False turns it off.
TOPIC_FACULTY_SCOPE = True
#: Plan rule FS-2, on since paired runs 39096181406 / 39096182669 / 39096183785
#: (narrowed form: removes UM's Linguistics IELTS 6.0 / TOEFL 78 that the
#: defaults claimed, warsaw programme labels a stable gain, 0 losses; owner
#: delegation 2026-10-17; False turns it off): a page reached by topic
#: search, or by a lead from one, that is another programme's own page yields
#: no requirement claims. UM, dev3 runs of 2026-10-18: the English-requirements
#: query returned the "Bachelor of English Language and Linguistics" page, and
#: its conditional-admission IELTS 6 was claimed for Computer Science (5.5).
#: The benchmark harness flips it per capture (``--topic-programme-scope``).
#: Narrowed after the fs2 runs: the classifier calls university pages such as
#: Auckland's "Undergraduate English language requirements", Delft's "Admission
#: Requirements" / "BSc International" and Imperial's "Deadlines" programme
#: pages, so the cut fires only when the subject is a degree title of another
#: field with no requirement-topic word (``_names_another_programme``).
TOPIC_PROGRAMME_SCOPE = True
#: Claim types FS-1 reads from one faculty's section of a per-faculty page.
_FACULTY_SCOPED_CLAIMS = frozenset({ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE})
_DEGREE_PREFIX = re.compile(
    r"^(?:b\.?sc\.?|b\.?a\.?|b\.?eng\.?|bachelor(?:'s)?(?:\s+of\s+\w+)?(?:\s+in)?)\s+", re.I
)
_TRAILING_NOTE = re.compile(r"\s*\([^)]*\)\s*$")
#: FS-2: words that make a "programme" subject a requirements topic page.
_REQUIREMENT_TOPIC = re.compile(
    r"\b(?:requirements?|prerequisites?|deadlines?|dates?|fees?|tuition|finances?|"
    r"admissions?|entry|applications?|apply|international|scholarships?|"
    r"english\s+(?:language\s+)?(?:requirements?|proficiency|tests?))\b",
    re.I,
)


def _names_another_programme(subject: str, field: str) -> bool:
    """FS-2: the subject is a degree title ("Bachelor of English Language and
    Linguistics") of a field other than ``field``, not a requirements topic."""
    return (
        _DEGREE_PREFIX.match(subject) is not None
        and not matches_field_text(subject, [field])
        and _REQUIREMENT_TOPIC.search(subject) is None
    )


def _programme_line_key(line: str) -> str:
    """A list line or programme name reduced for comparison ("BSc Computing Science")."""
    line = _TRAILING_NOTE.sub("", " ".join(line.split()))
    return _DEGREE_PREFIX.sub("", line).lower()


def _faculty_section(text: str, programme: str, faculty: str | None) -> tuple[bool, list[str]]:
    """FS-1: (is a per-faculty page, the sections that name the programme or its faculty).

    Sections that list the programme by name win over sections headed by its
    faculty; a page that is not per-faculty gives (False, []).
    """
    blocks = faculty_blocks(text)
    if not blocks:
        return False, []
    wanted = _programme_line_key(programme)
    naming = [
        block
        for _, block in blocks
        if wanted and any(_programme_line_key(line) == wanted for line in block.splitlines())
    ]
    if naming:
        return True, naming
    return True, [block for key, block in blocks if faculty and key == faculty]


_TOPIC_QUERIES = (
    ("english", "{name} undergraduate English language requirements international applicants"),
    ("fees", "{name} undergraduate tuition fees international students"),
    ("deadline", "{name} undergraduate application deadline international students"),
)


@dataclass(frozen=True)
class _Target:
    url: str
    specificity: SourceSpecificity
    #: Reached by following an English-requirement link from an official page.
    language_follow: bool = False
    #: Found by experiment ER-08 for this topic.
    topic: str | None = None
    #: Reached by following a route or deadline link (plan rule RL-1).
    route_follow: bool = False
    #: Reached by following a fee link from any official page (plan rule HL-1).
    fee_follow: bool = False
    #: FS-1: a lead from a page reached by topic search.
    from_topic: bool = False
    #: QR-1: the question ("english" or "deadline") this page was reached for.
    question: str | None = None
    #: QR-1: a page whose official links are scanned for the questions
    #: (programme, admissions and, without a programme page, home page).
    link_source: bool = False
    #: QR-1: read for its links only; nothing on it is claimed (home page).
    links_only: bool = False
    #: QR-1b: reached by a question, language or route link on the confirmed
    #: programme page; a page silent on its degree takes the programme's.
    #: QR-1c: also on the admissions page read beside a confirmed programme
    #: page, when the admissions page is silent on its degree or states the
    #: programme's.
    via_programme: bool = False
    #: QR-1c: the admissions page the link was on, when it was not the
    #: programme page (for the scope note).
    via_admissions: str | None = None


#: Language-requirement pages followed per programme, beyond the two targets.
_MAX_LANGUAGE_FOLLOWS = 2
_LANGUAGE_LINK = re.compile(
    r"english[\s-]+(language|proficiency|competency|requirement)|language[\s-]+"
    r"(requirement|proficiency|competency|admission)|\bielts\b",
    re.I,
)


def _language_links(
    html: str,
    base: str,
    domain: str | None,
    extra_domains: Sequence[str] = (),
    *,
    degree: object = None,
) -> list[str]:
    """Official links on a page whose text or URL names an English requirement.

    ``extra_domains`` are the candidate's DI-1 admissions domains. With
    ``degree`` (HL-1), a link naming another degree level is dropped.
    """
    if not domain:
        return []
    out: list[str] = []
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        if not url.startswith(("https://", "http://", "fixture://")):
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain, *extra_domains])):
            continue
        if degree is not None and _names_other_level(" ".join(link.text.split()), url, degree):
            continue
        named = _LANGUAGE_LINK.search(link.text) or _LANGUAGE_LINK.search(url.replace("/", " "))
        if named and url not in out and url.rstrip("/") != base.rstrip("/"):
            out.append(url)
    return out


#: Plan rule RL-1 (control run claude-control-twopass-1, 2026-10-06): the
#: deadline and the English minimum often sit two or three official links below
#: the admissions hub the adapter reads (Delft: hub -> "BSc - International
#: diploma" -> "Admission Requirements" / "Dates & Deadlines"; UBC: hub ->
#: "Dates and deadlines"). On since paired run 37545452839 (2 stable gains,
#: 0 losses; owner delegation 2026-10-06). False turns it off.
ROUTE_LEADS = True
#: Route and deadline pages followed per programme, beyond every other target.
_MAX_ROUTE_FOLLOWS = 4
_DEADLINE_LEAD = re.compile(
    r"\bdates?\s*(?:&|and)\s*deadlines?\b|\bapplication\s+deadlines?\b|\bkey\s+dates\b", re.I
)
#: The undergraduate route for an applicant with a foreign school diploma.
_ROUTE_LEAD = re.compile(
    r"\binternational\s+(?:diploma|high\s+schools?|secondary|qualifications?)\b"
    r"|\bnon[\s-]dutch\b|\bforeign\s+(?:diploma|qualifications?)\b",
    re.I,
)
#: A bare "Admission requirements" link, followed only from a page that is
#: already on the international route, so a domestic route is never read.
_REQUIREMENTS_LEAD = re.compile(r"^\s*(?:admission|entry)\s+requirements\s*$", re.I)
_ON_ROUTE = re.compile(r"international|non-dutch|foreign", re.I)
_GRADUATE_LEAD = re.compile(r"\b(?:msc|master'?s?|phd|doctoral|postgraduate|graduate)\b", re.I)


def _route_links(
    html: str,
    base: str,
    domain: str | None,
    extra_domains: Sequence[str] = (),
    *,
    deadline: bool,
    requirements: bool,
) -> list[tuple[str, bool]]:
    """Same-site links to the deadline or the foreign-diploma route (RL-1).

    Each item is ``(url, is_requirements_page)``. Link text decides; a link
    that names a graduate route is never followed.
    """
    if not domain:
        return []
    on_route = bool(_ON_ROUTE.search(base))
    out: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        text = " ".join(link.text.split())
        if not url.startswith(("https://", "http://", "fixture://")) or url in seen:
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain, *extra_domains])):
            continue
        if url.rstrip("/") == base.rstrip("/") or _GRADUATE_LEAD.search(text):
            continue
        if (deadline and _DEADLINE_LEAD.search(text)) or (
            requirements and _ROUTE_LEAD.search(text)
        ):
            out.append((url, False))
        elif requirements and on_route and _REQUIREMENTS_LEAD.search(text):
            out.append((url, True))
        else:
            continue
        seen.add(url)
    return out


#: Plan rule HL-1 (evidence analysis 2026-10-17, §0 cause 3, §4 rank 2):
#: leads were followed only from pages the classifier accepted, so a
#: programme page it rejected (TCD's course page reads as a catalogue) or an
#: admissions hub (UCT's international-applicants page reads as unknown) never
#: had its "English language requirements", route, fee or scholarship links
#: followed, though both carry the exact link an expert used. With HL-1 on,
#: every official HTML page read here, accepted or rejected, is scanned for
#: language, route and deadline links (``_language_links``, ``_route_links``)
#: and for fee and scholarship links (``_service_links``), under the same
#: follow caps; no lead whose text or URL names another degree level than the
#: request is followed. A fee link becomes ``candidate.costs_url`` and a
#: scholarship link ``candidate.scholarships_url`` when discovery left them
#: None, so the cost and funding adapters read them; a fee link on a candidate
#: that already has a cost page is read here as a fee page. A rejected page's
#: own text is still never claimed from. Off by default; the benchmark harness
#: flips it per capture (``--hub-leads``).
HUB_LEADS = False
_FEES_LEAD = re.compile(r"\b(?:tuition|fees?)\b", re.I)
_FEES_LEAD_PATH = re.compile(r"(?:^|[/_-])(?:fees?|tuition)(?:[/_.-]|$)", re.I)
#: An application fee or a fee waiver is not what a year of study costs.
_NOT_FEES_LEAD = re.compile(r"\bapplication[\s_-]+fees?\b|\bwaivers?\b", re.I)
_SCHOLARSHIP_LEAD = re.compile(
    r"\bscholarships?\b|\bfinancial[\s-]+(?:aid|support)\b|\bbursar(?:y|ies)\b|\bfunding\b",
    re.I,
)
_SCHOLARSHIP_LEAD_PATH = re.compile(
    r"(?:^|[/_-])(?:scholarships?|financial[_-]aid|funding|bursar(?:y|ies))(?:[/_.-]|$)", re.I
)
#: Link text that names a level other than the requested one (HL-1 guard).
_OTHER_LEVEL_TEXT: dict[str, re.Pattern[str]] = {
    "bachelor": _GRADUATE_LEAD,
    "master": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|phd|doctoral|doctorate)\b", re.I),
    "phd": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|msc|master'?s?)\b", re.I),
}


def _level_scope(degree: object) -> bool:
    """SL-1 (``web_scholarships.SCHOLARSHIP_LEVEL_SCOPE``): route links get a URL level guard."""
    from app.adapters.scholarship import web_scholarships

    return web_scholarships.SCHOLARSHIP_LEVEL_SCOPE and degree is not None


def _names_other_level(text: str, url: str, degree: object) -> bool:
    """HL-1: whether a lead's text or URL names a level the applicant did not ask for."""
    if not degree:
        return False
    level = str(degree)
    pattern = _OTHER_LEVEL_TEXT.get(level)
    return bool(pattern and pattern.search(text)) or names_other_degree_level(url, level)


def _service_links(
    html: str, base: str, domain: str | None, degree: object, extra_domains: Sequence[str] = ()
) -> tuple[list[str], list[str]]:
    """HL-1: official ``(fee, scholarship)`` links on a page.

    Link text or URL path decides; a link naming another degree level is
    dropped, and one naming the requested level comes before a neutral one.
    """
    if not domain:
        return [], []
    level = str(degree) if degree else None
    fees: list[tuple[bool, str]] = []
    awards: list[tuple[bool, str]] = []
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        text = " ".join(link.text.split())
        if not url.startswith(("https://", "http://", "fixture://")):
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain, *extra_domains])):
            continue
        if url.rstrip("/") == base.rstrip("/") or _names_other_level(text, url, degree):
            continue
        path = url[len("fixture://") :] if url.startswith("fixture://") else urlparse(url).path
        own_level = level is not None and degree_level_named(url) == level
        if (_FEES_LEAD.search(text) or _FEES_LEAD_PATH.search(path)) and not (
            _NOT_FEES_LEAD.search(text) or _NOT_FEES_LEAD.search(path)
        ):
            if url not in {u for _, u in fees}:
                fees.append((own_level, url))
        elif (
            _SCHOLARSHIP_LEAD.search(text) or _SCHOLARSHIP_LEAD_PATH.search(path)
        ) and url not in {u for _, u in awards}:
            awards.append((own_level, url))

    def ordered(items: list[tuple[bool, str]]) -> list[str]:
        return [u for own, u in items if own] + [u for own, u in items if not own]

    return ordered(fees), ordered(awards)


#: Plan rule QR-1 (structural analysis 2026-10-18, §2 F1/F2, §3 change 2),
#: off until a paired run passes. The evidence stage routed a page by the type
#: the classifier gave it, not by the question it was fetched for: every fee
#: page the fees query returned (12 of 16 cases) was rejected "classified as
#: costs", and TCD's and UCT's English pages were fetched and rejected as
#: ``unknown``; the programme page's own "Fees", "Selection procedure" and
#: "English language requirements" links were not followed unless their text
#: matched RL-1's two patterns. On:
#:
#: * targets per question, in order: (a) official links on the programme page
#:   and the admissions page (and, with no programme page, the home page)
#:   whose text or URL names English/language requirements, fees/tuition, or
#:   deadlines/dates/selection procedure/how to apply, under the URL and
#:   link-text degree-level guards, at most ``_MAX_QUESTION_LINKS`` each;
#:   (b) after those are read, one topic query per question still unanswered
#:   among english, fees and deadline, within the shared query budget;
#: * a page reached for English is read by the table and prose English
#:   readers, and one reached for the deadline by the deadline reader,
#:   whatever the classifier calls it (the ``language_follow`` exemption,
#:   generalised); only that question's claim types are kept from such a page;
#: * a page reached for fees is not read here: it is recorded in
#:   ``candidate.question_fee_urls`` and read by ``WebCostAdapter`` with the
#:   structured fee reader (TY-1 year selection) after ``costs_url``;
#: * a claim whose read scope names another degree level than the request is
#:   withheld (UCPH: IELTS from the master's language page for a bachelor);
#: * all of this runs when no programme page is confirmed, from the
#:   admissions and home pages, at university-admissions specificity.
#: * QR-1b (wrong-claims analysis 2026-10-18, R-A): a page reached by a
#:   question, language or route link on the confirmed programme page, and
#:   silent on its degree, is read in the programme's degree (and name) —
#:   the programme page's own degree, else the request's — with a scope note
#:   on each claim; a topic-search page inherits nothing, and a page naming
#:   another degree keeps it and is withheld below;
#: * QR-1b: a question page is read once per institution per run, and a
#:   second programme reuses its claims; every question page is read by the
#:   question's reader, whatever the classifier calls it.
#: * QR-1c (bundle4 dev2, UCT rep 2): UCT's programme page links no English
#:   page; the admissions page read beside it ("International applicants",
#:   itself degree-silent) does, so the language page came without the
#:   programme's degree and scored wrong-scope on the right value. A question,
#:   language or route link on the admissions page read beside a confirmed
#:   programme page carries the programme's degree as QR-1b's do, unless the
#:   admissions page states another degree; reused claims of a question page
#:   reached that way, or from the programme page, take it too when silent.
#:
#: FS-1 still applies to topic pages. The benchmark harness flips it per
#: capture (``--question-routing``).
QUESTION_ROUTED_EVIDENCE = True
#: QR-1: question links followed per question, beyond the topic query's page.
_MAX_QUESTION_LINKS = 2
#: QR-1: the deadline question's link text and URL path.
_DEADLINE_QUESTION_TEXT = re.compile(
    r"\bdeadlines?\b|\b(?:key|important)\s+dates\b|\bselection\s+procedure\b"
    r"|\bhow\s+to\s+apply\b|\bapplication\s+(?:procedure|process)\b",
    re.I,
)
_DEADLINE_QUESTION_PATH = re.compile(
    r"(?:^|[/_-])(?:deadlines?|key-dates|important-dates|dates-and-deadlines|how-to-apply"
    r"|selection-procedure|application-(?:procedure|process))(?:[/_.-]|$)",
    re.I,
)
#: Claim types a page reached for one question may yield when the classifier
#: would not admit it as a requirements page.
_QUESTION_CLAIMS: dict[str, frozenset[ClaimType]] = {
    "english": frozenset(
        {
            ClaimType.IELTS_MIN_OVERALL,
            ClaimType.IELTS_MIN_SUBSCORE,
            ClaimType.IELTS_ACCEPTED_TYPES,
            ClaimType.TOEFL_MIN_TOTAL,
            ClaimType.DUOLINGO_MIN,
            ClaimType.ENGLISH_EVIDENCE_MINIMUM,
            ClaimType.ENGLISH_TEST_WAIVER,
        }
    ),
    "deadline": frozenset({ClaimType.ADMISSION_DEADLINE}),
}
#: The claim that answers each question (QR-1's "still unanswered").
_QUESTION_ANSWER = {
    "english": ClaimType.IELTS_MIN_OVERALL,
    "fees": ClaimType.TUITION,
    "deadline": ClaimType.ADMISSION_DEADLINE,
}
#: ``read_scope`` degree words to the request's ``DegreeLevel`` values.
_SCOPE_LEVEL = {"bachelor": "bachelor", "master": "master", "doctorate": "phd"}


def _question_links(
    html: str,
    base: str,
    domain: str | None,
    extra_domains: Sequence[str] = (),
    *,
    degree: object = None,
) -> list[tuple[str, str]]:
    """QR-1: official ``(question, url)`` links on a page, in link order.

    The question is the first of english, fees, deadline that the link's text
    or URL path names; a link naming another degree level is dropped, and so
    is an application fee or waiver link and a scholarship deadline link.
    """
    if not domain:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = {base.rstrip("/")}
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        text = " ".join(link.text.split())
        if not url.startswith(("https://", "http://", "fixture://")) or url.rstrip("/") in seen:
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain, *extra_domains])):
            continue
        if _names_other_level(text, url, degree):
            continue
        path = url[len("fixture://") :] if url.startswith("fixture://") else urlparse(url).path
        question: str | None = None
        if _LANGUAGE_LINK.search(text) or _LANGUAGE_LINK.search(path.replace("/", " ")):
            question = "english"
        elif (_FEES_LEAD.search(text) or _FEES_LEAD_PATH.search(path)) and not (
            _NOT_FEES_LEAD.search(text) or _NOT_FEES_LEAD.search(path)
        ):
            question = "fees"
        elif (
            _DEADLINE_QUESTION_TEXT.search(text) or _DEADLINE_QUESTION_PATH.search(path)
        ) and not _SCHOLARSHIP_LEAD.search(text):
            question = "deadline"
        if question:
            seen.add(url.rstrip("/"))
            out.append((question, url))
    return out


def _home_url(candidate: Candidate) -> str | None:
    """QR-1: the institution's home page, a link source when no programme page is known."""
    return f"https://{candidate.domain}/" if candidate.domain else None


#: QR-1b: the request's ``DegreeLevel`` values to ``read_scope`` degree words.
_LEVEL_SCOPE = {level: word for word, level in _SCOPE_LEVEL.items()}
#: QR-1b: the scope note a claim carries when its degree came by route.
_ROUTE_SCOPE_NOTE = "Scope: degree from the linking programme page ({url})."
#: QR-1c: the note when the link was on the admissions page read beside it.
_ADMISSIONS_ROUTE_SCOPE_NOTE = (
    "Scope: degree from the confirmed programme page ({url}), "
    "linked through the admissions page ({admissions})."
)


def _route_scope(scope: ClaimScope, degree: str | None, programme: str) -> ClaimScope | None:
    """QR-1b: a linked page's read scope with the linking programme's degree.

    Only a page silent on its degree inherits one: a page that names a degree
    keeps it (and a degree other than the request's is then withheld).
    """
    if scope.degree or not degree:
        return None
    return replace(scope, degree=degree, programme=scope.programme or programme)


def _names_other_scope_level(claim: Claim, degree: object) -> bool:
    """QR-1: whether a claim's read scope names a degree level the request did not."""
    if claim.scope is None or not claim.scope.degree or not degree:
        return False
    level = _SCOPE_LEVEL.get(str(claim.scope.degree))
    return level is not None and str(degree) in _SCOPE_LEVEL.values() and level != str(degree)


class WebRequirementsAdapter:
    name = "web-requirements"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year
        #: Topic pages found per institution: programmes of one university
        #: share them, so each query is sent once per run.
        self._topic_pages: dict[str, tuple[tuple[str, str], ...]] = {}
        #: QR-1b: question pages read per institution, with the claims each
        #: yielded; a second programme of the university reuses them unread.
        self._question_pages: dict[str, dict[str, tuple[Claim, ...]]] = {}

    async def verify(
        self, candidate: Candidate, program: CandidateProgram, intake: str
    ) -> AdapterResult:
        out = AdapterResult()

        # Two sources on purpose: the programme page and the general admissions
        # page. When they disagree the conflict detector has something to find.
        targets = [
            _Target(program.url, SourceSpecificity.PROGRAM_INTAKE) if program.url else None,
            _Target(candidate.admissions_url, SourceSpecificity.UNIVERSITY_ADMISSIONS)
            if candidate.admissions_url
            else None,
        ]
        queue = [t for t in targets if t]
        #: QR-1: questions are routed, and topic search waits for the links.
        routed_questions = QUESTION_ROUTED_EVIDENCE
        if routed_questions:
            queue = [replace(t, link_source=True) for t in queue]
            home = _home_url(candidate) if not program.url else None
            if home and home not in {t.url for t in queue}:
                queue.append(
                    _Target(
                        home,
                        SourceSpecificity.UNIVERSITY_ADMISSIONS,
                        link_source=True,
                        links_only=True,
                    )
                )
        visited = {t.url for t in queue}
        if TOPIC_SEARCH and program.url and not routed_questions:
            for topic, url in await self._find_topic_pages(candidate, program, out):
                if url not in visited:
                    visited.add(url)
                    queue.append(_Target(url, SourceSpecificity.UNIVERSITY_ADMISSIONS, topic=topic))
        followed = 0
        routed = 0
        #: FS-1: the faculty the programme page named, once it has been read.
        programme_unit: str | None = None
        #: QR-1: question links queued per question; whether topic search ran;
        #: the programme page's final URLs (its claims keep their own guard).
        question_links: dict[str, int] = {}
        topics_asked = not (routed_questions and TOPIC_SEARCH)
        programme_pages: set[str] = set()
        #: QR-1b: the degree the programme page states (else the request's),
        #: the pages that took it by route, and this institution's question
        #: pages already read (url -> claims), with the one being read now.
        programme_degree: str | None = None
        route_scoped: dict[str, str] = {}
        #: QR-1c: the admissions page(s) whose links carry the programme's degree.
        admissions_pages: set[str] = set()
        question_pages = self._question_pages.setdefault(candidate.domain or candidate.name, {})
        reading_question: tuple[str, int] | None = None

        def file_question_page() -> None:
            """QR-1b: remember the question page just read, with its claims."""
            nonlocal reading_question
            if reading_question is not None:
                url, start = reading_question
                question_pages[url] = tuple(out.claims[start:])
                reading_question = None

        def route_note(target: _Target) -> str:
            """QR-1b/c: the scope note for a page that took the programme's degree."""
            if target.via_admissions:
                return _ADMISSIONS_ROUTE_SCOPE_NOTE.format(
                    url=program.url, admissions=target.via_admissions
                )
            return _ROUTE_SCOPE_NOTE.format(url=program.url)

        def rescope(claim: Claim, target: _Target) -> Claim:
            """QR-1c: a reused claim, silent on its degree, in the programme's."""
            if claim.scope is None:
                return claim
            inherited = _route_scope(claim.scope, programme_degree, program.name)
            if inherited is None:
                return claim
            route_scoped[claim.source_url] = route_note(target)
            return claim.model_copy(update={"scope": inherited})

        def note_fee_page(url: str) -> None:
            """QR-1: a page reached for fees goes to the cost adapter."""
            if (
                url == candidate.costs_url
                or url in candidate.question_fee_urls
                or len(candidate.question_fee_urls) >= _MAX_QUESTION_LINKS
            ):
                return
            candidate.question_fee_urls.append(url)

        def queue_questions(
            html: str, page_url: str, from_programme: bool = False, via: str | None = None
        ) -> None:
            """QR-1 (a): the official links on a link source that name a question."""
            for question, url in _question_links(
                html, page_url, candidate.domain, candidate.extra_domains, degree=program.degree
            ):
                if question == "fees":
                    note_fee_page(url)
                    continue
                if url in visited or question_links.get(question, 0) >= _MAX_QUESTION_LINKS:
                    continue
                visited.add(url)
                question_links[question] = question_links.get(question, 0) + 1
                queue.append(
                    _Target(
                        url,
                        SourceSpecificity.UNIVERSITY_ADMISSIONS,
                        question=question,
                        via_programme=from_programme,
                        via_admissions=via if from_programme else None,
                    )
                )

        async def queue_topic_questions() -> None:
            """QR-1 (b): one topic query per question the links left unanswered."""
            have = {c.claim_type for c in out.claims}
            wanted = [
                question
                for question, answer in _QUESTION_ANSWER.items()
                if answer not in have and not (question == "fees" and candidate.question_fee_urls)
            ]
            if not wanted:
                return
            for topic, url in await self._find_topic_pages(candidate, program, out, topics=wanted):
                if topic not in wanted:
                    continue
                if topic == "fees":
                    note_fee_page(url)
                    continue
                if url in visited:
                    continue
                visited.add(url)
                queue.append(
                    _Target(
                        url, SourceSpecificity.UNIVERSITY_ADMISSIONS, topic=topic, question=topic
                    )
                )

        def queue_leads(html: str, page_url: str, from_topic: bool = False) -> None:
            """Queue the official links below one read HTML page, within the caps."""
            nonlocal followed, routed
            from_topic = TOPIC_FACULTY_SCOPE and from_topic
            # QR-1b: a lead on the confirmed programme page carries its degree;
            # QR-1c: so does one on the admissions page read beside it.
            via_programme = routed_questions and (
                page_url in programme_pages or page_url in admissions_pages
            )
            via_admissions = page_url if page_url in admissions_pages else None
            # HL-1: no lead naming another degree level than the request.
            guard = HUB_LEADS and program.degree is not None
            # The English requirement often lives on its own page that the
            # programme or admissions page links to (UBC's English Language
            # Admission Standard, Groningen's faculty language page). When no
            # IELTS minimum has been read yet, follow at most
            # _MAX_LANGUAGE_FOLLOWS such official links, once.
            if followed < _MAX_LANGUAGE_FOLLOWS and not any(
                c.claim_type is ClaimType.IELTS_MIN_OVERALL for c in out.claims
            ):
                for url in _language_links(
                    html,
                    page_url,
                    candidate.domain,
                    candidate.extra_domains,
                    degree=program.degree if guard else None,
                ):
                    if url in visited or followed >= _MAX_LANGUAGE_FOLLOWS:
                        continue
                    visited.add(url)
                    followed += 1
                    queue.append(
                        _Target(
                            url,
                            SourceSpecificity.UNIVERSITY_ADMISSIONS,
                            language_follow=True,
                            from_topic=from_topic,
                            via_programme=via_programme,
                            via_admissions=via_admissions,
                        )
                    )
            if (ROUTE_LEADS or HUB_LEADS) and routed < _MAX_ROUTE_FOLLOWS:
                have = {c.claim_type for c in out.claims}
                want_deadline = ClaimType.ADMISSION_DEADLINE not in have
                want_english = ClaimType.IELTS_MIN_OVERALL not in have
                for url, is_requirements in _route_links(
                    html,
                    page_url,
                    candidate.domain,
                    candidate.extra_domains,
                    deadline=want_deadline,
                    requirements=want_english,
                ):
                    if url in visited or routed >= _MAX_ROUTE_FOLLOWS:
                        continue
                    # SL-1: deadline and route links get HL-1's URL level guard.
                    if (guard or _level_scope(program.degree)) and names_other_degree_level(
                        url, str(program.degree)
                    ):
                        continue
                    visited.add(url)
                    routed += 1
                    queue.append(
                        _Target(
                            url,
                            SourceSpecificity.UNIVERSITY_ADMISSIONS,
                            language_follow=is_requirements,
                            route_follow=True,
                            from_topic=from_topic,
                            via_programme=via_programme,
                            via_admissions=via_admissions,
                        )
                    )
            if not HUB_LEADS:
                return
            fees, awards = _service_links(
                html, page_url, candidate.domain, program.degree, candidate.extra_domains
            )
            if fees and not candidate.costs_url:
                # Read by the cost adapter, which runs after this one on the
                # same candidate (runner._stage_verify).
                candidate.costs_url = fees[0]
                visited.add(fees[0])
            elif not any(c.claim_type is ClaimType.TUITION for c in out.claims):
                for url in fees:
                    if url in visited or url == candidate.costs_url:
                        continue
                    if routed >= _MAX_ROUTE_FOLLOWS:
                        break
                    visited.add(url)
                    routed += 1
                    queue.append(
                        _Target(
                            url,
                            SourceSpecificity.UNIVERSITY_ADMISSIONS,
                            topic="fees",
                            fee_follow=True,
                            from_topic=from_topic,
                        )
                    )
                    break
            if awards and not candidate.scholarships_url:
                # Read by the funding stage, which walks it as the award index.
                candidate.scholarships_url = awards[0]

        while queue or not topics_asked:
            file_question_page()
            if not queue:
                topics_asked = True
                await queue_topic_questions()
                continue
            target = queue.pop(0)
            if target.question and _QUESTION_ANSWER[target.question] in {
                c.claim_type for c in out.claims
            }:
                # QR-1: answered by an earlier page; not read.
                continue
            if target.question and target.url in question_pages:
                # QR-1b: read for another programme of this university in this
                # run; its claims are reused, the page is not read again.
                reused = question_pages[target.url]
                if target.via_programme:
                    # QR-1c: the route this programme reached the page by
                    # gives its degree to claims the first read left silent.
                    reused = tuple(rescope(claim, target) for claim in reused)
                out.claims.extend(reused)
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="fetched-ok" if reused else "no-pattern-match",
                        detail=(
                            f"QR-1b: {target.question} page already read for this "
                            f"institution; {len(reused)} claims reused, not read again"
                        ),
                    )
                )
                continue
            res = await self.fetcher.get(target.url)
            out.pages_checked += 1
            if not res.ok:
                out.pages_failed += 1
                out.errors.append(f"{target.url}: {res.outcome.value} — {res.error}")
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="fetch-failed",
                        detail=f"{res.outcome.value} — {res.error}",
                    )
                )
                if res.outcome in (
                    FetchOutcome.TIMEOUT,
                    FetchOutcome.NETWORK_UNAVAILABLE,
                    FetchOutcome.HTTP_ERROR,
                ):
                    out.retry_urls.append(target.url)
                continue
            if not same_source_site(target.url, res.final_url or target.url):
                out.pages_failed += 1
                out.errors.append(
                    f"{target.url}: redirected off the source site; no requirements verified"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="fetch-failed",
                        detail="redirected off the source site",
                    )
                )
                continue

            text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
            if routed_questions and target.question:
                # QR-1b: read once per institution, whatever it yields.
                reading_question = (target.url, len(out.claims))
            if not text.strip():
                out.pages_failed += 1
                out.errors.append(
                    f"{target.url}: page fetched but no readable text could be extracted"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="unreadable",
                        detail="page fetched but no readable text could be extracted",
                    )
                )
                continue

            page_url = res.final_url or target.url
            page = classify_page(url=page_url, html="" if res.is_pdf else res.text, text=text)
            out.page_types.append((target.url, page.page_type.value))

            if (
                target.url == program.url
                and page.accepts("program_exists")
                and page.degree_level
                and program.degree
                and str(page.degree_level) != str(program.degree)
            ):
                out.errors.append(
                    f"{target.url}: final page {page_url} names {page.degree_level}; "
                    f"cannot verify the requested {program.degree} programme"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="classifier-rejected",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail="final page names a different degree level",
                    )
                )
                continue

            if (
                routed_questions
                and programme_pages
                and programme_degree
                and target.link_source
                and not target.links_only
                and target.url == candidate.admissions_url
                and target.url != program.url
                and not res.is_pdf
                and read_scope(text, title=html_title(res.text)).degree in (None, programme_degree)
            ):
                # QR-1c: the admissions page read beside a confirmed programme
                # page; silent on its degree (or stating the programme's), its
                # links carry the programme's degree.
                admissions_pages.add(page_url)
            if (
                routed_questions
                and target.link_source
                and not res.is_pdf
                and (
                    page_url.startswith("fixture://")
                    or is_official_domain(page_url, candidate.official_domains)
                )
            ):
                queue_questions(
                    res.text,
                    page_url,
                    from_programme=target.url == program.url or page_url in admissions_pages,
                    via=page_url if page_url in admissions_pages else None,
                )
            if target.links_only:
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="no-pattern-match",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail="QR-1: read for its question links only; nothing on it is claimed",
                    )
                )
                continue
            if routed_questions and target.url == program.url:
                programme_pages.add(page_url)

            page_title = html_title(res.text) if not res.is_pdf else page_url.rsplit("/", 1)[-1]
            scope = read_scope(text, title=page_title)
            if routed_questions and target.url == program.url:
                programme_degree = scope.degree or _LEVEL_SCOPE.get(str(program.degree or ""))
            elif routed_questions and target.via_programme:
                # QR-1b (owner, 2026-10-18): a page the programme page links to
                # for a question, and silent on its degree, is read in the
                # programme's degree; the evidence says so in a scope note.
                inherited = _route_scope(scope, programme_degree, program.name)
                if inherited is not None:
                    scope = inherited
                    route_scoped[page_url] = route_note(target)
            builder = ClaimBuilder(
                source_url=page_url,
                page_title=page_title,
                specificity=(
                    SourceSpecificity.PROGRAM_INTAKE
                    if page.page_type is PageType.INTAKE_SPECIFIC_PROGRAM
                    else target.specificity
                ),
                program=program.name,
                intake=intake,
                academic_year=page.academic_year or self.academic_year,
                official_domain=page_url.startswith("fixture://")
                or is_official_domain(page_url, candidate.official_domains),
                extraction_method="fixture" if target.url.startswith("fixture://") else "html_rule",
                accessed_at=res.fetched_at,
                # Read from the page's own words only. The programme, intake
                # and year above are what we asked for; this is what the page
                # answered, and recording the second as if it were the first
                # is the whole of the wrong-scope failure.
                scope=scope,
                # The verifier's context: without it the verbatim, domain and
                # page-type checks were silently skipped for every requirement
                # claim (found in the owner's adversarial review, 2026-09-25).
                page_text=text,
                page_type=page.page_type.value,
                allowed_domains=verification_domains(
                    page_url, candidate.domain, candidate.extra_domains
                ),
            )
            # TY-1: the year the applicant asked for, kept apart from the year
            # the page states first, so a fee table picks the applicant's row.
            builder.requested_academic_year = self.academic_year
            # HL-1: a page the classifier rejects is still scanned for leads;
            # its own text stays unclaimed.
            hub_scan = HUB_LEADS and not res.is_pdf and bool(builder.meta.get("official_domain"))
            topic_scoped = TOPIC_FACULTY_SCOPE and (target.topic is not None or target.from_topic)
            if TOPIC_FACULTY_SCOPE and target.url == program.url and not res.is_pdf:
                programme_unit = programme_faculty(text, res.text)
            if topic_scoped and programme_unit and not res.is_pdf:
                page_unit = page_faculty(res.text)
                if page_unit and page_unit != programme_unit:
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="no-pattern-match",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail=(
                                f"FS-1: the page names the faculty of {page_unit!r}; the "
                                f"programme is in {programme_unit!r}; nothing on it is claimed"
                            ),
                        )
                    )
                    continue

            if (
                TOPIC_PROGRAMME_SCOPE
                and (target.topic is not None or target.from_topic)
                and page.page_type is PageType.PROGRAM_DETAIL
                and page.subject
                and program.field
                and _names_another_programme(page.subject, program.field)
            ):
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="no-pattern-match",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail=(
                            f"FS-2: the page is the programme page of {page.subject!r}, "
                            f"not of {program.field!r}; nothing on it is claimed"
                        ),
                    )
                )
                continue

            if target.question in _QUESTION_CLAIMS:
                # QR-1: the question this page was reached for decides who
                # reads it, not its page type; verbatim and domain checks
                # still apply, and only that question's claims are kept.
                # QR-1b: an accepted page too (Imperial's "Deadlines" page
                # classifies as program_detail and leaked an intake claim).
                accepted = page.accepts("requirements")
                self._read_for_question(target.question, res, page_url, text, builder)
                if builder.claims and topic_scoped:
                    self._scope_to_faculty(text, program, programme_unit, builder)
                if builder.claims or (routed_questions and accepted):
                    out.claims.extend(builder.claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="fetched-ok" if builder.claims else "no-pattern-match",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail=(
                                f"{target.question} page: {len(builder.claims)} claims read "
                                "for the question it was reached for"
                            ),
                        )
                    )
                    if (hub_scan or accepted) and not res.is_pdf:
                        queue_leads(res.text, page_url, topic_scoped)
                    continue
                builder.claims.clear()
            if not page.accepts("requirements"):
                if target.fee_follow and not res.is_pdf and page.accepts("costs"):
                    # HL-1: a fee page reached by a fee link is read for its
                    # costs only, under the verifier's page-type table.
                    extract_costs(text, builder)
                    if builder.claims:
                        out.claims.extend(builder.claims)
                        out.page_outcomes.append(
                            PageOutcome(
                                url=target.url,
                                category="fetched-ok",
                                page_type=page.page_type.value,
                                readable_chars=len(text),
                                detail=f"fee page: {len(builder.claims)} cost claims read",
                            )
                        )
                        continue
                # A catalogue listing confirms existence by the T29 contract
                # (the university's own list); the verifier's page-type table
                # admits existence only on programme pages, so that one check
                # is lifted here while verbatim and domain still apply.
                builder.page_type = None
                if page.page_type in _LISTING_PAGE_TYPES and self._claim_listed_programme(
                    program, builder, text
                ):
                    # The page that confirms the programme may state its faculty
                    # in a labelled field; one value only (HKU, 2026-09-28).
                    if not res.is_pdf:
                        extract_programme_faculty(text, builder)
                    out.claims.extend(builder.claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="fetched-ok",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail="listing page: only the programme's existence was read",
                        )
                    )
                    if hub_scan:
                        queue_leads(res.text, page_url)
                    continue
                if target.language_follow and not res.is_pdf:
                    # The classifier's page type is a routing hint, not a permission
                    # (both reviews, 2026-09-25): a page reached through an official
                    # "English language requirements" link may state IELTS in a table
                    # whatever type it reads as. Only the structural IELTS reader runs;
                    # verbatim and domain checks still apply to what it reads.
                    tabled = extract_table_requirements(
                        build_document_ir(res.text, page_url), builder
                    )
                    if tabled and topic_scoped:
                        self._scope_to_faculty(text, program, programme_unit, builder)
                    if tabled and builder.claims:
                        out.claims.extend(builder.claims)
                        out.page_outcomes.append(
                            PageOutcome(
                                url=target.url,
                                category="fetched-ok",
                                page_type=page.page_type.value,
                                readable_chars=len(text),
                                detail=f"language page: {len(tabled)} claims read from its tables",
                            )
                        )
                        if hub_scan:
                            queue_leads(res.text, page_url, topic_scoped)
                        continue
                # An admission-route statement names admission itself ("admitted
                # without a declared major"), so it is read from any official page;
                # verbatim and domain checks still apply (KAIST's department page
                # classifies as unknown and states the route, 2026-09-27 trace).
                builder.page_type = None
                if not res.is_pdf and extract_admission_route(text, builder):
                    out.claims.extend(builder.claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="fetched-ok",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail="only the undergraduate admission route was read",
                        )
                    )
                    if hub_scan:
                        queue_leads(res.text, page_url)
                    continue
                out.errors.append(
                    f"{target.url}: classified as {page.page_type.value}; no requirement can be "
                    "read from this kind of page."
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="classifier-rejected",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail=(
                            f"classified as {page.page_type.value}; no requirement can be "
                            "read from this kind of page. "
                            # What the classifier saw, so a wrong call can be
                            # diagnosed from a capture without the page itself.
                            f"title={page.title[:80]!r} signals={'; '.join(page.signals[:3])!r} "
                            f"chars={len(text)} degrees={full_degree_titles(text)[:3]!r}"
                        ),
                    )
                )
                if hub_scan:
                    queue_leads(res.text, page_url)
                continue

            self._claim_program_exists(page, program, builder, out, text, identity_text=page_title)
            if page.accepts("program_exists") and not res.is_pdf:
                extract_programme_faculty(text, builder)
            if page.accepts("requirements"):
                # Structure first: a table row states the test, the column and the
                # value together (V2-30C). A prose claim of a type the table
                # already answered is dropped, so one page never states two
                # IELTS minimums from two readings of itself.
                tabled = (
                    extract_table_requirements(build_document_ir(res.text, page_url), builder)
                    if not res.is_pdf
                    else []
                )
                before = len(builder.claims)
                extract_requirements(text, builder)
                answered = {c.claim_type for c in tabled}
                builder.claims[before:] = [
                    c for c in builder.claims[before:] if c.claim_type not in answered
                ]
            self._claim_intake_state(page, text, intake, builder, out)
            self._claim_english_test_types(text, builder)
            self._claim_english_waiver(text, builder)
            self._claim_fees(text, builder)
            if (
                (TOPIC_SEARCH or (HUB_LEADS and target.topic is not None))
                and page.accepts("costs")
                and (target.topic is not None or target.url == program.url)
            ):
                # A programme page or a fee page states the tuition table
                # (Groningen: non-EU/EEA per academic year on the programme
                # page), which the university-level cost adapter never reads.
                extract_costs(text, builder)
            if topic_scoped:
                self._scope_to_faculty(text, program, programme_unit, builder)

            out.claims.extend(builder.claims)
            out.page_outcomes.append(
                PageOutcome(
                    url=target.url,
                    category="fetched-ok" if builder.claims else "no-pattern-match",
                    page_type=page.page_type.value,
                    readable_chars=len(text),
                    detail=(
                        f"{len(builder.claims)} claims read from this page"
                        if builder.claims
                        else "page was read and accepted, but no requirement pattern "
                        "matched; nothing on it is claimed"
                    ),
                )
            )
            if not res.is_pdf:
                queue_leads(res.text, page_url, topic_scoped)

        file_question_page()
        if route_scoped:
            # QR-1b: the evidence says where its degree came from.
            for claim in out.claims:
                note = route_scoped.get(claim.source_url)
                if (
                    note
                    and claim.scope is not None
                    and claim.scope.degree == programme_degree
                    and note not in claim.notes
                ):
                    claim.notes = f"{claim.notes} {note}" if claim.notes else note
        if routed_questions and program.degree:
            # QR-1: a page whose own words scope it to another degree level
            # does not answer for this one (UCPH's master's language page).
            withheld = [
                c
                for c in out.claims
                if c.source_url not in programme_pages
                and _names_other_scope_level(c, program.degree)
            ]
            if withheld:
                dropped = {id(c) for c in withheld}
                out.claims = [c for c in out.claims if id(c) not in dropped]
                for url in dict.fromkeys(c.source_url for c in withheld):
                    out.errors.append(
                        f"{url}: QR-1: the page scopes itself to another degree level than "
                        f"the requested {program.degree}; its claims are withheld"
                    )

        if not out.claims and out.pages_checked == 0:
            out.errors.append(
                f"No official page is known for {program.name} at {candidate.name}; "
                "requirements cannot be verified."
            )
        return out

    def _read_for_question(
        self, question: str, res, page_url: str, text: str, builder: ClaimBuilder
    ) -> None:
        """QR-1: read a page for one question only, whatever its page type.

        English: the structural table reader, then prose (a type the table
        answered is not read twice), then the accepted-test and waiver
        sentences. Deadline: the deadline reader. Every other claim type is
        dropped, so a page reached for one question answers only that one.
        """
        builder.page_type = None
        tabled = (
            extract_table_requirements(build_document_ir(res.text, page_url), builder)
            if question == "english" and not res.is_pdf
            else []
        )
        before = len(builder.claims)
        extract_requirements(text, builder)
        answered = {c.claim_type for c in tabled}
        builder.claims[before:] = [
            c for c in builder.claims[before:] if c.claim_type not in answered
        ]
        if question == "english":
            self._claim_english_test_types(text, builder)
            self._claim_english_waiver(text, builder)
        keep = _QUESTION_CLAIMS[question]
        builder.claims[:] = [c for c in builder.claims if c.claim_type in keep]

    async def _find_topic_pages(
        self,
        candidate: Candidate,
        program: CandidateProgram,
        out: AdapterResult,
        topics: Sequence[str] | None = None,
    ) -> tuple[tuple[str, str], ...]:
        """One official page per topic, from one public query each, or nothing.

        Only the institution's name enters a query. A result counts only on the
        institution's own domain, outside excluded paths and not naming another
        degree level. A provider failure (a 429 included) ends the search for
        this institution; nothing is retried.
        """
        from app.adapters.discovery.live_discovery import (
            is_excluded_path,
            names_other_degree_level,
            registrable_domain,
            same_institution,
        )
        from app.adapters.search import SearchError, get_search_provider
        from app.adapters.search import intent as intent_module
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DEFAULT_QUERY_BUDGET

        key = candidate.domain or candidate.name
        if key in self._topic_pages:
            return self._topic_pages[key]
        self._topic_pages[key] = ()
        if not candidate.domain:
            return ()
        # One institution gets DEFAULT_QUERY_BUDGET queries in all; topic
        # search spends only what discovery left (English first).
        remaining = DEFAULT_QUERY_BUDGET - candidate.search_queries_used
        if intent_module.SHARED_QUERY_BUDGET:
            remaining -= intent_module.SCHOLARSHIP_QUERY_RESERVE
        if remaining <= 0:
            out.errors.append(
                f"Topic search not run: discovery used the {DEFAULT_QUERY_BUDGET}-query budget"
            )
            return ()
        try:
            provider = get_search_provider()
        except SearchError:
            return ()
        found: list[tuple[str, str]] = []
        # QR-1: only the questions still unanswered are asked.
        queries = [q for q in _TOPIC_QUERIES if topics is None or q[0] in topics]
        for topic, template in queries[:remaining]:
            if intent_module.SHARED_QUERY_BUDGET:
                candidate.search_queries_used += 1
            try:
                response = await provider.search(
                    query=template.format(name=candidate.name),
                    domains=[
                        registrable_domain(candidate.domain) or candidate.domain,
                        *candidate.extra_domains,
                    ],
                    max_results=5,
                )
            except SearchError as exc:
                out.errors.append(
                    f"Topic search ({topic}): {search_failure_diagnostic(provider.name, exc)}"
                )
                # TS-2: one failed topic need not cost the others; a 429 still
                # stops, as it does in discovery.
                if TOPIC_SEARCH_CONTINUE and getattr(exc, "http_status", None) != 429:
                    continue
                break
            taken = {u for _, u in found}
            for result in response.results:
                url = result.url
                if (
                    any(same_institution(url, d) for d in candidate.official_domains)
                    and not is_excluded_path(url)
                    and not names_other_degree_level(url, str(program.degree))
                    and url not in taken
                ):
                    found.append((topic, url))
                    break
        self._topic_pages[key] = tuple(found)
        return self._topic_pages[key]

    @staticmethod
    def _scope_to_faculty(
        text: str, program: CandidateProgram, faculty: str | None, builder: ClaimBuilder
    ) -> None:
        """FS-1: on a per-faculty page, IELTS only from the programme's own section.

        Every IELTS claim read from the whole page is dropped and the sections
        that name the programme (else its faculty) are read again; the claims
        stand only when exactly one section yields them. Otherwise the page
        states no IELTS minimum for this programme.
        """
        per_faculty, sections = _faculty_section(text, program.name, faculty)
        if not per_faculty:
            return
        builder.claims[:] = [
            c for c in builder.claims if c.claim_type not in _FACULTY_SCOPED_CLAIMS
        ]
        yielded: list[list[Claim]] = []
        for section in sections:
            before = len(builder.claims)
            extract_requirements(section, builder)
            read = [c for c in builder.claims[before:] if c.claim_type in _FACULTY_SCOPED_CLAIMS]
            del builder.claims[before:]
            if read:
                yielded.append(read)
        if len(yielded) == 1:
            builder.claims.extend(yielded[0])

    # --- individual claims ------------------------------------------------

    def _claim_program_exists(
        self, page, program, builder, out, text: str, *, identity_text: str | None = None
    ) -> None:
        """Only a programme page whose own subject matches may confirm existence."""
        if not page.accepts("program_exists"):
            if page.page_type in _LISTING_PAGE_TYPES and self._claim_listed_programme(
                program, builder, text
            ):
                return
            out.errors.append(
                f"{builder.meta['source_url']}: {page.page_type.value} pages cannot confirm that "
                f"{program.name!r} exists."
            )
            return

        matched, why = program_matches(
            requested_name=program.name,
            requested_field=program.field,
            page_subject=page.subject,
            requested_degree=program.degree,
            page_degree=page.degree_level,
        )
        if (
            matched
            and program.field
            and _named_after_its_url(program)
            and not matches_field_text(page.subject or "", [program.field])
        ):
            # The requested name can be discovery's placeholder from a URL slug,
            # so it matches the page it came from. The applicant's field is the
            # check that cannot: HKU's "Computing and Data Science", reached by
            # search, confirmed itself for a computer science applicant (run 51).
            matched, why = (
                False,
                (
                    f"page subject {page.subject!r} does not name the requested field "
                    f"{program.field!r}"
                ),
            )
        if matched and _COURSE_LIST.search(page.subject or ""):
            # A calendar section lists courses, not a programme one can apply
            # to: Toronto's "Computer Science Topic Courses" (run 52).
            matched, why = False, f"page subject {page.subject!r} names courses, not a programme"
        if not matched:
            out.errors.append(
                f"{builder.meta['source_url']}: not confirming {program.name!r} — {why}"
            )
            return

        excerpt = _first_sentence_containing(text, page.subject) or page.subject or ""
        language = page.language_of_instruction
        identity_only = (
            not is_verbatim_excerpt(excerpt, text)
            and bool(identity_text)
            and is_verbatim_excerpt(page.subject or "", identity_text or "")
        )
        if identity_only:
            # This is the actual fetched title (or h1 fallback), outside the
            # selected article. It proves identity only; never join it to body
            # text to manufacture language or requirement evidence.
            excerpt = identity_text or ""
            language = None
        if not identity_only and page.language_evidence is not None:
            proof = _complete_language_excerpt(text, page.language_evidence)
            if proof:
                excerpt = proof
            else:
                language = None
        reading_context = builder.page_text
        try:
            if identity_only:
                builder.page_text = identity_text
            claim = builder.add(
                ClaimType.PROGRAM_EXISTS,
                {
                    "program": page.subject,
                    "degree": page.degree_level,
                    "language": language,
                    "matched_because": why,
                },
                excerpt,
                confidence=0.9,
                section="Programme identity",
                # The programme's own title states its degree; a stray "master's"
                # elsewhere on the page must not re-scope it (run 76, HKU).
                degree=str(page.degree_level) if page.degree_level else None,
            )
        finally:
            builder.page_text = reading_context
        if claim is None and builder.rejected:
            out.errors.append(
                f"{builder.meta['source_url']}: programme identity rejected: "
                f"{builder.rejected[-1][2].value}"
            )

    @staticmethod
    def _claim_listed_programme(program, builder, text: str) -> bool:
        """Confirm existence from a listing page, or do nothing.

        Owner decision 2026-09-23: a school or listing page may confirm
        **existence only**, and only by naming the requested programme by a
        full degree title the ontology's strong aliases equate with it. HKU's
        certified source is exactly such a page. Nothing else is read from it.
        """
        listed = _listed_programme(text, program)
        if listed is None:
            return False
        title, degree = listed
        builder.add(
            ClaimType.PROGRAM_EXISTS,
            {
                "program": title,
                "degree": degree,
                "language": None,
                "matched_because": "named by its full degree title on a listing page",
            },
            _first_sentence_containing(text, title, max_characters=300) or title,
            confidence=0.7,
            section="Programme identity",
            degree=str(degree) if degree else None,
        )
        return True

    def _claim_intake_state(self, page, text: str, intake: str, builder, out) -> None:
        """Open, closed, or no claim at all. Silence is never 'open'."""
        if not page.accepts("intake"):
            return
        flat = for_matching(text)

        closed = _INTAKE_CLOSED_EVIDENCE.search(flat)
        if closed:
            builder.add(
                ClaimType.INTAKE_OPEN,
                False,
                closed.group(0).strip()[:400],
                confidence=0.85,
                section="Key dates",
            )
            return

        for label, pattern in _INTAKE_OPEN_EVIDENCE:
            match = pattern.search(flat)
            if not match:
                continue
            sentence = match.group(0).strip()
            year = _target_year(intake)
            # The evidence has to be about the cycle being researched.
            years = {int(y) for y in re.findall(r"\b(20\d{2})\b", sentence)}
            if year and years and year not in years and (year - 1) not in years:
                out.errors.append(
                    f"{builder.meta['source_url']}: found an application window for "
                    f"{sorted(years)}, not {year}; intake status left unknown."
                )
                continue
            builder.add(
                ClaimType.INTAKE_OPEN,
                True,
                sentence[:400],
                confidence=0.8,
                section="Key dates",
                notes=f"positive evidence: {label}",
            )
            return

        out.errors.append(
            f"{builder.meta['source_url']}: no statement about the application window for "
            f"{intake}; intake status is unknown, not open."
        )

    def _claim_english_waiver(self, text: str, builder) -> None:
        """The published conditions under which no English test is required.

        Recorded as the page's own sentence, not as a boolean: "a waiver
        exists" is useless to an applicant who cannot tell whether it covers
        them, and the conditions are the whole content of the fact. A
        Kazakhstani applicant from an English-medium school lives or dies by
        this sentence, and until now the pipeline read only *fee* waivers and
        dropped it.

        The sentence must be about the language requirement: a fee waiver
        beside it is a different fact, and matching "waiver" alone would claim
        an English exemption from a page offering to waive an application fee.
        """
        flat = for_matching(text)
        for match in _ENGLISH_WAIVER.finditer(flat):
            sentence = match.group(0).strip()
            if not _MENTIONS_ENGLISH.search(sentence):
                continue
            if _NO_ENGLISH_WAIVER.search(sentence):
                # "No waivers are granted" settles it the other way, and
                # claiming a waiver here would be the worse error.
                builder.add(ClaimType.ENGLISH_TEST_WAIVER, "", sentence, confidence=0.7)
                return
            builder.add(ClaimType.ENGLISH_TEST_WAIVER, sentence, sentence, confidence=0.75)
            return

    def _claim_english_test_types(self, text: str, builder) -> None:
        flat = for_matching(text)
        match = re.search(
            r"[^.]*\bIELTS\b[^.]{0,120}?\b(Academic|General Training)\b[^.]{0,120}\.", flat, re.I
        )
        if not match:
            return
        sentence = match.group(0).strip()
        low = sentence.lower()
        accepted: list[str] = []
        if "academic" in low:
            accepted.append("academic")
        if "ukvi" in low:
            accepted.append("ukvi_academic")
        if re.search(r"general training is not accepted|not accept[^.]{0,30}general training", low):
            accepted = [a for a in accepted if a != "general_training"]
        elif "general training" in low and "not" not in low:
            accepted.append("general_training")
        if accepted:
            builder.add(
                ClaimType.IELTS_ACCEPTED_TYPES,
                accepted,
                sentence[:400],
                section="English language requirements",
            )

    def _claim_fees(self, text: str, builder) -> None:
        fee_line = _line_containing(text, "application fee")
        if fee_line:
            fee = _fee(fee_line)
            if fee is not None:
                builder.add(ClaimType.APPLICATION_FEE, fee, fee_line, confidence=0.7)
        waiver_line = _line_containing(text, "fee waiver")
        if not waiver_line:
            return
        if _WAIVER_NEGATION.search(waiver_line):
            # "Fee waivers are not available" — claiming True here was the
            # opposite of the page. Explicit negation is claimed as False.
            builder.add(ClaimType.FEE_WAIVER_AVAILABLE, False, waiver_line, confidence=0.7)
        elif _WAIVER_OFFERED.search(waiver_line):
            builder.add(ClaimType.FEE_WAIVER_AVAILABLE, True, waiver_line, confidence=0.7)
        # Anything else (e.g. "questions about fee waivers ...") neither
        # affirms nor negates: no claim at all.


# --- helpers ---------------------------------------------------------------


#: A subject that names a list of courses rather than a programme.
_COURSE_LIST = re.compile(r"\bcourses?\b(?!\s+of\s+study)", re.IGNORECASE)


def _named_after_its_url(program: CandidateProgram) -> bool:
    """Whether the requested name is only discovery's placeholder from the URL.

    Such a name matches the page it came from by construction, so it cannot
    say the page is the applicant's programme. A name from a catalogue or a
    registry is the university's own and is trusted as before.
    """
    if not program.url:
        return False
    slug = program.url.rstrip("/").rsplit("/", 1)[-1]
    slug_words = [w for w in re.split(r"[-_]+", slug.lower().replace(".html", "")) if w]
    name_words = [w for w in re.split(r"[^a-z0-9]+", program.name.lower()) if w]
    return bool(slug_words) and slug_words == name_words


def _target_year(intake: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", intake or "")
    return int(match.group(1)) if match else None


#: Pages that list programmes rather than describe one. Only these may name a
#: programme into existence, and only by its full degree title.
_LISTING_PAGE_TYPES = frozenset({PageType.PROGRAM_CATALOG, PageType.UNKNOWN})


def _listed_programme(text: str, program) -> tuple[str, str | None] | None:
    """The first full degree title on a listing page that names the requested
    programme, and its degree — or ``None``.

    Strict on both counts: the ontology must say YES (a strong alias, never a
    related field), and a stated degree level must be the requested one.
    """
    for title in full_degree_titles(text):
        # Against the requested field as well as the candidate's name: the
        # name can be what a faculty page calls itself. Run 35: HKU's page,
        # named "Computing and Data Science", listed "Bachelor of Engineering
        # in Computer Science" for a request for computer science.
        wanted = [n for n in (program.name, getattr(program, "field", "")) if n]
        if not any(titles_name_same_programme(title, n) is Verdict.YES for n in wanted):
            continue
        degree = degree_level_of(title)
        if degree_matches(program.degree, degree) is False:
            continue
        return title, degree
    return None


def _complete_language_excerpt(text: str, evidence: str) -> str:
    """Locate the whole main-content proof in the reader's original text."""
    if not evidence:
        return ""
    pattern = re.compile(r"\s+".join(re.escape(word) for word in evidence.split()), re.I)
    match = pattern.search(text)
    if match is None or match.end() - match.start() > MAX_EXCERPT_CHARS:
        return ""
    return match.group()


def _first_sentence_containing(
    text: str, needle: str | None, *, max_characters: int | None = None
) -> str:
    """A real quote from the page, or empty. Never a sentence we wrote."""
    if not needle:
        return ""
    flat = for_matching(text)
    index = flat.lower().find(needle.lower())
    if index < 0:
        return ""
    if max_characters is None:
        return excerpt_around(flat, index, index + len(needle))
    # Keep the full programme title within the owner's 300-character support
    # window; unrelated surrounding prose otherwise obscures listing evidence.
    radius = max(0, (max_characters - len(needle)) // 2)
    return excerpt_around(flat, index, index + len(needle), radius=radius)


def _fee(line: str) -> dict[str, object] | None:
    """The application fee, or None.

    Returning the raw sentence when no amount parses would put a fragment like
    "Among this year's applicants, thre" into the results as a fee. A fee we
    cannot read is simply not a claim.
    """
    from app.adapters.extraction import parse_money

    parsed = parse_money(line)
    return {"amount": parsed[0], "currency": parsed[1]} if parsed else None


def _line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line.lower():
            return line.strip()[:300]
    return ""
