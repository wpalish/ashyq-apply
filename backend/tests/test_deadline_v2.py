"""Plan rule DL-2: deadlines stated in forms the first readers never matched.

Each case is a verbatim excerpt from a cohort page read on 2026-10-05.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.adapters.extraction as extraction
from app.adapters.extraction import ClaimBuilder, extract_requirements

UBC = (
    "Early October 2026 Application opens Online application opens for Winter Session "
    "(September 2027 to April 2028) and Summer Session (May to August 2027). Apply here! "
    "November 15, 2026 (11:59 p.m. PST) Scholarships and awards International applicants: "
    "Deadline to apply to UBC and submit an award application if you're an international "
    "student and you wish to be considered for the UBC International Scholars Program awards . "
    "December 1, 2026 (11:59 p.m. PST) Scholarships and awards Canadian citizens and permanent "
    "residents: Deadline to apply to UBC if you wish to be considered for the Presidential "
    "Scholars Awards. January 15, 2027 (11:59 p.m. PST) Applications due Deadline to apply for "
    "Winter Session (September 2027 to April 2028)."
)
NTU = (
    "Application windows Our application windows are determined by qualification type. "
    "International qualifications/admission requirements Application status Application window "
    "Deadline for Document submission All other international qualifications not listed below "
    "(including German Abitur, Turkish High School, New Zealand NCEA, Bangladesh HSC, Pakistan "
    "HSC, Iran High School Diploma etc.) Closed 15 Oct 2026 - 20 Jan 2027 Upload/Submit "
    "documents according to the Checklist within 3 days after application closing date. "
    "American High School Diploma/High School Diploma with AP (Advanced Placement) Closed "
    "15 Oct 2026 - 19 Mar 2027 International Baccalaureate (IB) Diploma Closed "
    "15 Oct 2026 - 19 Mar 2027"
)
AALTO = (
    "Degree: Bachelor of Science (Technology) + Master of Science (Technology) Application "
    "period: 7 Jan 2027 – 22 Jan 2027 Language of instruction: English"
)
TORONTO = (
    "2027 admissions Deadlines to apply Faculty/program Recommended early application date "
    "Deadline Arts & Science, U of T St. George November 7 January 15"
)


def deadlines(text: str) -> list[tuple[str, str | None, str | None]]:
    builder = ClaimBuilder(
        source_url="https://www.example.edu/dates",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 5, tzinfo=UTC),
        page_text=text,
    )
    extract_requirements(text, builder)
    return [
        (
            c.normalized_value,
            c.scope.qualification if c.scope else None,
            c.scope.intake if c.scope else None,
        )
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setattr(extraction, "DEADLINE_V2", True)


def test_off_by_default_and_the_first_readers_miss_all_three():
    assert extraction.DEADLINE_V2 is False
    assert deadlines(UBC) == []
    assert deadlines(AALTO) == []
    assert deadlines(NTU) == []


def test_a_date_labelled_applications_due_is_the_deadline(v2):
    """Not the scholarship dates above it, and the session names the intake."""
    assert deadlines(UBC) == [("2027-01-15", None, "Fall 2027")]


def test_abbreviated_months_read_the_end_of_the_application_period(v2):
    assert deadlines(AALTO) == [("2027-01-22", None, None)]


def test_a_catch_all_row_names_its_qualification(v2):
    assert deadlines(NTU) == [
        ("2027-01-20", "All other international qualifications not listed below", None)
    ]


def test_windows_without_a_catch_all_still_claim_nothing(v2):
    listed_only = NTU.replace("All other international qualifications not listed below", "Others")
    assert deadlines(listed_only) == []


def test_a_date_without_a_year_is_not_dated(v2):
    assert deadlines(TORONTO) == []


def test_population_rows_are_unchanged(v2):
    groningen = (
        "Application deadlines Type of student Deadline Start course Dutch students 01 May 2027 "
        "01 September 2027 EU/EEA students 01 May 2027 01 September 2027 non-EU/EEA students "
        "15 April 2027 01 September 2027"
    )
    assert sorted(d for d, _, _ in deadlines(groningen)) == ["2027-04-15", "2027-05-01"]


def test_a_lone_catch_all_window_keeps_its_qualification() -> None:
    # Run 2026-10-05: NTU's reader saw only the catch-all row; the date was
    # right and the scope was not, because a single window skipped the row.
    text = (
        "Application window Deadline for Document submission All other international "
        "qualifications not listed below (including German Abitur etc.) Closed "
        "15 Oct 2026 - 20 Jan 2027 Upload documents"
    )
    read = extraction._deadline_v2(text)
    assert read is not None
    assert read[0] == "20 Jan 2027"
    assert read[3] == "All other international qualifications not listed below"
