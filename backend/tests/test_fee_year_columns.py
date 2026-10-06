"""DF-1: a fee table with academic years as columns and named tariffs as rows."""

from __future__ import annotations

import pytest

from app.adapters import extraction
from app.adapters.extraction import ClaimBuilder
from app.domain.enums import SourceSpecificity

# TU Delft "Tuition fee & finances", as the reader flattens it (2026-10-06).
DELFT = (
    "Statutory rate 2026/2027 2027/2028 Statutory rate € 2.694 € 2.771 Elective course "
    "Proof of paid tuition fee. Institutional rate 2026/2027 2027/2028 Institutional rate "
    "BSc € 19.906 MSc € 25.633 BSc € 20.563 MSc € 26.479 Transitional institutional rate* "
    "BSc € 18.175 MSc € 23.404 BSc € 18.175 MSc € 23.404"
)


def _fees(text: str, year: str | None) -> set[tuple[float, str | None, str | None, str | None]]:
    builder = ClaimBuilder(
        source_url="https://www.tudelft.nl/fees",
        specificity=SourceSpecificity.PROGRAM_INTAKE,
        official_domain=True,
    )
    builder.requested_academic_year = year
    return {
        (
            c.normalized_value["amount"],
            c.scope.population if c.scope else None,
            c.scope.degree if c.scope else None,
            c.scope.academic_year if c.scope else None,
        )
        for c in extraction.extract_costs(text, builder)
    }


def test_on_by_default_and_off_reads_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    assert extraction.FEE_YEAR_COLUMNS is True
    monkeypatch.setattr(extraction, "FEE_YEAR_COLUMNS", False)
    assert _fees(DELFT, "2027/28") == set()


@pytest.fixture
def df1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extraction, "FEE_YEAR_COLUMNS", True)


@pytest.mark.usefixtures("df1")
def test_the_requested_year_column_and_the_bachelor_cell() -> None:
    assert _fees(DELFT, "2027/28") == {
        (2771.0, "EU/EEA", None, "2027/28"),
        (20563.0, "non-EU/EEA", "bachelor", "2027/28"),
    }
    assert (19906.0, "non-EU/EEA", "bachelor", "2026/27") in _fees(DELFT, "2026/27")


@pytest.mark.usefixtures("df1")
def test_no_year_or_an_absent_year_claims_nothing() -> None:
    assert _fees(DELFT, None) == set()
    assert _fees(DELFT, "2028/29") == set()


@pytest.mark.usefixtures("df1")
def test_an_unnamed_tariff_is_left_alone() -> None:
    text = DELFT.replace("Institutional rate BSc", "Special rate BSc")
    assert {row[1] for row in _fees(text, "2027/28")} == {"EU/EEA"}
