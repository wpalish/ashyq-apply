"""Plan rule RL-1: deadline and foreign-diploma route links below the hub.

Delft's admissions hub links "BSc - International diploma"; that page links
"Admission Requirements" (the IELTS minimum) and "Dates & Deadlines". The
adapter read the hub and stopped (control run claude-control-twopass-1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter, _route_links
from app.domain.enums import ClaimType, DegreeLevel

PROGRAMME = """<html><head><title>BSc Computer Science and Engineering - TU Delft</title></head>
<body><h1>BSc Computer Science and Engineering</h1>
<p>Bachelor of Science in Computer Science and Engineering. Read how to apply:
<a href="fixture://delft/international-diploma.html">BSc - International diploma</a>,
<a href="fixture://delft/msc-international-diploma.html">MSc - International diploma</a>,
<a href="fixture://delft/admission-requirements.html">Admission requirements</a>.</p>
</body></html>"""

ROUTE = """<html><head><title>BSc - International diploma - TU Delft</title></head><body>
<h1>BSc - International diploma</h1>
<p>Apply for a BSc programme with an international diploma.</p>
<ul><li><a href="fixture://delft/international-diploma/requirements.html">Admission Requirements</a></li>
<li><a href="fixture://delft/international-diploma/dates.html">Dates &amp; Deadlines</a></li></ul>
</body></html>"""

REQUIREMENTS = """<html><head><title>Admission requirements - TU Delft</title></head><body>
<h1>Admission requirements for a bachelor's programme</h1>
<h2>English language requirements</h2>
<p>IELTS (academic): a minimum overall band score of 6.5, with a minimum of 6.0
for each section.</p></body></html>"""

DATES = """<html><head><title>Dates and deadlines - TU Delft</title></head><body>
<h1>Dates and deadlines for bachelor's programmes</h1>
<p>Application deadline for the numerus fixus programmes: 15 January 2027.</p>
</body></html>"""


def _site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    (root / "delft" / "international-diploma").mkdir(parents=True)
    pages = {
        "programme.html": PROGRAMME,
        "international-diploma.html": ROUTE,
        "msc-international-diploma.html": "<p>IELTS 9.0 overall</p>",
        "admission-requirements.html": "<p>IELTS 9.0 overall</p>",
        "international-diploma/requirements.html": REQUIREMENTS,
        "international-diploma/dates.html": DATES,
    }
    for name, html in pages.items():
        (root / "delft" / name).write_text(html, encoding="utf-8")
    return root


async def _run(settings, root: Path):
    candidate = Candidate(name="TU Delft", country="Netherlands", city="Delft", domain="tudelft.nl")
    program = CandidateProgram(
        name="BSc Computer Science and Engineering",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://delft/programme.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, program, "fall 2027")


@pytest.fixture
def route_leads(monkeypatch):
    monkeypatch.setattr(web_requirements, "ROUTE_LEADS", True)


@pytest.mark.asyncio
async def test_off_reads_only_the_programme_page(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(web_requirements, "ROUTE_LEADS", False)
    result = await _run(settings, _site(tmp_path))
    read = {o.url for o in result.page_outcomes}
    assert "fixture://delft/international-diploma.html" not in read


@pytest.mark.asyncio
async def test_route_then_requirements_and_dates_are_read(settings, tmp_path, route_leads):
    result = await _run(settings, _site(tmp_path))
    read = {o.url for o in result.page_outcomes}
    assert "fixture://delft/international-diploma.html" in read
    assert "fixture://delft/international-diploma/requirements.html" in read
    assert "fixture://delft/international-diploma/dates.html" in read
    # A graduate route and a bare "Admission requirements" link off the route
    # are never followed.
    assert "fixture://delft/msc-international-diploma.html" not in read
    assert "fixture://delft/admission-requirements.html" not in read
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert [c.normalized_value for c in ielts] == [6.5]
    assert ielts[0].source_url == "fixture://delft/international-diploma/requirements.html"
    deadlines = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
    assert [str(c.normalized_value) for c in deadlines] == ["2027-01-15"]


def test_links_from_a_page_off_the_route():
    html = (
        '<a href="https://you.ubc.ca/applying-ubc/dates-deadlines/">Dates and deadlines</a>'
        '<a href="https://you.ubc.ca/applying-ubc/requirements/">Admission requirements</a>'
        '<a href="https://you.ubc.ca/applying-ubc/requirements/international-high-schools/">'
        "International high schools</a>"
        '<a href="https://example.org/dates">Key dates</a>'
    )
    links = _route_links(
        html, "https://you.ubc.ca/applying-ubc/", "ubc.ca", deadline=True, requirements=True
    )
    assert links == [
        ("https://you.ubc.ca/applying-ubc/dates-deadlines/", False),
        ("https://you.ubc.ca/applying-ubc/requirements/international-high-schools/", False),
    ]
    assert (
        _route_links(
            html, "https://you.ubc.ca/applying-ubc/", "ubc.ca", deadline=False, requirements=False
        )
        == []
    )
