"""Run actual expert workflow shell steps with offline substitute executables."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from evaluation.research.live import COHORT

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/benchmark-capture.yml"


def shell_step(name: str) -> str:
    text = WORKFLOW.read_text()
    section = text.split(f"      - name: {name}\n", 1)[1].split("      - ", 1)[0]
    script = section.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] for line in script.splitlines()) + "\n"


def measurement_bindings() -> str:
    """The expert job's MEASUREMENT_BINDINGS env value (a folded ``>-`` scalar)."""
    text = WORKFLOW.read_text()
    block = text.split("      MEASUREMENT_BINDINGS: >-\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if not line.startswith("        "):
            break
        lines.append(line.strip())
    return " ".join(lines)


EXTRA_BINDINGS = [
    "evaluation/research/data/identity_bindings.draft2.json",
    "evaluation/research/data/identity_bindings.dev2-draft1.json",
    "evaluation/research/data/identity_bindings.dev3-draft1.json",
    "evaluation/research/data/identity_bindings.dev4-draft3.json",
    "evaluation/research/data/identity_bindings.dev5-draft1.json",
]


#: What the workflow's ``env:`` blocks hand a step when dispatched with defaults.
STEP_INPUTS = {"SECONDS_PER_CASE": "120", "MAX_PAGES": "60", "CASE_PARALLELISM": ""}


def extra_bindings(call: list[str]) -> list[str]:
    return [call[i + 1] for i, value in enumerate(call) if value == "--extra-bindings"]


def substitute_python(tmp_path: Path) -> Path:
    executable = tmp_path / ".venv/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\nfrom pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "with Path('calls.jsonl').open('a') as f: f.write(json.dumps(args)+'\\n')\n"
        f"if args[0] == '-c': print({' '.join(COHORT)!r})\n"
        "elif args[1] == 'evaluation.research.live':\n"
        " p=Path('out/capture/frozen.json');p.parent.mkdir(parents=True,exist_ok=True)\n"
        " p.write_text('{}');print(p)\n"
        "elif args[1] == 'evaluation.research.expert':\n"
        " assert all(args[i+1] for i,a in enumerate(args) if a=='--case')\n"
        "elif args[1] == 'evaluation.research.expert.controller':\n"
        " assert Path('out/logs/old-001.json').read_text()=='saved original'\n"
    )
    executable.chmod(0o700)
    return executable


@pytest.mark.parametrize("case_id", ["", "groningen"])
def test_blank_cohort_and_one_case_workflow_pass_real_cli_arguments(tmp_path, case_id) -> None:
    substitute_python(tmp_path)
    script = shell_step("Baseline capture and blinded packet")
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            **STEP_INPUTS,
            "EXTRA_ARGS": "--strict-expert-budget",
            "REQUESTED_CASE": case_id,
            "UNIMATCH_SEARCH_PROVIDER": "exa_mcp",
            "MEASUREMENT_BINDINGS": measurement_bindings(),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    live, packet = [call for call in calls if call[0] == "-m"]
    live_cases = [live[i + 1] for i, value in enumerate(live) if value == "--case"]
    packet_cases = [packet[i + 1] for i, value in enumerate(packet) if value == "--case"]
    assert live_cases == ([case_id] if case_id else [])
    assert packet_cases == ([case_id] if case_id else list(COHORT))
    assert live[live.index("--search-provider") + 1] == "exa_mcp"
    assert "--strict-expert-budget" in live
    assert extra_bindings(live) == EXTRA_BINDINGS


@pytest.mark.parametrize("cases", ["ethz tcd", "aitu tud"])
def test_both_paired_arms_map_with_the_same_extra_bindings(tmp_path, cases) -> None:
    """M-1: the draft bindings are part of the shared base, never of the rule under test.

    A dev5 pair gets the dev5 bindings like every other set (they are one shared list).
    """
    substitute_python(tmp_path)
    script = shell_step("Paired rule experiment (same runner, ABBA order)")
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            **STEP_INPUTS,
            "BASE_ARGS": "--shared-query-budget",
            "EXTRA_ARGS": "--route-leads",
            "REQUESTED_CASE": cases,
            "UNIMATCH_SEARCH_PROVIDER": "serper",
            "MEASUREMENT_BINDINGS": measurement_bindings(),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == 8
    assert {call[call.index("--case") + 1] for call in calls} == set(cases.split())
    for call in calls:
        arm = call[call.index("--out") + 1].rsplit("-", 1)[1]
        assert extra_bindings(call) == EXTRA_BINDINGS
        assert "--shared-query-budget" in call
        assert ("--route-leads" in call) == (arm == "on")
    assert all((Path(__file__).parents[1] / path).is_file() for path in EXTRA_BINDINGS)


@pytest.mark.parametrize(
    ("run_id", "plan", "valid"),
    [
        ("123", {"strict_budget": True, "resume_summary": {"raw_logs": {"log": "hash"}}}, True),
        ("-1", {"strict_budget": True, "resume_summary": {"raw_logs": {"log": "hash"}}}, False),
        ("123;echo bad", {"strict_budget": True}, False),
        ("123", {"strict_budget": True, "resume_summary": {}}, False),
        ("123", {"strict_budget": False, "resume_summary": {"raw_logs": {"log": "hash"}}}, False),
    ],
)
def test_workflow_resume_request_fails_before_artifact_download(
    tmp_path, run_id, plan, valid
) -> None:
    executable = tmp_path / ".venv/bin/python"
    executable.parent.mkdir(parents=True)
    executable.symlink_to(sys.executable)
    result = subprocess.run(
        ["bash", "-c", shell_step("Validate the resume request")],
        cwd=tmp_path,
        env={**os.environ, "RESUME_RUN_ID": run_id, "PLAN_JSON": json.dumps(plan)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is valid, result.stderr


def test_workflow_restores_raw_logs_before_controller_execution(tmp_path) -> None:
    substitute_python(tmp_path)
    preceding = tmp_path / "out/preceding/logs"
    preceding.mkdir(parents=True)
    (preceding / "old-001.json").write_text("saved original")
    result = subprocess.run(
        ["bash", "-c", shell_step("Execute an expert plan")],
        cwd=tmp_path,
        env={**os.environ, "PLAN_JSON": "{}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "out/preceding").exists()
    assert (tmp_path / "out/logs/old-001.json").read_text() == "saved original"


# ------------------------------------------------- SR-05: inputs never reach shell text

INPUT_EXPRESSION = re.compile(r"\$\{\{[^}]*\b(?:github\.event\.)?inputs\.")


def test_no_workflow_expands_an_input_inside_a_run_script() -> None:
    """A dispatcher's input is data: env:, with: and if: may name it, run: may not."""
    workflows = sorted(WORKFLOW.parent.glob("*.y*ml"))
    assert WORKFLOW in workflows
    offenders = []
    for path in workflows:
        document = yaml.safe_load(path.read_text())
        for job_name, job in (document.get("jobs") or {}).items():
            for index, step in enumerate(job.get("steps") or []):
                if INPUT_EXPRESSION.search(step.get("run") or ""):
                    offenders.append(f"{path.name}:{job_name}:{step.get('name', index)}")
    assert offenders == []
    # The check sees what it is meant to: the inputs still arrive, through env.
    assert INPUT_EXPRESSION.search(WORKFLOW.read_text())


@pytest.mark.parametrize(
    ("search_first", "case_id", "expected"),
    [
        ("true", "groningen", ["--search-first", "--case", "groningen"]),
        ("True", "", ["--search-first"]),
        ("false", "", []),
    ],
)
def test_capture_step_builds_the_same_flags_as_before(
    tmp_path: Path, search_first: str, case_id: str, expected: list[str]
) -> None:
    substitute_python(tmp_path)
    script = shell_step("Capture").replace("${{ github.run_id }}", "1")
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            **STEP_INPUTS,
            "SEARCH_FIRST": search_first,
            "REQUESTED_CASE": case_id,
            "UNIMATCH_SEARCH_PROVIDER": "serper",
            "GITHUB_ENV": str(tmp_path / "github_env"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    (live,) = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    after_budget = live[live.index("--max-pages") + 2 : live.index("--search-provider")]
    assert after_budget == expected
    assert live[live.index("--seconds-per-case") + 1] == "120"


@pytest.mark.parametrize(
    "step",
    [
        "Capture",
        "Baseline capture and blinded packet",
        "Paired rule experiment (same runner, ABBA order)",
    ],
)
def test_a_hostile_case_is_refused_before_anything_runs(tmp_path: Path, step: str) -> None:
    substitute_python(tmp_path)
    script = shell_step(step).replace("${{ github.run_id }}", "1")
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={**os.environ, **STEP_INPUTS, "REQUESTED_CASE": 'x"; touch pwned; "'},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "case must match" in result.stdout
    assert not (tmp_path / "calls.jsonl").exists() and not (tmp_path / "pwned").exists()


def test_extra_args_are_split_into_words_and_never_evaluated(tmp_path: Path) -> None:
    substitute_python(tmp_path)
    result = subprocess.run(
        ["bash", "-c", shell_step("Paired rule experiment (same runner, ABBA order)")],
        cwd=tmp_path,
        env={
            **os.environ,
            **STEP_INPUTS,
            "REQUESTED_CASE": "ethz",
            "BASE_ARGS": "--a  --b",
            "EXTRA_ARGS": "--rule $(touch pwned) `touch pwned2`",
            "UNIMATCH_SEARCH_PROVIDER": "serper",
            "MEASUREMENT_BINDINGS": "",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "pwned").exists() and not (tmp_path / "pwned2").exists()
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    on = [call for call in calls if call[call.index("--out") + 1].endswith("-on")]
    off = [call for call in calls if call[call.index("--out") + 1].endswith("-off")]
    assert on and off
    words = ["--a", "--b", "--rule", "$(touch", "pwned)", "`touch", "pwned2`"]
    for call in on:
        assert call[call.index("--a") : call.index("--search-provider")] == words
    for call in off:
        assert call[call.index("--a") : call.index("--search-provider")] == ["--a", "--b"]
