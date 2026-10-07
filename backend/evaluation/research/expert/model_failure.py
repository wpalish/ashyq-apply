"""Recognize authoritative selector failures without reading source or answer text.

This pure policy supplies an audit reason for a prospective parent's shared stop.
Raw streams stay in their original receipts. It neither changes the selector,
network counters, effort or wall guard nor authorizes a retry or another model.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

TRANSPORT_FAILURES = frozenset(
    {"selector_process_failed", "selector_process_unavailable", "selector_output_rejected"}
)
USAGE_CODES = frozenset(
    {"usage_limit_reached", "quota_exceeded", "insufficient_quota", "rate_limit_exceeded"}
)
AUTH_CODES = frozenset(
    {"authentication_error", "invalid_api_key", "token_expired", "account_deactivated"}
)


def model_batch_failure(stdout: str, *, error_kind: str | None) -> dict[str, Any] | None:
    """Stop on failed model transport; distinguish only trusted error events.

    A completed agent message mentioning quota, a page, stderr or a normal
    per-case guard timeout is not evidence of an account refusal. Unknown
    process failures still stop the batch, without guessing their cause.
    """
    stream_sha256 = hashlib.sha256(stdout.encode()).hexdigest()
    terminal_errors: list[tuple[int, str, dict[str, Any]]] = []
    for index, line in enumerate(stdout.splitlines(), start=1):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if event_type == "turn.completed":
            terminal_errors.clear()
        elif event_type in {"error", "turn.failed"}:
            payload = event.get("error") if event_type == "turn.failed" else event
            terminal_errors.append(
                (index, event_type, payload if isinstance(payload, dict) else {})
            )

    # Only the original terminal event sequence decides whether model failure
    # exists. Editable metadata can describe it, but cannot erase it. A later
    # completed turn clears stale attribution, while a canonical process failure
    # still requires an unknown transport stop even if that turn completed.
    if not terminal_errors and error_kind not in TRANSPORT_FAILURES:
        return None
    kind = "model_transport_failure"
    event_line, failure_type = terminal_errors[0][:2] if terminal_errors else (None, None)
    for index, event_type, payload in terminal_errors:
        message, code = payload.get("message"), payload.get("code")
        normalized = message.casefold().replace("\u2019", "'") if isinstance(message, str) else ""
        specific_kind = None
        if (isinstance(code, str) and code in USAGE_CODES) or any(
            phrase in normalized
            for phrase in ("hit your usage limit", "usage limit reached", "insufficient quota")
        ):
            specific_kind = "model_usage_limit"
        elif (isinstance(code, str) and code in AUTH_CODES) or any(
            phrase in normalized
            for phrase in (
                "authentication failed",
                "authentication error",
                "please log in",
                "please login",
                "invalid api key",
            )
        ):
            specific_kind = "model_authentication_refusal"
        if specific_kind is None:
            continue
        kind, event_line, failure_type = specific_kind, index, event_type
        break
    return {
        "kind": kind,
        "selector_error_kind": error_kind,
        "event_line": event_line,
        "event_type": failure_type,
        "stream_sha256": stream_sha256,
    }
