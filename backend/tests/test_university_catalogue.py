"""Local discovery survives outages without converting imported hints into facts."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
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


@pytest.mark.parametrize(
    "query",
    [
        "Columbia University",
        "University College Dublin",
        "Durham University",
        "Korea University",
        "Northwestern University",
    ],
)
def test_the_university_named_exactly_comes_first(catalogue_session, query):
    """Top-500 audit (PR #44): these exact names put another university first."""
    from app.domain.dedupe import normalize

    first = retrieve(catalogue_session, query=query)[0]
    assert normalize(query) in {normalize(first.name), *(normalize(a) for a in first.aliases or [])}


def test_every_seed_name_finds_its_own_university_first(catalogue_session):
    from app.catalogue.importer import identity_key

    by_key = {u.identity_key: u for u in catalogue_session.scalars(select(University))}
    misses = []
    for record in snapshot()["universities"]:
        own = by_key[identity_key(record["name"], record["country"])]
        found = retrieve(catalogue_session, query=record["name"])
        if not found or found[0].id != own.id:
            misses.append(record["name"])
    assert misses == []


def test_an_empty_query_keeps_the_previous_order(catalogue_session):
    rows = retrieve(catalogue_session)
    assert [u.id for u in rows] == [
        u.id
        for u in sorted(
            rows,
            key=lambda u: (0 if u.registry_entry else 1, normalize_name(u.name), u.id),
        )
    ]


def normalize_name(name: str) -> str:
    from app.domain.dedupe import normalize

    return normalize(name)


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


# ------------------------------------------------- verified-data coverage (CAT-1)

KB_URL = "https://www.mit.edu/admissions/synthetic"


def _kb_fact(key: str, value, quote: str, **extra) -> dict:
    return {
        "key": key,
        "value": value,
        "period": None,
        "academic_year": None,
        "population": None,
        "source_url": KB_URL,
        "quote": quote,
        "source_type": "official",
        "accessed_on": "2026-10-19",
        "verified_on": "2026-10-19",
        **extra,
    }


def _kb_entries() -> dict:
    """MIT with facts, Stanford with a related route only, Imperial with nothing verified."""
    programme = {
        "status": "known",
        "urls": [KB_URL],
        "evidence": [{"url": KB_URL, "quote": "Bachelor of Science in Computer Science"}],
    }
    return {
        "qs2027-001": {
            "seed_id": "qs2027-001",
            "review_status": "expert_checked",
            "verified_on": "2026-10-19",
            "university": "Massachusetts Institute of Technology (MIT)",
            "official_domain": "mit.edu",
            "programme": programme,
            "facts": {
                "english": [_kb_fact("ielts.overall", 7.0, "IELTS 7.0 overall")],
                "deadline": [_kb_fact("deadline", "2027-01-05", "Apply by 5 January 2027")],
                "tuition": [
                    _kb_fact(
                        "tuition",
                        {"amount": 2190.0, "currency": "CHF"},
                        "CHF 2,190 per semester",
                        period="semester",
                        caveat="fee policy page; no academic year printed",
                    )
                ],
                "documents": [
                    _kb_fact("documents.passport", {"kind": "passport"}, "a passport copy"),
                    _kb_fact("documents.transcript", {"kind": "transcript"}, "transcripts"),
                ],
            },
            "not_applicable": [
                {"question": "gpa", "key": "gpa", "reason": "no minimum", "quote": "none"}
            ],
        },
        "qs2027-003": {
            "seed_id": "qs2027-003",
            "review_status": "draft",
            "verified_on": "2026-10-19",
            "university": "Stanford University",
            "official_domain": "stanford.edu",
            "programme": {
                "status": "unknown",
                "related_programme_urls": ["https://cs.stanford.edu/related"],
            },
            "facts": {
                "tuition": [
                    _kb_fact(
                        "tuition",
                        {"amount": 60000.0, "currency": "USD"},
                        "Tuition 2026/27: USD 60,000",
                        period="year",
                        academic_year="2026/27",
                    )
                ]
            },
        },
        "qs2027-002": {
            "seed_id": "qs2027-002",
            "review_status": "draft",
            "university": "Imperial College London",
            "official_domain": "imperial.ac.uk",
            "programme": {"status": "unknown"},
            "facts": {},
        },
    }


@pytest.fixture
def kb_mode(monkeypatch, tmp_path):
    """The catalogue route in kb mode on a three-entry KB, judged on 2026-10-19."""
    import app.api.routes_universities as routes
    from app.config import get_settings

    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps({"version": "test.kb", "entries": _kb_entries()}), encoding="utf-8")
    settings = get_settings().model_copy(
        update={
            "demo_mode": False,
            "knowledge_mode": "kb",
            "knowledge_base_path": kb,
            "knowledge_imported_path": tmp_path / "no-import.json",
        }
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr("app.knowledge.claims.kb_today", lambda: date(2026, 10, 19))
    return settings


def _card(client, query: str, extra: str = "") -> dict:
    return client.get(f"/api/universities?q={query}{extra}").json()["items"][0]


def test_kb_mode_cards_carry_the_verified_coverage(paid_client, kb_mode):
    mit = _card(paid_client, "MIT")["knowledge"]
    assert mit == {
        "in_kb": True,
        "programme_page": "known",
        # English, deadline and tuition known; GPA verified as not applicable.
        "core_answered": 4,
        "documents": 2,
        "verified_on": "2026-10-19",
        "stale_count": 0,
        "review_label": "expert-checked, quote verified",
        "tuition": {
            "amount": 2190.0,
            "currency": "CHF",
            "range_low": None,
            "range_high": None,
            "period": "semester",
            "academic_year": None,
            "stale": False,
            "stale_reasons": [],
            "stale_messages": [],
            "caveat": "fee policy page; no academic year printed",
            "caveat_message": {"key": "caveat.feePolicy", "params": {}, "parts": {}},
            "source_url": KB_URL,
        },
    }
    stanford = _card(paid_client, "Stanford")["knowledge"]
    assert stanford["in_kb"] and stanford["programme_page"] == "related_only"
    assert stanford["core_answered"] == 1
    # No profile, no intake: a 2026/27 fee is current until its year is over.
    assert stanford["tuition"]["stale"] is False and stanford["stale_count"] == 0
    # In the KB with nothing verified, or not in it at all: no verified data.
    for query in ("Imperial", "Oxford"):
        card = _card(paid_client, query)
        assert card["knowledge"]["in_kb"] is False and card["knowledge"]["tuition"] is None
        assert card["tuition_status"] == "needs_verification"


def test_kb_mode_filters_to_verified_rows_and_counts_them(paid_client, kb_mode, case_id):
    body = paid_client.get("/api/universities").json()
    assert body["kb_total"] == 2 and body["catalogue_total"] == 501
    verified = paid_client.get("/api/universities?verified=true").json()
    assert verified["total"] == 2
    assert {u["name"] for u in verified["items"]} == {
        "Massachusetts Institute of Technology",
        "Stanford University",
    }
    assert paid_client.get("/api/universities?verified=true&q=Oxford").json()["total"] == 0
    # A fall 2027 CS bachelor's profile: the run's rule makes the 2026/27 fee stale.
    mine = _card(paid_client, "Stanford", f"&profile_id={case_id}")["knowledge"]
    assert mine["stale_count"] == 1 and mine["tuition"]["stale"] is True
    assert mine["tuition"]["stale_reasons"] == [
        "academic year 2026/27 is before the fall 2027 intake's 2027/28"
    ]
    # Keyed beside the English, so the card can say it in ru and kk.
    assert [m["key"] for m in mine["tuition"]["stale_messages"]] == ["stale.yearBeforeIntake"]


def test_kb_mode_shows_no_kb_data_for_a_request_the_kb_does_not_answer(paid_client, kb_mode):
    from app.corpus.demo_profile import DEMO_PROFILE

    other = DEMO_PROFILE.model_copy(deep=True)
    other.context.intended_fields = ["medicine"]
    created = paid_client.post("/api/profiles", json=other.model_dump(mode="json"))
    body = paid_client.get(f"/api/universities?profile_id={created.json()['id']}&q=MIT").json()
    assert body["kb_total"] == 0 and body["items"][0]["knowledge"]["in_kb"] is False


@pytest.mark.parametrize("update", [{"knowledge_mode": "live"}, {"demo_mode": True}])
def test_live_and_demo_cards_have_no_knowledge_block(paid_client, monkeypatch, update):
    import app.api.routes_universities as routes
    from app.config import get_settings

    settings = get_settings().model_copy(
        update={"demo_mode": False, "knowledge_mode": "kb", **update}
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    body = paid_client.get("/api/universities?verified=true").json()
    assert body["kb_total"] is None
    # ``verified`` means nothing without a knowledge base: nothing is filtered.
    assert body["total"] == 501
    assert all(u["knowledge"] is None for u in body["items"])
