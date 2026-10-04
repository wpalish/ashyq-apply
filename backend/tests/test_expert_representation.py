"""Bound public envelopes do not invent scope, accept sources or coerce values."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import JsonValue

from evaluation.research.expert.compact import (
    SCOPE_DIMENSIONS,
    CompactAction,
    CompactScope,
    parse_compact_decision,
)
from evaluation.research.expert.journal import (
    AcceptedJournal,
    journal_schema,
    parse_journal_decision,
)
from evaluation.research.expert.representation import (
    CLOSING_OBSERVATION,
    REPRESENTATION_VERSION,
    attributed_university,
    award_value,
    closing_prompt,
    closing_schema,
    journal_schema_for_case,
    parse_bound_journal_decision,
    representation_card,
    validate_award_subjects,
)
from evaluation.research.mapping import (
    AWARD_KEYS,
    CLAIM_KEYS,
    IELTS_BANDS,
    STRUCTURED_KEYS,
    normalize_claim,
)

HASH = AcceptedJournal.initial().sha256
UNIVERSITY = 'Example "Research" University'


def scope(**changes: Any) -> dict[str, Any]:
    return {**dict.fromkeys(SCOPE_DIMENSIONS), "university": UNIVERSITY, **changes}


def fact(**changes: Any) -> dict[str, Any]:
    return {
        "id": "synthetic_fact",
        "question": "OTHER",
        "claim_key": "unmapped.synthetic",
        "value_json": "false",
        "source_step": 1,
        "quotation": "A literal synthetic quotation.",
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": scope(),
        **changes,
    }


def decision(**changes: Any) -> dict[str, Any]:
    return {
        "kind": "submit",
        "observation": CLOSING_OBSERVATION,
        "journal_sha256": HASH,
        "action": None,
        "facts": [],
        "question_findings": [],
        **changes,
    }


def parse(value: Any, *, closing_only: bool = False) -> Any:
    return parse_bound_journal_decision(
        value,
        journal_sha256=HASH,
        canonical_university=UNIVERSITY,
        closing_only=closing_only,
    )


def test_university_attribution_returns_only_the_exact_proven_public_string() -> None:
    assert attributed_university(UNIVERSITY, source_attribution_proven=True) == UNIVERSITY
    assert attributed_university(UNIVERSITY, source_attribution_proven=False) is None
    assert attributed_university(" Example University ", source_attribution_proven=True) == (
        " Example University "
    )


@pytest.mark.parametrize("unproven", [None, 0, 1, "true", [], {}])
def test_attribution_proof_cannot_be_coerced(unproven: Any) -> None:
    with pytest.raises(ValueError, match="explicit boolean"):
        attributed_university(UNIVERSITY, source_attribution_proven=unproven)


@pytest.mark.parametrize("invalid", [None, "", " \t\n", 0, False])
def test_invalid_public_identity_is_rejected(invalid: Any) -> None:
    with pytest.raises(ValueError, match="public packet string"):
        attributed_university(invalid, source_attribution_proven=False)
    with pytest.raises(ValueError, match="public packet string"):
        representation_card(invalid)
    with pytest.raises(ValueError, match="public packet string"):
        journal_schema_for_case(journal_sha256=HASH, canonical_university=invalid)


def test_bound_schema_constrains_both_shared_scopes_and_preserves_the_original() -> None:
    original = journal_schema()
    original_scope = CompactScope.model_json_schema()
    bound = journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY)
    assert bound["properties"]["journal_sha256"]["enum"] == [HASH]
    assert bound["$defs"]["CompactScope"]["properties"]["university"]["enum"] == [None, UNIVERSITY]
    for name in ("CompactFact", "CompactFinding"):
        assert bound["$defs"][name]["properties"]["scope"]["$ref"] == "#/$defs/CompactScope"
    without_bindings = deepcopy(bound)
    without_bindings["properties"]["journal_sha256"].pop("enum")
    without_bindings["$defs"]["CompactScope"]["properties"]["university"].pop("enum")
    assert without_bindings == original
    assert journal_schema() == original
    assert CompactScope.model_json_schema() == original_scope
    assert CompactAction.model_json_schema()["properties"]["url"]["anyOf"][0]["format"] == "uri"


def test_case_bindings_do_not_mutate_other_cases_or_later_calls() -> None:
    first = journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY)
    first["properties"]["journal_sha256"]["enum"].append("b" * 64)
    first["$defs"]["CompactScope"]["properties"]["university"]["enum"].append("Foreign University")
    second = journal_schema_for_case(journal_sha256="a" * 64, canonical_university="Other Example")
    assert second["properties"]["journal_sha256"]["enum"] == ["a" * 64]
    assert second["$defs"]["CompactScope"]["properties"]["university"]["enum"] == [
        None,
        "Other Example",
    ]
    repeated = journal_schema_for_case(journal_sha256=HASH, canonical_university=UNIVERSITY)
    assert repeated["properties"]["journal_sha256"]["enum"] == [HASH]


@pytest.mark.parametrize(
    "bad_hash", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n", None]
)
def test_schema_and_prompt_reject_malformed_hashes(bad_hash: Any) -> None:
    with pytest.raises(ValueError, match="64 lowercase"):
        journal_schema_for_case(journal_sha256=bad_hash, canonical_university=UNIVERSITY)
    with pytest.raises(ValueError, match="64 lowercase"):
        closing_schema(journal_sha256=bad_hash)
    with pytest.raises(ValueError, match="64 lowercase"):
        closing_prompt(journal_sha256=bad_hash)


def test_null_unknown_scope_remains_null_and_is_not_filled_from_identity() -> None:
    finding = {
        "question": "Q3",
        "status": "unresolved",
        "fact_ids": [],
        "scope": scope(university=None),
        "observation": "No source-supported intake has been established.",
        "supporting_steps": [],
    }
    parsed = parse(decision(question_findings=[finding]))
    assert parsed.question_findings[0].scope.model_dump() == dict.fromkeys(SCOPE_DIMENSIONS)
    with pytest.raises(ValueError, match="university"):
        parse(decision(facts=[fact(scope=scope(university=None))]))


@pytest.mark.parametrize("where", ["fact", "finding"])
@pytest.mark.parametrize("foreign", ["Foreign University", "example university", UNIVERSITY + " "])
def test_local_bindings_reject_foreign_or_normalized_university(where: str, foreign: str) -> None:
    value = decision()
    if where == "fact":
        value["facts"] = [fact(scope=scope(university=foreign))]
    else:
        value["question_findings"] = [
            {
                "question": "Q0",
                "status": "unresolved",
                "fact_ids": [],
                "scope": scope(university=foreign),
                "observation": "Synthetic uncertainty.",
                "supporting_steps": [],
            }
        ]
    with pytest.raises(ValueError, match="exact public canonical"):
        parse(value)


def test_valid_but_stale_hash_is_rejected_locally() -> None:
    with pytest.raises(ValueError, match="exact current journal SHA"):
        parse(decision(journal_sha256="a" * 64))


@pytest.mark.parametrize(
    "raw_value",
    ["false", "true", "0", "0.0", '"0"', "null", "[1,false]", '{"condition":"example"}'],
)
def test_existing_json_values_remain_typed_and_unchanged(raw_value: str) -> None:
    value = decision(facts=[fact(value_json=raw_value)])
    original = deepcopy(value)
    parsed = parse(value)
    assert parsed.facts[0].value_json == raw_value
    decoded, expected = parsed.facts[0].decoded_value(), json.loads(raw_value)
    assert decoded == expected and type(decoded) is type(expected)
    assert value == original


def test_literal_programme_degree_and_field_are_independent() -> None:
    source_scope = scope(programme="Example Computing", degree="bachelor", field=None)
    parsed = parse(
        decision(facts=[fact(claim_key="programme.exists", value_json="true", scope=source_scope)])
    )
    assert parsed.facts[0].scope.programme == "Example Computing"
    assert parsed.facts[0].scope.degree == "bachelor"
    assert parsed.facts[0].scope.field is None


def test_historical_fact_is_preserved_as_other_without_a_requested_intake() -> None:
    parsed = parse(
        decision(
            facts=[
                fact(
                    claim_key="deadline",
                    value_json='"2030-03-15"',
                    scope=scope(intake="fall 2030", academic_year=None),
                )
            ]
        )
    )
    assert parsed.facts[0].question == "OTHER"
    assert parsed.facts[0].decoded_value() == "2030-03-15"
    assert parsed.facts[0].scope.intake == "fall 2030"
    assert parsed.question_findings == []


@pytest.mark.parametrize(
    "location",
    [
        {"kind": "text", "block_id": None, "section_path": [], "page": None},
        {
            "kind": "document_ir",
            "block_id": "b1",
            "section_path": ["Example section"],
            "page": None,
        },
        {"kind": "pdf", "block_id": None, "section_path": [], "page": 40},
    ],
)
def test_original_quote_coordinates_are_preserved(location: dict[str, Any]) -> None:
    parsed = parse(decision(facts=[fact(location=location)]))
    assert parsed.facts[0].location.model_dump() == location


@pytest.mark.parametrize(
    "location",
    [
        {"kind": "document_ir", "block_id": None, "section_path": [], "page": None},
        {"kind": "pdf", "block_id": None, "section_path": [], "page": None},
        {"kind": "pdf", "block_id": None, "section_path": [], "page": 0},
        {"kind": "pdf", "block_id": None, "section_path": [], "page": 41},
        {"kind": "text", "block_id": "b1", "section_path": [], "page": None},
    ],
)
def test_original_location_rejections_are_not_weakened(location: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        parse(decision(facts=[fact(location=location)]))


def test_bound_parse_is_not_a_source_or_journal_acceptance_gate() -> None:
    parsed = parse(decision(facts=[fact(source_step=999)]))
    journal = AcceptedJournal.initial()
    before = journal.snapshot()
    with pytest.raises(ValueError):
        journal.candidate(
            parsed, [], ended_at=datetime(2030, 1, 1, tzinfo=UTC), case_id="synthetic"
        )
    assert journal.snapshot() == before


def test_card_uses_public_contracts_and_explicit_synthetic_transport_examples() -> None:
    card = representation_card(UNIVERSITY)
    assert REPRESENTATION_VERSION in card and json.dumps(UNIVERSITY) in card
    assert "not admissions facts" in card and "university remains null" in card
    assert "literal programme title" in card and "OTHER" in card
    assert "page1-40" in card and "exact block_id and section_path" in card
    assert "Full\njournal, raw-log, quotation, location and scope validation" in card
    for input_key, output_key in CLAIM_KEYS.items():
        assert json.dumps(input_key) + ":" + json.dumps(output_key) in card
    for input_key, (template, names, field) in STRUCTURED_KEYS.items():
        assert input_key in card and template in card
        assert all(name in card for name in (*names, field))
    mapped = normalize_claim("ielts_min_subscore", {"normalized_value": 6.0})
    assert mapped[1] == {band: 6.0 for band in IELTS_BANDS}
    assert json.dumps(mapped[1], separators=(",", ":")) in card
    assert "https://" not in card and "http://" not in card
    assert len(card) < 7000


def test_closing_schema_is_only_the_original_six_fields_without_large_definitions() -> None:
    schema = closing_schema(journal_sha256=HASH)
    properties = schema["properties"]
    assert set(properties) == set(decision()) == set(schema["required"])
    assert schema["additionalProperties"] is False and "$defs" not in schema
    assert properties["kind"]["enum"] == ["submit"]
    assert properties["observation"]["enum"] == [CLOSING_OBSERVATION]
    assert properties["journal_sha256"]["enum"] == [HASH]
    assert properties["action"] == {"type": "null"}
    for field in ("facts", "question_findings"):
        assert properties[field]["type"] == "array" and properties[field]["maxItems"] == 0
    assert len(json.dumps(schema)) < 1200
    schema["properties"]["journal_sha256"]["enum"].append("b" * 64)
    assert closing_schema(journal_sha256=HASH)["properties"]["journal_sha256"]["enum"] == [HASH]


def test_closing_prompt_cannot_receive_sources_case_packet_or_ontology() -> None:
    prompt = closing_prompt(journal_sha256=HASH)
    assert set(prompt) == {"task", "journal_sha256"} and prompt["journal_sha256"] == HASH
    assert "facts=[]" in prompt["task"] and "question_findings=[]" in prompt["task"]
    assert "action=null" in prompt["task"] and CLOSING_OBSERVATION in prompt["task"]
    assert len(json.dumps(prompt)) < 650
    assert UNIVERSITY not in json.dumps(prompt)


def test_minimal_closing_is_an_original_empty_submit_not_a_new_protocol_model() -> None:
    parsed = parse(decision(), closing_only=True)
    assert parsed == parse_journal_decision(decision())
    journal = AcceptedJournal.initial()
    current = journal.candidate(
        parsed, [], ended_at=datetime(2030, 1, 1, tzinfo=UTC), case_id="synthetic"
    )
    assert current.snapshot() == journal.snapshot()


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "record"},
        {"observation": "Regenerate source evidence."},
        {"facts": [fact()]},
        {
            "question_findings": [
                {
                    "question": "Q3",
                    "status": "unresolved",
                    "fact_ids": [],
                    "scope": scope(),
                    "observation": "Synthetic unknown.",
                    "supporting_steps": [],
                }
            ]
        },
        {
            "action": {
                "tool": "view",
                "url": None,
                "query": None,
                "domains": [],
                "max_results": None,
                "source_step": 1,
                "page": None,
                "offset": None,
                "section_offset": None,
                "link_offset": None,
            }
        },
        {"extra": "untrusted"},
    ],
)
def test_local_closing_rejects_any_action_delta_or_shape_change(change: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        parse(decision(**change), closing_only=True)


def test_duplicate_json_and_model_proof_fields_remain_invalid() -> None:
    raw = json.dumps(decision()).replace('"kind": "submit"', '"kind":"submit","kind":"submit"')
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        parse(raw, closing_only=True)
    with pytest.raises(ValueError):
        parse(decision(source_attribution_proven=True))


def test_closing_mode_is_not_coerced() -> None:
    invalid_mode: Any = 1
    with pytest.raises(ValueError, match="explicit boolean"):
        parse_bound_journal_decision(
            decision(),
            journal_sha256=HASH,
            canonical_university=UNIVERSITY,
            closing_only=invalid_mode,
        )


@pytest.mark.parametrize("key", [*AWARD_KEYS, "scholarship_coverage"])
def test_public_award_wrapper_preserves_subject_and_original_typed_value(key: str) -> None:
    published: JsonValue = {
        "amount": 123,
        "currency": "EXAMPLE",
        "conditions": ["synthetic"],
        "applies": False,
    }
    wrapper: JsonValue = {"subject": "Example Merit Award", "value": published}
    result = award_value(key, wrapper)
    assert result == ("Example Merit Award", published)
    assert wrapper == {"subject": "Example Merit Award", "value": published}
    parsed = parse(decision(facts=[fact(claim_key=key, value_json=json.dumps(wrapper))]))
    assert award_value(parsed.facts[0].claim_key, parsed.facts[0].decoded_value()) == result


@pytest.mark.parametrize(
    "published", [False, 0, 1.5, "conditional text", None, ["example"], {"condition": "example"}]
)
def test_award_published_value_has_no_invented_scalar_type(published: Any) -> None:
    result = award_value(
        "scholarship_amount", {"subject": "Example Merit Award", "value": published}
    )
    assert result is not None
    assert result[1] == published and type(result[1]) is type(published)


@pytest.mark.parametrize(
    "invalid",
    [
        "Example Merit Award",
        {},
        {"value": 123},
        {"subject": "Example Merit Award"},
        {"subject": "Example Merit Award", "value": 123, "extra": "private"},
        {"subject": "", "value": 123},
        {"subject": " \n", "value": 123},
        {"subject": True, "value": 123},
        {"subject": None, "value": 123},
    ],
)
def test_invalid_award_wrapper_is_rejected_even_for_other_unreferenced_fact(invalid: Any) -> None:
    with pytest.raises(ValueError):
        award_value("scholarship_amount", invalid)
    with pytest.raises(ValueError):
        parse(
            decision(facts=[fact(claim_key="scholarship_amount", value_json=json.dumps(invalid))])
        )


def test_award_existence_is_the_source_name_not_a_boolean_or_wrapper() -> None:
    assert award_value("scholarship_exists", "Example Merit Award") == (
        "Example Merit Award",
        "Example Merit Award",
    )
    invalid_values: tuple[JsonValue, ...] = (
        True,
        "",
        " ",
        {"subject": "Example Merit Award", "value": True},
    )
    for value in invalid_values:
        with pytest.raises(ValueError):
            award_value("scholarship_exists", value)


def test_subject_spelling_is_never_normalized_and_guessed_private_ids_fail() -> None:
    subject = "Example Merit Award"
    assert award_value("scholarship_amount", {"subject": subject, "value": False}) == (
        subject,
        False,
    )
    assert award_value("ielts.overall", 6.0) is None
    with pytest.raises(ValueError, match="guessed scholarships"):
        parse(decision(facts=[fact(claim_key="scholarships.guessed.exists", value_json="true")]))


def test_award_subject_proof_covers_every_other_and_unreferenced_fact() -> None:
    first, second = "Example Merit Award", "Example Access Award"
    parsed = parse(
        decision(
            facts=[
                fact(id="award", claim_key="scholarship_exists", value_json=json.dumps(first)),
                fact(
                    id="amount",
                    claim_key="scholarship_amount",
                    value_json=json.dumps({"subject": second, "value": False}),
                ),
            ]
        )
    )
    contexts = {"award": first + " is offered.", "amount": second + " has conditional support."}
    proof = validate_award_subjects(parsed, contexts_by_fact_id=contexts)
    assert [entry["fact_id"] for entry in proof] == ["award", "amount"]
    assert [entry["literal_subject"] for entry in proof] == [first, second]
    assert proof[1]["context_sha256"] == hashlib.sha256(contexts["amount"].encode()).hexdigest()
    assert proof[0]["subject_sha256"] == hashlib.sha256(first.encode()).hexdigest()
    assert proof[0]["location"] == parsed.facts[0].location.model_dump(mode="json")
    journal_model = parsed
    compact_model = AcceptedJournal.initial().as_submission()
    assert validate_award_subjects(compact_model, contexts_by_fact_id={}) == []
    compact_model = parse_compact_decision(
        {
            key: value
            for key, value in parsed.model_dump(mode="json").items()
            if key != "journal_sha256"
        }
    )
    assert validate_award_subjects(compact_model, contexts_by_fact_id=contexts) == proof
    assert validate_award_subjects(journal_model, contexts_by_fact_id=contexts) == proof


@pytest.mark.parametrize(
    "context", [None, "", "example merit award", "Example  Merit Award", "Different Award"]
)
def test_subject_proof_requires_exact_selected_context_substring(context: Any) -> None:
    parsed = parse(
        decision(facts=[fact(claim_key="scholarship_exists", value_json='"Example Merit Award"')])
    )
    with pytest.raises(ValueError, match="validated selected context"):
        validate_award_subjects(parsed, contexts_by_fact_id={"synthetic_fact": context})


def test_source_step_alone_or_other_block_context_cannot_prove_subject() -> None:
    parsed = parse(
        decision(facts=[fact(claim_key="scholarship_exists", value_json='"Example Merit Award"')])
    )
    with pytest.raises(ValueError):
        validate_award_subjects(parsed, contexts_by_fact_id={"other_fact": "Example Merit Award"})
    with pytest.raises(ValueError):
        validate_award_subjects(
            parsed, contexts_by_fact_id={"synthetic_fact": "Another award's selected block."}
        )


def test_award_card_exposes_literal_shapes_and_no_private_subject_binding() -> None:
    card = representation_card(UNIVERSITY)
    assert "exactly" in card and '"subject":"verbatim official award name"' in card
    assert "case-sensitive substring" in card and "after sealing" in card
    assert "No private award IDs or scholarships.* keys may be guessed" in card
    for key in (*AWARD_KEYS, "scholarship_coverage", "scholarship_exists"):
        assert key in card


def test_later_invalid_subject_fails_the_whole_check_without_mutating_input() -> None:
    parsed = parse(
        decision(
            facts=[
                fact(
                    id="first", claim_key="scholarship_exists", value_json='"Example Merit Award"'
                ),
                fact(
                    id="second", claim_key="scholarship_exists", value_json='"Example Access Award"'
                ),
            ]
        )
    )
    before = parsed.model_dump(mode="json")
    with pytest.raises(ValueError):
        validate_award_subjects(
            parsed,
            contexts_by_fact_id={
                "first": "Example Merit Award is offered.",
                "second": "An unrelated selected block.",
            },
        )
    assert parsed.model_dump(mode="json") == before


@pytest.mark.parametrize("invalid", [float("inf"), float("nan"), b"not JSON"])
def test_direct_award_adapter_still_requires_finite_typed_json(invalid: Any) -> None:
    with pytest.raises(ValueError):
        award_value("scholarship_amount", {"subject": "Example Merit Award", "value": invalid})
