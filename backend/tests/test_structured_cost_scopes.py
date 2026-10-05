"""Qualified source tariffs and housing options do not select applicant costs."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.base import Candidate
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import ClaimBuilder, extract_costs, readable_text
from app.adapters.fetching import Fetcher, FetchResult
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType, CostCategory, FetchOutcome, SourceSpecificity

_URL = "https://admissions.hku.hk/fees-and-scholarships/fees"
_ACCESSED = datetime(2026, 9, 29, tzinfo=UTC)
_LOCAL = "Local Students Eligible for Government Subsidised Tuition Fees"
_OTHER = "Local Students not Eligible for Government Subsidised Tuition Fees and Non-Local Students"
_FEES = f"""
<h2>Annual Tuition Fee for {_LOCAL} in 2027/28 Academic Year</h2>
<table><tr><th>For all programmes</th><td>HK$ 49,500</td></tr></table>
<h2>Annual Tuition Fees for {_OTHER} in 2027/28 Academic Year</h2>
<table>
<tr><th>For STEM Faculties and Schools</th><td>HK$ 280,000
Faculties of Engineering, Medicine (except MBBS), and Science;
and Schools of Computing and Data Science and Innovation.</td></tr>
<tr><th>For Non-STEM Faculties and Schools</th><td>HK$ 250,000
Faculties of Architecture, Arts, Education, Law, and Social Sciences.</td></tr>
<tr><th>For the Bachelor of Medicine and Bachelor of Surgery (MBBS)
and the Bachelor of Dental Surgery (BDS)</th><td>HK$ 590,000</td></tr>
</table>
"""
_HALL = """<div class="option"><div>Residential halls and colleges</div>
<p>HKD17,290 to HKD37,940 per year.
This includes 285 residential days and excludes the summer semester.</p></div>"""
_OFF_CAMPUS = """<div class="option"><div>Off-campus housing</div>
<p>HKD30,000 to HKD50,000 per year. Depending on the housing type and district.</p></div>"""
_HOUSING = "<h2>Cost of Living</h2>" + _HALL + _OFF_CAMPUS


def _html(body: str) -> str:
    return "<html><head><title>Fees</title></head><body><main>" + body + "</main></body></html>"


def _builder(html: str) -> ClaimBuilder:
    return ClaimBuilder(
        source_url=_URL,
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        academic_year="2030/31",
        accessed_at=_ACCESSED,
        official_domain=True,
        scope=ClaimScope(population="international", academic_year="2030/31"),
        page_text=readable_text(html),
        allowed_domains=("hku.hk",),
    )


async def _fetch(html: str):
    fetcher = Mock(spec=Fetcher)
    fetcher.get = AsyncMock(
        return_value=FetchResult(
            url=_URL,
            outcome=FetchOutcome.OK,
            text=html,
            content=html.encode(),
            content_type="text/html",
            fetched_at=_ACCESSED,
        )
    )
    result = await WebCostAdapter(fetcher, "2030/31").fetch(
        Candidate(
            name="HKU", country="Hong Kong", city="Hong Kong", domain="hku.hk", costs_url=_URL
        )
    )
    fetcher.get.assert_awaited_once_with(_URL)
    return result


@pytest.mark.asyncio
async def test_qualified_tariffs_and_housing_are_read_without_selecting_applicant_costs():
    html = _html(
        "<h1>Tuition And Living Expenses</h1>"
        "<p>HKU has non-hall housing near the University. Here is a snapshot.</p>"
        + _FEES
        + _HOUSING
    )
    breakdown, out = await _fetch(html)

    assert len(out.claims) == 6
    tuition = [claim for claim in out.claims if claim.claim_type is ClaimType.TUITION]
    assert sorted(claim.normalized_value["amount"] for claim in tuition) == [
        49500,
        250000,
        280000,
        590000,
    ]
    assert {claim.scope.population for claim in tuition} == {_LOCAL, _OTHER}
    assert all(claim.scope.academic_year == "2027/28" for claim in tuition)
    assert all(claim.academic_year == "2027/28" for claim in tuition)
    assert len({claim.subject_key for claim in tuition}) == 4
    by_amount = {claim.normalized_value["amount"]: claim for claim in tuition}
    assert by_amount[280000].scope.faculty == "STEM Faculties and Schools"
    assert by_amount[250000].scope.faculty == "Non-STEM Faculties and Schools"
    assert "MBBS" in by_amount[590000].scope.programme
    assert "Academic Year" in by_amount[590000].relevant_section
    assert all(claim.scope.nationality is None for claim in tuition)
    assert all(claim.scope.residency is None for claim in tuition)
    assert all(claim.accessed_at == _ACCESSED for claim in out.claims)
    assert all(0 < len(claim.original_text_excerpt) <= 600 for claim in out.claims)
    assert all(
        " ".join(claim.original_text_excerpt.split()) in " ".join(readable_text(html).split())
        for claim in out.claims
    )
    assert breakdown.items == {} and breakdown.total is None
    assert out.page_outcomes[0].category == "fetched-ok"
    assert "6 cost figures" in out.page_outcomes[0].detail
    assert not any("no cost figures" in error for error in out.errors)


@pytest.mark.asyncio
async def test_qualified_price_cannot_fall_through_as_an_unscoped_arithmetic_fee():
    html = _html(_FEES + "<p>Tuition fee: HK$ 590,000.</p>")
    breakdown, out = await _fetch(html)

    assert len(out.claims) == 4
    assert all(claim.subject_key and claim.scope.population for claim in out.claims)
    assert CostCategory.TUITION not in breakdown.items
    assert breakdown.total is None


@pytest.mark.asyncio
async def test_unselected_housing_range_retains_upper_amount_and_period_without_cost_math():
    breakdown, out = await _fetch(_html(_HOUSING))

    assert len(out.claims) == 2
    by_option = {claim.subject_key: claim for claim in out.claims}
    assert by_option["Off-campus housing"].normalized_value == {
        "amount": 50000,
        "currency": "HKD",
        "range_low": 30000,
        "range_high": 50000,
    }
    hall = by_option["Residential halls and colleges"]
    assert hall.normalized_value["amount"] == 37940
    assert "285 residential days" in hall.original_text_excerpt
    assert "excludes the summer semester" in hall.original_text_excerpt
    assert all(claim.scope.population is None for claim in out.claims)
    assert all(claim.scope.academic_year is None for claim in out.claims)
    assert all(claim.academic_year is None for claim in out.claims)
    assert breakdown.items == {} and breakdown.total is None


@pytest.mark.asyncio
async def test_legacy_unhandled_categories_still_read_beside_qualified_prices():
    breakdown, out = await _fetch(_html(_FEES + _HOUSING + "<p>Books: HKD2,000 per year.</p>"))

    assert len(out.claims) == 7
    assert set(breakdown.items) == {CostCategory.BOOKS}
    assert breakdown.items[CostCategory.BOOKS].amount == 2000
    assert breakdown.items[CostCategory.BOOKS].currency == "HKD"
    assert breakdown.total is None


@pytest.mark.parametrize(
    "value",
    [
        "HKD50,000 to HKD30,000 per year.",
        "HKD30,000 to USD50,000 per year.",
        "HKD30,000 to HKD50,000 per month.",
        "HKD30,000 and HKD50,000 per year.",
    ],
)
@pytest.mark.asyncio
async def test_ambiguous_or_nonannual_option_does_not_become_a_point_cost(value):
    html = _html(f"<div><div>Off-campus housing</div><p>{value}</p></div>")
    breakdown, out = await _fetch(html)

    assert not out.claims
    assert breakdown.items == {} and breakdown.total is None


@pytest.mark.asyncio
async def test_full_local_proof_over_cap_does_not_leave_an_amount_after_clipping():
    long_option = _OFF_CAMPUS.replace(
        "Depending on the housing type and district.",
        "Depending on the housing type and district. " + "Full option conditions. " * 40,
    )
    breakdown, out = await _fetch(_html(long_option))

    assert not out.claims
    assert breakdown.items == {} and breakdown.total is None


def test_structural_reader_restores_page_metadata_and_uses_local_fee_year():
    from app.adapters.structured_costs import extract_structured_costs

    html = _html("<h1>Academic Year 2025/26</h1>" + _FEES + _HOUSING)
    builder = _builder(html)
    before = dict(builder.meta)
    read = extract_structured_costs(build_document_ir(html, _URL), builder, html=html)

    assert len(read.claims) == 6
    assert builder.meta == before
    assert {
        claim.academic_year for claim in read.claims if claim.claim_type is ClaimType.TUITION
    } == {"2027/28"}
    # Housing's own section states no year; the page's unrelated date is not copied.
    assert all(
        claim.academic_year is None
        for claim in read.claims
        if claim.claim_type is ClaimType.HOUSING_COST
    )


def test_legacy_reader_is_byte_identical_when_no_category_is_structurally_handled():
    from app.adapters.structured_costs import extract_structured_costs, extract_unhandled_costs

    html = _html("<p>Tuition fee: HKD50,000 per year.</p><p>Books: HKD2,000.</p>")
    builder = _builder(html)
    control = _builder(html)
    read = extract_structured_costs(build_document_ir(html, _URL), builder, html=html)

    assert not read.handled_types and not read.claims
    actual = extract_unhandled_costs(readable_text(html), builder, read.handled_types)
    expected = extract_costs(readable_text(html), control)
    assert [claim.model_dump_json() for claim in actual] == [
        claim.model_dump_json() for claim in expected
    ]


@pytest.mark.asyncio
async def test_navigation_tariff_table_is_not_source_cost_evidence():
    html = _html("<h1>Fees</h1><p>There are no published price figures in this content.</p>")
    html = html.replace("<main>", "<nav>" + _FEES + "</nav><main>")
    breakdown, out = await _fetch(html)

    assert not out.claims
    assert breakdown.items == {} and breakdown.total is None


@pytest.mark.asyncio
@pytest.mark.parametrize("second_option", ["Off-campus housing", "On-campus housing"])
async def test_identical_housing_prices_keep_their_own_dom_heading_year(second_option):
    price = "HKD30,000 to HKD50,000 per year."
    html = _html(
        "<h2>Housing in 2027/28 Academic Year</h2>"
        f"<div><div>On-campus housing</div><p>{price}</p></div>"
        "<h2>Housing in 2028/29 Academic Year</h2>"
        f"<div><div>{second_option}</div><p>{price}</p></div>"
    )
    breakdown, out = await _fetch(html)

    assert len(out.claims) == 2
    by_year = {claim.scope.academic_year: claim for claim in out.claims}
    assert by_year["2027/28"].subject_key == "On-campus housing"
    assert by_year["2028/29"].subject_key == second_option
    assert by_year["2027/28"].relevant_section == "Housing in 2027/28 Academic Year"
    assert by_year["2028/29"].relevant_section == "Housing in 2028/29 Academic Year"
    assert breakdown.items == {} and breakdown.total is None
