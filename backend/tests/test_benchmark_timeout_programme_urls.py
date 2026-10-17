"""A case that runs out of wall clock still reports the programme pages it confirmed.

QB-1 analysis (2026-10-17): Groningen's walker confirmed the programme page at
t=35 s and the page produced six claims, but the case was killed in the award
stage and the harness's ``TimeoutError`` branch never filled ``programme_urls``,
so the scorecard counted a programme-page loss that did not happen.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters.fetching import FetchResult
from app.config import get_settings
from app.domain.enums import FetchOutcome
from evaluation.research import live
from evaluation.research.schema import Evidence, Observation, Prediction, Scope
from scripts import canary_discovery as canary

PROGRAMME = "https://www.rug.nl/bachelors/computing-science"
TWIN = "https://www.rug.nl/bachelors/computing-science?lang=en"


@pytest.fixture(autouse=True)
def _offline_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _Fetcher:
    tier_counts = {"browser": 0}  # noqa: RUF012 - read-only test double

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        return FetchResult(url=url, outcome=FetchOutcome.CACHED, from_cache=True)


class _Session:
    def query(self, model: Any) -> Any:
        class _Rows(list[Any]):
            def filter(self, *args: Any) -> _Rows:
                return self

        return _Rows()


def _prediction(key: str, value: Any, url: str | None) -> Prediction:
    evidence = (
        Evidence(
            url=url,  # type: ignore[arg-type]
            excerpt="Computing Science (BSc)",
            scope=Scope(university="University of Groningen"),
            accessed_on=date(2026, 10, 17),
            source_type="official",
        )
        if url
        else None
    )
    return Prediction(key=key, value=value, evidence=evidence)


def _arrange(monkeypatch: pytest.MonkeyPatch, programmes: list[str]) -> None:
    """A run whose decision stage confirmed ``programmes`` and then never returns."""
    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: _Fetcher())
    monkeypatch.setattr(canary, "page_outcomes", lambda run: [])

    async def slow_decide(self: Any) -> None:
        await self._make_fetcher().get(PROGRAMME)
        self._candidates = [
            SimpleNamespace(
                name="University of Groningen",
                programs=[SimpleNamespace(url=url) for url in programmes],
            )
        ]
        await asyncio.sleep(5)

    monkeypatch.setattr(canary.CanaryRunner, "run_to_decision", slow_decide)

    async def run(*args: Any) -> dict[str, Any]:
        runner = object.__new__(canary.CanaryRunner)
        runner.session = _Session()  # type: ignore[assignment]
        runner.run = SimpleNamespace(id="run")  # type: ignore[assignment]
        runner._candidates = []
        await runner.run_to_decision()
        raise AssertionError("the decision stage never returns in this test")

    monkeypatch.setattr(canary, "run_canary", run)


@pytest.mark.asyncio
async def test_a_wall_clock_kill_keeps_the_confirmed_programme_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arrange(monkeypatch, [PROGRAMME, TWIN])
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 5, 0.2)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert [str(url) for url in observation.programme_urls] == [PROGRAMME, TWIN]
    # Everything else stays as the timeout path always left it.
    assert observation.predictions == []
    assert not output.with_suffix(".raw.json").exists()


@pytest.mark.asyncio
async def test_a_kill_before_any_programme_was_confirmed_reports_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arrange(monkeypatch, [])
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 5, 0.2)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert observation.programme_urls == []


def test_the_runner_rows_come_first() -> None:
    runner = SimpleNamespace(_candidates=[SimpleNamespace(programs=[SimpleNamespace(url=TWIN)])])
    predictions = [_prediction("programme.exists", True, PROGRAMME)]
    assert live.timeout_programme_urls([runner], predictions) == [TWIN]


def test_without_a_runner_the_programme_exists_evidence_stands_in() -> None:
    predictions = [
        _prediction("programme.exists", True, PROGRAMME),
        _prediction("programme.exists", True, PROGRAMME),
        _prediction("programme.language", "English", "https://www.rug.nl/other"),
        _prediction("programme.exists", False, "https://www.rug.nl/closed"),
        _prediction("programme.exists", True, None),
    ]
    assert live.timeout_programme_urls([], predictions) == [PROGRAMME]
    empty_runner = SimpleNamespace(_candidates=[])
    assert live.timeout_programme_urls([empty_runner], predictions) == [PROGRAMME]
