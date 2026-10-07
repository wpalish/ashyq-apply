"""Exact saved-source citation checks for every explicitly submitted compact fact.

This supplements complete ``validate_trace`` validation. It does not adjudicate
claim values or infer semantic applicability, and reads only supplied raw logs.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .compact import CompactDecision, CompactFact, _load_json, parse_compact_decision
from .controller import blocked
from .models import (
    Action,
    EvidenceLocation,
    QuestionFinding,
    SourceEvidence,
    _academic_year_evidence,
    _AcademicYearEvidenceError,
    _check_controller_action,
    _evidence_scope,
    _official_source,
    _quote_matches,
    _source_read,
    _SourceRead,
    _year_label,
)


def _case(packet: Mapping[str, Any]) -> dict[str, Any]:
    cases = packet.get("cases")
    if (
        not isinstance(cases, Sequence)
        or isinstance(cases, str | bytes)
        or len(cases) != 1
        or not isinstance(cases[0], Mapping)
    ):
        raise ValueError("Compact citations require one current-case packet")
    case = dict(cases[0])
    if not isinstance(case.get("case_id"), str) or not case["case_id"]:
        raise ValueError("Compact citation packet needs its explicit current case_id")
    if not isinstance(case.get("domain"), str) or not case["domain"]:
        raise ValueError("Compact citation packet needs its independently resolved official domain")
    return case


def _recorded_actions(
    actions: Sequence[Action | Mapping[str, Any]], case_id: str
) -> dict[int, Action]:
    """Validate the whole action sequence before any evidence-step lookup."""
    result: dict[int, Action] = {}
    paths: set[Path] = set()
    previous: Action | None = None
    used_queries = 0
    for recorded in actions:
        raw = recorded.model_dump() if isinstance(recorded, Action) else dict(recorded)
        if "case_id" in raw and raw.pop("case_id") != case_id:
            raise ValueError("Recorded source action belongs to a different case")
        action = Action.model_validate(raw)
        if action.step != len(result) + 1:
            raise ValueError("Current-case recorded actions need consecutive unique steps")
        if previous is not None and action.at < previous.at:
            raise ValueError("Recorded source actions must be chronological")
        if (action.step == 1 and action.observed_from_step is not None) or (
            action.step > 1
            and (action.observed_from_step is None or action.observed_from_step >= action.step)
        ):
            raise ValueError("Recorded actions must observe the baseline or an earlier step")
        path = Path(action.raw_log_path)
        if path in paths:
            raise ValueError("Every recorded action needs its own raw tool log")
        paths.add(path)
        previous_calls = previous.fetcher_calls_cumulative if previous else 0
        previous_ms = previous.elapsed_ms_cumulative if previous else 0
        if action.fetcher_calls_cumulative < previous_calls or (
            action.tool == "fetcher"
            and action.outcome_status != "blocked"
            and action.fetcher_calls_cumulative == previous_calls
        ):
            raise ValueError("Recorded Fetcher calls must not decrease or omit a consumed call")
        if action.elapsed_ms_cumulative < previous_ms + action.elapsed_ms:
            raise ValueError("Recorded cumulative time must include each action")
        if action.search_queries_cumulative is not None:
            if action.search_queries_cumulative < used_queries:
                raise ValueError("Recorded search query counters must not decrease")
            used_queries = action.search_queries_cumulative
        result[action.step] = action
        previous = action
    return result


def _raw_path(root: Path, action: Action) -> Path:
    path = root
    for part in Path(action.raw_log_path).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Compact citation raw logs cannot use symlinks")
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("Compact citation path escapes the recorded log directory")
    if not path.is_file():
        raise ValueError("Compact citation raw logs must be regular files")
    return path


def _read_source(
    action: Action, actions: Mapping[int, Action], root: Path, case: dict[str, Any]
) -> _SourceRead:
    data = _raw_path(root, action).read_bytes()
    if hashlib.sha256(data).hexdigest() != action.raw_log_sha256:
        raise ValueError("Compact citation raw log hash mismatch")
    record = _load_json(data.decode("utf-8"))
    if not isinstance(record, dict) or record.get("case_id") != case["case_id"]:
        raise ValueError("Compact citation source belongs to another case")
    if not isinstance(record.get("request"), dict) or not isinstance(record.get("response"), dict):
        raise ValueError("Compact citations require structured controlled source logs")
    previous = actions.get(action.step - 1)
    # Initial counters can include a baseline intervention. The full trace
    # independently binds those floors; this checks the cited record itself.
    previous_calls = (
        previous.fetcher_calls_cumulative if previous else (action.fetcher_calls_cumulative - 1)
    )
    previous_ms = (
        previous.elapsed_ms_cumulative
        if previous
        else record.get("elapsed_ms_before", action.elapsed_ms_cumulative - action.elapsed_ms)
    )
    previous_queries = (
        previous.search_queries_cumulative or 0
        if previous
        else action.search_queries_cumulative or 0
    )
    _check_controller_action(action, record, previous_calls, previous_ms, previous_queries)
    source = _source_read(record)
    if (
        source is None
        or action.url is None
        or blocked(str(action.url))
        or not _official_source(action.url, case)
        or blocked(str(source.url))
        or not _official_source(source.url, case)
        or str(source.url) != str(action.final_url or action.url)
    ):
        raise ValueError("Compact citation source is not this exact official page")
    return source


def _scope_context(evidence: SourceEvidence, source: _SourceRead) -> SourceEvidence:
    """Bind scope checks to the saved structural location, retaining proof inputs."""
    from app.domain.claim_verifier import is_verbatim_excerpt

    location = evidence.location
    if location.kind == "document_ir":
        return evidence
    if location.kind == "text" and source.document is not None:
        matches = [
            block
            for block in source.document.blocks
            if is_verbatim_excerpt(evidence.excerpt, block.text)
        ]
        if len(matches) != 1:
            raise ValueError(
                "HTML text quotation needs one unambiguous DocumentIR block or an explicit structural location"
            )
        block = matches[0]
        return SourceEvidence(
            action_step=evidence.action_step,
            source_url=evidence.source_url,
            excerpt=evidence.excerpt,
            location=EvidenceLocation(
                kind="document_ir", block_id=block.id, section_path=list(block.section_path)
            ),
        )
    if location.kind == "pdf":
        assert source.pdf_pages is not None and location.page is not None
        context = source.pdf_pages[location.page - 1]
    else:
        context = source.text
    return SourceEvidence(
        action_step=evidence.action_step,
        source_url=evidence.source_url,
        excerpt=context,
        location=location,
    )


def _check_fact_scope(
    fact: CompactFact, finding: QuestionFinding, evidence: SourceEvidence, source: _SourceRead
) -> None:
    try:
        _evidence_scope(finding, evidence, source)
    except _AcademicYearEvidenceError as exc:
        location = evidence.location.model_dump(mode="json")
        raise ValueError(
            f"{fact.question} fact {fact.id}: academic_year evidence {exc.reason}; "
            f"declared={fact.scope.academic_year!r}, observed={list(exc.published)!r}, "
            f"source_step={fact.source_step}, location={location!r}"
        ) from exc


def validate_fact_citations(
    decision: CompactDecision | str | Mapping[str, Any],
    actions: Sequence[Action | Mapping[str, Any]],
    *,
    logs_dir: Path,
    packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate every fact's exact source, coordinates and visible scope conflicts.

    OTHER facts and facts absent from question findings receive the same checks.
    Proof indices preserve the submitted fact order. Complete trace/controller
    validation, including the submission time interval and budgets, remains a
    separate required gate before journal or final submission acceptance.
    """
    parsed = parse_compact_decision(decision)
    case = _case(packet)
    recorded = _recorded_actions(actions, case["case_id"])
    root = logs_dir.resolve()
    sources: dict[int, _SourceRead] = {}
    proof: list[dict[str, Any]] = []
    for index, fact in enumerate(parsed.facts):
        action = recorded.get(fact.source_step)
        if (
            action is None
            or action.tool != "fetcher"
            or action.policy_mode != "same_policy"
            or action.outcome_status != "success"
        ):
            raise ValueError("Every compact fact requires its successful controlled source action")
        if fact.source_step not in sources:
            sources[fact.source_step] = _read_source(action, recorded, root, case)
        source = sources[fact.source_step]
        location = EvidenceLocation.model_validate(fact.location.model_dump())
        if not _quote_matches(fact.quotation, source, location):
            raise ValueError(
                "Compact fact quote or location is absent from its exact official source"
            )
        evidence = SourceEvidence(
            action_step=action.step,
            source_url=source.url,
            excerpt=fact.quotation,
            location=location,
        )
        check = QuestionFinding(
            question=fact.question if fact.question != "OTHER" else "Q1",
            status="unresolved",
            supporting_steps=[action.step],
            evidence=[evidence],
            scope=fact.scope.model_dump(),
            observation="Mechanical citation-scope check only.",
        )
        # Mixed page context must not mask a degree/population conflict in the
        # literal quotation. Q1 leaves year/programme/intake to the real location.
        quote_check = QuestionFinding.model_validate({**check.model_dump(), "question": "Q1"})
        quote_evidence = evidence.model_copy(update={"location": EvidenceLocation(kind="text")})
        _check_fact_scope(fact, quote_check, quote_evidence, source)
        # Existing intake checks permit silence; year checks need a literal year
        # marker so a short quote may still use its exact saved location's year.
        for dimension, question in (("intake", "Q3"), ("academic_year", "Q4")):
            if getattr(fact.scope, dimension) is None or (
                question == "Q4" and re.search(r"\b20\d{2}\b", fact.quotation) is None
            ):
                continue
            literal_check = QuestionFinding.model_validate(
                {**check.model_dump(), "question": question}
            )
            _check_fact_scope(fact, literal_check, quote_evidence, source)
        scope_evidence = _scope_context(evidence, source)
        _check_fact_scope(fact, check, scope_evidence, source)
        # Explicit scope cannot evade an existing guard through its Q/OTHER
        # label or by remaining unreferenced in sparse question findings.
        for dimension, question in (("programme", "Q0"), ("intake", "Q3"), ("academic_year", "Q4")):
            if getattr(fact.scope, dimension) is not None and question != check.question:
                dimension_check = QuestionFinding.model_validate(
                    {**check.model_dump(), "question": question}
                )
                _check_fact_scope(fact, dimension_check, scope_evidence, source)
        year_support: list[dict[str, Any]] = []
        if fact.scope.academic_year is not None:
            _years, year_support = _academic_year_evidence(
                scope_evidence, source, _year_label(fact.scope.academic_year)
            )
        proof.append(
            {
                "fact_id": fact.id,
                "proposal_index": index,
                "source_step": action.step,
                "raw_log_sha256": action.raw_log_sha256,
                "source_url": str(source.url),
                "quotation_sha256": hashlib.sha256(fact.quotation.encode()).hexdigest(),
                "location": fact.location.model_dump(mode="json"),
                "scope": fact.scope.model_dump(),
                **({"academic_year_support": year_support} if year_support else {}),
            }
        )
    return proof
