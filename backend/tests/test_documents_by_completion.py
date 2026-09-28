"""A document's form by completion state, read from one line (Groningen, 2026-09-28)."""

from datetime import UTC, datetime

from app.adapters.documents.web_documents import _completion_forms
from app.adapters.extraction import ClaimBuilder

GRONINGEN = (
    "Transcript Scan(s) of your academic record (i.e. final grade list/report card) and/or "
    "if not yet completed: school-issued list of your courses still to be completed "
    "(if applicable, including level/credits/units)"
)


def read(text: str):
    builder = ClaimBuilder(
        source_url="https://www.rug.nl/x",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    _completion_forms(text, builder)
    return [c.normalized_value for c in builder.claims]


def test_both_forms_of_the_transcript_are_read():
    assert read(GRONINGEN) == [
        {"document": "Full academic transcript", "status": "completed", "form": "academic_record"},
        {
            "document": "Full academic transcript",
            "status": "not_completed",
            "form": "school_course_list",
        },
    ]


def test_a_diploma_or_an_enrolment_statement():
    values = read(
        "Diploma Certified copy of your diploma or if not yet completed: "
        "a statement of enrolment from your school"
    )
    assert [v["form"] for v in values] == ["diploma", "school_enrolment_statement"]


def test_an_unrecognised_form_reads_nothing():
    assert read("Transcript Your grades, or if not yet completed: whatever you have") == []


def test_no_completion_clause_reads_nothing():
    assert read("Transcript Scan(s) of your academic record") == []
