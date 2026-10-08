"""CLI/child/preSTOP provenance controls; no process/provider execution."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import config
from app.pipeline import read_budget
from evaluation.research import live
from evaluation.research.schema import Observation, Telemetry
from scripts import canary_discovery as canary
from tests.readguard_support import offline as offline


@pytest.fixture
def cli(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        config,
        "Settings",
        lambda **kwargs: SimpleNamespace(search_provider="exa", _validate_search=lambda: None),
    )
    monkeypatch.setattr(
        live.subprocess, "check_output", lambda *args, **kwargs: b"frozen-source".decode()
    )

    def run(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen", telemetry=Telemetry()).model_dump_json())
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(live.subprocess, "run", run)
    return SimpleNamespace(root=tmp_path, calls=calls)


@pytest.mark.parametrize(
    "flags,source,native,fenced",
    [
        ([], False, False, False),
        (["--no-university-read-budget"], True, False, False),
        (["--fenced-research-job", "--university-read-budget"], False, True, True),
        (
            ["--university-read-budget", "--no-university-read-budget", "--fenced-research-job"],
            True,
            False,
            True,
        ),
        (["--no-fenced-research-job", "--fenced-research-job"], False, False, True),
        (["--fenced-research-job", "--no-fenced-research-job"], False, False, False),
    ],
)
def test_batch_resolved_flags_forwarded_and_recorded(
    cli, monkeypatch, flags, source, native, fenced
):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", source)
    monkeypatch.setattr(
        sys,
        "argv",
        ["live", "--live", "--case", "groningen", "--out", str(cli.root / "out"), *flags],
    )
    live.main()
    command = cli.calls[0]
    assert ("--university-read-budget" if native else "--no-university-read-budget") in command
    assert ("--fenced-research-job" if fenced else "--no-fenced-research-job") in command
    capture = json.loads(next((cli.root / "out").rglob("capture.json")).read_text())
    assert (
        capture["config"]["university_read_budget"] is native
        and capture["config"]["fenced_research_job"] is fenced
    )
    assert capture["config"]["research_job_protocol"] == (
        "genuine-research-job" if fenced else "legacy-direct-unfenced"
    )


@pytest.mark.parametrize(
    "flags",
    [
        ["--university-read-budget"],
        ["--fenced-research-job", "--with-documents", "1"],
        ["--fenced-research-job"],
    ],
)
def test_invalid_before_child_or_settings(cli, monkeypatch, flags):
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--out", str(cli.root / "out"), *flags])
    with pytest.raises(SystemExit) as info:
        live.main()
    assert info.value.code == 2 and cli.calls == [] and not (cli.root / "out").exists()


@pytest.mark.parametrize("native", [False, True])
def test_pre_stop_envelope_effective_flags_without_job(cli, monkeypatch, native):
    stop = cli.root / "stop.json"
    stop.write_text('{"reason":"synthetic"}')
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(cli.root / "out"),
            "--strict-expert-budget",
            "--stop-file",
            str(stop),
            "--fenced-research-job",
            "--university-read-budget" if native else "--no-university-read-budget",
        ],
    )
    live.main()
    capture = json.loads(next((cli.root / "out").rglob("capture.json")).read_text())
    assert cli.calls == [] and capture["observations"] == []
    assert (
        capture["config"]["university_read_budget"] is native
        and capture["config"]["fenced_research_job"] is True
    )
    assert capture["config"]["batch_attempted_case_ids"] == []


@pytest.mark.parametrize("native", [False, True])
def test_child_flags_are_passed_to_capture_without_global_promotion(cli, monkeypatch, native):
    got = []

    async def capture(*args, **kwargs):
        got.append(kwargs)

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", True)
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
            str(cli.root / "child.json"),
            "--fenced-research-job",
            "--university-read-budget" if native else "--no-university-read-budget",
        ],
    )
    live.main()
    assert got[0]["university_read_budget"] is native and got[0]["fenced_research_job"] is True
    assert read_budget.UNIVERSITY_READ_BUDGET is True and cli.calls == []


@pytest.mark.parametrize(
    "flags",
    [
        ["--check-seeds", "--fenced-research-job", "--only", "example.edu"],
        ["--university-read-budget", "--only", "example.edu"],
        ["--fenced-research-job", "--batch", "example.edu,second.edu"],
    ],
)
def test_canary_cli_rejects_excluded_protocol_before_seed_calls(monkeypatch, flags):
    called = []

    async def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError

    monkeypatch.setattr(canary, "check_seeds", forbidden)
    monkeypatch.setattr(canary, "run_canary", forbidden)
    monkeypatch.setattr(sys, "argv", ["canary", *flags])
    with pytest.raises(SystemExit):
        asyncio.run(canary.main())
    assert called == []


def test_outer_clock_is_original_entry_and_limits_unchanged():
    clock = [10.0]
    b = live._ExpertBudget(60, 120, "exa", clock[0], clock=lambda: clock[0])
    clock[0] += 17
    assert b.remaining() == 103 and b.started == 10
    assert (
        live.STRICT_MAX_FETCHER_CALLS == 60
        and live.STRICT_MAX_SEARCH_QUERIES == 6
        and live.STRICT_MAX_SECONDS == 120
    )
    assert "setup" in b.active_time_basis
