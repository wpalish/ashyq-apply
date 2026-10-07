"""Public comparison rules mirror the original scope gate without filling evidence."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from evaluation.research.expert.compact import parse_compact_decision
from evaluation.research.expert.journal import AcceptedJournal, parse_journal_decision
from evaluation.research.expert.models import (
    QUESTION_DESCRIPTIONS,
    QUESTIONS,
    ExpertTrace,
    Proposal,
    QuestionFinding,
    _scope_findings,
)
from evaluation.research.expert.question_contract import (
    EFFECTIVE_JOURNAL_INSTRUCTIONS,
    question_contract,
    question_scope_diagnostics,
)

PRIVATE = "PRIVATE_INPUT_MUST_NOT_APPEAR"


def packet(**request_changes: Any) -> dict[str, Any]:
    return {
        "public_profile": {"education_system": "Example secondary system"},
        "cases": [
            {
                "case_id": "synthetic",
                "request": {
                    "university": "Example University",
                    "programme": None,
                    "degree": "bachelor",
                    "field": "computer science",
                    "intake": "fall 2030",
                    "population": None,
                    "qualification": None,
                    "academic_year": None,
                    **request_changes,
                },
            }
        ],
    }


def scope(**changes: Any) -> dict[str, Any]:
    return {
        "university": "Example University",
        "programme": "Literal Programme",
        "degree": "bachelor",
        "field": "computer science",
        "intake": "fall 2030",
        "population": "international",
        "qualification": "Example secondary system",
        "academic_year": "2030/2031",
        **changes,
    }


def fact(question: str = "Q3", **changes: Any) -> dict[str, Any]:
    return {
        "id": "synthetic_fact",
        "question": question,
        "claim_key": "unmapped.synthetic",
        "value_json": "false",
        "source_step": 1,
        "quotation": "Synthetic source statement only.",
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": scope(),
        **changes,
    }


def decision(
    question: str = "Q3",
    status: str = "found",
    *,
    finding_scope: dict[str, Any] | None = None,
    fact_scope: dict[str, Any] | None = None,
    compact: bool = False,
) -> Any:
    fs = scope() if finding_scope is None else finding_scope
    raw = {
        "kind": "submit",
        "observation": "Completed synthetic decision.",
        "action": None,
        "facts": [fact(question, scope=deepcopy(fs) if fact_scope is None else fact_scope)],
        "question_findings": [
            {
                "question": question,
                "status": status,
                "fact_ids": ["synthetic_fact"] if status in {"found", "not_published"} else [],
                "scope": fs,
                "observation": "Synthetic finding.",
                "supporting_steps": [1] if status == "inaccessible" else [],
            }
        ],
    }
    if compact:
        return parse_compact_decision(raw)
    return parse_journal_decision({**raw, "journal_sha256": AcceptedJournal.initial().sha256})


def gate_accepts(chosen: Any, public: dict[str, Any], retained: tuple[Any, ...] = ()) -> bool:
    """Call the actual target-scope validator, independently of mandatory source gates."""
    facts = {f.id: f for f in (*retained, *chosen.facts)}
    ordered = list(facts)
    proposals = [
        Proposal.model_validate(
            {
                "claim_key": f.claim_key,
                "value": False,
                "source_url": "https://example.invalid/source",
                "excerpt": "Synthetic source statement only.",
                "accessed_on": "2030-01-01",
                "scope": f.scope.model_dump(),
                "supporting_steps": [1],
            }
        )
        for f in facts.values()
    ]
    findings = []
    for finding in chosen.question_findings:
        ids = list(finding.fact_ids)
        findings.append(
            QuestionFinding.model_validate(
                {
                    "question": finding.question,
                    "status": finding.status,
                    "supporting_steps": [1] if ids or finding.status == "inaccessible" else [],
                    "proposal_indices": [ordered.index(i) for i in ids],
                    "evidence": [
                        {
                            "action_step": 1,
                            "source_url": "https://example.invalid/source",
                            "excerpt": "Synthetic source statement only.",
                            "location": {"kind": "text"},
                        }
                    ]
                    if ids
                    else [],
                    "scope": finding.scope.model_dump(),
                    "observation": "Synthetic scope-only test.",
                }
            )
        )
    trace = ExpertTrace.model_construct(
        case_id="synthetic",
        packet_sha256="0" * 64,
        baseline_pipeline_sha="synthetic-frozen",
        max_fetcher_calls=60,
        max_elapsed_ms=120000,
        initial_fetcher_calls=0,
        initial_elapsed_ms=0,
        started_at=datetime(2030, 1, 1, tzinfo=UTC),
        ended_at=datetime(2030, 1, 1, tzinfo=UTC),
        actions=[],
        question_findings=findings,
        proposals=proposals,
    )
    try:
        _scope_findings(trace, public["cases"][0], public["public_profile"])
    except ValueError:
        return False
    return True


@pytest.mark.parametrize("question", QUESTIONS)
@pytest.mark.parametrize("status", ["found", "not_published"])
def test_matching_synthetic_findings_match_original_validator(question: str, status: str) -> None:
    chosen, public = decision(question, status), packet()
    assert question_scope_diagnostics(chosen, public) == []
    assert gate_accepts(chosen, public)


REQUIRED = {
    "Q0": ("degree", "programme"),
    "Q1": ("degree", "population"),
    "Q2": ("degree", "population", "qualification"),
    "Q3": ("degree", "intake", "population"),
    "Q4": ("academic_year", "degree", "population"),
    "Q5": ("degree",),
    "Q6": ("degree", "population"),
}


@pytest.mark.parametrize(
    "question,field", [(q, f) for q, fields in REQUIRED.items() for f in fields]
)
@pytest.mark.parametrize("status", ["found", "not_published"])
def test_each_required_scope_dimension_agrees_with_actual_gate(
    question: str, field: str, status: str
) -> None:
    chosen, public = decision(question, status, finding_scope=scope(**{field: None})), packet()
    diagnostics = question_scope_diagnostics(chosen, public)
    assert any(
        d["question"] == question
        and d["field"] == field
        and d["reason"] == "required_scope_missing"
        and d["required"] is True
        and d["asserted"] is None
        for d in diagnostics
    )
    assert not gate_accepts(chosen, public)


def test_contract_exposes_all_questions_required_fields_and_literal_fallbacks() -> None:
    contract = question_contract(packet())
    assert list(contract["questions"]) == list(QUESTIONS)
    for question, fields in REQUIRED.items():
        assert contract["questions"][question]["required_scope"] == sorted(fields)
        assert contract["questions"][question]["description"] == QUESTION_DESCRIPTIONS[question]
    assert contract["expected_scope"]["population"] == "international"
    assert contract["expected_scope"]["qualification"] == "Example secondary system"
    assert contract["expected_scope"]["programme"] is None
    assert contract["fixed_degree"] == "bachelor"


def test_null_target_does_not_mean_required_programme_must_be_null() -> None:
    chosen = decision("Q0", finding_scope=scope(programme=None))
    item = next(
        d for d in question_scope_diagnostics(chosen, packet()) if d["field"] == "programme"
    )
    assert item["required"] is True
    assert item["constraint"] == "nonempty_source_supported_text"
    assert item["expected"] is None
    assert item["asserted"] is None
    assert not gate_accepts(chosen, packet())


@pytest.mark.parametrize(
    "population,qualification",
    [("Declared cohort", "Declared qualification"), ("", ""), (None, None)],
)
def test_fallbacks_match_truthiness_and_explicit_public_values(
    population: Any, qualification: Any
) -> None:
    public = packet(population=population, qualification=qualification)
    expected_population = population or "international"
    expected_qualification = qualification or "Example secondary system"
    contract = question_contract(public)
    assert contract["expected_scope"]["population"] == expected_population
    assert contract["expected_scope"]["qualification"] == expected_qualification
    chosen = decision(
        "Q2",
        finding_scope=scope(population=expected_population, qualification=expected_qualification),
    )
    assert question_scope_diagnostics(chosen, public) == []
    assert gate_accepts(chosen, public)


def test_unknown_public_education_system_is_not_invented_but_q2_requires_source_qualification() -> (
    None
):
    public = packet()
    public["public_profile"] = {}
    assert question_contract(public)["expected_scope"]["qualification"] is None
    chosen = decision("Q2", finding_scope=scope(qualification="Literal source qualification"))
    assert question_scope_diagnostics(chosen, public) == []
    assert gate_accepts(chosen, public)
    missing = decision("Q2", finding_scope=scope(qualification=None))
    assert question_scope_diagnostics(missing, public)
    assert not gate_accepts(missing, public)


@pytest.mark.parametrize(
    "field,value",
    [
        ("intake", "Fall 2030"),
        ("intake", "fall 2030 "),
        ("intake", "September 2030"),
        ("population", "International"),
        ("population", "non-EU/EEA"),
        ("qualification", "example secondary system"),
        ("field", "Computer Science"),
        ("university", "Example University "),
        ("degree", "Bachelor"),
    ],
)
def test_exact_target_comparison_does_not_trim_fold_or_infer_aliases(
    field: str, value: str
) -> None:
    chosen, public = decision(finding_scope=scope(**{field: value})), packet()
    diagnostics = question_scope_diagnostics(chosen, public)
    item = next(
        d for d in diagnostics if d["reason"] == "target_scope_mismatch" and d["field"] == field
    )
    assert item["asserted"] == value
    assert item["expected"] == question_contract(public)["expected_scope"][field]
    assert not gate_accepts(chosen, public)


def test_optional_nonnull_dimensions_are_compared_even_for_q5() -> None:
    chosen, public = (
        decision("Q5", finding_scope=scope(population="Literal narrower cohort")),
        packet(),
    )
    item = next(d for d in question_scope_diagnostics(chosen, public) if d["field"] == "population")
    assert item["required"] is False
    assert item["reason"] == "target_scope_mismatch"
    assert not gate_accepts(chosen, public)


def test_null_optional_scope_remains_null_and_is_not_filled_from_target() -> None:
    chosen = decision(
        "Q5",
        finding_scope=scope(
            population=None,
            qualification=None,
            intake=None,
            programme=None,
            field=None,
            academic_year=None,
        ),
    )
    before = chosen.model_dump(mode="json")
    assert question_scope_diagnostics(chosen, packet()) == []
    assert gate_accepts(chosen, packet())
    assert chosen.model_dump(mode="json") == before


def test_fixed_bachelor_rule_is_reported_separately_even_when_request_degree_matches() -> None:
    chosen, public = decision("Q5", finding_scope=scope(degree="master")), packet(degree="master")
    diagnostics = question_scope_diagnostics(chosen, public)
    assert [d["reason"] for d in diagnostics] == ["bachelor_scope_mismatch"]
    assert diagnostics[0]["expected"] == "bachelor"
    assert not gate_accepts(chosen, public)


@pytest.mark.parametrize(
    "academic_year,accepted",
    [
        ("2030/2031", True),
        ("2030/31", True),
        ("2030", True),
        ("Year: 2030", True),
        ("2029/2030", False),
        ("2031/32", False),
        ("No explicit year", False),
        ("30/31", False),
    ],
)
@pytest.mark.parametrize("status", ["found", "not_published"])
def test_q4_first_year_rule_matches_actual_gate_not_range_overlap(
    academic_year: str, accepted: bool, status: str
) -> None:
    chosen, public = (
        decision("Q4", status, finding_scope=scope(academic_year=academic_year)),
        packet(),
    )
    diagnostics = question_scope_diagnostics(chosen, public)
    assert bool(diagnostics) is not accepted
    assert gate_accepts(chosen, public) is accepted
    if not accepted:
        item = next(d for d in diagnostics if d["reason"] == "fee_first_year_mismatch")
        assert item["expected"] == {"first_year": "2030"}
        assert item["asserted"] == academic_year


def test_q4_explicit_requested_year_disables_fallback_first_intake_year_rule() -> None:
    public = packet(intake="fall 2032", academic_year="2030/2031")
    chosen = decision("Q4", finding_scope=scope(intake=None, academic_year="2030/2031"))
    assert question_contract(public)["q4_first_year_rule"]["enabled"] is False
    assert question_scope_diagnostics(chosen, public) == []
    assert gate_accepts(chosen, public)


def test_q4_no_request_intake_year_adds_no_guessed_year_requirement() -> None:
    public = packet(intake=None)
    chosen = decision("Q4", finding_scope=scope(intake=None, academic_year="Literal source year"))
    assert question_contract(public)["q4_first_year_rule"]["required_first_year"] is None
    assert question_scope_diagnostics(chosen, public) == []
    assert gate_accepts(chosen, public)


@pytest.mark.parametrize("status", ["unresolved", "inaccessible"])
def test_unsettled_findings_are_not_filled_or_subject_to_settlement_matching(status: str) -> None:
    chosen = decision(status=status, finding_scope=scope(degree=None, population=None, intake=None))
    assert question_scope_diagnostics(chosen, packet()) == []
    assert gate_accepts(chosen, packet())


@pytest.mark.parametrize("compact", [False, True])
def test_found_reference_scope_mismatch_identifies_fact_finding_and_field(compact: bool) -> None:
    chosen = decision(fact_scope=scope(population=None), compact=compact)
    item = next(d for d in question_scope_diagnostics(chosen, packet()) if d["target"] == "fact")
    assert item == {
        "target": "fact",
        "fact_id": "synthetic_fact",
        "source_step": 1,
        "finding_index": 0,
        "question": "Q3",
        "field": "population",
        "reason": "fact_finding_scope_mismatch",
        "required": True,
        "expected": "international",
        "asserted": None,
    }
    assert not gate_accepts(chosen, packet())


def test_not_published_reference_compatibility_remains_separate_original_journal_gate() -> None:
    chosen = decision(status="not_published", fact_scope=scope(population=None))
    assert question_scope_diagnostics(chosen, packet()) == []
    assert gate_accepts(chosen, packet())


def test_journal_delta_can_diagnose_retained_public_fact_without_regenerating_it() -> None:
    chosen = decision(fact_scope=scope(population=None))
    retained = tuple(chosen.facts)
    chosen.facts = []
    before = chosen.model_dump(mode="json"), retained[0].model_dump(mode="json")
    diagnostics = question_scope_diagnostics(chosen, packet(), retained_facts=retained)
    assert any(d.get("fact_id") == "synthetic_fact" for d in diagnostics)
    assert not gate_accepts(chosen, packet(), retained)
    assert (chosen.model_dump(mode="json"), retained[0].model_dump(mode="json")) == before


def test_missing_retained_reference_is_identified_without_inventing_fact_scope() -> None:
    chosen = decision()
    chosen.facts = []
    item = question_scope_diagnostics(chosen, packet())[0]
    assert item["reason"] == "referenced_fact_not_supplied"
    assert item["asserted"] == "synthetic_fact"


@pytest.mark.parametrize("compact", [False, True])
def test_models_are_revalidated_in_python_mode_without_coercing_mutated_types(
    compact: bool,
) -> None:
    chosen = decision(compact=compact)
    chosen.facts[0].source_step = True
    with pytest.raises(ValueError):
        question_scope_diagnostics(chosen, packet())


def test_single_effective_instruction_has_only_four_two_limits_and_local_evidence_rules() -> None:
    text = EFFECTIVE_JOURNAL_INSTRUCTIONS
    assert "at most4 NEW facts" in text and "at most2 NEW findings" in text
    assert "at most16" not in text and "at most7" not in text
    assert "scholarships.<public-award>" not in text
    for obligation in (
        "EVERY FACT'S",
        "Page title alone",
        "TARGET MATCHING",
        "Never copy an expected target",
        "immutable",
        "entire candidate is atomic",
        "page1-40",
        "context-only",
        "supporting_steps=[]",
        "unresolved",
    ):
        assert obligation in text
    assert len(text) < 4000


def test_contract_and_diagnostics_are_deterministic_fresh_and_nonmutating() -> None:
    public, chosen = packet(), decision(finding_scope=scope(population="Literal source cohort"))
    before = deepcopy(public), chosen.model_dump(mode="json")
    first = question_contract(public)
    first["expected_scope"]["population"] = "mutated output"
    first["questions"]["Q3"]["required_scope"].clear()
    assert question_contract(public)["expected_scope"]["population"] == "international"
    assert question_scope_diagnostics(chosen, public) == question_scope_diagnostics(chosen, public)
    assert (public, chosen.model_dump(mode="json")) == before


class AllowlistedMapping(Mapping[str, Any]):
    def __init__(self, visible: dict[str, Any]) -> None:
        self.visible = visible

    def __getitem__(self, key: str) -> Any:
        if key not in self.visible:
            raise AssertionError(f"Unexpected private key lookup: {key}")
        return self.visible[key]

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("Public contract must not enumerate private input")

    def __len__(self) -> int:
        return len(self.visible)


def test_packet_private_fields_are_neither_enumerated_read_nor_leaked() -> None:
    public = packet()
    raw_request = public["cases"][0]["request"]
    raw_request["gold"] = PRIVATE
    public["cases"][0]["baseline"] = {"predictions": PRIVATE}
    public["public_profile"]["private_notes"] = PRIVATE
    public["ground_truth"] = PRIVATE
    guarded = AllowlistedMapping(
        {
            "cases": [
                AllowlistedMapping(
                    {"case_id": "synthetic", "request": AllowlistedMapping(raw_request)}
                )
            ],
            "public_profile": AllowlistedMapping({"education_system": "Example secondary system"}),
        }
    )
    contract = question_contract(guarded)
    assert PRIVATE not in json.dumps(contract)
    assert PRIVATE not in json.dumps(question_scope_diagnostics(decision(), guarded))


def test_explicit_qualification_does_not_read_unused_education_system_fallback() -> None:
    public = packet(qualification="Literal explicit qualification")
    public["public_profile"] = AllowlistedMapping({})
    assert (
        question_contract(public)["expected_scope"]["qualification"]
        == "Literal explicit qualification"
    )


def test_fact_values_quotations_and_observations_do_not_enter_scope_feedback() -> None:
    chosen = decision(finding_scope=scope(intake="Literal other term"))
    chosen.observation = PRIVATE
    chosen.facts[0].quotation = PRIVATE
    chosen.facts[0].value_json = json.dumps({"secret": PRIVATE})
    assert PRIVATE not in json.dumps(question_scope_diagnostics(chosen, packet()))


@pytest.mark.parametrize(
    "changes",
    [
        {"cases": []},
        {"cases": [{}, {}]},
        {"cases": [None]},
        {"cases": "bad"},
        {"public_profile": None},
        {"public_profile": []},
    ],
)
def test_invalid_public_packet_shape_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        question_contract({**packet(), **changes})


@pytest.mark.parametrize(
    "field,value",
    [
        ("degree", True),
        ("population", 1),
        ("qualification", {}),
        ("intake", ["fall 2030"]),
        ("academic_year", "x" * 1001),
    ],
)
def test_target_values_are_strict_bounded_text_without_coercion(field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        question_contract(packet(**{field: value}))


@pytest.mark.parametrize("retained", [None, "bad", [{}]])
def test_retained_input_requires_bounded_original_public_fact_models(retained: Any) -> None:
    with pytest.raises(ValueError):
        question_scope_diagnostics(decision(), packet(), retained_facts=retained)


def test_duplicate_or_reused_retained_fact_ids_rejected_without_ambiguity() -> None:
    chosen = decision()
    retained = tuple(chosen.facts)
    with pytest.raises(ValueError):
        question_scope_diagnostics(chosen, packet(), retained_facts=retained)
    chosen.facts = []
    with pytest.raises(ValueError):
        question_scope_diagnostics(chosen, packet(), retained_facts=retained * 2)


def test_no_files_sources_or_private_registry_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Public scope contract performs no I/O")

    chosen, public = decision(), packet()
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    assert question_contract(public)
    assert question_scope_diagnostics(chosen, public) == []
