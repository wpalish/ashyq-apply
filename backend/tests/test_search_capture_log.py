"""Titles and snippets for the replay: the capture's search log and recorded-search store v2.

MISS_STAGES 2026-10-19 §0.1: the base3 store holds URLs only, so replay ranks
on URL words and warsaw's gold (rank 2, "Informatyka" in its live title) falls
outside the read cap. A live capture now logs every request it sends (full
text, parameters, each result's URL, title, snippet and rank); the store
builder carries the titles and snippets into a v2 store; the recorded
provider hands them back. All offline: no provider is ever called.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.search import recorded
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.recorded import (
    COUNTERS,
    RecordedSearchProvider,
    RecordedSearchStore,
    RecordedStoreError,
)
from app.adapters.search.serper import SerperSearchProvider
from app.config import get_settings
from evaluation.research import live, recorded_search
from scripts import canary_discovery as canary

NOW = datetime(2026, 10, 19, tzinfo=UTC)
URLS = [f"https://www.uni.edu/p{n}" for n in range(1, 4)]
QUERY = 'site:uni.edu "computer science" "bachelor"'


@pytest.fixture(autouse=True)
def _fresh_counters():
    COUNTERS.reset()
    yield
    COUNTERS.reset()


def _v2(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "recorded-search/2", "provenance": {}, "entries": list(entries)}


def _entry(urls: list[str], **extra: Any) -> dict[str, Any]:
    return {"query": QUERY, "domains": ["uni.edu"], "hl": None, "gl": None, "urls": urls, **extra}


def _results(urls: list[str]) -> list[dict[str, str]]:
    return [{"url": u, "title": f"Title {u[-2:]}", "snippet": f"About {u[-2:]}"} for u in urls]


# --- the store and the provider --------------------------------------------------


async def test_a_v2_store_replays_each_results_title_and_snippet() -> None:
    store = RecordedSearchStore.from_document(_v2(_entry(URLS, results=_results(URLS))))
    response = await RecordedSearchProvider(store, now=NOW).search(
        query=QUERY, domains=["uni.edu"], max_results=2
    )
    assert [(r.url, r.title, r.snippet, r.rank) for r in response.results] == [
        (URLS[0], "Title p1", "About p1", 1),
        (URLS[1], "Title p2", "About p2", 2),
    ]
    assert {r.provider for r in response.results} == {"recorded"}


async def test_a_v2_entry_without_results_and_a_v1_store_replay_urls_only() -> None:
    for document in (
        _v2(_entry(URLS)),
        {"schema": "recorded-search/1", "provenance": {}, "entries": [_entry(URLS)]},
    ):
        store = RecordedSearchStore.from_document(document)
        response = await RecordedSearchProvider(store).search(query=QUERY, domains=["uni.edu"])
        assert [r.url for r in response.results] == URLS
        assert all(r.title == "" and r.snippet == "" for r in response.results)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (_v2(_entry(URLS, results=_results(URLS[:2]))), "every URL once"),
        (_v2(_entry(URLS, results=_results(URLS[::-1]))), "follow 'urls' in order"),
        (
            _v2(_entry(URLS[:1], results=[{"url": URLS[0], "title": 3, "snippet": ""}])),
            "title and snippet are strings",
        ),
        (
            {"schema": "recorded-search/1", "entries": [_entry(URLS, results=_results(URLS))]},
            "needs 'recorded-search/2'",
        ),
        (
            _v2(_entry(URLS, results=_results(URLS)), _entry(URLS)),
            "different result list",
        ),
        ({"schema": "recorded-search/3", "entries": []}, "recorded-search/2"),
    ],
)
def test_a_malformed_v2_store_is_refused(document: dict[str, Any], message: str) -> None:
    with pytest.raises(RecordedStoreError, match=message):
        RecordedSearchStore.from_document(document)


def test_the_committed_v1_store_still_loads_with_no_titles() -> None:
    store = RecordedSearchStore.from_file(live.DEFAULT_RECORDED_STORE)
    assert len(store) > 100
    assert store.texts == {}


# --- the capture's search log ----------------------------------------------------


def _response(query: str, urls: list[str]) -> SearchResponse:
    return SearchResponse(
        query=query,
        provider="serper",
        retrieved_at=NOW,
        results=tuple(
            SearchResult(
                url=u,
                title=f"Title {u[-2:]}" + "x" * 400,
                snippet=f"About {u[-2:]}",
                provider="serper",
                rank=n,
                retrieved_at=NOW,
            )
            for n, u in enumerate(urls, start=1)
        ),
    )


def test_the_search_log_keeps_the_request_and_every_result(tmp_path: Path) -> None:
    log = live.SearchLog(tmp_path / "uio.search.json", "uio")
    log.record(
        "serper",
        "search_localized",
        {"query": "informatikk bachelor", "hl": "no", "gl": "no", "domains": ["uio.no"]},
        _response("informatikk bachelor", URLS),
        "discovery",
    )
    document = json.loads((tmp_path / "uio.search.json").read_text(encoding="utf-8"))
    assert document["schema"] == live.SEARCH_LOG_SCHEMA and document["case"] == "uio"
    (row,) = document["requests"]
    assert {k: v for k, v in row.items() if k != "results"} == {
        "provider": "serper",
        "method": "search_localized",
        "kind": "discovery",
        "query": "informatikk bachelor",
        "domains": ["uio.no"],
        "hl": "no",
        "gl": "no",
        "max_results": 10,
    }
    assert [(r["rank"], r["url"], r["snippet"]) for r in row["results"]] == [
        (1, URLS[0], "About p1"),
        (2, URLS[1], "About p2"),
        (3, URLS[2], "About p3"),
    ]
    assert all(len(r["title"]) == live.SEARCH_LOG_TITLE_CHARS for r in row["results"])
    assert not list(tmp_path.glob("*.pending*"))


def test_the_search_log_is_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "SEARCH_LOG_CAP", 2)
    log = live.SearchLog(tmp_path / "c.search.json", "c")
    for n in range(4):
        log.record("serper", "search", {"query": f"q{n}"}, _response("q", []), None)
    assert [r["query"] for r in log.requests] == ["q0", "q1"]


@pytest.fixture
def _serper(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()

    async def answered(self: Any, *, query: str, **kwargs: Any) -> SearchResponse:
        return _response(query, URLS)

    async def answered_localized(self: Any, *, query: str, **kwargs: Any) -> SearchResponse:
        return _response(query, URLS[:1])

    # Stand-ins for the vendor call: nothing here can reach a network.
    monkeypatch.setattr(SerperSearchProvider, "search", answered)
    monkeypatch.setattr(SerperSearchProvider, "search_localized", answered_localized)
    monkeypatch.setattr(live, "_jev_shadow", lambda *a, **k: _none())
    yield
    get_settings.cache_clear()


async def _none() -> None:
    return None


def _report() -> dict[str, Any]:
    return {"institutions": [{"programs": []}], "run_error": ""}


async def test_a_live_capture_logs_every_request_beside_its_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _serper: Any
) -> None:
    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        provider = object.__new__(SerperSearchProvider)
        await provider.search(query=QUERY, domains=["uni.edu"], max_results=10)
        await provider.search_localized(query="informatyka studia", hl="pl", gl="pl")
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120)
    document = json.loads(output.with_suffix(".search.json").read_text(encoding="utf-8"))
    rows = document["requests"]
    assert [(r["provider"], r["method"], r["query"]) for r in rows] == [
        ("serper", "search", QUERY),
        ("serper", "search_localized", "informatyka studia"),
    ]
    assert rows[0]["domains"] == ["uni.edu"] and rows[1]["hl"] == "pl"
    assert [r["url"] for r in rows[0]["results"]] == URLS


async def test_a_capture_that_sent_no_query_writes_no_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _serper: Any
) -> None:
    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120)
    assert not output.with_suffix(".search.json").exists()


async def test_a_replayed_request_is_never_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _serper: Any
) -> None:
    store = RecordedSearchStore.from_document(_v2(_entry(URLS, results=_results(URLS))))

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        await RecordedSearchProvider(store).search(query=QUERY, domains=["uni.edu"])
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120)
    assert not output.with_suffix(".search.json").exists()
    assert COUNTERS.hits == 1


# --- the builder -------------------------------------------------------------------


def _write_rep(root: Path, stamp: str, urls: list[str], log: list[dict[str, Any]] | None) -> None:
    target = root / "uio-off" / stamp
    target.mkdir(parents=True)
    trace = {
        "institution": "University of Oslo",
        "domain": "www.uio.no",
        "search_results": [{"family": "field_and_degree", "urls": urls}],
    }
    raw = {"canary": {"institutions": [{"country": "Norway", "discovery_trace": trace}]}}
    (target / "uio.raw.json").write_text(json.dumps(raw))
    if log is not None:
        document = {"schema": live.SEARCH_LOG_SCHEMA, "case": "uio", "requests": log}
        (target / "uio.search.json").write_text(json.dumps(document))


def _logged(query: str, urls: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "provider": "serper",
        "method": "search",
        "kind": "discovery",
        "query": query,
        "domains": ["uio.no"],
        "hl": None,
        "gl": None,
        "max_results": 10,
        "results": [
            {"rank": n, "url": u, "title": f"T{n}", "snippet": f"S{n}"}
            for n, u in enumerate(urls, start=1)
        ],
        **extra,
    }


def test_the_builder_writes_v2_with_titles_from_the_search_log(tmp_path: Path) -> None:
    run = tmp_path / "run"
    urls = [f"https://www.uio.no/a{n}" for n in range(3)]
    planned = recorded_search.discovery_requests("University of Oslo", "www.uio.no", "Norway")
    request = planned["field_and_degree"]
    log = [_logged(request.query, urls)]
    # A topic search the trace never records becomes an entry of its own.
    log.append(_logged("uio.no application deadline", urls[:1], kind="topic"))
    _write_rep(run, "20261020T000001Z", urls, None)
    _write_rep(run, "20261020T000002Z", urls, log)
    document = recorded_search.build_store([("dev3", "9", "2026-10-20T00:00:00Z", "abc", run)])
    assert document["schema"] == "recorded-search/2"
    by_family = {e["family"]: e for e in document["entries"]}
    traced = by_family["field_and_degree"]
    assert traced["agreement"] == "2/2"
    assert traced["source_repetition"] == "uio-off/20261020T000002Z"
    assert traced["results"] == [
        {"url": u, "title": f"T{n}", "snippet": f"S{n}"} for n, u in enumerate(urls, start=1)
    ]
    assert traced["kind"] == "discovery" and traced["provider"] == "serper"
    topic = by_family[""]
    assert topic["query"] == "uio.no application deadline" and topic["kind"] == "topic"
    assert document["provenance"]["sources"][0]["repetitions_with_search_log"] == 1
    store = RecordedSearchStore.from_document(document)
    key = recorded.request_key(request.query, request.domains, request.hl, request.gl)
    assert store.texts[key][0] == ("T1", "S1")


def test_a_build_with_no_search_log_is_still_v1(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_rep(run, "20261020T000001Z", ["https://www.uio.no/a"], None)
    document = recorded_search.build_store([("dev3", "9", "2026-10-20T00:00:00Z", "abc", run)])
    assert document["schema"] == "recorded-search/1"
    (entry,) = document["entries"]
    assert "results" not in entry and "kind" not in entry
    assert "repetitions_with_search_log" not in document["provenance"]["sources"][0]


def test_a_search_log_of_another_format_stops_the_build(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_rep(run, "20261020T000001Z", ["https://www.uio.no/a"], [])
    path = run / "uio-off" / "20261020T000001Z" / "uio.search.json"
    path.write_text(json.dumps({"schema": "other", "requests": []}))
    with pytest.raises(ValueError, match="search-log/1"):
        recorded_search.collect("dev3", "9", "d", "s", run)
