"""v3-M2: the scorer's related outcome and canonical variants of the programme page.

Wayfinder programme-discovery ticket 03 (owner, 2026-10-18), as the v3 plan's
row M2 lands it:

* Q2 - a canonical variant is the same page: the same path with or without an
  intake-year segment, a trailing slash or ``index.html``; ``?lang=`` only when
  the page's own ``<html lang>`` confirms the language. Every other query
  parameter stays part of the identity (``?p7_code=`` names a programme).
* Q3 - a related programme (a sibling specialisation, a major page, the field's
  bachelor in another faculty) is neither a hit nor a wrong page: it leaves the
  precision denominator and the case reads ``related``. Ticket 16 Q6: discovery
  may also record one it refused only as related, on the trace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.research import live, scorecard
from evaluation.research.metrics import adjudicate_programme_pages, same_programme_page, score
from evaluation.research.schema import Capture, Dataset, Observation

GOLD = "https://www.uni.ac.uk/study/courses/undergraduate/computing-beng/"
SIBLING = "https://study.uni.edu/bachelor-of-computer-science-data-science"
SCOPE = {"university": "Example University"}


def _dataset(gold: str = GOLD, related: list[str] | None = None, status: str = "known") -> Dataset:
    evidence = {
        "url": gold,
        "excerpt": "BEng Computing",
        "scope": SCOPE,
        "accessed_on": "2026-10-18",
        "source_type": "official",
    }
    case: dict[str, Any] = {
        "id": "uni",
        "dataset_version": "test",
        "university": "Example University",
        "domain": "uni.ac.uk",
        "country": "United Kingdom",
        "site_types": ["static"],
        "request": SCOPE,
        "programme_urls": [gold] if status == "known" else [],
        "programme_status": status,
        "programme_evidence": [evidence] if status == "known" else [],
        "labels": [],
        "review": {
            "status": "human_verified",
            "prepared_by": "test",
            "reviewer": "test",
            "verified_on": "2026-10-18",
            "notes": "test",
        },
    }
    if related is not None:
        case["related_programme_urls"] = related
    return Dataset.model_validate({"version": "test", "split": "development", "cases": [case]})


def _observation(urls: list[str], **extra: Any) -> Observation:
    return Observation.model_validate({"case_id": "uni", "programme_urls": urls, **extra})


def _capture(urls: list[str], **extra: Any) -> Capture:
    return Capture.model_validate(
        {
            "pipeline_sha": "abc",
            "captured_at": "20261018T000000Z",
            "mode": "live",
            "config": {},
            "observations": [{"case_id": "uni", "programme_urls": urls, **extra}],
        }
    )


def _pages(metrics: dict[str, Any]) -> tuple[int, int, int]:
    recall, precision = metrics["programme_page_recall"], metrics["programme_page_precision"]
    return recall["numerator"], precision["numerator"], precision["denominator"]


# --- Q2: canonical variants ----------------------------------------------------


@pytest.mark.parametrize(
    "returned",
    [
        # Imperial's shape: the intake year in the path beside the yearless gold.
        "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng",
        "https://www.uni.ac.uk/study/courses/undergraduate/computing-beng",
        "https://www.uni.ac.uk/study/courses/undergraduate/computing-beng/index.html",
        "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng/index.html",
        "https://WWW.UNI.AC.UK/study/courses/undergraduate/computing-beng/",
    ],
)
def test_a_canonical_variant_of_the_gold_page_is_a_hit(returned: str) -> None:
    assert same_programme_page(returned, GOLD)
    metrics = score(_dataset(), _capture([returned]))["metrics"]
    assert _pages(metrics) == (1, 1, 1)


def test_the_year_works_from_either_side() -> None:
    with_year = "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng"
    metrics = score(_dataset(gold=with_year), _capture([GOLD]))["metrics"]
    assert _pages(metrics) == (1, 1, 1)


@pytest.mark.parametrize(
    "returned,gold",
    [
        # Two intakes' pages are not one page: "with or without", not "any year".
        ("https://uni.edu/2026/computing", "https://uni.edu/2027/computing"),
        # A query parameter can name the programme; it is never dropped.
        ("https://uni.edu/plan?p7_code=1", "https://uni.edu/plan?p7_code=2"),
        ("https://uni.edu/plan?p7_code=1", "https://uni.edu/plan"),
        # Path case is meaning, as before.
        ("https://uni.edu/CS", "https://uni.edu/cs"),
        # A year that is the whole page name is not an intake segment of it.
        ("https://uni.edu/computing-2027", "https://uni.edu/computing"),
        # Another index document is not in the decision.
        ("https://uni.edu/computing/index.php", "https://uni.edu/computing"),
    ],
)
def test_what_is_still_another_page(returned: str, gold: str) -> None:
    assert not same_programme_page(returned, gold)


def test_lang_is_a_variant_only_when_the_page_says_so() -> None:
    gold = "https://www.rug.nl/bachelors/computing-science"
    returned = gold + "?lang=en"
    # Nothing recorded the page's own language: ?lang= stays part of the URL.
    assert _pages(score(_dataset(gold=gold), _capture([returned]))["metrics"]) == (0, 0, 1)
    # The page read <html lang="en">: the parameter only chose that language.
    confirmed = _capture([returned], programme_page_languages={returned: "en-GB"})
    assert _pages(score(_dataset(gold=gold), confirmed)["metrics"]) == (1, 1, 1)
    # The page read another language: the parameter did not land on English.
    other = _capture([returned], programme_page_languages={returned: "nl"})
    assert _pages(score(_dataset(gold=gold), other)["metrics"]) == (0, 0, 1)
    # Only the lang parameter goes; another one still identifies the page.
    with_code = "https://uni.edu/plan?p7_code=1&lang=en"
    assert same_programme_page(with_code, "https://uni.edu/plan?p7_code=1", "en")
    assert not same_programme_page(with_code, "https://uni.edu/plan?p7_code=2", "en")


def test_a_twin_of_the_returned_page_matches_up_to_a_variant() -> None:
    twin = "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng"
    returned = "https://www.uni.ac.uk/fr/etudes/computing-beng"
    capture = _capture([returned], programme_url_aliases={returned: [twin]})
    assert _pages(score(_dataset(), capture)["metrics"]) == (1, 1, 1)


def test_ranked_recall_reads_variants_too() -> None:
    variant = "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng"
    capture = _capture([], ranked_urls=["https://www.uni.ac.uk/", variant])
    assert score(_dataset(), capture)["metrics"]["recall_at_5"]["numerator"] == 1


# --- Q3: the related outcome ---------------------------------------------------


def test_a_labelled_related_programme_is_neither_a_hit_nor_a_wrong_page() -> None:
    unlabelled = score(_dataset(), _capture([SIBLING]))["metrics"]
    assert _pages(unlabelled) == (0, 0, 1)  # today: a wrong page
    dataset = _dataset(related=[SIBLING + "/"])
    labelled = score(dataset, _capture([SIBLING]))["metrics"]
    assert _pages(labelled) == (0, 0, 0)  # out of the wrong-page count, still no hit
    verdict = adjudicate_programme_pages(dataset.cases[0], _observation([SIBLING]))
    assert verdict.outcome == "related"
    assert verdict.related == {SIBLING} and not verdict.wrong


def test_a_related_programme_beside_the_gold_leaves_the_hit_alone() -> None:
    dataset = _dataset(related=[SIBLING])
    metrics = score(dataset, _capture([GOLD, SIBLING]))["metrics"]
    assert _pages(metrics) == (1, 1, 1)
    assert adjudicate_programme_pages(dataset.cases[0], _observation([GOLD, SIBLING])).outcome == (
        "hit"
    )


def test_a_wrong_page_outranks_a_related_one() -> None:
    dataset = _dataset(related=[SIBLING])
    observation = _observation([SIBLING, "https://www.uni.ac.uk/open-day"])
    verdict = adjudicate_programme_pages(dataset.cases[0], observation)
    assert verdict.outcome == "wrong"
    assert verdict.wrong == {"https://www.uni.ac.uk/open-day"}


def test_a_page_discovery_recorded_as_related_scores_related_and_counts_nowhere() -> None:
    """Ticket 16 Q6: refused only on the subject head, recorded, never returned (UCT)."""
    uct = "https://uni.ac.za/business-science-computer-science"
    capture = _capture([], related_programme_urls=[uct])
    assert _pages(score(_dataset(), capture)["metrics"]) == (0, 0, 0)
    verdict = adjudicate_programme_pages(_dataset().cases[0], capture.observations[0])
    assert verdict.outcome == "related"
    assert verdict.related == {uct}


def test_nothing_returned_and_nothing_related_is_a_miss() -> None:
    assert adjudicate_programme_pages(_dataset().cases[0], _observation([])).outcome == "missed"
    unknown = _dataset(status="unknown").cases[0]
    assert adjudicate_programme_pages(unknown, _observation([GOLD])).outcome == "unadjudicated"


def test_an_unknown_programme_with_a_labelled_related_one_is_adjudicated_against_it() -> None:
    """Dev4 (owner 2026-10-18): vut, taltech, boun, itu have no exact CS programme;
    the closest equivalent is labelled related. Returning it must read ``related``,
    not ``unadjudicated`` as the status-first check used to report."""
    unknown = _dataset(status="unknown", related=[SIBLING]).cases[0]
    verdict = adjudicate_programme_pages(unknown, _observation([SIBLING + "/"]))
    assert verdict.outcome == "related"
    assert verdict.related == {SIBLING}
    recorded = _observation([], related_programme_urls=[SIBLING])
    assert adjudicate_programme_pages(unknown, recorded).outcome == "related"
    # Nothing returned while a related programme is labelled: a miss.
    assert adjudicate_programme_pages(unknown, _observation([])).outcome == "missed"
    # Another page, with no exact gold to call it wrong: still unadjudicated.
    other = _observation(["https://study.uni.edu/open-day"])
    assert adjudicate_programme_pages(unknown, other).outcome == "unadjudicated"
    unlabelled = _observation([], related_programme_urls=["https://study.uni.edu/maths"])
    assert adjudicate_programme_pages(unknown, unlabelled).outcome == "unadjudicated"
    # Without related labels an unknown programme is never adjudicated.
    bare = _dataset(status="unknown").cases[0]
    assert adjudicate_programme_pages(bare, _observation([])).outcome == "unadjudicated"
    assert adjudicate_programme_pages(bare, _observation([SIBLING])).outcome == "unadjudicated"
    # Precision and recall still leave the unknown case out.
    metrics = score(_dataset(status="unknown", related=[SIBLING]), _capture([SIBLING]))
    assert _pages(metrics["metrics"]) == (0, 0, 0)


def test_a_corpus_without_related_labels_hashes_as_before() -> None:
    """The field is not serialised while empty, so every frozen digest stays."""
    assert "related_programme_urls" not in _dataset().model_dump_json()
    assert "related_programme_urls" in _dataset(related=[SIBLING]).model_dump_json()


# --- the harness and the scorecard ----------------------------------------------


def test_the_harness_reads_related_programmes_off_the_trace() -> None:
    trace = {
        "related_programmes": [
            {"url": SIBLING, "title": "Bachelor of Computer Science (Data Science)"},
            [SIBLING, "again"],
            ("https://uni.edu/maths-cs", "Mathematics and Computer Science"),
            "https://uni.edu/major-cs",
            {"title": "no url"},
            "not a url",
        ]
    }
    assert live.related_programmes(trace) == [
        SIBLING,
        "https://uni.edu/maths-cs",
        "https://uni.edu/major-cs",
    ]
    assert live.related_programmes({}) == []
    assert live.related_programmes(None) == []


def test_the_scorecard_counts_programme_outcomes_and_sees_variants(tmp_path: Path) -> None:
    variant = "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng"
    for arm, urls, extra in (
        ("off", [variant], {}),
        ("on", [], {"related_programme_urls": [SIBLING]}),
    ):
        target = tmp_path / f"uni-{arm}" / "20261018T000001Z"
        target.mkdir(parents=True)
        capture = _capture(urls, **extra).model_dump(mode="json")
        (target / "capture.json").write_text(json.dumps(capture))
    raw = {"canary": {"institutions": [{"discovery_trace": {"pages_read": [[variant, ""]]}}]}}
    (tmp_path / "uni-off/20261018T000001Z/uni.raw.json").write_text(json.dumps(raw))

    card = scorecard.build(_dataset(), scorecard.load_run(tmp_path))
    off, on = (card["arms"][a]["repetitions"][0] for a in ("off", "on"))
    assert off["programme_pages"] == {"uni": "hit"}
    assert on["programme_pages"] == {"uni": "related"}
    assert off["gold_seen"]["uni"]["stage"] == "confirmed"
    assert "read" in off["gold_seen"]["uni"]["seen_as"]
    text = scorecard.render(card)
    assert "| programme pages hit/wrong/related/missed | 1/0/0/0 | 0/0/1/0 |" in text


def test_a_university_named_with_its_acronym_beside_it_is_the_same_scope():
    from evaluation.research.metrics import dimension_matches

    assert dimension_matches(
        "university", "Karlsruhe Institute of Technology", "KIT, Karlsruhe Institute of Technology"
    )
    assert dimension_matches("university", "University of Oslo", "University of Oslo")
    assert not dimension_matches("university", "University of Oslo", "Oslo Metropolitan University")
    assert not dimension_matches("university", "University of Oslo", None)
