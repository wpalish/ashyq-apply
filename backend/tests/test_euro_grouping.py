"""EURO_GROUPING: continental euro amounts ("€ 20.563") read as thousands, not cents."""

import pytest

from app.adapters import extraction
from app.adapters.extraction import ClaimBuilder, parse_money
from app.domain.enums import SourceSpecificity


@pytest.fixture
def euro_grouping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extraction, "EURO_GROUPING", True)


def test_flag_off_keeps_the_old_reading() -> None:
    assert parse_money("Tuition fee € 20.563 per year") == (20.56, "EUR")


@pytest.mark.usefixtures("euro_grouping")
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tuition fee € 20.563 per year", (20563.0, "EUR")),
        ("fee: €18.750,00", (18750.0, "EUR")),
        ("EUR 1.234.567", (1234567.0, "EUR")),
        ("20.563 EUR per year", (20563.0, "EUR")),
        ("€ 2.314,50 statutory", (2314.5, "EUR")),
    ],
)
def test_grouped_euros(text: str, expected: tuple[float, str]) -> None:
    assert parse_money(text) == expected


@pytest.mark.usefixtures("euro_grouping")
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("€ 20.56 admin fee", (20.56, "EUR")),
        ("€20,563 per year", (20563.0, "EUR")),
        ("US$ 1,200.50", (1200.5, "USD")),
    ],
)
def test_other_formats_unchanged(text: str, expected: tuple[float, str]) -> None:
    assert parse_money(text) == expected


@pytest.mark.usefixtures("euro_grouping")
def test_population_tuition_table_reads_grouped_euros() -> None:
    text = (
        "Tuition fees 2027-2028. EU/EEA students: € 2.601 per year. "
        "Non-EU/EEA students: € 20.563 per year."
    )
    builder = ClaimBuilder(
        source_url="https://example.edu/fees",
        specificity=SourceSpecificity.PROGRAM_INTAKE,
        official_domain=True,
    )
    amounts = {c.normalized_value["amount"] for c in extraction.extract_costs(text, builder)}
    assert amounts == {2601.0, 20563.0}
