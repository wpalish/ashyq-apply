"""A fee table is found after a word label, not inside a link slug (Groningen, 2026-10-04)."""

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder, extract_costs

PAGE = (
    "Admission: https://www.rug.nl/education/application-enrolment-tuition-fees/admission/ "
    "Questions: https://www.rug.nl/education/application-enrolment-tuition-fees/contact/ "
    "Application deadlines ... Tuition fees Nationality Year Fee Programme form "
    "EU/EEA 2026-2027 € 2694 full-time non-EU/EEA 2026-2027 € 19800 full-time "
    "EU/EEA 2027-2028 € 2771 full-time non-EU/EEA 2027-2028 € 19800 full-time"
)


def read(text: str, year: str | None):
    builder = ClaimBuilder(
        source_url="https://www.rug.nl/bachelors/computing-science/",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 4, tzinfo=UTC),
        page_text=text,
        academic_year=year,
    )
    extract_costs(text, builder)
    return {c.subject_key: c.normalized_value["amount"] for c in builder.claims}


def test_the_table_after_the_word_label_is_read_not_the_link_slug():
    assert read(PAGE, None) == {"EU/EEA": 2694.0, "non-EU/EEA": 19800.0}


def test_the_row_for_the_requested_academic_year_is_kept():
    assert read(PAGE, "2027/28") == {"EU/EEA": 2771.0, "non-EU/EEA": 19800.0}


def test_a_link_slug_alone_does_not_open_a_population_table():
    slug_only = (
        "See https://x.edu/application-enrolment-tuition-fees/ for EU/EEA € 2694 non-EU/EEA € 19800"
    )
    assert "non-EU/EEA" not in read(slug_only, None)
