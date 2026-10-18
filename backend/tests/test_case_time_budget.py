"""TB-1: one institution's case clock, shared by discovery, verify, costs and funding.

DoD target 5 allows 120 s per university, and a case the harness ends at
115 s counts as over budget (owner decision 2026-10-18). The cases still over
were clock kills with few requests: UBC (you.ubc.ca answers in 5-17 s) and
UNSW (``Crawl-delay: 10``). Offline: HTTP on ``httpx.MockTransport``, DNS on a
stub resolver, and the fetcher's clock and sleep replaced by a fake clock that
the mock hosts advance by their latency, so a 110 s case runs in milliseconds.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters import fetching
from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import (
    CaseTimeBudget,
    Fetcher,
    case_seconds_left,
    charging,
    reading_as,
    time_floor,
)
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.enums import DegreeLevel, FetchOutcome

UNSW = "www.unsw.edu.au"
UBC = "you.ubc.ca"
OTHER = "www.other.ac.uk"
PAGE = "<html><body>" + "Admissions. " * 60 + "</body></html>"


def _allow_all(url: str, **_kwargs: Any) -> Any:
    from app.adapters.network_policy import check_url as real

    def resolve(host: str, port: int, **_kw: Any) -> list[Any]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    return real(url, resolver=resolve)


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _allow_all)


class FakeClock:
    """Monotonic seconds that only sleeps and the mock hosts' latency advance."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds

    async def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.0)
        await asyncio.sleep(0)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(fetching, "_clock", fake)
    monkeypatch.setattr(fetching, "_sleep", fake.sleep)
    return fake


@pytest.fixture
def tb_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetching, "CASE_TIME_BUDGET", True)


@pytest.fixture
def tb_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetching, "CASE_TIME_BUDGET", False)


class Host:
    """A mock university host: a latency per read, an optional Crawl-delay.

    Records the fake-clock moment each page request reached it.
    """

    def __init__(
        self,
        clock: FakeClock,
        latency: float,
        crawl_delay: int | None = None,
        pages: dict[str, str] | None = None,
    ) -> None:
        self.clock = clock
        self.latency = latency
        self.crawl_delay = crawl_delay
        self.pages = pages or {}
        self.hits: list[tuple[float, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            body = "User-agent: *\nDisallow:\n"
            if self.crawl_delay is not None:
                body += f"Crawl-delay: {self.crawl_delay}\n"
            return httpx.Response(200, headers={"content-type": "text/plain"}, text=body)
        self.hits.append((self.clock.now, path))
        self.clock.advance(self.latency)
        if path.startswith("/hop/"):
            return httpx.Response(301, headers={"location": "/" + path.removeprefix("/hop/")})
        body = self.pages.get(path, PAGE)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=body)


class _Opened:
    """``async with`` a fetcher whose client is the mock host (installed after entry)."""

    def __init__(self, fetcher: Fetcher, handler: Callable[..., Any]) -> None:
        self.fetcher = fetcher
        self.handler = handler

    async def __aenter__(self) -> Fetcher:
        await self.fetcher.__aenter__()
        assert self.fetcher._client is not None
        await self.fetcher._client.aclose()
        self.fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(self.handler), follow_redirects=False
        )
        return self.fetcher

    async def __aexit__(self, *exc: object) -> None:
        await self.fetcher.__aexit__(*exc)


def _fetcher(tmp_path: Path, handler: Callable[..., Any], *, robots: bool = True) -> _Opened:
    return _Opened(Fetcher(tmp_path / "cache", delay_seconds=1.5, respect_robots=robots), handler)


def _elapsed(fetcher: Fetcher, host: str) -> float:
    return fetcher.timer_for(host).elapsed()


class TestBudget:
    def test_the_defaults(self) -> None:
        assert fetching.CASE_TIME_BUDGET is False
        assert fetching.CASE_TIME_SECONDS == 110.0
        assert fetching.VERIFY_RESERVE_SECONDS == 40.0
        assert fetching.CORE_RESERVE_SECONDS == 20.0

    def test_floors_refuse_in_the_stated_order(self) -> None:
        order = ["sitemap", "walker", "discovery", "question_extra", "award", "core"]
        floors = [time_floor(kind, 40.0, 20.0) for kind in order]
        assert floors == sorted(floors, reverse=True)
        assert time_floor("discovery", 40.0, 20.0) == 40.0
        assert time_floor("question_extra", 40.0, 20.0) == 20.0
        assert time_floor("core", 40.0, 20.0) == 0.0

    def test_a_core_read_starts_while_time_remains_after_its_wait(self) -> None:
        timer = CaseTimeBudget("uni", limit=110.0, accrued=104.0)
        # 6 s left: a core read waiting 4 s for its crawl delay still starts,
        assert timer.admit("core", wait=4.0, expected=10.0) == ""
        # but not one whose wait would leave under a second to read in.
        assert "crawl delay" in timer.admit("core", wait=5.5, expected=0.5)
        # An award page must be expected to end in time; an extra page must
        # leave the core reserve; a discovery read the verify reserve.
        assert timer.admit("award", wait=0.0, expected=5.0) == ""
        assert timer.admit("award", wait=2.0, expected=5.0)
        timer.accrued = 80.0
        assert timer.admit("question_extra", wait=0.0, expected=10.0) == ""
        assert "must leave 20 s" in timer.admit("question_extra", wait=1.0, expected=10.0)
        assert "must leave 40 s" in timer.admit("discovery", wait=0.0, expected=1.0)

    def test_the_clock_runs_for_the_latest_institution_only(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        """Production interleaves universities: each gets its own seconds."""
        fetcher = Fetcher(tmp_path / "cache")
        with fetcher.timing(UNSW, "discovery"):
            clock.advance(50)
        with fetcher.timing(OTHER, "discovery"):
            clock.advance(30)
        # The work between two stages is still the latest institution's.
        clock.advance(5)
        with fetcher.timing(UNSW, "verify"):
            clock.advance(10)
        assert _elapsed(fetcher, UNSW) == 60.0
        assert _elapsed(fetcher, OTHER) == 35.0
        assert fetcher.timer_for("unsw.edu.au") is fetcher.timer_for(UNSW)
        by_phase = fetcher.timer_for(UNSW).as_dict()["seconds_by_phase"]
        assert by_phase == {"discovery": 50.0, "verify": 10.0}


class TestOff:
    async def test_off_nothing_is_timed_and_reads_are_unchanged(
        self, tmp_path: Path, clock: FakeClock, tb_off: None
    ) -> None:
        host = Host(clock, latency=30.0)
        async with _fetcher(tmp_path, host, robots=False) as fetcher:
            with charging(fetcher, UBC, "verify"), reading_as("question_extra"):
                assert case_seconds_left() is None
                results = [await fetcher.get(f"https://{UBC}/p{i}") for i in range(6)]
        assert all(r.outcome is FetchOutcome.OK for r in results)
        assert fetcher.timers == {}
        assert fetcher._host_seconds == {}
        assert len(host.hits) == 6

    async def test_on_without_a_scope_nothing_is_refused(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        host = Host(clock, latency=60.0)
        async with _fetcher(tmp_path, host, robots=False) as fetcher:
            results = [await fetcher.get(f"https://{UBC}/p{i}") for i in range(3)]
        assert all(r.outcome is FetchOutcome.OK for r in results)
        assert fetcher.timers == {}


class TestUnswShaped:
    """``Crawl-delay: 10``: every read of the host costs about ten seconds of waiting."""

    async def test_the_crawl_delay_is_never_shortened_and_the_case_ends_in_time(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        host = Host(clock, latency=0.8, crawl_delay=10)
        async with _fetcher(tmp_path, host) as fetcher:
            base = f"https://{UNSW}"
            with charging(fetcher, UNSW, "discovery"):
                for i in range(4):
                    await fetcher.get(f"{base}/study/d{i}")
                clock.advance(10)  # queries, parsing
            with charging(fetcher, UNSW, "verify"):
                with reading_as("core"):
                    admissions = await fetcher.get(f"{base}/study/how-to-apply")
                extras = []
                for i in range(6):
                    with reading_as("question_extra"):
                        extras.append(await fetcher.get(f"{base}/study/extra-{i}"))
                with reading_as("core"):
                    english = await fetcher.get(f"{base}/study/english")
                    fees = await fetcher.get(f"{base}/study/fees")
                with reading_as("question_extra"):
                    research_fees = await fetcher.get(f"{base}/research/hdr/fees")
            with charging(fetcher, UNSW, "funding"), reading_as("core"):
                scholarships = await fetcher.get(f"{base}/study/international-scholarships")
        timer = fetcher.timer_for(UNSW)
        moments = [moment for moment, _path in host.hits]
        # Ten seconds or more between any two requests to the host: honoured, never shortened.
        assert all(b - a >= 10.0 - 1e-9 for a, b in pairwise(moments))
        # Core reads are read; the extra pages stop where they would eat the
        # cost and scholarship reserve; the scholarship index, whose wait
        # would end past the deadline, is refused instead of waited on.
        assert admissions.ok and english.ok and fees.ok
        assert [r.ok for r in extras] == [True] * 4 + [False] * 2
        assert all(r.outcome is FetchOutcome.BLOCKED and "TB-1" in r.error for r in extras[4:])
        assert research_fees.outcome is FetchOutcome.BLOCKED
        assert scholarships.outcome is FetchOutcome.BLOCKED
        assert "crawl delay" in scholarships.error
        # Every read ended by the case deadline; nothing was cut mid-read.
        assert timer.elapsed() <= fetching.CASE_TIME_SECONDS
        assert timer.cut == 0
        kinds = [r["kind"] for r in timer.refusals]
        assert kinds == ["question_extra"] * 3 + ["core"]
        assert timer.first_refusal_at is not None and timer.first_refusal_at < 90

    async def test_a_redirect_hop_does_not_wait_past_the_deadline(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        host = Host(clock, latency=0.5, crawl_delay=10)
        async with _fetcher(tmp_path, host) as fetcher:
            timer = fetcher.timer_for(UNSW)
            with charging(fetcher, UNSW, "verify"), reading_as("core"):
                timer.accrued = 101.0
                result = await fetcher.get(f"https://{UNSW}/hop/study/fees")
        # The first hop was read at 101 s and answered at 101.5 s; the second
        # would wait 9.5 s for the crawl delay with 8.5 s of the case left:
        # refused, not waited on.
        assert result.outcome is FetchOutcome.BLOCKED
        assert "crawl delay would end past the case deadline" in result.error
        assert [path for _moment, path in host.hits] == ["/hop/study/fees"]
        assert timer.elapsed() < fetching.CASE_TIME_SECONDS


class TestUbcShaped:
    """No Crawl-delay, but every read of the host takes seven seconds."""

    async def test_reads_are_predicted_from_the_host_and_core_reads_come_first(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        host = Host(clock, latency=7.0)
        async with _fetcher(tmp_path, host) as fetcher:
            base = f"https://{UBC}"
            discovery = []
            with charging(fetcher, UBC, "discovery"):
                for i in range(12):
                    discovery.append(await fetcher.get(f"{base}/programs/p{i}"))
            with charging(fetcher, UBC, "verify"):
                with reading_as("core"):
                    programme = await fetcher.get(f"{base}/programs/computer-science")
                    admissions = await fetcher.get(f"{base}/applying-ubc")
                with reading_as("question_extra"):
                    extra = await fetcher.get(f"{base}/applying-ubc/how-to-apply")
                with reading_as("core"):
                    deadlines = await fetcher.get(f"{base}/applying-ubc/dates-deadlines")
                    tuition = await fetcher.get(f"{base}/financial-planning/tuition-fees")
            with charging(fetcher, UBC, "funding"):
                with reading_as("core"):
                    index = await fetcher.get(f"{base}/financial-planning/scholarships")
                with reading_as("award"):
                    award = await fetcher.get(f"{base}/financial-planning/award-1")
        timer = fetcher.timer_for(UBC)
        # Discovery reads stop where one more would eat the verify reserve:
        # the tenth page ends at 70 s, an eleventh would end at 77 s > 70 s.
        assert [r.ok for r in discovery] == [True] * 10 + [False] * 2
        assert programme.ok and admissions.ok and deadlines.ok and tuition.ok
        # One extra page at 84 s would end at 91 s, past the 20 s core reserve.
        assert extra.outcome is FetchOutcome.BLOCKED
        # The scholarship index is read; the award page after it would end past 110 s.
        assert index.ok
        assert award.outcome is FetchOutcome.BLOCKED
        assert timer.elapsed() <= fetching.CASE_TIME_SECONDS
        assert fetcher._expected_seconds(f"{base}/x") == pytest.approx(7.0)
        recorded = timer.as_dict()
        assert set(recorded["seconds_by_phase"]) == {"discovery", "verify", "funding"}
        assert [r["kind"] for r in recorded["refusals"]] == ["discovery"] * 2 + [
            "question_extra",
            "award",
        ]

    async def test_funding_files_the_index_and_refuses_award_pages_in_time(
        self, tmp_path: Path, clock: FakeClock, tb_on: None
    ) -> None:
        index = (
            "<html><head><title>Scholarships</title></head><body><h1>Scholarships</h1>"
            "<p>Overview of scholarships available to our students.</p><ul>"
            + "".join(
                f'<li><a href="/study/scholarships/award-{i}">Award {i} scholarship</a></li>'
                for i in range(4)
            )
            + "</ul></body></html>"
        )
        host = Host(clock, latency=7.0, pages={"/study/scholarships": index})
        candidate = Candidate(
            name="Uni",
            country="Testland",
            city="T",
            domain=UBC,
            scholarships_url=f"https://{UBC}/study/scholarships",
        )
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)
        async with _fetcher(tmp_path, host, robots=False) as fetcher:
            timer = fetcher.timer_for(UBC)
            timer.accrued = 95.0
            with charging(fetcher, UBC, "funding"):
                _awards, result = await WebScholarshipAdapter(fetcher, "2026/27").find(
                    candidate, program, None, allow_search=False
                )
        # The index (95-102 s) and the first award page (a core read, 102-109 s)
        # are read; the other award pages would end past 110 s.
        assert [path for _moment, path in host.hits][:2] == [
            "/study/scholarships",
            "/study/scholarships/award-0",
        ]
        assert len(host.hits) == 2
        assert timer.elapsed() <= fetching.CASE_TIME_SECONDS
        assert [r["kind"] for r in timer.refusals] == ["award"] * 3
        assert any("TB-1" in o.detail for o in result.page_outcomes)


class TestCut:
    async def test_a_read_still_running_at_the_deadline_is_cut_and_the_host_kept(
        self, tmp_path: Path, tb_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Real clock: a core read admitted with 1.5 s left meets a host that
        needs 5 s. It ends at the deadline, and the host is not marked stalled."""
        monkeypatch.setattr(fetching, "CASE_TIME_SECONDS", 2.0)

        async def slow(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(5.0)
            return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGE)

        loop = asyncio.get_running_loop()
        async with _fetcher(tmp_path, slow, robots=False) as fetcher:
            timer = fetcher.timer_for(UBC)
            timer.accrued = 0.5
            began = loop.time()
            with charging(fetcher, UBC, "verify"), reading_as("core"):
                result = await fetcher.get(f"https://{UBC}/programs/computer-science")
            took = loop.time() - began
        assert result.outcome is FetchOutcome.BLOCKED
        assert "cut at the case deadline" in result.error
        assert 1.0 < took < 3.0
        assert timer.cut == 1
        assert UBC not in fetcher._stalled_hosts
        assert UBC not in fetcher._host_seconds


class TestTraceSearchAndHarness:
    def test_the_trace_carries_the_clock_only_when_there_is_one(self, clock: FakeClock) -> None:
        trace = DiscoveryTrace(institution="Uni", domain=UBC)
        assert "case_time" not in trace.as_dict()
        timer = CaseTimeBudget("ubc.ca")
        timer.refuse(f"https://{UBC}/x", "question_extra", "2.0 of 110 s left")
        trace.case_time = timer
        recorded = trace.as_dict()["case_time"]
        assert recorded["limit_seconds"] == 110.0
        assert recorded["refusals"][0]["reason"] == "2.0 of 110 s left"

    async def test_the_award_query_is_not_sent_without_time_to_read_its_pages(
        self, tmp_path: Path, clock: FakeClock, tb_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sent: list[str] = []

        class Provider:
            name = "stub"

            async def search(self, query: str, **_kwargs: Any) -> Any:
                sent.append(query)
                raise AssertionError("no query may be sent")

        import app.adapters.search as search_pkg

        monkeypatch.setattr(search_pkg, "get_search_provider", lambda: Provider())
        candidate = Candidate(name="Uni", country="Testland", city="T", domain=UNSW)
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)
        out = AdapterResult()
        fetcher = Fetcher(tmp_path / "cache")
        fetcher.timer_for(UNSW).accrued = 106.0
        adapter = WebScholarshipAdapter(fetcher, "2026/27")
        with fetcher.timing(UNSW, "funding"):
            assert case_seconds_left() == pytest.approx(4.0)
            found = await adapter._search_awards(candidate, program, out)
        assert found == ()
        assert sent == []
        assert any("case time budget" in e for e in out.errors)


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
    assert "--case-time-budget" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "tb1_module.CASE_TIME_BUDGET = True" in source
    assert '*(["--case-time-budget"] if args.case_time_budget else [])' in source
