"""A window's start date is never a deadline (NTU important dates, 2026-10-04)."""

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder, extract_requirements


def deadlines(text: str) -> list:
    builder = ClaimBuilder(
        source_url="https://www.example.edu/dates",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 4, tzinfo=UTC),
        page_text=text,
    )
    extract_requirements(text, builder)
    return [
        c.normalized_value for c in builder.claims if c.claim_type.value == "admission_deadline"
    ]


def test_a_single_window_reads_its_end_as_the_deadline():
    assert deadlines("Application deadline: 15 October 2026 - 20 January 2027.") == ["2027-01-20"]


def test_several_windows_by_qualification_claim_nothing():
    text = (
        "Dates / Deadlines. IB Diploma: Online application 15 October 2026 - 19 March 2027. "
        "All other international qualifications: 15 October 2026 - 20 January 2027."
    )
    assert deadlines(text) == []


def test_a_plain_deadline_is_unchanged():
    assert deadlines("The application deadline is 1 May 2027.") == ["2027-05-01"]
