"""Award statements read in the page's own words (NTU Nanyang Global, 2026-09-28 oracle run).

Sentences are quoted from the live page the oracle read; each rule is generic.
"""

from app.adapters.scholarship.web_scholarships import (
    _ALL_NATIONALITIES,
    _NORMAL_DURATION,
    _living_allowance,
    _renewal_condition,
)


def test_a_retention_grade_is_read_with_its_scale_and_review_period():
    text = (
        "Scholarship holder is required to maintain a minimum Cumulative Grade Point Average "
        "(CGPA) of 3.5 over 5.0. Academic performance will be reviewed every semester."
    )
    value, _quote = _renewal_condition(text)
    assert value == {"cgpa_gte": 3.5, "scale": 5.0, "review": "each_semester"}


def test_a_grade_without_its_scale_is_not_a_renewal_condition():
    assert _renewal_condition("Maintain a minimum CGPA of 3.5 to keep the award.") is None


def test_no_review_period_is_invented():
    value, _ = _renewal_condition("Keep a minimum GPA of 3.0 out of 4.0.")
    assert value == {"cgpa_gte": 3.0, "scale": 4.0}


def test_open_to_all_nationalities_is_read_and_a_restriction_is_not():
    assert _ALL_NATIONALITIES.search("Eligibility Open to all nationalities. Successful awardees")
    assert not _ALL_NATIONALITIES.search("Open only to citizens of Singapore.")


def test_normal_programme_duration_is_a_duration_in_words():
    assert _NORMAL_DURATION.search("The scholarship covers up to the normal programme duration")


def test_a_whole_allowance_is_an_integer():
    value, _ = _living_allowance("Living allowance of S$6,500 per academic year.")
    assert value == {"currency": "SGD", "amount": 6500, "period": "academic_year"}
    assert type(value["amount"]) is int
