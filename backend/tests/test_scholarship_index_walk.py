"""A funding index is discovery, not award proof (Phase 3 §8).

The adapter used to read one index page and throw away everything behind it:
a link that classified as another index - an international funding page, a
faculty funding page - was fetched, rejected and dropped, and the awards it
named were never seen. These tests pin the walk that reads it instead, and
the two rules that keep the walk from inventing anything: an index never
becomes a scholarship, and a page is fetched once.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.enums import DegreeLevel

_AWARD = """<html><head><title>{name}</title></head><body>
<h1>{name}</h1>
<p>The {name} covers full tuition for the first year of study.</p>
<p>Eligibility: open to international students holding an offer of admission.</p>
<p>The award is worth EUR 12,000 per year and the deadline is 1 March 2027.</p>
</body></html>"""

_INDEX = """<html><head><title>{title}</title></head><body>
<h1>{title}</h1>
<p>Overview of scholarships available to our students.</p>
<ul>{items}</ul>
</body></html>"""


def _write(root: Path, rel: str, html: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


@pytest.fixture
def site(tmp_path: Path) -> Path:
    """A university whose awards sit one index deeper than the main one."""
    root = tmp_path / "site"
    _write(
        root,
        "uni/scholarships.html",
        _INDEX.format(
            title="Scholarships",
            items=(
                '<li><a href="international-funding.html">International funding</a></li>'
                '<li><a href="merit-scholarship.html">Merit Scholarship</a></li>'
            ),
        ),
    )
    _write(
        root,
        "uni/international-funding.html",
        _INDEX.format(
            title="Scholarships for international students",
            items=(
                '<li><a href="global-scholarship.html">Global Scholarship</a></li>'
                '<li><a href="country-grant.html">Country Grant</a></li>'
            ),
        ),
    )
    for rel, name in (
        ("uni/merit-scholarship.html", "Merit Scholarship"),
        ("uni/global-scholarship.html", "Global Scholarship"),
        ("uni/country-grant.html", "Country Grant"),
    ):
        _write(root, rel, _AWARD.format(name=name))
    return root


def _candidate(**kwargs) -> Candidate:
    return Candidate(name="Test University", country="Testland", city="Test", **kwargs)


async def _run(site: Path, settings, candidate: Candidate, program: CandidateProgram):
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as f:
        return await WebScholarshipAdapter(f, "2026/27").find(candidate, program, None)


class TestAnIndexBehindAnIndex:
    @pytest.mark.asyncio
    async def test_the_awards_it_links_are_read(self, settings, site):
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)

        awards, result = await _run(site, settings, candidate, program)

        assert sorted(a.name for a in awards) == [
            "Country Grant",
            "Global Scholarship",
            "Merit Scholarship",
        ], result.errors

    @pytest.mark.asyncio
    async def test_the_index_itself_never_becomes_a_scholarship(self, settings, site):
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)

        awards, _ = await _run(site, settings, candidate, program)

        names = {a.name for a in awards}
        assert "Scholarships" not in names
        assert "Scholarships for international students" not in names
        assert all("fixture://uni/international-funding.html" not in a.source_urls for a in awards)

    @pytest.mark.asyncio
    async def test_no_page_is_fetched_twice(self, settings, site):
        """The two indexes link the same awards in a real site as often as not."""
        _write(
            site,
            "uni/international-funding.html",
            _INDEX.format(
                title="Scholarships for international students",
                items=(
                    '<li><a href="merit-scholarship.html">Merit Scholarship</a></li>'
                    '<li><a href="scholarships.html">All scholarships</a></li>'
                ),
            ),
        )
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)

        awards, result = await _run(site, settings, candidate, program)

        assert [a.name for a in awards] == ["Merit Scholarship"]
        assert result.pages_checked == 3


class TestTheProgrammePageIsAFallbackOnly:
    @pytest.mark.asyncio
    async def test_it_is_read_when_no_scholarship_page_is_known(self, settings, site):
        _write(
            site,
            "uni/programme.html",
            _INDEX.format(
                title="Scholarships",
                items='<li><a href="merit-scholarship.html">Merit Scholarship</a></li>',
            ),
        )
        candidate = _candidate()
        program = CandidateProgram(
            name="P", field="cs", degree=DegreeLevel.BACHELOR, url="fixture://uni/programme.html"
        )

        awards, result = await _run(site, settings, candidate, program)

        assert [a.name for a in awards] == ["Merit Scholarship"]
        assert any("read as a funding index" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_a_programme_page_is_not_itself_an_award(self, settings, site):
        _write(
            site,
            "uni/programme.html",
            _AWARD.format(name="Bachelor Scholarship Programme"),
        )
        candidate = _candidate()
        program = CandidateProgram(
            name="P", field="cs", degree=DegreeLevel.BACHELOR, url="fixture://uni/programme.html"
        )

        awards, _ = await _run(site, settings, candidate, program)

        assert awards == []

    @pytest.mark.asyncio
    async def test_it_is_not_fetched_when_the_index_named_an_award(self, settings, site):
        _write(site, "uni/programme.html", _AWARD.format(name="Never Read"))
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        program = CandidateProgram(
            name="P", field="cs", degree=DegreeLevel.BACHELOR, url="fixture://uni/programme.html"
        )

        awards, _ = await _run(site, settings, candidate, program)

        assert "Never Read" not in {a.name for a in awards}


class TestTheBudgetIsShared:
    @pytest.mark.asyncio
    async def test_three_index_pages_is_the_limit(self, settings, tmp_path):
        """A chain of indexes is a site map, not a funding route."""
        root = tmp_path / "chain"
        for i in range(6):
            nxt = f'<li><a href="level{i + 1}.html">More funding</a></li>'
            _write(root, f"uni/level{i}.html", _INDEX.format(title="Scholarships", items=nxt))
        _write(root, "uni/level6.html", _AWARD.format(name="Deep Award"))
        candidate = _candidate(scholarships_url="fixture://uni/level0.html")
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)

        awards, result = await _run(root, settings, candidate, program)

        assert awards == []
        assert result.pages_checked <= 4


class TestAPageIsReadOncePerRun:
    """EXTRA-8: funding runs once per programme, so a university with two
    programmes used to read its scholarship index and every award page twice.

    Every budget-killed case in live run 35697105238 died inside this adapter,
    so the second read is not free: it is half the run's page budget.
    """

    @pytest.mark.asyncio
    async def test_the_second_programme_re_reads_nothing(self, settings, site):
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        first = CandidateProgram(name="BSc CS", field="cs", degree=DegreeLevel.BACHELOR)
        second = CandidateProgram(name="BSc Maths", field="maths", degree=DegreeLevel.BACHELOR)

        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as fetcher:
            adapter = WebScholarshipAdapter(fetcher, "2026/27")
            awards_one, result_one = await adapter.find(candidate, first, None)
            awards_two, result_two = await adapter.find(candidate, second, None)

        assert [a.name for a in awards_one] == [a.name for a in awards_two], (
            "the same university funds the same awards whichever programme asks"
        )
        assert result_one.pages_checked > 0
        assert result_two.pages_checked == 0, "nothing new was read for the second programme"

    @pytest.mark.asyncio
    async def test_the_claims_still_belong_to_their_own_programme(self, settings, site):
        """The memo holds pages, never claims: a claim names its programme."""
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        first = CandidateProgram(name="BSc CS", field="cs", degree=DegreeLevel.BACHELOR)
        second = CandidateProgram(name="BSc Maths", field="maths", degree=DegreeLevel.BACHELOR)

        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as fetcher:
            adapter = WebScholarshipAdapter(fetcher, "2026/27")
            _, result_one = await adapter.find(candidate, first, None)
            _, result_two = await adapter.find(candidate, second, None)

        assert {c.program for c in result_one.claims} == {"BSc CS"}
        assert {c.program for c in result_two.claims} == {"BSc Maths"}
        assert len(result_two.claims) == len(result_one.claims), "same pages, same claims"

    @pytest.mark.asyncio
    async def test_a_page_that_failed_is_tried_again(self, settings, tmp_path):
        """A failure is not an answer, so it is not remembered as one."""
        root = tmp_path / "flaky"
        candidate = _candidate(scholarships_url="fixture://uni/scholarships.html")
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)

        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as fetcher:
            adapter = WebScholarshipAdapter(fetcher, "2026/27")
            _, first = await adapter.find(candidate, program, None)
            assert first.pages_failed == 1
            _write(
                root,
                "uni/scholarships.html",
                _INDEX.format(
                    title="Scholarships",
                    items='<li><a href="merit-scholarship.html">Merit Scholarship</a></li>',
                ),
            )
            _write(root, "uni/merit-scholarship.html", _AWARD.format(name="Merit Scholarship"))
            awards, second = await adapter.find(candidate, program, None)

        assert [a.name for a in awards] == ["Merit Scholarship"]

    @pytest.mark.asyncio
    async def test_the_memo_does_not_hold_every_university_s_pages(self, settings, site):
        """It exists to stop the second programme re-reading the first one's
        pages. Holding every university's HTML for a whole run would be tens
        of megabytes of dead weight for no gain, so the last one is dropped.
        """
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)
        first = _candidate(scholarships_url="fixture://uni/scholarships.html")
        second = Candidate(
            name="Other University",
            country="Testland",
            city="Test",
            scholarships_url="fixture://uni/scholarships.html",
        )

        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as fetcher:
            adapter = WebScholarshipAdapter(fetcher, "2026/27")
            await adapter.find(first, program, None)
            held_after_first = len(adapter._pages)
            await adapter.find(second, program, None)
            held_after_second = len(adapter._pages)

        assert held_after_first > 0
        assert held_after_second == held_after_first, "one university's pages, not two"

    @pytest.mark.asyncio
    async def test_returning_to_a_university_reads_it_again(self, settings, site):
        """The cost of bounding the memo, stated rather than hidden: rows are
        not guaranteed to be grouped by university."""
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)
        first = _candidate(scholarships_url="fixture://uni/scholarships.html")
        other = Candidate(
            name="Other University",
            country="Testland",
            city="Test",
            scholarships_url="fixture://uni/scholarships.html",
        )

        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=site) as fetcher:
            adapter = WebScholarshipAdapter(fetcher, "2026/27")
            await adapter.find(first, program, None)
            await adapter.find(other, program, None)
            _, back_again = await adapter.find(first, program, None)

        assert back_again.pages_checked > 0
