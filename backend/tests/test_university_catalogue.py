"""Local discovery survives outages without converting imported hints into facts."""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchOutcome, FetchResult
from app.adapters.search.base import SearchUnavailable
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import SEED_PATH, import_catalogue, seed_domain, validate_snapshot
from app.catalogue.retrieval import retrieve
from app.db import create_all_for_tests
from app.models import ResearchRun, University, UniversityObservation


@pytest.fixture
def catalogue_session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        yield session
    engine.dispose()


def snapshot():
    return json.loads(SEED_PATH.read_text())


def test_import_is_idempotent_and_preserves_curated_identity(catalogue_session):
    s = catalogue_session
    assert s.scalar(select(func.count()).select_from(University)) == 501
    assert s.scalar(select(func.count()).select_from(UniversityObservation)) == 500
    assert len([u for u in s.scalars(select(University)) if u.registry_entry]) == 19
    assert retrieve(s, query="Nazarbayev")
    assert import_catalogue(s)["new_observations"] == 0
    assert retrieve(s, query="Groningen")[0].domain == "rug.nl"
    assert len(retrieve(s, query="Nanyang")) == 1
    assert retrieve(s, query="MIT")[0].name == "Massachusetts Institute of Technology"


def test_seed_history_does_not_overwrite_live_identity_or_roll_back(catalogue_session):
    s = catalogue_session
    uni = retrieve(s, query="Massachusetts Institute")[0]
    uni.domain = "mit.edu"
    uni.domain_status = "site_identity_checked"
    s.flush()
    newer = snapshot()
    newer["generated_on"] = "2026-10-03"
    newer["universities"][0]["official_domain"] = "changed.edu"
    newer["universities"][0]["official_site"] = "https://changed.edu/"
    assert import_catalogue(s, newer)["new_observations"] == 500
    assert uni.domain == "mit.edu"
    assert uni.seed_version == "2026-10-03/1.0"
    import_catalogue(s)
    assert uni.seed_version == "2026-10-03/1.0"
    assert uni.domain_status == "site_identity_checked"


@pytest.mark.parametrize(
    "change", ["duplicate", "count", "schema", "private", "price", "refresh", "url"]
)
def test_invalid_import_is_atomic(catalogue_session, change):
    doc = snapshot()
    if change == "duplicate":
        doc["universities"][1] = deepcopy(doc["universities"][0])
    elif change == "count":
        doc["count"] = 499
    elif change == "schema":
        doc["schema_version"] = "2.0"
    elif change == "private":
        doc["universities"][0]["official_domain"] = "127.0.0.1"
    elif change == "price":
        doc["universities"][0]["tuition_usd_estimate"] = {"min": 9, "max": 1}
    elif change == "refresh":
        doc["universities"][0]["needs_live_refresh"] = False
    else:
        doc["universities"][0]["official_site"] = "javascript:alert(1)"
    with pytest.raises(ValueError):
        import_catalogue(catalogue_session, doc)
    assert catalogue_session.scalar(select(func.count()).select_from(UniversityObservation)) == 500


def test_conflicting_domains_remain_unknown():
    assert (
        seed_domain({"official_domain": "bath.edu", "official_site": "https://bath.ac.uk"}) is None
    )
    assert (
        seed_domain({"official_domain": "mit.edu", "official_site": "https://web.mit.edu"})
        == "mit.edu"
    )
    assert len(validate_snapshot(snapshot())) == 500


def test_local_filters_preference_and_unknown_prices(catalogue_session):
    s = catalogue_session
    europe = retrieve(s, country="europe")
    assert len(europe) > 100
    assert all(u.country != "United States" for u in europe)
    canadian = retrieve(s, country="canada")
    assert all(u.country == "Canada" for u in canadian)
    assert retrieve(s, preferred=["Canada"])[0].country == "Canada"
    excluded = retrieve(s, excluded=["Europe"])
    assert all(u.id not in {v.id for v in europe} for u in excluded)
    assert retrieve(s, query="MIT")[0].seed_snapshot["record"]["tuition_usd_estimate"] is None


def test_catalogue_api_filters_and_returns_only_preliminary_facts(paid_client, case_id):
    body = paid_client.get("/api/universities").json()
    assert body["catalogue_total"] == 501 and body["seed_count"] == 500
    assert len(body["items"]) == 20
    first = {u["id"] for u in body["items"]}
    second = paid_client.get("/api/universities?offset=20").json()
    assert first.isdisjoint(u["id"] for u in second["items"])
    mit = paid_client.get("/api/universities?q=MIT").json()["items"][0]
    assert mit["admissions_status"] == "unknown"
    assert mit["tuition_status"] == "needs_verification"
    assert mit["programme_status"] == "needs_research"
    assert "claims" not in mit and "admissions_snapshot" not in mit
    assert paid_client.get("/api/universities?country=canada").json()["total"] > 5
    assert paid_client.get(f"/api/universities?profile_id={case_id}").status_code == 200
    assert paid_client.get("/api/universities?profile_id=not-owned").status_code == 404
    assert paid_client.get("/api/universities?limit=501").status_code == 422


def test_selected_run_persists_ids_and_forces_live(paid_client, case_id):
    import app.db as db

    uid = paid_client.get("/api/universities?q=MIT").json()["items"][0]["id"]
    payload = {"profile_id": case_id, "university_ids": [uid, uid]}
    result = paid_client.post(
        "/api/runs", json=payload, headers={"Idempotency-Key": "catalogue-click"}
    )
    assert result.status_code == 202, result.text
    run_id = result.json()["id"]
    with db.session_scope() as s:
        run = s.get(ResearchRun, run_id)
        assert run.university_ids == [uid]
        assert run.demo_mode is False and run.candidate_limit == 1
    assert (
        paid_client.post(
            "/api/runs", json=payload, headers={"Idempotency-Key": "catalogue-click"}
        ).json()["id"]
        == run_id
    )


@pytest.mark.parametrize("ids,demo", [(["unknown"], False), ([], False), (["known"], True)])
def test_invalid_selected_run_is_rejected(paid_client, case_id, ids, demo):
    if ids == ["known"]:
        ids = [paid_client.get("/api/universities").json()["items"][0]["id"]]
    response = paid_client.post(
        "/api/runs", json={"profile_id": case_id, "university_ids": ids, "demo_mode": demo}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_provider_outage_keeps_candidates_without_inventing_programmes(
    catalogue_session, profile, monkeypatch
):
    uni = retrieve(catalogue_session, query="Massachusetts Institute")[0]
    provider = SimpleNamespace(
        search=AsyncMock(side_effect=SearchUnavailable("secret vendor body", http_status=429))
    )
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", lambda: provider)
    fetcher = SimpleNamespace(
        get=AsyncMock(
            return_value=FetchResult(url="https://mit.edu/", outcome=FetchOutcome.HTTP_ERROR)
        )
    )
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=catalogue_session, university_ids=[uni.id], live_limit=1
    )
    found = await adapter.discover(profile, 5)
    assert len(found) == 1 and found[0].name == uni.name
    assert found[0].programs == [] and found[0].rankings == []
    assert adapter.traces[0].search_limitations
    assert "429" in adapter.traces[0].search_failures[0]
    assert "secret vendor body" not in str(adapter.traces)
    query = provider.search.call_args.kwargs["query"]
    assert profile.display_name not in query and "6000" not in query


@pytest.mark.asyncio
async def test_identity_checks_page_preserves_proof_and_is_idempotent(catalogue_session):
    uni = retrieve(catalogue_session, query="Massachusetts Institute")[0]
    page = FetchResult(
        url="https://mit.edu/",
        outcome=FetchOutcome.OK,
        content=b"<title>Massachusetts Institute of Technology</title>",
    )
    fetcher = SimpleNamespace(get=AsyncMock(return_value=page))
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=catalogue_session, university_ids=[uni.id], live_limit=1
    )
    trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
    assert (await adapter._identify_site(uni, trace))["homepage"] == "https://mit.edu/"
    assert (await adapter._identify_site(uni, trace))["homepage"] == "https://mit.edu/"
    assert uni.domain_status == "site_identity_checked"
    assert catalogue_session.scalar(select(func.count()).select_from(UniversityObservation)) == 501
    proof = (
        catalogue_session.scalars(
            select(UniversityObservation).where(
                UniversityObservation.seed_version == "live-site-identity"
            )
        )
        .one()
        .payload
    )
    assert proof["accessed_at"] and proof["excerpt"] and proof["source_url"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,final",
    [
        (b"<title>University directory</title>", ""),
        (b"<h1>Massachusetts Institute of Technology</h1>", "https://evil.edu/"),
    ],
)
async def test_wrong_homepage_cannot_authorize_domain(catalogue_session, content, final):
    uni = retrieve(catalogue_session, query="Massachusetts Institute")[0]
    fetcher = SimpleNamespace(
        get=AsyncMock(
            return_value=FetchResult(
                url="https://mit.edu/", outcome=FetchOutcome.OK, content=content, final_url=final
            )
        )
    )
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=catalogue_session, university_ids=[uni.id], live_limit=1
    )
    assert await adapter._probe_site(uni, "https://mit.edu/") is None
    assert uni.domain_status == "seed"


@pytest.mark.asyncio
async def test_live_budget_and_timeout_leave_local_candidates(
    catalogue_session, profile, monkeypatch
):
    rows = retrieve(catalogue_session, country="Canada")[:2]
    adapter = CatalogueDiscoveryAdapter(
        SimpleNamespace(),
        session=catalogue_session,
        university_ids=[u.id for u in rows],
        live_limit=1,
    )
    enrich = AsyncMock(side_effect=TimeoutError)
    monkeypatch.setattr(adapter, "_enrich", enrich)
    found = await adapter.discover(profile)
    assert len(found) == 2 and enrich.await_count == 1
    assert "time limit" in adapter.traces[0].errors[0]
    assert not found[1].programs


def test_real_postgres_catalogue_import(pg_session):
    assert import_catalogue(pg_session)["universities"] == 501
    pg_session.commit()
    assert import_catalogue(pg_session)["new_observations"] == 0


@pytest.mark.asyncio
async def test_offline_selected_run_finishes_with_honest_unknowns(
    catalogue_session, profile, settings, monkeypatch
):
    from app.adapters.fetching import Fetcher
    from app.models import ClaimRow, ProgramResultRow
    from app.pipeline.runner import ResearchRunner
    from app.pipeline.state import RunState
    from tests.conftest import profile_row

    async def unavailable(self, url, **kwargs):
        return FetchResult(url=url, outcome=FetchOutcome.NETWORK_UNAVAILABLE)

    monkeypatch.setattr(Fetcher, "get", unavailable)
    provider = SimpleNamespace(search=AsyncMock(side_effect=SearchUnavailable("outage")))
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", lambda: provider)
    s = catalogue_session
    uni = retrieve(s, query="Massachusetts Institute")[0]
    applicant = profile_row(s, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="queued",
        demo_mode=False,
        candidate_limit=1,
        verify_limit=1,
        university_ids=[uni.id],
        stage_state=RunState.load(None).dump(),
    )
    s.add(run)
    s.flush()
    await ResearchRunner(s, run, profile, settings).run_to_decision()
    assert run.stage == "awaiting_user_decision"
    result = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    assert result.eligibility == "NEEDS_OFFICIAL_CLARIFICATION"
    assert s.scalar(select(func.count()).select_from(ClaimRow)) == 0
    assert run.settings_snapshot["university_ids"] == [uni.id]


def test_every_seed_country_has_a_region(catalogue_session):
    from app.catalogue.retrieval import REGIONS

    assert {u.country for u in catalogue_session.scalars(select(University))} <= set().union(
        *REGIONS.values()
    )


@pytest.mark.asyncio
async def test_acronym_identity_needs_matching_host_and_university_heading(catalogue_session):
    uni = next(u for u in catalogue_session.scalars(select(University)) if u.name == "UCL")
    fetcher = SimpleNamespace(
        get=AsyncMock(
            return_value=FetchResult(
                url="https://ucl.ac.uk/",
                outcome=FetchOutcome.OK,
                content=b"<title>UCL - London's Global University</title>",
            )
        )
    )
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=catalogue_session, university_ids=[uni.id], live_limit=1
    )
    assert await adapter._probe_site(uni, "https://directory.edu/") is None
    assert (await adapter._probe_site(uni, "https://ucl.ac.uk/"))[
        "homepage"
    ] == "https://ucl.ac.uk/"
