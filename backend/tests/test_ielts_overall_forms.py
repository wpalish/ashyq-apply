"""Overall IELTS bands in the shapes the 2026-10-18 structural analysis (§2 F4)
found unread on accepted pages. Fixtures are cut from hand-fetched pages.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirements, for_matching


def _read(text: str) -> dict[str, object]:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(for_matching(text), builder)
    return {c.claim_type.value: c.normalized_value for c in builder.claims}


class TestScoreRequiredCell:
    """Auckland's BSc entry table (hand-fetched 2026-10-18): the overall band
    sits in a "Score required" cell, the per-band floor in the next row."""

    AUCKLAND = (
        " Qualification\n \n\nIB\n\nInternational Baccalaureate Diploma\n\n"
        " Score required\n \n\n 26\n \n\n+\n\n"
        " Qualification\n \n\nIELTS Academic\n\n"
        "International English Language Testing System\n\n"
        " Score required\n \n\n 6.0\n \n\n"
        "No bands less than 5.5.\n\n"
        "See alternative English language requirements\n\n"
        " Qualification\n \n\nGCE A Level/CIE\n\n"
        "General Certificate of Education Advanced Level\n\n"
        " Score required\n \n\n BCC\n"
    )

    def test_the_overall_band_is_read_beside_the_floor(self):
        got = _read(self.AUCKLAND)
        assert got["ielts_min_overall"] == 6.0
        assert got["ielts_min_subscore"] == 5.5

    def test_the_prose_form_still_reads(self):
        got = _read("IELTS (Academic) Overall score of 6.0 and no bands below 5.5")
        assert got["ielts_min_overall"] == 6.0
        assert got["ielts_min_subscore"] == 5.5

    @pytest.mark.parametrize(
        "text",
        [
            # Another qualification's cell is not an IELTS band.
            "IB International Baccalaureate Diploma Score required 26",
            # A two-digit or percentage score after the label is not a band.
            "IELTS Academic or PTE Academic Score required 58",
            "IELTS Academic or a foundation exam Score required 65%",
            # No IELTS before the label: the A level row stays unread.
            "GCE A Level/CIE General Certificate of Education Score required 6",
        ],
    )
    def test_score_required_without_an_ielts_band_reads_nothing(self, text):
        assert "ielts_min_overall" not in _read(text)


class TestBandInAListOfTests:
    """Universiti Malaya's programme page (hand-fetched 2026-10-18): IELTS is one
    entry of a list of accepted tests, its band straight after the name."""

    UM = (
        "Obtained a \nminimum English language Competency\n in any \nONE (1) \n"
        "of the following requirements:\nMUET 4.0\nIELTS (Academic) 5.5\n"
        "TOEFL iBT (Centre-based) 46\nTOEFL Essentials (Online) 8.0\n"
        "Pearson Test of English (PTE Academic) 51\n"
    )

    def test_the_ielts_entry_is_read_with_the_toefl_one(self):
        got = _read(self.UM)
        assert got["ielts_min_overall"] == 5.5
        assert got["toefl_min_total"] == 46
        assert "ielts_min_subscore" not in got

    @pytest.mark.parametrize(
        ("text", "band"),
        [
            ("IELTS Academic 6.5, TOEFL iBT 90", 6.5),
            ("IELTS: 6 or TOEFL 80", 6.0),
            ("IELTS 7.0 | PTE Academic 65", 7.0),
        ],
    )
    def test_other_list_shapes(self, text, band):
        assert _read(text)["ielts_min_overall"] == band

    @pytest.mark.parametrize(
        "text",
        [
            # A per-band floor stays a subscore statement.
            "IELTS (Academic) 5.5 in each band, TOEFL iBT 46",
            # A band followed by a section name is not the overall one.
            "IELTS 6.0 writing TOEFL 80",
            # A longer number after the name is no band.
            "IELTS 65 TOEFL 80",
            # The name with no list after it is still not enough.
            "IELTS (Academic) 5.5 required for some programmes",
        ],
    )
    def test_a_band_not_followed_by_another_test_is_not_the_overall(self, text):
        assert "ielts_min_overall" not in _read(text)
