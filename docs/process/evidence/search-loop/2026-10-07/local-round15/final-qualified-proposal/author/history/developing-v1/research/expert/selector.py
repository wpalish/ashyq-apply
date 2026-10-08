"""Meter every isolated selector process, including failed or unfinished turns."""

from __future__ import annotations

import json
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .blind_cli import Isolation, selector_answer


@dataclass(frozen=True)
class SelectorTurn:
    answer: dict[str, Any] | None
    elapsed_ms: int
    stdout: str
    stderr: str
    returncode: int | None
    error_kind: str | None


def _text(value: str | bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def select(
    isolation: Isolation,
    schema: Path,
    output: Path,
    prompt: dict[str, Any],
    *,
    timeout_seconds: float,
    model: str | None = None,
    timeout_policy: str = "legacy_active",
) -> SelectorTurn:
    """Only completed, tool-free, exact output files can supply an answer.

    Partial timeout output is preserved for audit but never promoted to facts.
    File validation/parsing is included in this measured turn. An unavailable
    policy fails before spawning anything, so it cannot consume provider I/O.
    """
    if timeout_policy not in {"legacy_active", "expert_wall_only"}:
        raise ValueError("Unknown selector timeout policy")
    ceiling = 900 if timeout_policy == "expert_wall_only" else 55
    if not 0 < timeout_seconds <= ceiling:
        raise ValueError("Selector timeout exceeds its declared policy")
    command = isolation.command(schema, output=output, model=model)
    answer, stdout, stderr, code, error = None, "", "", None, None
    began = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=isolation.workspace,
            input=json.dumps(prompt, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
        if code or not output.is_file():
            error = "selector_process_failed"
        else:
            try:
                answer = selector_answer(stdout, output.read_text())
            except (ValueError, json.JSONDecodeError):
                error = "selector_output_rejected"
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = _text(exc.stdout), _text(exc.stderr)
        error = "selector_timeout"
    except OSError:
        error = "selector_process_unavailable"
    finally:
        elapsed_ms = math.ceil((time.monotonic() - began) * 1000)
    return SelectorTurn(answer, elapsed_ms, stdout, stderr, code, error)
