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
    if error_kind is None:
        return None
    stream_sha256 = hashlib.sha256(stdout.encode()).hexdigest()
    for index, line in enumerate(stdout.splitlines(), start=1):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("type") not in {"error", "turn.failed"}:
            continue
        payload = event.get("error") if event.get("type") == "turn.failed" else event
        if not isinstance(payload, dict):
            continue
        message, code = payload.get("message"), payload.get("code")
        normalized = message.casefold().replace("\u2019", "'") if isinstance(message, str) else ""
        kind = None
        if (isinstance(code, str) and code in USAGE_CODES) or any(
            phrase in normalized
            for phrase in ("hit your usage limit", "usage limit reached", "insufficient quota")
        ):
            kind = "model_usage_limit"
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
            kind = "model_authentication_refusal"
        if kind is not None:
            return {
                "kind": kind,
                "selector_error_kind": error_kind,
                "event_line": index,
                "event_type": event["type"],
                "stream_sha256": stream_sha256,
            }
    if error_kind in TRANSPORT_FAILURES:
        return {
            "kind": "model_transport_failure",
            "selector_error_kind": error_kind,
            "event_line": None,
            "event_type": None,
            "stream_sha256": stream_sha256,
        }
    return None
