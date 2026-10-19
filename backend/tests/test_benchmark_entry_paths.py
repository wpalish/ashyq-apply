"""G-06 (generalisation ticket 06): the cohort through three entry paths.

The cohort runs the registry path (curated seeds, slots pre-filled); dev2-dev4
run the no-seed path from a homepage; production's non-registry universities
run the identity gate first. ``--no-registry-seeds`` captures a cohort case
from its registry row without the seeds, ``--through-identity-gate`` now also
sends a cohort case through ``_identify_site``, and the scorecard and stage
summary name the arm's entry path. Offline: fake canary, fake child process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.catalogue.importer import SEED_PATH, identity_key, import_catalogue, stable_id
from app.db import create_all_for_tests
from app.models import University
from evaluation.research import live, scorecard, stage_summary
from evaluation.research.schema import Capture, Dataset, Observation, SiteIdentity
from scripts import canary_discovery as canary


@pytest.fixture
def catalogue_session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        yield session
    engine.dispose()


def _uni(session: Session, entry: dict[str, str]) -> University:
    uni = session.get(University, stable_id(identity_key(entry["name"], entry["country"])))
    assert uni is not None
    return uni


# --- the entries ------------------------------------------------------------------


def test_every_cohort_case_has_a_seedless_entry_and_a_seed_row(catalogue_session) -> None:
    rows = {
        r["seed_id"]: r for r in json.loads(SEED_PATH.read_text(encoding="utf-8"))["universities"]
    }
    assert set(live.COHORT_SEEDS) == set(live.COHORT)
    for case_id, seed_id in live.COHORT_SEEDS.items():
        entry = live.cohort_entry(case_id)
        assert set(entry) == {"name", "country", "city", "homepage"}
        uni = _uni(catalogue_session, entry)
        # The registry row the importer built, the same row as the seed's.
        assert uni.registry_entry is not None and uni.registry_entry["seeds"]
        assert entry["homepage"] == uni.registry_entry["homepage"]
        row = rows[seed_id]
        assert identity_key(row["name"], row["country"]) == uni.identity_key
        # The gate arm's entry names the same row.
        gate = live.seed_entry(case_id)
        assert {k: gate[k] for k in ("name", "country", "city")} == {
            k: entry[k] for k in ("name", "country", "city")
        }


def test_the_no_seed_install_replaces_the_curated_entry(catalogue_session) -> None:
    entry = live.cohort_entry("groningen")
    canary._install_identified_sites(catalogue_session, [entry], drop_registry_entry=True)
    uni = _uni(catalogue_session, entry)
    assert uni.registry_entry == entry and "seeds" not in uni.registry_entry
    assert uni.domain == "rug.nl" and uni.domain_status == "site_identity_checked"


@pytest.mark.parametrize("case_id,domain", [("groningen", "rug.nl"), ("vienna", None)])
def test_the_gate_install_leaves_a_seed_only_row(catalogue_session, case_id, domain) -> None:
    entry = live.seed_entry(case_id)
    canary._install_identified_sites(
        catalogue_session, [entry], establish=False, drop_registry_entry=True
    )
    uni = _uni(catalogue_session, entry)
    assert uni.registry_entry is None
    # The seed record's domain (vienna's row has none), never the curated one.
    assert uni.domain == domain
    assert uni.domain_status == ("seed" if domain else "unknown")


def test_without_the_switch_a_registry_row_keeps_its_seeds(catalogue_session) -> None:
    entry = live.cohort_entry("groningen")
    canary._install_identified_sites(catalogue_session, [entry])
    assert (_uni(catalogue_session, entry).registry_entry or {})["seeds"]


# --- the child: path selection ------------------------------------------------------


@pytest.fixture
def canary_calls(monkeypatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    async def fake_canary(selector, verbose, batch=None, *, entries=None, **kwargs):
        calls.append((selector, entries, kwargs))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    return calls


@pytest.mark.asyncio
async def test_the_three_cohort_arms(tmp_path, canary_calls) -> None:
    await live.capture_one("groningen", tmp_path / "registry.json", 4)
    await live.capture_one("groningen", tmp_path / "seedless.json", 4, no_registry_seeds=True)
    await live.capture_one("groningen", tmp_path / "gate.json", 4, through_identity_gate=True)
    assert canary_calls == [
        ("rug.nl", None, {}),
        (None, [live.cohort_entry("groningen")], {"drop_registry_entry": True}),
        (
            None,
            [live.seed_entry("groningen")],
            {"through_identity_gate": True, "drop_registry_entry": True},
        ),
    ]
    read = Observation.model_validate_json
    assert read((tmp_path / "registry.json").read_text()).site_identity is None
    assert read((tmp_path / "seedless.json").read_text()).site_identity is None
    assert read((tmp_path / "gate.json").read_text()).site_identity == SiteIdentity(
        established=False
    )


@pytest.mark.asyncio
async def test_the_no_seed_switch_leaves_other_sets_alone(tmp_path, canary_calls) -> None:
    await live.capture_one("ethz", tmp_path / "ethz.json", 4, no_registry_seeds=True)
    assert canary_calls == [(None, [live.dev2_entry("ethz")], {})]


# --- the parent --------------------------------------------------------------------


def _parent(monkeypatch, tmp_path: Path, case_id: str, *flags: str) -> list[list[str]]:
    argv = ["live", "--live", "--case", case_id, "--out", str(tmp_path), *flags]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands: list[list[str]] = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id=case_id).model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    return commands


def _config(tmp_path: Path) -> dict[str, Any]:
    return Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text()).config


def test_the_parent_forwards_the_no_seed_arm(tmp_path, monkeypatch) -> None:
    commands = _parent(monkeypatch, tmp_path, "groningen", "--no-registry-seeds")
    assert "--no-registry-seeds" in commands[0]
    assert _config(tmp_path)["entry_path"] == "no_seed"


def test_the_gate_arm_records_its_entry_path(tmp_path, monkeypatch) -> None:
    _parent(monkeypatch, tmp_path, "groningen", "--through-identity-gate")
    assert _config(tmp_path)["entry_path"] == "identity_gate"


def test_the_default_arm_records_no_entry_path(tmp_path, monkeypatch) -> None:
    _parent(monkeypatch, tmp_path, "groningen")
    assert "entry_path" not in _config(tmp_path)


@pytest.mark.parametrize(
    "case_id,flags",
    [
        ("groningen", ["--no-registry-seeds", "--through-identity-gate"]),
        ("ethz", ["--no-registry-seeds"]),
    ],
)
def test_the_parent_refuses_a_meaningless_arm(tmp_path, monkeypatch, case_id, flags) -> None:
    with pytest.raises(SystemExit):
        _parent(monkeypatch, tmp_path, case_id, *flags)


def test_the_child_hands_the_arm_to_capture_one(tmp_path, monkeypatch) -> None:
    seen: dict[str, Any] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "delft", "--out", str(tmp_path / "d.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--no-registry-seeds"])
    live.main()
    assert seen == {"no_registry_seeds": True}


# --- the arm header ------------------------------------------------------------------


def _dataset() -> Dataset:
    def case(case_id: str) -> dict:
        return {
            "id": case_id,
            "dataset_version": "test",
            "university": case_id,
            "domain": f"{case_id}.edu",
            "country": "Nowhere",
            "site_types": ["static"],
            "request": {"university": case_id},
            "labels": [],
            "review": {"status": "draft", "prepared_by": "test", "notes": "test"},
        }

    return Dataset.model_validate(
        {"version": "test", "split": "development", "cases": [case("qx1"), case("qx2")]}
    )


def _write(root: Path, arm: str, config: dict[str, Any]) -> None:
    target = root / f"x-{arm}" / "20261019T000001Z"
    target.mkdir(parents=True)
    capture = {
        "pipeline_sha": "abc",
        "captured_at": "20261019T000001Z",
        "mode": "live",
        "config": config,
        "observations": [{"case_id": "qx1"}, {"case_id": "qx2"}],
    }
    (target / "capture.json").write_text(json.dumps(capture))


def test_the_scorecard_and_stage_summary_name_the_entry_path(tmp_path: Path) -> None:
    _write(tmp_path, "off", {})
    _write(tmp_path, "on", {"entry_path": "no_seed"})
    arms = scorecard.load_run(tmp_path)
    card = scorecard.build(_dataset(), arms, allow_drafts=True)
    assert "| entry path | default | no_seed |" in scorecard.render(card)
    summary = scorecard.summarize(card)
    assert "| entry path | default | no_seed |" in scorecard.render_summary(summary)
    text = stage_summary.guarded_render(_dataset(), arms)
    assert "Entry path per arm: off#1 default, on#1 no_seed" in text


def test_a_run_on_the_default_path_keeps_its_header(tmp_path: Path) -> None:
    _write(tmp_path, "off", {})
    _write(tmp_path, "on", {})
    arms = scorecard.load_run(tmp_path)
    card = scorecard.build(_dataset(), arms, allow_drafts=True)
    assert "entry path" not in scorecard.render(card)
    assert "Entry path" not in stage_summary.guarded_render(_dataset(), arms)
