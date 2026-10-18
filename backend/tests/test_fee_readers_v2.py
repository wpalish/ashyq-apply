"""FE-2 (``FEE_READERS_V2``, ``--fee-readers-v2``): UK fee-status rows and
per-course fee tables (core-gap analysis 2026-10-18, change 4).

Imperial's programme page prints "Home fee 2027 entry £10,050 per year …
Overseas fee 2027 entry £47,800 per year": neither word was a population, so
no tuition was read. Trinity's undergraduate fees page is one table of every
course and year, the non-EU first-year fee in its own column: no tuition
keyword sits beside the money, so nothing was read. Both readers abstain
whenever the row or the page is not unmistakably the one asked about.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters import extraction
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import ClaimBuilder, extract_costs, fee_status_population
from app.adapters.fetching import Fetcher
from app.adapters.scope_reader import read_scope
from app.adapters.structured_costs import extract_programme_fee_rows
from app.domain.enums import ClaimType, DegreeLevel

BACKEND = Path(__file__).resolve().parents[1]

#: Imperial's programme page as ``readable_text`` gives it (2027 entry page).
IMPERIAL = (
    "Fees and funding  Home fee  Overseas fee     Home fee  Home fee  2027 entry   £10,050   "
    "per year  Home fees explained  It is current Imperial policy to charge Home fees in line "
    "with the Government's fee cap.  Learn more about additional costs  Overseas fee  "
    "Overseas fee  2027 entry   £47,800   per year  Which fee you pay  Whether you pay the "
    "Home or Overseas fee depends on your fee status."
)
IMPERIAL_TITLE = "Computing BEng | Study | Imperial College London"


@pytest.fixture
def v2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extraction, "FEE_READERS_V2", True)


def _builder(
    text: str,
    *,
    title: str = IMPERIAL_TITLE,
    program: str | None = "Computer Science",
    year: str = "2027/28",
) -> ClaimBuilder:
    builder = ClaimBuilder(
        source_url="https://www.example.ac.uk/study/courses/undergraduate/2027/computing-beng",
        page_title=title,
        program=program,
        academic_year=year,
        official_domain=True,
        accessed_at=datetime(2026, 10, 18, tzinfo=UTC),
        scope=read_scope(text, title=title),
        page_text=text,
    )
    builder.requested_academic_year = year
    return builder


def _tuition(builder: ClaimBuilder, text: str) -> list[tuple[float, str, str | None, str | None]]:
    extract_costs(text, builder)
    return [
        (
            c.normalized_value["amount"],
            c.normalized_value["currency"],
            c.scope.population if c.scope else None,
            c.scope.academic_year if c.scope else None,
        )
        for c in builder.claims
        if c.claim_type is ClaimType.TUITION
    ]


def test_the_rule_is_off_by_default() -> None:
    assert extraction.FEE_READERS_V2 is False
    assert _tuition(_builder(IMPERIAL), IMPERIAL) == []


class TestFeeStatusRows:
    def test_overseas_is_the_international_fee_and_home_the_domestic_one(self, v2: None) -> None:
        assert _tuition(_builder(IMPERIAL), IMPERIAL) == [
            (10050.0, "GBP", "domestic", "2027/28"),
            (47800.0, "GBP", "international", "2027/28"),
        ]

    def test_the_excerpt_quotes_the_overseas_row(self, v2: None) -> None:
        builder = _builder(IMPERIAL)
        extract_costs(IMPERIAL, builder)
        overseas = next(c for c in builder.claims if c.subject_key == "international")
        assert "Overseas fee 2027 entry £47,800 per year" in " ".join(
            overseas.original_text_excerpt.split()
        )

    @pytest.mark.parametrize(
        ("word", "population"),
        [
            ("Overseas", "international"),
            ("International", "international"),
            ("Home", "domestic"),
            ("non-EU", "non-EU/EEA"),
            ("Non EU/EEA", "non-EU/EEA"),
            ("Standard", None),
        ],
    )
    def test_fee_status_words(self, word: str, population: str | None) -> None:
        assert fee_status_population(word) == population

    def test_international_fee_wording(self, v2: None) -> None:
        text = "International fee 2027/28: £39,000 per year. Home fee 2027/28: £9,535 per year."
        assert _tuition(_builder(text), text) == [
            (39000.0, "GBP", "international", "2027/28"),
            (9535.0, "GBP", "domestic", "2027/28"),
        ]

    def test_a_page_that_names_another_programme_is_left_alone(self, v2: None) -> None:
        title = "History BA | Study | Imperial College London"
        assert _tuition(_builder(IMPERIAL, title=title), IMPERIAL) == []

    def test_a_page_of_no_named_programme_or_level_is_left_alone(self, v2: None) -> None:
        assert _tuition(_builder(IMPERIAL, title="Fees", program=None), IMPERIAL) == []

    def test_a_fee_page_of_the_requested_level_is_read(self, v2: None) -> None:
        text = "Undergraduate students: Overseas fee 2027 entry £41,000 per year."
        builder = _builder(text, title="Undergraduate tuition fees", program=None)
        builder.requested_degree = "bachelor"
        assert read_scope(text, title="Undergraduate tuition fees").degree == "bachelor"
        assert _tuition(builder, text) == [(41000.0, "GBP", "international", "2027/28")]
        other = _builder(text, title="Undergraduate tuition fees", program=None)
        other.requested_degree = "master"
        assert _tuition(other, text) == []

    def test_another_entry_year_is_not_the_requested_fee(self, v2: None) -> None:
        text = "Overseas fee 2026 entry £46,000 per year"
        assert _tuition(_builder(text), text) == []
        both = "Overseas fee 2026 entry £46,000 per year Overseas fee 2027 entry £47,800 per year"
        assert _tuition(_builder(both), both) == [(47800.0, "GBP", "international", "2027/28")]

    def test_a_row_without_a_year_keeps_no_year(self, v2: None) -> None:
        text = "Overseas fee £47,800 per year"
        assert _tuition(_builder(text), text) == [(47800.0, "GBP", "international", None)]

    @pytest.mark.parametrize(
        "text",
        [
            "Overseas fee 2027 entry £1,250 per module",
            "Overseas fee 2027 entry £47,800",
            "Overseas fee for most courses 2027 entry £47,800 per year",
            "Overseas fee 2027 entry £47,800 per year Overseas fee 2027 entry £52,000 per year",
        ],
        ids=["module-price", "no-period", "words-between", "two-amounts"],
    )
    def test_abstains(self, v2: None, text: str) -> None:
        assert _tuition(_builder(text), text) == []

    def test_a_tuition_table_keeps_its_reading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        text = (
            "Tuition fees 2027-2028 EU/EEA students € 2,601 non-EU/EEA students € 20,000 "
            "Overseas fee 2027 entry £47,800 per year"
        )
        before = _tuition(_builder(text), text)
        monkeypatch.setattr(extraction, "FEE_READERS_V2", True)
        assert _tuition(_builder(text), text) == before
        assert [population for _, _, population, _ in before] == ["EU/EEA", "non-EU/EEA"]


#: Trinity's per-course fee table, as its page prints it (rows abridged).
_HEAD = (
    "<thead><tr><th>Academic Year</th><th>School</th><th>Course Name</th><th>Course Code</th>"
    "<th>Fee Profile Code</th><th>EU Tuition</th><th>EU Student Contribution</th>"
    "<th>EU Student Total Fee - Year 1</th><th>Non-EU Student Total Fee - Year 1</th>"
    "</tr></thead>"
)


def _row(year: str, school: str, course: str, code: str, non_eu: str) -> str:
    cells = [year, school, course, code, "UF_000031", "€4,982.00", "€2,350.00", "€7,332.00"]
    return "<tr>" + "".join(f"<td>{c}</td>" for c in [*cells, non_eu]) + "</tr>"


_CS = "Computer Science (Year 5 is postgraduate)"
_SCSS = "School of Computer Science &amp; Statistics"
TCD_ROWS = [
    _row("2027/28", _SCSS, _CS, "UICS-ICSC-2F", "€30,450.00"),
    _row(
        "2027/28",
        "TCD-Multidisciplinary",
        "Computer Science and Geography",
        "UBJH-1F",
        "€30,450.00",
    ),
    _row("2027/28", "Trinity Business School", "Business Studies", "UBBS-1F", "€23,250.00"),
    _row("2026/27", _SCSS, _CS, "UICS-ICSC-2F", "€29,570.00"),
]


def _tcd(
    rows: list[str],
    *,
    head: str = _HEAD,
    heading: str = "Undergraduate Fees",
    programmes: tuple[str, ...] = ("Computer Science", "computer science"),
    degree: str | None = "bachelor",
    year: str = "2027/28",
) -> list[tuple[float, str, str | None, str | None, str | None]]:
    html = (
        "<html><head><title>Fees - Courses | Trinity College Dublin</title></head><body><main>"
        f"<h2>{heading}</h2><table>{head}<tbody>{''.join(rows)}</tbody></table></main></body></html>"
    )
    text = extraction.readable_text(html)
    builder = _builder(
        text, title="Fees - Courses | Trinity College Dublin", program=None, year=year
    )
    builder.requested_programmes = programmes
    builder.requested_degree = degree
    claims = extract_programme_fee_rows(build_document_ir(html, "https://www.tcd.ie/x/"), builder)
    return [
        (
            c.normalized_value["amount"],
            c.normalized_value["currency"],
            c.scope.population if c.scope else None,
            c.scope.academic_year if c.scope else None,
            c.scope.degree if c.scope else None,
        )
        for c in claims
    ]


class TestPerCourseFeeTable:
    def test_the_requested_course_and_year_in_the_international_column(self) -> None:
        assert _tcd(TCD_ROWS) == [(30450.0, "EUR", "non-EU/EEA", "2027/28", "bachelor")]

    def test_the_other_year_of_the_same_course(self) -> None:
        assert _tcd(TCD_ROWS, year="2026/27") == [
            (29570.0, "EUR", "non-EU/EEA", "2026/27", "bachelor")
        ]

    def test_a_year_the_table_does_not_list(self) -> None:
        assert _tcd(TCD_ROWS, year="2028/29") == []

    def test_a_joint_course_is_another_course(self) -> None:
        rows = [r for r in TCD_ROWS if _CS not in r]
        assert _tcd(rows) == []

    def test_two_rows_naming_the_course_abstain(self) -> None:
        twin = _row("2027/28", "Another School", "Computer Science", "X-1F", "€31,000.00")
        assert _tcd([*TCD_ROWS, twin]) == []

    def test_another_level_table_is_left_alone(self) -> None:
        assert _tcd(TCD_ROWS, heading="Postgraduate Fees") == []

    def test_no_international_column_no_claim(self) -> None:
        head = _HEAD.replace("Non-EU Student Total Fee - Year 1", "Total")
        assert _tcd(TCD_ROWS, head=head) == []

    def test_a_continuing_years_column_is_not_the_first_year_fee(self) -> None:
        head = _HEAD.replace("Non-EU Student Total Fee - Year 1", "Non-EU Fee - Years 2+")
        assert _tcd(TCD_ROWS, head=head) == []

    def test_no_requested_programme_no_claim(self) -> None:
        assert _tcd(TCD_ROWS, programmes=()) == []


@pytest.mark.asyncio
async def test_the_cost_adapter_reads_the_course_row_only_under_the_rule(
    settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "site"
    (root / "tcd").mkdir(parents=True)
    (root / "tcd/fees.html").write_text(
        "<html><head><title>Fees - Courses | Trinity College Dublin</title></head><body><main>"
        f"<h2>Undergraduate Fees</h2><table>{_HEAD}<tbody>{''.join(TCD_ROWS)}</tbody></table>"
        "</main></body></html>",
        encoding="utf-8",
    )
    candidate = Candidate(
        name="Trinity College Dublin",
        country="Ireland",
        city="Dublin",
        costs_url="fixture://tcd/fees.html",
        programs=[
            CandidateProgram(
                name="Computer Science", field="computer science", degree=DegreeLevel.BACHELOR
            )
        ],
    )

    async def read() -> list[tuple[object, str | None]]:
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as fetcher:
            _, out = await WebCostAdapter(fetcher, "2027/28").fetch(candidate)
        return [
            (c.normalized_value, c.scope.population if c.scope else None)
            for c in out.claims
            if c.claim_type is ClaimType.TUITION
        ]

    assert await read() == []
    monkeypatch.setattr(extraction, "FEE_READERS_V2", True)
    assert await read() == [({"amount": 30450.0, "currency": "EUR"}, "non-EU/EEA")]


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--fee-readers-v2" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "fe2_module.FEE_READERS_V2 = True" in source
    assert '["--fee-readers-v2"]' in source
