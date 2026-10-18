"""The TOEFL total never comes from another test's statement.

Wrong-claim analysis of 2026-10-18 (R-C): ``TOEFL[^.]{0,90}?(\\d{2,3})`` scanned
forward from the word into the next test's sentence and read PTE's score. UM's
pages write the TOEFL figure before the word. Fixtures are cut from the
hand-fetched pages.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirements, for_matching


def _toefl(text: str) -> object:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(for_matching(text), builder)
    got = {c.claim_type.value: c.normalized_value for c in builder.claims}
    return got.get("toefl_min_total")


UM_LINGUISTICS = (
    "Obtain at least Band 6 (Academic) in IELTS and a score of 6.0 in the Writing "
    "component of the IELTS; or\nObtain a minimum score of 78 in TOEFL iBT (Centre-based)\n"
    "Obtain a minimum score of 57 in PTE (Academic)\nMUET 5.0\nIELTS (Academic) 7.0\n"
    "TOEFL iBT (Centre-based) 96\n"
)
UM_FAQ = (
    "Applicant must obtain:\n\nBand of 5.0 and above in IELTS (Academic) ; or\n\n"
    "Score of 500 (PBT), 173 (CBT) or 60 (IBT) and above in TOEFL; or\n\n"
    "Band of 3 and above in Malaysian University English Test (MUET); or\n\n"
    "Score 41 and above in Pearson Test of Academic English (PTE Academic)"
)


def test_um_linguistics_reads_the_toefl_figure_not_ptes():
    assert _toefl(UM_LINGUISTICS) == 78


def test_um_faq_reads_the_ibt_figure_not_ptes():
    assert _toefl(UM_FAQ) == 60


def test_a_forward_scan_stops_at_another_tests_name():
    assert _toefl("TOEFL iBT accepted; or PTE Academic 58") is None


def test_a_number_that_belongs_to_the_next_test_is_not_taken():
    assert _toefl("TOEFL iBT (Centre-based) Obtain a minimum score of 57 in PTE") is None


@pytest.mark.parametrize(
    ("text", "score"),
    [
        (
            "Test of English as a Foreign Language (TOEFL): A valid (no more than 2 years "
            "old) TOEFL iBT Score Report with an overall score of 88 or above",
            88,
        ),
        ("TOEFL iBT\n90.0 Overall\nMin: 22.0 in reading", 90),
        ("TOEFL iBT: 92 overall, with no section below 20.", 92),
    ],
)
def test_the_forward_forms_still_read(text, score):
    assert _toefl(text) == score
