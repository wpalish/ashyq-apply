"""A source policy keeps conditional benefits without inventing entitlement."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from unittest.mock import Mock

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import ClaimBuilder, readable_text
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.scholarship.conditional_benefits import read_conditional_policy
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.claim_scope import ClaimScope
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.conflicts import find_conflicts
from app.domain.costs import compute_funding_gap
from app.domain.enums import (
    ClaimStatus,
    ClaimType,
    DegreeLevel,
    EligibilityStatus,
    SourceSpecificity,
)
from app.domain.funding import classify, roll_up_availability
from app.pipeline.runner import _applicant_eligible, _scholarship_eligibility
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim
from app.schemas.money import Money
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import CostBreakdown, Scholarship
from evaluation.research.identities import IdentityMap
from evaluation.research.mapping import normalize_subject_claims

CONDITION = (
    "The scholarship covers up to the normal programme duration on condition that the "
    "scholarship holder maintain a record of good academic performance and exemplary conduct."
)
ITEMS = [
    "Full coverage of subsidised tuition fees (after Tuition Grant).",
    "Living allowance of S$6,500 per academic year.",
    "Accommodation allowance of up to S$2,000 per academic year. "
    "(Applicable to scholarship holders who reside in NTU hostels only.)",
    "Travel grant of up to S$8,000 for an overseas programme subject to terms and conditions "
    "in the Travel Grant Form (for new cohorts from AY2025).",
]
BOND = (
    "No bond is attached to the Nanyang Global Scholarship apart from the three-year bond "
    "applicable to all Singapore PRs and international students under the MOE Tuition Grant Scheme."
)
TAIL = [
    "Computer allowance of S$2,000 (one-off).",
    BOND,
    "Enrolment into NTU’s flagship undergraduate college- NTU Honours College .",
]
URL = "https://example.edu/scholarships/nanyang"
ACCESSED = datetime(2026, 9, 29, 8, 30, 34, tzinfo=UTC)


def body(items: list[str] | None = None, *, in_table: bool = False) -> str:
    rows = [*ITEMS, *TAIL] if items is None else items
    heading = "<h3>Benefits of award</h3>"
    content = (
        f"<p>{escape(CONDITION)}</p><ul>"
        + "".join(f"<li>{escape(item)}</li>" for item in rows)
        + "</ul>"
    )
    if in_table:
        return f"<table><tr><td>{heading}</td></tr><tr><td>{content}</td></tr></table>"
    return heading + content


def page(benefits: str, *, table: str = "") -> str:
    return (
        "<html><head><title>Nanyang Global Scholarship</title></head><body><main>"
        "<h1>Nanyang Global Scholarship</h1><p>Nanyang Global Scholarship is awarded to "
        "outstanding freshmen pursuing undergraduate programmes.</p>"
        "<h3>Eligibility</h3><p>Open to all nationalities.</p>"
        "<p>Successful awardees should read a full-time undergraduate degree programme.</p>"
        + table
        + benefits
        + "<h3>Terms &amp; Conditions</h3><p>Scholarship holder is required to maintain a "
        "minimum Cumulative Grade Point Average (CGPA) of 3.5 over 5.0.</p>"
        "</main></body></html>"
    )


def read(html: str) -> tuple[Scholarship, list[Claim]]:
    fetcher = Mock(spec=Fetcher)
    award, claims = WebScholarshipAdapter(fetcher, "2026/27")._parse_award(
        Candidate("Example University", "Singapore", "Example", "example.edu"),
        CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR),
        URL,
        html,
        ACCESSED,
        classify_page(url=URL, html=html),
        0,
    )
    fetcher.get.assert_not_called()
    return award, claims


@pytest.mark.parametrize("in_table", [False, True])
def test_adapter_keeps_complete_policy_and_existing_bond_without_funding_promotion(
    in_table: bool, profile: ApplicantProfileIn
) -> None:
    html = page(body(in_table=in_table))
    award, claims = read(html)
    policies = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_COVERAGE]
    assert len(policies) == 1
    policy = policies[0]
    assert len(policy.original_text_excerpt) == 552 <= MAX_EXCERPT_CHARS
    assert is_verbatim_excerpt(policy.original_text_excerpt, readable_text(html))
    assert policy.normalized_value["conditions"] == [CONDITION]
    assert policy.normalized_value["living"] == {
        "currency": "SGD",
        "fixed_amount": 6500,
        "period": "academic_year",
    }
    assert policy.source_url == URL and policy.accessed_at == ACCESSED
    assert policy.subject_key == award.name == "Nanyang Global Scholarship"
    assert policy.program == "Computer Science" and policy.academic_year == "2026/27"
    assert policy.status is ClaimStatus.VERIFIED_CURRENT
    assert "stated by the scheme" in policy.notes
    assert "Applicant eligibility and other award terms must be checked separately" in policy.notes
    assert award.coverage == [] and award.amount is None
    assert award.amount_is_percentage_of_tuition is None
    assert classify(award).classification.value == "UNKNOWN"
    bonds = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_BOND]
    assert len(bonds) == 1 and bonds[0].original_text_excerpt == BOND
    assert bonds[0].normalized_value == {
        "years": 3,
        "basis": "MOE_Tuition_Grant",
        "population": ["Singapore_PR", "international"],
    }
    assert "bond" not in policy.normalized_value
    legacy = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_LIVING_ALLOWANCE]
    assert len(legacy) == 1
    assert legacy[0].normalized_value == {
        "currency": "SGD",
        "amount": 6500,
        "period": "academic_year",
    }
    award.eligibility_checks = _scholarship_eligibility(award, profile)
    award.applicant_eligible = _applicant_eligible(award)
    award.available_this_intake = roll_up_availability(
        opportunity_exists=award.opportunity_exists,
        applicant_eligible=award.applicant_eligible,
        application_window_open=award.application_window_open,
        award_current_for_intake=award.award_current_for_intake,
    )
    mode = [c for c in award.eligibility_checks if "full-time" in c.explanation]
    assert len(mode) == 1 and mode[0].status is EligibilityStatus.PENDING
    assert award.applicant_eligible == award.award_current_for_intake == "unknown"
    assert award.available_this_intake == "unknown"
    assert find_conflicts(claims)[0] == []


def test_adapter_suppresses_exact_responsive_duplicates() -> None:
    _, claims = read(page(body() + body()))
    policies = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_COVERAGE]
    assert len(policies) == 1
    assert len(policies[0].original_text_excerpt) == 552
    assert find_conflicts(claims)[0] == []


def test_adapter_preserves_existing_table_coverage_without_adding_conditional_policy() -> None:
    table = (
        "<table><tr><th>Cost</th><th>Status</th></tr>"
        "<tr><td>Tuition</td><td>Covered</td></tr>"
        "<tr><td>Housing</td><td>Partially covered</td></tr></table>"
    )
    award, claims = read(page(body(), table=table))
    policies = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_COVERAGE]
    assert len(policies) == 1
    assert policies[0].normalized_value == {"tuition": "yes", "housing": "partial"}
    assert [(c.category.value, c.covered) for c in award.coverage] == [
        ("tuition", "yes"),
        ("housing", "partial"),
    ]
    assert find_conflicts(claims)[0] == []


@pytest.mark.parametrize(
    "bad_policy",
    [
        body([ITEMS[0], ITEMS[1].replace("of S$6,500", "of up to S$6,500"), *ITEMS[2:]]),
        body([*ITEMS[:2], "Accommodation allowance of up to S$2,000 per academic year.", ITEMS[3]]),
        body([*ITEMS, "All above benefits are available only to domestic students."]),
        body() + body([ITEMS[0], ITEMS[1].replace("of S$6,500", "of up to S$6,500"), *ITEMS[2:]]),
    ],
)
def test_adapter_abstains_on_incomplete_ambiguous_or_qualified_policies(bad_policy: str) -> None:
    award, claims = read(page(bad_policy))
    assert not any(c.claim_type is ClaimType.SCHOLARSHIP_COVERAGE for c in claims)
    assert award.coverage == [] and award.amount is None
    assert award.amount_is_percentage_of_tuition is None
    assert classify(award).classification.value == "UNKNOWN"
    assert find_conflicts(claims)[0] == []


def policy_body(
    items: list[str] | None = None,
    condition: str = CONDITION,
    heading: str = "Benefits of award",
) -> str:
    rows = ITEMS if items is None else items
    return (
        f"<h2>{escape(heading)}</h2><p>{escape(condition)}</p><ul>"
        + "".join(f"<li>{escape(item)}</li>" for item in rows)
        + "</ul>"
    )


def policy_page(main: str, navigation: str = "") -> str:
    return (
        "<html><head><title>Example Award</title></head><body>"
        + (f"<nav>{navigation}</nav>" if navigation else "")
        + f"<main><h1>Example Award</h1>{main}</main></body></html>"
    )


def proof_builder(html: str) -> ClaimBuilder:
    return ClaimBuilder(
        source_url="https://example.edu/award",
        page_title="Example Award",
        specificity=SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
        program="Example Programme",
        academic_year="2026/27",
        official_domain=True,
        accessed_at=datetime(2026, 9, 29, tzinfo=UTC),
        scope=ClaimScope(),
        page_text=readable_text(html),
        page_type="scholarship_award",
        allowed_domains=["example.edu"],
    )


def test_source_shaped_policy_keeps_all_conditions_and_fixed_living_amount() -> None:
    html = policy_page(policy_body())
    result = read_conditional_policy(html)
    assert result is not None
    assert result.value["conditions"] == [CONDITION]
    assert result.value["tuition"] == {
        "fraction": 1.0,
        "basis": "subsidised_after_tuition_grant",
    }
    assert result.value["living"] == {
        "currency": "SGD",
        "fixed_amount": 6500,
        "period": "academic_year",
    }
    assert result.value["housing"] == {
        "currency": "SGD",
        "maximum": 2000,
        "period": "academic_year",
        "requires": "scholarship holders who reside in NTU hostels only",
    }
    assert result.value["travel"] == {
        "currency": "SGD",
        "maximum": 8000,
        "requires": "an overseas programme",
        "terms": "Travel Grant Form",
        "cohorts_from": "AY2025",
    }
    assert is_verbatim_excerpt(result.quote, readable_text(html))
    assert len(result.quote) <= 600


def test_dynamic_values_currencies_cohorts_and_institution_conditions_are_not_fixture_shortcuts() -> (
    None
):
    rows = [
        ITEMS[0].replace("Tuition Grant", "Public Study Grant"),
        ITEMS[1].replace("S$6,500", "EUR 7,250").replace("academic year", "month"),
        ITEMS[2].replace("S$2,000", "CAD 3,750").replace("NTU", "Example University"),
        ITEMS[3]
        .replace("S$8,000", "GBP 9,125")
        .replace("Travel Grant Form", "Mobility Form")
        .replace("AY2025", "AY2026"),
    ]
    result = read_conditional_policy(policy_page(policy_body(rows)))
    assert result is not None
    assert result.value["tuition"]["basis"] == "subsidised_after_public_study_grant"
    assert result.value["living"] == {
        "currency": "EUR",
        "fixed_amount": 7250,
        "period": "month",
    }
    assert result.value["housing"]["maximum"] == 3750
    assert result.value["housing"]["currency"] == "CAD"
    assert "Example University" in result.value["housing"]["requires"]
    assert result.value["travel"]["maximum"] == 9125
    assert result.value["travel"]["currency"] == "GBP"
    assert result.value["travel"]["cohorts_from"] == "AY2026"


@pytest.mark.parametrize(
    "heading",
    [
        "Examples",
        "Illustrative benefits",
        "Benefits may include",
        "Admission eligibility",
    ],
)
def test_non_policy_headings_cannot_supply_benefits(heading: str) -> None:
    assert read_conditional_policy(policy_page(policy_body(heading=heading))) is None


def test_navigation_cannot_supply_a_benefit_list() -> None:
    assert (
        read_conditional_policy(
            policy_page("<p>Contact the award office for information.</p>", policy_body())
        )
        is None
    )


@pytest.mark.parametrize(
    "condition",
    [
        "This is an example only.",
        "These benefits are optional.",
        "Benefits may be offered.",
        "Benefits are subject to change.",
    ],
)
def test_a_non_binding_context_paragraph_is_not_dropped(condition: str) -> None:
    assert read_conditional_policy(policy_page(policy_body(condition=condition))) is None


@pytest.mark.parametrize(
    "index,replacement",
    [
        (0, "Full coverage of subsidised tuition fees."),
        (1, "Living allowance of up to S$6,500 per academic year."),
        (1, "Living allowance of $6,500 per academic year."),
        (1, "Living allowance of S$6,500 or S$7,500 per academic year."),
        (1, "Living allowance of S$6,500 (2026) per academic year."),
        (1, "Living allowance of S$6,500."),
        (2, "Accommodation allowance of up to S$2,000 per academic year."),
        (2, ITEMS[2].replace("S$2,000", "S$2,00")),
        (
            2,
            ITEMS[2].replace("Accommodation allowance", "Optional accommodation allowance"),
        ),
        (3, ITEMS[3].replace(" (for new cohorts from AY2025)", "")),
        (
            3,
            ITEMS[3].replace("subject to terms and conditions in the Travel Grant Form ", ""),
        ),
    ],
)
def test_ambiguous_or_incomplete_benefit_values_abstain(index: int, replacement: str) -> None:
    rows = ITEMS.copy()
    rows[index] = replacement
    assert read_conditional_policy(policy_page(policy_body(rows))) is None


def test_overcap_complete_shared_condition_is_not_clipped() -> None:
    long_condition = CONDITION[:-1] + " " + "additional conduct condition " * 8 + "."
    assert read_conditional_policy(policy_page(policy_body(condition=long_condition))) is None


def test_responsive_identical_lists_and_items_produce_one_policy() -> None:
    single = read_conditional_policy(policy_page(policy_body()))
    repeated = read_conditional_policy(policy_page(policy_body() + policy_body()))
    duplicate_items = read_conditional_policy(
        policy_page(policy_body(ITEMS[:2] + [ITEMS[1]] + ITEMS[2:]))
    )
    assert single is not None and repeated is not None and duplicate_items is not None
    assert single.value == repeated.value == duplicate_items.value


def test_disagreeing_policy_lists_or_duplicate_category_values_abstain() -> None:
    altered = [item.replace("S$2,000", "S$3,000") for item in ITEMS]
    assert read_conditional_policy(policy_page(policy_body() + policy_body(altered))) is None
    assert read_conditional_policy(policy_page(policy_body([*ITEMS, altered[2]]))) is None


def test_existing_table_coverage_claim_prevents_a_second_policy_claim() -> None:
    html = policy_page(policy_body())
    existing = proof_builder(html).add(ClaimType.SCHOLARSHIP_COVERAGE, {"tuition": "yes"}, ITEMS[0])
    assert existing is not None
    assert read_conditional_policy(html, [existing]) is None


@pytest.mark.parametrize("condition", ["", "Applications close on 1 January."])
def test_missing_or_unrelated_shared_condition_abstains(condition: str) -> None:
    assert read_conditional_policy(policy_page(policy_body(condition=condition))) is None


def test_removed_shared_condition_abstains() -> None:
    html = policy_page(policy_body().replace(f"<p>{escape(CONDITION)}</p>", ""))
    assert read_conditional_policy(html) is None


def test_completed_sibling_section_cannot_supply_a_benefits_heading() -> None:
    policy_without_heading = policy_body().replace("<h2>Benefits of award</h2>", "")
    html = policy_page(
        "<section><h2>Benefits of award</h2><p>See another award.</p></section>"
        f"<section>{policy_without_heading}</section>"
    )
    assert read_conditional_policy(html) is None


@pytest.mark.parametrize(
    "tail",
    [
        "These benefits are optional and provided as examples only.",
        "All above benefits are available only to domestic students.",
    ],
)
def test_applicable_tail_polarity_or_scope_cannot_be_silently_dropped(
    tail: str,
) -> None:
    assert read_conditional_policy(policy_page(policy_body([*ITEMS, tail]))) is None


def test_malformed_second_benefits_policy_invalidates_otherwise_valid_policy() -> None:
    altered = ITEMS.copy()
    altered[1] = "Living allowance of up to S$6,500 per academic year."
    assert read_conditional_policy(policy_page(policy_body() + policy_body(altered))) is None


def test_independent_source_shaped_tail_statements_preserve_only_the_complete_policy() -> None:
    tails = [
        "Computer allowance of S$2,000 (one-off).",
        "No bond is attached to the Example Award apart from the three-year bond applicable "
        "to all permanent residents and international students under the Public Study Grant Scheme.",
        "Enrolment into Example University's flagship undergraduate college- Example Honours College.",
    ]
    result = read_conditional_policy(policy_page(policy_body([*ITEMS, *tails])))
    baseline = read_conditional_policy(policy_page(policy_body()))
    assert result is not None and baseline is not None
    assert result == baseline


@pytest.mark.parametrize(
    "tail",
    [
        "Computer allowance of S$2,000 (one-off). All benefits are optional.",
        "Computer allowance of S$2,000 (one-off) only for domestic students.",
        "No bond is attached to the Example Award apart from the three-year bond applicable "
        "to all permanent residents and international students under the Public Study Grant Scheme "
        "if all benefits are available only to domestic students.",
        "Enrolment into Example University's flagship undergraduate college- Example Honours College "
        "provided all benefits are available only to domestic students.",
        "Book allowance of EUR 1,500 (one-off).",
    ],
)
def test_independent_tail_grammar_never_drops_additional_conditions_or_unknown_items(
    tail: str,
) -> None:
    assert read_conditional_policy(policy_page(policy_body([*ITEMS, tail]))) is None


@pytest.mark.parametrize(
    "following",
    [
        "All above benefits are available only to domestic students.",
        "These benefits are optional and provided as examples only.",
    ],
)
def test_following_scope_paragraph_in_the_same_benefits_section_cannot_be_dropped(
    following: str,
) -> None:
    assert (
        read_conditional_policy(policy_page(policy_body() + f"<p>{escape(following)}</p>")) is None
    )


def test_following_separately_headed_section_does_not_condition_the_benefits() -> None:
    html = policy_page(
        policy_body()
        + "<h2>How to apply</h2><p>Example applications are optional for domestic students.</p>"
    )
    assert read_conditional_policy(html) is not None


def test_completed_child_section_cannot_supply_a_heading_to_the_parent_container() -> None:
    policy_without_heading = policy_body().replace("<h2>Benefits of award</h2>", "")
    html = policy_page("<section><h2>Benefits of award</h2></section>" + policy_without_heading)
    assert read_conditional_policy(html) is None


@pytest.mark.parametrize(
    "following",
    [
        "<h3>Conditions for these benefits</h3>"
        "<p>All above benefits are available only to domestic students.</p>",
        "<section><h3>More information</h3></section>"
        "<p>All above benefits are available only to domestic students.</p>",
        "<h2>Conditions for all above benefits</h2>"
        "<p>All above benefits are available only to domestic students.</p>",
    ],
)
def test_subordinate_or_nested_heading_cannot_end_the_benefits_scope(
    following: str,
) -> None:
    assert read_conditional_policy(policy_page(policy_body() + following)) is None


def test_h5_heading_between_benefits_and_policy_must_be_respected() -> None:
    html = policy_page(policy_body().replace("</h2>", "</h2><h5>Illustrative benefits</h5>"))
    assert read_conditional_policy(html) is None


def test_builder_mapper_and_domain_keep_evidence_without_coverage_or_money_projection() -> None:
    html = policy_page(policy_body())
    policy = read_conditional_policy(html)
    assert policy is not None
    proof = proof_builder(html)
    claim = proof.add(
        ClaimType.SCHOLARSHIP_COVERAGE,
        policy.value,
        policy.quote,
        subject_key="Example Award",
    )
    assert claim is not None and proof.rejected == []
    assert find_conflicts(proof.claims)[0] == []
    identities = IdentityMap.model_validate(
        {
            "version": "scratch",
            "bindings": [
                {
                    "kind": "award",
                    "source_url": "https://example.edu/award",
                    "subject": "Example Award",
                    "key": "scholarships.example",
                    "notes": "Scratch only",
                }
            ],
        }
    )
    normalized = normalize_subject_claims(
        claim.claim_type.value, claim.model_dump(mode="json"), identities
    )
    assert normalized == [
        ("unmapped.scholarship_coverage", policy.value, "Example Programme", None)
    ]
    award = Scholarship(id="scratch", name="Example Award", opportunity_exists=True)
    costs = CostBreakdown(total=Money(amount=10000, currency="SGD", academic_year="2026/27"))
    before = compute_funding_gap(costs, [award], target_currency="SGD").model_dump()
    assert (
        award.coverage == []
        and award.amount is None
        and award.amount_is_percentage_of_tuition is None
    )
    assert classify(award).classification.value == "UNKNOWN"
    assert compute_funding_gap(costs, [award], target_currency="SGD").model_dump() == before
