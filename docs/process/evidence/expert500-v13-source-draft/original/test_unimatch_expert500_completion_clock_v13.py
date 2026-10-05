"""Completion-clock regression against a distinct parent candidate; no real I/O."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PARENT = Path("/tmp/unimatch-expert500-journal-pilot-v13.py")
ORIGINAL_PARENT = Path("/tmp/unimatch-expert500-journal-pilot-v12.py")
ORIGINAL_FIXTURE = Path("/tmp/test_unimatch_expert500_journal_pilot_v12.py")
PARENT_V12_SHA = "1922e117436afdc001bef7cbf867e8b91db4062fd0b98cfce044c3b980a74b72"
FIXTURE_V12_SHA = "fcbca530b952625d4e8fbe752fbf45692ee7c380f3f6c26fd83c9ad9e8a483a9"


def load_frozen_fixture() -> Any:
    assert hashlib.sha256(ORIGINAL_PARENT.read_bytes()).hexdigest() == PARENT_V12_SHA
    assert hashlib.sha256(ORIGINAL_FIXTURE.read_bytes()).hexdigest() == FIXTURE_V12_SHA
    name = "expert500_completion_clock_v13_frozen_fixture"
    spec = importlib.util.spec_from_file_location(name, ORIGINAL_FIXTURE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # Only the local fixture's source pointer changes. The frozen file stays exact.
    module.PILOT = PARENT
    return module


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    fixture = load_frozen_fixture()
    value = fixture.pilot.__wrapped__(tmp_path, monkeypatch)
    return value, fixture


class DelayedDigest:
    def __init__(self, value: Any, callback: Callable[[], None]) -> None:
        self.value = value
        self.callback = callback

    def hexdigest(self) -> str:
        self.callback()
        return str(self.value.hexdigest())


def delay_action_file_hash(
    pilot: Any,
    fixture: Any,
    *,
    delay: timedelta,
    after_hash: Callable[[], None] | None = None,
) -> list[datetime]:
    original_sha256 = hashlib.sha256
    target = pilot.folder / "recorded-actions.json"
    entered_at: list[datetime] = []

    def sha256(value: bytes) -> Any:
        current = original_sha256(value)
        if not target.exists() or value != target.read_bytes():
            return current

        def finish() -> None:
            entered_at.append(fixture.FakeDatetime.current)
            fixture.FakeDatetime.current += delay
            if after_hash is not None:
                after_hash()

        return DelayedDigest(current, finish)

    # Patch the parent namespace only; library/raw/citation hashlib stays genuine.
    pilot.runtime["hashlib"] = SimpleNamespace(sha256=sha256)
    return entered_at


def queue_submission(pilot: Any, fixture: Any, *, commit_elapsed: int = 500) -> None:
    fixture.bootstrap(pilot)
    fixture.checkpoint(pilot)
    fixture.commit(pilot, elapsed=commit_elapsed)


def assert_one_completion_instant(result: dict[str, Any]) -> None:
    started = datetime.fromisoformat(result["wall_started_at"])
    finished = datetime.fromisoformat(result["finished_at"])
    elapsed = (finished - started).total_seconds()
    assert result["wall_elapsed_ms"] == math.ceil(elapsed * 1000)
    assert result["real_elapsed_seconds"] == elapsed


@pytest.mark.parametrize("hash_delay_us", [0, 1, 1000, 5000, 200_000])
def test_action_file_hash_finishes_before_completion_clock(
    harness: tuple[Any, Any], hash_delay_us: int
) -> None:
    pilot, fixture = harness
    queue_submission(pilot, fixture)
    entered_at = delay_action_file_hash(pilot, fixture, delay=timedelta(microseconds=hash_delay_us))
    result = pilot.run()
    assert result["validated"] and result["status"] == "submitted"
    assert len(entered_at) == 1
    assert datetime.fromisoformat(result["finished_at"]) == (
        entered_at[0] + timedelta(microseconds=hash_delay_us)
    )
    assert_one_completion_instant(result)
    assert (
        result["recorded_actions_sha256"]
        == hashlib.sha256(Path(result["recorded_actions_path"]).read_bytes()).hexdigest()
    )
    assert len(pilot.calls) == 1 and not pilot.queries and not pilot.pending
    assert result["network_budget"]["wall_guard_ms"] == 900_000
    assert result["requested_reasoning_effort"] is None


@pytest.mark.parametrize(
    ("hash_delay_us", "expected_status"),
    [(2999, "submitted"), (3000, "incomplete"), (3001, "incomplete"), (5000, "incomplete")],
)
def test_hash_crossing_exact_guard_cannot_leave_submitted(
    harness: tuple[Any, Any], hash_delay_us: int, expected_status: str
) -> None:
    pilot, fixture = harness
    # 12s bootstrap + 10ms source + 12s checkpoint + 875987ms commit
    # leave exactly 3ms of the original immutable guard before the final hash.
    queue_submission(pilot, fixture, commit_elapsed=875_987)
    entered_at = delay_action_file_hash(pilot, fixture, delay=timedelta(microseconds=hash_delay_us))
    result = pilot.run()
    assert len(entered_at) == 1
    deadline = datetime.fromisoformat(result["wall_deadline_at"])
    assert entered_at[0] == deadline - timedelta(milliseconds=3)
    assert result["status"] == expected_status
    assert result["validated"] and result["source_counters_complete"]
    assert_one_completion_instant(result)
    assert result["accepted_source_action_count"] == 1
    assert len(pilot.read("accepted-journal.json")["facts"]) == 1
    assert len(pilot.calls) == 1 and not pilot.queries and not pilot.pending
    assert not pilot.runtime["STOP"].is_set()
    assert datetime.fromisoformat(result["accepted_trace_ended_at"]) < deadline
    assert result["network_budget"]["wall_guard_ms"] == 900_000
    assert (deadline - datetime.fromisoformat(result["wall_started_at"])).total_seconds() == 900
    if expected_status == "incomplete":
        assert result["error"] == "wall_guard_exhausted_during_completion_hash"
        assert result["finalization_note"] == result["error"]
        assert result["error_recorded_at"] == result["finished_at"]
    else:
        assert "error" not in result


def test_completion_guard_keeps_original_failure_and_checkpoint(harness: tuple[Any, Any]) -> None:
    pilot, fixture = harness
    fixture.bootstrap(pilot)
    fixture.checkpoint(pilot)
    pilot.queue(elapsed=875_987, error="selector_timeout")
    delay_action_file_hash(pilot, fixture, delay=timedelta(milliseconds=5))
    result = pilot.run()
    assert result["status"] == "incomplete"
    assert result["error"] == "selector_timeout"
    assert result["validated"] and len(pilot.read("accepted-journal.json")["facts"]) == 1
    assert_one_completion_instant(result)
    assert datetime.fromisoformat(result["finished_at"]) > datetime.fromisoformat(
        result["wall_deadline_at"]
    )
    assert not pilot.runtime["STOP"].is_set()
    assert len(pilot.calls) == 1 and not pilot.pending


def test_completion_uses_one_utc_read_after_hash(harness: tuple[Any, Any]) -> None:
    pilot, fixture = harness
    queue_submission(pilot, fixture)
    hash_completed = False
    completion_reads: list[datetime] = []

    class CountingDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            value = fixture.FakeDatetime.now(tz or UTC)
            if hash_completed:
                completion_reads.append(value)
            return value

    def finished_hash() -> None:
        nonlocal hash_completed
        hash_completed = True

    pilot.runtime["datetime"] = CountingDatetime
    delay_action_file_hash(
        pilot, fixture, delay=timedelta(milliseconds=5), after_hash=finished_hash
    )
    result = pilot.run()
    assert result["status"] == "submitted"
    assert len(completion_reads) == 1
    assert result["finished_at"] == completion_reads[0].isoformat()
    assert_one_completion_instant(result)
    assert pilot.read("result.json")["finished_at"] == result["finished_at"]


def test_original_v12_fixture_and_parent_stay_exact() -> None:
    assert hashlib.sha256(ORIGINAL_PARENT.read_bytes()).hexdigest() == PARENT_V12_SHA
    assert hashlib.sha256(ORIGINAL_FIXTURE.read_bytes()).hexdigest() == FIXTURE_V12_SHA
    # This isolated clock candidate is deliberately not a complete V13 chain.
    source = PARENT.read_text()
    assert 'protocol_version="journal-v12"' in source
    assert 'trial["protocol_version"] != "journal-v12"' in source
