from datetime import date

from app.pipeline.runner import _previous_cycle


def test_a_date_before_the_cycle_cutoff_is_previous_cycle():
    assert _previous_cycle([date(2026, 5, 4)], "fall", 2027)


def test_dates_in_the_application_window_are_not():
    assert not _previous_cycle([date(2026, 10, 1)], "fall", 2027)
    assert not _previous_cycle([date(2027, 1, 15)], "fall", 2027)


def test_one_current_date_keeps_the_deadline():
    assert not _previous_cycle([date(2026, 5, 4), date(2026, 12, 1)], "fall", 2027)


def test_unknown_term_or_no_dates_changes_nothing():
    assert not _previous_cycle([date(2020, 1, 1)], "anytime", 2027)
    assert not _previous_cycle([None], "fall", 2027)


def test_january_intake_cutoff_rolls_back_a_year():
    assert _previous_cycle([date(2025, 11, 1)], "spring", 2027)
    assert not _previous_cycle([date(2026, 3, 1)], "spring", 2027)
