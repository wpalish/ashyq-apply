"""V6 source dispatch closes early without changing the original selector clock."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from evaluation.research.expert.compact import SCOPE_DIMENSIONS
from evaluation.research.expert.journal import AcceptedJournal
from evaluation.research.expert.research_timing import (
    policy_card,
    policy_limits,
    research_state,
    source_proposal,
)
from evaluation.research.expert.turn_policy import (
    parse_turn_decision,
    turn_window,
)
from evaluation.research.expert.turn_policy import (
    policy_limits as original_turn_limits,
)


@pytest.mark.parametrize(
    "active_ms,recorded,processed,mode,phase,pending,dispatch,full_window",
    [
        (0, 0, 0, "research", "bootstrap", 0, True, None),
        (48999, 0, 0, "research", "bootstrap", 0, True, None),
        (48999, 1, 0, "research", "data", 1, True, None),
        (48999, 1, 1, "research", "data", 0, True, None),
        (49000, 1, 0, "data_closure", "data", 1, False, True),
        (49000, 2, 1, "data_closure", "data", 1, False, True),
        (49000, 1, 1, "minimal_commit", "minimal_commit", 0, False, None),
        (49000, 0, 0, "data_closure", "data", 0, False, None),
        (52000, 1, 0, "data_closure", "data", 1, False, True),
        (52001, 1, 0, "data_closure", "data", 1, False, False),
        (120005, 1, 0, "data_closure", "data", 1, False, False),
        (120005, 1, 1, "minimal_commit", "minimal_commit", 0, False, None),
    ],
)
def test_state_uses_exact_clock_and_actual_processing_counts(
    active_ms: int,
    recorded: int,
    processed: int,
    mode: str,
    phase: str,
    pending: int,
    dispatch: bool,
    full_window: bool | None,
) -> None:
    state = research_state(
        active_ms=active_ms,
        recorded_source_count=recorded,
        processed_source_count=processed,
    )
    assert (state.mode, state.phase) == (mode, phase)
    assert state.active_ms == active_ms
    assert state.recorded_source_count == recorded
    assert state.processed_source_count == processed
    assert state.pending_source_count == pending
    assert state.can_dispatch_source is dispatch
    assert state.full_final_data_window_available is full_window
    assert state.source_cutoff_reached is (active_ms >= 49000)
    assert state.as_dict()["active_ms"] == active_ms


@pytest.mark.parametrize("recorded,processed", [(0, 0), (1, 0), (2, 1), (2, 2)])
def test_explicit_earlier_closure_preserves_pending_processing(
    recorded: int, processed: int
) -> None:
    state = research_state(
        active_ms=1000,
        recorded_source_count=recorded,
        processed_source_count=processed,
        source_closed=True,
    )
    assert state.source_closed is True
    assert state.can_dispatch_source is False
    assert state.source_cutoff_reached is False
    if recorded > 0 and recorded == processed:
        assert state.mode == state.phase == "minimal_commit"
        assert state.full_final_data_window_available is None
    else:
        assert state.mode == "data_closure" and state.phase == "data"
        assert state.full_final_data_window_available is (True if recorded > processed else None)


def test_full_final_data_window_boundary_does_not_round_or_change_v5_windows() -> None:
    for active_ms, expected in [(51999, True), (52000, True), (52001, False)]:
        state = research_state(
            active_ms=active_ms, recorded_source_count=1, processed_source_count=0
        )
        assert state.full_final_data_window_available is expected
        assert turn_window(phase="data", active_ms=active_ms).timeout_ms == min(
            55000, 120000 - active_ms - 13000
        )
    assert turn_window(phase="data", active_ms=52001).timeout_seconds == 54.999
    assert 52000 + 55000 + 10000 + 3000 == 120000


def test_pending_source_never_selects_hash_only_minimal_commit() -> None:
    for active_ms in (0, 49000, 52001, 117000, 120005):
        state = research_state(
            active_ms=active_ms,
            recorded_source_count=3,
            processed_source_count=2,
            source_closed=True,
        )
        assert state.phase == "data" and state.pending_source_count == 1
        assert state.mode == "data_closure"


def test_actual_overrun_remains_visible_and_does_not_grant_a_commit_window() -> None:
    state = research_state(active_ms=120005, recorded_source_count=3, processed_source_count=3)
    assert state.active_ms == 120005 and state.phase == "minimal_commit"
    assert source_proposal(active_ms=state.active_ms).as_dict()["active_ms"] == 120005
    window = turn_window(phase=state.phase, active_ms=state.active_ms)
    assert window.remaining_ms == -5 and window.timeout_ms is None


@pytest.mark.parametrize("active_ms", [0, 1, 48999, 49000, 49001, 95000, 120005])
def test_source_proposal_cutoff_is_checked_at_actual_dispatch_time(active_ms: int) -> None:
    result = source_proposal(active_ms=active_ms)
    assert result.active_ms == active_ms
    assert result.dispatch_allowed is (active_ms < 49000)
    assert result.status == ("dispatch_allowed" if active_ms < 49000 else "declined")
    assert result.reason == (
        "before_source_cutoff" if active_ms < 49000 else "source_cutoff_reached"
    )
    assert result.source_dispatch_cutoff_ms == 49000
    assert result.source_deadline_ms == 95000
    assert result.as_dict()["dispatch_allowed"] is result.dispatch_allowed


def test_earlier_source_closure_declines_even_before_cutoff() -> None:
    result = source_proposal(active_ms=1000, source_closed=True)
    assert result.status == "declined" and result.reason == "source_closed"
    assert result.active_ms == 1000 and result.source_closed is True


def test_valid_late_action_keeps_its_complete_typed_delta_and_declines_its_proposal() -> None:
    journal_hash = AcceptedJournal.initial().sha256
    scope = {**dict.fromkeys(SCOPE_DIMENSIONS), "university": "Example Research University"}
    value = {
        "kind": "action",
        "observation": "A synthetic saved source was processed; another action is proposed.",
        "journal_sha256": journal_hash,
        "action": {
            "tool": "fetcher",
            "url": "https://example.edu/next",
            "query": None,
            "domains": [],
            "max_results": None,
            "source_step": None,
            "page": None,
            "offset": None,
            "section_offset": None,
            "link_offset": None,
        },
        "facts": [
            {
                "id": "synthetic_fact",
                "question": "OTHER",
                "claim_key": "unmapped.example",
                "value_json": '{"value":false,"conditions":["example"]}',
                "source_step": 1,
                "quotation": "An exact synthetic source quotation.",
                "location": {
                    "kind": "text",
                    "block_id": None,
                    "section_path": [],
                    "page": None,
                },
                "scope": scope,
            }
        ],
        "question_findings": [],
    }
    original = deepcopy(value)
    parsed = parse_turn_decision(
        value,
        journal_sha256=journal_hash,
        canonical_university="Example Research University",
        phase="data",
    )
    # The genuine parent citation/journal gate must precede this clock-only check.
    assert turn_window(phase="data", active_ms=40000).timeout_ms == 55000
    decline = source_proposal(active_ms=60000)
    assert decline.status == "declined" and decline.reason == "source_cutoff_reached"
    assert parsed.model_dump(mode="json") == original and value == original
    assert parsed.facts[0].decoded_value() == {"value": False, "conditions": ["example"]}
    after_processing = research_state(
        active_ms=60000, recorded_source_count=1, processed_source_count=1
    )
    assert after_processing.phase == "minimal_commit"
    assert turn_window(phase=after_processing.phase, active_ms=60000).timeout_ms == 10000


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None, -1])
def test_clock_requires_nonnegative_exact_integer(invalid: Any) -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        research_state(active_ms=invalid, recorded_source_count=0, processed_source_count=0)
    with pytest.raises(ValueError, match="nonnegative integer"):
        source_proposal(active_ms=invalid)


@pytest.mark.parametrize("field", ["recorded_source_count", "processed_source_count"])
@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None, -1])
def test_counts_require_nonnegative_exact_integers(field: str, invalid: Any) -> None:
    values: dict[str, Any] = {
        "active_ms": 1000,
        "recorded_source_count": 2,
        "processed_source_count": 1,
    }
    values[field] = invalid
    with pytest.raises(ValueError, match="nonnegative integer"):
        research_state(**values)


def test_processed_count_cannot_exceed_recorded_count() -> None:
    with pytest.raises(ValueError, match="exceed"):
        research_state(active_ms=49000, recorded_source_count=1, processed_source_count=2)


@pytest.mark.parametrize("invalid", [0, 1, "false", None])
def test_source_closed_must_be_an_exact_boolean(invalid: Any) -> None:
    with pytest.raises(ValueError, match="boolean"):
        research_state(
            active_ms=0,
            recorded_source_count=0,
            processed_source_count=0,
            source_closed=invalid,
        )
    with pytest.raises(ValueError, match="boolean"):
        source_proposal(active_ms=0, source_closed=invalid)


def test_results_are_immutable_and_serialized_receipts_are_fresh() -> None:
    state = research_state(active_ms=49000, recorded_source_count=1, processed_source_count=0)
    proposal = source_proposal(active_ms=49000)
    mutable_state: Any = state
    mutable_proposal: Any = proposal
    with pytest.raises(FrozenInstanceError):
        mutable_state.active_ms = 0
    with pytest.raises(FrozenInstanceError):
        mutable_proposal.active_ms = 0
    state_dict = state.as_dict()
    state_dict["processed_source_count"] = 1
    proposal_dict = proposal.as_dict()
    proposal_dict["active_ms"] = 0
    assert state.as_dict()["processed_source_count"] == 0
    assert proposal.as_dict()["active_ms"] == 49000


def test_limits_keep_original_caps_and_exact_predeclared_partition() -> None:
    limits = policy_limits()
    assert limits["max_ms"] == 120000
    assert limits["max_calls"] == 60 and limits["max_search_queries"] == 6
    assert limits["source_deadline_ms"] == 95000
    assert limits["source_dispatch_cutoff_ms"] == 49000
    assert limits["final_data_start_deadline_ms"] == 52000
    assert (
        limits["source_dispatch_cutoff_ms"]
        + limits["preparation_reserve_ms"]
        + limits["full_final_data_ms"]
        + limits["minimal_commit_reserve_ms"]
        + limits["mechanical_validation_reserve_ms"]
    ) == limits["max_ms"]
    assert limits["phase_cap_ms"] == original_turn_limits()["phase_cap_ms"]
    assert limits["phase_cap_ms"] == {"bootstrap": 30000, "data": 55000, "minimal_commit": 10000}
    limits["phase_cap_ms"]["data"] = 99000
    assert policy_limits()["phase_cap_ms"]["data"] == 55000
    card = policy_card()
    assert "49000" in card and "52000" in card and "120000" in card
    assert "declin" in card and "pending" in card and "55000" in card
