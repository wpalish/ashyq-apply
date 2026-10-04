"""Default-effort V7 transport uses only one absolute guard; all I/O is mocked."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from evaluation.research.expert import network_turn_policy as policy
from evaluation.research.expert.blind_cli import DISABLED_FEATURES, Isolation
from evaluation.research.expert.compact import SCOPE_DIMENSIONS
from evaluation.research.expert.journal import AcceptedJournal, JournalDecision
from evaluation.research.expert.network_budget import WALL_GUARD_MS, WallGuard, parse_wall_guard
from evaluation.research.expert.network_turn_policy import (
    NetworkBudgetIsolation,
    TurnPhase,
    command_proof,
    journal_schema_for_turn,
    parse_turn_decision,
    policy_card,
    policy_limits,
    select,
    turn_window,
)
from evaluation.research.expert.representation import (
    CLOSING_OBSERVATION,
    closing_schema,
    journal_schema_for_case,
)
from evaluation.research.expert.selector import SelectorTurn
from evaluation.research.expert.turn_policy import AstraLowEffortIsolation
from evaluation.research.expert.workspace_policy import allocate_workspaces, selector_paths

START = datetime(2026, 10, 4, 0, 0, tzinfo=UTC)
GUARD = parse_wall_guard(
    wall_started_at=START.isoformat(),
    wall_deadline_at=(START + timedelta(milliseconds=WALL_GUARD_MS)).isoformat(),
)
HASH = AcceptedJournal.initial().sha256
UNIVERSITY = "Synthetic University"
PHASES: tuple[TurnPhase, ...] = ("bootstrap", "data", "minimal_commit")


@dataclass
class Clock:
    now: datetime = START
    elapsed: float = 0.0

    def wall(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.elapsed

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
        self.elapsed += seconds


def fact(index: int, **changes: Any) -> dict[str, Any]:
    return {
        "id": f"synthetic_{index}",
        "question": "OTHER",
        "claim_key": f"synthetic.{index}",
        "value_json": '{"published":false,"conditions":["synthetic"]}',
        "source_step": 1,
        "quotation": "A literal synthetic quotation.",
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": {**dict.fromkeys(SCOPE_DIMENSIONS), "university": UNIVERSITY},
        **changes,
    }


def decision(
    facts: int | list[dict[str, Any]] = 0, findings: int = 0, **changes: Any
) -> dict[str, Any]:
    return {
        "kind": "submit",
        "observation": CLOSING_OBSERVATION,
        "journal_sha256": HASH,
        "action": None,
        "facts": [fact(index) for index in range(facts)]
        if isinstance(facts, int)
        else deepcopy(facts),
        "question_findings": [
            {
                "question": f"Q{index}",
                "status": "unresolved",
                "fact_ids": [],
                "scope": dict.fromkeys(SCOPE_DIMENSIONS),
                "supporting_steps": [],
                "observation": "No matching synthetic source.",
            }
            for index in range(findings)
        ],
        **changes,
    }


def completed_events(raw: str) -> str:
    return "\n".join(
        json.dumps(item)
        for item in [
            {"type": "thread.started", "thread_id": "synthetic"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": raw}},
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
        ]
    )


def transport(tmp_path: Path) -> tuple[NetworkBudgetIsolation, Path, Path]:
    # Exercise the real canonical workspace/path API, never a model process.
    assignments, receipts = allocate_workspaces(("neutral",), temp_root=tmp_path)
    workspace = Path(assignments["neutral"])
    schema, output = selector_paths(
        assignments, receipts, case_id="neutral", turn=1, fresh_output=True
    )
    schema.write_text(
        json.dumps(
            journal_schema_for_turn(
                journal_sha256=HASH, canonical_university=UNIVERSITY, phase="data"
            )
        )
    )
    return (
        NetworkBudgetIsolation(workspace, (tmp_path.resolve() / "sealed",), "/sandbox", "/codex"),
        schema,
        output,
    )


def run(
    isolation: NetworkBudgetIsolation,
    schema: Path,
    output: Path,
    clock: Clock,
    *,
    phase: TurnPhase = "data",
) -> policy.NetworkSelectorTurn:
    return select(
        isolation,
        schema,
        output,
        {"public_synthetic": True},
        wall_guard=GUARD,
        phase=phase,
        clock=clock.wall,
        monotonic=clock.monotonic,
    )


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("elapsed", [0, 55, 120, 500.123, 899, 899.999999])
def test_every_phase_gets_only_the_original_remaining_guard(
    phase: TurnPhase, elapsed: float
) -> None:
    clock = Clock()
    clock.advance(elapsed)
    window = turn_window(phase=phase, wall_guard=GUARD, clock=clock.wall)
    remaining = GUARD.remaining_seconds(now=clock.now)
    assert window.timeout_seconds == remaining
    assert window.timeout_ms == remaining * 1000 and window.status == "available"
    assert window.wall_guard is GUARD and window.observed_at == clock.now
    assert window.as_dict()["wall_guard"] == GUARD.as_dict()
    assert window.remaining_ms == GUARD.remaining_ms(now=clock.now)
    assert (
        not {"phase_cap_ms", "reserved_ms", "active_ms", "source_deadline_ms"}
        & window.as_dict().keys()
    )


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("elapsed", [900, 900.001, 1200])
def test_guard_expiry_never_grants_any_phase_a_fresh_window(
    phase: TurnPhase, elapsed: float
) -> None:
    now = START + timedelta(seconds=elapsed)
    window = turn_window(phase=phase, wall_guard=GUARD, now=now)
    assert window.timeout_seconds is None and window.timeout_ms is None
    assert window.status == "no_available_window" and window.remaining_ms == 0


def test_submillisecond_window_is_not_rounded_up_or_given_a_minimum() -> None:
    window = turn_window(
        phase="data", wall_guard=GUARD, now=GUARD.deadline_at - timedelta(microseconds=1)
    )
    assert window.remaining_ms == 0 and window.timeout_seconds == 0.000001
    assert window.timeout_ms == 0.001


def test_window_and_guard_are_immutable_and_snapshot_is_fresh() -> None:
    window = turn_window(phase="data", wall_guard=GUARD, now=START)
    before = window.as_dict()
    with pytest.raises(FrozenInstanceError):
        window.phase = "bootstrap"  # type: ignore[misc]
    altered = window.as_dict()
    altered["wall_guard"]["wall_deadline_at"] = "untrusted"
    assert window.as_dict() == before


@pytest.mark.parametrize("phase", ["", "closing", "data ", None, True, 1])
def test_invalid_phase_fails_every_public_phase_gate(phase: Any) -> None:
    with pytest.raises(ValueError, match="Turn phase"):
        turn_window(phase=phase, wall_guard=GUARD, now=START)
    with pytest.raises(ValueError, match="Turn phase"):
        journal_schema_for_turn(journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase)
    with pytest.raises(ValueError, match="Turn phase"):
        parse_turn_decision(
            decision(), journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase
        )


@pytest.mark.parametrize("now", [START.replace(tzinfo=None), START - timedelta(microseconds=1)])
def test_invalid_or_before_start_clock_cannot_increase_allowance(now: datetime) -> None:
    with pytest.raises(ValueError):
        turn_window(phase="data", wall_guard=GUARD, now=now)


def test_untrusted_guard_mapping_is_not_an_immutable_case_guard() -> None:
    with pytest.raises(ValueError, match="immutable case WallGuard"):
        turn_window(phase="data", wall_guard=cast(WallGuard, GUARD.as_dict()), now=START)


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
def test_schema_only_changes_existing_delta_caps_and_retains_hash_identity(
    phase: TurnPhase,
) -> None:
    original = journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY)
    bound = journal_schema_for_turn(
        journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase
    )
    assert bound["properties"]["facts"]["maxItems"] == 4
    assert bound["properties"]["question_findings"]["maxItems"] == 2
    restored = deepcopy(bound)
    restored["properties"]["facts"]["maxItems"] = 16
    restored["properties"]["question_findings"]["maxItems"] = 7
    assert restored == original
    assert bound["properties"]["journal_sha256"]["enum"] == [HASH]
    assert bound["$defs"]["CompactScope"]["properties"]["university"]["enum"] == [None, UNIVERSITY]


def test_minimal_schema_preserves_exact_original_hash_only_contract() -> None:
    assert journal_schema_for_turn(
        journal_sha256=HASH, canonical_university=UNIVERSITY, phase="minimal_commit"
    ) == closing_schema(journal_sha256=HASH)


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
@pytest.mark.parametrize("shape", ["mapping", "json", "model"])
def test_four_facts_two_findings_preserve_unknowns_and_typed_values(
    phase: TurnPhase, shape: str
) -> None:
    original = decision(facts=4, findings=2)
    value: Any = original if shape == "mapping" else json.dumps(original)
    if shape == "model":
        value = JournalDecision.model_validate(original)
    parsed = parse_turn_decision(
        value, journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase
    )
    assert parsed.model_dump(mode="json") == original
    assert parsed.facts[0].decoded_value() == {"published": False, "conditions": ["synthetic"]}
    assert parsed.question_findings[0].scope.model_dump() == dict.fromkeys(SCOPE_DIMENSIONS)


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
@pytest.mark.parametrize("facts,findings", [(5, 0), (0, 3), (5, 3)])
def test_oversized_delta_is_rejected_atomically_without_truncation(
    phase: TurnPhase, facts: int, findings: int
) -> None:
    value = decision(facts=facts, findings=findings)
    original = deepcopy(value)
    with pytest.raises(ValueError, match="four facts|two question findings"):
        parse_turn_decision(
            value, journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase
        )
    assert original == value


@pytest.mark.parametrize(
    "changes",
    [
        {"journal_sha256": "f" * 64},
        {"facts": [fact(0, quotation=" ")]},
        {"facts": [fact(0, value_json="NaN")]},
        {
            "facts": [
                fact(0, scope={**dict.fromkeys(SCOPE_DIMENSIONS), "university": "Other Synthetic"})
            ]
        },
        {"private_answer_hint": "never allowed"},
    ],
)
def test_original_hash_identity_quote_value_and_allowlist_gates_remain(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        parse_turn_decision(
            decision(**changes), journal_sha256=HASH, canonical_university=UNIVERSITY, phase="data"
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"facts": [fact(0)]},
        {"question_findings": decision(findings=1)["question_findings"]},
        {"observation": "Rewritten completion"},
        {"kind": "record", "facts": [fact(0)]},
    ],
)
def test_minimal_phase_cannot_add_facts_findings_or_regenerate_a_close(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="Hash-only closing"):
        parse_turn_decision(
            decision(**changes),
            journal_sha256=HASH,
            canonical_university=UNIVERSITY,
            phase="minimal_commit",
        )


def test_default_effort_argv_retains_every_tool_free_isolation_feature(tmp_path: Path) -> None:
    isolation, schema, output = transport(tmp_path)
    argv = isolation.command(schema, output=output)
    assert argv == Isolation(
        isolation.workspace, isolation.sealed_roots, "/sandbox", "/codex"
    ).command(schema, output=output, model="gpt-6-astra")
    proof = command_proof(argv)
    assert proof["model"] == "gpt-6-astra" and proof["model_reasoning_effort"] is None
    assert proof["reasoning_override"] is None and proof["reasoning_effort_source"] == "cli_default"
    assert not any("model_reasoning_effort" in arg for arg in argv)
    assert argv.count("--disable") == len(DISABLED_FEATURES)
    for option in (
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
    ):
        assert argv.count(option) == 1
    assert argv[argv.index("-C") + 1] == str(isolation.workspace)
    assert (
        proof["argv_sha256"]
        == hashlib.sha256(
            json.dumps(argv, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
    )


@pytest.mark.parametrize("model", ["gpt-6-sol", "gpt-6-astra ", "", 1, True])
def test_model_changes_fail_before_any_process(tmp_path: Path, model: Any) -> None:
    isolation, schema, output = transport(tmp_path)
    with pytest.raises(ValueError, match="exact gpt-6-astra"):
        isolation.command(schema, output=output, model=model)


@pytest.mark.parametrize(
    "mutation",
    [
        "low",
        "high",
        "web",
        "enable_shell",
        "remove_disable",
        "missing_model",
        "duplicate_model",
        "foreign_schema",
        "foreign_output",
        "alias_workspace",
    ],
)
def test_command_proof_rejects_effort_tool_model_or_path_overrides(
    tmp_path: Path, mutation: str
) -> None:
    isolation, schema, output = transport(tmp_path)
    argv = isolation.command(schema, output=output)
    if mutation in {"low", "high"}:
        argv[-1:-1] = ["-c", f'model_reasoning_effort="{mutation}"']
    elif mutation == "web":
        argv[-1:-1] = ["-c", 'web_search="live"']
    elif mutation == "enable_shell":
        argv[-1:-1] = ["--enable", "shell_tool"]
    elif mutation == "remove_disable":
        index = argv.index("--disable")
        del argv[index : index + 2]
    elif mutation == "missing_model":
        index = argv.index("--model")
        del argv[index : index + 2]
    elif mutation == "duplicate_model":
        argv[-1:-1] = ["--model", "gpt-6-astra"]
    elif mutation == "alias_workspace":
        argv[argv.index("-C") + 1] = str(isolation.workspace) + "/../" + isolation.workspace.name
    else:
        option = "--output-schema" if mutation == "foreign_schema" else "--output-last-message"
        argv[argv.index(option) + 1] = str(tmp_path.resolve() / "outside")
    with pytest.raises(ValueError):
        command_proof(argv)


@pytest.mark.parametrize("path", ["workspace", "schema", "output"])
def test_real_filesystem_alias_is_rejected_by_new_isolation(tmp_path: Path, path: str) -> None:
    isolation, schema, output = transport(tmp_path)
    if path == "workspace":
        alias = tmp_path.resolve() / "workspace-alias"
        alias.symlink_to(isolation.workspace, target_is_directory=True)
        isolation = NetworkBudgetIsolation(alias, isolation.sealed_roots, "/sandbox", "/codex")
    else:
        alias = isolation.workspace / f"{path}-alias"
        alias.symlink_to(schema if path == "schema" else output)
        if path == "schema":
            schema = alias
        else:
            output = alias
    with pytest.raises(ValueError, match="canonical|aliases"):
        isolation.command(schema, output=output)


def test_public_policy_separates_network_actions_from_absolute_hang_guard() -> None:
    limits = policy_limits()
    assert limits["max_calls"] == 60 and limits["max_search_queries"] == 6
    assert limits["wall_guard_ms"] == 900000 and limits["model_thinking_included"] is False
    assert limits["model_reasoning_effort"] is limits["reasoning_override"] is None
    assert limits["comparison_mode"] == "independent_network_budget"
    assert (
        not {"phase_cap_ms", "minimal_commit_reserve_ms", "source_deadline_ms", "max_ms"}
        & limits.keys()
    )
    limits["model_reasoning_effort"] = "low"
    assert policy_limits()["model_reasoning_effort"] is None
    card = policy_card()
    assert "thinking consumes neither" in card and "15-minute" in card
    assert "no explicit effort override" in card and "outer wall-clock" in card


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("seconds", [56, 180, 899])
def test_mocked_long_model_turn_exceeds_old_caps_without_spending_network_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: TurnPhase, seconds: float
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock, calls = Clock(), []

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        assert kwargs["timeout"] == 900
        clock.advance(seconds)
        raw = json.dumps(decision())
        output.write_text(raw)
        return subprocess.CompletedProcess(argv, 0, completed_events(raw), "")

    monkeypatch.setattr(policy.subprocess, "run", completed)
    result = run(isolation, schema, output, clock, phase=phase)
    assert isinstance(result, SelectorTurn) and result.answer == decision()
    assert result.error_kind is None and result.elapsed_ms == seconds * 1000
    assert len(calls) == 1 and result.window.timeout_seconds == 900
    assert result.selector_finished_at == clock.now.isoformat()
    assert "model_reasoning_effort" not in " ".join(calls[0][0])


def test_preparation_cost_shrinks_actual_pre_spawn_guard_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()
    original = NetworkBudgetIsolation.command

    def delayed(self: NetworkBudgetIsolation, schema: Path, **kwargs: Any) -> list[str]:
        argv = original(self, schema, **kwargs)
        clock.advance(10)
        return argv

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == 890
        clock.advance(60)
        raw = json.dumps(decision())
        output.write_text(raw)
        return subprocess.CompletedProcess(argv, 0, completed_events(raw), "")

    monkeypatch.setattr(NetworkBudgetIsolation, "command", delayed)
    monkeypatch.setattr(policy.subprocess, "run", completed)
    result = run(isolation, schema, output, clock)
    assert result.answer == decision() and result.elapsed_ms == 70000
    assert result.window.observed_at == START + timedelta(seconds=10)
    assert result.window.timeout_seconds == 890


@pytest.mark.parametrize("when", ["before", "during_preparation"])
def test_expired_guard_never_spawns_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, when: str
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()
    if when == "before":
        clock.advance(900)
    else:
        original = NetworkBudgetIsolation.command

        def delayed(self: NetworkBudgetIsolation, schema: Path, **kwargs: Any) -> list[str]:
            argv = original(self, schema, **kwargs)
            clock.advance(900)
            return argv

        monkeypatch.setattr(NetworkBudgetIsolation, "command", delayed)
    monkeypatch.setattr(
        policy.subprocess, "run", lambda *a, **k: pytest.fail("Expired guard spawned a model")
    )
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.returncode is None
    assert result.error_kind == "selector_wall_guard_exhausted"
    assert result.window.timeout_seconds is None and not output.exists()


@pytest.mark.parametrize("late", [900, 900.001])
def test_completed_output_at_or_after_guard_is_preserved_but_not_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, late: float
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        clock.advance(late)
        raw = json.dumps(decision())
        output.write_text(raw)
        return subprocess.CompletedProcess(argv, 0, completed_events(raw), "")

    monkeypatch.setattr(policy.subprocess, "run", completed)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.error_kind == "selector_wall_guard_exhausted"
    assert result.returncode == 0 and "turn.completed" in result.stdout
    assert json.loads(output.read_text()) == decision()
    assert result.elapsed_ms >= 900000


def test_expiry_during_complete_stream_replay_does_not_accept_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()
    original = policy.selector_answer

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        clock.advance(1)
        raw = json.dumps(decision())
        output.write_text(raw)
        return subprocess.CompletedProcess(argv, 0, completed_events(raw), "")

    def slow_replay(events: str, raw: str) -> dict[str, Any]:
        answer = original(events, raw)
        clock.advance(899)
        return answer

    monkeypatch.setattr(policy.subprocess, "run", completed)
    monkeypatch.setattr(policy, "selector_answer", slow_replay)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.error_kind == "selector_wall_guard_exhausted"
    assert result.elapsed_ms == 900000


@pytest.mark.parametrize("bad", ["unfinished", "tool", "mismatch", "symlink", "hardlink", "failed"])
def test_uncertain_or_altered_completed_output_never_supplies_an_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        clock.advance(3)
        raw = json.dumps(decision())
        output.write_text(raw)
        events = completed_events(raw)
        if bad == "unfinished":
            events = '{"type":"turn.started"}'
        if bad == "tool":
            events = events.replace('"agent_message"', '"command_execution"')
        if bad == "mismatch":
            events = completed_events(json.dumps(decision(observation="Different")))
        if bad in {"symlink", "hardlink"}:
            moved = output.with_name("alternate.json")
            output.rename(moved)
            if bad == "symlink":
                output.symlink_to(moved)
            else:
                output.hardlink_to(moved)
        return subprocess.CompletedProcess(argv, 1 if bad == "failed" else 0, events, "")

    monkeypatch.setattr(policy.subprocess, "run", completed)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.elapsed_ms == 3000
    assert result.error_kind == (
        "selector_process_failed" if bad == "failed" else "selector_output_rejected"
    )


def test_timeout_charges_all_thinking_and_preserves_partial_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock, calls = Clock(), []

    def timeout(argv: list[str], **kwargs: Any) -> Any:
        calls.append(argv)
        clock.advance(900.125)
        raise subprocess.TimeoutExpired(
            argv, kwargs["timeout"], output=b"partial", stderr=b"unfinished"
        )

    monkeypatch.setattr(policy.subprocess, "run", timeout)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.error_kind == "selector_timeout"
    assert (
        result.elapsed_ms == 900125 and result.stdout == "partial" and result.stderr == "unfinished"
    )
    assert len(calls) == 1 and result.returncode is None


def test_process_unavailable_remains_metered_without_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock()

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        clock.advance(2)
        raise OSError("synthetic executable unavailable")

    monkeypatch.setattr(policy.subprocess, "run", unavailable)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.error_kind == "selector_process_unavailable"
    assert result.elapsed_ms == 2000


@pytest.mark.parametrize("wrapper", [Isolation, AstraLowEffortIsolation])
def test_old_selector_wrappers_cannot_silently_force_effort_or_old_mode(
    tmp_path: Path, wrapper: Any
) -> None:
    isolation, schema, output = transport(tmp_path)
    old = wrapper(isolation.workspace, isolation.sealed_roots, "/sandbox", "/codex")
    with pytest.raises(ValueError, match="default-effort isolated wrapper"):
        run(old, schema, output, Clock())


@pytest.mark.parametrize("regression", ["before_spawn", "after_return", "naive_after_return"])
def test_clock_regression_fails_before_dispatch_or_discards_completed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, regression: str
) -> None:
    isolation, schema, output = transport(tmp_path)
    clock = Clock(now=START + timedelta(seconds=10))
    original = NetworkBudgetIsolation.command
    if regression == "before_spawn":

        def changed(self: NetworkBudgetIsolation, schema: Path, **kwargs: Any) -> list[str]:
            argv = original(self, schema, **kwargs)
            clock.now -= timedelta(seconds=1)
            return argv

        monkeypatch.setattr(NetworkBudgetIsolation, "command", changed)
        monkeypatch.setattr(
            policy.subprocess, "run", lambda *a, **k: pytest.fail("Clock regression spawned model")
        )
        with pytest.raises(ValueError, match="backwards before dispatch"):
            run(isolation, schema, output, clock)
        return

    def completed(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        clock.advance(2)
        clock.now = (
            START + timedelta(seconds=9)
            if regression == "after_return"
            else clock.now.replace(tzinfo=None)
        )
        raw = json.dumps(decision())
        output.write_text(raw)
        return subprocess.CompletedProcess(argv, 0, completed_events(raw), "")

    monkeypatch.setattr(policy.subprocess, "run", completed)
    result = run(isolation, schema, output, clock)
    assert result.answer is None and result.error_kind == "selector_wall_clock_invalid"
    assert result.elapsed_ms == 2000


def test_legacy_low_effort_policy_and_selector_55s_limit_are_untouched(tmp_path: Path) -> None:
    from evaluation.research.expert.selector import select as old_select
    from evaluation.research.expert.turn_policy import policy_limits as old_limits

    isolation, schema, output = transport(tmp_path)
    old = AstraLowEffortIsolation(isolation.workspace, isolation.sealed_roots, "/sandbox", "/codex")
    assert 'model_reasoning_effort="low"' in old.command(schema, output=output)
    assert old_limits()["phase_cap_ms"] == {
        "bootstrap": 30000,
        "data": 55000,
        "minimal_commit": 10000,
    }
    with pytest.raises(ValueError, match="timeout"):
        old_select(old, schema, output, {}, timeout_seconds=56)
