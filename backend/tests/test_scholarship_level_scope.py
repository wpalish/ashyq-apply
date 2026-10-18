"""SL-1: a bachelor request reads no other level's funding or deadline page.

Read budget analysis 2026-10-18 §2: for a bachelor request Imperial's funding
walk read societal-engagement "funding" pages four times, then PhD
studentships and a PhD award until the clock ended the case, and its verify
stage read the postgraduate-taught deadlines page through a "deadlines" route
link that only HL-1 guards by URL. Offline: every page is a fixture.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship import web_scholarships
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter, _level_scope_refusal
from app.domain.enums import ClaimType, DegreeLevel

_AWARD = """<html><head><title>{name}</title></head><body>
<h1>{name}</h1>
<p>The {name} covers full tuition for the first year of study.</p>
<p>Eligibility: open to international students holding an offer of admission.</p>
<p>The award is worth GBP 5,000 per year and the deadline is 1 March 2027.</p>
</body></html>"""

_INDEX = """<html><head><title>{title}</title></head><body>
<h1>{title}</h1>
<p>Overview of scholarships available to our students.</p>
<ul>{items}</ul>
</body></html>"""

_PROGRAMME = """<html><head><title>Mathematics BSc</title></head><body>
<h1>Mathematics BSc</h1>
<p>Bachelor of Science in Mathematics, three years, full time.</p>
<ul>
<li><a href="fixture://uni/study/scholarships.html">Scholarships</a></li>
<li><a href="fixture://uni/study/apply/undergraduate/deadlines.html">Application deadlines</a></li>
<li><a href="fixture://uni/study/apply/postgraduate-taught/deadlines.html">Application deadlines</a></li>
</ul>
</body></html>"""

_DEADLINE = """<html><head><title>{title}</title></head><body>
<h1>{title}</h1>
<p>The application deadline is {date}.</p>
</body></html>"""


def _write(root: Path, rel: str, html: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


@pytest.fixture
def site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    _write(
        root,
        "uni/study/scholarships.html",
        _INDEX.format(
            title="Scholarships",
            items=(
                '<li><a href="phd-studentship-in-wireless.html">PhD studentship award</a></li>'
                '<li><a href="ada-lovelace-phd-scholarship.html">Ada Lovelace scholarship</a></li>'
                '<li><a href="masters-scholarship.html">Masters scholarship</a></li>'
                '<li><a href="president-undergraduate-scholarship.html">President award</a></li>'
                '<li><a href="merit-scholarship.html">Merit Scholarship</a></li>'
            ),
        ),
    )
    _write(
        root,
        "uni/be-inspired/societal-engagement/funding.html",
        _INDEX.format(
            title="Societal engagement funding",
            items='<li><a href="seed-fund-award.html">Seed fund award</a></li>',
        ),
    )
    for rel, name in (
        ("uni/study/phd-studentship-in-wireless.html", "PhD Studentship"),
        ("uni/study/ada-lovelace-phd-scholarship.html", "Ada Lovelace PhD Scholarship"),
        ("uni/study/masters-scholarship.html", "Masters Scholarship"),
        ("uni/study/president-undergraduate-scholarship.html", "President Scholarship"),
        ("uni/study/merit-scholarship.html", "Merit Scholarship"),
        ("uni/be-inspired/societal-engagement/seed-fund-award.html", "Seed Fund Award"),
    ):
        _write(root, rel, _AWARD.format(name=name))
    _write(root, "uni/programme.html", _PROGRAMME)
    _write(
        root,
        "uni/study/apply/undergraduate/deadlines.html",
        _DEADLINE.format(title="Undergraduate deadlines", date="14 January 2027"),
    )
    _write(
        root,
        "uni/study/apply/postgraduate-taught/deadlines.html",
        _DEADLINE.format(title="Deadlines", date="30 June 2027"),
    )
    return root


def _program(degree: DegreeLevel = DegreeLevel.BACHELOR) -> CandidateProgram:
    return CandidateProgram(
        name="Mathematics BSc",
        field="mathematics",
        degree=degree,
        url="fixture://uni/programme.html",
    )


async def _funding(site: Path, settings, candidate: Candidate, program: CandidateProgram):
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as f:
        return await WebScholarshipAdapter(f, "2026/27").find(
            candidate, program, None, allow_search=False
        )


def _candidate(**kwargs) -> Candidate:
    return Candidate(name="Test University", country="Testland", city="Test", **kwargs)


def _read(result) -> set[str]:
    return {o.url for o in result.page_outcomes if not o.detail.startswith("SL-1")}


class TestRefusal:
    @pytest.mark.parametrize(
        "url",
        [
            "https://u.ac.uk/study/scholarships-search/a-phd-studentship-in-wireless",
            "https://u.ac.uk/study/scholarships-search/ada-lovelace-phd-scholarship",
            "https://u.ac.uk/study/postgraduate/funding",
            "https://u.ac.uk/study/masters-scholarships",
            "https://u.ac.uk/study/funding/research-degrees",
            "https://u.ac.uk/be-inspired/societal-engagement/funding",
            "https://u.ac.th/en/news-type/awards-honours",
            "https://u.ac.th/research/funding-ora",
        ],
    )
    def test_other_level_and_off_study_funding_is_refused(self, url: str) -> None:
        assert _level_scope_refusal(url, "bachelor")

    @pytest.mark.parametrize(
        "url",
        [
            "https://u.ac.uk/study/fees-and-funding/",
            "https://u.ac.uk/study/fees-and-funding/scholarships-search",
            "https://u.ac.uk/business-school/undergraduate/economics/funding-scholarships",
            "https://u.ac.uk/undergraduate-and-masters-scholarships",
            "https://u.ac.th/en/academics/admissions/scholarships",
            "https://u.ac.uk/study/scholarships-search/advisory-board-20252026.php",
        ],
    )
    def test_bachelor_and_study_funding_is_kept(self, url: str) -> None:
        assert _level_scope_refusal(url, "bachelor") == ""

    def test_only_a_bachelor_request_is_scoped(self) -> None:
        url = "https://u.ac.uk/study/scholarships-search/a-phd-studentship"
        assert _level_scope_refusal(url, "phd") == ""
        assert _level_scope_refusal(url, "master") == ""

    def test_the_rule_is_on_by_default(self) -> None:
        assert web_scholarships.SCHOLARSHIP_LEVEL_SCOPE is True


class TestFundingWalk:
    async def test_on_other_level_awards_are_not_read(self, settings, site, monkeypatch) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", True)
        candidate = _candidate(scholarships_url="fixture://uni/study/scholarships.html")
        awards, result = await _funding(site, settings, candidate, _program())

        assert sorted(a.name for a in awards) == ["Merit Scholarship", "President Scholarship"]
        refused = {o.url for o in result.page_outcomes if o.detail.startswith("SL-1")}
        assert refused == {
            "fixture://uni/study/phd-studentship-in-wireless.html",
            "fixture://uni/study/ada-lovelace-phd-scholarship.html",
            "fixture://uni/study/masters-scholarship.html",
        }
        assert not refused & _read(result)

    async def test_off_every_linked_award_is_read(self, settings, site, monkeypatch) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", False)
        candidate = _candidate(scholarships_url="fixture://uni/study/scholarships.html")
        _awards, result = await _funding(site, settings, candidate, _program())
        assert {
            "fixture://uni/study/phd-studentship-in-wireless.html",
            "fixture://uni/study/ada-lovelace-phd-scholarship.html",
            "fixture://uni/study/masters-scholarship.html",
        } <= _read(result)

    async def test_on_a_master_request_is_unchanged(self, settings, site, monkeypatch) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", True)
        candidate = _candidate(scholarships_url="fixture://uni/study/scholarships.html")
        _awards, result = await _funding(site, settings, candidate, _program(DegreeLevel.MASTER))
        assert not any(o.detail.startswith("SL-1") for o in result.page_outcomes)

    async def test_on_an_off_study_funding_index_falls_back_to_the_programme_page(
        self, settings, site, monkeypatch
    ) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", True)
        candidate = _candidate(
            scholarships_url="fixture://uni/be-inspired/societal-engagement/funding.html"
        )
        awards, result = await _funding(site, settings, candidate, _program())

        read = _read(result)
        assert "fixture://uni/be-inspired/societal-engagement/seed-fund-award.html" not in read
        assert "fixture://uni/programme.html" in read
        assert "Seed Fund Award" not in {a.name for a in awards}

    async def test_on_the_programme_and_admissions_pages_are_never_refused(
        self, settings, site, monkeypatch
    ) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", True)
        program = CandidateProgram(
            name="Funding",
            field="mathematics",
            degree=DegreeLevel.BACHELOR,
            url="fixture://uni/be-inspired/societal-engagement/funding.html",
        )
        _awards, result = await _funding(site, settings, _candidate(), program)
        assert "fixture://uni/be-inspired/societal-engagement/funding.html" in _read(result)


async def _verify(settings, root: Path):
    candidate = _candidate(domain="uni.ac.uk")
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, _program(), "fall 2027")


class TestDeadlineRouteLinks:
    PGT = "fixture://uni/study/apply/postgraduate-taught/deadlines.html"

    async def test_on_the_other_level_deadline_page_is_not_followed(
        self, settings, site, monkeypatch
    ) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", True)
        monkeypatch.setattr(web_requirements, "HUB_LEADS", False)
        result = await _verify(settings, site)
        read = {o.url for o in result.page_outcomes}
        assert self.PGT not in read
        deadlines = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
        assert [str(c.normalized_value) for c in deadlines] == ["2027-01-14"]

    async def test_off_the_route_link_reads_it(self, settings, site, monkeypatch) -> None:
        monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_LEVEL_SCOPE", False)
        monkeypatch.setattr(web_requirements, "HUB_LEADS", False)
        result = await _verify(settings, site)
        assert self.PGT in {o.url for o in result.page_outcomes}


BACKEND = Path(__file__).resolve().parents[1]


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--scholarship-level-scope" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "sl1_module.SCHOLARSHIP_LEVEL_SCOPE = True" in source
    assert '["--scholarship-level-scope"]' in source
