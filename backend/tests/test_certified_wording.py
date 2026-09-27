"""EXTRA-11: the extractors, tested against the certified corpus' own wording.

Every certified excerpt is text a human confirmed appears on an official page.
An extractor that cannot read the excerpt certainly cannot read the page, so
this needs no live run to be evidence.

Each case below quotes the corpus. The guide calls checking only the overall
English band "the single most common error in this work": an applicant with
7.0 overall and 6.0 writing fails a 6.5 per-band requirement and is told they
qualify.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, for_matching
from app.adapters.requirements.web_requirements import extract_requirements


def _read(text: str) -> dict[str, object]:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(for_matching(text), builder)
    return {c.claim_type.value: c.normalized_value for c in builder.claims}


class TestThePerSectionMinimumSurvives:
    def test_ubcs_own_wording_no_part_less_than(self):
        """The certified excerpt for ubc.ielts.subscores is "no part less
        than 6.0". `part` was missing from the vocabulary, so the overall band
        was kept and the per-section floor silently dropped."""
        assert _read("IELTS Academic: overall 6.5, with no part less than 6.0.") == {
            "ielts_min_overall": 6.5,
            "ielts_min_subscore": 6.0,
        }

    @pytest.mark.parametrize("word", ["band", "score", "component", "section", "part"])
    def test_every_word_a_university_uses_for_a_section(self, word):
        got = _read(f"IELTS overall 6.5, no {word} less than 6.0.")
        assert got.get("ielts_min_subscore") == 6.0, word

    def test_the_overall_band_alone_is_still_read(self):
        """A page that states only an overall band must not gain a subscore."""
        got = _read("IELTS Academic overall band of 6.5 is required.")
        assert got.get("ielts_min_overall") == 6.5
        assert "ielts_min_subscore" not in got


class TestTheScoreMayComeBeforeItsTest:
    def test_ntus_own_wording_1250_for_redesigned_sat(self):
        """The certified excerpt for ntu.english_evidence.sat.minimum is
        "1250 for redesigned SAT", which read as nothing at all."""
        assert _read("A score of 1250 for redesigned SAT is required.") == {"sat_min_total": 1250}

    def test_the_forward_wording_still_works(self):
        assert _read("SAT minimum score of 1350 is required.") == {"sat_min_total": 1350}

    def test_or_above_is_understood(self):
        assert _read("Applicants need 1300 or above on the SAT.") == {"sat_min_total": 1300}

    @pytest.mark.parametrize(
        "sentence",
        [
            "Room 1250 is where the SAT is sat.",
            "Applicants present 1250 EUR with their SAT booking.",
            "Founded in 1250. SAT scores are accepted.",
            "1250 students sat the SAT last year.",
        ],
    )
    def test_a_number_near_the_word_sat_is_not_a_score(self, sentence):
        """The forward form has always demanded a qualifier. The reverse must
        demand one too: these all read as scores before it did."""
        assert "sat_min_total" not in _read(sentence), sentence
