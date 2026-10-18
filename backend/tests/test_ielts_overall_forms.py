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
