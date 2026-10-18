"""Plan rule FS-1: a topic page that speaks for another faculty claims nothing.

QB-1 paired run, Groningen on#1: topic search accepted the Faculty of
Economics and Business "Apply for a Bachelor" page (breadcrumb "Faculty of
Economics and Business › … › Apply for a Bachelor") and its IELTS 6.0 was
given to Computing Science, a Faculty of Science and Engineering programme at
6.5. On#2 read the university-wide per-faculty table and took its first IELTS
block (Campus Fryslân) — right by accident.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import (
    faculty_blocks,
    faculty_key,
    page_faculty,
    programme_faculty,
    readable_text,
)
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import ClaimType, DegreeLevel

PROGRAMME_URL = "fixture://rug/bachelors/computing-science.html"

PROGRAMME = """<html><head>
<title>Computing Science | Bachelor's degree programmes | University of Groningen</title></head>
<body><div class="rug-breadcrumbs" itemprop="breadcrumb">
<a href="/education/">Education</a> <a href="/bachelors/">Bachelor's degree programmes</a>
<a href="/bachelors/computing-science/">Computing Science</a></div>
<h1>Computing Science</h1>
<p>Bachelor's degree programme Computing Science, 3 years, English taught.</p>
<div><p>Faculty</p><p>Science and Engineering</p></div>
<p>Please be advised that Faculty of Science and Engineering students are expected to
bring their own device.</p>
</body></html>"""

#: The page FS-1 is about: another faculty's application route.
FEB = """<html><head>
<title>Step 1: Entry requirements | Apply for a Bachelor | University of Groningen</title></head>
<body><div class="rug-breadcrumbs" itemprop="breadcrumb">
<span><a href="/about-ug/">About us</a></span>
<span><a href="/feb/">Faculty of Economics and Business</a></span>
<span><a href="/feb/education/">Education</a></span>
<span><a href="/feb/education/admission-application/apply-bsc/">Apply for a Bachelor</a></span>
</div>
<h1>Step 1: Entry requirements</h1>
<h2>English language requirements</h2>
<p>For our Bachelor's programmes which are taught in English, the following
minimum requirements apply: IELTS Academic overall score 6.0.</p>
</body></html>"""

FSE = FEB.replace(
    "Faculty of Economics and Business", "Faculty of Science and Engineering"
).replace("/feb/", "/fse/")

NO_FACULTY = FEB.replace(
    '<span><a href="/feb/">Faculty of Economics and Business</a></span>', ""
).replace("/feb/", "/education/")

#: The university-wide page: one section per faculty, in this order.
TABLE = """<html><head>
<title>Bachelor's language requirements and exemptions | University of Groningen</title></head>
<body><h1>Bachelor's language requirements and exemptions (2026/27)</h1>
<h2>Language requirements per faculty</h2>
<p>Campus Fryslân</p>
<p>BSc Global Responsibility &amp; Leadership</p>
<p>IELTS (Academic): overall score 6.5 (min. 6.0 in all categories)</p>
<p>Faculty of Economics and Business</p>
<p>Econometrics and Operations Research</p>
<p>International Business</p>
<p>IELTS (Academic): overall score 6.0 (min. 6.0 in Speaking, 5.5 in Writing)</p>
<p>Faculty of Science and Engineering</p>
<p>Applied Mathematics</p>
<p>Computing Science</p>
<p>Physics</p>
<p>IELTS (Academic): overall score 7.0 (min. 6.5 in every category)</p>
<p>Faculty of Law</p>
<p>International and European Law</p>
<p>IELTS (Academic): overall score 7.5 (min. 6.0 in every category)</p>
</body></html>"""


def _site(tmp_path: Path, topic_html: str, table: str = TABLE) -> Path:
    root = tmp_path / "site"
    (root / "rug" / "bachelors").mkdir(parents=True)
    (root / "rug" / "bachelors" / "computing-science.html").write_text(PROGRAMME, encoding="utf-8")
    (root / "rug" / "topic.html").write_text(topic_html, encoding="utf-8")
    (root / "rug" / "table.html").write_text(table, encoding="utf-8")
    return root


def _program(name: str = "Computing Science") -> CandidateProgram:
    return CandidateProgram(
        name=name, field="computer science", degree=DegreeLevel.BACHELOR, url=PROGRAMME_URL
    )


async def _run(
    settings, root: Path, monkeypatch, page: str, program: CandidateProgram | None = None
):
    # QR-1 (on by default) asks only the questions still unanswered (``topics``).
    async def topic_pages(self, candidate, program, out, topics=None):
        return (("english", f"fixture://rug/{page}"),)

    monkeypatch.setattr(WebRequirementsAdapter, "_find_topic_pages", topic_pages)
    candidate = Candidate(
        name="University of Groningen", country="Netherlands", city="Groningen", domain="rug.nl"
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(
            candidate, program or _program(), "fall 2027"
        )


def _ielts(result: AdapterResult, url: str) -> list[object]:
    return [
        c.normalized_value
        for c in result.claims
        if c.claim_type is ClaimType.IELTS_MIN_OVERALL and c.source_url == url
    ]


@pytest.fixture(autouse=True, params=[True, False], ids=["qr1", "no-qr1"])
def question_routing(request, monkeypatch) -> bool:
    """FS-1/FS-2 hold with QR-1 on (the default, topic pages asked per question)
    and off (the pre-QR-1 topic search)."""
    monkeypatch.setattr(web_requirements, "QUESTION_ROUTED_EVIDENCE", request.param)
    return request.param


@pytest.fixture
def scoped(monkeypatch):
    monkeypatch.setattr(web_requirements, "TOPIC_FACULTY_SCOPE", True)


@pytest.fixture
def unscoped(monkeypatch):
    monkeypatch.setattr(web_requirements, "TOPIC_FACULTY_SCOPE", False)


def test_the_rule_is_on_by_default():
    assert web_requirements.TOPIC_FACULTY_SCOPE is True


def test_faculty_readers():
    assert faculty_key("Faculty of Economics & Business") == "economics and business"
    assert page_faculty(FEB) == "economics and business"
    assert page_faculty(NO_FACULTY) is None
    assert programme_faculty(readable_text(PROGRAMME), PROGRAMME) == "science and engineering"
    # A bare value under "Faculty" without "Faculty of <value>" elsewhere is a
    # heading over people, not a faculty.
    staff = "<p>Faculty</p><p>Jane Smith</p>"
    assert programme_faculty(readable_text(staff), staff) is None
    assert [k for k, _ in faculty_blocks(readable_text(TABLE))] == [
        "economics and business",
        "science and engineering",
        "law",
    ]


@pytest.mark.asyncio
async def test_off_another_faculty_page_still_claims(settings, tmp_path, monkeypatch, unscoped):
    result = await _run(settings, _site(tmp_path, FEB), monkeypatch, "topic.html")
    assert _ielts(result, "fixture://rug/topic.html") == [6.0]


@pytest.mark.asyncio
async def test_on_another_faculty_page_claims_nothing(settings, tmp_path, monkeypatch, scoped):
    result = await _run(settings, _site(tmp_path, FEB), monkeypatch, "topic.html")
    assert not [c for c in result.claims if c.source_url == "fixture://rug/topic.html"]
    outcome = next(o for o in result.page_outcomes if o.url == "fixture://rug/topic.html")
    assert outcome.category == "no-pattern-match"
    assert outcome.detail.startswith("FS-1:")
    assert "economics and business" in outcome.detail
    assert "science and engineering" in outcome.detail


@pytest.mark.asyncio
async def test_on_the_programme_faculty_page_is_kept(settings, tmp_path, monkeypatch, scoped):
    result = await _run(settings, _site(tmp_path, FSE), monkeypatch, "topic.html")
    assert _ielts(result, "fixture://rug/topic.html") == [6.0]


@pytest.mark.asyncio
async def test_on_a_page_naming_no_faculty_is_unchanged(settings, tmp_path, monkeypatch, scoped):
    result = await _run(settings, _site(tmp_path, NO_FACULTY), monkeypatch, "topic.html")
    assert _ielts(result, "fixture://rug/topic.html") == [6.0]


@pytest.mark.asyncio
async def test_on_unknown_programme_faculty_is_unchanged(settings, tmp_path, monkeypatch, scoped):
    bare = PROGRAMME.replace("<div><p>Faculty</p><p>Science and Engineering</p></div>", "").replace(
        "Faculty of Science and Engineering students", "Students"
    )
    root = _site(tmp_path, FEB)
    (root / "rug" / "bachelors" / "computing-science.html").write_text(bare, encoding="utf-8")
    result = await _run(settings, root, monkeypatch, "topic.html")
    assert _ielts(result, "fixture://rug/topic.html") == [6.0]


@pytest.mark.asyncio
async def test_off_a_per_faculty_table_gives_its_first_block(
    settings, tmp_path, monkeypatch, unscoped
):
    result = await _run(settings, _site(tmp_path, FEB), monkeypatch, "table.html")
    assert _ielts(result, "fixture://rug/table.html") == [6.5]


@pytest.mark.asyncio
async def test_on_a_per_faculty_table_gives_the_programme_block(
    settings, tmp_path, monkeypatch, scoped
):
    result = await _run(settings, _site(tmp_path, FEB), monkeypatch, "table.html")
    assert _ielts(result, "fixture://rug/table.html") == [7.0]


@pytest.mark.asyncio
async def test_on_a_per_faculty_table_falls_back_to_the_faculty_block(
    settings, tmp_path, monkeypatch, scoped
):
    """Not listed by name, but the programme page names its faculty."""
    table = TABLE.replace("<p>Computing Science</p>", "")
    result = await _run(settings, _site(tmp_path, FEB, table), monkeypatch, "table.html")
    assert _ielts(result, "fixture://rug/table.html") == [7.0]


@pytest.mark.asyncio
async def test_on_a_per_faculty_table_naming_neither_gives_no_ielts(
    settings, tmp_path, monkeypatch, scoped
):
    table = TABLE.replace("<p>Computing Science</p>", "").replace(
        "Faculty of Science and Engineering", "Faculty of Spatial Sciences"
    )
    result = await _run(settings, _site(tmp_path, FEB, table), monkeypatch, "table.html")
    assert _ielts(result, "fixture://rug/table.html") == []


HUB = """<html><head><title>Admission | University of Groningen</title></head><body>
<h1>Admission and application</h1>
<p>International applicants: read the
<a href="fixture://rug/topic.html">English language requirements</a>.</p>
</body></html>"""


@pytest.mark.asyncio
@pytest.mark.parametrize(("on", "expected"), [(False, [6.0]), (True, [])])
async def test_a_lead_from_a_topic_page_is_scoped_too(
    settings, tmp_path, monkeypatch, on, expected
):
    monkeypatch.setattr(web_requirements, "TOPIC_FACULTY_SCOPE", on)
    root = _site(tmp_path, FEB)
    (root / "rug" / "hub.html").write_text(HUB, encoding="utf-8")
    result = await _run(settings, root, monkeypatch, "hub.html")
    assert "fixture://rug/topic.html" in {o.url for o in result.page_outcomes}
    assert _ielts(result, "fixture://rug/topic.html") == expected
