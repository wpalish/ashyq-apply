"""Pure staged-research ledger helpers; durable fences belong to the Worker.

These helpers perform no dispatch or persistence. Commit each replacement under
an ownership fence before network I/O, and enforce its remaining deadline on the
actual operation. A metadata ledger alone does not enforce a runtime budget.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STAGED_RESEARCH = False
LEDGER_KEY = "staged_research_v1"
Phase = Literal["fast", "deep_queued", "deep", "complete", "cancelled"]
ResearchMode = Literal["fast", "fast_then_deep"]
Tier = Literal[120, 300, 900, 1800]


class StrictFrozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Caps(StrictFrozen):
    milliseconds: int
    queries: int
    reads: int


CAPS: dict[int, Caps] = {
    120: Caps(milliseconds=120000, queries=6, reads=60),
    300: Caps(milliseconds=300000, queries=12, reads=120),
    900: Caps(milliseconds=900000, queries=24, reads=240),
    1800: Caps(milliseconds=1800000, queries=24, reads=240),
}


class Clock(StrictFrozen):
    session_id: str = Field(min_length=1, max_length=128)
    monotonic_ms: int = Field(ge=0)
    wall_at: datetime

    @model_validator(mode="after")
    def aware(self) -> Clock:
        if self.wall_at.utcoffset() is None:
            raise ValueError("UTC-aware wall clock required")
        return self


class UniversityUsage(StrictFrozen):
    university: str = Field(min_length=1, max_length=256)
    queries: int = Field(default=0, ge=0)
    reads: int = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)
    clock: Clock | None = None


class StagedResearch(StrictFrozen):
    version: Literal[1] = 1
    episode_id: str = Field(min_length=1, max_length=128)
    research_mode: ResearchMode = "fast"
    deep_tier: Tier = 300
    phase: Phase = "fast"
    revision: int = Field(default=0, ge=0)
    universities: tuple[UniversityUsage, ...] = ()

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("unsupported staged ledger version")
        return value

    @model_validator(mode="after")
    def coherent(self) -> StagedResearch:
        keys = [u.university for u in self.universities]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate university identity")
        if self.research_mode == "fast" and self.phase in {"deep_queued", "deep"}:
            raise ValueError("fast-only research cannot enter deep phase")
        if self.phase not in {"fast", "deep"} and any(u.clock for u in self.universities):
            raise ValueError("inactive phase cannot retain an active clock")
        cap = self.caps
        if any(u.queries > cap.queries or u.reads > cap.reads for u in self.universities):
            raise ValueError("invalid cumulative reservation counts")
        return self

    @property
    def enqueue_key(self) -> str:
        # Stable across retries and revisions; database uniqueness owns idempotency.
        return "deep:" + hashlib.sha256(self.episode_id.encode()).hexdigest()

    @property
    def caps(self) -> Caps:
        return CAPS[120 if self.phase == "fast" or self.research_mode == "fast" else self.deep_tier]


class BudgetExhausted(ValueError):
    """Persist ``state`` even on exhaustion to retain elapsed-time accounting."""

    def __init__(self, reason: str, state: StagedResearch):
        super().__init__(reason)
        self.state = state


def _replace(state: StagedResearch, usage: UniversityUsage) -> StagedResearch:
    rows = (*(u for u in state.universities if u.university != usage.university), usage)
    return StagedResearch.model_validate(
        {
            **state.model_dump(),
            "universities": rows,
            "revision": state.revision + 1,
        }
    )


def _usage(state: StagedResearch, university: str) -> UniversityUsage:
    return next(
        (u for u in state.universities if u.university == university),
        UniversityUsage(university=university),
    )


def _clock(session_id: str, monotonic_ms: int, wall_at: datetime) -> Clock:
    return Clock(session_id=session_id, monotonic_ms=monotonic_ms, wall_at=wall_at)


def checkpoint(
    state: StagedResearch,
    university: str,
    *,
    session_id: str,
    monotonic_ms: int,
    wall_at: datetime,
) -> StagedResearch:
    """Charge active time; a new process conservatively includes outage time.

    A process must use a fresh session_id on restart/monotonic-clock reset.
    Cross-process wall-clock rollback fails closed; host downtime is charged,
    never silently forgiven. Persist checkpoints frequently to limit ambiguity.
    """
    current = _clock(session_id, monotonic_ms, wall_at)
    usage = _usage(state, university)
    if usage.clock is None:
        return state
    prior = usage.clock
    if prior.session_id == session_id:
        delta = monotonic_ms - prior.monotonic_ms
    else:
        wall_delta = (wall_at - prior.wall_at).total_seconds()
        if wall_delta < 0:
            raise BudgetExhausted("clock rollback; manual reconciliation required", state)
        delta = math.ceil(wall_delta * 1000)
    if delta < 0:
        raise BudgetExhausted("clock rollback; manual reconciliation required", state)
    return _replace(
        state,
        usage.model_copy(
            update={
                "elapsed_ms": usage.elapsed_ms + delta,
                "clock": current,
            }
        ),
    )


def begin_attempt(
    state: StagedResearch,
    university: str,
    *,
    session_id: str,
    monotonic_ms: int,
    wall_at: datetime,
) -> StagedResearch:
    if state.phase not in {"fast", "deep"}:
        raise ValueError("research phase is inactive")
    state = checkpoint(
        state, university, session_id=session_id, monotonic_ms=monotonic_ms, wall_at=wall_at
    )
    usage = _usage(state, university)
    return _replace(
        state,
        usage.model_copy(
            update={
                "clock": _clock(session_id, monotonic_ms, wall_at),
            }
        ),
    )


def end_attempt(
    state: StagedResearch,
    university: str,
    *,
    session_id: str,
    monotonic_ms: int,
    wall_at: datetime,
) -> StagedResearch:
    state = checkpoint(
        state, university, session_id=session_id, monotonic_ms=monotonic_ms, wall_at=wall_at
    )
    usage = _usage(state, university)
    if usage.clock is None:
        return state
    return _replace(state, usage.model_copy(update={"clock": None}))


def reserve(
    state: StagedResearch,
    university: str,
    kind: Literal["query", "read"],
    *,
    session_id: str,
    monotonic_ms: int,
    wall_at: datetime,
) -> tuple[StagedResearch, int]:
    """Return fenced replacement and remaining operation deadline in milliseconds.

    Reservations charge attempts, including failed dispatches and cached reads.
    The caller must persist before I/O and timeout/cancel I/O by the deadline.
    """
    if state.phase not in {"fast", "deep"} or kind not in {"query", "read"}:
        raise ValueError("invalid reservation phase or kind")
    state = checkpoint(
        state, university, session_id=session_id, monotonic_ms=monotonic_ms, wall_at=wall_at
    )
    usage = _usage(state, university)
    if usage.clock is None:
        raise ValueError("begin_attempt must be durably committed first")
    field = "queries" if kind == "query" else "reads"
    remaining = state.caps.milliseconds - usage.elapsed_ms
    if remaining <= 0 or getattr(usage, field) >= getattr(state.caps, field):
        raise BudgetExhausted("cumulative university budget exhausted", state)
    return _replace(state, usage.model_copy(update={field: getattr(usage, field) + 1})), remaining


def advance(
    state: StagedResearch,
    target: Phase,
    *,
    session_id: str,
    monotonic_ms: int,
    wall_at: datetime,
) -> StagedResearch:
    """Stop active clocks and replace phase; same-target transitions are no-ops.

    Commit fast->deep_queued with enqueue_key insertion in ONE fenced transaction.
    Claim that unique queue row before deep_queued->deep. These pure helpers do
    not provide leases, queue insertion, database CAS, or exactly-once dispatch.
    """
    if target == state.phase:
        return state
    allowed = {
        "fast": {"deep_queued", "complete", "cancelled"},
        "deep_queued": {"deep", "cancelled"},
        "deep": {"complete", "cancelled"},
        "complete": set(),
        "cancelled": set(),
    }
    if target not in allowed[state.phase]:
        raise ValueError("invalid phase transition")
    if target == "deep_queued" and state.research_mode != "fast_then_deep":
        raise ValueError("fast-only research cannot enqueue deep work")
    for usage in state.universities:
        if usage.clock is not None:
            state = end_attempt(
                state,
                usage.university,
                session_id=session_id,
                monotonic_ms=monotonic_ms,
                wall_at=wall_at,
            )
    return StagedResearch.model_validate(
        {
            **state.model_dump(),
            "phase": target,
            "revision": state.revision + 1,
        }
    )
