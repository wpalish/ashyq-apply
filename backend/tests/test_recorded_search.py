"""Recorded-search replay: search answered from captured lists, never from a provider.

Owner decision 2026-10-19: paid search frozen, no scraping; the work after search
goes on offline by replaying the result lists Serper returned in past captures.
Offline only: synthetic stores and runs, a faked capture child, no network.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import inspect
import json
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

from app.adapters.search import get_search_provider, recorded
from app.adapters.search.recorded import (
    COUNTERS,
    RecordedSearchProvider,
    RecordedSearchStore,
    RecordedStoreError,
    load_store,
    request_key,
)
from app.config import Settings, get_settings
from evaluation.research import live, recorded_search, scorecard, stage_summary
from evaluation.research.schema import Capture, Observation, Telemetry
from tests import test_stage_summary as staged

STORE = live.DEFAULT_RECORDED_STORE
#: The Serper store built from the base3 captures (the default until 2026-10-26).
BASE3 = live.BASE3_RECORDED_STORE


def _document(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "recorded-search/1", "provenance": {"sources": []}, "entries": list(entries)}


def _entry(query: str, urls: list[str], **extra: Any) -> dict[str, Any]:
    return {"query": query, "domains": ["uni.edu"], "hl": None, "gl": None, "urls": urls, **extra}


URLS = [f"https://www.uni.edu/p{n}" for n in range(1, 11)]


@pytest.fixture(autouse=True)
def _fresh_counters():
    COUNTERS.reset()
    yield
    COUNTERS.reset()


def _provider(*entries: dict[str, Any]) -> RecordedSearchProvider:
    return RecordedSearchProvider(RecordedSearchStore.from_document(_document(*entries)))


# --- hit ----------------------------------------------------------------------


async def test_a_recorded_request_is_answered_in_its_recorded_order() -> None:
    provider = _provider(_entry('site:uni.edu "computer science" "bachelor"', URLS))
    response = await provider.search(
        query='site:uni.edu "computer science" "bachelor"', domains=["uni.edu"], max_results=3
    )
    assert [r.url for r in response.results] == URLS[:3]
    assert [r.rank for r in response.results] == [1, 2, 3]
    assert {r.provider for r in response.results} == {"recorded"}
    # The captures keep URLs only: no title or snippet is invented.
    assert all(r.title == "" and r.snippet == "" for r in response.results)
    assert (COUNTERS.hits, COUNTERS.misses) == (1, 0)


async def test_the_key_ignores_spacing_case_and_domain_order_but_not_the_domain() -> None:
    provider = _provider(_entry("Uni  Bachelor computer science", URLS, domains=["b.edu", "a.edu"]))
    hit = await provider.search(
        query=" uni bachelor   COMPUTER science ", domains=["A.edu", "b.edu", "a.edu"]
    )
    assert len(hit.results) == 10
    missed = await provider.search(query="uni bachelor computer science", domains=["c.edu"])
    assert missed.results == ()
    assert (COUNTERS.hits, COUNTERS.misses) == (1, 1)


async def test_a_localised_request_is_keyed_by_its_language_and_country() -> None:
    provider = _provider(
        _entry("site:uio.no informatikk bachelor", URLS, domains=[], hl="no", gl="no")
    )
    hit = await provider.search_localized(
        query="site:uio.no informatikk bachelor", hl="no", gl="no", domains=()
    )
    assert len(hit.results) == 10
    # The same words without hl/gl were never recorded.
    plain = await provider.search(query="site:uio.no informatikk bachelor")
    assert plain.results == ()
    assert (COUNTERS.hits, COUNTERS.misses) == (1, 1)


# --- miss ---------------------------------------------------------------------


async def test_a_request_never_recorded_is_an_explicit_counted_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the recorded provider sent a request")

    monkeypatch.setattr(httpx.AsyncClient, "send", no_network)
    monkeypatch.setattr(httpx.Client, "send", no_network)
    provider = _provider(_entry("recorded words", URLS))
    response = await provider.search(query="words a rule changed", domains=["uni.edu"])
    assert response.results == ()
    assert response.provider == "recorded"
    assert COUNTERS.misses == 1
    assert COUNTERS.missed == [
        recorded.key_digest(request_key("words a rule changed", ["uni.edu"]))
    ]


def test_the_module_imports_no_network_client_and_no_other_provider() -> None:
    tree = ast.parse(Path(recorded.__file__).read_text(encoding="utf-8"))
    modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {m for m in modules if m.split(".")[0] in {"httpx", "requests", "socket", "urllib3"}}
    assert {m for m in modules if m.startswith("app.")} == {"app.adapters.search.base"}


# --- no paid fallback is possible ---------------------------------------------


def test_the_provider_takes_a_store_and_a_clock_and_nothing_else() -> None:
    assert list(inspect.signature(RecordedSearchProvider).parameters) == ["store", "now"]
    with pytest.raises(TypeError, match="RecordedSearchStore only"):
        RecordedSearchProvider(object())  # type: ignore[arg-type]
    instance = _provider()
    assert not any(
        hasattr(value, "search")
        for value in vars(instance).values()
        if not isinstance(value, RecordedSearchStore)
    )


async def test_recorded_with_a_paid_key_set_still_never_calls_the_paid_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.search.serper import SerperSearchProvider

    async def paid(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a paid provider was asked")

    monkeypatch.setattr(SerperSearchProvider, "search", paid)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "recorded")
    monkeypatch.setenv("UNIMATCH_RECORDED_SEARCH_STORE", str(STORE))
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "not-a-real-key")
    get_settings.cache_clear()
    try:
        provider = get_search_provider()
        assert provider.name == "recorded"
        assert isinstance(provider.inner, RecordedSearchProvider)  # type: ignore[attr-defined]
        missed = await provider.search(query="a query nobody recorded", domains=["uni.edu"])
    finally:
        get_settings.cache_clear()
    assert missed.results == ()
    assert COUNTERS.misses == 1


def test_settings_refuse_recorded_without_a_store_and_in_production(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="UNIMATCH_RECORDED_SEARCH_STORE"):
        Settings(search_provider="recorded")._validate_search()
    with pytest.raises(RuntimeError, match="UNIMATCH_RECORDED_SEARCH_STORE"):
        Settings(
            search_provider="recorded", recorded_search_store=tmp_path / "absent.json"
        )._validate_search()
    with pytest.raises(RuntimeError, match="must not be 'recorded' in production"):
        Settings(
            search_provider="recorded", recorded_search_store=STORE, environment="production"
        )._validate_search()
    Settings(search_provider="recorded", recorded_search_store=STORE)._validate_search()


def test_live_blanks_every_paid_key_for_a_recorded_child() -> None:
    environment = live.search_environment("recorded", STORE)
    assert environment["UNIMATCH_RECORDED_SEARCH_STORE"] == str(STORE)
    assert {k: environment[k] for k in live.PAID_SEARCH_KEYS} == dict.fromkeys(
        live.PAID_SEARCH_KEYS, ""
    )
    # Any capture measures the web pipeline, never the knowledge base (default kb).
    assert environment["UNIMATCH_KNOWLEDGE_MODE"] == "live"
    assert live.search_environment("serper", None) == {"UNIMATCH_KNOWLEDGE_MODE": "live"}
    with pytest.raises(ValueError):
        live.search_environment("recorded", None)


# --- store loading -------------------------------------------------------------


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"schema": "other", "entries": []}, "recorded-search/1"),
        ({"schema": "recorded-search/1", "entries": {}}, "'entries' must be a list"),
        (_document({"query": " ", "urls": []}), "has no query"),
        (_document(_entry("q", ["ftp://uni.edu/x"])), "http"),
        (_document(_entry("q", URLS[:1]), _entry("Q", URLS[1:2])), "different result list"),
        (_document(_entry("q", URLS, hl=5)), "'hl'/'gl'"),
    ],
)
def test_a_malformed_store_is_refused(document: dict[str, Any], message: str) -> None:
    with pytest.raises(RecordedStoreError, match=message):
        RecordedSearchStore.from_document(document)


def test_a_store_file_is_read_once_until_it_changes(tmp_path: Path) -> None:
    path = tmp_path / "store.json"
    path.write_text(json.dumps(_document(_entry("q", URLS))))
    first = load_store(path)
    assert load_store(path) is first
    path.write_text(json.dumps(_document(_entry("q", URLS), _entry("r", URLS))))
    assert len(load_store(path)) == 2
    with pytest.raises(RecordedStoreError, match="cannot read"):
        RecordedSearchStore.from_file(tmp_path / "missing.json")


def _development_only(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    store = RecordedSearchStore.from_document(document)
    assert len(store) == len(document["entries"]) > 100
    entries = document["entries"]
    assert {e["set"] for e in entries} == set(recorded_search.DEV_SETS)
    for entry in entries:
        assert entry["case"] in recorded_search.DEV_SETS[entry["set"]]
        assert entry["case"] not in recorded_search.FORBIDDEN_CASES
    forbidden = {*live.HELDOUT.values(), *live.DEV5_DOMAINS.values()}
    hosts = {urlsplit(u).hostname or "" for e in entries for u in e["urls"]}
    assert not {h for h in hosts for d in forbidden if h == d or h.endswith("." + d)}
    sources = document["provenance"]["sources"]
    assert {s["set"] for s in sources} == set(recorded_search.DEV_SETS)
    return list(sources)


def test_the_committed_store_holds_the_four_development_sets_only() -> None:
    sources = _development_only(BASE3)
    assert all(s["run_id"] and s["run_created_at"] < "2026-10-19T05:11" for s in sources)


def test_the_default_store_is_the_fused_store_of_exa_r1_and_serper_base3() -> None:
    """Owner flip 2026-10-26 (LOOP_REPORT): replay answers from fused1 by default."""
    assert STORE.name == "recorded_search.fused1.json"
    assert BASE3.name == "recorded_search.base3.json" and BASE3.is_file()
    sources = _development_only(STORE)
    assert {s["run_id"] for s in sources} == {
        "40314322985",  # Exa R1 (record-wide), every set
        "39172483236",
        "39172484697",
        "39172486984",
        "39172488858",
    }
    document = json.loads(STORE.read_text(encoding="utf-8"))
    assert document["schema"] == "recorded-search/2"
    assert document["provenance"]["fused"]["order"] == "interleave"


def test_the_committed_store_keys_are_todays_discovery_requests() -> None:
    """Every stored request is what discovery sends today for its case.

    Fails when the default discovery queries change: the store would then
    replay nothing for them. Rebuild it (``evaluation.research.recorded_search``)
    or accept that the replay misses those queries. The base3 store holds
    discovery's requests only (fused1 adds topic and scholarship ones).
    """
    document = json.loads(BASE3.read_text(encoding="utf-8"))
    plans: dict[tuple[str, str, str], dict[str, recorded_search.Request]] = {}
    for entry in document["entries"]:
        identity = (entry["institution"], entry["host"], entry["country"])
        if identity not in plans:
            plans[identity] = recorded_search.discovery_requests(*identity)
        request = plans[identity][entry["family"]]
        assert request_key(request.query, request.domains, request.hl, request.gl) == (
            request_key(entry["query"], entry["domains"], entry["hl"], entry["gl"])
        ), entry["case"]


# --- the builder ----------------------------------------------------------------


def _write_rep(root: Path, case_id: str, arm: str, stamp: str, trace: dict[str, Any]) -> None:
    target = root / f"{case_id}-{arm}" / stamp
    target.mkdir(parents=True)
    raw = {"canary": {"institutions": [{"country": "Norway", "discovery_trace": trace}]}}
    (target / f"{case_id}.raw.json").write_text(json.dumps(raw))


def _trace(urls: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "institution": "University of Oslo",
        "domain": "www.uio.no",
        "search_results": [{"family": "field_and_degree", "urls": urls}],
        **extra,
    }


def test_the_builder_keeps_the_modal_list_and_drops_failed_repetitions(tmp_path: Path) -> None:
    run = tmp_path / "run"
    a, b = (
        [f"https://www.uio.no/a{n}" for n in range(3)],
        [f"https://www.uio.no/b{n}" for n in range(3)],
    )
    _write_rep(run, "uio", "off", "20261018T000001Z", _trace(b))
    _write_rep(run, "uio", "on", "20261018T000002Z", _trace(a))
    _write_rep(run, "uio", "on", "20261018T000003Z", _trace(a))
    _write_rep(
        run, "uio", "off", "20261018T000004Z", _trace(b, search_failures=["(serper; HTTP 400)"])
    )
    # A heldout case's directory is never opened: its file is not even JSON.
    (run / "nu-off" / "20261018T000001Z").mkdir(parents=True)
    (run / "nu-off" / "20261018T000001Z" / "nu.raw.json").write_text("not json")
    document = recorded_search.build_store([("dev3", "123", "2026-10-18T00:00:00Z", "abc", run)])
    (entry,) = document["entries"]
    assert entry["urls"] == a
    assert entry["agreement"] == "2/3"
    assert entry["case"] == "uio" and entry["family"] == "field_and_degree"
    assert entry["query"] == 'site:uio.no "computer science" "bachelor"'
    assert entry["domains"] == ["uio.no"]
    (source,) = document["provenance"]["sources"]
    assert source["repetitions_read"] == 3
    assert source["repetitions_excluded"] == [
        {"repetition": "uio-off/20261018T000004Z", "reason": "search_failures recorded"}
    ]
    assert recorded_search.coverage(document) == {"dev3": {"cases": 1, "requests": 1}}
    RecordedSearchStore.from_document(document)


def test_the_builder_refuses_other_sets_and_unknown_families(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a development set"):
        recorded_search.collect("dev5", "1", "d", "s", tmp_path)
    with pytest.raises(SystemExit):
        recorded_search.main(["--source", "heldout", "1", "d", "s", str(tmp_path), "--out", "x"])
    run = tmp_path / "run"
    trace = _trace([])
    trace["search_results"] = [{"family": "invented", "urls": []}]
    _write_rep(run, "uio", "off", "20261018T000001Z", trace)
    with pytest.raises(ValueError, match="not in the rebuilt query plan"):
        recorded_search.collect("dev3", "1", "d", "s", run)


def test_the_local_language_request_goes_through_search_localized() -> None:
    plan = recorded_search.discovery_requests("University of Oslo", "www.uio.no", "Norway")
    local = plan["local_language"]
    assert (local.hl, local.gl) == ("no", "no")
    assert local.domains == ()
    assert plan["natural_language"].domains == ("uio.no",)


# --- the harness CLI ------------------------------------------------------------


def _parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *flags: str) -> list[dict[str, Any]]:
    argv = ["live", "--live", "--case", "uio", "--out", str(tmp_path), *flags]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    monkeypatch.delenv("UNIMATCH_RECORDED_SEARCH_STORE", raising=False)
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "not-a-real-key")
    calls: list[dict[str, Any]] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, "env": kwargs["env"]})
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="uio").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    return calls


def test_the_cli_replays_the_default_store_with_no_paid_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (call,) = _parent(monkeypatch, tmp_path, "--search-provider", "recorded", "--trust-env-proxy")
    command, env = call["command"], call["env"]
    assert command[command.index("--search-provider") + 1] == "recorded"
    assert "--trust-env-proxy" in command
    assert env["UNIMATCH_SEARCH_PROVIDER"] == "recorded"
    assert env["UNIMATCH_RECORDED_SEARCH_STORE"] == str(STORE.resolve())
    assert env["UNIMATCH_SERPER_API_KEY"] == ""
    assert env["UNIMATCH_KNOWLEDGE_MODE"] == "live"
    (capture_path,) = tmp_path.glob("*/capture.json")
    config = Capture.model_validate_json(capture_path.read_text()).config
    assert config["search_provider"] == "recorded"
    replayed = config["recorded_search_store"]
    assert isinstance(replayed, dict)
    assert replayed["file"] == STORE.name
    assert replayed["source_runs"] == [
        "40314322985",
        "40314322985",
        "40314322985",
        "40314322985",
        "39172483236",
        "39172484697",
        "39172486984",
        "39172488858",
    ]
    assert config["trust_env_proxy"] is True


def test_the_cli_takes_an_explicit_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = tmp_path / "mine.json"
    store.write_text(json.dumps(_document(_entry("q", URLS))))
    (call,) = _parent(
        monkeypatch,
        tmp_path / "out",
        "--search-provider",
        "recorded",
        "--recorded-store",
        str(store),
    )
    assert call["env"]["UNIMATCH_RECORDED_SEARCH_STORE"] == str(store.resolve())


@pytest.mark.parametrize(
    "flags",
    [
        ("--recorded-store", str(STORE)),
        ("--search-provider", "recorded", "--recorded-store", "/nonexistent/store.json"),
    ],
)
def test_the_cli_refuses_a_store_without_replay_or_an_unreadable_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, flags: tuple[str, ...]
) -> None:
    with pytest.raises(SystemExit):
        _parent(monkeypatch, tmp_path, *flags)


def test_a_live_capture_child_is_still_told_to_measure_the_web_pipeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (call,) = _parent(monkeypatch, tmp_path, "--search-provider", "none")
    assert call["env"]["UNIMATCH_KNOWLEDGE_MODE"] == "live"
    assert "UNIMATCH_RECORDED_SEARCH_STORE" not in call["env"]
    assert call["env"]["UNIMATCH_SERPER_API_KEY"] == "not-a-real-key"


# --- the stage summary and the scorecard report misses -------------------------


def _replay_run(root: Path, misses: dict[str, int]) -> Path:
    staged._run(root)
    for case_id in staged.IDS:
        path = next((root / f"{case_id}-off").glob("*/capture.json"))
        capture = json.loads(path.read_text())
        capture["config"]["search_provider"] = "recorded"
        capture["observations"][0]["telemetry"].update(
            recorded_search_hits=3, recorded_search_misses=misses[case_id]
        )
        path.write_text(json.dumps(capture))
    return root


def test_the_stage_summary_counts_recorded_hits_and_misses(tmp_path: Path) -> None:
    run = _replay_run(tmp_path / "run", {"zqalpha": 2, "zqbeta": 0})
    column = stage_summary.summarize_run(staged._dataset(), stage_summary.load_run(run))
    funnel = column["columns"]["off#1"]["discovery funnel"]
    assert funnel["recorded_search_hits"] == 6
    assert funnel["recorded_search_misses"] == 2
    assert funnel["recorded_search_cases_with_miss"] == 1
    text = stage_summary.guarded_render(staged._dataset(), stage_summary.load_run(run))
    assert "| recorded_search_misses | 2 |" in text


def test_a_live_run_has_no_recorded_rows(tmp_path: Path) -> None:
    run = staged._run(tmp_path / "run")
    column = stage_summary.summarize_run(staged._dataset(), stage_summary.load_run(run))
    assert "recorded_search_misses" not in column["columns"]["off#1"]["discovery funnel"]


def _replayed(misses: int) -> dict[str, Any]:
    from tests.test_scorecard import DEADLINE, capture

    replay = capture([DEADLINE])
    replay["config"]["search_provider"] = "recorded"
    replay["observations"][0]["telemetry"].update(
        recorded_search_hits=4, recorded_search_misses=misses
    )
    return replay


@pytest.mark.parametrize("summary_only", [False, True])
def test_a_rule_that_changes_the_queries_is_flagged_and_fails_a_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], summary_only: bool
) -> None:
    from tests.test_scorecard import dataset, write_run

    run = write_run(
        tmp_path / "run",
        {"off": [_replayed(1), _replayed(1)], "on": [_replayed(1), _replayed(3)]},
    )
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    args = [str(run), "--dataset", str(corpus), "--out", str(tmp_path / "c.json")]
    assert scorecard.main(args + (["--summary-only"] if summary_only else [])) == 0
    printed = capsys.readouterr().out
    assert "Recorded-search replay" in printed
    assert "WARNING: THE QUERIES CHANGED" in printed
    assert "on#2" in printed
    assert "| on | recorded_search_misses | 3 | <= 1 | NO |" in printed
    saved = json.loads((tmp_path / "c.json").read_text())
    rows = {r["arm"]: r for r in saved["targets"] if r["metric"] == "recorded_search_misses"}
    assert rows["off"]["met"] is True
    assert rows["on"]["met"] is False and rows["on"]["worst"] == 3


def test_unchanged_queries_on_a_replay_note_it_without_a_warning(tmp_path: Path) -> None:
    from tests.test_scorecard import dataset, write_run

    run = write_run(tmp_path / "run", {"off": [_replayed(2)], "on": [_replayed(2)]})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["arms"]["on"]["repetitions"][0]["recorded_search"] == {
        "hits": 4,
        "misses": 2,
        "cases_with_miss": 1,
    }
    text = scorecard.render(card)
    assert "Recorded-search replay" in text and "WARNING" not in text
    assert all(r["met"] for r in card["targets"] if r["metric"] == "recorded_search_misses")
    assert "recorded search answered/missed | 4/2 | 4/2" in scorecard.render_summary(
        scorecard.summarize(card)
    )


def test_a_live_run_has_no_replay_rows(tmp_path: Path) -> None:
    from tests.test_scorecard import DEADLINE, capture, dataset, write_run

    run = write_run(tmp_path / "run", {"off": [capture([DEADLINE])], "on": [capture([DEADLINE])]})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert "recorded_search" not in card["arms"]["on"]["repetitions"][0]
    assert "Recorded-search replay" not in scorecard.render(card)
    assert not any(r["metric"] == "recorded_search_misses" for r in card["targets"])


def test_recorded_without_a_store_is_a_missing_search_layer_not_a_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.search import SearchProviderNotConfigured

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "recorded")
    monkeypatch.delenv("UNIMATCH_RECORDED_SEARCH_STORE", raising=False)
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "not-a-real-key")
    get_settings.cache_clear()
    try:
        with pytest.raises(SearchProviderNotConfigured, match="RECORDED_SEARCH_STORE"):
            get_search_provider()
    finally:
        get_settings.cache_clear()


# --- H-1: misses per search kind ----------------------------------------------


async def test_a_miss_is_counted_under_the_kind_of_search_that_sent_it() -> None:
    provider = _provider(_entry("recorded words", URLS))
    with recorded.search_kind("discovery"):
        await provider.search(query="recorded words", domains=["uni.edu"])
        await provider.search(query="a second pass never recorded", domains=["uni.edu"])
        with recorded.search_kind("topic"):
            await provider.search(query="deadline page", domains=["uni.edu"])
        await provider.search_localized(
            query="ein lokaler Satz", hl="de", gl="de", domains=["uni.edu"]
        )
    with recorded.search_kind("scholarship"):
        await provider.search(query="scholarships for international students")
    await provider.search(query="outside every marked stage")
    assert (COUNTERS.hits, COUNTERS.misses) == (1, 5)
    assert COUNTERS.misses_by_kind == {
        "discovery": 2,
        "topic": 1,
        "scholarship": 1,
        "identity": 0,
    }
    COUNTERS.reset()
    assert COUNTERS.misses_by_kind == dict.fromkeys(recorded.SEARCH_KINDS, 0)


async def test_concurrent_searches_keep_the_kind_they_were_started_in() -> None:
    provider = _provider()

    async def ask(kind: str, n: int) -> None:
        with recorded.search_kind(kind):
            for i in range(n):
                await asyncio.sleep(0)
                await provider.search(query=f"{kind} {i}")

    await asyncio.gather(ask("discovery", 3), ask("identity", 2), ask("topic", 1))
    assert COUNTERS.misses_by_kind == {
        "discovery": 3,
        "topic": 1,
        "scholarship": 0,
        "identity": 2,
    }


def test_an_unknown_search_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown search kind"), recorded.search_kind("award"):
        pass


@pytest.mark.parametrize("stage", live.SEARCH_KIND_STAGES, ids=lambda s: s[3])
async def test_the_harness_marks_each_stage_that_searches(
    monkeypatch: pytest.MonkeyPatch, stage: tuple[str, str | None, str, str]
) -> None:
    module_name, owner_name, attribute, kind = stage
    module = importlib.import_module(module_name)
    owner = getattr(module, owner_name) if owner_name else module
    provider = _provider()
    observed: list[str] = []

    # Stands in for the stage (and for an observer the harness already
    # installed on it): one search that misses, then the stage's own answer.
    async def stage_body(*args: Any, **kwargs: Any) -> str:
        await provider.search(query="never recorded")
        observed.append("observer kept")
        return "stage answer"

    monkeypatch.setattr(owner, attribute, stage_body)
    with ExitStack() as stack:
        for kind_patch in live.search_kind_patches():
            stack.enter_context(kind_patch)
        assert await getattr(owner, attribute)() == "stage answer"
    assert getattr(owner, attribute) is stage_body
    assert observed == ["observer kept"]
    assert COUNTERS.misses == 1
    assert COUNTERS.misses_by_kind[kind] == 1
    assert sum(COUNTERS.misses_by_kind.values()) == 1


def test_the_harness_copies_the_counters_per_kind_into_telemetry() -> None:
    COUNTERS.hits, COUNTERS.misses = 4, 6
    COUNTERS.misses_by_kind.update(discovery=1, topic=2, scholarship=3)
    telemetry = Telemetry()
    live.recorded_kind_telemetry(telemetry, COUNTERS)
    assert telemetry.model_dump(exclude_none=True) == {
        "recorded_search_hits": 4,
        "recorded_search_misses": 6,
        "recorded_search_misses_discovery": 1,
        "recorded_search_misses_topic": 2,
        "recorded_search_misses_scholarship": 3,
        "recorded_search_misses_identity": 0,
    }
    # A live capture keeps its bytes: the fields are not serialised unset.
    assert "recorded_search" not in Telemetry().model_dump_json()
