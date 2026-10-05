"""Published tariff evidence does not answer an applicant's projected cost."""

from __future__ import annotations

import pytest

from app.domain.enums import ClaimStatus, ClaimType, CostCategory
from app.pipeline.runner import _completeness
from app.schemas.money import Money
from app.schemas.result import CostBreakdown
from tests.conftest import make_claim
from tests.test_structured_cost_scopes import _FEES, _HOUSING, _fetch, _html


@pytest.mark.asyncio
async def test_actual_shaped_hku_tariffs_do_not_answer_unprojected_applicant_cost():
    costs, out = await _fetch(_html(_FEES + _HOUSING))

    assert len(out.claims) == 6
    assert sum(claim.claim_type is ClaimType.TUITION for claim in out.claims) == 4
    assert not costs.items and costs.total is None
    # Omitting a projection must fail closed too: these are source tariffs.
    assert _completeness(out.claims) == 0.0
    assert _completeness(out.claims, costs=costs) == 0.0


@pytest.mark.parametrize("status", [ClaimStatus.VERIFIED_CURRENT, ClaimStatus.POSSIBLY_STALE])
@pytest.mark.parametrize("kind", [ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE])
def test_matching_applicant_projection_and_accepted_evidence_answer_cost(kind, status):
    value = {"amount": 20000, "currency": "EUR"}
    claim = make_claim(kind.value, value, status=status.value)
    money = Money(**value)
    costs = (
        CostBreakdown(items={CostCategory.TUITION: money})
        if kind is ClaimType.TUITION
        else CostBreakdown(total=money)
    )

    assert _completeness([claim], costs=costs) == 0.167


@pytest.mark.parametrize("kind", [ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE])
def test_unrelated_projection_does_not_answer_the_cost_evidence(kind):
    value = {"amount": 20000, "currency": "EUR"}
    claim = make_claim(kind.value, value)
    money = Money(**value)
    wrong_projection = (
        CostBreakdown(total=money)
        if kind is ClaimType.TUITION
        else CostBreakdown(items={CostCategory.TUITION: money})
    )

    assert _completeness([claim], costs=wrong_projection) == 0.0
    assert _completeness([claim], costs=CostBreakdown(items={CostCategory.BOOKS: money})) == 0.0


@pytest.mark.parametrize("kind", [ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE])
@pytest.mark.parametrize(
    "amount,currency,academic_year",
    [(25000, "EUR", "2027/28"), (20000, "USD", "2027/28"), (20000, "EUR", "2028/29")],
)
def test_a_different_projected_tariff_does_not_answer_cost(kind, amount, currency, academic_year):
    claim = make_claim(kind.value, {"amount": 20000, "currency": "EUR"}, academic_year="2027/28")
    money = Money(amount=amount, currency=currency, academic_year=academic_year)
    costs = (
        CostBreakdown(items={CostCategory.TUITION: money})
        if kind is ClaimType.TUITION
        else CostBreakdown(total=money)
    )

    assert _completeness([claim], costs=costs) == 0.0


def test_population_range_upper_tariff_remains_a_cost_answer():
    claims = [
        make_claim("tuition", {"amount": 10000, "currency": "EUR"}, academic_year="2027/28"),
        make_claim("tuition", {"amount": 20000, "currency": "EUR"}, academic_year="2027/28"),
    ]
    costs = CostBreakdown(
        items={
            CostCategory.TUITION: Money(
                amount=20000,
                currency="EUR",
                academic_year="2027/28",
                range_low=10000,
                range_high=20000,
                is_estimate=True,
            )
        },
        is_range=True,
    )

    assert _completeness(claims, costs=costs) == 0.167


@pytest.mark.parametrize(
    "status",
    [ClaimStatus.UNVERIFIED, ClaimStatus.CONFLICTING, ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION],
)
def test_projection_does_not_upgrade_unsettled_cost_evidence(status):
    value = {"amount": 20000, "currency": "EUR"}
    claim = make_claim(ClaimType.TUITION.value, value, status=status.value)
    costs = CostBreakdown(items={CostCategory.TUITION: Money(**value)})

    assert _completeness([claim], costs=costs) == 0.0
    assert _completeness([], costs=costs) == 0.0


def test_unprojected_cost_does_not_change_other_core_questions():
    claims = [
        make_claim("ielts_min_overall", 6.5),
        make_claim("min_gpa", 3.0),
        make_claim("admission_deadline", "2027-01-15"),
        make_claim("scholarship_exists", "Talent Grant"),
        make_claim("scholarship_international_eligible", True),
        make_claim("tuition", {"amount": 20000, "currency": "EUR"}),
    ]

    assert _completeness(claims) == 0.833
    assert _completeness(claims, costs=CostBreakdown()) == 0.833
    costs = CostBreakdown(items={CostCategory.TUITION: Money(amount=20000, currency="EUR")})
    assert _completeness(claims, costs=costs) == 1.0


@pytest.mark.asyncio
async def test_legacy_projected_fee_keeps_its_cost_answer():
    costs, out = await _fetch(_html("<p>Tuition fee: HKD50,000 per year.</p>"))

    assert costs.items[CostCategory.TUITION].amount == 50000
    assert any(claim.claim_type is ClaimType.TUITION for claim in out.claims)
    assert _completeness(out.claims, costs=costs) == 0.167
