"""No workflow that starts by itself can reach a self-hosted runner (security review 2026-10-22, SR2-03).

RP-1 plans a self-hosted runner on the owner's computer for ``mode=read_pages``.
A job that a push, a pull request or a schedule starts runs whatever the
pushed ref says, so if such a job could pick a self-hosted label, every branch
an agent pushes would run on that computer without anyone dispatching it. Only
``workflow_dispatch`` jobs may take a free ``runner`` input; every other job
names a GitHub-hosted image, or a ``runner`` choice whose options all are.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

WORKFLOWS = sorted((Path(__file__).resolve().parents[2] / ".github/workflows").glob("*.y*ml"))
HOSTED = re.compile(r"^(ubuntu|windows|macos)-[A-Za-z0-9.-]+$")
RUNNER_INPUT = re.compile(r"^\$\{\{\s*inputs\.runner\s*\|\|\s*'([^']+)'\s*\}\}$")


def _triggers(document: dict[Any, Any]) -> set[str]:
    # PyYAML reads the bare key ``on`` as the boolean True.
    on = document.get("on", document.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on or {})


def _hosted(runs_on: Any, document: dict[Any, Any]) -> bool:
    if isinstance(runs_on, str) and HOSTED.match(runs_on):
        return True
    found = RUNNER_INPUT.match(runs_on) if isinstance(runs_on, str) else None
    if found is None or not HOSTED.match(found.group(1)):
        return False
    on = document.get("on", document.get(True)) or {}
    runner = ((on.get("workflow_dispatch") or {}).get("inputs") or {}).get("runner") or {}
    options = runner.get("options") or []
    return (
        runner.get("type") == "choice" and bool(options) and all(HOSTED.match(o) for o in options)
    )


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_a_job_that_starts_by_itself_runs_on_a_github_hosted_image(path: Path) -> None:
    document = yaml.safe_load(path.read_text())
    automatic = _triggers(document) - {"workflow_dispatch"}
    if not automatic:
        return
    for name, job in (document.get("jobs") or {}).items():
        assert _hosted(job.get("runs-on"), document), (
            f"{path.name}: job {name} starts on {sorted(automatic)} and could run on "
            f"{job.get('runs-on')!r}"
        )


def test_the_check_sees_the_workflows() -> None:
    names = {p.name for p in WORKFLOWS}
    assert {"ci.yml", "kb-refresh.yml", "benchmark-capture.yml"} <= names
    # kb-refresh is scheduled and takes a runner input: a choice of hosted images only.
    kb_refresh = yaml.safe_load((WORKFLOWS[0].parent / "kb-refresh.yml").read_text())
    assert _hosted(kb_refresh["jobs"]["refresh"]["runs-on"], kb_refresh)
    # A free-text runner input is refused for an automatic job.
    free = {"on": {"workflow_dispatch": {"inputs": {"runner": {"default": "ubuntu-latest"}}}}}
    assert not _hosted("${{ inputs.runner || 'ubuntu-latest' }}", free)
    assert not _hosted("self-hosted", free)
    assert not _hosted(["self-hosted", "linux"], free)
