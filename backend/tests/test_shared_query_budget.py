"""Plan rule BL-1: one budget of six provider queries per institution.

Five cohort cases sent seven (discovery six, then the scholarship search one,
run 37279746829). With the rule on, every stage spends from the count kept
on the candidate, and topic search leaves one query for the scholarship
search that runs after it.
"""

from __future__ import annotations

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship import web_scholarships
from app.adapters.search import intent
from app.domain.enums import DegreeLevel
from tests.test_scholarship_search_fallback import Provider


def candidate(used: int) -> Candidate:
    return Candidate(
        name="University of Groningen",
        country="Netherlands",
        city="Groningen",
        domain="www.rug.nl",
        search_queries_used=used,
    )


PROGRAM = CandidateProgram(
    name="Computing Science",
    field="computer science",
    degree=DegreeLevel.BACHELOR,
    url="https://www.rug.nl/bachelors/computing-science/",
)


@pytest.fixture
def shared(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)


@pytest.fixture
def fake(monkeypatch):
    from app.adapters import search

    built = Provider(["https://www.rug.nl/a", "https://www.rug.nl/b", "https://www.rug.nl/c"])
    monkeypatch.setattr(search, "get_search_provider", lambda: built)
    return built


def test_on_by_default():
    assert intent.SHARED_QUERY_BUDGET is True


async def test_topic_search_leaves_one_query_for_scholarships(shared, fake):
    spent = candidate(3)
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    pages = await adapter._find_topic_pages(spent, PROGRAM, AdapterResult())
    assert [topic for topic, _ in pages] == ["english", "fees"]
    assert len(fake.calls) == 2
    assert spent.search_queries_used == 5


async def test_scholarship_search_spends_the_last_query(shared, fake):
    spent = candidate(5)
    adapter = web_scholarships.WebScholarshipAdapter(None, "2027/28")  # type: ignore[arg-type]
    await adapter._search_awards(spent, PROGRAM, AdapterResult())
    assert len(fake.calls) == 1
    assert spent.search_queries_used == 6


async def test_scholarship_search_is_skipped_when_the_budget_is_spent(shared, fake):
    spent = candidate(6)
    adapter = web_scholarships.WebScholarshipAdapter(None, "2027/28")  # type: ignore[arg-type]
    out = AdapterResult()
    assert await adapter._search_awards(spent, PROGRAM, out) == ()
    assert fake.calls == []
    assert any("scholarship search not run" in e for e in out.errors)
