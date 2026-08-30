"""Does this applicant satisfy this award's published restriction?

The matrix the product has to get right. Every row is a real shape a
scholarship page uses, and the third answer — unknown — is as important as the
other two: an award that has not said an applicant may hold it has not said so,
and refusing them is as wrong as promising them.
"""

from __future__ import annotations

import copy

from app.corpus.demo_profile import DEMO_PROFILE
from app.domain.enums import EligibilityStatus
from app.pipeline.assessment import _applicant_eligible, _scholarship_eligibility
from app.schemas.result import Scholarship


def applicant(citizenship: str = "", residence: str = ""):
    profile = copy.deepcopy(DEMO_PROFILE)
    profile.context.citizenship = citizenship
    profile.context.country_of_residence = residence or citizenship
    return profile


def award(
    citizenships: list[str] | None = None,
    residencies: list[str] | None = None,
    logic: str = "any",
) -> Scholarship:
    return Scholarship(
        id="s1", name="Test Award",
        citizenship_restrictions=citizenships or [],
        residency_restrictions=residencies or [],
        restriction_logic=logic,
        # Neutralised so the rolled-up verdict reflects the country question
        # and nothing else. An award whose degree applicability is unknown is
        # correctly "unknown" overall, which would mask what is under test.
        degree_applicability="yes",
    )


def verdict(scholarship: Scholarship, profile) -> str:
    scholarship.eligibility_checks = _scholarship_eligibility(scholarship, profile)
    return _applicant_eligible(scholarship)


def status_of(scholarship: Scholarship, profile) -> EligibilityStatus:
    checks = _scholarship_eligibility(scholarship, profile)
    match = [c for c in checks if "citizenship" in c.requirement.lower()]
    assert match, f"no citizenship check produced: {[c.requirement for c in checks]}"
    return match[0].status


class TestBlocMembership:
    """The defect: `"Germany" in "European Union"` is False, so a German
    citizen was refused an EU-only award."""

    def test_germany_is_eligible_for_an_eu_award(self):
        assert verdict(award(["European Union"]), applicant("Germany")) == "yes"

    def test_norway_is_eligible_for_an_eea_award(self):
        assert verdict(award(["European Economic Area"]), applicant("Norway")) == "yes"

    def test_norway_is_not_eligible_for_an_eu_only_award(self):
        assert verdict(award(["European Union"]), applicant("Norway")) == "no"

    def test_switzerland_is_not_eligible_for_an_eea_only_award(self):
        assert verdict(award(["European Economic Area"]), applicant("Switzerland")) == "no"

    def test_switzerland_is_eligible_when_the_page_names_it_alongside_the_eea(self):
        scholarship = award(["European Economic Area", "Switzerland"])
        assert verdict(scholarship, applicant("Switzerland")) == "yes"

    def test_kazakhstan_is_not_eligible_for_an_eu_award(self):
        assert verdict(award(["European Union"]), applicant("Kazakhstan")) == "no"

    def test_the_united_kingdom_is_eligible_for_a_commonwealth_award(self):
        assert verdict(award(["Commonwealth"]), applicant("United Kingdom")) == "yes"

    def test_the_united_kingdom_is_no_longer_eligible_for_an_eu_award(self):
        assert verdict(award(["European Union"]), applicant("United Kingdom")) == "no"


class TestCitizenshipAndResidency:
    def test_either_route_qualifies_when_the_page_says_or(self):
        """CLIP: "hold either a Greek passport or Greek residence"."""
        scholarship = award(["Greece"], ["Greece"], logic="any")
        assert verdict(scholarship, applicant("Kazakhstan", "Greece")) == "yes"
        assert verdict(award(["Greece"], ["Greece"], "any"),
                       applicant("Greece", "Kazakhstan")) == "yes"

    def test_both_are_needed_when_the_page_says_and(self):
        """"citizens of X who are resident in Y" is not an either/or."""
        both = award(["Germany"], ["Austria"], logic="all")
        assert verdict(both, applicant("Germany", "Austria")) == "yes"
        assert verdict(award(["Germany"], ["Austria"], "all"),
                       applicant("Germany", "Germany")) == "no"

    def test_citizenship_only_ignores_where_they_live(self):
        scholarship = award(["Germany"], [], logic="any")
        assert verdict(scholarship, applicant("Germany", "Kazakhstan")) == "yes"

    def test_residence_only_ignores_their_passport(self):
        scholarship = award([], ["Germany"], logic="any")
        assert verdict(scholarship, applicant("Kazakhstan", "Germany")) == "yes"


class TestUnknownStaysUnknown:
    def test_a_missing_applicant_citizenship_is_unknown_not_no(self):
        scholarship = award(["European Union"])
        assert status_of(scholarship, applicant("", "")) is (
            EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        )

    def test_an_unresolvable_group_is_unknown_not_no(self):
        """"open to students from Europe" has no agreed membership."""
        scholarship = award(["Europe"])
        assert status_of(scholarship, applicant("Germany")) is (
            EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        )

    def test_an_unrecognised_country_is_unknown_not_no(self):
        scholarship = award(["European Union"])
        assert status_of(scholarship, applicant("Atlantis")) is (
            EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        )

    def test_an_award_with_no_stated_restriction_produces_no_verdict(self):
        """Silence is not permission and not refusal."""
        checks = _scholarship_eligibility(award(), applicant("Kazakhstan"))
        assert not [c for c in checks if "citizenship" in c.requirement.lower()]

    def test_unknown_logic_does_not_silently_become_or(self):
        """If the page's wording did not say, do not decide it did."""
        scholarship = award(["Germany"], ["Austria"], logic="unknown")
        assert status_of(scholarship, applicant("Germany", "Germany")) is (
            EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        )


class TestEvidence:
    def test_the_check_names_what_the_restriction_means(self):
        checks = _scholarship_eligibility(award(["European Union"]), applicant("Germany"))
        text = " ".join(c.explanation for c in checks)
        assert "European Union" in text
        assert "member states" in text or "27" in text

    def test_a_refusal_says_which_group_excluded_them(self):
        checks = _scholarship_eligibility(
            award(["European Union"]), applicant("Kazakhstan")
        )
        match = next(c for c in checks if "citizenship" in c.requirement.lower())
        assert "European Union" in match.explanation
        assert "Kazakhstan" in match.explanation
