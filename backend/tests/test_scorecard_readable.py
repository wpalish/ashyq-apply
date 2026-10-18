"""Targets 3 and 4 as scorecard rows, on what the run could read (finish-algorithm ticket 03).

A case leaves both readable denominators when its ``access`` is ``BLOCKED`` or
half its requests failed in that repetition; a known core question leaves
target 4's readable denominator when every one of its labels is a PDF or sits
on a host whose every request failed. A non-English page and a case whose
programme page we did not find stay.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from evaluation.research import scorecard
from evaluation.research.schema import Dataset
from tests.test_scorecard import DEADLINE, TUITION_RIGHT, capture, dataset, evidence


def _raw(access: str, checked: int, failed: int) -> dict[str, Any]:
    return {
        "canary": {
            "institutions": [{"access": access, "pages_checked": checked, "pages_failed": failed}]
        }
    }


def _run(
    root: Path,
    reps: list[dict[str, Any]],
    *,
    raws: list[dict[str, Any] | None] | None = None,
    logs: list[str | None] | None = None,
) -> Path:
    for i, rep in enumerate(reps):
        target = root / "uni-on" / f"20261005T00000{i + 1}Z"
        target.mkdir(parents=True)
        (target / "capture.json").write_text(json.dumps(rep))
        raw = (raws or [None] * len(reps))[i]
        if raw is not None:
            (target / "uni.raw.json").write_text(json.dumps(raw))
        log = (logs or [None] * len(reps))[i]
        if log is not None:
            (target / "uni.log").write_text(log)
    return root


def _dataset(**label_urls: str) -> Dataset:
    """The test corpus with some labels' evidence moved to another URL."""
    raw = dataset().model_dump(mode="json")
    for label in raw["cases"][0]["labels"]:
        if label["key"] in label_urls:
            label["evidence"] = [evidence(label_urls[label["key"]], "moved")]
    return Dataset.model_validate(raw)


def _readable(card: dict[str, Any], index: int = 0) -> dict[str, Any]:
    return card["arms"]["on"]["repetitions"][index]["readable"]


def test_a_readable_case_counts_in_both_denominators(tmp_path: Path) -> None:
    run = _run(tmp_path, [capture([DEADLINE])], raws=[_raw("REACHED", 20, 2)])
    rows = _readable(scorecard.build(dataset(), scorecard.load_run(run)))
    assert rows["programme_found_on_readable"]["numerator"] == 1
    assert rows["programme_found_on_readable"]["denominator"] == 1
    assert rows["core_known_rate"] == {"numerator": 1, "denominator": 2, "value": 0.5}
    assert rows["core_known_readable_rate"] == rows["core_known_rate"]
    assert rows["wrong_programme_pages"] == 0
    assert rows["excluded"] == {}


def test_a_blocked_case_leaves_the_denominator(tmp_path: Path) -> None:
    run = _run(tmp_path, [capture([])], raws=[_raw("BLOCKED", 12, 12)])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    rows = _readable(card)
    assert rows["programme_found_on_readable"]["denominator"] == 0
    assert rows["core_known_readable_rate"]["denominator"] == 0
    # Today's denominator keeps it.
    assert rows["core_known_rate"]["denominator"] == 2
    assert rows["excluded"] == {"uni": ["access"]}
    assert "| excluded | page n/N |" in scorecard.render(card)
    # The page was found, yet the case is out of the denominator.
    assert " | access | 1/1 |" in scorecard.render(card)


def test_a_half_failed_case_leaves_it_in_that_repetition_only(tmp_path: Path) -> None:
    run = _run(
        tmp_path,
        [capture([DEADLINE]), capture([DEADLINE])],
        raws=[_raw("REACHED", 20, 10), _raw("REACHED", 20, 9)],
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert _readable(card, 0)["programme_found_on_readable"]["denominator"] == 0
    assert _readable(card, 1)["programme_found_on_readable"]["denominator"] == 1
    rows = {r["metric"]: r for r in card["targets"]}
    # The empty repetition has no value; the worst of the rest is judged.
    assert rows["programme_found_on_readable"]["worst"] == 1.0
    assert rows["programme_found_on_readable"]["met"] is True


def test_cache_hits_are_not_requests_in_the_half_failed_rule(tmp_path: Path) -> None:
    """unibo base2 off#2: 8 failed of 17 checked, 3 cached, is 8 of 14 on the wire."""
    raw = _raw("REACHED", 17, 8)
    raw["canary"]["institutions"][0]["outcomes"] = {"ok": 6, "cached": 3, "timeout": 7}
    run = _run(tmp_path, [capture([DEADLINE])], raws=[raw])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert _readable(card)["excluded"] == {"uni": ["access"]}
    # The per-case access cell keeps the raw report's counts.
    assert "| uni | REACHED (8/17 failed) |" in scorecard.render(card)


def test_probe_404s_and_our_own_refusals_are_not_the_site_failing(tmp_path: Path) -> None:
    """um base2 off#2: 8 of 18 failed, but 5 are absent sitemaps/robots, 1 our privacy rule."""
    raw = _raw("REACHED", 18, 8)
    inst = raw["canary"]["institutions"][0]
    inst["outcomes"] = {"ok": 6, "cached": 4, "http_error": 5, "blocked": 2, "refused_privacy": 1}
    inst["failures"] = [
        ["https://uni.edu/robots.txt", "http_error: HTTP 404"],
        ["https://uni.edu/sitemap.xml", "http_error: HTTP 404"],
        ["https://uni.edu/sitemap_index.xml", "http_error: HTTP 404"],
        ["https://uni.edu/sitemap-index.xml", "http_error: HTTP 404"],
        ["https://uni.edu/sitemap/sitemap.xml", "http_error: HTTP 404"],
        ["https://dept.uni.edu/", "blocked: private network"],
        ["https://dept.uni.edu/cs", "blocked: private network"],
        ["https://uni.edu/fees.pdf?_t=1761184801", "refused_privacy: long digit sequence"],
    ]
    run = _run(tmp_path, [capture([DEADLINE])], raws=[raw])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert _readable(card)["excluded"] == {}
    # A 403 on every page is the site refusing, whatever the path.
    inst["failures"] = [["https://uni.edu/cs", "http_error: HTTP 403"]] * 8
    run = _run(tmp_path / "403", [capture([DEADLINE])], raws=[raw])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert _readable(card)["excluded"] == {"uni": ["access"]}


LOG = "\n".join(
    [
        "get #1 start t=0s https://fees.uni.edu/robots.txt",
        "get #1 took 0.2s ok",
        "get #2 start t=1s https://fees.uni.edu/fees",
        "get #2 took 0.2s http_error",
        "get #3 start t=2s https://fees.uni.edu/fees",
        "get #3 took 0.0s cached",
        "get #4 start t=3s https://www.uni.edu/apply",
        "get #4 took 0.2s http_error",
        "get #5 start t=4s https://uni.edu/cs",
        "get #5 took 0.2s ok",
    ]
)


def test_failed_hosts_are_those_whose_every_request_failed() -> None:
    """robots.txt and cache hits are not the host answering; one ok page is."""
    assert scorecard.failed_hosts(LOG) == {"fees.uni.edu"}


def test_a_label_on_a_failed_host_leaves_the_denominator(tmp_path: Path) -> None:
    run = _run(tmp_path, [capture([DEADLINE])], raws=[_raw("REACHED", 5, 2)], logs=[LOG])
    corpus = _dataset(tuition="https://fees.uni.edu/fees")
    rows = _readable(scorecard.build(corpus, scorecard.load_run(run)))
    assert rows["core_known_readable_rate"] == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert rows["excluded"] == {"uni": ["host_failed:cost"]}


def test_a_pdf_label_leaves_while_its_html_sibling_stays(tmp_path: Path) -> None:
    run = _run(tmp_path, [capture([DEADLINE, TUITION_RIGHT])], raws=[_raw("REACHED", 20, 0)])
    corpus = _dataset(tuition="https://uni.edu/fees/tuition-2027.PDF")
    rows = _readable(scorecard.build(corpus, scorecard.load_run(run)))
    assert rows["core_known_readable_rate"] == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert rows["core_known_rate"]["denominator"] == 2
    assert rows["excluded"] == {"uni": ["pdf:cost"]}


def test_a_label_with_one_html_page_among_pdfs_stays() -> None:
    label = (
        dataset()
        .cases[0]
        .labels[1]
        .model_copy(
            update={
                "evidence": [
                    dataset()
                    .cases[0]
                    .labels[1]
                    .evidence[0]
                    .model_copy(update={"url": "https://uni.edu/fees.pdf"}),
                    dataset().cases[0].labels[1].evidence[0],
                ]
            }
        )
    )
    assert scorecard.label_exclusion(label, set()) is None
    assert scorecard.label_exclusion(label, {"uni.edu"}) == "host_failed"


def test_a_non_english_page_stays(tmp_path: Path) -> None:
    run = _run(tmp_path, [capture([])], raws=[_raw("REACHED", 20, 0)])
    corpus = _dataset(deadline="https://uni.edu/de/bewerbung/fristen")
    rows = _readable(scorecard.build(corpus, scorecard.load_run(run)))
    assert rows["core_known_readable_rate"]["denominator"] == 2
    assert rows["excluded"] == {}


def test_a_case_with_no_programme_page_found_stays(tmp_path: Path) -> None:
    rep = capture([DEADLINE])
    rep["observations"][0]["programme_urls"] = []
    run = _run(tmp_path, [rep], raws=[_raw("REACHED", 20, 0)])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    rows = _readable(card)
    assert rows["programme_found_on_readable"] == {"numerator": 0, "denominator": 1, "value": 0.0}
    assert rows["core_known_readable_rate"]["denominator"] == 2


def test_a_wrong_programme_page_is_counted(tmp_path: Path) -> None:
    rep = capture([])
    rep["observations"][0]["programme_urls"] = ["https://uni.edu/law"]
    run = _run(tmp_path, [rep])
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert _readable(card)["wrong_programme_pages"] == 1
    row = next(r for r in card["targets"] if r["metric"] == "wrong_programme_pages")
    assert (row["worst"], row["met"]) == (1, False)


def test_target_4_is_judged_on_the_readable_denominator_by_default(tmp_path: Path) -> None:
    """Owner decision 2026-10-18 (01-Q2): the readable column is target 4's row."""
    run = _run(
        tmp_path,
        [capture([DEADLINE, TUITION_RIGHT])],
        raws=[_raw("REACHED", 20, 0)],
    )
    corpus = _dataset(tuition="https://uni.edu/fees.pdf")
    card = scorecard.build(corpus, scorecard.load_run(run))
    core = [r for r in card["targets"] if r["metric"].startswith("core_known")]
    assert [(r["metric"], r["worst"], r["met"]) for r in core] == [
        ("core_known_readable_rate", 1.0, True)
    ]
    assert "| on | core_known_readable_rate | 1.000 | >= 0.8 | yes |" in scorecard.render(card)
    old = scorecard.build(corpus, scorecard.load_run(run), core_denominator="all")
    core = [r for r in old["targets"] if r["metric"].startswith("core_known")]
    assert [(r["metric"], r["met"]) for r in core] == [("core_known_rate", True)]


def test_the_cli_takes_the_core_denominator(tmp_path: Path) -> None:
    run = _run(tmp_path / "run", [capture([DEADLINE])])
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    out = tmp_path / "card.json"
    args = [str(run), "--dataset", str(corpus), "--out", str(out), "--core-denominator", "all"]
    assert scorecard.main(args) == 0
    metrics = [r["metric"] for r in json.loads(out.read_text())["targets"]]
    assert "core_known_rate" in metrics
    assert "core_known_readable_rate" not in metrics


def test_the_rows_before_ticket_03_are_byte_identical(tmp_path: Path) -> None:
    """Without the readable rows the scorecard renders exactly as before; with
    them, every old line is still there (a per-case row only gains cells)."""
    run = _run(
        tmp_path,
        [capture([DEADLINE]), capture([DEADLINE, TUITION_RIGHT])],
        raws=[_raw("REACHED", 20, 0), _raw("BLOCKED", 5, 5)],
        logs=[LOG, None],
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    old = copy.deepcopy(card)
    for rep in old["arms"]["on"]["repetitions"]:
        del rep["readable"]
    old["targets"] = scorecard.check_targets(old)
    before, after = scorecard.render(old).splitlines(), scorecard.render(card).splitlines()
    assert [r["metric"] for r in old["targets"]] == [
        "claim_precision",
        "wrong_scope_claim_rate",
        "cases_over_budget",
    ]
    assert card["targets"][:3] == old["targets"]
    for line in before:
        assert line in after or any(new.startswith(line) for new in after), line
