"""A cancelled expert consumes time without creating evidence or fresh retries."""

import json
import subprocess
from pathlib import Path

import pytest

from evaluation.research.expert.blind_cli import Isolation
from evaluation.research.expert.selector import select


def policy(tmp_path: Path) -> Isolation:
    tmp_path.mkdir(exist_ok=True)
    return Isolation(tmp_path, (tmp_path.parent / "sealed",), "/sandbox", "/codex")


def clock(monkeypatch, *values):
    ticks = iter(values)
    monkeypatch.setattr("evaluation.research.expert.selector.time.monotonic", lambda: next(ticks))


def test_timeout_charges_elapsed_time_and_preserves_partial_stream(tmp_path, monkeypatch):
    clock(monkeypatch, 1, 56.125)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            "selector", 55, output=b'{"partial":true}', stderr=b"unfinished"
        )

    monkeypatch.setattr("evaluation.research.expert.selector.subprocess.run", timeout)
    result = select(
        policy(tmp_path), tmp_path / "schema", tmp_path / "answer", {}, timeout_seconds=55
    )
    assert result.elapsed_ms == 55125
    assert result.error_kind == "selector_timeout"
    assert result.stdout == '{"partial":true}' and result.stderr == "unfinished"
    assert result.answer is None


def test_failed_process_consumes_time_without_accepting_output(tmp_path, monkeypatch):
    clock(monkeypatch, 1, 3)
    monkeypatch.setattr(
        "evaluation.research.expert.selector.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "no", "failed"),
    )
    result = select(
        policy(tmp_path), tmp_path / "schema", tmp_path / "answer", {}, timeout_seconds=5
    )
    assert result.elapsed_ms == 2000 and result.error_kind == "selector_process_failed"
    assert result.answer is None


def test_success_uses_isolated_cwd_requested_model_and_exact_completed_stream(
    tmp_path, monkeypatch
):
    clock(monkeypatch, 1, 1.5)
    output = tmp_path / "answer"

    def completed(command, **kwargs):
        assert kwargs["cwd"] == tmp_path
        assert command[command.index("--model") + 1] == "gpt-6-astra"
        output.write_text('{"decision":"act"}')
        stream = "\n".join(
            json.dumps(v)
            for v in [
                {"type": "thread.started", "thread_id": "fresh"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": output.read_text()},
                },
                {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
            ]
        )
        return subprocess.CompletedProcess(command, 0, stream, "")

    monkeypatch.setattr("evaluation.research.expert.selector.subprocess.run", completed)
    result = select(
        policy(tmp_path), tmp_path / "schema", output, {}, timeout_seconds=5, model="gpt-6-astra"
    )
    assert result.answer == {"decision": "act"} and result.elapsed_ms == 500
    assert result.error_kind is None


def test_unfinished_stream_and_stale_output_never_supply_facts(tmp_path, monkeypatch):
    clock(monkeypatch, 1, 2)
    output = tmp_path / "answer"

    def unfinished(command, **kwargs):
        output.write_text('{"facts":["untrusted"]}')
        return subprocess.CompletedProcess(command, 0, '{"type":"turn.started"}', "")

    monkeypatch.setattr("evaluation.research.expert.selector.subprocess.run", unfinished)
    result = select(policy(tmp_path), tmp_path / "schema", output, {}, timeout_seconds=5)
    assert result.answer is None and result.error_kind == "selector_output_rejected"
    with pytest.raises(ValueError, match="fresh"):
        select(policy(tmp_path), tmp_path / "schema", output, {}, timeout_seconds=5)


@pytest.mark.parametrize("timeout", [0, -1, 56])
def test_invalid_deadline_fails_before_spawning(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout"):
        select(
            policy(tmp_path), tmp_path / "schema", tmp_path / "answer", {}, timeout_seconds=timeout
        )
