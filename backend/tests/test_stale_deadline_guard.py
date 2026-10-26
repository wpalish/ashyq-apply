"""A last-cycle deadline and a mobility page never answer the admission deadline.

Wrong-claim analysis of 2026-10-18 (R-F): PUC's exchange / double-degree
calendar ("From August until October 1, 2024 ("deadline" October 1, 2024)") was
reached by topic search and 2024-10-01 was claimed for a fall-2027 applicant.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.adapters.discovery.live_discovery import is_excluded_path
from app.domain.claim_verifier import value_in_range
from app.domain.enums import ClaimType

TODAY = date(2026, 10, 18)


@pytest.mark.parametrize(
    ("iso", "kept"),
    [
        ("2024-10-01", False),  # PUC's partner-university calendar
        ("2025-10-17", False),  # one day over a year ago
        ("2025-10-18", True),
        ("2026-01-15", True),  # this cycle's past deadline is still a fact
        ("2027-01-15", True),
        ("2026-02-30", False),  # not a date
    ],
)
def test_an_iso_deadline_more_than_a_year_past_is_out_of_range(iso, kept):
    assert value_in_range(ClaimType.ADMISSION_DEADLINE, iso, today=TODAY) is kept


@pytest.mark.parametrize(
    "url",
    [
        "https://internacionalizacion.uc.cl/en/come-to-uc/double-degree-international-students/"
        "application-calendar-international-students/",
        "https://www.example.edu/study/exchange-students/apply",
        "https://www.example.edu/international/student-exchange/",
        "https://www.example.edu/study-abroad/incoming",
        "https://www.example.edu/en/mobility/deadlines",
        "https://www.example.edu/partner-universities/application",
    ],
)
def test_mobility_pages_are_excluded(url):
    assert is_excluded_path(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.example.edu/study/undergraduate/international/deadlines",
        "https://www.example.edu/study/bachelor/computer-science",
        "https://www.example.edu/admissions/english-language-requirements",
    ],
)
def test_degree_admission_pages_are_not_excluded(url):
    assert is_excluded_path(url) is False
