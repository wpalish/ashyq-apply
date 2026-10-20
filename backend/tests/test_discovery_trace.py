"""TR-1: the no-search trace explains itself (NEXT_CYCLES_2026-10-22, ticket TR-1).

Measurement only. The discovery trace records the confirm queue (every queued
programme candidate with its score, source, whether it was read and the
verdict or why not), what the sitemap stage's ``keep`` did with each URL, the
pages the navigation fallback queued, per-read seconds and bytes
(``host_cost.samples``) and why a stage stopped early. Each row is serialised
only when non-empty and bounded. The scorecard reads the gold page's place in
the confirm queue (``gold_confirm_rank``, evaluation only).

Every site here is written for the test (``example-uni.edu`` / ``uni.dk``); no
page, label or word comes from a development or heldout case. Offline: HTTP runs
on ``httpx.MockTransport`` with the real ``Fetcher``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    CONFIRM_QUEUE_TRACE_CAP,
    MAX_PROGRAM_CANDIDATES_CHECKED,
    NAVIGATION_QUEUE_TRACE_CAP,
    READ_SAMPLES_TRACE_CAP,
    DiscoveryTrace,
    StageBudget,
)
from evaluation.research import scorecard, stage_summary
from evaluation.research.schema import Capture
from tests.test_benchmark_provider_results import LOCAL, TWIN, _capture, _dataset
from tests.test_homepage_hop_reads import (
    HOME,
    WWW,
    _allow_all,
    _discover,
    _html,
    _robots,
    _sibling_site,
    _site,
)
from tests.test_live_discovery import program_html, sitemap_xml

TR1_KEYS = ("confirm_queue", "sitemap_keep", "navigation_queue")


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _allow_all)


def _url(path: str) -> str:
    return f"https://{WWW}{path}"


CS = _url("/bachelor/computer-science")
MUSIC = _url("/bachelor/music")
HISTORY = _url("/bachelor/history-of-art")
MASTER = _url("/master/computer-science")
NEWS = _url("/news/open-day")


def _sitemap_site(*extra_programmes: str) -> dict[str, tuple[int, str]]:
    sitemap = _url("/sitemap.xml")
    pages = _site(
        _html("Example University", ("/about", "About")),
        **{
            f"https://{WWW}/robots.txt": _robots(f"User-agent: *\nSitemap: {sitemap}\n"),
            sitemap: (
                200,
                sitemap_xml(MUSIC, CS, HISTORY, MASTER, NEWS, *extra_programmes),
            ),
            CS: (200, program_html("BSc Computer Science")),
            MUSIC: (200, program_html("BMus Music")),
            HISTORY: (200, program_html("BA History of Art")),
        },
    )
    return pages


# --- 1. the rows appear on a synthetic run ---------------------------------------


@pytest.mark.asyncio
async def test_a_sitemap_run_records_the_confirm_queue_and_the_keep_counts(
    tmp_path: Path, profile: Any
) -> None:
    candidate, trace, _wire = await _discover(tmp_path, _sitemap_site(), profile)
    assert [p.url for p in candidate.programs] == [CS]
    data = json.loads(json.dumps(trace.as_dict()))

    queue = data["confirm_queue"]
    assert queue[0]["url"] == CS, "the field match ranks first"
    assert {row["url"] for row in queue} == {CS, MUSIC, HISTORY}
    by_url = {row["url"]: row for row in queue}
    assert by_url[CS] == {
        "url": CS,
        "score": by_url[CS]["score"],
        "source": "sitemap",
        "read": True,
        "verdict": "",
    }
    assert by_url[CS]["score"] > by_url[MUSIC]["score"] > 0
    for other in (MUSIC, HISTORY):
        assert by_url[other]["read"] is True
        assert by_url[other]["verdict"], "a refusal names its reason"
    assert all(set(row) == {"url", "score", "source", "read", "verdict"} for row in queue)

    counts = data["sitemap_keep"]["counts"]
    assert counts["seen"] == 5
    assert counts["kept"] == 3
    assert counts["other_level"] == 1
    assert counts["excluded"] == 1
    kept = data["sitemap_keep"]["kept"]["program_page"]
    assert kept[0][1] == CS
    assert {pair[1] for pair in kept} == {CS, MUSIC, HISTORY}

    samples = data["host_cost"]["samples"]
    assert samples, "every read through the stage budget is timed"
    assert all(set(row) == {"url", "stage", "seconds", "bytes"} for row in samples)
    read = next(row for row in samples if row["url"] == CS)
    assert read["stage"] == "confirm"
    assert read["bytes"] == len(program_html("BSc Computer Science"))
    assert "navigation_queue" not in data, "navigation never ran"


@pytest.mark.asyncio
async def test_candidates_past_the_read_cap_say_so(tmp_path: Path, profile: Any) -> None:
    extra = [_url(f"/bachelor/subject-{n:02d}") for n in range(12)]
    _candidate, trace, _wire = await _discover(tmp_path, _sitemap_site(*extra), profile)
    queue = trace.as_dict()["confirm_queue"]
    assert len(queue) == 15
    beyond = queue[MAX_PROGRAM_CANDIDATES_CHECKED:]
    assert all(row["read"] is False for row in beyond)
    assert {row["verdict"] for row in beyond} == {"not read: beyond the confirm read cap"}
    # The first one was accepted; the rest inside the cap were read or say why not.
    for row in queue[:MAX_PROGRAM_CANDIDATES_CHECKED]:
        assert row["read"] or str(row["verdict"]).startswith(("not read", "could not be read"))


@pytest.mark.asyncio
async def test_a_navigation_run_records_the_navigation_queue(tmp_path: Path, profile: Any) -> None:
    _candidate, trace, _wire = await _discover(tmp_path, _sibling_site(), profile)
    data = trace.as_dict()
    reasons = [(row["url"], row["reason"]) for row in data["navigation_queue"]]
    assert reasons[0] == (HOME, "homepage")
    assert any(reason == "homepage_hop" for _url, reason in reasons)
    hop = next(row for row in data["navigation_queue"] if row["reason"] == "homepage_hop")
    assert isinstance(hop["score"], int) and hop["score"] > 0
    assert [row["source"] for row in data["confirm_queue"]] == ["navigation"]


@pytest.mark.asyncio
async def test_the_trace_rows_change_no_result(
    tmp_path: Path, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the recorders silenced, discovery returns the same pages from the same reads."""
    with_rows = await _discover(tmp_path / "a", _sitemap_site(), profile)
    for name in ("note_keep", "note_kept_lists", "note_navigation_queued", "note_read_sample"):
        monkeypatch.setattr(DiscoveryTrace, name, lambda *_a, **_k: None)
    without = await _discover(tmp_path / "b", _sitemap_site(), profile)
    assert [p.url for p in with_rows[0].programs] == [p.url for p in without[0].programs]
    assert with_rows[2] == without[2], "the same reads, in the same order"
    assert without[1].sitemap_keep == {}


# --- 2. absent on an empty run, bounded on a large one ---------------------------


def test_an_empty_trace_serialises_none_of_the_rows() -> None:
    data = DiscoveryTrace(institution="U", domain="u.example").as_dict()
    for key in TR1_KEYS:
        assert key not in data
    assert "host_cost" not in data


def test_host_cost_keeps_its_own_keys_beside_the_samples() -> None:
    trace = DiscoveryTrace(institution="U", domain="u.example")
    trace.host_cost = {"crawl_delay": None, "median_read_seconds": 0.1, "slow": False}
    assert trace.as_dict()["host_cost"] == trace.host_cost
    trace.note_read_sample("https://u.example/a", "sitemap", 0.12345, 10)
    assert trace.as_dict()["host_cost"] == {
        **trace.host_cost,
        "samples": [
            {"url": "https://u.example/a", "stage": "sitemap", "seconds": 0.123, "bytes": 10}
        ],
    }


def test_the_rows_are_bounded() -> None:
    trace = DiscoveryTrace(institution="U", domain="u.example")
    for n in range(500):
        trace.note_navigation_queued(f"https://u.example/{n}", n, "catalogue_link")
        trace.note_read_sample(f"https://u.example/{n}", "walker", 0.1, n)
    trace.note_navigation_queued("https://u.example/0", 0, "catalogue_link")
    assert len(trace.navigation_queue) == NAVIGATION_QUEUE_TRACE_CAP
    assert len(trace.read_samples) == READ_SAMPLES_TRACE_CAP
    ranked = {"program_page": [(n, f"https://u.example/p{n}") for n in range(500)]}
    trace.note_kept_lists(ranked)
    kept = trace.sitemap_keep["kept"]
    assert isinstance(kept, dict)
    assert len(kept["program_page"]) == live_discovery.MAX_CANDIDATES_PER_CATEGORY
    queued = [f"https://u.example/q{n}" for n in range(500)]
    live_discovery._confirm_queue_rows(queued, {"program_page": []}, trace)
    assert len(trace.confirm_queue) == CONFIRM_QUEUE_TRACE_CAP


def test_a_stage_stop_is_recorded_once_per_stage() -> None:
    budget = StageBudget(deadline_seconds=100.0, read_cap=0)
    assert budget.as_dict().get("stage_stopped_by") is None
    budget.note_stop("sitemap", "stage_cap")
    budget.note_stop("sitemap", "budget")
    budget.enter("confirm")
    assert budget.exhausted()
    assert budget.as_dict()["stage_stopped_by"] == {"sitemap": "stage_cap", "confirm": "read_cap"}


# --- 3. the scorecard column ------------------------------------------------------


def _rank(trace: dict[str, Any] | None, gold: str = LOCAL) -> int | str | None:
    return scorecard.gold_confirm_rank(_dataset(gold).cases[0], trace)


def _row(url: str, read: bool = False) -> dict[str, Any]:
    return {"url": url, "score": 3, "source": "sitemap", "read": read, "verdict": ""}


def test_gold_confirm_rank_names_the_gold_position_or_why_it_has_none() -> None:
    other = "https://studier.uni.dk/bachelor/fysik"
    assert _rank(None) is None
    assert _rank({"pages_read": [[LOCAL, ""]]}) is None, "a trace from before TR-1"
    assert _rank({"confirm_queue": [_row(other), _row(LOCAL)]}) == 2
    twinned = {
        "programme_url_aliases": {LOCAL: [TWIN], TWIN: [LOCAL]},
        "confirm_queue": [_row(TWIN)],
    }
    assert _rank(twinned) == 1, "a declared twin of the gold is the gold"
    kept = {"sitemap_keep": {"kept": {"program_page": [[19, LOCAL]]}}}
    assert _rank({**kept, "confirm_queue": [_row(other)]}) == "not_queued"
    assert _rank({"navigation_queue": [{"url": LOCAL, "score": 1, "reason": "x"}]}) == (
        "not_queued"
    )
    assert _rank({"confirm_queue": [_row(other)]}) == "not_seen"


def test_the_scorecard_and_the_stage_summary_carry_the_rank(tmp_path: Path) -> None:
    target = tmp_path / "uni-on" / "20261018T000001Z"
    target.mkdir(parents=True)
    (target / "capture.json").write_text(json.dumps(_capture(urls=[])))
    trace = {"confirm_queue": [_row("https://studier.uni.dk/x", True), _row(LOCAL)]}
    raw = {"canary": {"institutions": [{"discovery_trace": trace}]}}
    (target / "uni.raw.json").write_text(json.dumps(raw))

    arms = scorecard.load_run(tmp_path)
    card = scorecard.build(_dataset(), arms)
    assert card["arms"]["on"]["repetitions"][0]["gold_confirm_rank"] == {"uni": 2}
    text = scorecard.render(card)
    assert " gold confirm rank |" in text
    assert "| 2 |" in text

    capture = Capture.model_validate(_capture(urls=[]))
    rows = stage_summary.repetition_summary(_dataset(), capture, {"uni": trace})
    assert rows["discovery funnel"]["confirm_queue_len"] == 2
    assert rows["gold programme page"]["gold_queued"] == 1
    assert rows["gold programme page"]["gold_queued_not_read"] == 1
    rendered = stage_summary.render(stage_summary.summarize_run(_dataset(), arms))
    assert stage_summary.leak_check(rendered, _dataset()) == []


def test_a_run_without_tr1_traces_keeps_its_table_shape(tmp_path: Path) -> None:
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(_capture()))
    card = scorecard.build(_dataset(), scorecard.load_run(path))
    assert "gold confirm rank" not in scorecard.render(card)
