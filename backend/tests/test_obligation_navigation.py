"""Synthetic offline regressions, not live recall evidence."""

from pathlib import Path

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter, _obligation_links
from app.domain.enums import ClaimType, DegreeLevel
from tests.test_topic_search import Provider, candidate, program


async def _verify(settings, tmp_path: Path, pages: dict[str, str], enabled: bool):
    root = tmp_path / "site"
    (root / "uni").mkdir(parents=True)
    for name, html in pages.items():
        (root / "uni" / name).write_text(html, encoding="utf-8")
    cand = Candidate(name="University", country="Canada", city="", domain="uni.example")
    prog = CandidateProgram(
        name="Computer Science (BSc)",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://uni/programme.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as fetcher:
        return await WebRequirementsAdapter(
            fetcher,
            "2027/28",
            question_frontier=enabled,
        ).verify(cand, prog, "fall 2027")


@pytest.fixture(autouse=True)
def no_topics(monkeypatch):
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_navigation_only_page_retains_requirement_lead(settings, tmp_path, enabled):
    result = await _verify(
        settings,
        tmp_path,
        {
            "programme.html": '<title>Welcome</title><a href="fixture://uni/entry.html">Entry requirements</a>',
            "entry.html": "<title>Bachelor admission requirements</title><h1>Undergraduate admission requirements</h1><p>IELTS overall band of 6.5.</p>",
        },
        enabled,
    )
    assert ("fixture://uni/entry.html" in {p.url for p in result.page_outcomes}) == enabled
    assert (
        bool([c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]) == enabled
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_ielts_does_not_settle_academic_route(settings, tmp_path, enabled):
    result = await _verify(
        settings,
        tmp_path,
        {
            "programme.html": '<title>Computer Science (BSc)</title><h1>Bachelor of Science in Computer Science</h1><p>IELTS overall band of 7.0.</p><a href="fixture://uni/qualification.html">International qualifications</a>',
            "qualification.html": "<title>Bachelor admission requirements</title><h1>Undergraduate admission requirements</h1><p>Minimum GPA of 3.5 on a 4.0 scale.</p>",
        },
        enabled,
    )
    assert ("fixture://uni/qualification.html" in {p.url for p in result.page_outcomes}) == enabled
    assert any(c.claim_type is ClaimType.IELTS_MIN_OVERALL for c in result.claims)
    assert any(c.claim_type is ClaimType.MIN_GPA for c in result.claims) == enabled


def test_frontier_rejects_other_degree_exchange_external_and_duplicates():
    html = """<a href="https://uni.example/entry">Entry requirements</a>
    <a href="https://uni.example/entry#details">Entry requirements</a>
    <a href="https://uni.example/graduate/entry">Entry requirements</a>
    <a href="https://uni.example/exchange/entry">Entry requirements</a>
    <a href="https://uni.example/msc/entry">Entry requirements</a>
    <a href="https://evil.example/entry">Entry requirements</a>
    <a href="https://uni.example/docs">Required documents</a>"""
    assert _obligation_links(
        html, "https://uni.example/", "uni.example", academic=True, language=True, deadline=True
    ) == [
        ("https://uni.example/entry", False),
        ("https://uni.example/docs", False),
    ]


@pytest.mark.asyncio
async def test_frontier_cap_and_cycles(settings, tmp_path):
    links = "".join(
        f'<a href="fixture://uni/entry{i}.html">Entry requirements</a>' for i in range(9)
    )
    pages = {"programme.html": "<title>Welcome</title>" + links}
    pages.update({f"entry{i}.html": "<title>Welcome</title>" + links for i in range(9)})
    result = await _verify(settings, tmp_path, pages, True)
    urls = [p.url for p in result.page_outcomes]
    assert len(urls) == 1 + web_requirements._MAX_ROUTE_FOLLOWS
    assert len(urls) == len(set(urls))


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,expected", [(False, 1), (True, 2)])
async def test_multiple_topic_results_without_extra_queries(monkeypatch, enabled, expected):
    import app.adapters.search as search_pkg

    built = Provider(["https://www.rug.nl/a", "https://www.rug.nl/b", "https://www.rug.nl/c"])
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: built)
    cand = candidate()
    cand.search_queries_used = 4
    adapter = WebRequirementsAdapter(None, "2027/28", question_frontier=enabled)  # type: ignore[arg-type]
    pages = await adapter._find_topic_pages(cand, program(), AdapterResult())
    assert len(pages) == expected
    assert len(built.queries) == 1


@pytest.mark.parametrize(
    "field,key,neighbour",
    [
        ("Business Administration", "business_administration", "business analytics"),
        ("Mechanical Engineering", "mechanical_engineering", "computer engineering"),
    ],
)
def test_new_fields_are_literal_equivalents_only(field, key, neighbour):
    from app.adapters.search.ontology import canonical_field, is_equivalent

    assert canonical_field(field) == key
    assert not is_equivalent(field, neighbour)
