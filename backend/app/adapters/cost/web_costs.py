"""Cost of attendance from an official fees page (HTML or PDF)."""

from __future__ import annotations

from app.adapters.base import AdapterResult, Candidate, PageOutcome
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import (
    ClaimBuilder,
    html_title,
    is_official_domain,
    pdf_to_text,
    readable_text,
    verification_domains,
)
from app.adapters.fetching import Fetcher
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import classify_page, main_content
from app.adapters.requirements import web_requirements as _requirements
from app.adapters.scope_reader import read_scope
from app.adapters.structured_costs import (
    StructuredCosts,
    extract_structured_costs,
    extract_unhandled_costs,
)
from app.domain.enums import ClaimType, CostCategory, SourceSpecificity
from app.schemas.money import Money
from app.schemas.result import CostBreakdown

_CLAIM_TO_CATEGORY = {
    ClaimType.TUITION: CostCategory.TUITION,
    ClaimType.MANDATORY_FEES: CostCategory.MANDATORY_FEES,
    ClaimType.HOUSING_COST: CostCategory.HOUSING,
    ClaimType.MEALS_COST: CostCategory.MEALS,
    ClaimType.HEALTH_INSURANCE_COST: CostCategory.HEALTH_INSURANCE,
    ClaimType.BOOKS_COST: CostCategory.BOOKS,
    ClaimType.TRAVEL_COST: CostCategory.TRAVEL,
    ClaimType.PERSONAL_EXPENSES_COST: CostCategory.PERSONAL,
}


class WebCostAdapter:
    name = "web-costs"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year

    async def fetch(self, candidate: Candidate) -> tuple[CostBreakdown, AdapterResult]:
        if not _requirements.QUESTION_ROUTED_EVIDENCE or not candidate.question_fee_urls:
            if not candidate.costs_url:
                out = AdapterResult()
                out.errors.append(f"No official cost page is known for {candidate.name}.")
                return CostBreakdown(academic_year=self.academic_year), out
            return await self._read_page(candidate, candidate.costs_url)
        # QR-1: the cost page discovery chose is read first, as before; a fee
        # page reached for the fees question is read only while no page has
        # stated a tuition figure (Chula's ``costs_url`` was a feedback page,
        # its "Tuition and fees" page came from the fees query).
        urls = [candidate.costs_url] if candidate.costs_url else []
        urls += [u for u in candidate.question_fee_urls if u not in urls]
        out = AdapterResult()
        breakdown: CostBreakdown | None = None
        for url in urls:
            page_breakdown, page_out = await self._read_page(candidate, url)
            _merge_results(out, page_out)
            if breakdown is None:
                breakdown = page_breakdown
            else:
                _merge_breakdowns(breakdown, page_breakdown)
            if any(c.claim_type is ClaimType.TUITION for c in out.claims):
                break
        assert breakdown is not None
        return breakdown, out

    async def _read_page(
        self, candidate: Candidate, costs_url: str
    ) -> tuple[CostBreakdown, AdapterResult]:
        """One fee page read: its breakdown and what happened reading it."""
        out = AdapterResult()
        breakdown = CostBreakdown(academic_year=self.academic_year)
        res = await self.fetcher.get(costs_url)
        out.pages_checked += 1
        if not res.ok:
            out.pages_failed += 1
            out.errors.append(f"{costs_url}: {res.outcome.value} — {res.error}")
            out.page_outcomes.append(
                PageOutcome(
                    url=costs_url,
                    category="fetch-failed",
                    detail=f"{res.outcome.value} — {res.error}",
                )
            )
            out.retry_urls.append(costs_url)
            return breakdown, out

        text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
        if not text.strip():
            out.pages_failed += 1
            out.errors.append(f"{costs_url}: page fetched but no readable text could be extracted")
            out.page_outcomes.append(
                PageOutcome(
                    url=costs_url,
                    category="unreadable",
                    detail="page fetched but no readable text could be extracted",
                )
            )
            return breakdown, out

        # Classified for the record only: a fees page read as a navigation
        # shell still yields no figures, and the run should be able to say why.
        page = classify_page(url=costs_url, html="" if res.is_pdf else res.text, text=text)
        out.page_types.append((costs_url, page.page_type.value))
        year = _detect_year(text) or self.academic_year
        builder = ClaimBuilder(
            source_url=costs_url,
            page_title=html_title(res.text) if not res.is_pdf else "Fee schedule (PDF)",
            specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
            academic_year=year,
            official_domain=costs_url.startswith("fixture://")
            or is_official_domain(costs_url, candidate.official_domains),
            extraction_method="fixture"
            if costs_url.startswith("fixture://")
            else ("pdf_rule" if res.is_pdf else "html_rule"),
            accessed_at=res.fetched_at,
            # A fee figure's scope is usually its fee status: "home" and
            # "overseas" are different numbers on the same page.
            scope=read_scope(text, title=html_title(res.text) if not res.is_pdf else ""),
            page_text=text,
            allowed_domains=verification_domains(
                costs_url, candidate.domain, candidate.extra_domains
            ),
        )
        # As in the requirements adapter: a fee table picks the applicant's
        # year, not the first year the page prints (Delft, run 37500440224).
        builder.requested_academic_year = self.academic_year
        structured = StructuredCosts()
        if not res.is_pdf:
            document = build_document_ir(str(main_content(parse_html(res.text))), costs_url)
            structured = extract_structured_costs(document, builder, html=res.text)
        unhandled = extract_unhandled_costs(text, builder, structured.handled_types)
        claims = [*structured.claims, *unhandled]
        out.claims.extend(claims)

        breakdown.academic_year = year
        breakdown.source_urls.append(costs_url)
        # Qualified tariffs and named housing alternatives are source facts.
        # This adapter has no confirmed applicant tariff or housing selection.
        by_population = _tuition_by_population(unhandled)
        for c in unhandled:
            category = _CLAIM_TO_CATEGORY.get(c.claim_type)
            value = c.normalized_value
            if not isinstance(value, dict):
                continue
            money = Money(
                amount=value["amount"],
                currency=value["currency"],
                academic_year=year,
                source_url=costs_url,
                range_low=value.get("range_low"),
                range_high=value.get("range_high"),
            )
            if c.claim_type == ClaimType.TOTAL_COST_OF_ATTENDANCE:
                breakdown.total = money
            elif category is not None:
                breakdown.items[category] = money
            if money.range_low is not None or money.range_high is not None:
                breakdown.is_range = True
        if by_population is not None:
            low, high, currency = by_population
            # The applicant's fee population here is not inferred, so the
            # cost is the highest row — never understated — and the range
            # the page publishes stays on the figure for everything downstream.
            breakdown.items[CostCategory.TUITION] = Money(
                amount=high,
                currency=currency,
                academic_year=year,
                source_url=costs_url,
                range_low=low,
                range_high=high,
            )
            breakdown.is_range = True

        if not claims and not breakdown.items and breakdown.total is None:
            out.errors.append(f"{costs_url}: page was read but no cost figures could be extracted.")
            out.page_outcomes.append(
                PageOutcome(
                    url=costs_url,
                    category="no-pattern-match",
                    page_type=page.page_type.value,
                    readable_chars=len(text),
                    detail="page was read but no cost figures could be extracted",
                )
            )
        else:
            out.page_outcomes.append(
                PageOutcome(
                    url=costs_url,
                    category="fetched-ok",
                    page_type=page.page_type.value,
                    readable_chars=len(text),
                    detail=f"{len(claims)} cost figures read from this page",
                )
            )
        return breakdown, out


def _merge_results(into: AdapterResult, part: AdapterResult) -> None:
    into.claims.extend(part.claims)
    into.errors.extend(part.errors)
    into.pages_checked += part.pages_checked
    into.pages_failed += part.pages_failed
    into.retry_urls.extend(part.retry_urls)
    into.page_types.extend(part.page_types)
    into.page_outcomes.extend(part.page_outcomes)


def _merge_breakdowns(into: CostBreakdown, part: CostBreakdown) -> None:
    """QR-1: a later fee page fills only what the earlier ones left empty."""
    if not part.items and part.total is None:
        return
    if not into.items and into.total is None:
        into.academic_year = part.academic_year
    for category, money in part.items.items():
        into.items.setdefault(category, money)
    if into.total is None:
        into.total = part.total
    into.is_range = into.is_range or part.is_range
    into.source_urls.extend(u for u in part.source_urls if u not in into.source_urls)


def _detect_year(text: str) -> str | None:
    import re

    m = re.search(r"\b(20\d{2})\s*[/-]\s*(\d{2,4})\b", text)
    if not m:
        return None
    end = m.group(2)
    return f"{m.group(1)}/{end[-2:]}"


def _tuition_by_population(claims) -> tuple[float, float, str] | None:
    """``(lowest, highest, currency)`` when tuition is published per fee
    population with different amounts in one currency, else ``None``.

    Two currencies are not ranged here: converting to compare them is a
    judgement this adapter does not make, and the ordinary last-wins path
    keeps its behaviour.
    """
    rows = [
        c.normalized_value
        for c in claims
        if c.claim_type == ClaimType.TUITION
        and c.scope is not None
        and c.scope.population
        and c.subject_key == c.scope.population
        and isinstance(c.normalized_value, dict)
    ]
    if len(rows) < 2 or len({r["currency"] for r in rows}) != 1:
        return None
    amounts = [float(r["amount"]) for r in rows]
    if min(amounts) == max(amounts):
        return None
    return min(amounts), max(amounts), rows[0]["currency"]
