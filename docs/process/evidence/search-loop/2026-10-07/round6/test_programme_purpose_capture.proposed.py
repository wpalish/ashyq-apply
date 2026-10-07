"""Capture choices stay reproducible across child and pre-start refusal paths."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.adapters import page_classifier
from app.adapters.search import intent
from app.config import get_settings
from evaluation.research import live
from evaluation.research.schema import Capture, Observation


@pytest.fixture(autouse=True)
def configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setattr(page_classifier, "PROGRAMME_IDENTITY_BEFORE_FUNDING", False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "default_shared,explicit_shared", [(False, False), (True, False), (False, True)]
)
@pytest.mark.parametrize("pre_stopped", [False, True])
def test_capture_records_effective_rules_and_forwards_explicit_programme_choice(
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
        "--programme-identity-before-funding" if enabled else "--no-programme-identity-before-funding",
    ]
    if explicit_shared:
        args.append("--shared-query-budget")
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "b" * 40)
    dispatched: list[bool] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert not pre_stopped
        assert ("--programme-identity-before-funding" in command) is enabled
        assert ("--no-programme-identity-before-funding" in command) is not enabled
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
    assert capture.config["programme_identity_before_funding"] is enabled
    assert capture.config["shared_query_budget"] is (default_shared or explicit_shared)
    assert dispatched == ([] if pre_stopped else [enabled])


@pytest.mark.parametrize("enabled", [False, True])
def test_child_applies_programme_choice_before_the_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
) -> None:
    monkeypatch.setattr(page_classifier, "PROGRAMME_IDENTITY_BEFORE_FUNDING", not enabled)
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
            "--programme-identity-before-funding" if enabled else "--no-programme-identity-before-funding",
        ],
    )
    seen: list[bool] = []

    async def capture(*args: Any, **kwargs: Any) -> None:
        seen.append(page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING)

    monkeypatch.setattr(live, "capture_one", capture)
    live.main()
    assert seen == [enabled]
