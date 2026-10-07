"""Pure contract for prospective expert runs with separate network budgets.

The baseline keeps its 120 second active budget. The expert has the same 60
controlled page reads and six provider queries; model thinking consumes neither
the source ledger nor a smaller turn deadline. ``max_elapsed_ms`` labels the
900 second overall hang guard, rather than an allowance for source or model
time. A case's absolute wall interval is immutable across controller resumes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

NETWORK_COMPARISON_MODE = "independent_network_budget"
BUDGET_MODEL = "network_actions_v1"
WALL_GUARD_MS = 900_000
MAX_FETCHER_CALLS = 60
MAX_SEARCH_QUERIES = 6
BASELINE_MAX_ELAPSED_MS = 120_000


def expert_budget() -> dict[str, Any]:
    """Return fresh, explicit packet metadata for the expert policy."""
    return {
        "max_fetcher_calls": MAX_FETCHER_CALLS,
        "max_elapsed_ms": WALL_GUARD_MS,
        "max_search_queries": MAX_SEARCH_QUERIES,
        "browser_enabled": False,
        "model_thinking_included": False,
        "budget_model": BUDGET_MODEL,
        "wall_guard_ms": WALL_GUARD_MS,
        "max_elapsed_ms_purpose": "hang_guard_only",
        "elapsed_time_basis": "controller_actions_only",
    }


def validate_expert_budget(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Require the predeclared network policy and unchanged baseline caps."""
    if packet.get("comparison_mode") != NETWORK_COMPARISON_MODE:
        raise ValueError("Packet is not an independent network-budget comparison")
    expected = expert_budget()
    declared = packet.get("expert_budget")
    if not isinstance(declared, Mapping) or any(
        type(declared.get(key)) is not type(value) or declared.get(key) != value
        for key, value in expected.items()
    ):
        raise ValueError("Packet must declare the exact expert network budget")
    baseline = packet.get("baseline_budget")
    baseline_expected = {
        "max_fetcher_calls": MAX_FETCHER_CALLS,
        "max_search_queries": MAX_SEARCH_QUERIES,
        "max_elapsed_ms": BASELINE_MAX_ELAPSED_MS,
        "browser_enabled": False,
    }
    if not isinstance(baseline, Mapping) or any(
        type(baseline.get(key)) is not type(value) or baseline.get(key) != value
        for key, value in baseline_expected.items()
    ):
        raise ValueError(
            "Network comparison requires baseline 60 reads, six queries and 120 seconds"
        )
    return expected


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    return value.astimezone(UTC)


def parse_timestamp(value: str, *, field: str = "timestamp") -> datetime:
    """Parse a timestamp to aware UTC, rejecting naive or non-string values."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware timestamp") from exc
    return _utc(parsed, field)


@dataclass(frozen=True)
class WallGuard:
    """An exact absolute interval; no resume or timeout grants a fresh period."""

    started_at: datetime
    deadline_at: datetime

    def __post_init__(self) -> None:
        started = _utc(self.started_at, "wall_started_at")
        deadline = _utc(self.deadline_at, "wall_deadline_at")
        if deadline - started != timedelta(milliseconds=WALL_GUARD_MS):
            raise ValueError("Wall guard must span exactly 900000 milliseconds")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "deadline_at", deadline)

    def as_dict(self) -> dict[str, str]:
        return {
            "wall_started_at": self.started_at.isoformat(),
            "wall_deadline_at": self.deadline_at.isoformat(),
        }

    def remaining_seconds(self, *, now: datetime) -> float:
        current = self._current(now)
        return max(0.0, (self.deadline_at - current).total_seconds())

    def remaining_ms(self, *, now: datetime) -> int:
        # Floor exact microseconds: public metadata never rounds up an allowance.
        delta = self.deadline_at - self._current(now)
        microseconds = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
        return max(0, microseconds // 1_000)

    def _current(self, now: datetime) -> datetime:
        current = _utc(now, "now")
        if current < self.started_at:
            raise ValueError("Wall clock precedes the recorded case start")
        return current


def parse_wall_guard(*, wall_started_at: str, wall_deadline_at: str) -> WallGuard:
    return WallGuard(
        parse_timestamp(wall_started_at, field="wall_started_at"),
        parse_timestamp(wall_deadline_at, field="wall_deadline_at"),
    )
