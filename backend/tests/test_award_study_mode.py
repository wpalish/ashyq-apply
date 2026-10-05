"""An unconfirmed study mode is a pending condition, not degree ineligibility."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from html import escape
from unittest.mock import Mock

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import readable_text
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageClassification, PageType
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.conflicts import find_conflicts
from app.domain.enums import ClaimType, DegreeLevel, EligibilityStatus
from app.domain.funding import roll_up_availability
from app.pipeline.runner import _applicant_eligible, _scholarship_eligibility
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import Scholarship

_NTU_CONDITION = "Successful awardees should read a full-time undergraduate degree programme."


def _read_study_mode_page(
    *paragraphs: str,
    navigation: str = "",
    degree: DegreeLevel = DegreeLevel.BACHELOR,
) -> tuple[Scholarship, list[Claim], str]:
    """The production parser receives public synthetic HTML; no fetch runs."""
    name = "Example Scholarship"
    deadline = (date.today() + timedelta(days=60)).strftime("%d %B %Y")
    html = (
        f"<html><head><title>{name}</title></head><body>"
        + (f"<nav>{escape(navigation)}</nav>" if navigation else "")
        + f"<main><h1>{name}</h1>"
        f"<p>{name} is awarded to outstanding freshmen pursuing undergraduate programmes.</p>"
        "<p>Open to all nationalities.</p>"
        + "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        + f"<p>The scholarship deadline is {deadline}.</p></main></body></html>"
    )
    fetcher = Mock(spec=Fetcher)
    award, claims = WebScholarshipAdapter(fetcher, "2026/27")._parse_award(
        Candidate("Example University", "Singapore", "Example", "example.edu"),
        CandidateProgram("Computer Science", "computer science", degree),
        "https://example.edu/scholarships/example",
        html,
        datetime.now(UTC),
        PageClassification(PageType.SCHOLARSHIP_AWARD, 1.0, subject=name),
        0,
    )
    fetcher.get.assert_not_called()
    return award, claims, html


def _roll_runner_eligibility(award: Scholarship, profile: ApplicantProfileIn) -> None:
    """The runner recalculates the adapter's earlier verdict from its checks."""
    award.eligibility_checks = _scholarship_eligibility(award, profile)
    award.applicant_eligible = _applicant_eligible(award)
    award.available_this_intake = roll_up_availability(
        opportunity_exists=award.opportunity_exists,
        applicant_eligible=award.applicant_eligible,
        application_window_open=award.application_window_open,
        award_current_for_intake=award.award_current_for_intake,
    )


@pytest.mark.parametrize(
    "condition",
    [
        _NTU_CONDITION,
        "Successful awardees should read a full-time\nundergraduate degree programme.",
    ],
)
def test_a_full_time_only_award_keeps_eligibility_pending_without_study_mode_confirmation(
    condition: str, profile: ApplicantProfileIn
) -> None:
    """NTU's exact condition cannot be settled by finding the word undergraduate."""
    award, claims, html = _read_study_mode_page(condition)

    assert award.degree_applicability == "yes"
    assert award.international_eligible == "yes"
    assert award.application_window_open == "yes"
    assert any("full-time" in restriction for restriction in award.program_restrictions)
    assert award.applicant_eligible == "unknown"
    assert award.available_this_intake == "unknown"

    _roll_runner_eligibility(award, profile)

    mode_checks = [check for check in award.eligibility_checks if "full-time" in check.explanation]
    assert len(mode_checks) == 1
    assert mode_checks[0].status is EligibilityStatus.PENDING
    assert award.applicant_eligible == "unknown"
    assert award.available_this_intake == "unknown"
    # One level claim carries the condition's own proof. A second restriction
    # claim under the same award would be mistaken for contradictory evidence.
    restriction_claims = [
        claim for claim in claims if claim.claim_type is ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION
    ]
    assert len(restriction_claims) == 1
    assert restriction_claims[0].normalized_value == {"degree": "bachelor", "applies": "yes"}
    assert " ".join(restriction_claims[0].original_text_excerpt.split()) == " ".join(
        condition.split()
    )
    assert is_verbatim_excerpt(restriction_claims[0].original_text_excerpt, readable_text(html))
    assert find_conflicts(claims)[0] == []


@pytest.mark.parametrize(
    "non_requirement",
    [
        "We offer full-time undergraduate degree programmes.",
        "Successful awardees may read a full-time undergraduate degree programme.",
        "Successful awardees are not required to read a full-time undergraduate degree programme.",
        "If successful awardees should read a full-time undergraduate degree programme, ask us.",
        (
            "It is not required that successful awardees should read a full-time "
            "undergraduate degree programme."
        ),
        (
            "There is no requirement that successful awardees should read a full-time "
            "undergraduate degree programme."
        ),
    ],
)
def test_full_time_description_or_optional_prose_does_not_invent_a_restriction(
    non_requirement: str, profile: ApplicantProfileIn
) -> None:
    award, _, _ = _read_study_mode_page(non_requirement)

    assert award.program_restrictions == []
    assert award.applicant_eligible == "yes"
    _roll_runner_eligibility(award, profile)
    assert award.applicant_eligible == "yes"
    assert award.available_this_intake == "yes"
    assert not any(check.status is EligibilityStatus.PENDING for check in award.eligibility_checks)


def test_a_full_time_rule_in_site_navigation_does_not_restrict_the_award(
    profile: ApplicantProfileIn,
) -> None:
    award, _, _ = _read_study_mode_page(navigation=_NTU_CONDITION)

    assert award.program_restrictions == []
    _roll_runner_eligibility(award, profile)
    assert award.applicant_eligible == "yes"


def test_study_mode_does_not_overwrite_an_existing_named_programme_restriction(
    profile: ApplicantProfileIn,
) -> None:
    award, _, _ = _read_study_mode_page(
        "Restricted to applicants enrolled in the BSc Data Science programme.", _NTU_CONDITION
    )

    assert any("BSc Data Science" in restriction for restriction in award.program_restrictions)
    assert any("full-time" in restriction for restriction in award.program_restrictions)
    _roll_runner_eligibility(award, profile)
    assert award.applicant_eligible == "unknown"
    assert sum(check.status is EligibilityStatus.PENDING for check in award.eligibility_checks) == 2


def test_a_different_degree_keeps_its_original_applicability_proof() -> None:
    award, claims, _ = _read_study_mode_page(_NTU_CONDITION, degree=DegreeLevel.MASTER)

    assert award.degree_applicability == "no"
    degree_claims = [
        claim
        for claim in claims
        if claim.claim_type is ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION
        and claim.normalized_value == {"degree": "master", "applies": "no"}
    ]
    assert len(degree_claims) == 1
    assert "awarded to outstanding freshmen pursuing undergraduate programmes" in (
        degree_claims[0].original_text_excerpt
    )
    assert "full-time" not in degree_claims[0].original_text_excerpt
