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
from dataclasses import dataclass

from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.discovery.live_discovery import matches_field_text
from app.adapters.extraction import (
    ClaimBuilder,
    excerpt_around,
    extract_requirements,
    for_matching,
    html_title,
    is_official_domain,
    pdf_to_text,
    readable_text,
)
from app.adapters.fetching import Fetcher
from app.adapters.matching import degree_matches, program_matches
from app.adapters.page_classifier import (
    PageType,
    classify_page,
    degree_level_of,
    full_degree_titles,
)
from app.adapters.scope_reader import read_scope
from app.adapters.search.ontology import titles_name_same_programme
from app.domain.enums import ClaimType, FetchOutcome, SourceSpecificity
from app.domain.programme_identity import Verdict

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


@dataclass(frozen=True)
class _Target:
    url: str
    specificity: SourceSpecificity


class WebRequirementsAdapter:
    name = "web-requirements"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year

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
        for target in [t for t in targets if t]:
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

            text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
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

            page = classify_page(url=target.url, html="" if res.is_pdf else res.text, text=text)
            out.page_types.append((target.url, page.page_type.value))

            page_title = html_title(res.text) if not res.is_pdf else target.url.rsplit("/", 1)[-1]
            builder = ClaimBuilder(
                source_url=target.url,
                page_title=page_title,
                specificity=(
                    SourceSpecificity.PROGRAM_INTAKE
                    if page.page_type is PageType.INTAKE_SPECIFIC_PROGRAM
                    else target.specificity
                ),
                program=program.name,
                intake=intake,
                academic_year=page.academic_year or self.academic_year,
                official_domain=target.url.startswith("fixture://")
                or is_official_domain(target.url, [candidate.domain]),
                extraction_method="fixture" if target.url.startswith("fixture://") else "html_rule",
                accessed_at=res.fetched_at,
                # Read from the page's own words only. The programme, intake
                # and year above are what we asked for; this is what the page
                # answered, and recording the second as if it were the first
                # is the whole of the wrong-scope failure.
                scope=read_scope(text, title=page_title),
            )

            if not page.accepts("requirements"):
                if page.page_type in _LISTING_PAGE_TYPES and self._claim_listed_programme(
                    program, builder, text
                ):
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
                continue

            self._claim_program_exists(page, program, builder, out, text)
            if page.accepts("requirements"):
                extract_requirements(text, builder)
            self._claim_intake_state(page, text, intake, builder, out)
            self._claim_english_test_types(text, builder)
            self._claim_english_waiver(text, builder)
            self._claim_fees(text, builder)

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

        if not out.claims and out.pages_checked == 0:
            out.errors.append(
                f"No official page is known for {program.name} at {candidate.name}; "
                "requirements cannot be verified."
            )
        return out

    # --- individual claims ------------------------------------------------

    def _claim_program_exists(self, page, program, builder, out, text: str) -> None:
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
        if not matched:
            out.errors.append(
                f"{builder.meta['source_url']}: not confirming {program.name!r} — {why}"
            )
            return

        excerpt = _first_sentence_containing(text, page.subject) or page.subject or ""
        builder.add(
            ClaimType.PROGRAM_EXISTS,
            {
                "program": page.subject,
                "degree": page.degree_level,
                "language": page.language_of_instruction,
                "matched_because": why,
            },
            excerpt,
            confidence=0.9,
            section="Programme identity",
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
            _first_sentence_containing(text, title) or title,
            confidence=0.7,
            section="Programme identity",
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


def _first_sentence_containing(text: str, needle: str | None) -> str:
    """A real quote from the page, or empty. Never a sentence we wrote."""
    if not needle:
        return ""
    flat = for_matching(text)
    index = flat.lower().find(needle.lower())
    if index < 0:
        return ""
    return excerpt_around(flat, index, index + len(needle))


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
