"""Scorer: a trailing ``.htm`` / ``.html`` is a canonical variant (loss stages v3 §7).

KU Leuven's gold is ``…/SC_51016742.htm``; the ``local_language`` family
returned ``…/SC_51016742`` at rank 2, and the scorer wrote ``gold_seen=never``
because ``same_programme_page`` kept the extension. Measurement only: nothing
in the pipeline changes. URLs are written for the test (the dev3 gold shape).
"""

from __future__ import annotations

import pytest

from evaluation.research import scorecard
from evaluation.research.metrics import same_programme_page, score
from tests.test_scorer_programme_outcomes import _capture, _dataset, _pages

BASE = "https://onderwijsaanbod.kuleuven.be/opleidingen/n"
GOLD_HTM = f"{BASE}/SC_51016742.htm"
BARE = f"{BASE}/SC_51016742"


@pytest.mark.parametrize(
    ("returned", "gold"),
    [
        (BARE, GOLD_HTM),
        (GOLD_HTM, BARE),
        (f"{BARE}.html", GOLD_HTM),
        (f"{BARE}.HTM", BARE),
        (f"{BARE}/", GOLD_HTM),
        ("https://uni.edu/2027/computing.html", "https://uni.edu/computing"),
        ("https://uni.edu/computing/index.html", "https://uni.edu/computing.htm"),
        ("https://uni.edu/plan.htm?p7_code=1", "https://uni.edu/plan?p7_code=1"),
    ],
)
def test_an_html_extension_is_a_canonical_variant(returned: str, gold: str) -> None:
    assert same_programme_page(returned, gold)


@pytest.mark.parametrize(
    ("returned", "gold"),
    [
        # Another page under the same stem is still another page.
        (f"{BASE}/SC_51016742/diploma_omschrijving", GOLD_HTM),
        (f"{BASE}/SC_51016743", GOLD_HTM),
        # Only .htm / .html: another extension is another document.
        ("https://uni.edu/computing.php", "https://uni.edu/computing"),
        ("https://uni.edu/computing.aspx", "https://uni.edu/computing.htm"),
        # A query parameter still identifies the page.
        ("https://uni.edu/plan.htm?p7_code=1", "https://uni.edu/plan?p7_code=2"),
        # The extension of a directory name is not a page extension.
        ("https://uni.edu/a.html/b", "https://uni.edu/a/b"),
        # A bare ".html" segment is not a page with an extension.
        ("https://uni.edu/x/.html", "https://uni.edu/x"),
    ],
)
def test_what_is_still_another_page(returned: str, gold: str) -> None:
    assert not same_programme_page(returned, gold)


def test_the_bare_page_scores_as_a_hit() -> None:
    metrics = score(_dataset(gold=GOLD_HTM), _capture([BARE]))["metrics"]
    assert _pages(metrics) == (1, 1, 1)


def test_gold_seen_finds_the_bare_page_in_search_results() -> None:
    dataset = _dataset(gold=GOLD_HTM)
    case = dataset.cases[0]
    observation = _capture([]).observations[0]
    trace = {"search_results": [{"family": "local_language", "urls": [GOLD_HTM[:-4] + "/x", BARE]}]}
    seen = scorecard.gold_seen(case, observation, trace)
    assert seen["stage"] == "returned", seen
    assert seen["seen_as"] == ["returned:local_language"], seen
