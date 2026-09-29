"""A programme's faculty read from a labelled field (HKU, 2026-09-28 oracle run)."""

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder, extract_programme_faculty
from app.domain.enums import ClaimType


def read(text: str):
    builder = ClaimBuilder(
        source_url="https://admissions.hku.hk/programmes/x",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    builder.add(
        ClaimType.PROGRAM_EXISTS,
        {"program": "Bachelor of Engineering in Computer Science", "degree": "bachelor"},
        "x",
    )
    claim = extract_programme_faculty(text, builder)
    return None if claim is None else claim.normalized_value


def test_a_label_on_its_own_line_names_the_faculty_below_it():
    text = "CODE\n6999\nFACULTY\nSchool of Computing and Data Science\nParagraphs"
    assert read(text) == "School of Computing and Data Science"


def test_a_label_and_value_on_one_line():
    assert read("Faculty: Faculty of Engineering") == "Faculty of Engineering"


def test_a_page_naming_two_faculties_names_none():
    assert read("Faculty\nFaculty of Arts\nFaculty\nFaculty of Science") is None


def test_a_person_under_the_label_is_not_a_faculty():
    assert read("Faculty\nProf. Jane Doe, Head of Admissions") is None


def test_prose_mentioning_a_faculty_is_not_a_label():
    assert read("Our Faculty of Engineering welcomes international students.") is None


def test_the_faculty_is_filed_under_the_programme_the_page_confirmed():
    builder = ClaimBuilder(
        source_url="https://admissions.hku.hk/programmes/x",
        page_title="x",
        program="Computing And Data Science",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    builder.add(
        ClaimType.PROGRAM_EXISTS,
        {"program": "Bachelor of Engineering in Computer Science", "degree": "bachelor"},
        "x",
    )
    claim = extract_programme_faculty("FACULTY\nSchool of Computing and Data Science", builder)
    assert claim is not None
    assert claim.program == "Bachelor of Engineering in Computer Science"
    assert claim.scope is not None
    assert claim.scope.programme == "Bachelor of Engineering in Computer Science"
    assert claim.scope.degree == "bachelor"
    assert builder.meta["program"] == "Computing And Data Science"


def test_no_confirmed_programme_no_faculty():
    builder = ClaimBuilder(
        source_url="https://x.hk/p",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    assert extract_programme_faculty("FACULTY\nSchool of Engineering", builder) is None
