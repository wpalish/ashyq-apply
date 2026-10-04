"""Pure replay and post-seal diagnosis for equal-action expert comparisons.

This module reads no files or labels and performs no calls. Source counters are
reconstructed from the executed flags of original controller records. A model
or transport clock can never be substituted for that ledger. Miss diagnoses
remain unresolved unless a fact-specific recorded observation supports them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import _outcome
from .network_budget import (
    BUDGET_MODEL,
    MAX_FETCHER_CALLS,
    MAX_SEARCH_QUERIES,
    NETWORK_COMPARISON_MODE,
    WALL_GUARD_MS,
    WallGuard,
    expert_budget,
    parse_timestamp,
)

MISS_CAUSES = frozenset(
    {
        "NOT_DISCOVERED",
        "OTHER_PAGE",
        "EXTRACTOR",
        "CLASSIFIER",
        "SLOT",
        "BUDGET",
        "PDF",
        "JS",
        "SCOPE",
        "ACCESS",
    }
)


def _int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a strict nonnegative integer")
    return value


def _equal(record: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    if any(
        type(record.get(key)) is not type(value) or record.get(key) != value
        for key, value in expected.items()
    ):
        raise ValueError(f"{label} differs from the declared network contract")


def _timestamp(value: Any, field: str) -> datetime:
    if type(value) is not str:
        raise ValueError(f"{field} must be a recorded aware timestamp")
    return parse_timestamp(value, field=field)


@dataclass(frozen=True, slots=True)
class SourceCounters:
    """Only independently measured source work; wall/model time is separate."""

    fetcher_calls: int = 0
    search_queries: int = 0
    source_ms: int = 0

    def __post_init__(self) -> None:
        for field in ("fetcher_calls", "search_queries", "source_ms"):
            _int(getattr(self, field), field)

    def as_dict(self) -> dict[str, int]:
        return {
            "fetcher_calls": self.fetcher_calls,
            "search_queries": self.search_queries,
            "elapsed_ms": self.source_ms,
        }


def validate_source_run(
    plan: Mapping[str, Any],
    summary: Mapping[str, Any],
    raw: Mapping[str, Any],
    *,
    case_id: str,
    official_domains: Sequence[str],
    wall_guard: WallGuard,
    raw_sha256: str,
    provider: str = "exa_mcp",
    prior: SourceCounters = SourceCounters(),
    prior_summary: Mapping[str, Any] | None = None,
) -> SourceCounters:
    """Replay one original source action and its strict resume continuity.

    A failed action may finish after the hang guard during cancellation cleanup;
    its executed query/read still counts. A successful page or search response
    must finish strictly before the immutable deadline and can support facts
    only through the separate original citation validator.
    """
    if type(provider) is not str or provider not in {"exa", "exa_mcp"}:
        raise ValueError("A source run requires a pinned allowed search provider")
    if plan.get("provider", "exa_mcp") != provider:
        raise ValueError("Dispatch plan differs from the pinned search provider")
    _equal(
        plan,
        {
            "case_id": case_id,
            "log_prefix": case_id,
            "strict_budget": True,
            "max_calls": MAX_FETCHER_CALLS,
            "max_search_queries": MAX_SEARCH_QUERIES,
            "max_ms": WALL_GUARD_MS,
            "budget_origin": NETWORK_COMPARISON_MODE,
            "budget_model": BUDGET_MODEL,
            **wall_guard.as_dict(),
        },
        "Dispatch plan",
    )
    if (
        plan.get("official_domains") != list(official_domains)
        or plan.get("action_deadline_ms") is not None
        or plan.get("replay", [])
        or plan.get("exploration_mode", "same_policy") != "same_policy"
    ):
        raise ValueError("Primary dispatch cannot change domains, replay or source policy")
    actions = plan.get("actions")
    if not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], Mapping):
        raise ValueError("Each source dispatch needs one original model-selected action")
    starts = {
        "start_calls": prior.fetcher_calls,
        "start_search_queries": prior.search_queries,
        "start_ms": prior.source_ms,
    }
    for key, expected in starts.items():
        value = plan.get(key, 0)
        if type(value) is not int or value != expected:
            raise ValueError("Resume counters must equal the previous source ledger")
    if prior_summary is None:
        if plan.get("resume_summary") is not None:
            raise ValueError("Fresh source dispatch cannot import a resume summary")
    else:
        if prior_summary.get("provider") != provider:
            raise ValueError("Resume cannot change the pinned search provider")
        expected_resume = {
            key: value
            for key, value in prior_summary.items()
            if key not in {"actions", "replay", "initial"}
        }
        if plan.get("resume_summary") != expected_resume:
            raise ValueError("Resume must retain the exact preceding controller summary")
    identity = {
        "case_id": case_id,
        "provider": provider,
        "log_prefix": case_id,
        "budget_origin": NETWORK_COMPARISON_MODE,
        **expert_budget(),
        **wall_guard.as_dict(),
    }
    _equal(summary, identity, "Controller summary")
    _equal(raw, identity, "Original raw action")
    policy = raw.get("tool_policy")
    if not isinstance(policy, Mapping):
        raise ValueError("Original source action lacks its tool policy")
    _equal(
        policy,
        {
            "strict_budget": True,
            "budget_origin": NETWORK_COMPARISON_MODE,
            "exploration_mode": "same_policy",
            "official_domains": list(official_domains),
            **expert_budget(),
            **wall_guard.as_dict(),
        },
        "Original raw tool policy",
    )
    if (
        policy.get("action_deadline_ms") is not None
        or policy.get("allowed_search_providers") != ["exa", "exa_mcp"]
        or summary.get("tool_policy") != policy
        or raw.get("phase") != "actions"
        or raw.get("budgets") != {"max_calls": 60, "max_ms": WALL_GUARD_MS, "max_search_queries": 6}
        or summary.get("initial") != starts
    ):
        raise ValueError("Controller raw policy or initial source state changed")
    produced = summary.get("actions")
    if not isinstance(produced, list) or len(produced) != 1:
        raise ValueError("Source summary must contain the one original action")
    action = produced[0]
    if not isinstance(action, Mapping):
        raise ValueError("Source summary action must be a mapping")
    name = action.get("raw_log_path")
    expected_raw_logs = dict(prior_summary["raw_logs"]) if prior_summary else {}
    if type(name) is not str or not name or "/" in name or "\\" in name:
        raise ValueError("Source raw-log name must be local and exact")
    if name in expected_raw_logs:
        raise ValueError("A raw source log cannot be overwritten on resume")
    expected_raw_logs[name] = raw_sha256
    if action.get("raw_log_sha256") != raw_sha256 or summary.get("raw_logs") != expected_raw_logs:
        raise ValueError("Source summary does not bind the immutable original raw bytes")
    request = raw.get("request")
    if not isinstance(request, Mapping) or request.get("tool") not in {
        "fetcher",
        "search_provider",
    }:
        raise ValueError("Raw source request must use a controlled network tool")
    # Search defaults are materialized by the controller; the caller separately
    # compares these against the selected action via its frozen domain helper.
    if action.get("request") != request or action.get("tool") != request["tool"]:
        raise ValueError("Summary action differs from its original raw request")
    response = raw.get("response") or {}
    if not isinstance(response, Mapping):
        raise ValueError("Original controller response must be a mapping")
    expected_outcome, expected_status = _outcome(dict(raw))
    if raw.get("outcome_status") != expected_status or (
        response.get("outcome_status") is not None and response["outcome_status"] != expected_status
    ):
        raise ValueError("Original source status disagrees with its actual response")
    if expected_status == "success" and request["tool"] == "fetcher":
        code = response.get("status_code")
        if type(code) is not int or not (
            200 <= code < 300 or (expected_outcome == "cached" and code == 304)
        ):
            raise ValueError("A successful Fetcher source requires its original HTTP success")
    for key, expected in {
        "at": raw.get("at"),
        "outcome": expected_outcome,
        "outcome_status": raw.get("outcome_status"),
        "executed": raw.get("executed"),
        "elapsed_ms": raw.get("elapsed_ms"),
        "policy_mode": raw.get("policy_mode"),
        "final_url": raw.get("response", {}).get("final_url"),
    }.items():
        if type(action.get(key)) is not type(expected) or action.get(key) != expected:
            raise ValueError("Source summary fabricated an outcome/status from the raw record")
    at = _timestamp(raw.get("at"), "source at")
    completed = _timestamp(raw.get("completed_at"), "source completed_at")
    if not wall_guard.started_at <= at <= completed:
        raise ValueError("Original source wall chronology is invalid")
    executed = raw.get("executed")
    if type(executed) is not bool:
        raise ValueError("Actual source invocation must have a strict executed flag")
    if executed != bool(response):
        raise ValueError("Controller executed flag disagrees with its recorded response")
    dispatch = raw.get("dispatch_at")
    if executed:
        sent = _timestamp(dispatch, "source dispatch_at")
        if not at <= sent < wall_guard.deadline_at or sent > completed:
            raise ValueError("A source invocation cannot start after the absolute guard")
    elif dispatch is not None:
        raise ValueError("A blocked source action cannot invent a dispatch")
    elapsed = _int(raw.get("elapsed_ms"), "raw elapsed_ms")
    before = _int(raw.get("elapsed_ms_before"), "raw elapsed_ms_before")
    charged = _int(raw.get("charged_elapsed_ms"), "raw charged_elapsed_ms")
    wall_interval_ms = (completed - at).total_seconds() * 1000
    if elapsed > wall_interval_ms + 1:
        raise ValueError("Measured source elapsed exceeds its original source wall interval")
    if before != prior.source_ms or charged != elapsed or (not executed and elapsed != 0):
        raise ValueError("Source elapsed ledger cannot contain model or transport time")
    counters = SourceCounters(
        prior.fetcher_calls + int(executed and request["tool"] == "fetcher"),
        prior.search_queries + int(executed and request["tool"] == "search_provider"),
        before + charged,
    )
    if counters.fetcher_calls > MAX_FETCHER_CALLS or counters.search_queries > MAX_SEARCH_QUERIES:
        raise ValueError("Primary source actions exceeded the equal 60/6 budget")
    final = summary.get("final")
    if not isinstance(final, Mapping):
        raise ValueError("Controller summary lacks its original final source counters")
    for key, raw_key, expected in (
        ("fetcher_calls", "fetcher_calls_cumulative", counters.fetcher_calls),
        ("search_queries", "search_queries_cumulative", counters.search_queries),
        ("elapsed_ms", "elapsed_ms_cumulative", counters.source_ms),
    ):
        for record, name_key in ((raw, raw_key), (action, raw_key), (final, key)):
            if type(record.get(name_key)) is not int or record[name_key] != expected:
                raise ValueError("Original raw, action and summary source counters disagree")
    status = raw.get("outcome_status")
    if status not in {"success", "failure", "blocked"} or (not executed and status != "blocked"):
        raise ValueError("Original controller source status is invalid")
    if status == "success" and (not executed or completed >= wall_guard.deadline_at):
        raise ValueError("A successful source response must complete before the case guard")
    if (
        isinstance(response, Mapping)
        and response.get("outcome_status") == "success"
        and status != "success"
    ):
        raise ValueError("A failed source cannot expose a successful response")
    reason = raw.get("stop_reason")
    if reason not in {None, "http_429", "budget_exhausted", "wall_guard_exhausted"}:
        raise ValueError("Unknown original network controller stop reason")
    provider_429 = (
        executed
        and request["tool"] == "search_provider"
        and any(
            type(response.get(key)) is int and response[key] == 429
            for key in ("http_status", "status_code")
        )
    )
    prior_reason = prior_summary["final"].get("stop_reason") if prior_summary else None
    if provider_429:
        if status != "failure" or reason != "http_429" or final.get("stop_reason") != "http_429":
            raise ValueError(
                "Actual provider HTTP429 must retain the original raw/final http_429 latch"
            )
        required_reason = "http_429"
    elif prior_reason is not None:
        required_reason = prior_reason
    elif completed >= wall_guard.deadline_at or (
        response.get("outcome") == "action_timeout"
        and raw.get("timeout_reason") == "wall_guard_exhausted"
    ):
        required_reason = "wall_guard_exhausted"
    elif (
        raw.get("outcome") == "budget_exhausted"
        and not executed
        and (
            (request["tool"] == "fetcher" and prior.fetcher_calls >= MAX_FETCHER_CALLS)
            or (request["tool"] == "search_provider" and prior.search_queries >= MAX_SEARCH_QUERIES)
        )
    ):
        required_reason = "budget_exhausted"
    else:
        required_reason = None
    if reason != required_reason:
        raise ValueError(
            "Original source stop reason does not follow its actual response/caps/wall"
        )
    # Controller serialization can itself cross the guard after a valid source.
    # The late summary must make that exhaustion visible; it cannot close a
    # prior selector before the raw action was actually completed.
    final_completed = _timestamp(final.get("completed_at"), "summary completed_at")
    if final_completed < completed:
        raise ValueError("Controller summary completion precedes its original source")
    expected_reason = reason or (
        "wall_guard_exhausted" if final_completed >= wall_guard.deadline_at else None
    )
    if final.get("stop_reason") != expected_reason:
        raise ValueError("Summary stop reason differs from the original source state")
    if prior_summary and prior_summary["final"].get("stop_reason") is not None and executed:
        raise ValueError("No primary invocation may resume a stopped source ledger")
    return counters


def network_gate(metrics: Mapping[str, Any], *, eligible: bool, diagnoses_complete: bool) -> bool:
    """Count the expert's unique scored known keys, excluding diagnostic work."""
    recall = metrics.get("claim_recall", {})
    return (
        eligible
        and diagnoses_complete
        and isinstance(recall, Mapping)
        and type(recall.get("numerator")) is int
        and type(recall.get("denominator")) is int
        and recall["denominator"] == 62
        and 40 <= recall["numerator"] <= 62
    )


def diagnose_fact(
    *,
    fact_id: str,
    source_url: str,
    claim_key: str,
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Retain a cause only when a source/fact-specific observable supports it.

    Observations are already sealed post-submission records. Every supporting
    record must retain an artifact hash and a structural path. A budget flag,
    absent ranked URL, empty HTML or a missing output alone settles no cause.
    This pure function deliberately never fills a cause from the claim key.
    """
    candidates: dict[str, list[dict[str, Any]]] = {}
    for item in observations:
        if (
            item.get("source_url") != source_url
            or item.get("fact_id") not in {None, fact_id}
            or item.get("claim_key") not in {None, claim_key}
            or type(item.get("artifact_sha256")) is not str
            or len(item["artifact_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in item["artifact_sha256"])
            or type(item.get("path")) is not str
            or not item["path"]
        ):
            continue
        kind = item.get("kind")
        cause: str | None = None
        if kind == "access_failure" and item.get("read_attempted") is True and item.get("failure"):
            cause = "ACCESS"
        elif kind == "classifier_rejection" and item.get("stage_rejected") is True:
            cause = "CLASSIFIER"
        elif kind == "extractor_miss" and item.get("verbatim_in_saved_payload") is True:
            cause = "EXTRACTOR"
        elif kind == "slot_miss" and item.get("literal_claim_recorded") is True:
            cause = "SLOT"
        elif (
            kind == "pdf_failure"
            and item.get("representation") == "pdf"
            and item.get("parser_failure")
        ):
            cause = "PDF"
        elif kind == "javascript_required" and item.get("explicit_saved_requirement"):
            cause = "JS"
        elif (
            kind == "scope_mismatch"
            and item.get("same_typed_value") is True
            and item.get("scope_rejection")
        ):
            cause = "SCOPE"
        elif (
            kind == "other_page"
            and item.get("candidate_recorded") is True
            and item.get("selected_other_page")
        ):
            cause = "OTHER_PAGE"
        elif (
            kind == "not_discovered"
            and item.get("complete_candidate_registry") is True
            and item.get("absent_from_registry") is True
        ):
            cause = "NOT_DISCOVERED"
        elif (
            kind == "budget_skip"
            and item.get("candidate_recorded") is True
            and item.get("explicit_skip_reason")
            in {"page_budget_exhausted", "search_budget_exhausted", "wall_clock_budget_exhausted"}
        ):
            cause = "BUDGET"
        if cause is not None:
            candidates.setdefault(cause, []).append(dict(item))
    resolved = len(candidates) == 1
    return {
        "fact_id": fact_id,
        "claim_key": claim_key,
        "source_url": source_url,
        "cause": next(iter(candidates)) if resolved else None,
        "status": "resolved" if resolved else "unresolved",
        "support": next(iter(candidates.values())) if resolved else [],
        "candidate_causes": sorted(candidates),
        "diagnostic_only": True,
    }


def validate_diagnoses(
    expected_fact_ids: Sequence[str], diagnoses: Sequence[Mapping[str, Any]]
) -> bool:
    """Each genuinely expert-only scored fact must occur once, including unknowns."""
    ids = [item.get("fact_id") for item in diagnoses]
    if len(set(expected_fact_ids)) != len(expected_fact_ids):
        raise ValueError("Expert-only scored facts must be unique")
    if len(ids) != len(set(ids)) or set(ids) != set(expected_fact_ids):
        raise ValueError("Every expert-only fact requires exactly one visible diagnosis")
    complete = True
    for item in diagnoses:
        if item.get("cause") is None:
            if item.get("status") != "unresolved" or item.get("support"):
                raise ValueError("Unknown miss causes must remain explicitly unresolved")
            complete = False
        elif (
            item.get("cause") not in MISS_CAUSES
            or item.get("status") != "resolved"
            or not item.get("support")
        ):
            raise ValueError("Miss cause requires a dictionary value and observable support")
        else:
            replayed = diagnose_fact(
                fact_id=item["fact_id"],
                source_url=item["source_url"],
                claim_key=item["claim_key"],
                observations=item["support"],
            )
            if replayed["cause"] != item["cause"]:
                raise ValueError("Declared miss cause does not follow its recorded support")
    return complete
