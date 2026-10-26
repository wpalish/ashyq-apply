"""SM-1: ``benchmark-capture.yml`` mode ``preflight`` is a 1-query smoke of a named provider.

The key track's first step (NEXT_CYCLES_2026-10-26 §4.2 B1) should cost one query, print
the provider's answer and let the dashboard's per-query cost be read before a record run
spends 264. Offline only: the steps run with substitute executables, no provider is called
and no key is real. The job's first real run is the smoke itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/benchmark-capture.yml"
SECRET = "synthetic-key-never-printed"
CAP_STEP = "Search query cap (refuse a provider run without one)"


def jobs() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]  # type: ignore[no-any-return]


def preflight_job() -> dict[str, Any]:
    return jobs()["preflight"]  # type: ignore[no-any-return]


def step(job: dict[str, Any], name: str) -> dict[str, Any]:
    return next(s for s in job["steps"] if s.get("name") == name)


def run_step(
    name: str, tmp_path: Path, env: dict[str, str]
) -> tuple[subprocess.CompletedProcess[str], str]:
    github_env = tmp_path / "github.env"
    github_env.write_text("")
    result = subprocess.run(
        ["bash", "-c", step(preflight_job(), name)["run"]],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "GITHUB_ENV": str(github_env), **env},
        capture_output=True,
        text=True,
        check=False,
    )
    return result, github_env.read_text()


def test_the_job_exists_and_runs_only_for_mode_preflight() -> None:
    job = preflight_job()
    assert job["if"] == "inputs.mode == 'preflight'"
    assert job["runs-on"] == "${{ inputs.runner || 'ubuntu-latest' }}"
    assert job["timeout-minutes"] == 10
    others = [j["if"] for name, j in jobs().items() if name != "preflight"]
    assert not any("preflight" in condition for condition in others)
    mode = yaml.safe_load(WORKFLOW.read_text())[True]["workflow_dispatch"]["inputs"]["mode"]
    assert "preflight (SM-1" in mode["description"]


def test_it_sends_one_query_through_search_preflight_with_both_cap_flags() -> None:
    script = step(preflight_job(), "One query through the product client")["run"]
    assert ".venv/bin/python -m evaluation.research.search_preflight" in script
    assert '--max-search-queries "$CAP"' in script
    assert "--search-ledger out/search_ledger.json" in script


def test_no_step_captures_anything() -> None:
    for s in preflight_job()["steps"]:
        text = str(s.get("run", ""))
        assert "-m evaluation.research.live" not in text
        assert "-m evaluation.research.expert" not in text


@pytest.mark.parametrize("name", ["Select the search layer", CAP_STEP])
def test_the_search_steps_are_the_expert_jobs_verbatim(name: str) -> None:
    mine, theirs = step(preflight_job(), name), step(jobs()["expert"], name)
    assert mine["run"] == theirs["run"]
    assert mine.get("env") == theirs.get("env")


@pytest.mark.parametrize(
    ("provider", "refused"),
    [
        ("auto", True),
        ("none", True),
        ("recorded", True),
        ("exa", False),
        ("exa_mcp", False),
        ("tavily", False),
        ("brave", False),
    ],
)
def test_only_an_explicitly_named_provider_is_accepted(
    tmp_path: Path, provider: str, refused: bool
) -> None:
    result, _ = run_step(
        "Refuse a search layer that is not named",
        tmp_path,
        {"REQUESTED_SEARCH_PROVIDER": provider},
    )
    assert (result.returncode != 0) is refused, result.stdout + result.stderr
    if refused:
        assert "explicit search_provider" in result.stdout


def test_the_refusal_names_the_three_arms() -> None:
    script = step(preflight_job(), "Refuse a search layer that is not named")["run"]
    assert "auto|none|recorded)" in script


@pytest.mark.parametrize("provider", ["none", "recorded"])
def test_the_cap_step_refuses_a_layer_that_sends_nothing(tmp_path: Path, provider: str) -> None:
    (tmp_path / "out").mkdir()
    result, github_env = run_step(
        CAP_STEP,
        tmp_path,
        {
            "UNIMATCH_SEARCH_PROVIDER": provider,
            "REQUESTED_CAP": "1",
            "REQUESTED_MODE": "preflight",
            "REQUESTED_CASE": "groningen",
            "REQUESTED_COLUMNS": "4",
        },
    )
    assert result.returncode == 1
    assert "preflight needs a provider" in result.stdout
    assert github_env == ""


@pytest.mark.parametrize(("cap", "ok"), [("1", True), ("264", True), ("", False), ("0", False)])
def test_the_cap_step_plans_exactly_one_query(tmp_path: Path, cap: str, ok: bool) -> None:
    result, github_env = run_step(
        CAP_STEP,
        tmp_path,
        {
            "UNIMATCH_SEARCH_PROVIDER": "exa",
            "UNIMATCH_EXA_API_KEY": SECRET,
            "REQUESTED_CAP": cap,
            "REQUESTED_MODE": "preflight",
            "REQUESTED_CASE": "groningen delft",
            "REQUESTED_COLUMNS": "4",
        },
    )
    assert (result.returncode == 0) is ok, result.stdout + result.stderr
    assert SECRET not in result.stdout + result.stderr
    if ok:
        assert f"search query cap: {cap} for exa (planned 1)" in result.stdout
        assert (
            f"max_search_queries={cap} planned=1 provider=exa"
            in (tmp_path / "out/config.txt").read_text()
        )
        assert "--search-ledger" in github_env
    else:
        assert "needs the max_search_queries input" in result.stdout


def _substitute_preflight(tmp_path: Path, *, fail: bool) -> None:
    executable = tmp_path / ".venv/bin/python"
    executable.parent.mkdir(parents=True)
    body = (
        "import json, sys\nfrom pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "assert args[:2] == ['-m', 'evaluation.research.search_preflight'], args\n"
        "ledger = Path(args[args.index('--search-ledger') + 1])\n"
        "cap = int(args[args.index('--max-search-queries') + 1])\n"
        "ledger.write_text(json.dumps({'cap': cap, 'used': 1}))\n"
    )
    if fail:
        body += (
            "print('search pre-flight FAILED: exa answered http 402 (reason credit, body \"***\").',"
            " file=sys.stderr)\nsys.exit(1)\n"
        )
    else:
        body += "print('search pre-flight ok: exa answered with 1 result(s)')\n"
    executable.write_text(f"#!{sys.executable}\n{body}")
    executable.chmod(0o700)


@pytest.mark.parametrize("fail", [False, True])
def test_the_query_step_prints_the_answer_and_records_the_ledger(
    tmp_path: Path, fail: bool
) -> None:
    _substitute_preflight(tmp_path, fail=fail)
    (tmp_path / "out").mkdir()
    (tmp_path / "out/config.txt").write_text("provider=exa\ndecided_by=explicit input\n")
    result, _ = run_step("One query through the product client", tmp_path, {"CAP": "1"})
    config = (tmp_path / "out/config.txt").read_text()
    assert "provider=exa" in config
    assert json.loads(
        config.split("search_ledger=out/search_ledger.json ", 1)[1].splitlines()[0]
    ) == {
        "cap": 1,
        "used": 1,
    }
    if fail:
        assert result.returncode == 1
        assert "::error::search pre-flight FAILED: exa answered http 402" in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert "search pre-flight ok: exa answered with 1 result(s)" in result.stdout


def test_the_artifact_carries_config_ledger_and_both_streams() -> None:
    upload = next(s for s in preflight_job()["steps"] if "upload-artifact" in str(s.get("uses")))
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "preflight-${{ github.run_id }}"
    paths = upload["with"]["path"].split()
    for name in ("config.txt", "search_ledger.json", "preflight.out", "preflight.err"):
        assert f"backend/out/{name}" in paths


def test_every_run_block_of_the_job_is_valid_bash() -> None:
    for s in preflight_job()["steps"]:
        if "run" in s:
            subprocess.run(["bash", "-n", "-c", s["run"]], check=True)
