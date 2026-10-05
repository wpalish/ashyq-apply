"""Plan rule AY-1: tables are read for the applicant's academic year."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.pipeline import runner
from app.pipeline.runner import ResearchRunner, applicant_academic_year


@pytest.mark.parametrize(
    ("term", "year", "expected"),
    [
        ("fall", 2027, "2027/28"),
        ("winter", 2027, "2027/28"),
        ("spring", 2027, "2026/27"),
        ("summer", 2027, "2026/27"),
        ("fall", 2029, "2029/30"),
    ],
)
def test_the_academic_year_an_intake_begins_in(term, year, expected):
    assert applicant_academic_year(term, year) == expected


def stub(term: str = "fall", year: int = 2027) -> SimpleNamespace:
    return SimpleNamespace(
        profile=SimpleNamespace(context=SimpleNamespace(intake_term=term, intake_year=year)),
        settings=SimpleNamespace(academic_year="2026/27"),
    )


def test_off_by_default_the_server_year_is_used():
    assert runner.APPLICANT_ACADEMIC_YEAR is False
    assert ResearchRunner._academic_year(stub()) == "2026/27"  # type: ignore[arg-type]


def test_on_the_applicant_year_is_used(monkeypatch):
    monkeypatch.setattr(runner, "APPLICANT_ACADEMIC_YEAR", True)
    assert ResearchRunner._academic_year(stub()) == "2027/28"  # type: ignore[arg-type]
