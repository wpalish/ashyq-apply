"""Public target-matching rules and diagnostics, never source-scope repairs.

This is a pure view of the existing ``models._scope_findings`` rules. It reads
only one packet case's public request and the public education-system fallback.
Matching a target establishes no evidence. The original journal, trace, source
quotation/location/scope and publication guards remain mandatory.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .compact import (
    SCOPE_DIMENSIONS,
    CompactDecision,
    CompactFact,
    parse_compact_decision,
)
from .journal import JournalDecision, parse_journal_decision
from .models import QUESTION_DESCRIPTIONS, QUESTIONS

EFFECTIVE_JOURNAL_INSTRUCTIONS = """Return one complete journal JSON object with
exactly kind, observation, journal_sha256, action, facts, question_findings.
Bind the currently supplied journal_sha256. Each delta has at most4 NEW facts
and at most2 NEW findings. Never repeat retained fact IDs or recorded questions.
kind=action carries exactly one next controlled action and may carry a delta;
kind=record has action=null and a nonempty delta; kind=submit has action=null
and may carry a last delta or empty facts/findings to commit by hash. A pending
recorded source must be processed explicitly before hash-only closure.

Every fact carries id, question Q0-Q6 or OTHER, public claim_key, value_json
(a STRING encoding the original typed JSON value), source_step, quotation,
location and all eight scope fields: university, programme, degree, field,
intake, population, qualification, academic_year. Preserve literal source values,
conditions and years. Follow the public representation card; never guess private
award IDs or scholarships.* keys. University needs proven source attribution.
Every unknown scope dimension is null. EVERY FACT'S nonnull programme needs its
literal name in that fact's own selected block/header/section or exact saved
PDF/plain context. Page title alone, another block or another fact is not local
programme proof. Degree/field are separate categories only when source-supported.

Use only a completed successful same-policy source read, an exact1-600 character
quotation and real coordinates: document_ir block_id/section_path for HTML when
available; text has null block_id/page and []; pdf has exact one-based page1-40,
never aggregate text. Unused coordinates are null or []. URL/access date derive
from the recorded source action. A context-only match is not a citable quotation.
Navigation uses fetcher for an official URL, search_provider for query/domains,
or view for an already recorded source_step; no upcoming action supports a fact.

The public question contract describes TARGET MATCHING, not source evidence.
Never copy an expected target into scope to pass a check. Settled findings need
all required source-supported dimensions and exact matching where specified.
Without matching actual source scope, retain supported facts under OTHER where
appropriate and leave the question unresolved; do not change a date, intake,
population, programme or qualification to match the request.

Findings are sparse and reference compatible NEW or RETAINED current-case
fact_ids assigned to the same question. found/not_published use supporting_steps=[];
not_published additionally needs an explicit official publication statement.
Failed search never establishes nonpublication. inaccessible has no fact_ids and
needs actual failed/blocked same-policy source steps. Omit unresolved/inaccessible
until closing if they may resolve: recorded findings, including these, are
immutable. Omitted questions remain unresolved. The entire candidate is atomic;
rejection/timeout preserves earlier checkpoints without accepting this delta.
All original journal, raw-log, citation and scope gates remain mandatory.
"""

_EVIDENCE_ONLY = "Expected scope is a target comparison, never evidence or replacement scope. Preserve source-literal scope and every unknown as null. Do not settle found/not_published without matching actual source support; keep source-specific facts under OTHER where appropriate and leave the question unresolved. Every fact's nonnull programme needs its own selected evidence context, not page title alone or an unrelated fact. All original acceptance gates remain mandatory."


def _required(question: str) -> list[str]:
    required = {"degree"}
    if question == "Q0":
        required.add("programme")
    if question in {"Q1", "Q2", "Q3", "Q4", "Q6"}:
        required.add("population")
    if question == "Q2":
        required.add("qualification")
    if question == "Q3":
        required.add("intake")
    if question == "Q4":
        required.add("academic_year")
    return sorted(required)


def _public_text(value: Any, name: str) -> str | None:
    if value is not None and (not isinstance(value, str) or len(value) > 1000):
        raise ValueError(f"Public {name} must be bounded text or null")
    return value


def question_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Return fresh allowlisted rules for exactly one public packet case.

    The expected values apply to EVERY nonnull declared dimension of a settled
    finding, even dimensions not required for that question. Null targets impose
    no equality requirement. Q4's existing rule compares the first 20xx year,
    not arbitrary year-range overlap or a guessed seasonal equivalence.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("Question contract needs a public packet mapping")
    cases = packet.get("cases")
    if not isinstance(cases, list | tuple) or len(cases) != 1 or not isinstance(cases[0], Mapping):
        raise ValueError("Question contract requires exactly one public case")
    case = cases[0]
    request, profile = case.get("request"), packet.get("public_profile", {})
    if not isinstance(request, Mapping) or not isinstance(profile, Mapping):
        raise ValueError("Public request and public_profile must be mappings")
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip() or len(case_id) > 200:
        raise ValueError("Public case_id must be bounded nonempty text")
    requested = {name: _public_text(request.get(name), name) for name in SCOPE_DIMENSIONS}
    education_system = (
        _public_text(profile.get("education_system"), "education_system")
        if not requested["qualification"]
        else None
    )
    expected = {
        **requested,
        "population": requested["population"] or "international",
        "qualification": requested["qualification"] or education_system,
    }
    intake_years = re.findall(r"\b20\d{2}\b", requested["intake"] or "")
    return {
        "schema_version": "1",
        "case_id": case_id,
        "settled_statuses": ["found", "not_published"],
        "expected_scope": expected,
        "comparison": "Every nonnull declared dimension with a nonnull expected value must match by exact string equality; no trimming, case folding or alias inference.",
        "fixed_degree": "bachelor",
        "questions": {
            question: {
                "description": QUESTION_DESCRIPTIONS[question],
                "required_scope": _required(question),
            }
            for question in QUESTIONS
        },
        "q4_first_year_rule": {
            "enabled": not requested["academic_year"],
            "required_first_year": intake_years[0] if intake_years else None,
            "comparison": "When enabled and request intake contains a 20xx year, the first 20xx year in declared academic_year must equal that first intake year.",
        },
        "evidence_only_instruction": _EVIDENCE_ONLY,
    }


def question_scope_diagnostics(
    decision: JournalDecision | CompactDecision,
    packet: Mapping[str, Any],
    *,
    retained_facts: Sequence[CompactFact] = (),
) -> list[dict[str, Any]]:
    """Identify failed target comparisons without changing any submission.

    Current/retained fact scopes are checked for found findings exactly as in
    ``_scope_findings``. A journal delta may refer to retained public facts; pass
    those models explicitly. Raw-source/local programme support is diagnosed by
    the separate source-view helper, never inferred here from target strings.
    Empty diagnostics certify neither source support nor acceptance.
    """
    contract = question_contract(packet)
    parsed: JournalDecision | CompactDecision
    if isinstance(decision, JournalDecision):
        parsed = parse_journal_decision(decision.model_dump(mode="python"))
    elif isinstance(decision, CompactDecision):
        parsed = parse_compact_decision(decision.model_dump(mode="python"))
    else:
        raise ValueError("Question diagnostics need a completed parsed journal/compact decision")
    if (
        not isinstance(retained_facts, Sequence)
        or isinstance(retained_facts, str | bytes)
        or len(retained_facts) > 128
    ):
        raise ValueError("Retained facts must be a bounded sequence of public fact models")
    facts = {}
    for fact in retained_facts:
        if not isinstance(fact, CompactFact):
            raise ValueError("Retained facts must be original CompactFact models")
        validated = CompactFact.model_validate(fact.model_dump(mode="python"))
        if validated.id in facts:
            raise ValueError("Retained fact IDs must be unique")
        facts[validated.id] = validated
    for fact in parsed.facts:
        if fact.id in facts:
            raise ValueError("A new delta cannot reuse a retained fact ID")
        facts[fact.id] = fact
    result: list[dict[str, Any]] = []
    for index, finding in enumerate(parsed.question_findings):
        if finding.status not in {"found", "not_published"}:
            continue
        scope = finding.scope.model_dump()
        required = contract["questions"][finding.question]["required_scope"]
        identity = {
            "target": "finding",
            "finding_index": index,
            "question": finding.question,
            "fact_ids": list(finding.fact_ids),
        }
        for field in required:
            if not scope.get(field):
                result.append(
                    {
                        **identity,
                        "field": field,
                        "reason": "required_scope_missing",
                        "required": True,
                        "constraint": "nonempty_source_supported_text",
                        "expected": contract["expected_scope"][field],
                        "asserted": scope.get(field),
                    }
                )
        for field, asserted in scope.items():
            expected = contract["expected_scope"].get(field)
            if asserted is not None and expected is not None and asserted != expected:
                result.append(
                    {
                        **identity,
                        "field": field,
                        "reason": "target_scope_mismatch",
                        "required": field in required,
                        "expected": expected,
                        "asserted": asserted,
                    }
                )
        if scope["degree"] is not None and scope["degree"] != "bachelor":
            result.append(
                {
                    **identity,
                    "field": "degree",
                    "reason": "bachelor_scope_mismatch",
                    "required": True,
                    "expected": "bachelor",
                    "asserted": scope["degree"],
                }
            )
        if finding.question == "Q4":
            rule = contract["q4_first_year_rule"]
            years = re.findall(r"\b20\d{2}\b", scope["academic_year"] or "")
            if (
                rule["enabled"]
                and rule["required_first_year"] is not None
                and (not years or years[0] != rule["required_first_year"])
            ):
                result.append(
                    {
                        **identity,
                        "field": "academic_year",
                        "reason": "fee_first_year_mismatch",
                        "required": True,
                        "expected": {"first_year": rule["required_first_year"]},
                        "asserted": scope["academic_year"],
                    }
                )
        if finding.status != "found":
            continue
        for fact_id in finding.fact_ids:
            referenced = facts.get(fact_id)
            if referenced is None:
                result.append(
                    {
                        **identity,
                        "field": "fact_ids",
                        "reason": "referenced_fact_not_supplied",
                        "required": True,
                        "expected": "new or retained current-case fact",
                        "asserted": fact_id,
                    }
                )
                continue
            fact_scope = referenced.scope.model_dump()
            for field, expected in scope.items():
                if expected is not None and fact_scope.get(field) != expected:
                    result.append(
                        {
                            "target": "fact",
                            "fact_id": fact_id,
                            "source_step": referenced.source_step,
                            "finding_index": index,
                            "question": finding.question,
                            "field": field,
                            "reason": "fact_finding_scope_mismatch",
                            "required": True,
                            "expected": expected,
                            "asserted": fact_scope.get(field),
                        }
                    )
    return result
