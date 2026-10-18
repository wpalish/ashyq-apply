"""Plan rule PL-1: identity recovery reaches the provider results it was given.

On the 2026-10-18 clean baseline the provider returned the programme page in
five development misses and identity recovery never read it: links followed
from a refused course page spent the checks the provider results share with
them (CTU, IIT Delhi), or the first pass started late, read one or two leads
before the deadline and SB-1b's reserve stayed shut (UiO, UBA). Off, both
paths are exactly as before.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DISCOVERY_DEADLINE_SECONDS,
    MAX_PROGRAM_CANDIDATES_CHECKED,
    RECOVERY_RESERVE_READS,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    StageBudget,
)
from app.adapters.fetching import Fetcher
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html
from tests.test_stage_budgets import DEAD, PROGRAMME, FakeClock, _walker_run

COURSE = "https://uni.edu/courses/introduction-to-computer-science"
MODULES = [
    f"https://uni.edu/programmes/computer-science-module-{i}"
    for i in range(MAX_PROGRAM_CANDIDATES_CHECKED + 2)
]
DETAIL = "https://uni.edu/bsc/computer-science"


def _course_page() -> str:
    links = "".join(
        f"<a href='{url}'>Computer Science module {i}</a>" for i, url in enumerate(MODULES)
    )
    prose = " ".join(
        ["This course introduces algorithms, data structures and programming in Python."] * 8
    )
    return f"<h1>Introduction to Computer Science</h1><p>{prose}</p>{links}"


async def _recover(tmp_path, profile, monkeypatch, *, flag: bool):
    monkeypatch.setattr(live_discovery, "PROVIDER_LEAD_FLOOR", flag)
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    bodies: dict[str, bytes | str] = {COURSE: _course_page(), DETAIL: program_html()}
    for i, url in enumerate(MODULES):
        bodies[url] = f"<h1>Computer Science module {i}</h1><p>Lecture notes.</p>"
    site = StubSite(bodies)
    trace = DiscoveryTrace(institution="U", domain="uni.edu")
    candidates = [
        RankedCandidate(COURSE, "Introduction to Computer Science", 2, "fake"),
        RankedCandidate(DETAIL, "Computer Science", 1, "fake"),
    ]
    pages: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(candidates, pages, trace, profile)
    return pages, trace, site.requested


class TestFollowedLinksHaveTheirOwnChecks:
    @pytest.mark.asyncio
    async def test_off_a_course_pages_links_spend_the_provider_results_checks(
        self, tmp_path, profile, monkeypatch
    ):
        """CTU: four course links took checks 5-8; the programme was the next result."""
        pages, trace, requested = await _recover(tmp_path, profile, monkeypatch, flag=False)
        assert pages == []
        assert DETAIL not in requested
        assert requested == [COURSE, *MODULES[: MAX_PROGRAM_CANDIDATES_CHECKED - 1]]
        assert "search identity recovery: checked 8, confirmed 0" in trace.errors

    @pytest.mark.asyncio
    async def test_on_the_next_provider_result_is_still_read(self, tmp_path, profile, monkeypatch):
        pages, trace, requested = await _recover(tmp_path, profile, monkeypatch, flag=True)
        assert pages == [DETAIL]
        # The order is unchanged: the links still go first, within their own checks.
        assert requested == [COURSE, *MODULES[:MAX_PROGRAM_CANDIDATES_CHECKED], DETAIL]
        assert "search identity recovery: checked 2, confirmed 1, followed links 8" in trace.errors


class TestReservePastTheDeadline:
    def _budget(self, monkeypatch, *, flag: bool) -> tuple[StageBudget, FakeClock]:
        monkeypatch.setattr(live_discovery, "PROVIDER_LEAD_FLOOR", flag)
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget(deadline_seconds=10, read_cap=28)
        budget.enter("recovery")
        budget.note_recovery_read()  # read in time, as UiO's first lead was
        clock.now = 10.0
        assert budget.exhausted()
        return budget, clock

    def test_off_no_reserve_once_recovery_has_read(self, monkeypatch):
        budget, _ = self._budget(monkeypatch, flag=False)
        assert not budget.reserve_open()

    def test_on_the_first_pass_gets_the_reserve_in_reads_in_all(self, monkeypatch):
        budget, _ = self._budget(monkeypatch, flag=True)
        for _ in range(RECOVERY_RESERVE_READS - 1):
            assert budget.reserve_open()
            budget.note_recovery_read()
        assert budget.recovery_reads == RECOVERY_RESERVE_READS
        assert not budget.reserve_open()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flag", [False, True])
    async def test_a_late_first_pass_reads_the_lead_after_the_deadline(
        self, tmp_path, cs_bachelor, monkeypatch, flag
    ):
        """UiO, UBA: one lead read in time, the deadline falls, the page is next."""
        monkeypatch.setattr(live_discovery, "PROVIDER_LEAD_FLOOR", flag)
        candidate, trace, site, provider, _ = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=3.0,
            answers=[DEAD[0], PROGRAMME],
            latency=6.5,
        )
        report = trace.stage_budget
        assert provider is not None and len(provider.sent_at) == 3
        assert provider.sent_at[-1] + 6.5 < DISCOVERY_DEADLINE_SECONDS, "queries in time"
        assert report["stopped_by"] == "deadline"
        assert DEAD[0] in site.requested
        if flag:
            assert site.requested[-1] == PROGRAMME
            assert [program.url for program in candidate.programs] == [PROGRAMME]
        else:
            assert PROGRAMME not in site.requested[site.requested.index(DEAD[0]) :]
            assert candidate.programs == []


@pytest.fixture
def cs_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


def test_the_harness_flag_flips_the_rule():
    source = (Path(__file__).resolve().parents[1] / "evaluation/research/live.py").read_text(
        encoding="utf-8"
    )
    assert '"--provider-lead-floor"' in source
    assert "pl1_module.PROVIDER_LEAD_FLOOR = True" in source
    assert '["--provider-lead-floor"] if args.provider_lead_floor' in source


def test_pl1_is_off_by_default():
    assert live_discovery.PROVIDER_LEAD_FLOOR is False
