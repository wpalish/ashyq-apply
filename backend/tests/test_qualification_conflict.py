"""Owner decision, 2026-09-22: two qualifications are two scopes, not a clash.

"The Abitur route requires 6.5" and "the attestat route requires 7.0" are both
true. Until now `_KIND_BY_DIMENSION` had no entry for `qualification`, so such
a pair fell through to TRUE_CONFLICT — and a conflicting claim cannot support
an answer, so the applicant was left with neither value.

The safety property is unchanged and is what the rest of these tests guard: a
scope nobody recorded is never rounded into "different". Wrongly keeping a
conflict costs a question; wrongly dismissing one costs a decision.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.claim_scope import ClaimScope
from app.domain.conflicts import _ask, classify_conflict
from app.domain.enums import ClaimStatus, ClaimType, ConflictKind, SourceSpecificity
from app.schemas.claim import Claim


def _claim(value: float, url: str, **scope) -> Claim:
    return Claim(
        claim_type=ClaimType.IELTS_MIN_OVERALL,
        normalized_value=value,
        source_url=url,
        original_text_excerpt="the page said so",
        accessed_at=datetime.now(UTC),
        status=ClaimStatus.VERIFIED_CURRENT,
        source_specificity=SourceSpecificity.PROGRAM_INTAKE,
        scope=ClaimScope(**scope),
    )


class TestTwoQualificationsAreTwoScopes:
    def test_they_are_no_longer_a_contradiction(self):
        pool = [
            _claim(6.5, "https://uni.edu/abitur", qualification="Abitur"),
            _claim(7.0, "https://uni.edu/attestat", qualification="attestat"),
        ]
        assert classify_conflict(pool) is ConflictKind.DIFFERENT_QUALIFICATION

    def test_the_applicant_is_asked_which_one_applies_to_them(self):
        question = _ask(ConflictKind.DIFFERENT_QUALIFICATION)
        assert "different qualifications" in question
        assert "which one applies to me" in question


class TestTheSafetyPropertyIsUnchanged:
    def test_the_same_qualification_twice_is_still_a_conflict(self):
        """Two pages about Abitur holders that disagree do contradict."""
        pool = [
            _claim(6.5, "https://uni.edu/a", qualification="Abitur"),
            _claim(7.0, "https://uni.edu/b", qualification="Abitur"),
        ]
        assert classify_conflict(pool) is ConflictKind.TRUE_CONFLICT

    def test_a_scope_nobody_recorded_is_still_a_conflict(self):
        """Unknown is never rounded into "different"; that would explain away
        a real disagreement."""
        pool = [_claim(6.5, "https://uni.edu/a"), _claim(7.0, "https://uni.edu/b")]
        assert classify_conflict(pool) is ConflictKind.TRUE_CONFLICT

    def test_one_side_stating_a_qualification_is_not_enough(self):
        pool = [
            _claim(6.5, "https://uni.edu/a", qualification="Abitur"),
            _claim(7.0, "https://uni.edu/b"),
        ]
        assert classify_conflict(pool) is ConflictKind.TRUE_CONFLICT

    @pytest.mark.parametrize(
        "dimension,left,right,expected",
        [
            ("population", "international", "domestic", ConflictKind.DIFFERENT_POPULATION),
            ("intake", "fall 2027", "spring 2027", ConflictKind.DIFFERENT_INTAKE),
            ("degree", "bachelor", "master", ConflictKind.DIFFERENT_DEGREE),
        ],
    )
    def test_the_other_dimensions_are_untouched(self, dimension, left, right, expected):
        pool = [
            _claim(6.5, "https://uni.edu/a", **{dimension: left}),
            _claim(7.0, "https://uni.edu/b", **{dimension: right}),
        ]
        assert classify_conflict(pool) is expected
