"""Independent real batch/child parsers, mocked only external execution/capture.

No facts or corpus labels are loaded; arbitrary catalogue case ids are emitted
as empty observations. The fake pipeline SHA is explicitly test-only.
"""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.search import intent
from evaluation.research import live
from evaluation.research.schema import Capture, Observation

ROOT = Path(__file__).resolve().parent
CASE_IDS = ["offline-test-a", "offline-test-b"]


def run_batch(tmp_path, monkeypatch, *, subject_args, initial_subject=False,
              shared_default=True, shared_explicit=False, stop_before=False,
              stop_after_first=False):
    monkeypatch.setattr(live_discovery, "SUBJECT_PHRASE_MATCH", initial_subject)
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", shared_default)
    monkeypatch.setattr("evaluation.research.expert.catalogue.load_catalogue",
                        lambda: SimpleNamespace(identities=[SimpleNamespace(id=i, domain="offline.example.edu") for i in CASE_IDS]))
    stop = tmp_path / "synthetic-STOP.json"
    if stop_before:
        stop.write_text('{"reason":"synthetic pre-start refusal"}')
    output_dir = tmp_path / "capture"
    arguments = ["live", "--live", "--catalogue-id", CASE_IDS[0],
                 "--catalogue-id", CASE_IDS[1], "--out", str(output_dir),
                 "--strict-expert-budget", "--stop-file", str(stop), *subject_args]
    if shared_explicit:
        arguments.append("--shared-query-budget")
    monkeypatch.setattr(sys, "argv", arguments)
    def mock_sha(command, **kwargs):
        assert command == ["git", "rev-parse", "HEAD"]
        return "a" * 40
    monkeypatch.setattr(subprocess, "check_output", mock_sha)
    commands = []
    child_effective = []
    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        child_effective.append({"subject_phrase_match": live_discovery.SUBJECT_PHRASE_MATCH,
                                "shared_query_budget": intent.SHARED_QUERY_BUDGET})
        output.write_text(Observation(case_id=case_id).model_dump_json())
        output.with_suffix(".budget.json").write_text(json.dumps({"stop_reason":"completed"}))
    monkeypatch.setattr(live, "capture_one", fake_capture)
    def fake_process(command, **kwargs):
        assert command[:3] == [sys.executable, "-m", "evaluation.research.live"]
        assert command.count("--subject-phrase-match") + command.count("--no-subject-phrase-match") == 1
        assert kwargs["env"]["UNIMATCH_ENABLE_BROWSER_TIER"] == "false"
        commands.append(command[3:])
        old_arguments = sys.argv
        try:
            sys.argv = ["mock-child", *command[3:]]
            live.main()  # Actual child parser and flag application; no capture/network work.
        finally:
            sys.argv = old_arguments
        if stop_after_first and len(commands) == 1:
            stop.write_text('{"reason":"synthetic refusal between cases"}')
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(subprocess, "run", fake_process)
    live.main()
    capture_path = next(output_dir.rglob("capture.json"))
    capture = Capture.model_validate_json(capture_path.read_text())
    row = {"subject_arguments": subject_args, "initial_subject": initial_subject,
           "shared_default": shared_default, "shared_explicit": shared_explicit,
           "stop_before": stop_before, "stop_after_first": stop_after_first,
           "child_effective": child_effective, "commands": commands,
           "capture": capture.model_dump(mode="json"),
           "pipeline_sha_is_mock": True, "network_calls": 0,
           "capture_one_is_mock": True, "real_subprocess_calls": 0}
    record = ROOT / "raw-controls" / (tmp_path.name + ".json")
    record.parent.mkdir(exist_ok=True)
    record.write_text(json.dumps(row, indent=2) + "\n")
    return capture, commands, child_effective


@pytest.mark.parametrize("subject_args,initial,expected", [
    ([], False, False),
    (["--subject-phrase-match"], False, True),
    (["--no-subject-phrase-match"], True, False),
    (["--subject-phrase-match", "--no-subject-phrase-match"], True, False),
    (["--no-subject-phrase-match", "--subject-phrase-match"], False, True),
])
def test_real_batch_to_real_child_parser_applies_exact_subject_choice(tmp_path, monkeypatch, subject_args, initial, expected):
    capture, commands, seen = run_batch(tmp_path, monkeypatch, subject_args=subject_args, initial_subject=initial)
    assert seen == [{"subject_phrase_match": expected, "shared_query_budget": True}] * 2
    assert capture.config["subject_phrase_match"] is expected
    assert capture.config["shared_query_budget"] is True
    assert len(capture.observations) == len(commands) == 2
    assert capture.config["batch_remaining_case_ids"] == []
    assert all(("--subject-phrase-match" in command) is expected for command in commands)
    assert all(("--no-subject-phrase-match" in command) is not expected for command in commands)


@pytest.mark.parametrize("subject", [False, True])
@pytest.mark.parametrize("source_shared,explicit_shared,expected", [
    (True, False, True), (False, False, False), (False, True, True),
])
def test_parent_config_matches_real_child_effective_shared_not_just_cli(tmp_path, monkeypatch, subject, source_shared, explicit_shared, expected):
    option = "--subject-phrase-match" if subject else "--no-subject-phrase-match"
    capture, _, seen = run_batch(tmp_path, monkeypatch, subject_args=[option],
                                shared_default=source_shared, shared_explicit=explicit_shared)
    assert capture.config["shared_query_budget"] is expected
    assert seen == [{"subject_phrase_match": subject, "shared_query_budget": expected}] * 2


@pytest.mark.parametrize("subject", [False, True])
def test_pre_start_refusal_records_requested_subject_and_effective_shared_without_dispatch(tmp_path, monkeypatch, subject):
    option = "--subject-phrase-match" if subject else "--no-subject-phrase-match"
    capture, commands, seen = run_batch(tmp_path, monkeypatch, subject_args=[option],
                                       initial_subject=not subject, stop_before=True)
    assert commands == seen == []
    assert capture.config["subject_phrase_match"] is subject
    assert capture.config["shared_query_budget"] is True
    assert capture.config["batch_attempted_case_ids"] == []
    assert capture.config["batch_remaining_case_ids"] == CASE_IDS


@pytest.mark.parametrize("subject", [False, True])
def test_refusal_between_cases_keeps_mode_and_first_observation(tmp_path, monkeypatch, subject):
    option = "--subject-phrase-match" if subject else "--no-subject-phrase-match"
    capture, commands, seen = run_batch(tmp_path, monkeypatch, subject_args=[option], stop_after_first=True)
    assert len(commands) == len(seen) == len(capture.observations) == 1
    assert capture.observations[0].case_id == CASE_IDS[0]
    assert capture.config["subject_phrase_match"] is subject
    assert capture.config["shared_query_budget"] is True
    assert capture.config["batch_attempted_case_ids"] == CASE_IDS[:1]
    assert capture.config["batch_remaining_case_ids"] == CASE_IDS[1:]


def test_actual_source_default_remains_false():
    assert live_discovery.SUBJECT_PHRASE_MATCH is False
