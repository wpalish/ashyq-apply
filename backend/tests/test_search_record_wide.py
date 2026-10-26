"""SR-WIDE — record wide, rank narrow.

A record run asks each keyed provider for the whole page one paid request
buys (Exa 25 results, Tavily 20 at ``basic``), records every result, and
still hands the pipeline exactly the head it asked for, so discovery ranks
what it ranked before. A request already answered in a case is never sent
again. Offline only: every provider answers through a mock transport or a
patched method, and no request leaves the process.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters.search import get_search_provider, recorded
from app.adapters.search.base import ProviderPage, SearchResponse, SearchResult
from app.adapters.search.exa import ExaSearchProvider
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.recorded import (
    COUNTERS,
    RecordedSearchProvider,
    RecordedSearchStore,
    RecordedStoreError,
)
from app.adapters.search.retrieval import discover_candidates
from app.adapters.search.tavily import TavilySearchProvider
from app.config import Settings, get_settings
from app.domain.enums import DegreeLevel
from evaluation.research import live, recorded_search
from evaluation.research.schema import Capture, Observation
from evaluation.research.search_cap import SearchQueryLedger
from scripts import canary_discovery as canary

NOW = datetime(2026, 10, 26, tzinfo=UTC)
KEY = "synthetic-key-never-printed"
DOMAIN = "uni.edu"


@pytest.fixture(autouse=True)
def _fresh() -> Any:
    COUNTERS.reset()
    get_settings.cache_clear()
    yield
    COUNTERS.reset()
    get_settings.cache_clear()


# --- a provider page of 25 ----------------------------------------------------------


def _exa_rows(count: int = 25) -> list[dict[str, Any]]:
    """25 Exa rows. Ranks 11-25 are the *most* relevant words on purpose: if
    any of them leaked into ranking, discovery's answer would change."""
    rows = []
    for n in range(1, count + 1):
        if n <= 10:
            title, words = f"Page {n}", [f"Faculty news item {n}", "campus life"]
        else:
            title = f"Bachelor of Computer Science programme {n}"
            words = ["Bachelor computer science admission requirements", "x" * 900]
        rows.append({"url": f"https://www.{DOMAIN}/p{n}", "title": title, "highlights": words})
    return rows


def _exa_handler(rows: list[dict[str, Any]], cost: float | None = 0.022):
    """Answers like Exa: at most ``numResults`` rows, with its cost block."""
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        sent.append(payload)
        body: dict[str, Any] = {"results": rows[: payload["numResults"]]}
        if cost is not None:
            body["costDollars"] = {"total": cost}
        return httpx.Response(200, json=body)

    handler.sent = sent  # type: ignore[attr-defined]
    return handler


def _exa(handler: Any, *, record_wide: bool) -> ExaSearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExaSearchProvider(KEY, client=client, record_wide=record_wide)


async def test_exa_records_wide_and_hands_the_caller_its_own_head() -> None:
    handler = _exa_handler(_exa_rows())
    response = await _exa(handler, record_wide=True).search(
        query="cs", domains=[DOMAIN], max_results=10
    )
    (payload,) = handler.sent
    assert payload["numResults"] == 25
    assert payload["contents"] == {"highlights": {"maxCharacters": 1000}}
    assert len(response.results) == 10 and response.page is not None
    page = response.page
    assert len(page.results) == 25 and page.results[:10] == response.results
    assert [r.rank for r in page.results] == list(range(1, 26))
    assert (page.requested, page.cost, page.cost_unit) == (25, 0.022, "usd")
    assert dict(page.parameters) == {
        "type": "auto",
        "numResults": 25,
        "highlights.maxCharacters": 1000,
    }
    # A highlight is still a hint with one home, cut at the adapter's own bound.
    assert all(len(r.snippet) <= 1000 for r in page.results)


async def test_exa_narrow_is_todays_request_exactly() -> None:
    handler = _exa_handler(_exa_rows())
    response = await _exa(handler, record_wide=False).search(query="cs", max_results=10)
    assert handler.sent == [
        {"query": "cs", "type": "auto", "numResults": 10, "contents": {"highlights": True}}
    ]
    assert response.page is None and len(response.results) == 10


@pytest.mark.parametrize("max_results", [1, 3, 5, 10, 25])
async def test_every_caller_gets_the_same_results_wide_or_narrow(max_results: int) -> None:
    rows = _exa_rows()
    wide = await _exa(_exa_handler(rows), record_wide=True).search(
        query="cs", max_results=max_results
    )
    narrow = await _exa(_exa_handler(rows), record_wide=False).search(
        query="cs", max_results=max_results
    )
    strip = [(r.url, r.title, r.snippet, r.rank) for r in narrow.results]
    assert [(r.url, r.title, r.snippet, r.rank) for r in wide.results] == strip


async def test_exa_without_a_cost_block_records_no_cost() -> None:
    response = await _exa(_exa_handler(_exa_rows(3), cost=None), record_wide=True).search(
        query="cs"
    )
    assert response.page is not None and response.page.cost is None
    assert len(response.page.results) == 3 == len(response.results)


async def test_discovery_ranks_the_same_ten_when_the_provider_returns_25() -> None:
    """Rank narrow: a wide page leaves discovery's whole report unchanged."""
    intent = DiscoveryIntent(
        institution="Uni", domain=DOMAIN, degree=DegreeLevel.BACHELOR, field="computer science"
    )
    rows = _exa_rows()
    wide_handler, narrow_handler = _exa_handler(rows), _exa_handler(rows)
    wide = await discover_candidates(
        _exa(wide_handler, record_wide=True), intent, top_k=10, hop_entry_points=0
    )
    narrow = await discover_candidates(
        _exa(narrow_handler, record_wide=False), intent, top_k=10, hop_entry_points=0
    )
    assert {p["numResults"] for p in wide_handler.sent} == {25}
    assert {p["numResults"] for p in narrow_handler.sent} == {10}
    assert wide == narrow
    assert not {c.url for c in wide.candidates} & {r["url"] for r in rows[10:]}
    assert all(len(urls) <= 10 for _family, urls in wide.results_by_family)


class _WideFake:
    """A fake provider that returns 25 per request, narrowed to the caller's ask."""

    name = "fake"

    def __init__(self, count: int = 25) -> None:
        self.count = count

    async def search(self, *, query: str, domains: Any = (), max_results: int = 10):
        page = tuple(
            SearchResult(
                url=f"https://www.{DOMAIN}/r{n}",
                title=f"Result {n}",
                provider="fake",
                rank=n,
                retrieved_at=NOW,
            )
            for n in range(1, self.count + 1)
        )
        return SearchResponse(
            query=query,
            provider="fake",
            retrieved_at=NOW,
            results=page[:max_results],
            page=ProviderPage(results=page, requested=self.count),
        )


def test_a_response_must_be_the_head_of_its_page() -> None:
    page = tuple(
        SearchResult(url=f"https://a.b/{n}", title="", provider="p", rank=n, retrieved_at=NOW)
        for n in (1, 2, 3)
    )
    with pytest.raises(ValueError, match="head of its recorded page"):
        SearchResponse(
            query="q",
            provider="p",
            retrieved_at=NOW,
            results=page[1:2],
            page=ProviderPage(results=page, requested=3),
        )


# --- Tavily -----------------------------------------------------------------------


def _tavily_handler(count: int = 20):
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        sent.append(payload)
        rows = [
            {"url": f"https://www.{DOMAIN}/t{n}", "title": f"T{n}", "content": "c" * 1200}
            for n in range(1, count + 1)
        ][: payload["max_results"]]
        body: dict[str, Any] = {"results": rows}
        if payload.get("include_usage"):
            body["usage"] = {"credits": 1}
        return httpx.Response(200, json=body)

    handler.sent = sent  # type: ignore[attr-defined]
    return handler


def _tavily(handler: Any, **kw: Any) -> TavilySearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TavilySearchProvider(KEY, client=client, **kw)


async def test_tavily_records_20_at_basic_for_one_credit() -> None:
    handler = _tavily_handler()
    response = await _tavily(handler, record_wide=True).search(query="cs", max_results=5)
    (payload,) = handler.sent
    assert (payload["max_results"], payload["search_depth"], payload["include_usage"]) == (
        20,
        "basic",
        True,
    )
    assert len(response.results) == 5 and response.page is not None
    assert len(response.page.results) == 20 and response.page.results[:5] == response.results
    assert (response.page.cost, response.page.cost_unit) == (1.0, "credits")
    assert all(len(r.snippet) == 1000 for r in response.page.results)


async def test_tavily_narrow_is_todays_request_exactly() -> None:
    handler = _tavily_handler()
    response = await _tavily(handler).search(query="cs", max_results=5)
    assert handler.sent == [{"query": "cs", "search_depth": "basic", "max_results": 5}]
    assert response.page is None


def test_tavily_records_wide_at_basic_depth_only() -> None:
    with pytest.raises(ValueError, match="basic"):
        TavilySearchProvider(KEY, search_depth="advanced", record_wide=True)


# --- the setting ---------------------------------------------------------------------


def test_record_wide_is_off_unless_the_record_path_turns_it_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert Settings().search_record_wide is False
    monkeypatch.setenv("UNIMATCH_EXA_API_KEY", KEY)
    monkeypatch.setenv("UNIMATCH_TAVILY_API_KEY", KEY)
    for name in ("exa", "tavily"):
        monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", name)
        monkeypatch.delenv("UNIMATCH_SEARCH_RECORD_WIDE", raising=False)
        get_settings.cache_clear()
        assert get_search_provider().inner._record_wide is False  # type: ignore[attr-defined]
        monkeypatch.setenv("UNIMATCH_SEARCH_RECORD_WIDE", "true")
        get_settings.cache_clear()
        assert get_search_provider().inner._record_wide is True  # type: ignore[attr-defined]


def test_the_harness_sets_the_switch_only_when_asked() -> None:
    assert "UNIMATCH_SEARCH_RECORD_WIDE" not in live.search_environment("exa", None)
    assert live.search_environment("exa", None, record_wide=True)[
        "UNIMATCH_SEARCH_RECORD_WIDE"
    ] == ("true")
    assert "UNIMATCH_SEARCH_RECORD_WIDE" in live.search_environment(
        "tavily", None, record_wide=True
    )
    with pytest.raises(ValueError, match="record-wide"):
        live.search_environment("serper", None, record_wide=True)


@pytest.mark.parametrize("provider", ["none", "exa_mcp", "serper"])
def test_record_wide_on_another_provider_never_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", KEY)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--out",
            str(tmp_path),
            "--search-provider",
            provider,
            "--max-search-queries",
            "60",
            "--record-wide",
        ],
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("must not launch"))
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: pytest.fail("no git"))
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert "--record-wide" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_a_record_wide_run_passes_the_switch_to_every_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNIMATCH_EXA_API_KEY", KEY)
    monkeypatch.delenv("UNIMATCH_SEARCH_RECORD_WIDE", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--search-provider",
            "exa",
            "--max-search-queries",
            "6",
            "--record-wide",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "sha")
    seen: list[str | None] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(kwargs["env"].get("UNIMATCH_SEARCH_RECORD_WIDE"))
        Path(command[command.index("--out") + 1]).write_text(
            Observation(case_id="groningen").model_dump_json()
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert seen == ["true"]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.config["search_record_wide"] is True


# --- the search log -------------------------------------------------------------------


def test_the_search_log_keeps_the_whole_page_uncut(tmp_path: Path) -> None:
    page = tuple(
        SearchResult(
            url=f"https://www.{DOMAIN}/p{n}",
            title=f"T{n}",
            snippet="s" * 1000,
            provider="exa",
            rank=n,
            retrieved_at=NOW,
        )
        for n in range(1, 26)
    )
    response = SearchResponse(
        query="q",
        provider="exa",
        retrieved_at=NOW,
        results=page[:10],
        page=ProviderPage(
            results=page,
            requested=25,
            parameters=(("numResults", 25),),
            cost=0.022,
            cost_unit="usd",
        ),
    )
    log = live.SearchLog(tmp_path / "c.search.json", "c")
    log.record("exa", "search", {"query": "q", "domains": [DOMAIN]}, response, "discovery")
    (row,) = json.loads((tmp_path / "c.search.json").read_text())["requests"]
    assert [r["rank"] for r in row["results"]] == list(range(1, 26))
    assert all(len(r["snippet"]) == 1000 for r in row["results"])
    assert row["page"] == {
        "requested": 25,
        "returned": 25,
        "consumed": 10,
        "parameters": {"numResults": 25},
        "cost": 0.022,
        "cost_unit": "usd",
    }


def test_no_trace_or_log_cap_truncates_a_wide_record() -> None:
    from app.adapters.discovery import live_discovery
    from app.adapters.search import exa, tavily

    # The log keeps every request a strict case can send and every result of it.
    assert live.SEARCH_LOG_CAP >= 6 * 4
    assert max(exa.SNIPPET_CHARS, tavily.SNIPPET_CHARS) <= live.SEARCH_LOG_SNIPPET_CHARS
    # The trace keeps discovery's own ten per query (what it ranked); the
    # rest of the page reaches the store through the log, not the trace.
    assert live_discovery.SEARCH_RESULTS_PER_QUERY == 10


# --- the store -------------------------------------------------------------------------


def _write_wide_rep(root: Path, urls: list[str], log: list[dict[str, Any]]) -> None:
    target = root / "uio-on" / "20261027T000001Z"
    target.mkdir(parents=True)
    trace = {
        "institution": "University of Oslo",
        "domain": "www.uio.no",
        # The trace keeps the ten discovery ranked (SEARCH_RESULTS_PER_QUERY).
        "search_results": [{"family": "field_and_degree", "urls": urls[:10]}],
    }
    raw = {"canary": {"institutions": [{"country": "Norway", "discovery_trace": trace}]}}
    (target / "uio.raw.json").write_text(json.dumps(raw))
    document = {"schema": live.SEARCH_LOG_SCHEMA, "case": "uio", "requests": log}
    (target / "uio.search.json").write_text(json.dumps(document))


def _wide_logged(query: str, urls: list[str], consumed: int, **extra: Any) -> dict[str, Any]:
    return {
        "provider": "exa",
        "method": "search",
        "kind": "discovery",
        "query": query,
        "domains": ["uio.no"],
        "hl": None,
        "gl": None,
        "max_results": consumed,
        "results": [
            {"rank": n, "url": u, "title": f"T{n}", "snippet": f"S{n}"}
            for n, u in enumerate(urls, start=1)
        ],
        "page": {
            "requested": 25,
            "returned": len(urls),
            "consumed": consumed,
            "parameters": {"numResults": 25},
            "cost": 0.022,
            "cost_unit": "usd",
        },
        **extra,
    }


def test_a_wide_record_run_builds_a_store_of_every_result(tmp_path: Path) -> None:
    run = tmp_path / "run"
    urls = [f"https://www.uio.no/a{n}" for n in range(1, 26)]
    planned = recorded_search.discovery_requests("University of Oslo", "www.uio.no", "Norway")
    request = planned["field_and_degree"]
    topic = [f"https://www.uio.no/t{n}" for n in range(1, 26)]
    _write_wide_rep(
        run,
        urls,
        [
            _wide_logged(request.query, urls, 10),
            _wide_logged("uio.no application deadline", topic, 5, kind="topic"),
        ],
    )
    document = recorded_search.build_store([("dev3", "9", "2026-10-27T00:00:00Z", "abc", run)])
    assert document["schema"] == "recorded-search/2"
    by_family = {e["family"]: e for e in document["entries"]}
    traced = by_family["field_and_degree"]
    assert traced["urls"] == urls  # all 25, not the trace's ten
    assert [r["rank"] for r in traced["results"]] == list(range(1, 26))
    assert traced["provider"] == "exa"
    assert traced["page"]["consumed"] == 10 and traced["page"]["cost_unit"] == "usd"
    assert len(by_family[""]["urls"]) == 25 and by_family[""]["page"]["consumed"] == 5
    assert document["provenance"]["record_wide"]["entries"] == 2
    assert document["provenance"]["record_wide"]["results"] == 50

    # Replay: the top N a caller asks for, titles included; discovery's ten.
    store = RecordedSearchStore.from_document(document)
    provider = RecordedSearchProvider(store, now=NOW)

    def replay(query: str, domains: Any, n: int) -> SearchResponse:
        return asyncio.run(provider.search(query=query, domains=domains, max_results=n))

    ten = replay(request.query, request.domains, 10)
    assert [r.url for r in ten.results] == urls[:10]
    assert ten.results[0].title == "T1" and ten.page is None
    every = replay(request.query, request.domains, 25)
    assert [r.url for r in every.results] == urls
    five = replay("uio.no application deadline", ["uio.no"], 5)
    assert [r.url for r in five.results] == topic[:5]
    assert COUNTERS.misses == 0


def _v2(entry: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "recorded-search/2", "provenance": {}, "entries": [entry]}


def _entry(urls: list[str], **extra: Any) -> dict[str, Any]:
    return {"query": "q", "domains": [], "hl": None, "gl": None, "urls": urls, **extra}


URLS = [f"https://www.uni.edu/w{n}" for n in range(1, 4)]
RESULTS = [{"rank": n, "url": u, "title": "", "snippet": ""} for n, u in enumerate(URLS, 1)]
PAGE = {"requested": 25, "returned": 3, "consumed": 2}


def test_a_wide_entry_loads() -> None:
    store = RecordedSearchStore.from_document(_v2(_entry(URLS, results=RESULTS, page=PAGE)))
    assert len(store) == 1


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (_v2(_entry(URLS, results=RESULTS[::-1])), "in order"),
        (
            _v2(_entry(URLS, results=[{**r, "rank": 9} for r in RESULTS])),
            "1-based position",
        ),
        (_v2(_entry(URLS, results=RESULTS, page={**PAGE, "consumed": 4})), "consumed no more"),
        (_v2(_entry(URLS, results=RESULTS, page={**PAGE, "returned": 2})), "at least the URLs"),
        (_v2(_entry(URLS, results=RESULTS, page={**PAGE, "requested": "25"})), "whole numbers"),
        (_v2(_entry(URLS, page=PAGE)), "beside 'results'"),
        (
            {"schema": "recorded-search/1", "entries": [_entry(URLS, page=PAGE)]},
            "'page' needs 'recorded-search/2'",
        ),
    ],
)
def test_a_malformed_wide_entry_is_refused(document: dict[str, Any], message: str) -> None:
    with pytest.raises(RecordedStoreError, match=message):
        RecordedSearchStore.from_document(document)


def test_the_committed_base3_store_still_loads_unchanged() -> None:
    store = RecordedSearchStore.from_file(live.BASE3_RECORDED_STORE)
    assert len(store) > 100 and store.texts == {}


# --- no duplicate spend ------------------------------------------------------------------


@pytest.fixture
def _exa_mcp(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    monkeypatch.setattr(live, "_jev_shadow", lambda *a, **k: _none())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _none() -> None:
    return None


def _report() -> dict[str, Any]:
    return {"institutions": [{"programs": []}], "run_error": ""}


def _patch_sender(monkeypatch: pytest.MonkeyPatch, sent: list[tuple[str, int]], wide: bool):
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider

    async def search(self: Any, *, query: str, domains: Any = (), max_results: int = 10):
        sent.append((query, max_results))
        response = await _WideFake(25 if wide else max_results).search(
            query=query, max_results=max_results
        )
        page = response.page if wide else None
        results = tuple(
            SearchResult(
                url=r.url, title=r.title, provider="exa_mcp", rank=r.rank, retrieved_at=NOW
            )
            for r in (page.results if page else response.results)
        )
        return SearchResponse(
            query=query,
            provider="exa_mcp",
            retrieved_at=NOW,
            results=results[:max_results],
            page=ProviderPage(results=results, requested=25) if wide else None,
        )

    monkeypatch.setattr(ExaMcpSearchProvider, "search", search)
    return ExaMcpSearchProvider


@pytest.mark.parametrize("strict", [False, True])
async def test_a_request_already_answered_is_never_sent_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _exa_mcp: Any, strict: bool
) -> None:
    sent: list[tuple[str, int]] = []
    cls = _patch_sender(monkeypatch, sent, wide=True)
    ledger = SearchQueryLedger.open(tmp_path / "search_ledger.json", 6)
    answers: list[list[str]] = []

    async def run(*args: Any) -> dict[str, Any]:
        provider = cls()
        for query, domains, n in (
            ("cs bachelor", [DOMAIN], 10),
            ("cs bachelor", [DOMAIN], 10),  # the same request
            ("  CS   Bachelor ", [DOMAIN.upper()], 5),  # the same key, a shorter head
            ("cs master", [DOMAIN], 10),  # a different request
            ("cs bachelor", [DOMAIN], 20),  # within the recorded page of 25
        ):
            response = await provider.search(query=query, domains=domains, max_results=n)
            answers.append([r.url for r in response.results])
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen", output, 60, 120, strict_expert_budget=strict, search_ledger=ledger
    )
    assert sent == [("cs bachelor", 10), ("cs master", 10)]
    assert ledger.state() == {"max_search_queries": 6, "used": 2, "refused": 0}
    assert answers[1] == answers[0] and answers[2] == answers[0][:5]
    assert answers[4] == [f"https://www.{DOMAIN}/r{n}" for n in range(1, 21)]
    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.search_cache_hits == 3
    # The case's own budget counts every request asked, as an uncached
    # capture did, so the pipeline's choices are unchanged.
    assert observation.telemetry.search_calls == 5
    log = json.loads(output.with_suffix(".search.json").read_text())
    assert [r["query"] for r in log["requests"]] == ["cs bachelor", "cs master"]
    if strict:
        budget = json.loads(output.with_suffix(".budget.json").read_text())
        assert budget["search_queries"] == 5


async def test_a_narrow_answer_is_resent_only_for_a_longer_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _exa_mcp: Any
) -> None:
    sent: list[tuple[str, int]] = []
    cls = _patch_sender(monkeypatch, sent, wide=False)
    ledger = SearchQueryLedger.open(tmp_path / "search_ledger.json", 6)

    async def run(*args: Any) -> dict[str, Any]:
        provider = cls()
        await provider.search(query="q", max_results=3)
        await provider.search(query="q", max_results=2)  # inside the first answer
        await provider.search(query="q", max_results=10)  # more than it could hold
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120, search_ledger=ledger)
    assert sent == [("q", 3), ("q", 10)]
    assert ledger.state()["used"] == 2
    assert Observation.model_validate_json(output.read_text()).telemetry.search_cache_hits == 1


async def test_a_replay_is_never_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _exa_mcp: Any
) -> None:
    store = RecordedSearchStore.from_document(_v2(_entry(URLS)))

    async def run(*args: Any) -> dict[str, Any]:
        for _ in range(2):
            await RecordedSearchProvider(store).search(query="q")
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120)
    assert COUNTERS.hits == 2
    assert "search_cache_hits" not in output.read_text()


def test_a_capture_without_a_repeat_keeps_its_bytes() -> None:
    assert "search_cache_hits" not in Observation(case_id="c").model_dump_json()
    assert recorded.request_key(" A  b ", ["X.edu"]) == recorded.request_key("a b", ["x.edu"])
