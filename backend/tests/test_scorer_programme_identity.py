"""Owner decision, 2026-09-22: the scorer compares programme identity.

`wrong_scope_claim_rate` counted NTU's "Bachelor of Computing (Hons) in
Computer Science" as a wrong-scope claim against a label reading "Computer
Science" — the same programme written two ways. That measured our naming
rather than our research, and `programme.exists` is the single most common
key in the certified corpus: 11 facts of 74.

Only YES is a match. UNKNOWN stays a miss: a benchmark that scores "we could
not tell" as a hit measures nothing.
"""

from __future__ import annotations

import pytest

from evaluation.research.metrics import scope_matches
from evaluation.research.schema import Scope


def _scope(**overrides) -> Scope:
    base = {
        "university": "Example University",
        "programme": None,
        "degree": None,
        "field": None,
        "intake": None,
        "population": None,
        "qualification": None,
        "academic_year": None,
    }
    base.update(overrides)
    return Scope(**base)


class TestTheSameProgrammeUnderTwoTitles:
    def test_the_full_official_title_matches_the_short_label(self):
        """NTU's own wording, and the reason this decision exists."""
        assert scope_matches(
            _scope(programme="Computer Science"),
            _scope(programme="Bachelor of Computing (Hons) in Computer Science"),
        )

    def test_an_identical_title_still_matches(self):
        assert scope_matches(
            _scope(programme="Computer Science"), _scope(programme="Computer Science")
        )


class TestWhatIsStillAMiss:
    def test_a_different_subject_is_refused(self):
        assert not scope_matches(
            _scope(programme="Computer Science"), _scope(programme="BSc Mathematics")
        )

    def test_a_joint_degree_is_not_assumed_to_be_the_same_programme(self):
        """ "Mathematical and Computer Sciences" overlaps but is not equal, so
        the ontology answers UNKNOWN — a question for a human, not a hit."""
        assert not scope_matches(
            _scope(programme="Computer Science"),
            _scope(programme="Bachelor of Science in Mathematical and Computer Sciences"),
        )

    def test_recording_no_programme_at_all_is_not_a_match(self):
        assert not scope_matches(_scope(programme="Computer Science"), _scope(programme=None))


class TestEveryOtherDimensionIsUnchanged:
    @pytest.mark.parametrize(
        "dimension,expected,actual",
        [
            ("intake", "fall 2027", "fall 2026"),
            ("degree", "bachelor", "master"),
            ("population", "international", "domestic"),
            ("qualification", "attestat", "IB"),
        ],
    )
    def test_a_differing_dimension_still_fails_literally(self, dimension, expected, actual):
        assert not scope_matches(_scope(**{dimension: expected}), _scope(**{dimension: actual}))

    def test_a_dimension_the_label_leaves_open_is_not_asked_about(self):
        """A label that states no intake is not asking about the intake."""
        assert scope_matches(_scope(), _scope(intake="fall 2027", programme="Anything At All"))
