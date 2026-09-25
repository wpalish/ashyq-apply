"""A living allowance and a duration in words (NTU Nanyang, corpus keys
coverage.living and duration), and the currency of a country-prefixed dollar.
"""

from __future__ import annotations

from app.adapters.extraction import parse_money
from app.adapters.scholarship.web_scholarships import _NORMAL_DURATION, _living_allowance
from evaluation.research.mapping import AWARD_KEYS


def test_a_prefixed_dollar_keeps_its_country():
    assert parse_money("S$6,500 per year") == (6500.0, "SGD")
    assert parse_money("HK$182,000") == (182000.0, "HKD")
    assert parse_money("350,000 KRW") == (350000.0, "KRW")
    assert parse_money("$5,000") == (5000.0, "USD")


def test_a_living_allowance_needs_amount_and_period():
    text = "A living allowance of S$6,500 per academic year is provided."
    value, quote = _living_allowance(text)  # type: ignore[misc]
    assert value == {"currency": "SGD", "amount": 6500.0, "period": "academic_year"}
    assert quote in text
    assert _living_allowance("A monthly living subsidy of 350,000 KRW.")[0]["period"] == "month"  # type: ignore[index]
    assert _living_allowance("A living allowance is provided.") is None
    assert _living_allowance("A living allowance of S$6,500 is provided.") is None


def test_the_programmes_normal_duration_is_read_in_words():
    assert _NORMAL_DURATION.search("tenable for the normal duration of the programme")
    assert _NORMAL_DURATION.search("for the minimum candidature")
    assert not _NORMAL_DURATION.search("the programme takes four years")


def test_the_scorer_files_them_under_the_corpus_keys():
    assert AWARD_KEYS["scholarship_living_allowance"] == "coverage.living"
    assert AWARD_KEYS["scholarship_duration"] == "duration"
