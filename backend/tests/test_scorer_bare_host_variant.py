"""Scorer: a leading ``www.`` on the host is a canonical variant (owner, 2026-10-26).

Track B §1.1: Exa returned usp's gold ``https://www.icmc.usp.br/en/…`` as
``https://icmc.usp.br/en/…`` and Tavily delft's ``https://www.tudelft.nl/…`` as
``https://tudelft.nl/…``; the scorer read each as another page, so a hit scored
wrong. The owner signed the bare-host rule: a URL that differs from the gold (or
a twin) only by a leading ``www.`` is the same page. Measurement only: nothing in
the pipeline changes. URLs are written for the test (the dev3 gold shape).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.research import live, scorecard
from evaluation.research.metrics import (
    adjudicate_programme_pages,
    same_programme_page,
    score,
)
from evaluation.research.schema import Dataset, Observation
from tests.test_scorer_programme_outcomes import _capture, _dataset, _pages

GOLD = "https://www.icmc.usp.br/en/admission/undergraduate/computer-science"
BARE = "https://icmc.usp.br/en/admission/undergraduate/computer-science"


@pytest.mark.parametrize(
    ("returned", "gold"),
    [
        (BARE, GOLD),
        (GOLD, BARE),
        ("https://WWW.ICMC.usp.br/en/admission/undergraduate/computer-science/", BARE),
        # The rule composes with the other canonical variants.
        ("https://tudelft.nl/en/2027/bachelor.html", "https://www.tudelft.nl/en/bachelor"),
        ("https://uni.edu/plan?p7_code=1", "https://www.uni.edu/plan?p7_code=1"),
        ("https://www.uni.edu:8443/plan", "https://uni.edu:8443/plan"),
    ],
)
def test_a_leading_www_is_a_canonical_variant(returned: str, gold: str) -> None:
    assert same_programme_page(returned, gold)


@pytest.mark.parametrize(
    ("returned", "gold"),
    [
        # Another subdomain is another host.
        ("https://cs.usp.br/en/admission/undergraduate/computer-science", GOLD),
        ("https://www2.icmc.usp.br/en/admission/undergraduate/computer-science", GOLD),
        ("https://www.www.icmc.usp.br/en/admission/undergraduate/computer-science", BARE),
        ("https://usp.br/en/admission/undergraduate/computer-science", BARE),
        ("https://wwwicmc.usp.br/en/admission/undergraduate/computer-science", BARE),
        # Another registrable domain, even one that ends the same.
        ("https://www.icmc-usp.br/en/admission/undergraduate/computer-science", GOLD),
        # "www." in the path is not the host.
        ("https://uni.edu/www.uni.edu/plan", "https://uni.edu/plan"),
        # A host left without a dot is not folded.
        ("https://com/plan", "https://www.com/plan"),
        # The path and query still decide.
        (BARE + "-ba", GOLD),
        ("https://uni.edu/plan?p7_code=1", "https://www.uni.edu/plan?p7_code=2"),
        # Another port is another server.
        ("https://www.uni.edu:8443/plan", "https://uni.edu/plan"),
    ],
)
def test_no_other_host_is_merged(returned: str, gold: str) -> None:
    assert not same_programme_page(returned, gold)


def test_the_bare_host_page_scores_as_a_hit_not_wrong() -> None:
    dataset = _dataset(gold=GOLD)
    capture = _capture([BARE])
    assert adjudicate_programme_pages(dataset.cases[0], capture.observations[0]).outcome == "hit"
    assert _pages(score(dataset, capture)["metrics"]) == (1, 1, 1)


def test_a_bare_host_related_page_reads_related() -> None:
    dataset = _dataset(gold=GOLD, related=["https://www.icmc.usp.br/en/bsc-data-science"])
    capture = _capture(["https://icmc.usp.br/en/bsc-data-science"])
    assert (
        adjudicate_programme_pages(dataset.cases[0], capture.observations[0]).outcome == "related"
    )


@pytest.mark.parametrize(
    ("name", "case_id", "returned"),
    [
        # Exa's usp page (Track B §1.1, base5-dev3 all four columns).
        ("dev3.draft3.json", "usp", BARE),
        # Tavily's delft page (base5t-cohort off#1, on#2).
        (
            "ground_truth.reviewed11.json",
            "delft",
            "https://tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/"
            "bachelor-of-computer-science-and-engineering",
        ),
    ],
)
def test_the_track_b_bare_host_pages_score_hits(name: str, case_id: str, returned: str) -> None:
    data = Path(live.__file__).parent / "data"
    dataset = Dataset.model_validate_json((data / name).read_text(encoding="utf-8"))
    case = next(c for c in dataset.cases if c.id == case_id)
    observation = Observation(case_id=case_id, programme_urls=[returned])
    assert adjudicate_programme_pages(case, observation).outcome == "hit"


def test_gold_seen_finds_the_bare_host_page_in_search_results() -> None:
    dataset = _dataset(gold=GOLD)
    trace = {"search_results": [{"family": "field_and_degree", "urls": [BARE]}]}
    seen = scorecard.gold_seen(dataset.cases[0], _capture([]).observations[0], trace)
    assert seen["stage"] == "returned", seen
