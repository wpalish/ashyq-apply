"""Offline actual-wrapper checks for comparable strict algorithm captures."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.fetching import FetchResult
from app.adapters.search.base import SearchResponse, SearchUnavailable
from app.config import get_settings
from app.domain.enums import DegreeLevel, FetchOutcome
from evaluation.research import live
from evaluation.research.schema import Capture, Observation
from scripts import canary_discovery as canary


@pytest.fixture(autouse=True)
def _public_strict_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _report() -> dict[str, Any]:
    return {"institutions": [{"programs": []}], "run_error": ""}


class _Fetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.tier_counts = {"browser": 0}

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append((url, kwargs))
        return FetchResult(url=url, outcome=FetchOutcome.CACHED, from_cache=True)


def _output(tmp_path: Path) -> Path:
    return tmp_path / "groningen.json"


@pytest.mark.asyncio
@pytest.mark.parametrize("strict", [True, False])
async def test_strict_capture_skips_sealed_gold_shadow_but_keeps_app_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, strict: bool
) -> None:
    from unittest.mock import AsyncMock

    from app.adapters.discovery.live_discovery import (
        DiscoveryTrace,
        LiveDiscoveryAdapter,
        PageCategory,
    )

    shadow, confirm = AsyncMock(), AsyncMock()
    monkeypatch.setattr(live, "_jev_shadow", shadow)
    monkeypatch.setattr(LiveDiscoveryAdapter, "_confirm_programs", confirm)

    async def run(*args: Any) -> dict[str, Any]:
        adapter = object.__new__(LiveDiscoveryAdapter)
        await adapter._confirm_programs(
            {PageCategory.PROGRAM_PAGE: ["https://rug.nl/programme"]},
            {PageCategory.PROGRAM_PAGE: []},
            DiscoveryTrace(institution="Public university", domain="rug.nl"),
            canary.canary_profile(),
        )
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("groningen", _output(tmp_path), 60, 120, strict_expert_budget=strict)
    assert confirm.await_count == 1
    assert shadow.await_count == (0 if strict else 1)


@pytest.mark.asyncio
async def test_strict_get_cap_is_shared_across_fetchers_and_cache_hits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetchers = [_Fetcher(), _Fetcher()]
    pending = iter(fetchers)
    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: next(pending))

    async def run(*args: Any) -> dict[str, Any]:
        runner = object.__new__(canary.CanaryRunner)
        first, second = runner._make_fetcher(), runner._make_fetcher()
        await first.get("https://rug.nl/a", use_cache=True)
        await second.get("https://rug.nl/b")
        with pytest.raises(RuntimeError, match="PAGE_BUDGET_EXHAUSTED"):
            await first.get("https://rug.nl/blocked")
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("groningen", _output(tmp_path), 2, 120, strict_expert_budget=True)
    assert [len(fetcher.calls) for fetcher in fetchers] == [1, 1]
    assert all(kwargs["use_cache"] is False for f in fetchers for _url, kwargs in f.calls)
    observation = Observation.model_validate_json(_output(tmp_path).read_text())
    assert observation.telemetry.http_fetches == 2
    budget = json.loads(_output(tmp_path).with_suffix(".budget.json").read_text())
    assert budget["fetcher_calls"] == 2
    assert budget["network_http_requests"] == 0
    assert budget["stop_reason"] == "page_budget_exhausted"


@pytest.mark.asyncio
async def test_legacy_cache_hits_keep_their_existing_free_page_accounting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = _Fetcher()
    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: fetcher)

    async def run(*args: Any) -> dict[str, Any]:
        wrapped = object.__new__(canary.CanaryRunner)._make_fetcher()
        await wrapped.get("https://rug.nl/a")
        await wrapped.get("https://rug.nl/b")
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("groningen", _output(tmp_path), 1, 120)
    assert len(fetcher.calls) == 2
    assert all("use_cache" not in kwargs for _url, kwargs in fetcher.calls)
    assert not _output(tmp_path).with_suffix(".budget.json").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_status", [None, 402, 429])
async def test_search_budget_wraps_cached_provider_across_discovery_and_funding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_status: int | None,
) -> None:
    import app.adapters.search
    from app.adapters.base import AdapterResult, Candidate, CandidateProgram
    from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider
    from app.adapters.search.intent import DiscoveryIntent
    from app.adapters.search.retrieval import discover_candidates

    queries: list[str] = []
    cached = ExaMcpSearchProvider()

    async def search(self: Any, *, query: str, **kwargs: Any) -> SearchResponse:
        queries.append(query)
        if failure_status is not None:
            raise SearchUnavailable("Bearer vendor-secret-key response", http_status=failure_status)
        return SearchResponse(query=query, provider="exa_mcp", retrieved_at=datetime.now(UTC))

    monkeypatch.setattr(ExaMcpSearchProvider, "search", search)
    monkeypatch.setattr(app.adapters.search, "get_search_provider", lambda: cached)
    original = ExaMcpSearchProvider.search

    async def run(*args: Any) -> dict[str, Any]:
        intent = DiscoveryIntent(
            institution="University of Groningen",
            domain="rug.nl",
            degree=DegreeLevel.BACHELOR,
            field="computer science",
        )
        await discover_candidates(cached, intent, query_budget=6)
        adapter = object.__new__(WebScholarshipAdapter)
        adapter._award_searches = {}
        await adapter._search_awards(
            Candidate(
                name="University of Groningen", country="NL", city="Groningen", domain="rug.nl"
            ),
            CandidateProgram(
                name="Computer Science", degree=DegreeLevel.BACHELOR, field="computer science"
            ),
            AdapterResult(),
        )
        return _report()

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("groningen", _output(tmp_path), 60, 120, strict_expert_budget=True)
    assert len(queries) == (1 if failure_status is not None else 6)
    assert ExaMcpSearchProvider.search is original
    observation = Observation.model_validate_json(_output(tmp_path).read_text())
    assert observation.telemetry.search_calls == len(queries)
    budget_text = _output(tmp_path).with_suffix(".budget.json").read_text()
    budget = json.loads(budget_text)
    assert budget["blocked_search_queries"] >= 1
    assert budget["stop_reason"] == (
        f"http_{failure_status}" if failure_status is not None else "search_budget_exhausted"
    )
    assert "vendor-secret-key" not in budget_text + _output(tmp_path).read_text()
    if failure_status is not None:
        assert budget["provider_failure"]["http_status"] == failure_status


@pytest.mark.asyncio
async def test_strict_active_deadline_cancels_pipeline_and_keeps_budget_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancelled = False

    async def run(*args: Any) -> dict[str, Any]:
        nonlocal cancelled
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            raise
        raise AssertionError("must time out")

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("groningen", _output(tmp_path), 60, 0.15, strict_expert_budget=True)
    assert cancelled
    observation = Observation.model_validate_json(_output(tmp_path).read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    budget = json.loads(_output(tmp_path).with_suffix(".budget.json").read_text())
    assert budget["max_active_seconds"] == 0.15
    assert budget["fetcher_calls"] == budget["search_queries"] == 0
    assert "canary setup" in budget["active_time_basis"]


@pytest.mark.parametrize("failure_status", [None, 402, 429])
def test_strict_parent_forwards_budget_and_stops_cohort_after_recorded_account_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_status: int | None,
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--strict-expert-budget"]
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: "app-and-harness-test-sha"
    )
    started: list[str] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "--strict-expert-budget" in command
        assert command[command.index("--max-pages") + 1] == "60"
        assert command[command.index("--seconds-per-case") + 1] == "120"
        assert kwargs["timeout"] == 135
        assert kwargs["env"]["UNIMATCH_ENABLE_BROWSER_TIER"] == "false"
        assert kwargs["env"]["UNIMATCH_RESPECT_ROBOTS"] == "true"
        case_id = command[command.index("--case") + 1]
        started.append(case_id)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id=case_id).model_dump_json())
        output.with_suffix(".budget.json").write_text(
            json.dumps(
                {
                    "stop_reason": f"http_{failure_status}" if failure_status is not None else None,
                    "provider_failure": (
                        {"http_status": failure_status} if failure_status is not None else None
                    ),
                    "fetcher_calls": 3,
                    "search_queries": 1,
                }
            )
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert len(started) == (1 if failure_status is not None else len(live.COHORT))
    assert capture.config["strict_expert_budget"] is True
    assert capture.config["max_search_queries_per_case"] == 6
    assert capture.config["child_active_seconds"] == 120
    assert capture.config["parent_process_timeout_seconds"] == 135
    assert capture.config["cold_fetcher_reads"] is True
    assert capture.config["batch_remaining_case_ids"] == (
        list(live.COHORT)[1:] if failure_status is not None else []
    )
    assert capture.config["batch_stop_reason"] == (
        f"http_{failure_status}" if failure_status is not None else None
    )


def test_strict_child_receives_full_active_budget_and_resets_cached_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def capture(*args: Any, **kwargs: Any) -> None:
        called.append((args, kwargs))

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--strict-expert-budget",
        ],
    )
    live.main()
    assert called[0][0][2:] == (60, 120)
    assert called[0][1] == {"strict_expert_budget": True}


@pytest.mark.parametrize(
    "extra",
    [
        ["--max-pages", "61"],
        ["--seconds-per-case", "121"],
        ["--search-provider", "none"],
    ],
)
def test_strict_cli_rejects_expanded_or_unconfigured_budget_before_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra: list[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--strict-expert-budget", *extra]
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not launch child")
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("must fail before git")
    )
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("partial", [False, True])
def test_strict_parent_hard_timeout_keeps_active_and_process_clocks_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial: bool,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["live", "--live", "--case", "groningen", "--out", str(tmp_path), "--strict-expert-budget"],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "test-sha")

    def child(command: list[str], **kwargs: Any) -> None:
        if partial:
            output = Path(command[command.index("--out") + 1])
            observation = Observation(case_id="groningen")
            observation.telemetry.latency_seconds = 12.0
            output.write_text(observation.model_dump_json())
            output.with_suffix(".budget.json").write_text(json.dumps({"elapsed_ms": 12_000}))
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    observation = capture.observations[0]
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert observation.telemetry.latency_seconds == (12.0 if partial else None)
    status = capture.config["case_budgets"]
    assert isinstance(status, dict) and isinstance(status["groningen"], dict)
    assert status["groningen"]["process_error"] == observation.error
    assert status["groningen"]["active_checkpoint_available"] is partial


def test_strict_implicit_exa_configuration_requires_key_before_starting_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa")
    monkeypatch.setenv("UNIMATCH_EXA_API_KEY", "")
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--strict-expert-budget"]
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not launch child")
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("must fail before git")
    )
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert "needs UNIMATCH_EXA_API_KEY" in capsys.readouterr().err
