"""HP-1: a hop entry root has a deadline, so a dead host cannot eat the run.

Charles/Exa spent 64 of its 115 s opening two roots (``explorer.cuni.cz/``,
``nomos.is.cuni.cz/``) that refused connections: each cost the fetcher's full
timeout and its retries. A root is a supplement to search; under HP-1 one past
its deadline is counted unreachable and the hop moves on. Offline: the slow host
is a coroutine that sleeps.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import pytest

from app.adapters.search import retrieval
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel

NOW = datetime(2026, 10, 17, tzinfo=UTC)
_DEAD_HOST = "explorer.nu.edu.kz"
_MENU = '<a href="/content?menu=188">Computer Science programme</a>'


def _intent() -> DiscoveryIntent:
    return DiscoveryIntent(
        institution="Nazarbayev University",
        domain="nu.edu.kz",
        degree=DegreeLevel.BACHELOR,
        field="computer science",
    )


def _provider(intent: DiscoveryIntent) -> FakeSearchProvider:
    rows = [
        (f"https://{_DEAD_HOST}/programmes/computer-science", "Computer Science", ""),
        ("https://nu.edu.kz/programmes/computer-science", "Computer Science", ""),
    ]
    return FakeSearchProvider({q.text: rows for q in queries_for(intent, budget=99)}, now=NOW)


def _fetcher(slow_seconds: float, opened: list[str]):
    async def fetch(url: str) -> str:
        opened.append(url)
        if _DEAD_HOST in url:
            await asyncio.sleep(slow_seconds)
            return _MENU
        return _MENU

    return fetch


def test_the_rule_is_off_by_default_with_an_eight_second_deadline() -> None:
    assert retrieval.HOP_ROOT_DEADLINE is False
    assert retrieval.HOP_ROOT_DEADLINE_SECONDS == 8.0


async def test_a_slow_root_is_cut_off_and_counted_unreachable(monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "HOP_ROOT_DEADLINE", True)
    monkeypatch.setattr(retrieval, "HOP_ROOT_DEADLINE_SECONDS", 0.05)
    intent = _intent()
    opened: list[str] = []

    started = time.perf_counter()
    report = await discover_candidates(_provider(intent), intent, fetch=_fetcher(30.0, opened))
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"the dead root held the hop for {elapsed:.2f} s"
    assert f"https://{_DEAD_HOST}/" in opened
    assert f"https://{_DEAD_HOST}/" not in report.hop_entry_points
    assert report.hop_entry_points_unreachable == 1
    # The live root is still opened and its navigation still read.
    assert "https://nu.edu.kz/" in report.hop_entry_points
    assert report.hop_candidates >= 1


async def test_without_the_rule_a_slow_root_is_waited_for(monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "HOP_ROOT_DEADLINE", False)
    monkeypatch.setattr(retrieval, "HOP_ROOT_DEADLINE_SECONDS", 0.05)
    intent = _intent()
    opened: list[str] = []

    report = await discover_candidates(_provider(intent), intent, fetch=_fetcher(0.2, opened))

    assert f"https://{_DEAD_HOST}/" in report.hop_entry_points
    assert report.hop_entry_points_unreachable == 0


@pytest.mark.parametrize("flag", [True, False])
async def test_a_fast_root_is_untouched_by_the_rule(monkeypatch, flag: bool) -> None:
    monkeypatch.setattr(retrieval, "HOP_ROOT_DEADLINE", flag)
    intent = _intent()
    opened: list[str] = []

    report = await discover_candidates(_provider(intent), intent, fetch=_fetcher(0.0, opened))

    assert set(report.hop_entry_points) == {f"https://{_DEAD_HOST}/", "https://nu.edu.kz/"}
    assert report.hop_entry_points_unreachable == 0
