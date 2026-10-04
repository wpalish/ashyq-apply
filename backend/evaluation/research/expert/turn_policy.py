"""Pure V5 selector limits within the original strict evaluation clock.

The caller supplies cumulative active milliseconds from its first case clock.
These windows do not meter work, reset that clock, accept a journal, retry a
provider, or salvage a partial selector response. Full trace/citation gates and
the unchanged controller remain the caller's responsibility.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from .blind_cli import DISABLED_FEATURES, SELECTOR_INSTRUCTIONS, Isolation
from .journal import JournalDecision
from .representation import (
    closing_schema,
    journal_schema_for_case,
    parse_bound_journal_decision,
)

TurnPhase = Literal["bootstrap", "data", "minimal_commit"]
POLICY_VERSION = "1"
ASTRA_MODEL = "gpt-6-astra"
REASONING_EFFORT = "low"
REASONING_OVERRIDE = 'model_reasoning_effort="low"'
MAX_MS = 120000
MAX_CALLS = 60
MAX_SEARCH_QUERIES = 6
SOURCE_DEADLINE_MS = 95000
MAX_NEW_FACTS = 4
MAX_NEW_FINDINGS = 2
MECHANICAL_VALIDATION_RESERVE_MS = 3000
MINIMAL_COMMIT_RESERVE_MS = 10000
_PHASE_CAP_MS: dict[TurnPhase, int] = {
    "bootstrap": 30000,
    "data": 55000,
    "minimal_commit": 10000,
}


def _phase(value: TurnPhase) -> TurnPhase:
    if type(value) is not str or value not in _PHASE_CAP_MS:
        raise ValueError("Turn phase must be bootstrap, data or minimal_commit")
    return cast(TurnPhase, value)


@dataclass(frozen=True, slots=True)
class TurnWindow:
    """A selector allowance; nonpositive available time never starts a turn."""

    phase: TurnPhase
    active_ms: int
    cap_ms: int
    reserved_ms: int
    remaining_ms: int
    available_ms: int
    timeout_ms: int | None

    @property
    def timeout_seconds(self) -> float | None:
        return None if self.timeout_ms is None else self.timeout_ms / 1000

    @property
    def status(self) -> Literal["available", "no_available_window"]:
        return "no_available_window" if self.timeout_ms is None else "available"

    @property
    def deadline_ms(self) -> int | None:
        return None if self.timeout_ms is None else self.active_ms + self.timeout_ms

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "active_ms": self.active_ms,
            "cap_ms": self.cap_ms,
            "reserved_ms": self.reserved_ms,
            "remaining_ms": self.remaining_ms,
            "available_ms": self.available_ms,
            "timeout_ms": self.timeout_ms,
            "timeout_seconds": self.timeout_seconds,
            "deadline_ms": self.deadline_ms,
            "status": self.status,
        }


def turn_window(*, phase: TurnPhase, active_ms: int) -> TurnWindow:
    """Reserve closure/validation inside 120000 ms, without rounding or reset.

    Actual overruns remain visible as negative remaining/available milliseconds.
    A 1 ms positive window stays 0.001 seconds; unavailable windows return None,
    rather than gaining a minimum timeout or fresh allowance.
    """
    selected = _phase(phase)
    if type(active_ms) is not int or active_ms < 0:
        raise ValueError("Active case time must be a nonnegative integer number of milliseconds")
    reserve = MECHANICAL_VALIDATION_RESERVE_MS
    if selected != "minimal_commit":
        reserve += MINIMAL_COMMIT_RESERVE_MS
    remaining = MAX_MS - active_ms
    available = remaining - reserve
    cap = _PHASE_CAP_MS[selected]
    return TurnWindow(
        phase=selected,
        active_ms=active_ms,
        cap_ms=cap,
        reserved_ms=reserve,
        remaining_ms=remaining,
        available_ms=available,
        timeout_ms=min(cap, available) if available > 0 else None,
    )


def journal_schema_for_turn(
    *, journal_sha256: str, canonical_university: str, phase: TurnPhase
) -> dict[str, Any]:
    """Wrap the unchanged bound schema with four-fact/two-finding delta caps."""
    selected = _phase(phase)
    schema = journal_schema_for_case(
        journal_sha256=journal_sha256, canonical_university=canonical_university
    )
    if selected == "minimal_commit":
        return closing_schema(journal_sha256=journal_sha256)
    schema["properties"]["facts"]["maxItems"] = MAX_NEW_FACTS
    schema["properties"]["question_findings"]["maxItems"] = MAX_NEW_FINDINGS
    return schema


def parse_turn_decision(
    value: JournalDecision | str | Mapping[str, Any],
    *,
    journal_sha256: str,
    canonical_university: str,
    phase: TurnPhase,
) -> JournalDecision:
    """Revalidate the original model and reject oversized deltas in full."""
    selected = _phase(phase)
    parsed = parse_bound_journal_decision(
        value,
        journal_sha256=journal_sha256,
        canonical_university=canonical_university,
        closing_only=selected == "minimal_commit",
    )
    if len(parsed.facts) > MAX_NEW_FACTS:
        raise ValueError("V5 turn permits at most four facts")
    if len(parsed.question_findings) > MAX_NEW_FINDINGS:
        raise ValueError("V5 turn permits at most two question findings")
    return parsed


def policy_limits() -> dict[str, Any]:
    """Fresh public metadata; the source controller enforces its own caps."""
    return {
        "policy_version": POLICY_VERSION,
        "model": ASTRA_MODEL,
        "model_reasoning_effort": REASONING_EFFORT,
        "max_ms": MAX_MS,
        "max_calls": MAX_CALLS,
        "max_search_queries": MAX_SEARCH_QUERIES,
        "source_deadline_ms": SOURCE_DEADLINE_MS,
        "max_new_facts": MAX_NEW_FACTS,
        "max_new_findings": MAX_NEW_FINDINGS,
        "mechanical_validation_reserve_ms": MECHANICAL_VALIDATION_RESERVE_MS,
        "minimal_commit_reserve_ms": MINIMAL_COMMIT_RESERVE_MS,
        "phase_cap_ms": dict(_PHASE_CAP_MS),
    }


def policy_card() -> str:
    """Public transport instructions only; no source facts or private identity."""
    return (
        "V5 turn limits: provide at most four new facts and two new question findings "
        "in each complete bootstrap/data response. Keep original typed values, exact "
        "quotations, coordinates and declared scope. Refer to retained facts by ID; "
        "do not repeat the accepted journal. Minimal commit copies only the accepted "
        "journal hash with no action, new facts or findings. The selector is explicit "
        'gpt-6-astra with model_reasoning_effort="low". The original cumulative case '
        "clock is 120000 ms with 60 page-read calls and six provider queries; source "
        "navigation ends at 95000 ms. Bootstrap/data caps are 30000/55000 ms, retaining "
        "10000 ms for minimal commit and 3000 ms for mechanical validation inside "
        "the case clock. Minimal commit is capped at 10000 ms and retains 3000 ms "
        "for validation. No available window ends selection. Partial text cannot "
        "be accepted. Every timeout and all finalization remain charged to the "
        "original clock; this policy grants no retry or additional allowance."
    )


class AstraLowEffortIsolation(Isolation):
    """The existing tool-free isolation plus one explicit Astra effort setting."""

    def command(self, schema: Path, *, output: Path, model: str | None = None) -> list[str]:
        if model is not None and (type(model) is not str or model != ASTRA_MODEL):
            raise ValueError("V5 selector requires the exact gpt-6-astra model")
        command = super().command(schema, output=output, model=ASTRA_MODEL)
        return [*command[:-1], "-c", REASONING_OVERRIDE, command[-1]]


def command_proof(command: Sequence[str]) -> dict[str, Any]:
    """Hash an exact wrapper argv, without reading files or executing a command.

    This records requested effort, not the unknown previous default or an
    execution result. The parent binds this argv to its metered selector call
    and separately proves OS isolation. The command has only the known base
    options plus the exact low-effort override; conflicting options fail closed.
    """
    if (
        isinstance(command, str | bytes)
        or not isinstance(command, Sequence)
        or any(type(arg) is not str or not arg for arg in command)
    ):
        raise ValueError("Selector command must be exact nonempty string argv")
    argv = list(command)
    if len(argv) < 7 or argv[1] != "-p" or argv[4] != "exec":
        raise ValueError("Selector command must use the known isolated CLI shape")

    def argument(option: str) -> str:
        if argv.count(option) != 1:
            raise ValueError("Selector command must have each known option exactly once")
        index = argv.index(option)
        if index + 1 >= len(argv):
            raise ValueError("Selector command option is missing its argument")
        return argv[index + 1]

    if argument("--model") != ASTRA_MODEL:
        raise ValueError("Selector command must request exact Astra")
    flags = [part for feature in DISABLED_FEATURES for part in ("--disable", feature)]
    expected = [
        *argv[:5],
        "--model",
        ASTRA_MODEL,
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-C",
        argument("-C"),
        "-c",
        "project_doc_max_bytes=0",
        "-c",
        'web_search="disabled"',
        "-c",
        f"instructions={json.dumps(SELECTOR_INSTRUCTIONS)}",
        "-c",
        'developer_instructions=""',
        *flags,
        "--output-schema",
        argument("--output-schema"),
        "--output-last-message",
        argument("--output-last-message"),
        "--json",
        "-c",
        REASONING_OVERRIDE,
        "-",
    ]
    if argv != expected:
        raise ValueError("Selector command must retain isolation and the exact low effort override")
    encoded = json.dumps(argv, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return {
        "policy_version": POLICY_VERSION,
        "model": ASTRA_MODEL,
        "model_reasoning_effort": REASONING_EFFORT,
        "reasoning_override": REASONING_OVERRIDE,
        "command": argv,
        "argv_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }
