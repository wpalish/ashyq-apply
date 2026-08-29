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

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import (
    ClaimBuilder,
    excerpt_around,
    extract_cost_tables,
    extract_requirements,
    for_matching,
    html_title,
    is_official_domain,
    pdf_to_text,
    readable_text,
)
from app.adapters.fetching import Fetcher
from app.adapters.matching import program_matches
from app.adapters.page_classifier import PageType, classify_page
from app.domain.enums import ClaimType, FetchOutcome, SourceSpecificity

#: An intake is open only when a page says so. Each pattern must capture the
#: sentence it matched, which becomes the claim's excerpt.
_INTAKE_OPEN_EVIDENCE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("application window", re.compile(
        r"[^.]*\bapplications?\b[^.]{0,80}\b(?:open|opens|opened|will open)\b[^.]{0,80}\.", re.I)),
    ("currently accepting", re.compile(
        r"[^.]*\b(?:now accepting|currently accepting|accepting applications|applications are open)\b[^.]{0,80}\.", re.I)),
    ("apply now for cycle", re.compile(
        r"[^.]*\bapply (?:now|online|here)\b[^.]{0,80}\b(20\d{2})\b[^.]{0,60}\.", re.I)),
)
_INTAKE_CLOSED_EVIDENCE = re.compile(
    r"[^.]*\b(?:applications? (?:are |is )?closed|no longer accepting|admissions? (?:are |is )?closed"
    r"|intake (?:is )?closed|not accepting applications)\b[^.]{0,80}\.", re.I,
)


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
            if candidate.admissions_url else None,
        ]
        for target in [t for t in targets if t]:
            res = await self.fetcher.get(target.url)
            out.pages_checked += 1
            if not res.ok:
                out.pages_failed += 1
                out.errors.append(f"{target.url}: {res.outcome.value} — {res.error}")
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
                continue

            page = classify_page(url=target.url, html="" if res.is_pdf else res.text, text=text)
            out.page_types.append((target.url, page.page_type.value))

            if not page.accepts("requirements"):
                out.errors.append(
                    f"{target.url}: classified as {page.page_type.value}; no requirement can be "
                    "read from this kind of page."
                )
                continue

            builder = ClaimBuilder(
                source_url=target.url,
                page_title=html_title(res.text) if not res.is_pdf else target.url.rsplit("/", 1)[-1],
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
            )

            self._claim_program_exists(page, program, builder, out, text)
            if page.accepts("requirements"):
                extract_requirements(text, builder)
            self._claim_intake_state(page, text, intake, builder, out)
            self._claim_english_test_types(text, builder)
            self._claim_fees(text, builder)
            if not res.is_pdf:
                # Some universities put the fee table on the programme page
                # rather than a separate fees page. Groningen is one, and its
                # EU/EEA and non-EU/EEA rates are the difference between
                # €2,694 and €19,800 for the same year.
                claims_from_fee_tables(res.text, builder)

            out.claims.extend(builder.claims)

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
        if not matched:
            out.errors.append(f"{builder.meta['source_url']}: not confirming {program.name!r} — {why}")
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

    def _claim_intake_state(self, page, text: str, intake: str, builder, out) -> None:
        """Open, closed, or no claim at all. Silence is never 'open'."""
        if not page.accepts("intake"):
            return
        flat = for_matching(text)

        closed = _INTAKE_CLOSED_EVIDENCE.search(flat)
        if closed:
            builder.add(
                ClaimType.INTAKE_OPEN, False, closed.group(0).strip()[:400],
                confidence=0.85, section="Key dates",
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
                ClaimType.INTAKE_OPEN, True, sentence[:400],
                confidence=0.8, section="Key dates",
                notes=f"positive evidence: {label}",
            )
            return

        out.errors.append(
            f"{builder.meta['source_url']}: no statement about the application window for "
            f"{intake}; intake status is unknown, not open."
        )

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
                ClaimType.IELTS_ACCEPTED_TYPES, accepted, sentence[:400],
                section="English language requirements",
            )

    def _claim_fees(self, text: str, builder) -> None:
        fee_line = _line_containing(text, "application fee")
        if fee_line:
            fee = _fee(fee_line)
            if fee is not None:
                builder.add(ClaimType.APPLICATION_FEE, fee, fee_line, confidence=0.7)
        waiver = _line_containing(text, "fee waiver")
        if waiver:
            builder.add(ClaimType.FEE_WAIVER_AVAILABLE, True, waiver, confidence=0.7)


# --- helpers ---------------------------------------------------------------


def _target_year(intake: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", intake or "")
    return int(match.group(1)) if match else None


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


def claims_from_fee_tables(html: str, builder) -> list:
    """Tuition rows from any fee table the programme page carries itself.

    A separate name rather than a bare call so the programme-page path can be
    tested directly: this is where Groningen's fees live, and wiring tables
    only into the cost adapter would have left them unread on the very page a
    student is reading.
    """
    return extract_cost_tables(html, builder)
