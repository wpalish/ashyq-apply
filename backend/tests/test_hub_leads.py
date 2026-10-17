"""Plan rule HL-1: leads are followed from every official page read, accepted or not.

Evidence analysis 2026-10-17 §0 cause 3: TCD's course page classifies as a
catalogue ("Computer Science - Courses" + h2 "Overview") and UCT's
international-applicants hub as unknown, so ``verify`` left both before the
lead scan; each carries the exact English-requirements link an expert used.
The fixtures below are minimal reconstructions of those two pages (same title,
headings and link shapes), not copies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter, _service_links
from app.domain.enums import ClaimType, DegreeLevel

COURSE = """<html><head><title>Computer Science - Courses | Trinity College Dublin</title></head>
<body><nav><a href="fixture://tcd/courses/undergraduate/fees/index.html">Fees</a>
<a href="fixture://tcd/courses/postgraduate/fees/index.html">Fees</a></nav>
<h1>Computer Science</h1><h2>Overview</h2>
<p>Computer Science at Trinity is a four-year course.</p>
<ul><li><a href="fixture://tcd/courses/a.html">Engineering</a></li>
<li><a href="fixture://tcd/courses/b.html">Mathematics</a></li>
<li><a href="fixture://tcd/courses/c.html">Physics</a></li>
<li><a href="fixture://tcd/courses/d.html">Computer Engineering</a></li>
<li><a href="fixture://tcd/courses/e.html">Data Science</a></li></ul>
<h2>Admission Requirements</h2>
<p>Applicants whose first language is not English: see the English language requirements
<a href="fixture://tcd/study/english-language-requirements/index.html">here.</a></p>
</body></html>"""

LANGUAGE = """<html><head><title>English Language Requirements - Trinity College Dublin</title>
</head><body><h1>English language requirements for undergraduate admission</h1>
<p>IELTS (academic): a minimum overall band score of 6.5, with a minimum of 6.0
in each section.</p></body></html>"""

HUB = """<html><head><title>International applicants | University of Cape Town</title></head>
<body><h1>International applicants</h1>
<p>Welcome to UCT.</p>
<ul><li><a href="fixture://uct/fees/postgraduate-fees.html">Postgraduate fees</a></li>
<li><a href="fixture://uct/fees/undergraduate-fees.html">Undergraduate fees</a></li>
<li><a href="fixture://uct/fees/application-fee.html">Application fee</a></li>
<li><a href="fixture://uct/funding/postgraduate-funding.html">Postgraduate funding</a></li>
<li><a href="fixture://uct/funding/scholarships.html">Scholarships</a></li></ul>
</body></html>"""

FEES = """<html><head><title>Undergraduate fees - University of Cape Town</title></head><body>
<h1>Undergraduate tuition fees for international students</h1>
<p>Tuition fee for international students: €12,000 per year.</p></body></html>"""


def _site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    pages = {
        "tcd/programme.html": COURSE,
        "tcd/study/english-language-requirements/index.html": LANGUAGE,
        "tcd/courses/undergraduate/fees/index.html": FEES,
        "tcd/courses/postgraduate/fees/index.html": FEES,
        "uct/hub.html": HUB,
        "uct/programme.html": "<html><body><p>Nothing here.</p></body></html>",
        "uct/fees/undergraduate-fees.html": FEES,
        "uct/fees/postgraduate-fees.html": FEES,
        "uct/fees/application-fee.html": FEES,
        "uct/funding/scholarships.html": "<p>Scholarships</p>",
        "uct/funding/postgraduate-funding.html": "<p>Funding</p>",
    }
    for name, html in pages.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    return root


def _tcd() -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="Trinity College Dublin",
        country="Ireland",
        city="Dublin",
        domain="tcd.ie",
        costs_url="fixture://tcd/costs-known.html",
        scholarships_url="fixture://tcd/awards-known.html",
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://tcd/programme.html",
    )
    return candidate, program


def _uct(*, costs_url: str | None = None) -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="University of Cape Town",
        country="South Africa",
        city="Cape Town",
        domain="uct.ac.za",
        admissions_url="fixture://uct/hub.html",
        costs_url=costs_url,
    )
    program = CandidateProgram(
        name="BSc Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://uct/programme.html",
    )
    return candidate, program


async def _verify(settings, root: Path, candidate: Candidate, program: CandidateProgram):
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, program, "fall 2027")


@pytest.fixture
def hub_leads(monkeypatch):
    monkeypatch.setattr(web_requirements, "HUB_LEADS", True)
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)


@pytest.mark.asyncio
async def test_off_a_rejected_course_page_is_a_dead_end(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(web_requirements, "HUB_LEADS", False)
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)
    result = await _verify(settings, _site(tmp_path), *_tcd())
    assert [o.url for o in result.page_outcomes] == ["fixture://tcd/programme.html"]
    assert result.page_outcomes[0].category == "classifier-rejected"


@pytest.mark.asyncio
async def test_rejected_course_page_language_link_is_read(settings, tmp_path, hub_leads):
    result = await _verify(settings, _site(tmp_path), *_tcd())
    outcomes = {o.url: o for o in result.page_outcomes}
    # The course page still reads as a catalogue and nothing is claimed from it.
    assert outcomes["fixture://tcd/programme.html"].category == "classifier-rejected"
    assert not [c for c in result.claims if c.source_url == "fixture://tcd/programme.html"]
    assert "fixture://tcd/study/english-language-requirements/index.html" in outcomes
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert [c.normalized_value for c in ielts] == [6.5]
    assert ielts[0].source_url == "fixture://tcd/study/english-language-requirements/index.html"
    # The candidate already has a cost page: the undergraduate fee link is read
    # here as a fee page, the postgraduate one never.
    assert "fixture://tcd/courses/undergraduate/fees/index.html" in outcomes
    assert "fixture://tcd/courses/postgraduate/fees/index.html" not in outcomes


@pytest.mark.asyncio
async def test_hub_follows_only_the_undergraduate_fee_link(settings, tmp_path, hub_leads):
    candidate, program = _uct(costs_url="fixture://uct/costs-known.html")
    result = await _verify(settings, _site(tmp_path), candidate, program)
    read = {o.url for o in result.page_outcomes}
    assert "fixture://uct/fees/undergraduate-fees.html" in read
    assert "fixture://uct/fees/postgraduate-fees.html" not in read
    assert "fixture://uct/fees/application-fee.html" not in read
    assert candidate.costs_url == "fixture://uct/costs-known.html"
    tuition = [c for c in result.claims if c.claim_type is ClaimType.TUITION]
    assert tuition and tuition[0].source_url == "fixture://uct/fees/undergraduate-fees.html"


@pytest.mark.asyncio
async def test_missing_cost_and_award_pages_are_set_from_hub_links(settings, tmp_path, hub_leads):
    root = _site(tmp_path)
    candidate, program = _uct()
    result = await _verify(settings, root, candidate, program)
    assert candidate.costs_url == "fixture://uct/fees/undergraduate-fees.html"
    assert candidate.scholarships_url == "fixture://uct/funding/scholarships.html"
    # Left to the cost adapter, which runs next on the same candidate.
    read = {o.url for o in result.page_outcomes}
    assert "fixture://uct/fees/undergraduate-fees.html" not in read
    assert "fixture://uct/fees/postgraduate-fees.html" not in read
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        _, costs = await WebCostAdapter(f, "2027/28").fetch(candidate)
    assert costs.pages_checked == 1
    assert {o.url for o in costs.page_outcomes} == {"fixture://uct/fees/undergraduate-fees.html"}


@pytest.mark.asyncio
async def test_off_leaves_missing_cost_page_missing(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(web_requirements, "HUB_LEADS", False)
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)
    candidate, program = _uct()
    await _verify(settings, _site(tmp_path), candidate, program)
    assert candidate.costs_url is None
    assert candidate.scholarships_url is None


def test_service_links_guard_and_order():
    fees, awards = _service_links(HUB, "fixture://uct/hub.html", "uct.ac.za", DegreeLevel.BACHELOR)
    assert fees == ["fixture://uct/fees/undergraduate-fees.html"]
    assert awards == ["fixture://uct/funding/scholarships.html"]
    # A master's request keeps the postgraduate links and drops the undergraduate one.
    fees, _ = _service_links(HUB, "fixture://uct/hub.html", "uct.ac.za", DegreeLevel.MASTER)
    assert fees == ["fixture://uct/fees/postgraduate-fees.html"]
    assert _service_links(HUB, "fixture://uct/hub.html", "", DegreeLevel.BACHELOR) == ([], [])
