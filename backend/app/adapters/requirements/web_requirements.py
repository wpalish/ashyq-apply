"""Admission requirements from a programme page.

URL-scheme agnostic on purpose: the same adapter reads a bundled
``fixture://`` page and a live university page, so demo mode rehearses the real
extraction path instead of returning canned objects.
"""

from __future__ import annotations

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import (
    ClaimBuilder,
    extract_requirements,
    html_title,
    html_to_text,
    is_official_domain,
    pdf_to_text,
)
from app.adapters.fetching import Fetcher
from app.domain.enums import ClaimType, FetchOutcome, SourceSpecificity


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
            (program.url, SourceSpecificity.PROGRAM_INTAKE),
            (candidate.admissions_url, SourceSpecificity.UNIVERSITY_ADMISSIONS),
        ]
        for url, specificity in targets:
            if not url:
                continue
            res = await self.fetcher.get(url)
            out.pages_checked += 1
            if not res.ok:
                out.pages_failed += 1
                out.errors.append(f"{url}: {res.outcome.value} — {res.error}")
                if res.outcome in (
                    FetchOutcome.TIMEOUT,
                    FetchOutcome.NETWORK_UNAVAILABLE,
                    FetchOutcome.HTTP_ERROR,
                ):
                    out.retry_urls.append(url)
                continue

            text = pdf_to_text(res.content) if res.is_pdf else html_to_text(res.text)
            if not text.strip():
                out.pages_failed += 1
                out.errors.append(f"{url}: page fetched but no readable text could be extracted")
                continue

            builder = ClaimBuilder(
                source_url=url,
                page_title=html_title(res.text) if not res.is_pdf else url.rsplit("/", 1)[-1],
                specificity=specificity,
                program=program.name,
                intake=intake,
                academic_year=self.academic_year,
                official_domain=url.startswith("fixture://")
                or is_official_domain(url, [candidate.domain]),
                extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
                accessed_at=res.fetched_at,
            )
            builder.add(
                ClaimType.PROGRAM_EXISTS,
                program.name,
                f"Programme page reachable: {builder.meta['page_title']}",
                confidence=0.95,
            )
            extract_requirements(text, builder)

            low = text.lower()
            if "ielts general training is not accepted" in low or "ielts academic" in low:
                accepted = ["academic"]
                if "ukvi" in low:
                    accepted.append("ukvi_academic")
                builder.add(
                    ClaimType.IELTS_ACCEPTED_TYPES,
                    accepted,
                    "IELTS Academic required; General Training not accepted.",
                    section="English language requirements",
                )
            if "not accepting applications" in low or "applications are closed" in low:
                builder.add(ClaimType.INTAKE_OPEN, False, "Programme states applications are closed.")
            else:
                builder.add(
                    ClaimType.INTAKE_OPEN,
                    True,
                    f"Page describes entry for the {intake} intake.",
                    confidence=0.6,
                )
            fee = _fee(text)
            if fee is not None:
                builder.add(
                    ClaimType.APPLICATION_FEE,
                    fee,
                    _line_containing(text, "application fee"),
                    confidence=0.7,
                )
            if "fee waiver" in low:
                builder.add(
                    ClaimType.FEE_WAIVER_AVAILABLE,
                    True,
                    _line_containing(text, "fee waiver"),
                    confidence=0.7,
                )

            out.claims.extend(builder.claims)

        if not out.claims and out.pages_checked == 0:
            out.errors.append(
                f"No official page is known for {program.name} at {candidate.name}; "
                "requirements cannot be verified."
            )
        return out


def _fee(text: str) -> dict[str, object] | None:
    """The application fee, or None.

    Returning the raw sentence when no amount parses would put a fragment like
    "Among this year's applicants, thre" into the results as a fee. A fee we
    cannot read is simply not a claim.
    """
    from app.adapters.extraction import parse_money

    line = _line_containing(text, "application fee")
    parsed = parse_money(line)
    return {"amount": parsed[0], "currency": parsed[1]} if parsed else None


def _line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line.lower():
            return line.strip()[:300]
    return ""
