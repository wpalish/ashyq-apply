"""A live search must not try synthetic government pages or hide missing sources."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.fetching import Fetcher
from app.adapters.government.web_government import WebGovernmentAdapter
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.diagnostics import DiagnosticKind, classify
from app.domain.enums import ClaimType, DegreeLevel
from app.models import Base, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from app.schemas.result import CostBreakdown
from tests.conftest import profile_row


@pytest.mark.parametrize("offline,with_corpus", [(False, False), (False, True), (True, False)])
async def test_fixture_default_requires_an_actual_offline_corpus(
    tmp_path, corpus_dir, monkeypatch, offline, with_corpus
):
    fetcher = Fetcher(
        tmp_path / "cache", offline=offline, corpus_dir=corpus_dir if with_corpus else None
    )
    get = AsyncMock()
    monkeypatch.setattr(fetcher, "get", get)

    result = await WebGovernmentAdapter(fetcher).post_study_work("Singapore")

    get.assert_not_awaited()
    assert result.claims == []
    assert result.pages_checked == result.pages_failed == 0
    assert len(result.errors) == 1
    assert "Singapore" in result.errors[0]
    assert "fixture://" not in result.errors[0]
    assert classify(result.errors[0]) is DiagnosticKind.UNKNOWN


async def test_demo_keeps_the_bundled_government_evidence(tmp_path, corpus_dir):
    async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus_dir) as fetcher:
        result = await WebGovernmentAdapter(fetcher).post_study_work("Singapore")

    assert result.pages_checked == 1
    assert result.pages_failed == 0
    assert len(result.claims) == 1
    assert result.claims[0].claim_type is ClaimType.POST_STUDY_WORK
    assert result.claims[0].source_url == "fixture://government/singapore.html"


async def test_live_run_persists_the_missing_government_source_as_unknown(
    settings, profile, monkeypatch
):
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(WebRequirementsAdapter, "verify", AsyncMock(return_value=AdapterResult()))
    monkeypatch.setattr(
        WebCostAdapter, "fetch", AsyncMock(return_value=(CostBreakdown(), AdapterResult()))
    )
    fetcher = Fetcher(settings.cache_dir, offline=False)
    get = AsyncMock()
    monkeypatch.setattr(fetcher, "get", get)
    try:
        with Session(engine) as session:
            row = profile_row(session, profile)
            run = ResearchRun(
                profile_id=row.id,
                stage="queued",
                demo_mode=False,
                stage_state=RunState.load(None).dump(),
            )
            session.add(run)
            session.commit()
            runner = ResearchRunner(session, run, profile, settings)
            runner._candidates = [
                Candidate(
                    name="Synthetic University",
                    country="Singapore",
                    city="Singapore",
                    domain="university.example",
                    programs=[
                        CandidateProgram(
                            name="BSc Computer Science",
                            field="computer science",
                            degree=DegreeLevel.BACHELOR,
                            url="https://university.example/computer-science",
                        )
                    ],
                )
            ]
            await runner._stage_verify(fetcher)
            session.expire_all()

            assert any("government source" in message for message in run.unknowns)
            assert not any("government" in message for message in run.errors)
            assert not any("fixture://" in message for message in run.errors + run.unknowns)
            assert run.pages_checked == run.pages_failed == 0
            get.assert_not_awaited()
    finally:
        engine.dispose()
