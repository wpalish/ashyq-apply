"""Original failure shapes and adversarial source text; no model/network calls."""

import hashlib
import json

import pytest

from evaluation.research.expert.blind_cli import DISABLED_CODE_MODE_DIAGNOSTIC
from evaluation.research.expert.model_failure import model_batch_failure

LIMIT = "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage."


def stream(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


def test_original_v9_terminal_usage_refusal_stops_even_with_expected_startup_diagnostic():
    raw = stream(
        {"type": "thread.started", "thread_id": "synthetic"},
        {
            "type": "item.completed",
            "item": {"type": "error", "message": DISABLED_CODE_MODE_DIAGNOSTIC},
        },
        {"type": "turn.started"},
        {"type": "error", "message": LIMIT.replace("'", "\u2019")},
        {"type": "turn.failed", "error": {"message": LIMIT}},
    )
    failure = model_batch_failure(raw, error_kind="selector_process_failed")
    assert failure == {
        "kind": "model_usage_limit",
        "selector_error_kind": "selector_process_failed",
        "event_line": 4,
        "event_type": "error",
        "stream_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }


@pytest.mark.parametrize(
    "code", ["usage_limit_reached", "quota_exceeded", "insufficient_quota", "rate_limit_exceeded"]
)
def test_structured_terminal_quota_code_stops_without_message(code):
    raw = stream({"type": "turn.failed", "error": {"code": code}})
    assert (
        model_batch_failure(raw, error_kind="selector_process_failed")["kind"]
        == "model_usage_limit"
    )


@pytest.mark.parametrize("message", ["Authentication failed", "Please log in", "Invalid API key"])
def test_authoritative_authentication_refusal_stops(message):
    raw = stream({"type": "turn.failed", "error": {"message": message}})
    assert (
        model_batch_failure(raw, error_kind="selector_process_failed")["kind"]
        == "model_authentication_refusal"
    )


@pytest.mark.parametrize(
    "code", ["authentication_error", "invalid_api_key", "token_expired", "account_deactivated"]
)
def test_structured_authentication_code_stops(code):
    raw = stream({"type": "error", "code": code})
    assert (
        model_batch_failure(raw, error_kind="selector_process_failed")["kind"]
        == "model_authentication_refusal"
    )


@pytest.mark.parametrize("error_kind", [None, "selector_timeout", "selector_wall_guard_exhausted"])
def test_answer_or_source_text_does_not_manufacture_account_refusal(error_kind):
    raw = stream(
        {"type": "item.completed", "item": {"type": "agent_message", "text": LIMIT}},
        {"type": "item.completed", "item": {"type": "reasoning", "text": LIMIT}},
        {"type": "turn.completed"},
    )
    assert model_batch_failure(raw, error_kind=error_kind) is None


def test_complete_turn_with_disabled_capability_diagnostic_is_not_global_failure():
    raw = stream(
        {
            "type": "item.completed",
            "item": {"type": "error", "message": DISABLED_CODE_MODE_DIAGNOSTIC},
        },
        {"type": "turn.started"},
        {"type": "turn.completed"},
    )
    assert model_batch_failure(raw, error_kind=None) is None


@pytest.mark.parametrize(
    "raw", ["", "not-json", "[]\nnull\n1\n", '{"type":"turn.failed","error":"unknown"}\n']
)
def test_unknown_process_failure_stops_without_guessing_quota(raw):
    failure = model_batch_failure(raw, error_kind="selector_process_failed")
    assert failure["kind"] == "model_transport_failure"
    assert failure["event_type"] is None


@pytest.mark.parametrize(
    "error_kind",
    ["selector_timeout", "selector_wall_guard_exhausted", "selector_wall_clock_invalid"],
)
def test_only_trusted_quota_receipt_promotes_other_terminal_error_to_shared_stop(error_kind):
    assert model_batch_failure("", error_kind=error_kind) is None
    raw = stream({"type": "turn.failed", "error": {"message": LIMIT}})
    assert model_batch_failure(raw, error_kind=error_kind)["kind"] == "model_usage_limit"


def test_completed_model_transport_cannot_be_reclassified_by_stale_error_event():
    raw = stream({"type": "error", "message": LIMIT}, {"type": "turn.completed"})
    assert model_batch_failure(raw, error_kind=None) is None
