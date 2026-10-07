"""Pure V6 research/closure routing inside the unchanged strict case clock.

The parent supplies actual cumulative active milliseconds and verified source
processing counts. This helper performs no I/O, accepts no journal or source,
and changes no V5 selector window. The parent must meter preparation/validation,
retain real overruns, bind every source proposal to a controlled request or a
saved measured decline, and validate genuine journal deltas independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .turn_policy import (
    MAX_CALLS,
    MAX_MS,
    MAX_SEARCH_QUERIES,
    MECHANICAL_VALIDATION_RESERVE_MS,
    MINIMAL_COMMIT_RESERVE_MS,
    SOURCE_DEADLINE_MS,
    TurnPhase,
)
from .turn_policy import (
    policy_limits as turn_policy_limits,
)

POLICY_VERSION = "1"
SOURCE_DISPATCH_CUTOFF_MS = 49000
PREPARATION_RESERVE_MS = 3000
FULL_FINAL_DATA_MS = 55000
FINAL_DATA_START_DEADLINE_MS = (
    MAX_MS - FULL_FINAL_DATA_MS - MINIMAL_COMMIT_RESERVE_MS - MECHANICAL_VALIDATION_RESERVE_MS
)
ResearchMode = Literal["research", "data_closure", "minimal_commit"]
ProposalStatus = Literal["dispatch_allowed", "declined"]
ProposalReason = Literal["before_source_cutoff", "source_cutoff_reached", "source_closed"]


def _nonnegative_integer(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _closed(value: bool) -> bool:
    if type(value) is not bool:
        raise ValueError("Source closed must be an exact boolean")
    return value


@dataclass(frozen=True, slots=True)
class ResearchState:
    """Routing only; verified counts and the existing turn window are required."""

    active_ms: int
    recorded_source_count: int
    processed_source_count: int
    source_closed: bool
    mode: ResearchMode
    phase: TurnPhase

    @property
    def pending_source_count(self) -> int:
        return self.recorded_source_count - self.processed_source_count

    @property
    def source_cutoff_reached(self) -> bool:
        return self.active_ms >= SOURCE_DISPATCH_CUTOFF_MS

    @property
    def can_dispatch_source(self) -> bool:
        return not self.source_closed and not self.source_cutoff_reached

    @property
    def full_final_data_window_available(self) -> bool | None:
        if self.can_dispatch_source or self.pending_source_count == 0:
            return None
        return self.active_ms <= FINAL_DATA_START_DEADLINE_MS

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "mode": self.mode,
            "phase": self.phase,
            "active_ms": self.active_ms,
            "recorded_source_count": self.recorded_source_count,
            "processed_source_count": self.processed_source_count,
            "pending_source_count": self.pending_source_count,
            "source_closed": self.source_closed,
            "source_cutoff_reached": self.source_cutoff_reached,
            "can_dispatch_source": self.can_dispatch_source,
            "full_final_data_window_available": self.full_final_data_window_available,
            "source_dispatch_cutoff_ms": SOURCE_DISPATCH_CUTOFF_MS,
            "source_deadline_ms": SOURCE_DEADLINE_MS,
            "final_data_start_deadline_ms": FINAL_DATA_START_DEADLINE_MS,
        }


def research_state(
    *,
    active_ms: int,
    recorded_source_count: int,
    processed_source_count: int,
    source_closed: bool = False,
) -> ResearchState:
    """Route by the original clock and genuine accepted source-processing count.

    Source dispatch closes at 49000 ms or an explicitly retained earlier
    closure. A pending source always requires a data turn, never a hash-only
    acknowledgment. With closing/pending source work, a full final 55000 ms
    turn requires active_ms <= 52000; False requires the parent to retain real
    timing and fail incomplete, rather than present a clipped window as full.

    A genuine accepted data/action response can finish after the source cutoff.
    Once it processes all recorded sources, a nonempty source history routes to
    minimal commit. Zero recorded sources cannot select this shortcut. These
    modes grant no allowance: the unchanged V5 turn_window still governs starts
    and can refuse a minimal commit after the cumulative clock is exhausted.
    """
    active = _nonnegative_integer(active_ms, "Active case milliseconds")
    recorded = _nonnegative_integer(recorded_source_count, "Recorded source count")
    processed = _nonnegative_integer(processed_source_count, "Processed source count")
    explicitly_closed = _closed(source_closed)
    if processed > recorded:
        raise ValueError("Processed source count cannot exceed recorded source count")
    if not explicitly_closed and active < SOURCE_DISPATCH_CUTOFF_MS:
        mode: ResearchMode = "research"
        phase: TurnPhase = "bootstrap" if recorded == 0 else "data"
    elif recorded > 0 and processed == recorded:
        mode = "minimal_commit"
        phase = "minimal_commit"
    else:
        mode = "data_closure"
        phase = "data"
    return ResearchState(
        active_ms=active,
        recorded_source_count=recorded,
        processed_source_count=processed,
        source_closed=explicitly_closed,
        mode=mode,
        phase=phase,
    )


@dataclass(frozen=True, slots=True)
class SourceProposalDecision:
    """A clock-only receipt to bind to one genuine accepted next-action proposal."""

    active_ms: int
    source_closed: bool

    @property
    def source_dispatch_cutoff_ms(self) -> int:
        return SOURCE_DISPATCH_CUTOFF_MS

    @property
    def source_deadline_ms(self) -> int:
        return SOURCE_DEADLINE_MS

    @property
    def dispatch_allowed(self) -> bool:
        return not self.source_closed and self.active_ms < SOURCE_DISPATCH_CUTOFF_MS

    @property
    def status(self) -> ProposalStatus:
        return "dispatch_allowed" if self.dispatch_allowed else "declined"

    @property
    def reason(self) -> ProposalReason:
        if self.active_ms >= SOURCE_DISPATCH_CUTOFF_MS:
            return "source_cutoff_reached"
        return "source_closed" if self.source_closed else "before_source_cutoff"

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "status": self.status,
            "reason": self.reason,
            "active_ms": self.active_ms,
            "source_closed": self.source_closed,
            "dispatch_allowed": self.dispatch_allowed,
            "source_dispatch_cutoff_ms": self.source_dispatch_cutoff_ms,
            "source_deadline_ms": self.source_deadline_ms,
        }


def source_proposal(*, active_ms: int, source_closed: bool = False) -> SourceProposalDecision:
    """Decide before dispatch; preserve the accepted delta and save any decline.

    The parent must remeasure after model work and all proposal preparation,
    and save the exact original proposal alongside this receipt. A successful
    response after cutoff retains its authentic validated delta; its next
    action is explicitly declined. A timeout/rejection remains a failure and
    cannot be reclassified as a valid cutoff decline. Existing source caps,
    provider stops, safety checks and controller ceilings still apply.
    """
    return SourceProposalDecision(
        active_ms=_nonnegative_integer(active_ms, "Active case milliseconds"),
        source_closed=_closed(source_closed),
    )


def policy_limits() -> dict[str, Any]:
    """Fresh public metadata for the exact predeclared 120000 ms allocation."""
    return {
        "policy_version": POLICY_VERSION,
        "max_ms": MAX_MS,
        "max_calls": MAX_CALLS,
        "max_search_queries": MAX_SEARCH_QUERIES,
        "source_dispatch_cutoff_ms": SOURCE_DISPATCH_CUTOFF_MS,
        "source_deadline_ms": SOURCE_DEADLINE_MS,
        "preparation_reserve_ms": PREPARATION_RESERVE_MS,
        "full_final_data_ms": FULL_FINAL_DATA_MS,
        "minimal_commit_reserve_ms": MINIMAL_COMMIT_RESERVE_MS,
        "mechanical_validation_reserve_ms": MECHANICAL_VALIDATION_RESERVE_MS,
        "final_data_start_deadline_ms": FINAL_DATA_START_DEADLINE_MS,
        "phase_cap_ms": dict(turn_policy_limits()["phase_cap_ms"]),
    }


def policy_card() -> str:
    """Public timing instructions; no source facts, routes or answer changes."""
    return (
        "V6 research timing: the original cumulative active case clock remains 120000 ms, "
        "with 60 cold page-read calls and six provider queries. Source dispatch ends at "
        "49000 ms, retaining the existing outer source ceiling of 95000 ms. The declared "
        "allocation is 49000 ms for research, 3000 ms for source/view/prompt preparation, "
        "55000 ms for a full final data turn, 10000 ms for minimal commit and 3000 ms for "
        "mechanical validation. Existing V5 bootstrap/data/minimal caps remain "
        "30000/55000/10000 ms, clipped only by their original internal reserves. "
        "A genuine complete accepted action response may finish after the source cutoff; "
        "retain its authentic validated journal delta and explicitly record a measured "
        "decline of its next source proposal before dispatch. A pending source must be "
        "processed by a genuine data response; it cannot be acknowledged only by hash. "
        "A closing data turn with pending source requires active time at most 52000 ms "
        "for its full 55000 ms window. Preparation overruns remain charged and cause "
        "incomplete failure rather than an extra allowance or a claimed full clipped "
        "window. Minimal commit requires a nonempty fully processed source history and "
        "the unchanged available V5 commit window. All actual time remains recorded; "
        "no resets, rounding allowance, partial-text salvage, timeout/rejection waiver "
        "or provider retry is granted."
    )
