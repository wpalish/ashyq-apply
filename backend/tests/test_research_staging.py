"""Pure durable accounting controls; no provider or Worker integration claim."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.research.staging import (
    CAPS,
    STAGED_RESEARCH,
    BudgetExhausted,
    StagedResearch,
    advance,
    begin_attempt,
    checkpoint,
    end_attempt,
    reserve,
)

NOW = datetime(2026, 10, 10, tzinfo=UTC)


def clock(ms=0, session="process1", wall_ms=None):
    return {
        "session_id": session,
        "monotonic_ms": ms,
        "wall_at": NOW + timedelta(milliseconds=ms if wall_ms is None else wall_ms),
    }


def started(**kwargs):
    return begin_attempt(StagedResearch(episode_id="job1", **kwargs), "uni1", **clock())


def usage(state):
    return next(u for u in state.universities if u.university == "uni1")


def test_defaults_are_off_and_fast_only():
    assert STAGED_RESEARCH is False
    state = started()
    with pytest.raises(ValueError, match="fast-only"):
        advance(state, "deep_queued", **clock())


def test_strict_version_and_roundtrip():
    state = started(research_mode="fast_then_deep", deep_tier=900)
    assert StagedResearch.model_validate_json(state.model_dump_json()) == state
    for changes in (
        {"version": 2},
        {"version": True},
        {"version": 1.0},
        {"extra": True},
        {"revision": True},
    ):
        with pytest.raises(ValidationError):
            StagedResearch.model_validate({**state.model_dump(), **changes})


def test_reserve_returns_immutable_replacement_and_deadline():
    state = started()
    newer, remaining = reserve(state, "uni1", "query", **clock(1000))
    assert usage(state).queries == 0
    assert usage(newer).queries == 1 and usage(newer).elapsed_ms == 1000
    assert remaining == 119000
    assert newer.revision > state.revision
    with pytest.raises(ValidationError):
        newer.phase = "deep"


def test_failed_dispatch_and_retry_do_not_refund_counts_or_time():
    state = started()
    state, _ = reserve(state, "uni1", "query", **clock(1000))
    state = end_attempt(state, "uni1", **clock(3000))
    state = begin_attempt(state, "uni1", **clock(10000))
    state, remaining = reserve(state, "uni1", "query", **clock(11000))
    assert usage(state).queries == 2 and usage(state).elapsed_ms == 4000
    assert remaining == 116000  # deliberately ended queue/wait time is not active


def test_crash_recovery_charges_since_durable_checkpoint():
    state = started()
    state, _ = reserve(state, "uni1", "read", **clock(5000))
    restored = StagedResearch.model_validate_json(state.model_dump_json())
    restored = begin_attempt(restored, "uni1", **clock(10, "process2", 25000))
    assert usage(restored).elapsed_ms == 25000
    assert usage(restored).reads == 1


def test_clock_rollback_fails_closed_without_budget_reset():
    state = started()
    state = checkpoint(state, "uni1", **clock(5000))
    with pytest.raises(BudgetExhausted, match="rollback") as exc:
        begin_attempt(state, "uni1", **clock(1, "process2", 4999))
    assert exc.value.state == state
    with pytest.raises(BudgetExhausted, match="rollback"):
        checkpoint(state, "uni1", **clock(4999))


@pytest.mark.parametrize("kind,limit", [("query", 6), ("read", 60)])
def test_fast_caps_reserve_before_dispatch(kind, limit):
    state = started()
    for _ in range(limit):
        state, _ = reserve(state, "uni1", kind, **clock())
    with pytest.raises(BudgetExhausted):
        reserve(state, "uni1", kind, **clock())
    assert getattr(usage(state), "queries" if kind == "query" else "reads") == limit


def test_exhaustion_preserves_elapsed_replacement_for_fenced_commit():
    state = started()
    with pytest.raises(BudgetExhausted) as exc:
        reserve(state, "uni1", "read", **clock(120001))
    assert usage(exc.value.state).elapsed_ms == 120001
    assert usage(exc.value.state).reads == 0


@pytest.mark.parametrize("tier", [120, 300, 900, 1800])
def test_deep_caps_are_cumulative_across_phases(tier):
    state = started(research_mode="fast_then_deep", deep_tier=tier)
    state, _ = reserve(state, "uni1", "query", **clock(1000))
    state = advance(state, "deep_queued", **clock(2000))
    key = state.enqueue_key
    assert advance(state, "deep_queued", **clock(9000)) is state
    state = advance(state, "deep", **clock(10000))
    state = begin_attempt(state, "uni1", **clock(11000))
    assert state.enqueue_key == key
    for _ in range(CAPS[tier].queries - 1):
        state, _ = reserve(state, "uni1", "query", **clock(12000))
    assert usage(state).elapsed_ms == 3000
    assert usage(state).queries == CAPS[tier].queries
    with pytest.raises(BudgetExhausted):
        reserve(state, "uni1", "query", **clock(12000))


def test_universities_have_separate_cumulative_caps():
    state = started()
    for _ in range(6):
        state, _ = reserve(state, "uni1", "query", **clock())
    state = end_attempt(state, "uni1", **clock())
    state = begin_attempt(state, "uni2", **clock())
    state, _ = reserve(state, "uni2", "query", **clock())
    assert {u.university: u.queries for u in state.universities} == {"uni1": 6, "uni2": 1}


@pytest.mark.parametrize("target", ["complete", "cancelled"])
def test_terminal_state_cannot_resume_or_dispatch(target):
    state = advance(started(), target, **clock(1000))
    assert usage(state).clock is None and usage(state).elapsed_ms == 1000
    assert advance(state, target, **clock()) is state
    with pytest.raises(ValueError):
        advance(state, "fast", **clock())
    with pytest.raises(ValueError):
        reserve(state, "uni1", "read", **clock())


def test_missing_attempt_and_incompatible_phase_are_rejected():
    state = StagedResearch(episode_id="job1")
    with pytest.raises(ValueError, match="begin_attempt"):
        reserve(state, "uni1", "query", **clock())
    with pytest.raises(ValueError, match="transition"):
        advance(state, "deep", **clock())
    with pytest.raises(ValidationError):
        begin_attempt(
            state, "uni1", session_id="process1", monotonic_ms=0, wall_at=datetime(2026, 10, 10)
        )


def test_restored_fast_ledger_cannot_use_deep_count_caps():
    state = started(research_mode="fast_then_deep", deep_tier=900)
    invalid = state.model_dump()
    invalid["universities"][0]["queries"] = 10
    with pytest.raises(ValidationError, match="cumulative"):
        StagedResearch.model_validate(invalid)


def test_fast_only_terminal_caps_remain_fast():
    state = advance(started(deep_tier=900), "complete", **clock())
    assert state.caps == CAPS[120]


def test_recovery_never_rounds_away_clock_rollback_or_active_time():
    state = started()
    with pytest.raises(BudgetExhausted, match="rollback"):
        begin_attempt(
            state,
            "uni1",
            session_id="process2",
            monotonic_ms=0,
            wall_at=NOW - timedelta(microseconds=1),
        )
    newer = begin_attempt(
        state,
        "uni1",
        session_id="process2",
        monotonic_ms=0,
        wall_at=NOW + timedelta(microseconds=1),
    )
    assert usage(newer).elapsed_ms == 1
