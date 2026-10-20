"""A KB fee is a finite figure or nothing (security review 2026-10-22, SR2-06).

``float`` reads ``"nan"``, ``"inf"`` and ``"1e400"``; a draft that carried one
built a KB fact whose value Python's ``json`` writes as ``NaN``/``Infinity``,
and the API's JSON encoder refuses that, so every catalogue page and result
listing the university answered 500. The draft reader now takes no such
number, and the runtime reads no such fee.
"""

from __future__ import annotations

import json
import math

import pytest

from app.knowledge.claims import tuition_value
from evaluation.research.expert import kb_build
from evaluation.research.expert.core_drafts import _number


@pytest.mark.parametrize(
    "raw", ["nan", "NaN", "inf", "-inf", "Infinity", "1e400", math.nan, math.inf]
)
def test_a_draft_number_is_finite(raw: object) -> None:
    assert _number(raw) is None


@pytest.mark.parametrize("raw", ["27,650", 27650, 49581.6, "0", 0])
def test_ordinary_draft_numbers_still_read(raw: object) -> None:
    assert _number(raw) is not None


def test_a_range_with_an_infinite_bound_is_not_kept() -> None:
    value, _problem = kb_build.tuition_range(
        {"min": "27,650", "max": "inf", "currency": "GBP"}, "between £27,650 and inf"
    )
    assert value is None


@pytest.mark.parametrize(
    "value",
    [
        {"amount": math.nan, "currency": "EUR"},
        {"amount": math.inf, "currency": "EUR"},
        {"amount": -1500, "currency": "EUR"},
        {"min": math.nan, "max": 30000, "currency": "GBP"},
        {"min": 1000, "max": math.inf, "currency": "GBP"},
        {"min": 30000, "max": 20000, "currency": "GBP"},
    ],
)
def test_the_runtime_reads_no_fee_that_is_not_a_figure(value: dict) -> None:
    assert tuition_value(value) is None


def test_the_runtime_still_reads_a_fee_and_a_range() -> None:
    assert tuition_value({"amount": 0, "currency": "EUR"}) == {"amount": 0.0, "currency": "EUR"}
    found = tuition_value({"min": 27650, "max": 34670, "currency": "GBP"})
    assert found == {
        "amount": 34670.0,
        "currency": "GBP",
        "range_low": 27650.0,
        "range_high": 34670.0,
    }
    json.dumps(found, allow_nan=False)
