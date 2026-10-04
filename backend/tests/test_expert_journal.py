"""Append-only selector checkpoints retain explicit, independently cited facts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from evaluation.research.expert.compact import CompactAction, expand_submission
from evaluation.research.expert.journal import (
    JOURNAL_INSTRUCTIONS,
    AcceptedJournal,
    journal_schema,
    parse_journal_decision,
)
from evaluation.research.expert.models import QUESTIONS, Action

START = datetime(2026, 10, 4, tzinfo=UTC)
END = START + timedelta(seconds=10)
URL = "https://u.edu/admissions"
QUOTE = "International bachelor applicants need IELTS Academic overall 6.5."


def scope(**changes: str | None) -> dict[str, str | None]:
    return {
        "university": "U",
        "programme": None,
        "degree": "bachelor",
        "field": None,
        "intake": None,
        "population": "international",
        "qualification": None,
        "academic_year": None,
        **changes,
    }


def action(step: int = 1, **changes: Any) -> dict[str, Any]:
    return {
        "step": step,
        "at": (START + timedelta(seconds=step)).isoformat(),
        "observed_before": "Read an official public page.",
        "observed_from_step": step - 1 if step > 1 else None,
        "tool": "fetcher",
        "action": "Read an official source.",
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
        **changes,
    }


def fact(**changes: Any) -> dict[str, Any]:
    return {
        "id": "english_overall",
        "question": "Q1",
        "claim_key": "ielts.overall",
        "value_json": "6.5",
        "source_step": 1,
        "quotation": QUOTE,
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": scope(),
        **changes,
    }


def finding(**changes: Any) -> dict[str, Any]:
    return {
        "question": "Q1",
        "status": "found",
        "fact_ids": ["english_overall"],
        "scope": scope(),
        "observation": "The official page states the test minimum.",
        "supporting_steps": [],
        **changes,
    }


def navigation(**changes: Any) -> dict[str, Any]:
    return {
        "tool": "fetcher",
        "url": "https://u.edu/qualifications",
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


def decision(journal: AcceptedJournal, **changes: Any) -> dict[str, Any]:
    return {
        "kind": "record",
        "observation": "Record the explicitly supported fact.",
        "journal_sha256": journal.sha256,
        "action": None,
        "facts": [fact()],
        "question_findings": [],
        **changes,
    }


def candidate(
    journal: AcceptedJournal, value: Any, actions: list[Any] | None = None
) -> AcceptedJournal:
    return journal.candidate(
        value, actions if actions is not None else [action()], ended_at=END, case_id="u"
    )


def canonical_hash(snapshot: dict[str, Any]) -> str:
    payload = {"facts": snapshot["facts"], "question_findings": snapshot["question_findings"]}
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def test_initial_journal_hash_and_snapshot_are_deterministic_without_timestamp() -> None:
    first, second = AcceptedJournal.initial(), AcceptedJournal.initial()
    expected = hashlib.sha256(b'{"facts":[],"question_findings":[]}').hexdigest()
    assert first.sha256 == second.sha256 == expected
    assert first.snapshot() == {
        "schema_version": "1",
        "journal_sha256": expected,
        "facts": [],
        "question_findings": [],
    }
    assert first.as_submission().kind == "submit"
    assert not first.as_submission().facts
    assert not first.as_submission().question_findings
    assert (
        first.as_submission(observation="A different closing observation.").observation
        != second.as_submission().observation
    )
    assert first.sha256 == expected


def test_provider_schema_is_one_root_object_and_preserves_local_httpurl() -> None:
    schema = journal_schema()
    assert schema["type"] == "object"
    assert "anyOf" not in schema and "oneOf" not in schema
    assert set(schema["required"]) == {
        "kind",
        "observation",
        "journal_sha256",
        "action",
        "facts",
        "question_findings",
    }
    assert schema["additionalProperties"] is False
    assert schema["properties"]["facts"]["maxItems"] == 16
    assert schema["properties"]["question_findings"]["maxItems"] == 7
    assert '"format": "uri"' not in json.dumps(schema)
    assert CompactAction.model_json_schema()["properties"]["url"]["anyOf"][0]["format"] == "uri"


def test_two_deltas_reference_retained_facts_without_resubmitting_quotes() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty))
    assert empty.snapshot()["facts"] == []
    second = candidate(first, decision(first, facts=[], question_findings=[finding()]))
    submission = second.as_submission()
    assert len(submission.facts) == 1
    assert submission.facts[0].quotation == QUOTE
    assert submission.question_findings[0].fact_ids == ["english_overall"]
    expanded = expand_submission(submission, [action()], ended_at=END, case_id="u")
    assert expanded["question_findings"][1]["proposal_indices"] == [0]
    assert expanded["question_findings"][1]["supporting_steps"] == [1]
    assert len(first.as_submission().question_findings) == 0
    assert empty.sha256 != first.sha256 != second.sha256


def test_action_may_checkpoint_a_delta_before_choosing_one_next_controlled_action() -> None:
    empty = AcceptedJournal.initial()
    value = decision(empty, kind="action", action=navigation())
    parsed = parse_journal_decision(json.dumps(value))
    assert parsed.action is not None
    assert parsed.action.controller_request() == {
        "tool": "fetcher",
        "url": "https://u.edu/qualifications",
    }
    first = candidate(empty, parsed)
    assert len(first.as_submission().facts) == 1
    unchanged = candidate(first, decision(first, kind="action", action=navigation(), facts=[]))
    assert unchanged.sha256 == first.sha256


def test_view_must_reference_a_recorded_step_and_cannot_observe_its_upcoming_action() -> None:
    empty = AcceptedJournal.initial()
    value = decision(
        empty,
        kind="action",
        facts=[],
        action=navigation(
            tool="view",
            url=None,
            source_step=1,
            page=2,
            offset=20,
        ),
    )
    assert candidate(empty, value).sha256 == empty.sha256
    value["action"]["source_step"] = 2
    with pytest.raises(ValueError, match="recorded"):
        candidate(empty, value)


def test_short_final_commit_retains_prior_data_without_regenerating_it() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, question_findings=[finding()]))
    final = candidate(
        first, decision(first, kind="submit", facts=[], observation="Commit the accepted journal.")
    )
    assert final.sha256 == first.sha256
    assert final.snapshot() == first.snapshot()
    assert len(final.as_submission().facts) == 1
    assert len(final.as_submission().question_findings) == 1
    closed = expand_submission(final.as_submission(), [action()], ended_at=END, case_id="u")
    assert [item["question"] for item in closed["question_findings"]] == list(QUESTIONS)
    assert all(
        item["status"] == "unresolved"
        for item in closed["question_findings"]
        if item["question"] != "Q1"
    )


def test_stale_sha_rejects_even_a_short_final_commit_atomically() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty))
    before = first.snapshot()
    with pytest.raises(ValueError, match="SHA"):
        candidate(first, decision(empty, kind="submit", facts=[]))
    assert first.snapshot() == before


@pytest.mark.parametrize("hash_value", ["", "A" * 64, "g" * 64, "0" * 63])
def test_prior_sha_requires_exact_lowercase_hex(hash_value) -> None:
    empty = AcceptedJournal.initial()
    with pytest.raises(ValueError):
        parse_journal_decision(decision(empty, journal_sha256=hash_value))


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "action"},
        {"kind": "record", "action": navigation()},
        {"kind": "submit", "action": navigation()},
        {"facts": [], "question_findings": []},
        {"facts": [fact(), fact()]},
        {"question_findings": [finding(), finding()]},
        {"facts": [fact(id=f"f{index}") for index in range(17)]},
    ],
)
def test_decision_shape_duplicates_and_delta_bound_are_strict(changes) -> None:
    with pytest.raises(ValueError):
        parse_journal_decision(decision(AcceptedJournal.initial(), **changes))


@pytest.mark.parametrize("extra", ["trace", "source_url", "accepted", "timestamp"])
def test_unknown_decision_fields_are_rejected(extra) -> None:
    value = decision(AcceptedJournal.initial())
    value[extra] = "unsupported"
    with pytest.raises(ValueError):
        parse_journal_decision(value)


def test_duplicate_json_fields_and_value_objects_are_not_last_wins() -> None:
    value = json.dumps(decision(AcceptedJournal.initial()))
    value = value.replace('"kind": "record"', '"kind":"submit","kind":"record"')
    with pytest.raises(ValueError, match="Duplicate"):
        parse_journal_decision(value)
    with pytest.raises(ValueError, match="Duplicate"):
        parse_journal_decision(
            decision(AcceptedJournal.initial(), facts=[fact(value_json='{"a":1,"a":2}')])
        )


def test_repeated_fact_id_is_rejected_even_if_identical_and_entire_delta_is_atomic() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty))
    before = first.snapshot()
    with pytest.raises(ValueError, match="fact ID"):
        candidate(
            first, decision(first, facts=[fact(id="new_fact", claim_key="ielts.subscores"), fact()])
        )
    assert first.snapshot() == before
    assert [item.id for item in first.as_submission().facts] == ["english_overall"]


@pytest.mark.parametrize(
    "old_status,new_status", [("found", "unresolved"), ("unresolved", "found"), ("found", "found")]
)
def test_repeated_findings_cannot_change_or_downgrade_accepted_questions(
    old_status, new_status
) -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, question_findings=[finding(status=old_status)]))
    before = first.snapshot()
    with pytest.raises(ValueError, match="question"):
        candidate(first, decision(first, facts=[], question_findings=[finding(status=new_status)]))
    assert first.snapshot() == before


def test_inaccessible_finding_cannot_be_later_replaced_and_defaults_are_not_recorded() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(
        empty,
        decision(
            empty,
            facts=[],
            question_findings=[
                finding(
                    status="inaccessible",
                    fact_ids=[],
                    supporting_steps=[1],
                )
            ],
        ),
        [action(outcome_status="failure", outcome="action_timeout")],
    )
    assert [item.question for item in first.as_submission().question_findings] == ["Q1"]
    with pytest.raises(ValueError, match="question"):
        candidate(first, decision(first, question_findings=[finding()]))
    assert "mechanically" in JOURNAL_INSTRUCTIONS.casefold()
    assert "until closing" in " ".join(JOURNAL_INSTRUCTIONS.split())


@pytest.mark.parametrize("question", ["OTHER", "Q1"])
def test_conflicting_same_key_scope_values_reject_even_without_found_finding(question) -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, facts=[fact(question=question)]))
    before = first.snapshot()
    with pytest.raises(ValueError, match="conflict"):
        candidate(
            first,
            decision(first, facts=[fact(id="different", question=question, value_json="7.0")]),
        )
    assert first.snapshot() == before


def test_cross_question_same_key_scope_conflict_cannot_hide_under_other() -> None:
    empty = AcceptedJournal.initial()
    with pytest.raises(ValueError, match="conflict"):
        candidate(
            empty,
            decision(empty, facts=[fact(), fact(id="other", question="OTHER", value_json="7.0")]),
        )


def test_equal_values_with_distinct_ids_and_different_scopes_are_never_merged() -> None:
    empty = AcceptedJournal.initial()
    facts = [
        fact(),
        fact(id="copy"),
        fact(id="domestic", value_json="7.0", scope=scope(population="domestic")),
    ]
    first = candidate(empty, decision(empty, facts=facts))
    assert [item.id for item in first.as_submission().facts] == [
        "english_overall",
        "copy",
        "domestic",
    ]
    assert len(expand_submission(first.as_submission(), [action()], ended_at=END)["proposals"]) == 3


@pytest.mark.parametrize(
    "changes",
    [
        {"fact_ids": ["missing"]},
        {"question": "Q2"},
        {"scope": scope(population="domestic")},
    ],
)
def test_bad_references_and_finding_scope_reject_against_all_retained_facts(changes) -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty))
    before = first.snapshot()
    with pytest.raises(ValueError):
        candidate(first, decision(first, facts=[], question_findings=[finding(**changes)]))
    assert first.snapshot() == before


@pytest.mark.parametrize(
    "changes",
    [
        {"at": "2026-10-05T00:00:00+00:00"},
        {"case_id": "foreign"},
        {"tool": "search_provider"},
        {"outcome_status": "failure"},
        {"policy_mode": "outside_policy"},
    ],
)
def test_every_candidate_source_must_be_observed_current_case_successful_page(changes) -> None:
    empty = AcceptedJournal.initial()
    with pytest.raises(ValueError):
        candidate(empty, decision(empty), [action(**changes)])
    assert empty.snapshot()["facts"] == []


def test_future_or_missing_source_step_and_naive_closing_time_are_rejected() -> None:
    empty = AcceptedJournal.initial()
    with pytest.raises(ValueError, match="recorded"):
        candidate(empty, decision(empty, facts=[fact(source_step=2)]))
    with pytest.raises(ValueError, match="timezone"):
        empty.candidate(decision(empty), [action()], ended_at=datetime(2026, 10, 4))


def test_exact_source_action_date_redirect_and_explicit_false_are_conserved() -> None:
    empty = AcceptedJournal.initial()
    source = action(at="2026-10-03T23:55:00-02:00", final_url="https://u.edu/negative")
    negative = fact(
        question="Q0",
        claim_key="programme.exists",
        value_json="false",
        quotation="BSc Computing is not offered as a bachelor programme.",
        scope=scope(programme="BSc Computing"),
    )
    journal = empty.candidate(
        decision(
            empty,
            facts=[negative],
            question_findings=[finding(question="Q0", scope=negative["scope"])],
        ),
        [Action.model_validate(source)],
        ended_at=START + timedelta(hours=3),
        case_id="u",
    )
    expanded = expand_submission(
        journal.as_submission(), [source], ended_at=START + timedelta(hours=3)
    )
    assert expanded["proposals"][0]["value"] is False
    assert expanded["proposals"][0]["accessed_on"] == "2026-10-03"
    assert expanded["proposals"][0]["source_url"] == "https://u.edu/negative"
    assert expanded["proposals"][0]["scope"] == negative["scope"]


def test_snapshot_roundtrip_is_strict_and_retains_the_complete_journal() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, question_findings=[finding()]))
    restored = AcceptedJournal.from_snapshot(first.snapshot())
    assert restored.snapshot() == first.snapshot()
    assert restored.sha256 == canonical_hash(first.snapshot())
    assert restored.as_submission().model_dump(mode="json")["facts"] == first.snapshot()["facts"]


@pytest.mark.parametrize(
    "field,new_value", [("value_json", "9.0"), ("quotation", "changed"), ("source_step", 2)]
)
def test_snapshot_content_tampering_fails_hash_verification(field, new_value) -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty))
    value = first.snapshot()
    value["facts"][0][field] = new_value
    with pytest.raises(ValueError, match="SHA"):
        AcceptedJournal.from_snapshot(value)
    assert first.as_submission().facts[0].quotation == QUOTE


def test_snapshot_recomputed_hash_cannot_hide_duplicates_conflicts_or_bad_references() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, question_findings=[finding()]))
    duplicate = first.snapshot()
    duplicate["facts"].append(deepcopy(duplicate["facts"][0]))
    conflict = first.snapshot()
    conflicting = deepcopy(conflict["facts"][0])
    conflicting.update(id="conflicting", question="OTHER", value_json="7.0")
    conflict["facts"].append(conflicting)
    reference = first.snapshot()
    reference["question_findings"][0]["fact_ids"] = ["missing"]
    for value in (duplicate, conflict, reference):
        value["journal_sha256"] = canonical_hash(value)
        with pytest.raises(ValueError):
            AcceptedJournal.from_snapshot(value)


@pytest.mark.parametrize(
    "change", [{"schema_version": "2"}, {"timestamp": "unsupported"}, {"journal_sha256": "0" * 64}]
)
def test_snapshot_unknown_fields_versions_and_false_hash_are_rejected(change) -> None:
    with pytest.raises(ValueError):
        AcceptedJournal.from_snapshot({**AcceptedJournal.initial().snapshot(), **change})


def test_returned_models_and_snapshots_cannot_mutate_the_immutable_journal() -> None:
    empty = AcceptedJournal.initial()
    value = decision(empty)
    first = candidate(empty, value)
    before = first.snapshot()
    value["facts"][0]["value_json"] = "999"
    first.as_submission().facts[0].value_json = "888"
    first.facts[0].scope.university = "Foreign"
    first.snapshot()["facts"][0]["quotation"] = "modified copy"
    assert first.snapshot() == before
    with pytest.raises(FrozenInstanceError):
        cast(Any, first)._facts_json = ()


def test_invalid_or_timed_out_later_delta_retains_the_completed_checkpoint() -> None:
    empty = AcceptedJournal.initial()
    first = candidate(empty, decision(empty, question_findings=[finding()]))
    before = first.snapshot()
    incomplete = json.dumps(decision(first, facts=[fact(id="later")]))[:-20]
    with pytest.raises(ValueError):
        candidate(first, incomplete)
    assert first.snapshot() == before
    final = candidate(first, decision(first, kind="submit", facts=[]))
    assert final.snapshot() == before
    assert "completed clean run" in JOURNAL_INSTRUCTIONS


@pytest.mark.parametrize(
    "url", ["not a URL", "/admissions", "ftp://u.edu/fact", "javascript:alert(1)"]
)
def test_local_http_url_validation_remains_strict(url) -> None:
    empty = AcceptedJournal.initial()
    with pytest.raises(ValueError):
        parse_journal_decision(decision(empty, kind="action", facts=[], action=navigation(url=url)))
