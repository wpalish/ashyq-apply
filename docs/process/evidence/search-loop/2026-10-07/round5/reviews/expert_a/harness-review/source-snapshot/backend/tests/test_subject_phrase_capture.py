"""Capture choices stay reproducible across child and pre-start refusal paths."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.search import intent
from app.config import get_settings
from evaluation.research import live
from evaluation.research.schema import Capture, Observation


@pytest.fixture(autouse=True)
def configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setattr(live_discovery, "SUBJECT_PHRASE_MATCH", False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "default_shared,explicit_shared", [(False, False), (True, False), (False, True)]
)
@pytest.mark.parametrize("pre_stopped", [False, True])
def test_capture_records_effective_rules_and_forwards_explicit_subject_choice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    default_shared: bool,
    explicit_shared: bool,
    pre_stopped: bool,
) -> None:
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", default_shared)
    stop = tmp_path / "STOP.json"
    if pre_stopped:
        stop.write_text("{}")
    args = [
        "live",
        "--live",
        "--case",
        "groningen",
        "--out",
        str(tmp_path / "run"),
        "--strict-expert-budget",
        "--stop-file",
        str(stop),
        "--subject-phrase-match" if enabled else "--no-subject-phrase-match",
    ]
    if explicit_shared:
        args.append("--shared-query-budget")
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "b" * 40)
    dispatched: list[bool] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert not pre_stopped
        assert ("--subject-phrase-match" in command) is enabled
        assert ("--no-subject-phrase-match" in command) is not enabled
        assert ("--shared-query-budget" in command) is explicit_shared
        dispatched.append(enabled)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json())
        output.with_suffix(".budget.json").write_text(json.dumps({"stop_reason": "completed"}))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(
        next((tmp_path / "run").rglob("capture.json")).read_text()
    )
    assert capture.config["subject_phrase_match"] is enabled
    assert capture.config["shared_query_budget"] is (default_shared or explicit_shared)
    assert dispatched == ([] if pre_stopped else [enabled])


@pytest.mark.parametrize("enabled", [False, True])
def test_child_applies_subject_choice_before_the_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
) -> None:
    monkeypatch.setattr(live_discovery, "SUBJECT_PHRASE_MATCH", not enabled)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(tmp_path / "one.json"),
            "--strict-expert-budget",
            "--subject-phrase-match" if enabled else "--no-subject-phrase-match",
        ],
    )
    seen: list[bool] = []

    async def capture(*args: Any, **kwargs: Any) -> None:
        seen.append(live_discovery.SUBJECT_PHRASE_MATCH)

    monkeypatch.setattr(live, "capture_one", capture)
    live.main()
    assert seen == [enabled]
