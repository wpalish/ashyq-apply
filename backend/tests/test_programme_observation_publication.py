"""Early publication through real page classification and native migrated stores.

Only synthetic public pages, native owned SQLite/PostgreSQL, no IP/DNS/startup.
An observation is never an assessed result or an extracted admissions fact.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import inspect, select

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, PageCategory
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.search.base import SearchUnavailable
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.config import get_settings
from app.db import _alembic_config, migrate_to_head
from app.domain.enums import FetchOutcome
from app.jobs.store import JobStore
from app.models import ApplicantProfileRow, Job, ProgramResultRow, ResearchRun, University
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from app.schemas.profile import ApplicantProfileIn
from app.schemas.programme_observations import (
    PageReadProof,
    ProgrammeObservation,
    ProgrammeObservationSet,
    observation_id,
    observation_projection,
)
from tests.test_live_discovery import StubSite, program_html
from tests.test_preparation_graph_api import _foreign_case

pytest_plugins = ("tests.test_preparation_api",)
PAGE = "https://synthetic.edu/bsc/computer-science"


def observed(url=PAGE, *, at=None):
    return ProgrammeObservation(
        id=observation_id("Synthetic University", "synthetic.edu", url),
        institution="Synthetic University",
        domain="synthetic.edu",
        programme_url=url,
        requested_degree="bachelor",
        reads=(
            PageReadProof(
                content_hash=hashlib.sha256(b"synthetic public page").hexdigest(),
                fetched_at=at or datetime.now(UTC),
                page_type="program_detail",
                classified_degree="bachelor",
                classified_subject="Computer Science",
            ),
        ),
    )


def seed_run(lab, *, case=None):
    with lab["factory"]() as session:
        run = ResearchRun(
            profile_id=case or lab["case"],
            demo_mode=False,
            stage="candidate_discovery",
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        job_id = JobStore(session).enqueue("research", run_id=run.id).job_id
        session.commit()
        return run.id, job_id


def claimed_runner(lab, run_id, job_id):
    with lab["factory"]() as session:
        job = JobStore(session).claim(worker_id="synthetic-observation-worker")
        assert job is not None and job.id == job_id
        token = job.attempts
        session.commit()
    session = lab["factory"]()
    run = session.get(ResearchRun, run_id)
    profile = session.get(ApplicantProfileRow, lab["case"])
    assert run is not None and profile is not None
    return ResearchRunner(
        session,
        run,
        ApplicantProfileIn.model_validate(profile.payload),
        get_settings(),
        job_id=job_id,
        worker_id="synthetic-observation-worker",
        lease_token=token,
    )


def test_read_survives_next_optional_timeout_and_reload_without_an_assessment(prep_lab, tmp_path):
    lab = prep_lab
    run_id, job_id = seed_run(lab)
    runner = claimed_runner(lab, run_id, job_id)
    runner.profile.context.level = "bachelor"
    runner.profile.context.intended_fields = ["computer science"]
    html = program_html()
    site = StubSite({PAGE: html})
    adapter = LiveDiscoveryAdapter(
        site.install(Fetcher(tmp_path / "cache", offline=True)),
        observation_recorder=runner._record_programme_observation,
    )
    trace = DiscoveryTrace(institution="Synthetic University", domain="synthetic.edu")
    selected = {PageCategory.PROGRAM_PAGE: [PAGE]}

    async def research():
        await adapter._confirm_programs(
            selected, {PageCategory.PROGRAM_PAGE: []}, trace, runner.profile
        )
        # A second native session can read the accepted page BEFORE this await.
        with lab["factory"]() as reader:
            saved = reader.get(ResearchRun, run_id).programme_observations
            assert (
                observation_projection(saved)["programme_observations"][0]["programme_url"] == PAGE
            )
        await asyncio.sleep(10)

    try:
        with pytest.raises(TimeoutError):
            asyncio.run(asyncio.wait_for(research(), timeout=0.1))
    finally:
        runner.session.close()
    assert site.requested == [PAGE]
    assert len(adapter.confirmed_observations.items) == 1
    with lab["factory"]() as session:
        run = session.get(ResearchRun, run_id)
        proof = ProgrammeObservationSet.model_validate(run.programme_observations).items[0]
        assert proof.reads[0].content_hash == hashlib.sha256(html.encode()).hexdigest()
        assert proof.reads[0].classified_degree == "bachelor"
        assert proof.requirements_state == "unknown" and proof.compatibility == "not_assessed"
        assert (
            session.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run_id)).all()
            == []
        )
        assert session.get(Job, job_id).status == "running"
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["programme_observations"][0]["id"] == proof.id
    assert response.json()["results_count"] == 0
    exported = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert exported.status_code == 200
    exported_run = next(row for row in exported.json()["runs"] if row["id"] == run_id)
    assert exported_run["programme_observations"][0]["id"] == proof.id


@pytest.mark.parametrize(
    "stop", ["timeout", "cancelled", "run_cancelled", "lease_lost", "refusal", "checkpoint_busy"]
)
def test_catalogue_timeout_keeps_observation_while_controls_still_propagate(
    prep_lab, tmp_path, monkeypatch, stop
):
    lab = prep_lab
    run_id, job_id = seed_run(lab)
    runner = claimed_runner(lab, run_id, job_id)
    runner.profile.context.level = "bachelor"
    runner.profile.context.intended_fields = ["computer science"]
    with runner.session.no_autoflush:
        university = University(
            identity_key=uuid4().hex,
            name="Synthetic University",
            country="Canada",
            domain="synthetic.edu",
        )
        runner.session.add(university)
        runner.session.commit()
    adapter = CatalogueDiscoveryAdapter(
        StubSite({PAGE: program_html()}).install(Fetcher(tmp_path / "cache", offline=True)),
        session=runner.session,
        university_ids=[university.id],
        live_limit=1,
        observation_recorder=runner._record_programme_observation,
    )
    controls = {
        "cancelled": asyncio.CancelledError(),
        "run_cancelled": RunCancelled("synthetic cancel"),
        "lease_lost": LeaseLost("synthetic lost attempt"),
        "refusal": SearchUnavailable("synthetic refusal"),
        "checkpoint_busy": UniversityReadStopped("checkpoint_busy"),
    }
    original_wait = asyncio.wait_for

    async def wait_with_test_deadline(awaitable, *, timeout):
        assert timeout == 300  # This increment does not rewrite production budgets.
        return await original_wait(awaitable, timeout=0.1)

    async def enrichment(uni, profile, candidate, trace):
        await adapter._confirm_programs(
            {PageCategory.PROGRAM_PAGE: [PAGE]}, {PageCategory.PROGRAM_PAGE: []}, trace, profile
        )
        if stop == "timeout":
            await asyncio.sleep(10)
        raise controls[stop]

    monkeypatch.setattr(adapter, "_enrich", enrichment)
    monkeypatch.setattr("app.catalogue.discovery.asyncio.wait_for", wait_with_test_deadline)
    try:
        if stop == "timeout":
            candidates = asyncio.run(adapter.discover(runner.profile, 1))
            assert len(candidates) == 1 and not candidates[0].programs
            assert "time limit" in adapter.traces[0].errors[0]
        else:
            with pytest.raises(type(controls[stop])):
                asyncio.run(adapter.discover(runner.profile, 1))
        with lab["factory"]() as session:
            assert (
                len(
                    ProgrammeObservationSet.model_validate(
                        session.get(ResearchRun, run_id).programme_observations
                    ).items
                )
                == 1
            )
            assert session.get(Job, job_id).status == "running"
    finally:
        runner.session.close()


@pytest.mark.parametrize(
    "stop", ["cancel_run", "cancel_job", "same_worker_new_attempt", "new_worker"]
)
def test_cancel_or_lost_attempt_cannot_publish(prep_lab, stop):
    lab = prep_lab
    run_id, job_id = seed_run(lab)
    runner = claimed_runner(lab, run_id, job_id)
    with lab["factory"]() as session:
        if stop == "cancel_run":
            session.get(ResearchRun, run_id).cancelled = True
        elif stop == "cancel_job":
            JobStore(session).cancel(job_id)
        else:
            job = session.get(Job, job_id)
            job.attempts += 1
            if stop == "new_worker":
                job.worker_id = "another-worker"
        session.commit()
    try:
        with pytest.raises(RunCancelled if stop.startswith("cancel") else LeaseLost):
            runner._record_programme_observation(observed())
    finally:
        runner.session.close()
    with lab["factory"]() as session:
        assert session.get(ResearchRun, run_id).programme_observations is None
        assert session.get(Job, job_id).status != "succeeded"


def test_own_run_projection_export_and_delete_do_not_expose_foreign_or_corrupt_data(prep_lab):
    lab = prep_lab
    own, _ = seed_run(lab)
    foreign, _ = seed_run(lab, case=_foreign_case(lab))
    with lab["factory"]() as session:
        session.get(ResearchRun, own).programme_observations = {
            "private_corrupt_sentinel": "never echo"
        }
        session.get(ResearchRun, foreign).programme_observations = ProgrammeObservationSet(
            items=(observed(),)
        ).model_dump(mode="json")
        session.commit()
    response = lab["client"].get(f"/api/runs/{own}")
    assert response.status_code == 200
    assert response.json()["programme_observation_state"] == "unavailable"
    assert response.json()["programme_observations"] == []
    assert "private_corrupt_sentinel" not in response.text
    assert lab["client"].get(f"/api/runs/{foreign}").status_code == 404
    export = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert export.status_code == 200
    assert "private_corrupt_sentinel" not in export.text and foreign not in export.text
    assert lab["client"].delete(f"/api/profiles/{lab['case']}").status_code == 204
    with lab["factory"]() as session:
        assert session.get(ResearchRun, own) is None
        assert session.get(ResearchRun, foreign) is not None


def test_migration_roundtrip_keeps_existing_case_and_reads_old_null_rows(prep_lab):
    lab = prep_lab
    url = str(lab["engine"].url)
    run_id, _ = seed_run(lab)
    command.downgrade(_alembic_config(url), "d7a61e902024")
    assert "programme_observations" not in {
        col["name"] for col in inspect(lab["engine"]).get_columns("research_runs")
    }
    with lab["engine"].connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM applicant_profiles").scalar() == 1
    migrate_to_head(url)
    with lab["factory"]() as session:
        assert session.get(ResearchRun, run_id).programme_observations is None
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["programme_observations"] == []
    assert response.json()["programme_observation_state"] == "readable"


@pytest.mark.parametrize("kind", ["wrong_degree", "news", "unreadable", "offsite"])
def test_rejected_pages_do_not_become_observations(profile, tmp_path, monkeypatch, kind):
    profile.context.level = "master" if kind == "wrong_degree" else "bachelor"
    profile.context.intended_fields = ["computer science"]
    site = StubSite(
        {PAGE: "<html><h1>University news</h1></html>" if kind == "news" else program_html()}
    )
    fetcher = site.install(Fetcher(tmp_path / "cache", offline=True))
    if kind in {"offsite", "unreadable"}:

        async def get_page(*_args, **_kwargs):
            return FetchResult(
                url=PAGE,
                final_url="https://another.edu/bsc" if kind == "offsite" else PAGE,
                outcome=FetchOutcome.OK if kind == "offsite" else FetchOutcome.ROBOTS_DISALLOWED,
                text=program_html(),
                fetched_at=datetime.now(UTC),
            )

        monkeypatch.setattr(fetcher, "get", get_page)
    adapter = LiveDiscoveryAdapter(fetcher)
    trace = DiscoveryTrace(institution="Synthetic University", domain="synthetic.edu")
    selected = {PageCategory.PROGRAM_PAGE: [PAGE]}
    asyncio.run(
        adapter._confirm_programs(selected, {PageCategory.PROGRAM_PAGE: []}, trace, profile)
    )
    assert adapter.confirmed_observations.items == ()
    assert selected[PageCategory.PROGRAM_PAGE] == []


def test_same_page_retains_new_reads_and_explicit_caps_instead_of_inventing_completeness():
    start = datetime.now(UTC)
    saved = ProgrammeObservationSet()
    for index in range(61):
        saved = saved.add(observed(at=start + timedelta(seconds=index)))
    assert len(saved.items) == 1 and len(saved.items[0].reads) == 60
    assert saved.items[0].further_reads_omitted is True
    for index in range(151):
        saved = saved.add(observed(url=f"https://synthetic.edu/bsc/{index}"))
    assert len(saved.items) == 150 and saved.additional_observations_omitted is True
    assert observation_projection(None)["programme_observation_state"] == "readable"


@pytest.mark.parametrize("mutation", ["id", "url", "timestamp", "degree", "unknown_extra"])
def test_corrupt_observation_is_unavailable_without_echoing_raw_storage(mutation):
    raw = ProgrammeObservationSet(items=(observed(),)).model_dump(mode="json")
    item = raw["items"][0]
    if mutation == "id":
        item["id"] = uuid4().hex
    elif mutation == "url":
        item["programme_url"] = "javascript:alert(1)"
    elif mutation == "timestamp":
        item["reads"][0]["fetched_at"] = 123
    elif mutation == "degree":
        item["requested_degree"] = "unsupported"
    else:
        item["secret_corrupt_field"] = "never echo"
    result = observation_projection(raw)
    assert result == {
        "programme_observations": [],
        "programme_observation_state": "unavailable",
        "additional_programme_observations_omitted": False,
    }
