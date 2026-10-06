"""Prospective V7 isolated selection under one absolute case hang guard.

Model thinking never advances the source-action ledger or consumes its 60/6
network limits. It still runs inside the same immutable 900 second case guard.
No smaller phase timeout, reasoning-effort override, fresh guard or retry is
introduced here. A completed response is only transport data: the original
journal, every citation, raw source and outer wall-clock gates remain required.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from .blind_cli import DISABLED_FEATURES, SELECTOR_INSTRUCTIONS, Isolation, selector_answer
from .journal import JournalDecision
from .network_budget import (
    BUDGET_MODEL,
    MAX_FETCHER_CALLS,
    MAX_SEARCH_QUERIES,
    NETWORK_COMPARISON_MODE,
    WALL_GUARD_MS,
    WallGuard,
)
from .representation import closing_schema, journal_schema_for_case, parse_bound_journal_decision
from .selector import SelectorTurn

TurnPhase = Literal["bootstrap", "data", "minimal_commit"]
POLICY_VERSION = "1"
ASTRA_MODEL = "gpt-6-astra"
MAX_NEW_FACTS = 4
MAX_NEW_FINDINGS = 2


def _phase(value: TurnPhase) -> TurnPhase:
    if type(value) is not str or value not in {"bootstrap", "data", "minimal_commit"}:
        raise ValueError("Turn phase must be bootstrap, data or minimal_commit")
    return cast(TurnPhase, value)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TurnWindow:
    phase: TurnPhase
    wall_guard: WallGuard
    observed_at: datetime
    remaining_ms: int
    remaining_seconds: float

    @property
    def timeout_seconds(self) -> float | None:
        return self.remaining_seconds if self.remaining_seconds > 0 else None

    @property
    def timeout_ms(self) -> float | None:
        # Preserve a positive fraction below 1ms without rounding up the guard.
        return None if self.timeout_seconds is None else self.timeout_seconds * 1000

    @property
    def status(self) -> Literal["available", "no_available_window"]:
        return "available" if self.timeout_seconds is not None else "no_available_window"

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "wall_guard": self.wall_guard.as_dict(),
            "observed_at": self.observed_at.isoformat(),
            "remaining_ms": self.remaining_ms,
            "remaining_seconds": self.remaining_seconds,
            "timeout_ms": self.timeout_ms,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status,
        }


def turn_window(
    *,
    phase: TurnPhase,
    wall_guard: WallGuard,
    now: datetime | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> TurnWindow:
    """Use only the remaining immutable guard, including its sub-ms precision."""
    selected = _phase(phase)
    if not isinstance(wall_guard, WallGuard):
        raise ValueError("Selector requires the immutable case WallGuard")
    observed = clock() if now is None else now
    seconds = wall_guard.remaining_seconds(now=observed)
    return TurnWindow(
        selected,
        wall_guard,
        observed.astimezone(UTC),
        wall_guard.remaining_ms(now=observed),
        seconds,
    )


def journal_schema_for_turn(
    *, journal_sha256: str, canonical_university: str, phase: TurnPhase
) -> dict[str, Any]:
    selected = _phase(phase)
    if selected == "minimal_commit":
        return closing_schema(journal_sha256=journal_sha256)
    schema = journal_schema_for_case(
        journal_sha256=journal_sha256, canonical_university=canonical_university
    )
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
    selected = _phase(phase)
    parsed = parse_bound_journal_decision(
        value,
        journal_sha256=journal_sha256,
        canonical_university=canonical_university,
        closing_only=selected == "minimal_commit",
    )
    if len(parsed.facts) > MAX_NEW_FACTS:
        raise ValueError("Network turn permits at most four facts")
    if len(parsed.question_findings) > MAX_NEW_FINDINGS:
        raise ValueError("Network turn permits at most two question findings")
    return parsed


def policy_limits() -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "comparison_mode": NETWORK_COMPARISON_MODE,
        "budget_model": BUDGET_MODEL,
        "model": ASTRA_MODEL,
        "model_reasoning_effort": None,
        "reasoning_override": None,
        "reasoning_effort_source": "cli_default",
        "model_thinking_included": False,
        "max_calls": MAX_FETCHER_CALLS,
        "max_search_queries": MAX_SEARCH_QUERIES,
        "wall_guard_ms": WALL_GUARD_MS,
        "selector_timeout_basis": "remaining_absolute_wall_guard",
        "max_new_facts": MAX_NEW_FACTS,
        "max_new_findings": MAX_NEW_FINDINGS,
    }


def policy_card() -> str:
    return (
        "Expert network limits are 60 controlled page reads and six provider queries "
        "per case. Model thinking consumes neither these network actions nor the "
        "controller source-time ledger. Model selection, queueing, source work, "
        "validation and finalization all remain inside one immutable absolute "
        "15-minute (900000ms) case hang guard. Each selector gets only its remaining "
        "guard time; no smaller bootstrap/data/minimal-commit timeout or reserve is "
        "imposed. The isolated model is gpt-6-astra with normal CLI default reasoning "
        "effort and no explicit effort override; the actual service default is not "
        "asserted. Provide at most four new facts and two new findings per completed "
        "data delta. Minimal commit is an empty hash-only submit. Preserve original "
        "typed values, source-literal scope, exact quotations and coordinates. All "
        "original journal/raw-log/citation and outer wall-clock acceptance gates "
        "remain mandatory. Partial responses and responses after the case guard "
        "cannot be accepted. This policy permits no retry or guard renewal."
    )


def _absolute(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts:
        raise ValueError("Selector paths must use exact absolute canonical spelling")
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("Selector paths must already be canonical and cannot be aliases")


class NetworkBudgetIsolation(Isolation):
    """The exact tool-free Astra wrapper without a reasoning-effort override."""

    @classmethod
    def local(cls, workspace: Path, sealed_roots: list[Path]) -> NetworkBudgetIsolation:
        return cast(NetworkBudgetIsolation, super().local(workspace, sealed_roots))

    def command(self, schema: Path, *, output: Path, model: str | None = None) -> list[str]:
        if model is not None and (type(model) is not str or model != ASTRA_MODEL):
            raise ValueError("Network selector requires the exact gpt-6-astra model")
        for path in (self.workspace, schema, output):
            _absolute(path)
        return super().command(schema, output=output, model=ASTRA_MODEL)


def command_proof(command: Sequence[str]) -> dict[str, Any]:
    """Prove exact default-effort argv; parent still binds paths and OS isolation."""
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
            raise ValueError("Selector command needs each known option exactly once")
        index = argv.index(option)
        if index + 1 >= len(argv):
            raise ValueError("Selector command option is missing its argument")
        return argv[index + 1]

    if argument("--model") != ASTRA_MODEL:
        raise ValueError("Selector command must request exact Astra")
    workspace = argument("-C")
    schema, output = argument("--output-schema"), argument("--output-last-message")
    for spelling in (workspace, schema, output):
        path = Path(spelling)
        if not path.is_absolute() or str(path) != spelling or ".." in path.parts:
            raise ValueError("Selector argv paths must retain absolute canonical spelling")
    if not Path(schema).is_relative_to(workspace) or not Path(output).is_relative_to(workspace):
        raise ValueError("Selector argv files must remain inside their declared workspace")
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
        workspace,
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
        schema,
        "--output-last-message",
        output,
        "--json",
        "-",
    ]
    if argv != expected:
        raise ValueError("Selector command must retain exact isolation and no effort override")
    encoded = json.dumps(argv, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return {
        "policy_version": POLICY_VERSION,
        "model": ASTRA_MODEL,
        "model_reasoning_effort": None,
        "reasoning_override": None,
        "reasoning_effort_source": "cli_default",
        "command": argv,
        "argv_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }


@dataclass(frozen=True)
class NetworkSelectorTurn(SelectorTurn):
    window: TurnWindow
    selector_started_at: str
    selector_finished_at: str


def _text(value: str | bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def select(
    isolation: NetworkBudgetIsolation,
    schema: Path,
    output: Path,
    prompt: dict[str, Any],
    *,
    wall_guard: WallGuard,
    phase: TurnPhase,
    model: str | None = ASTRA_MODEL,
    clock: Callable[[], datetime] = utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    environment: Mapping[str, str] | None = None,
) -> NetworkSelectorTurn:
    """Spawn once within the remaining guard, preserving every failed stream.

    The exact pre-spawn window is returned for audit. It includes command and
    prompt preparation time; queueing/process work uses that window alone.
    Recheck expiry after output replay before exposing any answer. The parent
    must separately gate subsequent bound parsing, journal and source proof.
    """
    if not isinstance(isolation, NetworkBudgetIsolation):
        raise ValueError("Network selector requires the default-effort isolated wrapper")
    explicit_environment = None
    if environment is not None:
        if not isinstance(environment, Mapping) or any(
            not isinstance(key, str)
            or not key
            or "=" in key
            or "\0" in key
            or not isinstance(value, str)
            or "\0" in value
            for key, value in environment.items()
        ):
            raise ValueError("Selector environment must be an explicit string mapping")
        explicit_environment = dict(environment)
    environment_arguments: dict[str, Any] = (
        {"env": explicit_environment} if explicit_environment is not None else {}
    )
    began = monotonic()
    window = turn_window(phase=phase, wall_guard=wall_guard, clock=clock)
    ended = window.observed_at
    answer, stdout, stderr, code, error = None, "", "", None, None
    if window.timeout_seconds is not None:
        argv = isolation.command(schema, output=output, model=model)
        command_proof(argv)
        payload = json.dumps(prompt, ensure_ascii=False, allow_nan=False)
        next_window = turn_window(phase=phase, wall_guard=wall_guard, clock=clock)
        if next_window.observed_at < window.observed_at:
            raise ValueError("Selector wall clock moved backwards before dispatch")
        window = next_window
    try:
        if window.timeout_seconds is None:
            error = "selector_wall_guard_exhausted"
        else:
            completed = subprocess.run(
                argv,
                cwd=isolation.workspace,
                input=payload,
                text=True,
                capture_output=True,
                timeout=window.timeout_seconds,
                check=False,
                **environment_arguments,
            )
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
            if code or not output.is_file():
                error = "selector_process_failed"
            else:
                try:
                    for path in (isolation.workspace, schema, output):
                        _absolute(path)
                    if output.stat().st_nlink != 1:
                        raise ValueError("Selector output must remain a single-link regular file")
                    answer = selector_answer(stdout, output.read_text())
                except (ValueError, json.JSONDecodeError):
                    error = "selector_output_rejected"
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = _text(exc.stdout), _text(exc.stderr)
        error = "selector_timeout"
    except OSError:
        error = "selector_process_unavailable"
    finally:
        try:
            finished = clock()
            remaining = wall_guard.remaining_seconds(now=finished)
            ended = finished.astimezone(UTC)
            if ended < window.observed_at:
                answer, error = None, "selector_wall_clock_invalid"
            elif remaining <= 0:
                answer = None
                error = error or "selector_wall_guard_exhausted"
        except ValueError:
            answer, error = None, "selector_wall_clock_invalid"
        elapsed_ms = math.ceil((monotonic() - began) * 1000)
        if elapsed_ms < 0:
            raise ValueError("Selector monotonic clock moved backwards")
    return NetworkSelectorTurn(
        answer,
        elapsed_ms,
        stdout,
        stderr,
        code,
        error,
        window,
        window.observed_at.isoformat(),
        ended.isoformat(),
    )
