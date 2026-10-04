"""A fresh expert cannot run tools or read sealed local answer roots."""

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from evaluation.research.expert.blind_cli import (
    DISABLED_CODE_MODE_DIAGNOSTIC,
    Isolation,
    selector_answer,
)


def isolated(tmp_path: Path) -> Isolation:
    return Isolation(tmp_path / "expert", (tmp_path / "sealed",), "/sandbox", "/codex")


def sentinels(policy: Isolation) -> tuple[Path, Path]:
    allowed = policy.workspace / "allowed"
    sealed = policy.sealed_roots[0] / "sealed"
    allowed.parent.mkdir(parents=True)
    sealed.parent.mkdir(parents=True)
    allowed.write_bytes(b"allowed")
    sealed.write_bytes(b"sealed harmless fixture")
    return allowed, sealed


def completed_stream(answer: str) -> str:
    return "\n".join(
        json.dumps(record)
        for record in (
            {"type": "thread.started", "thread_id": "fresh-expert"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": answer}},
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
        )
    )


def test_selector_does_not_load_local_context_or_expose_research_tools(tmp_path: Path) -> None:
    policy = isolated(tmp_path)
    command = policy.command(policy.workspace / "schema.json", output=policy.workspace / "answer")
    assert "--ignore-user-config" in command
    assert "--ephemeral" in command
    assert "project_doc_max_bytes=0" in command
    assert 'web_search="disabled"' in command
    for name in ("shell_tool", "unified_exec", "apps", "memories", "multi_agent"):
        assert command[command.index(name) - 1] == "--disable"
    assert str(policy.sealed_roots[0]) in policy.profile()
    assert "CODEX_HOME" not in " ".join(command)


def test_unavailable_isolation_and_overlapping_workspace_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("evaluation.research.expert.blind_cli.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="requires"):
        Isolation.local(tmp_path / "expert", [tmp_path / "sealed"])
    monkeypatch.setattr("evaluation.research.expert.blind_cli.shutil.which", lambda name: "/x")
    with pytest.raises(ValueError, match="Separate"):
        Isolation.local(tmp_path / "sealed" / "expert", [tmp_path / "sealed"])


def test_output_files_cannot_leave_selector_workspace(tmp_path: Path) -> None:
    policy = isolated(tmp_path)
    with pytest.raises(ValueError, match="schema"):
        policy.command(tmp_path / "schema", output=policy.workspace / "answer")
    with pytest.raises(ValueError, match="output"):
        policy.command(policy.workspace / "schema", output=tmp_path / "answer")


def test_preexisting_output_cannot_masquerade_as_a_fresh_answer(tmp_path: Path) -> None:
    policy = isolated(tmp_path)
    policy.workspace.mkdir()
    output = policy.workspace / "answer"
    output.write_text('{"action":"stop"}')
    with pytest.raises(ValueError, match="fresh"):
        policy.command(policy.workspace / "schema", output=output)


def test_sentinel_probe_rejects_an_unenforced_access_policy(tmp_path, monkeypatch) -> None:
    policy = isolated(tmp_path)
    allowed, sealed = sentinels(policy)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 0, stdout=b"data", stderr=b"")

    monkeypatch.setattr("evaluation.research.expert.blind_cli.subprocess.run", run)
    with pytest.raises(RuntimeError, match="proof failed"):
        policy.prove_access(allowed, sealed)
    assert [c[-1] for c in calls] == [str(allowed), str(sealed)]


def test_sentinel_probe_checks_both_allowed_and_denied_reads(tmp_path, monkeypatch) -> None:
    policy = isolated(tmp_path)
    allowed, sealed = sentinels(policy)

    def run(command, **kwargs):
        return CompletedProcess(
            command,
            0 if command[-1] == str(allowed) else 1,
            stdout=b"allowed" if command[-1] == str(allowed) else b"",
            stderr=b"" if command[-1] == str(allowed) else b"cat: Operation not permitted",
        )

    monkeypatch.setattr("evaluation.research.expert.blind_cli.subprocess.run", run)
    proof = policy.prove_access(allowed, sealed)
    assert proof["sealed_read_denied"] and proof["sealed_stdout_empty"]
    assert proof["persistent_session"] is False


def test_missing_sealed_fixture_is_not_an_access_denial(tmp_path, monkeypatch) -> None:
    policy = isolated(tmp_path)
    allowed, sealed = sentinels(policy)
    sealed.unlink()
    calls = []
    monkeypatch.setattr(
        "evaluation.research.expert.blind_cli.subprocess.run",
        lambda *args, **kwargs: calls.append(args),
    )
    with pytest.raises(ValueError, match="existing"):
        policy.prove_access(allowed, sealed)
    assert calls == []


def test_missing_file_error_is_not_accepted_as_permission_denial(tmp_path, monkeypatch) -> None:
    policy = isolated(tmp_path)
    allowed, sealed = sentinels(policy)

    def run(command, **kwargs):
        return CompletedProcess(
            command,
            0 if command[-1] == str(allowed) else 1,
            stdout=b"allowed" if command[-1] == str(allowed) else b"",
            stderr=b"" if command[-1] == str(allowed) else b"No such file or directory",
        )

    monkeypatch.setattr("evaluation.research.expert.blind_cli.subprocess.run", run)
    with pytest.raises(RuntimeError, match="proof failed"):
        policy.prove_access(allowed, sealed)


@pytest.mark.parametrize(
    "kind", ["command_execution", "mcp_tool_call", "web_search", "file_change"]
)
def test_tool_invocation_invalidates_the_blind_trace(kind: str) -> None:
    event = '{"type":"turn.started"}\n' + json.dumps(
        {"type": "item.completed", "item": {"type": kind}}
    )
    with pytest.raises(ValueError, match="non-text"):
        selector_answer(event, '{"action": "stop"}')


def test_text_only_json_answer_and_errors() -> None:
    answer = '{"action":"stop"}'
    assert selector_answer(completed_stream(answer), answer) == {"action": "stop"}
    with pytest.raises(ValueError, match="successfully"):
        selector_answer('{"type":"turn.failed"}', "{}")
    with pytest.raises(ValueError, match="object"):
        selector_answer(completed_stream("[]"), "[]")


@pytest.mark.parametrize(
    "events",
    [
        "",
        "[]",
        "{}",
        '{"type":"tool_call"}',
        '{"type":"mcp_tool_call"}',
        '{"type":"turn.started"}',
        '{"type":"turn.completed","usage":{"input_tokens":1}}',
        '{"type":"turn.started"}\n{"type":"item.completed","item":{}}',
    ],
)
def test_empty_unknown_and_incomplete_event_streams_fail_closed(events: str) -> None:
    with pytest.raises(ValueError):
        selector_answer(events, '{"action":"stop"}')


def test_final_output_must_match_completed_message() -> None:
    with pytest.raises(ValueError, match="differs"):
        selector_answer(completed_stream('{"action":"get"}'), '{"action":"stop"}')


def test_events_after_completed_turn_are_rejected() -> None:
    answer = '{"action":"stop"}'
    with pytest.raises(ValueError, match="after completion"):
        selector_answer(completed_stream(answer) + '\n{"type":"turn.started"}', answer)


def test_known_disabled_tool_capability_notice_can_precede_the_turn() -> None:
    answer = '{"action":"stop"}'
    events = completed_stream(answer).splitlines()
    notice = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "error", "message": DISABLED_CODE_MODE_DIAGNOSTIC},
        }
    )
    events.insert(1, notice)
    assert selector_answer("\n".join(events), answer) == {"action": "stop"}
    events.remove(notice)
    events.insert(2, notice)
    with pytest.raises(ValueError, match="non-text"):
        selector_answer("\n".join(events), answer)


def test_other_startup_errors_still_fail_closed() -> None:
    events = completed_stream('{"action":"stop"}').splitlines()
    events.insert(
        1,
        '{"type":"item.completed","item":{"type":"error","message":"could not isolate"}}',
    )
    with pytest.raises(ValueError, match="precedes"):
        selector_answer("\n".join(events), '{"action":"stop"}')
