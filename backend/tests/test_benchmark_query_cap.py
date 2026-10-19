"""Free-search ticket 02: the run's hard cap on provider queries.

Offline only: every provider here is patched, no request leaves the process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.search.base import SearchResponse, SearchUnavailable
from app.config import get_settings
from evaluation.research import live, scorecard, search_preflight
from evaluation.research.schema import Capture, Observation, Telemetry
from evaluation.research.search_cap import (
    SearchCapError,
    SearchQueryLedger,
    needs_cap,
    planned_queries,
)
from scripts import canary_discovery as canary
from tests.test_expert_workflow import shell_step, substitute_python

SECRET = "synthetic-key-never-printed"


@pytest.fixture(autouse=True)
def _public_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- the ledger ----------------------------------------------------------------


def test_only_providers_that_send_nothing_are_uncapped() -> None:
    assert not any(needs_cap(p) for p in ("none", "fake", "recorded"))
    assert all(needs_cap(p) for p in ("exa", "exa_mcp", "tavily", "brave", "serper", "new"))
    assert planned_queries(10) == 60
    assert planned_queries(9, columns=4, extra=1) == 217


def test_the_ledger_refuses_the_query_after_the_cap_and_is_shared(tmp_path: Path) -> None:
    path = tmp_path / "search_ledger.json"
    first = SearchQueryLedger.open(path, 3)
    second = SearchQueryLedger.open(path, 3)  # another capture of the same run
    assert [first.reserve(), second.reserve(), first.reserve()] == [True, True, True]
    assert second.reserve() is False
    assert first.state() == {"max_search_queries": 3, "used": 3, "refused": 1}
    assert first.exhausted() and second.remaining() == 0


def test_a_later_capture_cannot_raise_the_cap(tmp_path: Path) -> None:
    path = tmp_path / "search_ledger.json"
    SearchQueryLedger.open(path, 6)
    with pytest.raises(SearchCapError, match="cap of 6"):
        SearchQueryLedger.open(path, 600)
    with pytest.raises(SearchCapError, match="positive"):
        SearchQueryLedger.open(tmp_path / "other.json", 0)
    path.write_text("{not json")
    with pytest.raises(SearchCapError, match="unreadable"):
        SearchQueryLedger.open(path, 6)


# --- the counted search wrapper ---------------------------------------------------


def _patched_provider(monkeypatch: pytest.MonkeyPatch, sent: list[str]) -> Any:
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider

    async def search(self: Any, *, query: str, **kwargs: Any) -> SearchResponse:
        sent.append(query)
        return SearchResponse(query=query, provider="exa_mcp", retrieved_at=datetime.now(UTC))

    monkeypatch.setattr(ExaMcpSearchProvider, "search", search)
    return ExaMcpSearchProvider()


@pytest.mark.asyncio
@pytest.mark.parametrize("strict", [False, True])
async def test_the_cap_trips_at_n_plus_one_with_no_request_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, strict: bool
) -> None:
    sent: list[str] = []
    provider = _patched_provider(monkeypatch, sent)
    ledger = SearchQueryLedger.open(tmp_path / "search_ledger.json", 4)
    refused: list[str] = []

    async def run(*args: Any) -> dict[str, Any]:
        for index in range(6):
            try:
                await provider.search(query=f"q{index}")
            except SearchUnavailable as exc:
                refused.append(str(exc))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen",
        output,
        60,
        120,
        strict_expert_budget=strict,
        search_ledger=ledger,
    )
    assert sent == ["q0", "q1", "q2", "q3"]
    assert len(refused) == 2 and all("cap" in message for message in refused)
    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.search_calls == 4
    assert observation.telemetry.search_cap_refusals == 2
    assert ledger.state() == {"max_search_queries": 4, "used": 4, "refused": 2}
    if strict:
        budget = json.loads(output.with_suffix(".budget.json").read_text())
        assert budget["search_queries"] == 4
        assert budget["blocked_search_queries"] == 2
        assert budget["stop_reason"] == "search_budget_exhausted"


@pytest.mark.asyncio
async def test_without_a_ledger_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []
    provider = _patched_provider(monkeypatch, sent)

    async def run(*args: Any) -> dict[str, Any]:
        for index in range(3):
            await provider.search(query=f"q{index}")
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 60, 120)
    assert len(sent) == 3
    assert "search_cap_refusals" not in output.read_text()


# --- the parent: refuse to start, stop cleanly ------------------------------------


def _forbid_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not launch child")
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("must fail before git")
    )


@pytest.mark.parametrize(
    ("provider", "key"),
    [
        ("exa_mcp", None),
        ("serper", "UNIMATCH_SERPER_API_KEY"),
        ("tavily", "UNIMATCH_TAVILY_API_KEY"),
        ("exa", "UNIMATCH_EXA_API_KEY"),
    ],
)
def test_a_provider_run_without_a_cap_never_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
    key: str | None,
) -> None:
    if key:
        monkeypatch.setenv(key, SECRET)
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--search-provider", provider]
    )
    _forbid_start(monkeypatch)
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "--max-search-queries" in captured.err
    assert SECRET not in captured.out + captured.err
    assert not list(tmp_path.iterdir())


def test_a_plan_over_the_cap_never_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--max-search-queries", "59"]
    )
    _forbid_start(monkeypatch)
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert "plans 60 provider queries" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_a_capture_that_finds_the_shared_ledger_spent_never_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger = SearchQueryLedger.open(tmp_path / "search_ledger.json", 12)
    for _ in range(7):
        ledger.reserve()
    out = tmp_path / "capture"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(out),
            "--max-search-queries",
            "12",
            "--search-ledger",
            str(ledger.path),
        ],
    )
    _forbid_start(monkeypatch)
    with pytest.raises(SystemExit):
        live.main()
    assert "leaves 5 of 12" in capsys.readouterr().err
    assert not out.exists()


def test_uncapped_providers_still_start_without_a_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
            "none",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "sha")

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "--max-search-queries" not in command
        Path(command[command.index("--out") + 1]).write_text(
            Observation(case_id="groningen").model_dump_json()
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert "search_query_cap" not in capture.config


def test_the_run_stops_cleanly_when_the_cap_is_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--out", str(tmp_path), "--max-search-queries", "60"]
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "sha")
    started: list[str] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[command.index("--max-search-queries") + 1] == "60"
        ledger = SearchQueryLedger.open(Path(command[command.index("--search-ledger") + 1]), 60)
        case_id = command[command.index("--case") + 1]
        started.append(case_id)
        # A child that asks for 40 queries: the ledger grants what is left.
        granted = sum(ledger.reserve() for _ in range(40))
        observation = Observation(case_id=case_id, telemetry=Telemetry(search_calls=granted))
        Path(command[command.index("--out") + 1]).write_text(observation.model_dump_json())
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert started == list(live.COHORT)[:2]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    cap = capture.config["search_query_cap"]
    assert isinstance(cap, dict)
    assert (cap["max_search_queries"], cap["used"], cap["refused"]) == (60, 60, 20)
    assert cap["stop_reason"] == "search_budget_exhausted"
    assert cap["remaining_case_ids"] == list(live.COHORT)[2:]
    assert "search query cap is reached" in capsys.readouterr().out


# --- the pre-flight and the scorecard ------------------------------------------------


class _Provider:
    name = "serper"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, *, query: str, domains: Any = (), max_results: int = 10) -> Any:
        self.calls += 1
        return type("R", (), {"results": ()})()


def test_the_preflight_is_charged_and_refused_on_a_spent_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _Provider()
    monkeypatch.setattr(search_preflight, "get_search_provider", lambda: provider)
    path = tmp_path / "search_ledger.json"
    arguments = ["--max-search-queries", "1", "--search-ledger", str(path)]
    assert search_preflight.main(arguments) == 0
    assert provider.calls == 1
    assert search_preflight.main(arguments) == 1
    assert provider.calls == 1  # the second query was never sent
    assert "cap is already spent" in capsys.readouterr().err
    assert SearchQueryLedger.open(path, 1).state()["refused"] == 1


def test_a_capped_repetition_is_not_a_valid_measurement() -> None:
    def observation(refusals: int | None) -> Observation:
        return Observation(
            case_id="uni", telemetry=Telemetry(search_calls=6, search_cap_refusals=refusals)
        )

    def capture(refusals: int | None) -> Capture:
        return Capture(
            pipeline_sha="sha",
            captured_at="now",
            mode="live",
            config={},
            observations=[observation(refusals)],
        )

    assert scorecard.search_health(capture(None), {}, {})["healthy"] is True
    health = scorecard.search_health(capture(2), {}, {})
    assert (health["healthy"], health["cap_refused"]) == (False, 2)
    banner = scorecard.search_warning([("on", 0, {"search_health": health})])
    assert "SEARCH QUERY CAP WAS REACHED" in banner[0]


# --- the workflow guard step ---------------------------------------------------------


def _guard(
    tmp_path: Path, provider: str, cap: str, mode: str, cases: str
) -> tuple[subprocess.CompletedProcess[str], str, str]:
    substitute_python(tmp_path)
    github_env = tmp_path / "github.env"
    github_env.write_text("")
    result = subprocess.run(
        ["bash", "-c", shell_step("Search query cap (refuse a provider run without one)")],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "GITHUB_ENV": str(github_env),
            "UNIMATCH_SEARCH_PROVIDER": provider,
            "REQUESTED_CAP": cap,
            "REQUESTED_MODE": mode,
            "REQUESTED_CASE": cases,
            "UNIMATCH_SERPER_API_KEY": SECRET,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    config = tmp_path / "out" / "config.txt"
    return result, github_env.read_text(), config.read_text() if config.exists() else ""


@pytest.mark.parametrize("cap", ["", "0", "ten", "5 --search-provider serper"])
def test_the_workflow_refuses_a_provider_run_without_a_valid_cap(tmp_path: Path, cap: str) -> None:
    result, github_env, _ = _guard(tmp_path, "serper", cap, "expert_paired", "ethz")
    assert result.returncode == 1
    assert "needs the max_search_queries input" in result.stdout
    assert "--max-search-queries" not in github_env
    assert SECRET not in result.stdout + result.stderr


@pytest.mark.parametrize(
    ("provider", "mode", "cases", "planned"),
    [
        ("serper", "expert_paired", "ethz uppsala", 6 * 2 * 4 + 1),
        ("exa_mcp", "expert_paired", "ethz uppsala", 6 * 2 * 4),
        ("exa", "benchmark", "", 6 * len(live.COHORT)),
        ("tavily", "expert_baseline", "groningen", 6),
    ],
)
def test_the_workflow_cap_must_cover_the_plan(
    tmp_path: Path, provider: str, mode: str, cases: str, planned: int
) -> None:
    short, github_env, _ = _guard(tmp_path / "short", provider, str(planned - 1), mode, cases)
    assert short.returncode == 1
    assert f"plans {planned} provider queries" in short.stdout
    assert "--max-search-queries" not in github_env
    enough, github_env, config = _guard(tmp_path / "enough", provider, str(planned), mode, cases)
    assert enough.returncode == 0, enough.stdout + enough.stderr
    assert f"SEARCH_CAP_ARGS=--max-search-queries {planned} --search-ledger " in github_env
    assert github_env.rstrip().endswith("out/search_ledger.json")
    assert f"max_search_queries={planned} planned={planned} provider={provider}" in config


@pytest.mark.parametrize("provider", ["recorded", "none"])
def test_the_workflow_needs_no_cap_where_nothing_is_sent(tmp_path: Path, provider: str) -> None:
    result, github_env, config = _guard(tmp_path, provider, "", "expert_paired", "ethz")
    assert result.returncode == 0
    assert github_env == "SEARCH_CAP_ARGS=\n"
    assert f"max_search_queries=uncapped ({provider})" in config
