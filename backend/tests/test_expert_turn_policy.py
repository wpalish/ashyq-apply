"""V5 deltas and phase windows stay inside the original strict case clock."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from evaluation.research.expert.blind_cli import DISABLED_FEATURES, Isolation
from evaluation.research.expert.compact import SCOPE_DIMENSIONS
from evaluation.research.expert.journal import AcceptedJournal, JournalDecision
from evaluation.research.expert.representation import (
    CLOSING_OBSERVATION,
    closing_schema,
    journal_schema_for_case,
    parse_bound_journal_decision,
)
from evaluation.research.expert.turn_policy import (
    REASONING_OVERRIDE,
    AstraLowEffortIsolation,
    TurnPhase,
    command_proof,
    journal_schema_for_turn,
    parse_turn_decision,
    policy_card,
    policy_limits,
    turn_window,
)

HASH = AcceptedJournal.initial().sha256
UNIVERSITY = "Example Research University"


def scope(**changes: Any) -> dict[str, Any]:
    return {**dict.fromkeys(SCOPE_DIMENSIONS), "university": UNIVERSITY, **changes}


def fact(index: int) -> dict[str, Any]:
    return {
        "id": f"example_fact_{index}",
        "question": "OTHER",
        "claim_key": f"unmapped.example_{index}",
        "value_json": '{"value":false,"conditions":["example"]}',
        "source_step": 1,
        "quotation": "An exact synthetic source quotation.",
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": scope(),
    }


def finding(index: int) -> dict[str, Any]:
    return {
        "question": f"Q{index}",
        "status": "unresolved",
        "fact_ids": [],
        "scope": scope(university=None),
        "observation": "No matching synthetic source was established.",
        "supporting_steps": [],
    }


def decision(*, facts: int = 0, findings: int = 0, **changes: Any) -> dict[str, Any]:
    return {
        "kind": "submit",
        "observation": CLOSING_OBSERVATION,
        "journal_sha256": HASH,
        "action": None,
        "facts": [fact(index) for index in range(facts)],
        "question_findings": [finding(index) for index in range(findings)],
        **changes,
    }


def parse(value: Any, *, phase: TurnPhase = "data") -> JournalDecision:
    return parse_turn_decision(
        value,
        journal_sha256=HASH,
        canonical_university=UNIVERSITY,
        phase=phase,
    )


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
def test_bounded_schema_only_adds_delta_caps_to_the_existing_case_schema(phase: TurnPhase) -> None:
    original = journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY)
    schema = journal_schema_for_turn(
        journal_sha256=HASH, canonical_university=UNIVERSITY, phase=phase
    )
    assert schema["properties"]["facts"]["maxItems"] == 4
    assert schema["properties"]["question_findings"]["maxItems"] == 2
    restored = deepcopy(schema)
    restored["properties"]["facts"]["maxItems"] = 16
    restored["properties"]["question_findings"]["maxItems"] = 7
    assert restored == original
    assert journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY) == original


def test_minimal_schema_is_the_existing_zero_delta_hash_bound_closure() -> None:
    schema = journal_schema_for_turn(
        journal_sha256=HASH, canonical_university=UNIVERSITY, phase="minimal_commit"
    )
    assert schema == closing_schema(journal_sha256=HASH)
    assert schema["properties"]["facts"]["maxItems"] == 0
    assert schema["properties"]["question_findings"]["maxItems"] == 0


def test_schemas_and_limits_are_fresh_mappings() -> None:
    first = journal_schema_for_turn(
        journal_sha256=HASH, canonical_university=UNIVERSITY, phase="data"
    )
    first["properties"]["facts"]["maxItems"] = 100
    second = journal_schema_for_turn(
        journal_sha256="a" * 64, canonical_university="Other Example", phase="data"
    )
    assert second["properties"]["facts"]["maxItems"] == 4
    assert second["properties"]["journal_sha256"]["enum"] == ["a" * 64]
    assert second["$defs"]["CompactScope"]["properties"]["university"]["enum"] == [
        None,
        "Other Example",
    ]
    limits = policy_limits()
    limits["phase_cap_ms"]["data"] = 999999
    assert policy_limits()["phase_cap_ms"]["data"] == 55000


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
@pytest.mark.parametrize("representation", ["mapping", "json", "model"])
def test_four_facts_two_findings_preserve_types_and_unknown_scope(
    phase: TurnPhase, representation: str
) -> None:
    value: Any = decision(facts=4, findings=2)
    original = deepcopy(value)
    if representation == "json":
        value = json.dumps(value)
    elif representation == "model":
        value = JournalDecision.model_validate(value)
    parsed = parse(value, phase=phase)
    assert len(parsed.facts) == 4 and len(parsed.question_findings) == 2
    assert parsed.facts[0].decoded_value() == {"value": False, "conditions": ["example"]}
    assert parsed.question_findings[0].scope.model_dump() == dict.fromkeys(SCOPE_DIMENSIONS)
    assert parsed.model_dump(mode="json") == original


@pytest.mark.parametrize("phase", ["bootstrap", "data"])
@pytest.mark.parametrize("facts,findings", [(5, 0), (0, 3), (5, 3)])
def test_valid_legacy_deltas_over_v5_limits_are_rejected_without_truncation(
    phase: TurnPhase, facts: int, findings: int
) -> None:
    value = decision(facts=facts, findings=findings)
    original = deepcopy(value)
    legacy = parse_bound_journal_decision(
        value, journal_sha256=HASH, canonical_university=UNIVERSITY
    )
    assert len(legacy.facts) == facts and len(legacy.question_findings) == findings
    with pytest.raises(ValueError, match="four facts|two question findings"):
        parse(value, phase=phase)
    with pytest.raises(ValueError, match="four facts|two question findings"):
        parse(json.dumps(value), phase=phase)
    with pytest.raises(ValueError, match="four facts|two question findings"):
        parse(legacy, phase=phase)
    assert value == original and len(legacy.facts) == facts


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"journal_sha256": "a" * 64}, "exact current journal SHA"),
        ({"facts": [{**fact(0), "scope": scope(university="Other Example")}]}, "canonical"),
        ({"facts": [{**fact(0), "value_json": "NaN"}]}, "Non-JSON"),
        ({"facts": [{**fact(0), "quotation": " "}]}, "contain text"),
        ({"extra_field": 1}, "Extra inputs"),
    ],
)
def test_local_v5_parser_retains_original_strict_bindings(
    changes: dict[str, Any], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        parse({**decision(), **changes})


def test_duplicate_json_fields_and_mutated_input_models_are_revalidated() -> None:
    encoded = json.dumps(decision())
    duplicate = encoded.replace('"kind": "submit"', '"kind": "submit", "kind": "submit"')
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        parse(duplicate)
    model = parse(decision(facts=4))
    model.facts.append(model.facts[0].model_copy(update={"id": "fifth_fact"}))
    with pytest.raises(ValueError, match="four facts"):
        parse(model)


@pytest.mark.parametrize(
    "changes",
    [
        {"facts": [fact(0)]},
        {"question_findings": [finding(0)]},
        {"observation": "A regenerated completion statement."},
        {"kind": "record", "facts": [fact(0)]},
    ],
)
def test_minimal_phase_cannot_add_delta_or_regenerate_completion(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Hash-only closing"):
        parse({**decision(), **changes}, phase="minimal_commit")
    assert parse(decision(), phase="minimal_commit").model_dump(mode="json") == decision()


@pytest.mark.parametrize(
    "phase,active_ms,timeout_ms",
    [
        ("bootstrap", 0, 30000),
        ("data", 0, 55000),
        ("minimal_commit", 0, 10000),
        ("bootstrap", 77000, 30000),
        ("bootstrap", 77001, 29999),
        ("data", 52000, 55000),
        ("data", 52001, 54999),
        ("data", 106999, 1),
        ("bootstrap", 107000, None),
        ("data", 107000, None),
        ("minimal_commit", 107000, 10000),
        ("minimal_commit", 116999, 1),
        ("minimal_commit", 117000, None),
        ("data", 120005, None),
        ("minimal_commit", 120005, None),
    ],
)
def test_phase_windows_reserve_time_from_the_original_clock_without_rounding(
    phase: TurnPhase, active_ms: int, timeout_ms: int | None
) -> None:
    window = turn_window(phase=phase, active_ms=active_ms)
    assert window.active_ms == active_ms and window.timeout_ms == timeout_ms
    assert window.timeout_seconds == (None if timeout_ms is None else timeout_ms / 1000)
    assert window.status == ("no_available_window" if timeout_ms is None else "available")
    assert window.remaining_ms == 120000 - active_ms
    assert window.as_dict()["timeout_ms"] == timeout_ms
    if timeout_ms is not None:
        reserve = 3000 if phase == "minimal_commit" else 13000
        assert active_ms + timeout_ms + reserve <= 120000
    else:
        assert window.available_ms <= 0


def test_depleted_data_window_still_permits_only_reserved_minimal_commit() -> None:
    assert turn_window(phase="data", active_ms=108123).timeout_ms is None
    closure = turn_window(phase="minimal_commit", active_ms=108123)
    assert closure.timeout_ms == 8877 and closure.timeout_seconds == 8.877
    assert turn_window(phase="minimal_commit", active_ms=117001).timeout_ms is None


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None, -1])
def test_active_clock_must_be_a_nonnegative_exact_integer(invalid: Any) -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        turn_window(phase="data", active_ms=invalid)


@pytest.mark.parametrize("invalid", ["closing", "Data", " data", "", None, 0, True, []])
def test_unknown_or_coerced_phase_is_rejected_everywhere(invalid: Any) -> None:
    with pytest.raises(ValueError, match="phase"):
        turn_window(phase=invalid, active_ms=0)
    with pytest.raises(ValueError, match="phase"):
        journal_schema_for_turn(journal_sha256=HASH, canonical_university=UNIVERSITY, phase=invalid)
    with pytest.raises(ValueError, match="phase"):
        parse_turn_decision(
            decision(), journal_sha256=HASH, canonical_university=UNIVERSITY, phase=invalid
        )


def isolation(tmp_path: Path) -> AstraLowEffortIsolation:
    return AstraLowEffortIsolation(
        tmp_path / "isolated", (tmp_path / "sealed",), "/sandbox", "/codex"
    )


def test_low_effort_command_adds_only_the_exact_override_to_pinned_astra(tmp_path: Path) -> None:
    policy = isolation(tmp_path)
    schema, output = policy.workspace / "schema.json", policy.workspace / "answer.json"
    base = Isolation(policy.workspace, policy.sealed_roots, "/sandbox", "/codex").command(
        schema, output=output, model="gpt-6-astra"
    )
    command = policy.command(schema, output=output)
    assert command == [*base[:-1], "-c", 'model_reasoning_effort="low"', base[-1]]
    assert command == policy.command(schema, output=output, model="gpt-6-astra")
    assert command[-1] == "-" and "--ignore-user-config" in command
    for feature in DISABLED_FEATURES:
        assert command[command.index(feature) - 1] == "--disable"
    proof = command_proof(command)
    assert proof["command"] == command
    assert proof["model"] == "gpt-6-astra"
    assert proof["model_reasoning_effort"] == "low"
    assert proof["reasoning_override"] == REASONING_OVERRIDE
    encoded = json.dumps(command, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert proof["argv_sha256"] == hashlib.sha256(encoded.encode()).hexdigest()


@pytest.mark.parametrize("invalid", ["gpt-6-sol", "", "gpt-6-astra ", 1, False])
def test_wrapper_rejects_another_or_coerced_model(tmp_path: Path, invalid: Any) -> None:
    policy = isolation(tmp_path)
    with pytest.raises(ValueError, match="gpt-6-astra"):
        policy.command(
            policy.workspace / "schema", output=policy.workspace / "answer", model=invalid
        )


def test_inherited_local_factory_and_replace_preserve_low_effort_wrapper(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("evaluation.research.expert.blind_cli.shutil.which", lambda name: "/x")
    policy = AstraLowEffortIsolation.local(tmp_path / "isolated", [tmp_path / "sealed"])
    assert isinstance(policy, AstraLowEffortIsolation)
    changed = replace(policy, codex_executable="/new-codex")
    command = changed.command(changed.workspace / "schema", output=changed.workspace / "answer")
    assert command[3] == "/new-codex" and command[-2] == REASONING_OVERRIDE


def test_wrapper_preserves_confinement_and_fresh_output_guards(tmp_path: Path) -> None:
    policy = isolation(tmp_path)
    policy.workspace.mkdir()
    schema, output = policy.workspace / "schema", policy.workspace / "answer"
    with pytest.raises(ValueError, match="schema"):
        policy.command(tmp_path / "schema", output=output)
    with pytest.raises(ValueError, match="output"):
        policy.command(schema, output=tmp_path / "answer")
    output.write_text("synthetic stale output")
    with pytest.raises(ValueError, match="fresh"):
        policy.command(schema, output=output)
    output.unlink()
    output.symlink_to(policy.workspace / "nonexistent")
    with pytest.raises(ValueError, match="fresh"):
        policy.command(schema, output=output)


@pytest.mark.parametrize(
    "mutation", ["effort", "duplicate_effort", "model", "duplicate_model", "stdin"]
)
def test_command_proof_rejects_conflicting_or_incomplete_provenance(
    tmp_path: Path, mutation: str
) -> None:
    policy = isolation(tmp_path)
    command = policy.command(policy.workspace / "schema", output=policy.workspace / "answer")
    if mutation == "effort":
        command[command.index(REASONING_OVERRIDE)] = 'model_reasoning_effort="high"'
    elif mutation == "duplicate_effort":
        command[-1:-1] = ["-c", 'model_reasoning_effort = "high"']
    elif mutation == "model":
        command[command.index("--model") + 1] = "gpt-6-sol"
    elif mutation == "duplicate_model":
        command[-1:-1] = ["--model", "gpt-6-astra"]
    else:
        command.pop()
    with pytest.raises(ValueError, match="command|effort|Astra"):
        command_proof(command)


@pytest.mark.parametrize("invalid", ["-c low", [], ["x", 1], ["x", ""], None])
def test_command_proof_requires_exact_nonempty_argv(invalid: Any) -> None:
    with pytest.raises(ValueError, match="command"):
        command_proof(invalid)


def test_public_limits_card_and_proof_never_claim_a_new_budget(tmp_path: Path) -> None:
    limits = policy_limits()
    assert limits == {
        "policy_version": "1",
        "model": "gpt-6-astra",
        "model_reasoning_effort": "low",
        "max_ms": 120000,
        "max_calls": 60,
        "max_search_queries": 6,
        "source_deadline_ms": 95000,
        "max_new_facts": 4,
        "max_new_findings": 2,
        "mechanical_validation_reserve_ms": 3000,
        "minimal_commit_reserve_ms": 10000,
        "phase_cap_ms": {"bootstrap": 30000, "data": 55000, "minimal_commit": 10000},
    }
    card = policy_card()
    assert "four" in card and "two" in card and "120000" in card and "95000" in card
    assert "low" in card and "partial" in card.lower()
    policy = isolation(tmp_path)
    command = policy.command(policy.workspace / "schema", output=policy.workspace / "answer")
    proof = command_proof(command)
    cast(list[str], proof["command"]).append("synthetic mutation")
    assert command[-1] == "-"
