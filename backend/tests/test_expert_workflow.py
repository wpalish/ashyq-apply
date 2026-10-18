"""Run actual expert workflow shell steps with offline substitute executables."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

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
]


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
    script = (
        script.replace("${{ inputs.seconds_per_case }}", "120")
        .replace("${{ inputs.max_pages }}", "60")
        .replace("${{ inputs.extra_args }}", "--strict-expert-budget")
    )
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
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


def test_both_paired_arms_map_with_the_same_extra_bindings(tmp_path) -> None:
    """M-1: the draft bindings are part of the shared base, never of the rule under test."""
    substitute_python(tmp_path)
    script = (
        shell_step("Paired rule experiment (same runner, ABBA order)")
        .replace("${{ inputs.seconds_per_case }}", "120")
        .replace("${{ inputs.max_pages }}", "60")
        .replace("${{ inputs.base_args }}", "--shared-query-budget")
        .replace("${{ inputs.extra_args }}", "--route-leads")
        .replace("${{ inputs.case }}", "ethz tcd")
    )
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
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
