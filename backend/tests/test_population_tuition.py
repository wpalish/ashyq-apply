"""Tuition published per fee population (V2-32).

A European fee page lists the statutory EU/EEA fee beside the institutional
non-EU/EEA fee — often several times higher. The first-match reading quoted
whichever came first to everybody, so an international applicant could be
shown the domestic figure and a funding gap several times too small.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.base import Candidate
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.extraction import ClaimBuilder, extract_costs
from app.adapters.fetching import Fetcher
from app.domain.enums import CostCategory

_PER_POPULATION = (
    "Tuition fees 2026-2027 EU/EEA students € 2,601 per year non-EU/EEA students € 20,000 per year"
)


def _tuition(text: str) -> list[tuple[float, str | None]]:
    builder = ClaimBuilder(
        source_url="https://www.example.edu/fees",
        official_domain=True,
        accessed_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    extract_costs(text, builder)
    return [
        (c.normalized_value["amount"], c.scope.population if c.scope else None)
        for c in builder.claims
        if c.claim_type.value == "tuition"
    ]


class TestReadingTheTable:
    def test_each_population_keeps_its_own_fee(self):
        assert _tuition(_PER_POPULATION) == [(2601.0, "EU/EEA"), (20000.0, "non-EU/EEA")]

    def test_one_fee_for_everybody_keeps_the_ordinary_reading(self):
        assert _tuition("Tuition fee: €15,000 per year for all students.") == [(15000.0, None)]

    def test_one_population_row_is_not_a_table(self):
        assert _tuition("Tuition fee: EU/EEA students €2,601") == [(2601.0, None)]


@pytest.mark.asyncio
async def test_the_cost_is_the_highest_row_and_the_range_is_kept(settings, tmp_path: Path):
    root = tmp_path / "site"
    (root / "uni").mkdir(parents=True)
    (root / "uni/fees.html").write_text(
        f"<html><head><title>Tuition fees</title></head><body><main>"
        f"<h1>Tuition fees</h1><p>{_PER_POPULATION}</p></main></body></html>",
        encoding="utf-8",
    )
    candidate = Candidate(
        name="Example University",
        country="Netherlands",
        city="Groningen",
        costs_url="fixture://uni/fees.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as fetcher:
        breakdown, _ = await WebCostAdapter(fetcher, "2026/27").fetch(candidate)

    tuition = breakdown.items[CostCategory.TUITION]
    assert tuition.amount == 20000.0
    assert (tuition.range_low, tuition.range_high) == (2601.0, 20000.0)
    assert breakdown.is_range is True
