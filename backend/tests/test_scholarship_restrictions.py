"""Nationality, residency and award-count extraction from real award pages.

`docs/CANARY_AUDIT.md` recorded this as a known recall gap: the CLIP award page
says the scholarships go to students who "hold either a Greek passport or Greek
residence", and the system read none of it. A Kazakhstani applicant was shown
an award they cannot hold.

The rule these tests protect: an award existing and an applicant being able to
hold it are two different claims, and the second one must be answered from the
page's own words or left unknown.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.adapters.extraction import html_to_text
from app.adapters.page_classifier import main_content
from app.adapters.scholarship.restrictions import (
    assess_applicant_eligibility,
    extract_published_count,
    extract_restrictions,
)

FIXTURES = Path(__file__).parent / "fixtures" / "pages"


def page_text(stem: str) -> str:
    html = (FIXTURES / f"{stem}.html").read_text()
    return html_to_text(str(main_content(BeautifulSoup(html, "lxml"))))


class TestNationalityAndResidency:
    def test_the_clip_award_is_restricted_to_greece(self):
        """"...hold either a Greek passport or Greek residence"."""
        found = extract_restrictions(page_text("clip-scholarship"))
        assert "Greece" in found.citizenships
        assert "Greece" in found.residencies
        assert "greek passport" in found.evidence.lower()

    def test_the_excerpt_proves_the_restriction(self):
        found = extract_restrictions(page_text("clip-scholarship"))
        assert found.evidence in page_text("clip-scholarship"), (
            "the excerpt must be verbatim from the page"
        )

    def test_an_unrestricted_award_reports_no_restriction(self):
        """The van Effen award restricts by degree, not by nationality."""
        found = extract_restrictions(page_text("delft-vaneffen"))
        assert found.citizenships == []

    @pytest.mark.parametrize("text,country", [
        ("Applicants must hold a Greek passport.", "Greece"),
        ("Open to citizens of Kazakhstan only.", "Kazakhstan"),
        ("The award is restricted to Turkish nationals.", "Turkey"),
        ("Applicants must be nationals of India.", "India"),
        ("Only students with German citizenship may apply.", "Germany"),
    ])
    def test_common_phrasings_are_recognised(self, text, country):
        assert country in extract_restrictions(text).citizenships

    @pytest.mark.parametrize("text", [
        "The programme welcomes students from all over the world.",
        "Our international students come from over 100 countries.",
        "Greek mythology is taught in the first year.",
        "The Dutch government funds part of this programme.",
    ])
    def test_a_country_mentioned_in_passing_is_not_a_restriction(self, text):
        """A nationality word is not a rule. Restriction needs restricting
        language beside it, or the extractor invents barriers."""
        assert extract_restrictions(text).citizenships == []


class TestApplicantEligibility:
    """Award exists, applicant can hold it — two claims, never merged."""

    def test_a_kazakhstani_applicant_is_excluded_by_a_greek_restriction(self):
        found = extract_restrictions(page_text("clip-scholarship"))
        verdict = assess_applicant_eligibility(found, citizenship="Kazakhstan",
                                               residence="Kazakhstan")
        assert verdict.eligible == "no"
        assert "Greece" in verdict.reason

    def test_a_greek_applicant_is_not_excluded(self):
        found = extract_restrictions(page_text("clip-scholarship"))
        assert assess_applicant_eligibility(
            found, citizenship="Greece", residence="Greece").eligible == "yes"

    def test_residence_alone_satisfies_an_either_or_restriction(self):
        """"a Greek passport *or* Greek residence" — either one qualifies."""
        found = extract_restrictions(page_text("clip-scholarship"))
        assert assess_applicant_eligibility(
            found, citizenship="Kazakhstan", residence="Greece").eligible == "yes"

    def test_no_restriction_means_unknown_not_yes(self):
        """Silence is not permission. An award that says nothing about
        nationality has not confirmed this applicant may hold it."""
        found = extract_restrictions("This award covers full tuition fees.")
        assert assess_applicant_eligibility(
            found, citizenship="Kazakhstan", residence="Kazakhstan").eligible == "unknown"

    def test_an_unstated_applicant_citizenship_stays_unknown(self):
        found = extract_restrictions(page_text("clip-scholarship"))
        assert assess_applicant_eligibility(
            found, citizenship="", residence="").eligible == "unknown"


class TestPublishedCount:
    def test_the_clip_award_publishes_five(self):
        """"Up to five CLIP Scholarships are provided annually"."""
        count = extract_published_count(page_text("clip-scholarship"))
        assert count is not None
        assert count.value == 5
        assert "five" in count.evidence.lower()

    @pytest.mark.parametrize("text,expected", [
        ("Up to five scholarships are provided annually.", 5),
        ("Number of scholarships 2 per faculty", 2),
        ("We award 25 scholarships each year.", 25),
        ("Ten awards are available for the 2027 intake.", 10),
    ])
    def test_counts_are_read_when_published(self, text, expected):
        count = extract_published_count(text)
        assert count is not None and count.value == expected

    @pytest.mark.parametrize("text", [
        "A number of scholarships are available for excellent applicants.",
        "Several awards are offered each year.",
        "Many students receive funding.",
        "Scholarships are available.",
    ])
    def test_a_vague_quantity_is_not_a_count(self, text):
        """"A number of scholarships" publishes no number."""
        assert extract_published_count(text) is None


class TestAssessmentHonoursResidency:
    """The layering the adapter must not take over.

    The adapter records what the award restricts; the assessment stage decides
    whether *this* applicant satisfies it. These check the second half.
    """

    @staticmethod
    def award(citizenships: list[str], residencies: list[str]):
        from app.schemas.result import Scholarship

        return Scholarship(
            id="a1", name="Test Award",
            citizenship_restrictions=citizenships,
            residency_restrictions=residencies,
        )

    def test_residence_alone_can_satisfy_the_award(self, profile):
        """CLIP: "either a Greek passport or Greek residence"."""
        from app.pipeline.runner import _scholarship_eligibility

        profile.context.citizenship = "Kazakhstan"
        profile.context.country_of_residence = "Greece"
        checks = _scholarship_eligibility(self.award(["Greece"], ["Greece"]), profile)
        verdicts = [c for c in checks if "citizenship or residency" in c.requirement.lower()]
        assert verdicts and verdicts[0].status.value == "MET"

    def test_neither_citizenship_nor_residence_excludes_the_applicant(self, profile):
        from app.pipeline.runner import _applicant_eligible, _scholarship_eligibility

        profile.context.citizenship = "Kazakhstan"
        profile.context.country_of_residence = "Kazakhstan"
        award = self.award(["Greece"], ["Greece"])
        award.eligibility_checks = _scholarship_eligibility(award, profile)
        assert _applicant_eligible(award) == "no"

    def test_an_award_with_no_restriction_is_not_excluded(self, profile):
        from app.pipeline.runner import _scholarship_eligibility

        checks = _scholarship_eligibility(self.award([], []), profile)
        assert not [c for c in checks if "citizenship or residency" in c.requirement.lower()]
