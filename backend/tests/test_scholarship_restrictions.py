"""Plan V2-33: a faculty or programme restriction is recorded, and asked about.

§6 decomposes `faculty_restrictions` and `programme_restrictions` separately.
`Scholarship.program_restrictions` existed as a declared field nothing ever
set, and there was no faculty field at all — so an award page saying "open to
students in the Faculty of Engineering" was recorded as applying to everyone.
"""

from __future__ import annotations

import pytest

from app.adapters.scholarship.web_scholarships import (
    _FACULTY_RESTRICTION,
    _PROGRAMME_RESTRICTION,
    _restricted_to,
)
from app.domain.enums import EligibilityStatus
from app.pipeline.runner import _applicant_eligible, _scholarship_eligibility
from app.schemas.result import Scholarship


class TestReadingTheRestriction:
    @pytest.mark.parametrize(
        "sentence,expected",
        [
            (
                "The award is open to students in the Faculty of Engineering.",
                "Faculty of Engineering",
            ),
            ("Restricted to applicants from the School of Law.", "School of Law"),
            (
                "Available only to students enrolled in the College of Medicine.",
                "College of Medicine",
            ),
        ],
    )
    def test_a_stated_faculty_is_read_in_the_page_s_own_words(self, sentence, expected):
        found = _restricted_to(sentence, _FACULTY_RESTRICTION)
        assert found is not None
        assert expected in found.group("subject")

    @pytest.mark.parametrize(
        "sentence",
        [
            "Open to all international students.",
            "Students in the faculty are welcome to visit during the open day.",
            "The faculty of the university is world renowned.",
            "Applications are open to everyone.",
        ],
    )
    def test_prose_that_states_no_restriction_produces_none(self, sentence):
        """A restriction we invent excludes a real applicant from real money."""
        assert _restricted_to(sentence, _FACULTY_RESTRICTION) is None
        assert _restricted_to(sentence, _PROGRAMME_RESTRICTION) is None

    def test_a_named_programme_is_read_as_a_programme_not_a_faculty(self):
        sentence = "Restricted to applicants enrolled in the BSc Data Science programme."
        assert _restricted_to(sentence, _FACULTY_RESTRICTION) is None
        found = _restricted_to(sentence, _PROGRAMME_RESTRICTION)
        assert found is not None
        assert "BSc Data Science" in found.group("subject")


class TestWhatTheRestrictionDoesToTheVerdict:
    @staticmethod
    def _award(**kwargs) -> Scholarship:
        return Scholarship(id="x", name="Award", **kwargs)

    def test_a_faculty_restriction_is_an_open_question_not_a_refusal(self, profile):
        """The applicant's faculty is not in the profile at all."""
        award = self._award(faculty_restrictions=["the Faculty of Engineering"])

        checks = _scholarship_eligibility(award, profile)

        restriction = [c for c in checks if "faculty restriction" in c.requirement.lower()]
        assert len(restriction) == 1
        assert restriction[0].status is EligibilityStatus.PENDING
        assert "Faculty of Engineering" in restriction[0].explanation

    def test_a_programme_restriction_is_not_decided_by_comparing_names(self, profile):
        """NTU taught this: 'Bachelor of Computing (Hons) in Computer Science'
        against 'Computer Science' is the same programme under two titles, and
        the scorer's own comparison could not tell."""
        award = self._award(program_restrictions=["the BSc Data Science programme"])

        checks = _scholarship_eligibility(award, profile)

        restriction = [c for c in checks if "programme restriction" in c.requirement.lower()]
        assert len(restriction) == 1
        assert restriction[0].status is EligibilityStatus.PENDING

    def test_it_leaves_the_award_unknown_rather_than_eligible(self, profile):
        award = self._award(faculty_restrictions=["the Faculty of Engineering"])
        award.eligibility_checks = _scholarship_eligibility(award, profile)

        assert _applicant_eligible(award) == "unknown"

    def test_an_award_with_no_restriction_is_unaffected(self, profile):
        award = self._award()

        checks = _scholarship_eligibility(award, profile)

        assert not [c for c in checks if "restriction" in c.requirement.lower()]


class TestTheRollUpNeverRoundsUp:
    """Phase 3 §7: UNKNOWN propagates, and is never changed to YES."""

    def test_the_adapter_does_not_call_a_restricted_award_eligible(self):
        from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter

        award = Scholarship(
            id="x",
            name="Engineering Excellence Award",
            opportunity_exists=True,
            degree_applicability="yes",
            international_eligible="yes",
            faculty_restrictions=["the Faculty of Engineering"],
        )
        WebScholarshipAdapter._derive_availability(award)

        assert award.applicant_eligible == "unknown"
        assert award.available_this_intake != "yes"

    def test_an_unrestricted_award_with_every_positive_is_still_eligible(self):
        from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter

        award = Scholarship(
            id="x",
            name="Open Award",
            opportunity_exists=True,
            degree_applicability="yes",
            international_eligible="yes",
        )
        WebScholarshipAdapter._derive_availability(award)

        assert award.applicant_eligible == "yes"


def test_a_translated_copy_of_a_page_is_one_page():
    """Run 25: HKU's scholarship list was read in en, zh-hant and zh-hans."""
    from app.adapters.scholarship.web_scholarships import _without_locale

    en = "https://admissions.hku.hk/fees-and-scholarships/scholarships"
    assert (
        _without_locale("https://admissions.hku.hk/zh-hant/fees-and-scholarships/scholarships")
        == en
    )
    assert (
        _without_locale("https://admissions.hku.hk/zh-hans/fees-and-scholarships/scholarships")
        == en
    )
    assert _without_locale(en) == en
    # A locale-looking word that is the whole path is not a translation prefix.
    assert _without_locale("https://x.edu/fi") == "https://x.edu/fi"


def test_domestic_only_award_lists_are_skipped_only_for_a_plain_foreigner():
    """Run 36: UBC read eight Canadian-students award pages for a Kazakh applicant."""
    from types import SimpleNamespace

    from app.adapters.scholarship.web_scholarships import _DOMESTIC_ONLY, _is_international

    uni = SimpleNamespace(country="Canada")

    def applicant(first, second=None):
        return SimpleNamespace(
            context=SimpleNamespace(citizenship=first, second_citizenship=second)
        )

    assert _is_international(applicant("Kazakhstan"), uni)
    assert not _is_international(applicant("Canada"), uni)
    assert not _is_international(applicant("Kazakhstan", "Canada"), uni)
    assert not _is_international(applicant("CA"), uni), "a code is never guessed at"
    assert _DOMESTIC_ONLY.search(
        "https://you.ubc.ca/financial-planning/scholarships-awards-canadian-students/loran-awards"
    )
    assert not _DOMESTIC_ONLY.search(
        "https://you.ubc.ca/financial-planning/scholarships-awards-international-students"
    )
