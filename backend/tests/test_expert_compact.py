"""Compact submissions conserve declared facts and use recorded source actions."""

from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from evaluation.research.expert.compact import (
    COMPACT_INSTRUCTIONS,
    CompactAction,
    compact_schema,
    expand_submission,
    parse_compact_decision,
)
from evaluation.research.expert.models import QUESTIONS, Action, validate_trace
from evaluation.research.expert.packet import digest

START = datetime(2026, 10, 4, tzinfo=UTC)
URL = "https://u.edu/admissions"
QUOTE = "International bachelor applicants need IELTS Academic overall 6.5."
DIMENSIONS = (
    "university",
    "programme",
    "degree",
    "field",
    "intake",
    "population",
    "qualification",
    "academic_year",
)


def scope(**changes: str | None) -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "university": "U",
        "programme": None,
        "degree": "bachelor",
        "field": None,
        "intake": None,
        "population": "international",
        "qualification": None,
        "academic_year": None,
    }
    return {**result, **changes}


def action(step: int = 1, **changes: Any) -> dict[str, Any]:
    result = {
        "step": step,
        "at": (START + timedelta(seconds=step)).isoformat(),
        "observed_before": "Read a public official admissions source.",
        "observed_from_step": step - 1 if step > 1 else None,
        "tool": "fetcher",
        "action": "Read the official page.",
        "outcome_status": "success",
        "outcome": "ok",
        "stage": "extraction",
        "policy_mode": "same_policy",
        "url": URL,
        "final_url": URL,
        "request": {"tool": "fetcher", "url": URL},
        "raw_log_path": f"action-{step:03}.json",
        "raw_log_sha256": "0" * 64,
        "elapsed_ms": 20,
        "fetcher_calls_cumulative": step,
        "search_queries_cumulative": 0,
        "elapsed_ms_cumulative": step * 20,
    }
    return {**result, **changes}


def fact(**changes: Any) -> dict[str, Any]:
    result = {
        "id": "english_overall",
        "question": "Q1",
        "claim_key": "ielts.overall",
        "value_json": "6.5",
        "source_step": 1,
        "quotation": QUOTE,
        "location": {
            "kind": "document_ir",
            "block_id": "b1",
            "section_path": ["International bachelor admissions"],
            "page": None,
        },
        "scope": scope(),
    }
    return {**result, **changes}


def finding(**changes: Any) -> dict[str, Any]:
    result = {
        "question": "Q1",
        "status": "found",
        "fact_ids": ["english_overall"],
        "scope": scope(),
        "observation": "The saved official page states this test minimum.",
        "supporting_steps": [],
    }
    return {**result, **changes}


def submission(**changes: Any) -> dict[str, Any]:
    result = {
        "kind": "submit",
        "observation": "Research ended with the following evidence.",
        "action": None,
        "facts": [fact()],
        "question_findings": [finding()],
    }
    return {**result, **changes}


def navigation_action(**changes: Any) -> dict[str, Any]:
    return {
        "tool": "fetcher",
        "url": URL,
        "query": None,
        "domains": [],
        "max_results": None,
        "source_step": None,
        "page": None,
        "offset": None,
        "section_offset": None,
        "link_offset": None,
        **changes,
    }


def expand(value: dict[str, Any], actions: list[Any] | None = None) -> dict[str, Any]:
    return expand_submission(
        parse_compact_decision(value),
        actions if actions is not None else [action()],
        ended_at=START + timedelta(seconds=10),
        case_id="u",
    )


def test_schema_has_single_root_and_explicit_eight_dimension_scope() -> None:
    schema = compact_schema()
    assert schema["type"] == "object"
    assert "oneOf" not in schema and "anyOf" not in schema
    assert set(schema["required"]) == {
        "kind",
        "observation",
        "action",
        "facts",
        "question_findings",
    }
    scopes = schema["$defs"]["CompactScope"]
    assert set(scopes["properties"]) == set(DIMENSIONS)
    assert set(scopes["required"]) == set(DIMENSIONS)
    assert scopes["additionalProperties"] is False
    for dimension in DIMENSIONS:
        assert {item["type"] for item in scopes["properties"][dimension]["anyOf"]} == {
            "string",
            "null",
        }
    assert "JSON-encoded" in COMPACT_INSTRUCTIONS
    assert "unresolved" in COMPACT_INSTRUCTIONS


def test_provider_schema_omits_uri_format_without_changing_local_httpurl_schema() -> None:
    provider = compact_schema()
    url_schema = provider["$defs"]["CompactAction"]["properties"]["url"]["anyOf"][0]
    assert "format" not in url_schema
    assert url_schema["type"] == "string"
    assert '"format": "uri"' not in json.dumps(provider)
    local = CompactAction.model_json_schema()
    assert local["properties"]["url"]["anyOf"][0]["format"] == "uri"


@pytest.mark.parametrize(
    "url", ["not a URL", "/admissions", "ftp://u.edu/fact", "javascript:alert(1)"]
)
def test_invalid_local_url_still_fails_after_provider_schema_projection(url) -> None:
    compact_schema()
    with pytest.raises(ValueError, match="url"):
        parse_compact_decision(
            json.dumps(
                {
                    "kind": "action",
                    "observation": "Read an official page.",
                    "action": navigation_action(url=url),
                    "facts": [],
                    "question_findings": [],
                }
            )
        )


def test_one_navigation_action_has_no_submission_fields() -> None:
    decision = parse_compact_decision(
        {
            "kind": "action",
            "observation": "The page links to an official admissions source.",
            "action": navigation_action(),
            "facts": [],
            "question_findings": [],
        }
    )
    assert decision.action is not None
    assert decision.action.controller_request() == {"tool": "fetcher", "url": URL}
    with pytest.raises(ValueError, match="submission"):
        expand_submission(decision, [action()], ended_at=START + timedelta(seconds=10))
    bad = decision.model_dump(mode="json")
    bad["facts"] = [fact()]
    with pytest.raises(ValueError, match="Navigation"):
        parse_compact_decision(bad)
    bad = submission(action=decision.action.model_dump(mode="json"))
    with pytest.raises(ValueError, match="submission"):
        parse_compact_decision(bad)


def test_search_navigation_is_one_explicit_controller_request() -> None:
    decision = parse_compact_decision(
        {
            "kind": "action",
            "observation": "Find a missing official qualification page.",
            "action": navigation_action(
                tool="search_provider",
                url=None,
                query="site:u.edu international secondary qualifications",
                domains=["u.edu"],
                max_results=6,
            ),
            "facts": [],
            "question_findings": [],
        }
    )
    assert decision.action is not None
    assert decision.action.controller_request() == {
        "tool": "search_provider",
        "query": "site:u.edu international secondary qualifications",
        "domains": ["u.edu"],
        "max_results": 6,
    }


def test_fetch_url_survives_json_input_and_strict_revalidation() -> None:
    value = {
        "kind": "action",
        "observation": "Read the official public programme page.",
        "action": navigation_action(),
        "facts": [],
        "question_findings": [],
    }
    parsed = parse_compact_decision(json.dumps(value))
    revalidated = parse_compact_decision(parsed.model_dump(mode="json"))
    assert revalidated.action is not None
    assert revalidated.action.controller_request() == {"tool": "fetcher", "url": URL}
    assert 'value_json="true"' in COMPACT_INSTRUCTIONS
    assert 'value_json="false"' in COMPACT_INSTRUCTIONS


def test_dates_and_final_source_url_come_from_the_exact_selected_action() -> None:
    selected = action(at="2026-10-03T23:55:00-02:00", final_url="https://u.edu/english")
    later = action(2, at="2026-10-04T02:00:01+00:00", final_url="https://u.edu/later")
    result = expand_submission(
        parse_compact_decision(submission()),
        [selected, later],
        ended_at=START + timedelta(hours=3),
        case_id="u",
    )
    proposal = result["proposals"][0]
    assert proposal["accessed_on"] == "2026-10-03"
    assert proposal["source_url"] == "https://u.edu/english"
    assert proposal["supporting_steps"] == [1]
    assert result["question_findings"][1]["evidence"][0]["source_url"] == proposal["source_url"]


def test_stored_view_carries_only_explicit_pagination_and_never_a_url() -> None:
    decision = parse_compact_decision(
        {
            "kind": "action",
            "observation": "Continue reading the saved PDF page.",
            "action": navigation_action(
                tool="view",
                url=None,
                source_step=3,
                page=2,
                offset=1200,
                section_offset=4,
                link_offset=20,
            ),
            "facts": [],
            "question_findings": [],
        }
    )
    assert decision.action is not None
    assert decision.action.controller_request() == {
        "tool": "view",
        "source_step": 3,
        "page": 2,
        "offset": 1200,
        "section_offset": 4,
        "link_offset": 20,
    }
    value = decision.model_dump(mode="json")
    value["action"]["url"] = URL
    with pytest.raises(ValueError, match="new fetch"):
        parse_compact_decision(value)
    value["action"]["url"] = None
    value["action"]["source_step"] = None
    with pytest.raises(ValueError, match="source_step"):
        parse_compact_decision(value)


@pytest.mark.parametrize(
    "changes",
    [
        {"tool": "search_provider"},
        {"tool": "internal_index"},
        {"policy_mode": "outside_policy"},
        {"outcome_status": "failure"},
        {"outcome_status": "blocked"},
        {"url": None, "final_url": None},
        {"at": "2026-10-05T00:00:00+00:00"},
        {"case_id": "foreign"},
    ],
)
def test_source_step_must_be_a_current_successful_same_policy_page_read(changes) -> None:
    with pytest.raises(ValueError):
        expand(submission(), [action(**changes)])


def test_missing_source_step_cannot_reference_another_cases_actions() -> None:
    with pytest.raises(ValueError, match="recorded"):
        expand(submission(facts=[fact(source_step=2)]))
    with pytest.raises(ValueError):
        expand(submission(facts=[fact(source_step=0)]))
    with pytest.raises(ValueError, match="timezone"):
        expand_submission(
            parse_compact_decision(submission()), [action()], ended_at=datetime(2026, 10, 4)
        )


def test_typed_action_input_and_raw_case_identity_are_supported() -> None:
    assert expand(submission(), [Action.model_validate(action())])["proposals"][0]["value"] == 6.5
    assert expand(submission(), [action(case_id="u")])["proposals"][0]["value"] == 6.5


def test_quotation_location_and_all_declared_scope_values_are_conserved() -> None:
    declared = scope(programme="BSc Computing", field="computing", population="nonresident")
    quotation = "  Original source\nspacing is preserved.  "
    location: dict[str, Any] = {"kind": "pdf", "block_id": None, "section_path": [], "page": 3}
    result = expand(
        submission(
            facts=[fact(question="OTHER", quotation=quotation, location=location, scope=declared)],
            question_findings=[],
        )
    )
    proposal = result["proposals"][0]
    assert proposal["excerpt"] == quotation
    assert proposal["scope"] == declared
    assert result["question_findings"][1]["status"] == "unresolved"
    result = expand(submission(facts=[fact(quotation=quotation, location=location)]))
    assert result["question_findings"][1]["evidence"][0]["location"] == location


@pytest.mark.parametrize("quotation", ["x" * 601, " ", "\t\n", "\u00a0\u2003"])
def test_empty_or_overlong_quotation_is_rejected(quotation) -> None:
    with pytest.raises(ValueError):
        parse_compact_decision(submission(facts=[fact(quotation=quotation)]))


@pytest.mark.parametrize(
    "value_json,expected",
    [
        ("false", False),
        ("true", True),
        ("null", None),
        ("0", 0),
        ("6.5", 6.5),
        ('"published"', "published"),
        ('["A", "B"]', ["A", "B"]),
        ('{"minimum":6.5,"optional":false}', {"minimum": 6.5, "optional": False}),
    ],
)
def test_json_encoded_values_preserve_their_types(value_json, expected) -> None:
    value = expand(submission(facts=[fact(value_json=value_json)]))["proposals"][0]["value"]
    assert value == expected
    assert type(value) is type(expected)


@pytest.mark.parametrize(
    "value_json", ["NaN", "Infinity", "-Infinity", "1e999", '{"a":1,"a":2}', False, {}]
)
def test_value_json_rejects_nonjson_native_values_and_last_wins_objects(value_json) -> None:
    with pytest.raises(ValueError):
        parse_compact_decision(submission(facts=[fact(value_json=value_json)]))


def test_root_json_duplicate_fields_are_rejected() -> None:
    raw = json.dumps(submission())
    raw = raw.replace('"kind": "submit"', '"kind":"action","kind":"submit"')
    with pytest.raises(ValueError, match="Duplicate"):
        parse_compact_decision(raw)


def test_explicit_false_programme_existence_is_never_changed_to_true() -> None:
    negative = fact(
        question="Q0",
        claim_key="programme.exists",
        value_json="false",
        quotation="BSc Computing is not offered as a bachelor programme.",
        scope=scope(programme="BSc Computing"),
    )
    result = expand(
        submission(
            facts=[negative],
            question_findings=[
                finding(
                    question="Q0",
                    scope=negative["scope"],
                )
            ],
        )
    )
    assert result["proposals"][0]["value"] is False
    assert result["proposals"][0]["claim_key"] == "programme.exists"


@pytest.mark.parametrize(
    "key",
    [
        "programme.language",
        "sat.policy",
        "subjects.mathematics.required",
        "country_credential.attestat.minimum",
        "english_evidence.toefl.minimum",
        "documents.admission.transcript",
        "mandatory_fees",
        "application_fee",
        "scholarships.declared-public-award.applicability.degree",
        "unmapped.award_observation",
    ],
)
def test_full_public_claim_namespace_is_kept_without_mapping_or_award_identity(key) -> None:
    result = expand(submission(facts=[fact(question="OTHER", claim_key=key)], question_findings=[]))
    assert result["proposals"][0]["claim_key"] == key
    assert all(item["status"] == "unresolved" for item in result["question_findings"])


def test_conflicting_facts_are_separate_and_cannot_be_silently_resolved() -> None:
    facts = [fact(), fact(id="alternative", value_json="7.0")]
    with pytest.raises(ValueError, match="conflict"):
        expand(submission(facts=facts))
    result = expand(
        submission(
            facts=facts,
            question_findings=[
                finding(
                    status="unresolved",
                    fact_ids=["english_overall", "alternative"],
                )
            ],
        )
    )
    assert [item["value"] for item in result["proposals"]] == [6.5, 7.0]
    assert result["question_findings"][1]["proposal_indices"] == [0, 1]


def test_found_finding_cannot_union_different_scopes_or_fill_a_missing_dimension() -> None:
    facts = [
        fact(),
        fact(id="domestic", claim_key="ielts.subscores", scope=scope(population="domestic")),
    ]
    with pytest.raises(ValueError, match="scope"):
        expand(
            submission(
                facts=facts, question_findings=[finding(fact_ids=["english_overall", "domestic"])]
            )
        )
    with pytest.raises(ValueError, match="scope"):
        expand(submission(facts=[fact(scope=scope(population=None))]))
    blank = scope(degree=None, population=None)
    result = expand(submission(facts=[fact(question="OTHER", scope=blank)], question_findings=[]))
    assert result["proposals"][0]["scope"] == blank


@pytest.mark.parametrize(
    "changes",
    [
        {"facts": [fact(), fact()]},
        {"question_findings": [finding(), finding()]},
        {"question_findings": [finding(fact_ids=["missing"])]},
        {"question_findings": [finding(question="Q2")]},
        {"question_findings": [finding(fact_ids=["english_overall", "english_overall"])]},
        {"facts": [fact(scope=scope(university=None))]},
    ],
)
def test_unique_ids_and_explicit_question_references_are_required(changes) -> None:
    with pytest.raises(ValueError):
        expand(submission(**changes))


def test_scope_nulls_must_be_explicit_and_model_source_metadata_is_rejected() -> None:
    value = submission()
    del value["facts"][0]["scope"]["qualification"]
    with pytest.raises(ValueError):
        parse_compact_decision(value)
    value = submission()
    value["facts"][0]["scope"]["nationality"] = "invented"
    with pytest.raises(ValueError):
        parse_compact_decision(value)
    for field, asserted in (
        ("source_url", "https://foreign.edu/fact"),
        ("accessed_on", "2099-01-01"),
    ):
        value = submission()
        value["facts"][0][field] = asserted
        with pytest.raises(ValueError):
            parse_compact_decision(value)


def test_empty_and_omitted_questions_synthesize_only_unresolved() -> None:
    result = expand(submission(facts=[], question_findings=[]))
    assert result["proposals"] == []
    assert [item["question"] for item in result["question_findings"]] == list(QUESTIONS)
    assert all(
        item["status"] == "unresolved" and not item["evidence"]
        for item in result["question_findings"]
    )
    assert all(item["scope"] == {} for item in result["question_findings"])


@pytest.mark.parametrize("status", ["found", "not_published", "inaccessible"])
def test_sparse_status_cannot_claim_absence_or_failure_without_evidence(status) -> None:
    with pytest.raises(ValueError):
        expand(submission(facts=[], question_findings=[finding(status=status, fact_ids=[])]))


def test_inaccessible_needs_failed_same_policy_page_steps_not_search_or_success() -> None:
    sparse = submission(
        facts=[],
        question_findings=[
            finding(
                status="inaccessible",
                fact_ids=[],
                supporting_steps=[1],
                observation="The recorded official page read failed.",
            )
        ],
    )
    attempts: tuple[dict[str, Any], ...] = (
        {},
        {"tool": "search_provider", "outcome_status": "failure"},
        {"policy_mode": "outside_policy", "outcome_status": "blocked"},
    )
    for changes in attempts:
        with pytest.raises(ValueError, match="failed"):
            expand(sparse, [action(**changes)])
    result = expand(sparse, [action(outcome_status="failure", outcome="action_timeout")])
    assert result["question_findings"][1]["supporting_steps"] == [1]
    assert result["question_findings"][1]["evidence"] == []
    with pytest.raises(ValueError):
        expand(submission(question_findings=[finding(status="inaccessible", supporting_steps=[1])]))


def trace_fixture(
    tmp_path: Path, submitted: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    html = f"<html><body><main><h1>International bachelor admissions</h1><p>{QUOTE}</p></main></body></html>"
    body = html.encode()
    recorded = action()
    raw_record = {
        "case_id": "u",
        "request": recorded["request"],
        "at": recorded["at"],
        "phase": "actions",
        "executed": True,
        "outcome_status": "success",
        "response": {
            "outcome": "ok",
            "outcome_status": "success",
            "ok": True,
            "status_code": 200,
            "final_url": URL,
            "content_type": "text/html",
            "fetch_tier": "http",
            "fetched_at": START.isoformat(),
            "error": "",
            "from_cache": False,
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "content_b64": base64.b64encode(body).decode(),
        },
        "elapsed_ms": 20,
        "elapsed_ms_cumulative": 20,
        "fetcher_calls_cumulative": 1,
        "search_queries_cumulative": 0,
        "policy_mode": "same_policy",
    }
    raw = json.dumps(raw_record).encode()
    (tmp_path / recorded["raw_log_path"]).write_bytes(raw)
    recorded["raw_log_sha256"] = hashlib.sha256(raw).hexdigest()
    packet = {
        "schema_version": "1",
        "baseline_pipeline_sha": "abcdef0123456789",
        "baseline_budget": {
            "max_fetcher_calls": 60,
            "max_elapsed_ms": 120000,
            "max_search_queries": 6,
            "browser_enabled": False,
        },
        "public_profile": {"education_system": "KZ national secondary"},
        "cases": [
            {
                "case_id": "u",
                "university": "U",
                "domain": "u.edu",
                "request": {
                    "university": "U",
                    "programme": None,
                    "degree": "bachelor",
                    "field": "computer science",
                    "intake": "fall 2027",
                    "population": None,
                    "qualification": None,
                    "academic_year": None,
                },
                "baseline": {},
            }
        ],
    }
    trace = {
        "case_id": "u",
        "packet_sha256": digest(packet),
        "baseline_pipeline_sha": packet["baseline_pipeline_sha"],
        "max_fetcher_calls": 60,
        "max_elapsed_ms": 120000,
        "max_search_queries": 6,
        "initial_fetcher_calls": 0,
        "initial_elapsed_ms": 0,
        "initial_search_queries": 0,
        "started_at": START.isoformat(),
        "ended_at": (START + timedelta(seconds=10)).isoformat(),
        "actions": [recorded],
        **expand(submitted, [recorded]),
        "review_status": "unreviewed",
    }
    return trace, packet


def test_expanded_submission_must_still_pass_raw_quote_and_location_validation(tmp_path) -> None:
    trace, packet = trace_fixture(tmp_path, submission())
    assert validate_trace(trace, packet, logs_dir=tmp_path).proposals[0].value == 6.5
    wrong_quote = deepcopy(trace)
    wrong_quote["proposals"][0]["excerpt"] = "IELTS overall 9.0 is required."
    wrong_quote["question_findings"][1]["evidence"][0]["excerpt"] = wrong_quote["proposals"][0][
        "excerpt"
    ]
    with pytest.raises(ValueError, match="quote"):
        validate_trace(wrong_quote, packet, logs_dir=tmp_path)
    wrong_location = deepcopy(trace)
    wrong_location["question_findings"][1]["evidence"][0]["location"]["block_id"] = "b999"
    with pytest.raises(ValueError, match="quote"):
        validate_trace(wrong_location, packet, logs_dir=tmp_path)


def test_not_published_requires_official_explicit_statement_at_trace_validation(tmp_path) -> None:
    trace, packet = trace_fixture(
        tmp_path, submission(question_findings=[finding(status="not_published")])
    )
    with pytest.raises(ValueError, match="publication statement"):
        validate_trace(trace, packet, logs_dir=tmp_path)
