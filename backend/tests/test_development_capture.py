"""Opt-in catalogue capture and fail-closed batch checks; no live network."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.search.base import SearchFailureReason, SearchUnavailable
from app.catalogue.importer import import_catalogue
from app.config import get_settings
from app.models import Base
from evaluation.research import live, scorecard
from evaluation.research.schema import Capture, Observation
from scripts import canary_discovery as canary

DALIAN = "01d3bb22815c61aa8454283116cbd4fa"
NAGOYA = "01ea8dd78746c15f2655b59fd4f5deab"


@pytest.fixture(autouse=True)
def configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def catalogue() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        import_catalogue(session)
        yield session
    engine.dispose()


def test_explicit_seed_selection_preserves_order_and_exports_no_seed_facts(catalogue: Session):
    selected = canary.select_catalogue_entries(catalogue, [NAGOYA, DALIAN])
    assert [entry["id"] for entry in selected] == [NAGOYA, DALIAN]
    assert [entry["homepage"] for entry in selected] == [
        "https://nagoya-u.ac.jp/",
        "https://dlut.edu.cn/",
    ]
    assert all(
        set(entry) == {"id", "name", "country", "homepage", "identity_status"} for entry in selected
    )
    assert all(entry["identity_status"] == "seed" for entry in selected)


@pytest.mark.parametrize("ids", [[], [DALIAN, DALIAN], ["not-an-id"], ["f" * 32]])
def test_invalid_explicit_selection_never_falls_back_to_registry(
    catalogue: Session, ids: list[str]
):
    with pytest.raises(ValueError):
        canary.select_catalogue_entries(catalogue, ids)


@pytest.mark.asyncio
async def test_seed_canary_uses_imported_identity_without_generating_claims(
    monkeypatch: pytest.MonkeyPatch,
):
    seen = []

    async def run(runner: Any) -> None:
        seen.extend(runner.run.university_ids)

    # The actual runner constructor and throwaway importer still execute.
    monkeypatch.setattr(canary.CanaryRunner, "run_to_decision", run)
    report = await canary.run_canary(None, False, catalogue_ids=[DALIAN])
    assert report["batch"] == ["Dalian University of Technology"]
    assert report["institutions"][0]["catalogue_id"] == DALIAN
    assert report["totals"]["claims"] == 0
    assert report["totals"]["program_pages_found"] == 0
    assert seen == [DALIAN]


@pytest.mark.parametrize("status", [401, 402, 429, 500, None])
def test_any_provider_failure_blocks_search_and_fetch_and_retains_first_cause(
    tmp_path: Path, status: int | None
):
    stop = tmp_path / "STOP.json"
    budget = live._ExpertBudget(60, 120, "exa", 0, clock=lambda: 1, stop_file=stop, case_id=DALIAN)
    reason = SearchFailureReason.TIMEOUT if status is None else None
    budget.failed_search(SearchUnavailable("vendor-secret", http_status=status, reason=reason))
    first = budget.provider_failure.copy() if budget.provider_failure else None
    budget.failed_search(SearchUnavailable("second-secret", http_status=503))
    assert budget.provider_failure == first
    for action in (budget.before_fetch, lambda: budget.before_search("exa")):
        with pytest.raises(SearchUnavailable):
            action()
    assert budget.fetcher_calls == budget.search_queries == 0
    assert "secret" not in stop.read_text() + json.dumps(budget.snapshot())
    assert json.loads(stop.read_text())["http_status"] == status
    assert budget.stop_reason == ("http_429" if status == 429 else "provider_failure")


def test_shared_stop_blocks_another_ledger_without_reset_or_network(tmp_path: Path):
    stop = tmp_path / "STOP.json"
    stop.write_text('{"failure_reason":"timeout"}')
    budget = live._ExpertBudget(60, 120, "exa", 0, clock=lambda: 1, stop_file=stop)
    with pytest.raises(SearchUnavailable):
        budget.before_fetch()
    with pytest.raises(SearchUnavailable):
        budget.before_search("exa")
    assert budget.stop_reason == "external_provider_failure"
    assert json.loads(stop.read_text()) == {"failure_reason": "timeout"}


@pytest.mark.asyncio
async def test_shared_stop_prevents_a_later_http_hop_in_an_inflight_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from app.adapters import fetching

    stop = tmp_path / "STOP.json"
    transports = []
    monkeypatch.setattr(fetching, "_pinned_request", lambda *a, **k: transports.append("sent"))

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        transport: Any = fetching._pinned_request
        transport("first-mocked-hop")
        stop.write_text('{"failure_reason":"quota"}')
        with pytest.raises(SearchUnavailable):
            transport("second-mocked-hop")
        return {"institutions": [], "run_error": None}

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "capture.json"
    await live.capture_one("groningen", output, 60, 120, strict_expert_budget=True, stop_file=stop)
    assert transports == ["sent"]
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    assert budget["network_http_requests"] == 1
    assert budget["stop_reason"] == "external_provider_failure"
    assert Observation.model_validate_json(output.read_text()).error == "BENCHMARK_PROVIDER_FAILURE"


def test_explicit_catalogue_batch_preserves_requested_ids_and_stops_on_402(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from evaluation.research.expert import catalogue as catalogue_module

    imported = catalogue_module.load_catalogue(source_sha="a" * 40)
    monkeypatch.setattr(catalogue_module, "load_catalogue", lambda: imported)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--catalogue-id",
            DALIAN,
            "--catalogue-id",
            NAGOYA,
            "--out",
            str(tmp_path),
            "--strict-expert-budget",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "a" * 40)
    started = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "--case" not in command
        case = command[command.index("--catalogue-id") + 1]
        started.append(case)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id=case).model_dump_json())
        output.with_suffix(".budget.json").write_text(
            json.dumps(
                {"stop_reason": "provider_failure", "provider_failure": {"http_status": 402}}
            )
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert started == [DALIAN]
    assert capture.config["cohort"] == [DALIAN, NAGOYA]
    assert capture.config["batch_attempted_case_ids"] == [DALIAN]
    assert capture.config["batch_remaining_case_ids"] == [NAGOYA]
    assert capture.config["batch_stop_reason"] == "provider_failure"


def test_preexisting_shared_stop_dispatches_no_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    stop = tmp_path / "STOP.json"
    stop.write_text("{}")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--out",
            str(tmp_path / "run"),
            "--strict-expert-budget",
            "--stop-file",
            str(stop),
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("no child may start"))
    live.main()
    capture = Capture.model_validate_json(
        next((tmp_path / "run").rglob("capture.json")).read_text()
    )
    assert capture.observations == []
    assert capture.config["batch_attempted_case_ids"] == []
    assert capture.config["batch_remaining_case_ids"] == list(live.COHORT)
    assert capture.config["batch_stop_reason"] == "external_provider_failure"
    arm = scorecard.load_run(next((tmp_path / "run").rglob("capture.json")))["run"]
    completeness = scorecard.completeness(arm, arm.expected_cases)
    assert completeness["status"] == "incomplete"
    assert len(completeness["missing"]) == len(live.COHORT)
