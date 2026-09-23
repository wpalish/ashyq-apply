"""A deadline table with one row per fee population.

Groningen's certified page: "Type of student | Deadline | Start course" with a
row each for Dutch, EU/EEA and non-EU/EEA students. The single-match reading
quoted the first row as the deadline for everybody; where the rows differ,
that is the wrong date for every other population.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.adapters.extraction import ClaimBuilder, extract_requirements
from app.domain.claim_scope import ClaimScope
from app.domain.eligibility import evaluate_program, population_deadlines
from app.domain.enums import EligibilityStatus
from tests.conftest import make_claim as C

_GRONINGEN = (
    "Application deadlines Type of student Deadline Start course "
    "Dutch students 01 May 2027 01 September 2027 "
    "EU/EEA students 01 May 2027 01 September 2027 "
    "non-EU/EEA students 01 March 2027 01 September 2027 Please note"
)


def _deadlines(text: str) -> list[tuple[str, str | None]]:
    builder = ClaimBuilder(
        source_url="https://www.rug.nl/bachelors/computing-science/",
        official_domain=True,
        accessed_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    extract_requirements(text, builder)
    return [
        (str(c.normalized_value), c.scope.population if c.scope else None)
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


class TestReadingTheTable:
    def test_each_named_population_gets_its_own_row(self):
        assert _deadlines(_GRONINGEN) == [
            ("2027-05-01", "EU/EEA"),
            ("2027-03-01", "non-EU/EEA"),
        ]

    def test_the_deadline_column_follows_the_header_not_position(self):
        text = (
            "Deadlines Start of studies Deadline "
            "EU/EEA applicants 1 September 2027 1 May 2027 "
            "non-EU/EEA applicants 1 September 2027 1 April 2027"
        )
        assert _deadlines(text) == [("2027-05-01", "EU/EEA"), ("2027-04-01", "non-EU/EEA")]

    def test_one_row_is_not_a_table(self):
        assert _deadlines("Deadline: EU/EEA students 1 May 2027") == [("2027-05-01", None)]

    def test_a_plain_sentence_keeps_the_ordinary_reading(self):
        assert _deadlines("The application deadline is 15 January 2027.") == [("2027-01-15", None)]


def _row(population: str, iso: str):
    return C(
        "admission_deadline",
        iso,
        subject_key=population,
        scope=ClaimScope(population=population),
    )


TODAY = date(2027, 4, 1)


class TestAssessingIt:
    def test_the_same_date_for_every_population_needs_no_choice(self):
        assert (
            population_deadlines([_row("EU/EEA", "2027-05-01"), _row("non-EU/EEA", "2027-05-01")])
            == []
        )

    def test_a_row_still_open_is_never_eliminated_by_another_rows_date(self, profile):
        outcome = evaluate_program(
            profile,
            [_row("EU/EEA", "2027-05-01"), _row("non-EU/EEA", "2027-03-01")],
            today=TODAY,
        )
        [check] = [c for c in outcome.checks if c.requirement == "Admission deadline"]
        assert check.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert check.is_hard_filter is False
        assert "non-EU/EEA" in check.explanation

    def test_the_earliest_is_shown_while_every_row_is_open(self, profile):
        outcome = evaluate_program(
            profile,
            [_row("EU/EEA", "2027-05-01"), _row("non-EU/EEA", "2027-06-01")],
            today=TODAY,
        )
        [check] = [c for c in outcome.checks if c.requirement == "Admission deadline"]
        assert check.status is EligibilityStatus.MET
        assert check.published_value == "2027-05-01"

    def test_every_row_passed_is_a_gap(self, profile):
        outcome = evaluate_program(
            profile,
            [_row("EU/EEA", "2027-02-01"), _row("non-EU/EEA", "2027-03-01")],
            today=TODAY,
        )
        [check] = [c for c in outcome.checks if c.requirement == "Admission deadline"]
        assert check.status is EligibilityStatus.GAP


def test_each_row_takes_its_intake_from_the_start_column():
    """Groningen's "Deadline | Start course": the start date is the row's own."""
    builder = ClaimBuilder(
        source_url="https://www.rug.nl/bachelors/computing-science/",
        official_domain=True,
        accessed_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    extract_requirements(_GRONINGEN, builder)
    intakes = {c.scope.population: c.scope.intake for c in builder.claims if c.scope}
    assert intakes == {"EU/EEA": "Fall 2027", "non-EU/EEA": "Fall 2027"}
