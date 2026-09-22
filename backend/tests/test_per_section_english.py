"""Owner decision, 2026-09-22: a per-section English minimum has somewhere to live.

NTU's certified value is a map — {"overall": 6, "writing": 6, "speaking": 6} —
and the extractor produced a single floor, so the named sections were dropped.
Collapsing them to one number would convert a value silently, which this
repository forbids: "Writing 6, Reading 6.5" is not the statement "no band
below 6".

The consumer was already built for this. `eligibility` has read a per-band
map since it was written; nothing upstream ever produced one.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, for_matching
from app.adapters.requirements.web_requirements import extract_requirements
from app.domain.claim_verifier import VALUE_RANGE_RULES
from app.domain.enums import ClaimType


def _read(text: str) -> dict[str, object]:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(for_matching(text), builder)
    return {c.claim_type.value: c.normalized_value for c in builder.claims}


class TestSectionsNamedOneByOne:
    def test_ntus_certified_wording(self):
        """ "Overall 6, Writing 6,speaking 6" — note the missing space, which is
        how the cells were joined."""
        got = _read("IELTS: Overall 6, Writing 6,speaking 6")
        assert got["ielts_min_subscore"] == {"writing": 6.0, "speaking": 6.0}
        assert got["ielts_min_overall"] == 6.0

    def test_bands_that_differ_are_kept_apart(self):
        """The whole point: one floor cannot say writing 6.5 and reading 6.0."""
        got = _read("IELTS Academic: overall 7.0, with Writing 6.5 and Reading 6.0.")
        assert got["ielts_min_subscore"] == {"writing": 6.5, "reading": 6.0}

    def test_a_decimal_point_does_not_end_the_sentence(self):
        """ "[^.]" stopped at the 7 of "overall 7.0" and lost every band after."""
        assert _read("IELTS overall 7.0, Writing 6.5.")["ielts_min_subscore"] == {"writing": 6.5}


class TestWhatMustNotBecomeABand:
    def test_a_single_floor_still_reads_as_one_number(self):
        """Unchanged behaviour for the commonest wording of all."""
        assert _read("IELTS overall 6.5, no band less than 6.0.")["ielts_min_subscore"] == 6.0

    def test_a_section_word_in_another_sentence_is_not_a_band(self):
        got = _read("IELTS overall 6.5. Writing competitions are held in June 7.")
        assert "ielts_min_subscore" not in got

    def test_a_section_word_with_no_ielts_nearby_is_not_a_band(self):
        assert _read("Writing 6 is the room number. Applicants need a good essay.") == {}

    def test_a_band_outside_the_scale_is_refused(self):
        assert "ielts_min_subscore" not in _read("IELTS: Writing 12, Speaking 3")


class TestTheVerifierChecksEveryBand:
    @staticmethod
    def _check(value: object) -> bool:
        return VALUE_RANGE_RULES[ClaimType.IELTS_MIN_SUBSCORE](value, date(2026, 9, 22))

    def test_a_map_passes_when_every_band_is_a_real_band(self):
        assert self._check({"writing": 6.0, "speaking": 6.5})

    @pytest.mark.parametrize(
        "bands",
        [
            {"writing": 12.0},
            {"writing": 6.0, "speaking": 9.5},
            {"writing": 6.2},
            {},
            {"writing": "six"},
        ],
    )
    def test_a_map_fails_when_any_band_does_not(self, bands):
        """One bad band condemns the map: a range check that passes on
        average is not a range check. The bounds are the ones a single value
        has always had, not stricter ones invented for maps.
        """
        assert not self._check(bands)

    def test_a_single_value_is_unaffected(self):
        assert self._check(6.0)
        assert not self._check(12.0)
