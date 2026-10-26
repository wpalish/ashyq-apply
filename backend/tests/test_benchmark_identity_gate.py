"""v3-M3: the benchmark arm that goes through production's site-identity gate.

Wayfinder programme-discovery ticket 05 Q3 (owner, 2026-10-18), plan row M3.
By default ``live.dev2_entry`` hands discovery a verified homepage, so the
benchmark never exercises ``CatalogueDiscoveryAdapter._identify_site``. Under
``--through-identity-gate`` a dev2/dev3 case's seed row goes through that gate
itself, the observation records what the gate said, and the scorecard reports
"identity established n/N". Offline: fake fetchers, fake provider, no network.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchOutcome, FetchResult
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import SEED_PATH, identity_key, import_catalogue, stable_id
from app.db import create_all_for_tests
from app.models import University
from evaluation.research import live, scorecard
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


def _row(case_id: str) -> University:
    entry = live.dev2_entry(case_id)
    return University(id=stable_id(identity_key(entry["name"], entry["country"])))


def _page(url: str, title: str) -> FetchResult:
    return FetchResult(url=url, outcome=FetchOutcome.OK, content=f"<title>{title}</title>".encode())


# --- the entry: the seed row alone --------------------------------------------


def test_the_gate_arm_entry_is_the_seed_row_without_the_harness_correction() -> None:
    rows = {
        r["seed_id"]: r for r in json.loads(SEED_PATH.read_text(encoding="utf-8"))["universities"]
    }
    for case_id, seed_id in live.DEV2.items():
        entry, verified = live.seed_entry(case_id), live.dev2_entry(case_id)
        # The same catalogue row, so the canary finds its candidate and trace.
        assert {k: entry[k] for k in ("name", "country", "city")} == {
            k: verified[k] for k in ("name", "country", "city")
        }
        row = rows[seed_id]
        if row.get("official_site"):
            assert entry["homepage"] == row["official_site"]
        elif row.get("official_domain"):
            assert entry["homepage"] == f"https://{row['official_domain']}/"
        else:
            assert entry["homepage"] == verified["homepage"]
    # Khalifa's seed is the stale domain the default arm corrects; the gate sees it.
    assert live.seed_entry("khalifa")["homepage"] == "http://www.kustar.ac.ae/"
    assert live.dev2_entry("khalifa")["homepage"] == "https://www.ku.ac.ae/"


def test_the_canary_leaves_identity_to_the_gate(catalogue_session) -> None:
    entry = live.dev2_entry("ethz")
    canary._install_identified_sites(catalogue_session, [entry], establish=False)
    uni = catalogue_session.get(University, _row("ethz").id)
    assert uni.registry_entry is None
    assert uni.domain == "ethz.ch" and uni.domain_status == "seed"
    # The default arm: the state _identify_site leaves behind on success.
    canary._install_identified_sites(catalogue_session, [entry])
    assert uni.registry_entry == entry and uni.domain_status == "site_identity_checked"
    with pytest.raises(SystemExit):
        canary._install_identified_sites(
            catalogue_session, [{**entry, "name": "No Such University"}], establish=False
        )


# --- the child: production's gate, recorded -------------------------------------


@pytest.mark.asyncio
async def test_the_gate_arm_runs_the_seed_row_through_the_gate(tmp_path, monkeypatch) -> None:
    calls: list[tuple[Any, ...]] = []

    async def fake_canary(selector, verbose, batch=None, *, entries=None, **kwargs):
        calls.append((selector, entries, kwargs))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "khalifa.json"
    await live.capture_one("khalifa", output, 4, through_identity_gate=True)
    assert calls == [(None, [live.seed_entry("khalifa")], {"through_identity_gate": True})]
    observation = Observation.model_validate_json(output.read_text())
    # The gate never answered, so the case counts as not established.
    assert observation.site_identity == SiteIdentity(established=False)

    await live.capture_one("khalifa", tmp_path / "default.json", 4)
    assert calls[-1] == (None, [live.dev2_entry("khalifa")], {})
    default = Observation.model_validate_json((tmp_path / "default.json").read_text())
    assert default.site_identity is None


@pytest.mark.asyncio
async def test_a_proxy_case_has_no_gate_to_go_through(tmp_path, monkeypatch) -> None:
    # G-06 extended the gate to the cohort (DEV2 and COHORT); dev4/dev5 stay outside it.
    async def fake_canary(selector, verbose, batch=None, *, entries=None, **kwargs):
        assert kwargs == {}
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "rwth.json"
    await live.capture_one("rwth", output, 4, through_identity_gate=True)
    assert Observation.model_validate_json(output.read_text()).site_identity is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title,established,homepage",
    [("ETH Zurich | Home", True, "https://ethz.ch/"), ("Welcome", False, None)],
)
async def test_the_observation_records_what_productions_gate_said(
    tmp_path, monkeypatch, catalogue_session, title, established, homepage
) -> None:
    """The canary's runner calls the real ``_identify_site``; the harness only listens."""
    # Today's title rule (R6 off): this test pins what the harness records, not the branch.
    monkeypatch.setattr("app.catalogue.discovery.SITE_IDENTITY_V2", False)
    provider = SimpleNamespace(search=AsyncMock(return_value=SimpleNamespace(results=[])))
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", lambda: provider)
    fetcher = SimpleNamespace(get=AsyncMock(side_effect=lambda url, **_: _page(url, title)))
    answers: list[dict | None] = []

    async def fake_canary(selector, verbose, batch=None, *, entries=None, **kwargs):
        canary._install_identified_sites(catalogue_session, entries, establish=False)
        uni = catalogue_session.get(University, _row("ethz").id)
        adapter = CatalogueDiscoveryAdapter(
            fetcher, session=catalogue_session, university_ids=[uni.id], live_limit=1
        )
        trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
        answers.append(await adapter._identify_site(uni, trace))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "ethz.json"
    await live.capture_one("ethz", output, 4, through_identity_gate=True)
    observation = Observation.model_validate_json(output.read_text())
    assert observation.site_identity == SiteIdentity(established=established, homepage=homepage)
    assert (answers[0] or {}).get("homepage") == homepage
    # The seed row's own domain was probed first, as production does.
    assert fetcher.get.call_args_list[0].args[0] == "https://ethz.ch/"
    if not established:
        # Production's one-query fallback ran (ticket 05 Q4), with identity only.
        query = provider.search.call_args.kwargs["query"]
        assert query == '"ETH Zurich" "Switzerland" official university website'


# --- the parent and the scorecard ------------------------------------------------


def test_the_parent_passes_the_arm_to_the_child_and_the_capture(tmp_path, monkeypatch) -> None:
    argv = ["live", "--live", "--case", "uio", "--out", str(tmp_path), "--through-identity-gate"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands: list[list[str]] = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="uio").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--through-identity-gate" in commands[0]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.config["through_identity_gate"] is True


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
        {"version": "test", "split": "development", "cases": [case("a"), case("b")]}
    )


def _write(root: Path, arm: str, observations: list[dict]) -> None:
    target = root / f"x-{arm}" / "20261018T000001Z"
    target.mkdir(parents=True)
    capture = {
        "pipeline_sha": "abc",
        "captured_at": "20261018T000001Z",
        "mode": "live",
        "config": {},
        "observations": observations,
    }
    (target / "capture.json").write_text(json.dumps(capture))


def test_the_scorecard_reports_identity_established_n_of_n(tmp_path: Path) -> None:
    _write(tmp_path, "off", [{"case_id": "a"}, {"case_id": "b"}])
    _write(
        tmp_path,
        "on",
        [
            {"case_id": "a", "site_identity": {"established": True, "homepage": "https://a.edu/"}},
            {"case_id": "b", "site_identity": {"established": False}},
        ],
    )
    card = scorecard.build(_dataset(), scorecard.load_run(tmp_path), allow_drafts=True)
    assert card["arms"]["off"]["repetitions"][0]["site_identity"] == {}
    assert card["arms"]["on"]["repetitions"][0]["site_identity"] == {"a": True, "b": False}
    assert "| identity established | 0/0 | 1/2 |" in scorecard.render(card)


def test_a_run_without_the_gate_keeps_its_table_shape(tmp_path: Path) -> None:
    _write(tmp_path, "off", [{"case_id": "a"}])
    card = scorecard.build(_dataset(), scorecard.load_run(tmp_path), allow_drafts=True)
    assert "identity established" not in scorecard.render(card)
