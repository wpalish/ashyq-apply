"""Cost of attendance from an official fees page (HTML or PDF)."""

from __future__ import annotations

from app.adapters.base import AdapterResult, Candidate
from app.adapters.extraction import (
    ClaimBuilder,
    extract_costs,
    html_title,
    is_official_domain,
    pdf_to_text,
    readable_text,
)
from app.adapters.fetching import Fetcher
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
        out = AdapterResult()
        breakdown = CostBreakdown(academic_year=self.academic_year)
        if not candidate.costs_url:
            out.errors.append(f"No official cost page is known for {candidate.name}.")
            return breakdown, out

        res = await self.fetcher.get(candidate.costs_url)
        out.pages_checked += 1
        if not res.ok:
            out.pages_failed += 1
            out.errors.append(f"{candidate.costs_url}: {res.outcome.value} — {res.error}")
            out.retry_urls.append(candidate.costs_url)
            return breakdown, out

        text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
        year = _detect_year(text) or self.academic_year
        builder = ClaimBuilder(
            source_url=candidate.costs_url,
            page_title=html_title(res.text) if not res.is_pdf else "Fee schedule (PDF)",
            specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
            academic_year=year,
            official_domain=candidate.costs_url.startswith("fixture://")
            or is_official_domain(candidate.costs_url, [candidate.domain]),
            extraction_method="fixture" if candidate.costs_url.startswith("fixture://") else (
                "pdf_rule" if res.is_pdf else "html_rule"
            ),
            accessed_at=res.fetched_at,
        )
        claims = extract_costs(text, builder)
        out.claims.extend(claims)

        breakdown.academic_year = year
        breakdown.source_urls.append(candidate.costs_url)
        for c in claims:
            category = _CLAIM_TO_CATEGORY.get(c.claim_type)
            value = c.normalized_value
            if not isinstance(value, dict):
                continue
            money = Money(
                amount=value["amount"],
                currency=value["currency"],
                academic_year=year,
                source_url=candidate.costs_url,
            )
            if c.claim_type == ClaimType.TOTAL_COST_OF_ATTENDANCE:
                breakdown.total = money
            elif category is not None:
                breakdown.items[category] = money

        if not breakdown.items and breakdown.total is None:
            out.errors.append(
                f"{candidate.costs_url}: page was read but no cost figures could be extracted."
            )
        return breakdown, out


def _detect_year(text: str) -> str | None:
    import re

    m = re.search(r"\b(20\d{2})\s*[/-]\s*(\d{2,4})\b", text)
    if not m:
        return None
    end = m.group(2)
    return f"{m.group(1)}/{end[-2:]}"
