"""Which way a right-valued claim's quote relates to the reviewer's.

Synthetic throughout: no universities, no network, no corpus.
"""

from __future__ import annotations

from evaluation.research.schema import Capture
from evaluation.research.support_report import (
    NEITHER,
    OTHER_PAGE,
    OURS_IN_THEIRS,
    THEIRS_IN_OURS,
    summarise,
    support_shapes,
)
from tests.test_scope_report import SCOPE, _capture, _dataset


def _with_excerpt(capture: Capture, excerpt: str, url: str = "https://example.edu/entry"):
    raw = capture.model_dump(mode="json")
    raw["observations"][0]["predictions"][0]["evidence"].update(excerpt=excerpt, url=url)
    return Capture.model_validate(raw)


def test_a_window_around_the_reviewers_words_is_theirs_in_ours():
    capture = _with_excerpt(
        _capture(dict(SCOPE)), "Applicants need an IELTS overall 6.5 with no band below 6.0."
    )
    [row] = support_shapes(_dataset(SCOPE), capture)
    assert row.shape == THEIRS_IN_OURS


def test_a_quote_inside_the_reviewers_is_what_the_scorer_counts():
    capture = _with_excerpt(_capture(dict(SCOPE)), "overall 6.5")
    [row] = support_shapes(_dataset(SCOPE), capture)
    assert row.shape == OURS_IN_THEIRS


def test_unrelated_quotes_on_the_same_page_are_neither():
    capture = _with_excerpt(_capture(dict(SCOPE)), "English requirements vary by programme.")
    [row] = support_shapes(_dataset(SCOPE), capture)
    assert row.shape == NEITHER


def test_another_page_is_named_as_such():
    capture = _with_excerpt(
        _capture(dict(SCOPE)), "IELTS overall 6.5", url="https://example.edu/other"
    )
    [row] = support_shapes(_dataset(SCOPE), capture)
    assert row.shape == OTHER_PAGE


def test_a_wrong_value_is_not_this_reports_business():
    assert support_shapes(_dataset(SCOPE), _capture(dict(SCOPE), value=7.0)) == []
    assert "no value-correct claims" in summarise([])
