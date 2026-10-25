"""The confirm checkpoint persists what discovery had confirmed, and its trace.

Structural analysis 2026-10-18, section 4.2: UBC read and confirmed its
programme page, was killed by the wall clock in search, and reported
``programme_urls == []`` with no trace at all. A kill that skips the
``TimeoutError`` branch (the parent's SIGKILL) left nothing either.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, PageCategory
from app.config import get_settings
from evaluation.research import live, scorecard
from evaluation.research.schema import Capture, Observation
from scripts import canary_discovery as canary

PROGRAMME = "https://you.ubc.ca/programs/computer-science/"
WALKED = "https://you.ubc.ca/programs/computer-science-bsc/"


@pytest.fixture(autouse=True)
def _offline_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _arrange(
    monkeypatch: pytest.MonkeyPatch, output: Path, *, finish: bool, seen: dict[str, Any]
) -> None:
    """Discovery confirms one page, the walker adds one, then the run stalls or finishes."""

    async def confirm(adapter: Any, selected: Any, ranked: Any, trace: Any, profile: Any) -> None:
        selected[PageCategory.PROGRAM_PAGE] = [PROGRAMME]

    async def walk(adapter: Any, entry: Any, selected: Any, trace: Any, profile: Any) -> None:
        selected[PageCategory.PROGRAM_PAGE].append(WALKED)

    monkeypatch.setattr(LiveDiscoveryAdapter, "_confirm_programs", confirm)
    monkeypatch.setattr(LiveDiscoveryAdapter, "_walk_catalogs", walk)

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        trace = DiscoveryTrace(institution="University of British Columbia", domain="ubc.ca")
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        selected[PageCategory.PROGRAM_PAGE] = ["https://you.ubc.ca/open-day/"]
        ranked: dict[str, list[tuple[int, str]]] = {PageCategory.PROGRAM_PAGE: []}
        await LiveDiscoveryAdapter._confirm_programs(None, selected, ranked, trace, None)  # type: ignore[arg-type]
        # What a SIGKILL right here would leave on disk.
        seen["after_confirm"] = Observation.model_validate_json(output.read_text())
        seen["trace_after_confirm"] = json.loads(output.with_suffix(".trace.json").read_text())
        await LiveDiscoveryAdapter._walk_catalogs(None, {}, selected, trace, None)  # type: ignore[arg-type]
        if not finish:
            await asyncio.sleep(5)
        return {"institutions": [{"programs": [PROGRAMME, WALKED]}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)


@pytest.mark.asyncio
async def test_a_kill_after_the_confirm_checkpoint_keeps_its_pages_and_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    seen: dict[str, Any] = {}
    _arrange(monkeypatch, output, finish=False, seen=seen)
    await live.capture_one("ubc", output, 5, 0.3)

    # Already on disk at the confirm checkpoint, before any kill.
    assert [str(u) for u in seen["after_confirm"].programme_urls] == [PROGRAMME]
    assert seen["after_confirm"].error == "CAPTURE_IN_PROGRESS"
    assert seen["trace_after_confirm"]["checkpoint"] == "confirm"
    assert seen["trace_after_confirm"]["programme_urls"] == [PROGRAMME]

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert [str(u) for u in observation.programme_urls] == [PROGRAMME, WALKED]
    partial = json.loads(output.with_suffix(".trace.json").read_text())
    assert partial["partial"] is True
    assert partial["checkpoint"] == "timeout"
    assert partial["programme_urls"] == [PROGRAMME, WALKED]
    assert partial["discovery_trace"]["domain"] == "ubc.ca"
    assert not output.with_suffix(".raw.json").exists()


@pytest.mark.asyncio
async def test_a_completed_run_keeps_only_the_raw_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    _arrange(monkeypatch, output, finish=True, seen={})
    await live.capture_one("ubc", output, 5, 5)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error is None
    assert [str(u) for u in observation.programme_urls] == [PROGRAMME, WALKED]
    assert output.with_suffix(".raw.json").exists()
    assert not output.with_suffix(".trace.json").exists()


def test_the_checkpoint_pages_stand_in_only_when_the_runner_has_none() -> None:
    assert live.timeout_programme_urls([], [], [PROGRAMME]) == [PROGRAMME]
    assert live.timeout_programme_urls([], [], []) == []


# --- HC-1: a case the parent's kill ends keeps the claims it had filed --------
#
# LOOP_REPORT 2026-10-20 10:45: a case whose own stop does not finish before the
# parent's kill at 120 s leaves the last checkpoint on disk. Simulated without a
# real process: the fake run files two claims through the runner's own
# ``_store_claims`` and then raises ``_ParentKill``, which no ``except`` in the
# harness catches, so nothing after that point writes the observation - what a
# SIGKILL leaves.

PAGE = "https://example.edu/admissions/english-language/"


class _ParentKill(BaseException):
    """The parent's kill: no harness code runs after it."""


def _ielts_claims() -> list[Any]:
    from app.domain.enums import ClaimType
    from app.schemas.claim import Claim

    read_at = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
    return [
        Claim(
            claim_type=ClaimType.IELTS_MIN_OVERALL,
            normalized_value=6.5,
            original_text_excerpt="IELTS Academic: overall band 6.5",
            source_url=PAGE,
            official_domain=True,
            accessed_at=read_at,
        ),
        Claim(
            claim_type=ClaimType.IELTS_MIN_SUBSCORE,
            normalized_value=6.0,
            original_text_excerpt="with no band below 6.0",
            source_url=PAGE,
            official_domain=True,
            accessed_at=read_at,
        ),
    ]


def _arrange_filed_then_killed(
    monkeypatch: pytest.MonkeyPatch, output: Path, seen: dict[str, Any], *, stall: bool = False
) -> None:
    """Discovery confirms a page, the evidence stage files two claims, the parent kills.

    ``stall``: the run stalls instead, so the child's own stop ends it.
    """

    async def confirm(adapter: Any, selected: Any, ranked: Any, trace: Any, profile: Any) -> None:
        selected[PageCategory.PROGRAM_PAGE] = [PROGRAMME]

    monkeypatch.setattr(LiveDiscoveryAdapter, "_confirm_programs", confirm)

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        trace = DiscoveryTrace(institution="University of British Columbia", domain="ubc.ca")
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        ranked: dict[str, list[tuple[int, str]]] = {PageCategory.PROGRAM_PAGE: []}
        await LiveDiscoveryAdapter._confirm_programs(None, selected, ranked, trace, None)  # type: ignore[arg-type]
        # The harness's own runner class (patched in by capture_one), built
        # without a database: only what ``_store_claims`` and the claim
        # mapping read.
        runner = object.__new__(canary.CanaryRunner)
        runner.run = SimpleNamespace(id="run-hc1")  # type: ignore[assignment]
        runner.session = SimpleNamespace(add=lambda row: None)  # type: ignore[assignment]
        runner._candidates = []  # type: ignore[assignment]
        runner._store_claims("result-hc1", _ielts_claims())
        seen["at_kill"] = Observation.model_validate_json(output.read_text())
        trace_file = output.with_suffix(".trace.json")
        seen["trace_at_kill"] = json.loads(trace_file.read_text()) if trace_file.exists() else {}
        if stall:
            await asyncio.sleep(5)
        raise _ParentKill

    monkeypatch.setattr(canary, "run_canary", run)


@pytest.mark.asyncio
async def test_a_parent_kill_after_two_claims_were_filed_keeps_them_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    seen: dict[str, Any] = {}
    _arrange_filed_then_killed(monkeypatch, output, seen)
    with pytest.raises(_ParentKill):
        await live.capture_one("ubc", output, 5, 100)

    # Before HC-1 the last checkpoint was discovery's confirm checkpoint and
    # held no claim. Now filing the claims is itself a checkpoint.
    on_disk = Observation.model_validate_json(output.read_text())
    assert on_disk == seen["at_kill"]
    assert on_disk.error == "CAPTURE_IN_PROGRESS"
    assert [p.key for p in on_disk.predictions] == ["ielts.overall", "ielts.subscores"]
    assert on_disk.predictions[0].value == 6.5
    assert on_disk.predictions[0].evidence is not None
    assert str(on_disk.predictions[0].evidence.url) == PAGE
    assert [str(u) for u in on_disk.programme_urls] == [PROGRAMME]
    partial = seen["trace_at_kill"]
    assert partial["checkpoint"] == "claims"
    assert [c["claim_type"] for c in partial["claims"]] == [
        "ielts_min_overall",
        "ielts_min_subscore",
    ]


@pytest.mark.asyncio
async def test_the_child_s_own_stop_keeps_the_filed_claims_when_the_runner_never_read_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    seen: dict[str, Any] = {}
    _arrange_filed_then_killed(monkeypatch, output, seen, stall=True)
    await live.capture_one("ubc", output, 5, 0.3)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert [p.key for p in observation.predictions] == ["ielts.overall", "ielts.subscores"]
    assert observation.telemetry.stop_reason is None


def test_the_parent_finalises_a_killed_case_with_the_claims_it_had_filed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ubc", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    seen: dict[str, Any] = {}

    def child(command: list[str], **kwargs: Any) -> None:
        output = Path(command[command.index("--out") + 1])
        _arrange_filed_then_killed(monkeypatch, output, seen)
        with pytest.raises(_ParentKill):
            asyncio.run(live.capture_one("ubc", output, 5, 100))
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    observation = capture.observations[0]
    assert seen["at_kill"].error == "CAPTURE_IN_PROGRESS"
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert observation.telemetry.stop_reason == "parent_kill"
    assert [p.key for p in observation.predictions] == ["ielts.overall", "ielts.subscores"]
    # The parent's clock, not the last checkpoint's.
    assert observation.telemetry.latency_seconds is not None
    assert observation.telemetry.latency_seconds >= seen["at_kill"].telemetry.latency_seconds
    # The case is still over the latency budget, and reads as killed by the clock.
    row = scorecard.cost(capture)["ubc"]
    assert row["killed_by_clock"] == 1
    assert "capture_in_progress" not in row


def test_the_case_file_beside_the_capture_says_what_killed_the_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # HC-1b, runs hc1-dev3 / rp-hc1-dev3: capture.json carried the parent's
    # finalisation, but unsw.json beside it stayed the child's last checkpoint
    # (CAPTURE_IN_PROGRESS, no stop_reason, 115-119 s), and that file was read.
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ubc", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    seen: dict[str, Any] = {}

    def child(command: list[str], **kwargs: Any) -> None:
        output = Path(command[command.index("--out") + 1])
        _arrange_filed_then_killed(monkeypatch, output, seen)
        with pytest.raises(_ParentKill):
            asyncio.run(live.capture_one("ubc", output, 5, 100))
        on_disk = Observation.model_validate_json(output.read_text(encoding="utf-8"))
        assert on_disk.error == "CAPTURE_IN_PROGRESS"
        assert on_disk.telemetry.stop_reason is None
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture_path = next(tmp_path.rglob("capture.json"))
    capture = Capture.model_validate_json(capture_path.read_text())
    case_file = Observation.model_validate_json((capture_path.parent / "ubc.json").read_text())
    assert case_file.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert case_file.telemetry.stop_reason == "parent_kill"
    assert case_file == capture.observations[0]
    assert [p.key for p in case_file.predictions] == ["ielts.overall", "ielts.subscores"]
    assert not list(capture_path.parent.glob("*.pending"))


def test_a_case_the_child_finished_keeps_its_own_file_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ubc", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    written: dict[str, bytes] = {}

    def child(command: list[str], **kwargs: Any) -> SimpleNamespace:
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="ubc").model_dump_json(indent=2))
        written["bytes"] = output.read_bytes()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture_path = next(tmp_path.rglob("capture.json"))
    assert (capture_path.parent / "ubc.json").read_bytes() == written["bytes"]


def test_a_child_that_fails_on_its_own_is_not_finalised_as_a_parent_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ubc", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")

    def child(command: list[str], **kwargs: Any) -> SimpleNamespace:
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="ubc", error="CAPTURE_IN_PROGRESS").model_dump_json())
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    observation = capture.observations[0]
    assert observation.error == "PROCESS_EXIT_1"
    assert observation.telemetry.stop_reason is None
    case_file = next(tmp_path.rglob("ubc.json")).read_text()
    assert Observation.model_validate_json(case_file).error == "PROCESS_EXIT_1"
    assert "stop_reason" not in capture.model_dump_json()
