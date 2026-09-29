"""Source-shaped NTU submission rules retain their complete conditions."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from unittest.mock import Mock

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import readable_text
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.conflicts import find_conflicts
from app.domain.enums import ApplicationMode, ClaimStatus, ClaimType, DegreeLevel
from app.domain.funding import classify
from app.schemas.claim import Claim
from app.schemas.result import Scholarship

_ORDER = (
    "Applicants are required to submit their application for admission before submitting "
    "their application for scholarship."
)
_ESSAY = (
    "As part of completing the form, a Personal Essay of not more than 250 words is required. "
    "The scholarship application form includes 1 compulsory topic for you to write on."
)
_BOND = (
    "No bond is attached to the Nanyang Global Scholarship apart from the three-year bond "
    "applicable to all Singapore PRs and international students under the MOE Tuition Grant Scheme."
)
_URL = "https://example.edu/scholarships/nanyang"
_ACCESSED = datetime(2026, 9, 29, 8, 30, 34, tzinfo=UTC)


def _read(*paragraphs: str, navigation: str = "") -> tuple[Scholarship, list[Claim], str]:
    html = (
        "<html><head><title>Nanyang Global Scholarship</title></head><body>"
        + (f"<nav>{escape(navigation)}</nav>" if navigation else "")
        + "<main><h1>Nanyang Global Scholarship</h1>"
        "<p>Nanyang Global Scholarship is awarded to outstanding freshmen "
        "pursuing undergraduate programmes.</p><p>Open to all nationalities.</p>"
        "<p>Successful awardees should read a full-time undergraduate degree programme.</p>"
        "<h2>Application Procedures</h2>"
        + "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        + "</main></body></html>"
    )
    fetcher = Mock(spec=Fetcher)
    award, claims = WebScholarshipAdapter(fetcher, "2026/27")._parse_award(
        Candidate("Example University", "Singapore", "Example", "example.edu"),
        CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR),
        _URL,
        html,
        _ACCESSED,
        classify_page(url=_URL, html=html),
        0,
    )
    fetcher.get.assert_not_called()
    return award, claims, html


def _proof(claim: Claim, quote: str, html: str) -> None:
    assert claim.original_text_excerpt == quote
    assert len(claim.original_text_excerpt) <= 600
    assert is_verbatim_excerpt(claim.original_text_excerpt, readable_text(html))
    assert claim.status is ClaimStatus.VERIFIED_CURRENT
    assert claim.source_url == _URL
    assert claim.subject_key == "Nanyang Global Scholarship"
    assert claim.academic_year == "2026/27"
    assert claim.accessed_at == _ACCESSED


@pytest.mark.parametrize(
    "order", [_ORDER, _ORDER.replace("before submitting", "before\nsubmitting")]
)
def test_admission_application_first_is_a_separate_application_without_an_offer_inference(
    order: str,
) -> None:
    award, claims, html = _read(order)

    assert award.application_mode is ApplicationMode.SEPARATE
    assert award.offer_required == "unknown"
    mode = [claim for claim in claims if claim.claim_type is ClaimType.SCHOLARSHIP_APPLICATION_MODE]
    assert len(mode) == 1
    assert mode[0].normalized_value == ApplicationMode.SEPARATE.value
    _proof(mode[0], " ".join(order.split()), html)
    assert "admission application" in mode[0].notes.lower()
    assert "before" in mode[0].notes.lower()
    assert not any(claim.claim_type is ClaimType.SCHOLARSHIP_OFFER_REQUIRED for claim in claims)


def test_the_required_ntu_personal_essay_sets_the_extra_essay_flag() -> None:
    award, _, _ = _read(_ESSAY)

    assert award.requires_extra_essays is True


@pytest.mark.parametrize(
    "essay",
    [
        "A Personal Essay of not more than 250 words is optional.",
        "A Personal Essay of not more than 250 words is not required.",
        "Guidance on the Personal Essay of not more than 250 words is available online.",
        "A statement of motivation is optional.",
    ],
)
def test_optional_denied_or_context_only_essays_do_not_become_required(essay: str) -> None:
    award, _, _ = _read(essay)

    assert award.requires_extra_essays is False


@pytest.mark.parametrize(
    "essay",
    [
        "A Personal Essay is required if shortlisted.",
        "A Personal Essay is required when invited by the scholarship committee.",
        "A Personal Essay is required unless an approved writing sample was submitted.",
        "Applicants must submit the scholarship form; if shortlisted, a Personal Essay is required.",
        "A Personal Essay must not be submitted.",
        "No mandatory Personal Essay is required.",
        "No Personal Essay is mandatory for the scholarship application.",
    ],
)
def test_conditional_or_prohibited_essay_does_not_set_an_unconditional_requirement(
    essay: str,
) -> None:
    award, _, _ = _read(essay)

    assert award.requires_extra_essays is False


def test_actual_tuition_grant_exception_is_kept_with_the_no_award_bond_clause() -> None:
    award, claims, html = _read(_BOND)

    bonds = [claim for claim in claims if claim.claim_type is ClaimType.SCHOLARSHIP_BOND]
    assert len(bonds) == 1
    assert bonds[0].normalized_value == {
        "years": 3,
        "basis": "MOE_Tuition_Grant",
        "population": ["Singapore_PR", "international"],
    }
    _proof(bonds[0], _BOND, html)
    assert bonds[0].scope is not None
    assert bonds[0].scope.population == "Singapore PRs and international students"
    assert award.applicant_eligible == "unknown"
    assert find_conflicts(claims)[0] == []


def test_submission_rules_in_navigation_cannot_supply_award_requirements() -> None:
    award, claims, _ = _read(navigation=" ".join([_ORDER, _ESSAY, _BOND]))

    assert award.application_mode is ApplicationMode.UNKNOWN
    assert award.requires_extra_essays is False
    assert not any(claim.claim_type is ClaimType.SCHOLARSHIP_BOND for claim in claims)


def test_a_conditional_order_does_not_establish_a_required_separate_application() -> None:
    order = "If " + _ORDER[0].lower() + _ORDER[1:-1] + ", contact admissions."
    award, claims, _ = _read(order)

    assert award.application_mode is ApplicationMode.UNKNOWN
    assert not any(claim.claim_type is ClaimType.SCHOLARSHIP_APPLICATION_MODE for claim in claims)


@pytest.mark.parametrize(
    "condition",
    [
        "if shortlisted",
        "when invited by the scholarship committee",
        "unless exempted by the scholarship committee",
        "; if shortlisted, follow these procedures",
    ],
)
def test_a_trailing_conditional_order_does_not_establish_a_required_separate_application(
    condition: str,
) -> None:
    award, claims, _ = _read(_ORDER[:-1] + " " + condition + ".")

    assert award.application_mode is ApplicationMode.UNKNOWN
    assert not any(claim.claim_type is ClaimType.SCHOLARSHIP_APPLICATION_MODE for claim in claims)


def test_an_overlong_exception_clause_is_not_truncated_into_no_bond() -> None:
    clause = _BOND.replace(
        "apart from", ", ".join(["with administrative context"] * 25) + " apart from"
    )
    assert len(clause) > 600
    _, claims, _ = _read(clause)

    assert not any(claim.claim_type is ClaimType.SCHOLARSHIP_BOND for claim in claims)


def test_new_submission_facts_do_not_promote_conditional_funding_or_future_availability() -> None:
    award, claims, _ = _read(
        _ORDER,
        _ESSAY,
        _BOND,
        "Full coverage of subsidised tuition fees (after Tuition Grant).",
        "Accommodation allowance of up to S$2,000 per academic year. "
        "(Applicable to scholarship holders who reside in NTU hostels only.)",
        "Travel grant of up to S$8,000 for an overseas programme subject to terms and conditions "
        "in the Travel Grant Form (for new cohorts from AY2025).",
    )

    assert award.application_mode is ApplicationMode.SEPARATE
    assert award.requires_extra_essays is True
    assert award.applicant_eligible == "unknown"
    assert award.award_current_for_intake == "unknown"
    assert award.available_this_intake == "unknown"
    assert award.coverage == []
    assert award.amount is None
    assert award.amount_is_percentage_of_tuition is None
    assert classify(award).classification.value == "UNKNOWN"
    assert find_conflicts(claims)[0] == []
