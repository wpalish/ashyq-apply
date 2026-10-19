"""The verified knowledge base: build, merge, staleness, and the kb research mode.

Owner decision 2026-10-19: live search frozen; a CS bachelor is answered from
the KB. Every URL and quote below is synthetic test data.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.catalogue.importer import import_catalogue
from app.catalogue.retrieval import retrieve
from app.config import Settings
from app.db import create_all_for_tests
from app.domain.enums import ClaimStatus, ClaimType
from app.knowledge import load_knowledge_base, review_label, stale_reasons
from app.knowledge.claims import answer
from app.models import ClaimRow, ProgramResultRow, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from evaluation.research.expert import kb_build
from tests.conftest import profile_row

MIT = "qs2027-001"
URL = "https://www.mit.edu/admissions/synthetic"


def _fact(key: str, value: Any, quote: str, **extra: Any) -> dict[str, Any]:
    return {
        "key": key,
        "value": value,
        "period": None,
        "academic_year": None,
        "population": None,
        "source_url": URL,
        "quote": quote,
        "source_type": "official",
        "accessed_on": "2026-10-19",
        "verified_on": "2026-10-19",
        **extra,
    }


def _kb(path: Path, entries: dict[str, Any], version: str = "test.kb") -> Path:
    path.write_text(
        json.dumps(
            {
                "format": "kb-cs-bachelor/1",
                "version": version,
                "built_at": "2026-10-19",
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    return path


def _mit_entry(**facts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "seed_id": MIT,
        "review_status": "expert_checked",
        "verified_on": "2026-10-19",
        "university": "Massachusetts Institute of Technology (MIT)",
        "country": "United States of America",
        "official_domain": "mit.edu",
        "programme": {
            "status": "known",
            "urls": [URL],
            "evidence": [
                {
                    "url": URL,
                    "quote": "Bachelor of Science in Computer Science",
                    "accessed_on": "2026-10-19",
                    "verified_on": "2026-10-19",
                }
            ],
        },
        "facts": facts,
    }


# ------------------------------------------------------------------ converter


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _batch(root: Path) -> None:
    _write(
        root / "batch1/programme" / f"{MIT}.0-local.json",
        {"case": MIT, "programme": {"url": URL, "title": "Computer Science BSc"}, "answers": {}},
    )
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "english": {
                    "status": "known",
                    "value": {"ielts_overall": 7.0},
                    "url": URL,
                    "quote": "IELTS 7.0 overall",
                },
                "deadline": {
                    "status": "known",
                    "value": "2027-01-05",
                    "url": "https://elsewhere.example/deadline",
                    "quote": "Apply by 5 January 2027",
                },
            },
        },
    )


def _report(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _row(item: str, url: str, official: bool = True, found: bool = True) -> dict[str, Any]:
    return {
        "case": MIT,
        "item": item,
        "url": url,
        "outcome": "ok",
        "official": official,
        "quote_found": found,
    }


def test_converter_marks_known_only_what_the_ci_check_found(tmp_path):
    _batch(tmp_path / "drafts")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [
            _row("programme", URL),
            _row("english", URL),
            _row("deadline", "https://elsewhere.example/deadline", official=False),
        ],
    )
    data = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")
    assert data["version"] and data["built_at"] == "2026-10-21"
    entry = data["entries"][MIT]
    assert entry["programme"]["status"] == "known"
    english = entry["facts"]["english"]
    assert [f["key"] for f in english] == ["ielts.overall"]
    fact = english[0]
    assert fact["value"] == 7.0 and fact["quote"] == "IELTS 7.0 overall"
    assert fact["source_url"] == URL and fact["unit"] == "IELTS band"
    assert fact["accessed_on"] == "2026-10-19"
    assert fact["verified_on"] == "2026-10-20"  # the date of the CI check (report name)
    assert {"period", "academic_year", "population"} <= set(fact)
    assert entry["facts"]["deadline"] == []
    deadline = next(u for u in entry["unknown"] if u["key"] == "deadline")
    assert "not an official domain" in deadline["reason"]


def test_converter_keeps_a_past_year_fee_as_stale_with_its_period(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch2/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "tuition": {
                    "status": "known",
                    "value": {
                        "amount": 555000,
                        "currency": "SEK",
                        "academic_year": "2026/27",
                        "period": "programme (total, 3 years)",
                    },
                    "url": URL,
                    "quote": "Total programme price 555 000 kr (2026/27)",
                },
            },
        },
    )
    rows = [_row("tuition", URL)]
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", rows)
    container = _report(tmp_path / "evidence_check.container-2026-10-19.json", rows)
    assert (
        kb_build.build(root, [container], built_at="2026-10-19")["entries"][MIT]["facts"]["tuition"]
        == []
    )  # a container pre-check is not the CI evidence check
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    (fee,) = entry["facts"]["tuition"]
    assert fee["value"] == {"amount": 555000.0, "currency": "SEK"}
    assert fee["period"] == "programme (total, 3 years)" and fee["academic_year"] == "2026/27"
    assert fee["stale"] and any("2026/27" in r for r in fee["stale_reasons"])
    assert not any(u["key"] == "tuition" for u in entry["unknown"])


def test_converter_without_evidence_knows_nothing(tmp_path):
    _batch(tmp_path / "drafts")
    data = kb_build.build(tmp_path / "drafts", [], built_at="2026-10-21")
    entry = data["entries"][MIT]
    assert entry["known_fact_count"] == 0
    assert entry["programme"]["status"] == "unknown"
    assert all("unverified" in u["reason"] or "did not" in u["reason"] for u in entry["unknown"])


def test_verify_evidence_accepts_kb_list_domains():
    from scripts import verify_evidence

    assert verify_evidence.is_official("https://web.mit.edu/x", MIT)
    assert verify_evidence.is_official("https://www.ox.ac.uk/admissions", "qs2027-004")
    assert verify_evidence.is_official("https://www.mit.edu/", "mit", seed_id=MIT)
    assert not verify_evidence.is_official("https://mit.example.com/", MIT)
    assert verify_evidence.is_official("https://cs.illinois.edu/x", "qs2027-074")  # extra_domains
    assert verify_evidence.is_official("https://www.rug.nl/x", "groningen")


# --------------------------------------------------------------------- loader


def test_loader_merges_the_development_import_by_seed_id(tmp_path):
    built = _kb(
        tmp_path / "kb.json",
        {
            MIT: _mit_entry(
                english=[_fact("ielts.overall", 7.0, "IELTS 7.0", verified_on="2026-10-19")]
            )
        },
    )
    imported = tmp_path / "imported.json"
    imported.write_text(
        json.dumps(
            {
                "format": "kb-imported-dev/1",
                "entries": {
                    MIT: {
                        **_mit_entry(
                            english=[
                                _fact("ielts.overall", 6.5, "IELTS 6.5", verified_on="2026-10-01")
                            ],
                            deadline=[_fact("deadline", "2027-01-05", "5 Jan 2027")],
                        ),
                        "review_status": "human_verified",
                    },
                    "qs2027-002": {
                        **_mit_entry(),
                        "seed_id": "qs2027-002",
                        "review_status": "draft",
                        "official_domain": "imperial.ac.uk",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    kb = load_knowledge_base(built, imported)
    assert set(kb.entries) == {MIT, "qs2027-002"}
    mit = kb.entries[MIT]
    assert [f["value"] for f in mit.facts["english"]] == [7.0]  # the newer fact wins
    assert [f["value"] for f in mit.facts["deadline"]] == ["2027-01-05"]  # import fills a gap
    assert kb.by_domain("www.imperial.ac.uk") is kb.entries["qs2027-002"]
    assert review_label(kb.entries["qs2027-002"].review_status) == (
        "expert-checked, quote verified"
    )
    assert review_label("human_verified") == "human verified"
    assert load_knowledge_base(tmp_path / "none.json", tmp_path / "none2.json").entries == {}


def test_repository_import_loads():
    kb = load_knowledge_base()
    assert "qs2027-002" in kb.entries  # the committed development import
    for entry in kb.entries.values():
        for _q, fact in entry.all_facts():
            assert fact["source_url"].startswith("http") and fact["quote"]


def test_stale_facts_are_not_current():
    today = date(2026, 10, 19)
    assert stale_reasons(_fact("x", 1, "q", verified_on="2025-10-01"), today)
    assert stale_reasons(_fact("tuition", 1, "q", academic_year="2025/26"), today)
    assert stale_reasons(_fact("deadline", "2026-01-15", "q"), today)
    assert not stale_reasons(_fact("tuition", 1, "q", academic_year="2026/27"), today)
    # ... but a 2026/27 fee is not current for a fall 2027 applicant.
    assert stale_reasons(_fact("tuition", 1, "q", academic_year="2026/27"), today, "fall 2027")
    assert not stale_reasons(_fact("tuition", 1, "q", academic_year="2027/28"), today, "fall 2027")
    from app.knowledge import _entry

    entry = _entry(
        MIT,
        _mit_entry(
            english=[_fact("ielts.overall", 7.0, "IELTS 7.0", verified_on="2025-01-01")],
            tuition=[
                _fact(
                    "tuition",
                    {"amount": 60000, "currency": "USD"},
                    "USD 60,000",
                    academic_year="2027/28",
                )
            ],
        ),
        "t",
    )
    found = answer(entry, programme="CS", intake="fall 2027", academic_year="2026/27", today=today)
    by_type = {c.claim_type: c for c in found.claims}
    assert by_type[ClaimType.IELTS_MIN_OVERALL].status is ClaimStatus.POSSIBLY_STALE
    assert "Stale" in by_type[ClaimType.IELTS_MIN_OVERALL].notes
    assert by_type[ClaimType.TUITION].status is ClaimStatus.VERIFIED_CURRENT
    assert found.costs.items  # a current tuition fact is the cost table


# --------------------------------------------------------------- product mode


@pytest.fixture
def catalogue_session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test on any search provider, live discovery or page read."""
    import app.adapters.search as search
    from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
    from app.adapters.fetching import Fetcher
    from app.adapters.search import brave, exa, exa_mcp, fake, serper, tavily

    def refuse(*args, **kwargs):
        raise AssertionError("network or search was called in kb mode")

    async def refuse_async(*args, **kwargs):
        raise AssertionError("network or search was called in kb mode")

    monkeypatch.setattr(search, "get_search_provider", refuse)
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", refuse)
    for module in (brave, exa, exa_mcp, fake, serper, tavily):
        for name in dir(module):
            cls = getattr(module, name)
            if isinstance(cls, type) and name.endswith("SearchProvider") and hasattr(cls, "search"):
                monkeypatch.setattr(cls, "search", refuse_async)
    monkeypatch.setattr(LiveDiscoveryAdapter, "discover", refuse_async)
    monkeypatch.setattr(Fetcher, "get", refuse_async)


def _kb_settings(settings: Settings, tmp_path: Path, mode: str = "kb") -> Settings:
    kb = _kb(
        tmp_path / "kb.json",
        {
            MIT: _mit_entry(
                english=[
                    _fact("ielts.overall", 7.0, "IELTS 7.0 overall"),
                    _fact(
                        "english_evidence.toefl_ibt.minimum",
                        100,
                        "TOEFL 100",
                        verified_on="2025-01-01",
                    ),
                ],
                deadline=[_fact("deadline", "2027-01-05", "Apply by 5 January 2027")],
                tuition=[
                    _fact(
                        "tuition",
                        {"amount": 60000.0, "currency": "USD"},
                        "Tuition 2027/28: USD 60,000",
                        academic_year="2027/28",
                    )
                ],
            )
        },
    )
    return settings.model_copy(
        update={
            "knowledge_mode": mode,
            "knowledge_base_path": kb,
            "knowledge_imported_path": tmp_path / "no-import.json",
        }
    )


async def _run(session: Session, profile, settings: Settings, query: str) -> ResearchRun:
    uni = retrieve(session, query=query)[0]
    applicant = profile_row(session, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="queued",
        demo_mode=False,
        candidate_limit=1,
        verify_limit=1,
        university_ids=[uni.id],
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    await ResearchRunner(session, run, profile, settings).run_to_decision()
    return run


@pytest.mark.asyncio
async def test_kb_mode_answers_from_the_kb_without_network(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    assert run.stage == "awaiting_user_decision"
    assert run.settings_snapshot["knowledge_mode"] == "kb"
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    claims = {c["claim_type"]: c for c in row.payload["claims"]}
    assert set(claims) >= {"program_exists", "ielts_min_overall", "admission_deadline", "tuition"}
    ielts = claims["ielts_min_overall"]
    assert ielts["original_text_excerpt"] == "IELTS 7.0 overall"
    assert ielts["official_domain"] is True and ielts["confidence"] == 0.8
    assert ielts["status"] == "VERIFIED_CURRENT" and ielts["is_stale"] is False
    toefl = claims["toefl_min_total"]
    assert toefl["status"] == "POSSIBLY_STALE" and toefl["is_stale"] is True
    assert row.payload["costs"]["items"]["tuition"]["amount"] == 60000.0
    assert s.scalars(select(ClaimRow).where(ClaimRow.run_id == run.id)).all()
    assert run.pages_checked == 0


@pytest.mark.asyncio
async def test_kb_mode_says_no_verified_data_for_a_university_outside_it(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Stanford")
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    assert row.payload["claims"] == []
    questions = [q["question"] for q in row.payload["unresolved"]]
    assert any(q.startswith("No verified data yet for Stanford") for q in questions)
    assert s.scalars(select(ClaimRow).where(ClaimRow.run_id == run.id)).all() == []


def test_live_mode_keeps_the_live_pipeline(catalogue_session, settings, tmp_path, profile):
    from app.catalogue.discovery import CatalogueDiscoveryAdapter

    s = catalogue_session
    applicant = profile_row(s, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="queued",
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
    )
    live = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "live"))
    assert not live.kb_mode
    assert isinstance(live._make_discovery_adapter(live._make_fetcher()), CatalogueDiscoveryAdapter)
    kb = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "kb"))
    assert kb.kb_mode and kb._make_fetcher().offline
    # Demo mode keeps its own fixtures whatever the knowledge mode says.
    run.demo_mode = True
    assert not ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "kb")).kb_mode


def test_knowledge_mode_defaults_to_kb_and_rejects_others(monkeypatch):
    monkeypatch.delenv("UNIMATCH_KNOWLEDGE_MODE", raising=False)
    assert Settings().knowledge_mode == "kb"
    with pytest.raises(RuntimeError, match="KNOWLEDGE_MODE"):
        Settings(knowledge_mode="web", demo_mode=True)._validate_search()
