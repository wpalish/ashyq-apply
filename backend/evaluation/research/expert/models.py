"""Strict, auditable shape for expert intervention records."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Action(Strict):
    step: int = Field(ge=1)
    at: datetime
    observed_before: str = Field(min_length=1)
    observed_from_step: int | None = Field(default=None, ge=1)
    tool: Literal["search_provider", "fetcher", "browser", "pdf_parser", "internal_index", "other"]
    action: str = Field(min_length=1)
    outcome_status: Literal["success", "failure", "blocked"]
    outcome: str = Field(min_length=1)
    stage: Literal[
        "access",
        "candidate_generation",
        "ranking",
        "page_understanding",
        "representation",
        "extraction",
        "identity_scope",
        "schema",
        "conflict_freshness",
    ]
    policy_mode: Literal["same_policy", "outside_policy"]
    url: HttpUrl | None = None
    raw_log_path: str = Field(min_length=1)
    raw_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    elapsed_ms: int = Field(ge=0)
    fetcher_calls_cumulative: int = Field(ge=0)
    elapsed_ms_cumulative: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def flag_other_tool(self) -> Self:
        if self.tool == "other" and self.policy_mode != "outside_policy":
            raise ValueError("Unlisted tools must be outside_policy")
        if self.at.tzinfo is None:
            raise ValueError("Action time must include a timezone")
        path = Path(self.raw_log_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Raw log path must stay relative to the log directory")
        return self


class Proposal(Strict):
    claim_key: str = Field(min_length=1)
    value: JsonValue
    source_url: HttpUrl
    excerpt: str = Field(min_length=1)
    accessed_on: date
    scope: dict[str, str | None]
    supporting_steps: list[int] = Field(min_length=1)
    status: Literal["unreviewed"] = "unreviewed"


class ExpertTrace(Strict):
    schema_version: Literal["1"] = "1"
    case_id: str = Field(min_length=1)
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_pipeline_sha: str = Field(min_length=7)
    max_fetcher_calls: int = Field(ge=1)
    max_elapsed_ms: int = Field(ge=1)
    initial_fetcher_calls: int = Field(ge=0)
    initial_elapsed_ms: int = Field(ge=0)
    started_at: datetime
    ended_at: datetime
    actions: list[Action] = Field(min_length=1)
    proposals: list[Proposal] = Field(default_factory=list)
    review_status: Literal["unreviewed"] = "unreviewed"

    @model_validator(mode="after")
    def ordered_actions(self) -> Self:
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
            raise ValueError("Trace times must include a timezone")
        if self.ended_at < self.started_at:
            raise ValueError("Trace ends before it starts")
        if [action.step for action in self.actions] != list(range(1, len(self.actions) + 1)):
            raise ValueError("Actions must have consecutive 1-based steps")
        if len({action.raw_log_path for action in self.actions}) != len(self.actions):
            raise ValueError("Every action needs its own raw tool log")
        previous = self.started_at
        used_calls = self.initial_fetcher_calls
        used_ms = self.initial_elapsed_ms
        for action in self.actions:
            if not previous <= action.at <= self.ended_at:
                raise ValueError("Actions must be chronologically ordered within the trace")
            if action.step == 1 and action.observed_from_step is not None:
                raise ValueError("First action must observe the baseline packet")
            if action.step > 1 and (
                action.observed_from_step is None or action.observed_from_step >= action.step
            ):
                raise ValueError("Later actions must cite an earlier observation step")
            if action.fetcher_calls_cumulative < used_calls:
                raise ValueError("Fetcher call count must not decrease")
            if action.tool == "fetcher" and action.fetcher_calls_cumulative == used_calls:
                raise ValueError("A Fetcher action must consume a Fetcher call")
            if action.elapsed_ms_cumulative < used_ms + action.elapsed_ms:
                raise ValueError("Cumulative elapsed time must include the action")
            if action.policy_mode == "same_policy" and (
                action.fetcher_calls_cumulative > self.max_fetcher_calls
                or action.elapsed_ms_cumulative > self.max_elapsed_ms
            ):
                raise ValueError("Same-policy action exceeds the bounded run budget")
            previous = action.at
            used_calls = action.fetcher_calls_cumulative
            used_ms = action.elapsed_ms_cumulative
        steps = {action.step for action in self.actions}
        if any(set(proposal.supporting_steps) - steps for proposal in self.proposals):
            raise ValueError("Every proposed fact must cite recorded actions")
        for proposal in self.proposals:
            if not any(
                action.step in proposal.supporting_steps
                and action.tool in {"fetcher", "browser"}
                and action.policy_mode == "same_policy"
                and action.outcome_status == "success"
                and action.url == proposal.source_url
                for action in self.actions
            ):
                raise ValueError(
                    "Proposed evidence needs a same-policy page read of its source URL"
                )
        return self


def validate_trace(
    trace: dict[str, Any], packet: dict[str, Any], *, logs_dir: Path | None = None
) -> ExpertTrace:
    """Validate linkage and, when supplied, the bytes of recorded tool logs."""
    from .packet import digest

    parsed = ExpertTrace.model_validate(trace)
    if parsed.packet_sha256 != digest(packet):
        raise ValueError("Trace was not made against this exact packet")
    if parsed.case_id not in {case["case_id"] for case in packet["cases"]}:
        raise ValueError("Unknown case ID")
    if parsed.baseline_pipeline_sha != packet["baseline_pipeline_sha"]:
        raise ValueError("Wrong baseline pipeline")
    budget = packet["baseline_budget"]
    if (parsed.max_fetcher_calls, parsed.max_elapsed_ms) != (
        budget["max_fetcher_calls"],
        budget["max_elapsed_ms"],
    ):
        raise ValueError("Trace budget differs from the baseline packet")
    if not budget["browser_enabled"] and any(
        action.tool == "browser" and action.policy_mode == "same_policy"
        for action in parsed.actions
    ):
        raise ValueError("Browser action is outside the baseline policy")
    if logs_dir is not None:
        root = logs_dir.resolve()
        for action in parsed.actions:
            path = (root / action.raw_log_path).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Raw log path escapes the log directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != action.raw_log_sha256:
                raise ValueError(f"Raw tool log hash mismatch at step {action.step}")
    return parsed
