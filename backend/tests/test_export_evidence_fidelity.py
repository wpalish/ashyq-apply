"""Accepted evidence survives XLSX save/reload without becoming a formula."""

from __future__ import annotations

import io
from datetime import UTC, datetime

import pytest
from openpyxl import load_workbook

from app.domain.enums import ClaimType
from app.export.tabular import to_xlsx
from app.schemas.claim import MAX_EXCERPT_CHARS, ClaimOut
from app.schemas.result import ProgramResult
from tests.conftest import make_claim

_CONDITION = (
    "The scholarship covers up to the normal programme duration on condition that the "
    "scholarship holder maintain a record of good academic performance and exemplary conduct."
)
_POLICY = {
    "conditions": [_CONDITION],
    "tuition": {"fraction": 1.0, "basis": "subsidised_after_tuition_grant"},
    "living": {"currency": "SGD", "fixed_amount": 6500, "period": "academic_year"},
    "housing": {
        "currency": "SGD",
        "maximum": 2000,
        "period": "academic_year",
        "requires": "scholarship holders who reside in NTU hostels only",
    },
    "travel": {
        "currency": "SGD",
        "maximum": 8000,
        "requires": "an overseas programme",
        "terms": "Travel Grant Form",
        "cohorts_from": "AY2025",
    },
}
_ACTUAL_QUOTE = (
    _CONDITION + "\nFull coverage of subsidised tuition fees (after Tuition Grant)."
    "\nLiving allowance of S$6,500 per academic year."
    "\nAccommodation allowance of up to S$2,000 per academic year."
    "\n(Applicable to scholarship holders who reside in NTU hostels only.)"
    "\nTravel grant of up to S$8,000 for an overseas programme subject to terms and conditions "
    "in the Travel Grant Form (for new cohorts from AY2025)."
)
_CAP_QUOTE = "Published conditions: " + "x" * 549 + " Last condition must survive."
_URL = (
    "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
    "scholarship-opportunities/detail/nanyang-scholarship"
)
_HEADERS = [
    "University",
    "Program",
    "Claim type",
    "Value",
    "Status",
    "Specificity",
    "Accessed",
    "Source URL",
    "Excerpt",
]


def _result(value: object, excerpt: str) -> ProgramResult:
    claim = make_claim(
        ClaimType.SCHOLARSHIP_COVERAGE.value,
        value,
        url=_URL,
        specificity="scholarship_administrator",
        subject_key="Nanyang Global Scholarship",
        accessed_at=datetime(2026, 9, 29, 8, 30, 34, 955612, tzinfo=UTC),
        academic_year="2026/27",
    )
    payload = claim.model_dump()
    payload["original_text_excerpt"] = excerpt
    return ProgramResult(
        id="result-1",
        run_id="run-1",
        university="Nanyang Technological University",
        university_id="ntu",
        country="Singapore",
        city="Singapore",
        program="Bachelor Of Computing In Computer Science",
        degree="bachelor",
        intake="Fall 2027",
        claims=[ClaimOut(id="claim-1", **payload)],
    )


def test_complete_nested_policy_survives_workbook_round_trip():
    result = _result(_POLICY, _ACTUAL_QUOTE)
    workbook = load_workbook(io.BytesIO(to_xlsx([result])))

    assert workbook.sheetnames == ["Shortlist", "Evidence", "Open questions"]
    evidence = workbook["Evidence"]
    assert [cell.value for cell in evidence[1]] == _HEADERS
    expected = str(result.claims[0].normalized_value)
    assert len(expected) > 200
    assert evidence["D2"].value == expected
    assert "Travel Grant Form" in evidence["D2"].value
    assert "AY2025" in evidence["D2"].value
    assert "scholarship holders who reside in NTU hostels only" in evidence["D2"].value
    assert evidence["H2"].value == _URL


@pytest.mark.parametrize("excerpt", [_ACTUAL_QUOTE, _CAP_QUOTE], ids=["actual-552", "cap-600"])
def test_complete_accepted_excerpt_survives_workbook_round_trip(excerpt):
    assert len(_ACTUAL_QUOTE) == 552
    assert len(_CAP_QUOTE) == MAX_EXCERPT_CHARS
    result = _result(_POLICY, excerpt)
    workbook = load_workbook(io.BytesIO(to_xlsx([result])))

    assert result.claims[0].original_text_excerpt == excerpt
    assert workbook["Evidence"]["I2"].value == excerpt


@pytest.mark.parametrize("lead", ["=", "+", "-", "@"])
def test_long_untrusted_evidence_stays_complete_and_inert(lead):
    value = lead + 'HYPERLINK("https://attacker.invalid/", "' + "x" * 480 + '")'
    result = _result(value, value)
    workbook = load_workbook(io.BytesIO(to_xlsx([result])), data_only=False)
    evidence = workbook["Evidence"]

    for cell in (evidence["D2"], evidence["I2"]):
        assert cell.value == "'" + value
        assert cell.data_type == "s"
