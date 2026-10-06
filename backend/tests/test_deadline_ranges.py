"""A window's start date is never a deadline (NTU important dates, 2026-10-04)."""

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder, extract_requirements


def _builder(text: str = "") -> ClaimBuilder:
    return ClaimBuilder(
        source_url="https://www.example.edu/dates",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 4, tzinfo=UTC),
        page_text=text,
    )


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


SEVERAL_WINDOWS = (
    "Dates / Deadlines. IB Diploma: Online application 15 October 2026 - 19 March 2027. "
    "All other international qualifications: 15 October 2026 - 20 January 2027."
)


def test_several_windows_by_qualification_claim_nothing_before_dl2(monkeypatch):
    from app.adapters import extraction

    monkeypatch.setattr(extraction, "DEADLINE_V2", False)
    assert deadlines(SEVERAL_WINDOWS) == []


def test_several_windows_claim_only_the_catch_all_row_under_dl2():
    """DL-2 (default since 2026-10-05): the catch-all row's date, scoped to that row."""
    text = SEVERAL_WINDOWS
    builder = _builder(text)

    claims = [
        c for c in extract_requirements(text, builder) if c.claim_type.value == "admission_deadline"
    ]
    assert [c.normalized_value for c in claims] == ["2027-01-20"]
    assert claims[0].scope is not None
    assert claims[0].scope.qualification == "All other international qualifications"


def test_a_plain_deadline_is_unchanged():
    assert deadlines("The application deadline is 1 May 2027.") == ["2027-05-01"]


def test_the_end_of_an_application_window_is_not_an_intake():
    """NTU: "Online Application  Day of A-level results release to 19 March 2026"."""
    from app.adapters.extraction import extract_intake_terms

    text = (
        "Application for Admission  Online Application  "
        "Day of A-level results release to 19 March 2026"
    )
    assert extract_intake_terms(text, _builder(text)) == []


def test_a_stated_start_is_still_an_intake():
    from app.adapters.extraction import extract_intake_terms

    START = "Students beginning their studies in September 2027."
    claims = extract_intake_terms(START, _builder(START))
    assert [c.normalized_value for c in claims] == ["fall 2027"]


def test_a_dated_event_is_not_an_intake():
    """Groningen: "Beginning January 21, 2026, TOEFL iBT score reports ..."."""
    from app.adapters.extraction import extract_intake_terms

    text = "Beginning January 21, 2026, TOEFL iBT score reports will feature a new scale."
    assert extract_intake_terms(text, _builder(text)) == []
