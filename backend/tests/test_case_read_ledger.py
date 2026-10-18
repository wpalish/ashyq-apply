"""RL-1: one institution's wire requests are metered where the scorecard counts them.

DoD target 5 (owner decision 2026-10-18): a read is every HTTP request to a
university site, which the benchmark counts by patching
``fetching._pinned_request``. Before RL-1 no cap in the code counted that
number (read budget analysis 2026-10-18 §0). Offline: HTTP runs on
``httpx.MockTransport`` and DNS on a stub resolver; requests are counted with
the harness's own patch.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters import fetching
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import (
    CaseReadLedger,
    CaseReadSpent,
    Fetcher,
    charging,
    read_floor,
    reading_as,
)
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.enums import DegreeLevel, FetchOutcome

HOST = "www.uni.ac.uk"
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


@pytest.fixture
def ledger_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetching, "CASE_READ_LEDGER", True)


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every wire request, counted exactly as evaluation/research/live.py counts them."""
    sent: list[str] = []
    original = fetching._pinned_request

    def counted_request(*args: Any, **kwargs: Any) -> httpx.Request:
        sent.append(args[1].url)
        return original(*args, **kwargs)

    monkeypatch.setattr(fetching, "_pinned_request", counted_request)
    return sent


_FLAKY: list[str] = []


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\n")
    if path.startswith("/hop/"):
        rest = path.removeprefix("/hop/")
        hops, _, target = rest.partition("/")
        location = f"/hop/{int(hops) - 1}/{target}" if int(hops) > 1 else f"/{target}"
        return httpx.Response(301, headers={"location": location})
    if path.startswith("/flaky"):
        # 503 on the first attempt only: the retry is a second wire request.
        _FLAKY.append(path)
        if len(_FLAKY) == 1:
            return httpx.Response(503)
    return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGE)


def _fetcher(tmp_path: Any, *, robots: bool = True) -> Fetcher:
    return Fetcher(tmp_path / "cache", delay_seconds=0.0, respect_robots=robots)


def _install(fetcher: Fetcher) -> None:
    fetcher._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_handler), follow_redirects=False
    )


class TestLedger:
    def test_floors_refuse_in_the_stated_order(self) -> None:
        reserve = 16
        order = ["sitemap", "walker", "discovery", "award", "question_extra", "core"]
        floors = [read_floor(kind, reserve) for kind in order]
        assert floors == sorted(floors, reverse=True)
        assert read_floor("discovery", reserve) == reserve
        assert read_floor("core", reserve) == 0

    def test_core_reads_are_admitted_until_the_cap(self) -> None:
        ledger = CaseReadLedger("uni", cap=60, reserve=16, phase="verify")
        ledger.spent = 59
        assert ledger.admit(1, "core") == ""
        assert ledger.admit(2, "core")
        assert ledger.admit(1, "question_extra")
        ledger.spent = 44
        assert ledger.admit(1, "discovery")
        assert ledger.admit(1, "award") == ""

    def test_the_cap_is_hard(self) -> None:
        ledger = CaseReadLedger("uni", cap=2, reserve=0)
        ledger.charge("https://u/a")
        ledger.charge("https://u/b")
        with pytest.raises(CaseReadSpent):
            ledger.charge("https://u/c")
        assert ledger.spent == 2

    def test_the_defaults(self) -> None:
        assert fetching.CASE_READ_LEDGER is False
        assert fetching.CASE_READ_CAP == 60
        assert fetching.VERIFY_RESERVE_READS == 16


class TestCharging:
    async def test_off_nothing_is_metered(self, tmp_path: Any, wire: list[str]) -> None:
        async with _fetcher(tmp_path) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "verify") as ledger:
                await fetcher.get(f"https://{HOST}/a")
        assert ledger is None
        assert fetcher.ledgers == {}
        assert len(wire) == 2

    async def test_on_every_wire_request_is_charged_as_the_harness_counts_it(
        self, tmp_path: Any, wire: list[str], ledger_on: None
    ) -> None:
        async with _fetcher(tmp_path) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "verify") as ledger:
                await fetcher.get(f"https://{HOST}/hop/2/page")  # robots + 3 hops
                _FLAKY.clear()
                await fetcher.get(f"https://{HOST}/flaky")  # a 503, then a retry
                await fetcher.get(f"https://{HOST}/hop/2/page")  # a cache hit: free
        assert ledger is not None
        assert ledger.spent == len(wire) == 1 + 3 + 2
        assert ledger.by_phase == {"verify": 6}

    async def test_on_the_cap_stops_a_redirect_chain_and_nothing_crosses_it(
        self, tmp_path: Any, wire: list[str], ledger_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetching, "CASE_READ_CAP", 4)
        async with _fetcher(tmp_path) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "verify") as ledger, reading_as("core"):
                first = await fetcher.get(f"https://{HOST}/hop/5/page")
                second = await fetcher.get(f"https://{HOST}/other")
        assert ledger is not None
        assert len(wire) == 4 and ledger.spent == 4
        assert first.outcome is FetchOutcome.BLOCKED
        assert "cap" in first.error
        assert second.outcome is FetchOutcome.BLOCKED
        reasons = [r["reason"] for r in ledger.refusals]
        assert reasons[0] == "the cap was reached during the read"
        assert ledger.refused == 2

    async def test_on_a_short_ledger_refuses_sitemaps_before_core_reads(
        self, tmp_path: Any, wire: list[str], ledger_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with _fetcher(tmp_path, robots=False) as fetcher:
            _install(fetcher)
            ledger = fetcher.ledger_for(HOST)
            ledger.spent = 60 - 21
            with charging(fetcher, HOST, "discovery"):
                with reading_as("sitemap"):
                    sitemap = await fetcher.get(f"https://{HOST}/sitemap.xml")
                with reading_as("walker"):
                    walker = await fetcher.get(f"https://{HOST}/catalogue")
                other = await fetcher.get(f"https://{HOST}/navigation")
            with charging(fetcher, HOST, "verify"), reading_as("core"):
                core = await fetcher.get(f"https://{HOST}/programme")
        assert sitemap.outcome is FetchOutcome.BLOCKED
        assert "RL-1" in sitemap.error
        assert walker.outcome is FetchOutcome.OK
        assert other.outcome is FetchOutcome.OK
        assert core.outcome is FetchOutcome.OK
        assert [(r["kind"], r["phase"]) for r in ledger.refusals] == [("sitemap", "discovery")]
        assert ledger.spent == 42 and len(wire) == 3

    async def test_on_discovery_leaves_the_verify_reserve(
        self, tmp_path: Any, wire: list[str], ledger_on: None
    ) -> None:
        async with _fetcher(tmp_path, robots=False) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "discovery") as ledger:
                results = [await fetcher.get(f"https://{HOST}/d{i}") for i in range(50)]
        assert ledger is not None
        assert ledger.spent == 60 - fetching.VERIFY_RESERVE_READS
        assert sum(r.outcome is FetchOutcome.OK for r in results) == ledger.spent
        assert len(wire) == ledger.spent

    async def test_on_robots_counts_toward_the_admission(
        self, tmp_path: Any, wire: list[str], ledger_on: None
    ) -> None:
        async with _fetcher(tmp_path) as fetcher:
            _install(fetcher)
            ledger = fetcher.ledger_for(HOST)
            ledger.spent = 59
            with charging(fetcher, HOST, "verify"), reading_as("core"):
                result = await fetcher.get(f"https://{HOST}/programme")
        # One read left, but robots.txt would take it and the page would cross 60.
        assert result.outcome is FetchOutcome.BLOCKED
        assert wire == []

    async def test_on_ledgers_are_per_institution_and_a_shared_page_is_charged_once(
        self, tmp_path: Any, wire: list[str], ledger_on: None
    ) -> None:
        async with _fetcher(tmp_path, robots=False) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "verify"):
                await fetcher.get(f"https://{HOST}/a")
                await fetcher.get("https://www.gov.example/post-study-work")
            with charging(fetcher, OTHER, "verify"):
                await fetcher.get(f"https://{OTHER}/a")
                await fetcher.get("https://www.gov.example/post-study-work")
        assert fetcher.ledger_for(HOST).spent == 2
        assert fetcher.ledger_for(OTHER).spent == 1
        assert len(wire) == 3

    async def test_on_concurrent_reads_cannot_cross_the_cap(
        self, tmp_path: Any, wire: list[str], ledger_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetching, "CASE_READ_CAP", 5)
        async with _fetcher(tmp_path, robots=False) as fetcher:
            _install(fetcher)
            with charging(fetcher, HOST, "verify"), reading_as("core"):
                results = await asyncio.gather(
                    *(fetcher.get(f"https://{HOST}/hop/2/p{i}") for i in range(4))
                )
        assert len(wire) <= 5
        assert fetcher.ledger_for(HOST).spent == len(wire)
        assert any(r.outcome is FetchOutcome.BLOCKED for r in results)

    def test_the_start_host_and_the_catalogue_domain_share_one_ledger(self, tmp_path: Any) -> None:
        fetcher = _fetcher(tmp_path)
        assert fetcher.ledger_for("www.uni.ac.uk") is fetcher.ledger_for("uni.ac.uk")
        assert fetcher.ledger_for("uni.ac.uk") is not fetcher.ledger_for("other.ac.uk")

    async def test_on_a_stub_fetcher_is_not_metered(self, ledger_on: None) -> None:
        class Stub:
            pass

        with charging(Stub(), HOST, "verify") as ledger:
            assert ledger is None


class TestTraceAndAdapters:
    def test_the_trace_carries_the_ledger_only_when_there_is_one(self) -> None:
        trace = DiscoveryTrace(institution="Uni", domain=HOST)
        assert "read_ledger" not in trace.as_dict()
        ledger = CaseReadLedger(HOST)
        ledger.refuse(f"https://{HOST}/news-sitemap.xml", "sitemap", "2 of 60 reads left")
        trace.read_ledger = ledger
        recorded = trace.as_dict()["read_ledger"]
        assert recorded["refusals"][0]["reason"] == "2 of 60 reads left"
        assert recorded["cap"] == 60

    async def test_funding_award_pages_are_refused_before_the_index(
        self, tmp_path: Any, wire: list[str], ledger_on: None
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

        def handler(request: httpx.Request) -> httpx.Response:
            body = index if request.url.path == "/study/scholarships" else PAGE
            return httpx.Response(200, headers={"content-type": "text/html"}, text=body)

        candidate = Candidate(
            name="Uni",
            country="Testland",
            city="T",
            domain=HOST,
            scholarships_url=f"https://{HOST}/study/scholarships",
        )
        program = CandidateProgram(name="P", field="cs", degree=DegreeLevel.BACHELOR)
        async with _fetcher(tmp_path, robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            ledger = fetcher.ledger_for(HOST)
            ledger.spent = 60 - 5
            with charging(fetcher, HOST, "funding"):
                _awards, result = await WebScholarshipAdapter(fetcher, "2026/27").find(
                    candidate, program, None, allow_search=False
                )
        # The index and the first award page are core reads; one more award
        # page would leave fewer than four, the award floor: the rest are refused.
        assert wire[0].endswith("/study/scholarships")
        assert ledger.spent == 57
        assert [r["kind"] for r in ledger.refusals] == ["award"] * 3
        assert any("RL-1" in o.detail for o in result.page_outcomes)


class TestDiscovery:
    SITEMAP = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>https://{HOST}/study/bachelor/computer-science</loc></url></urlset>"
    )

    async def _discover(self, tmp_path: Any, profile: Any) -> tuple[Any, Fetcher]:
        import json

        from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/plain"},
                    text=f"User-agent: *\nSitemap: https://{HOST}/sitemap.xml\n",
                )
            if request.url.path == "/sitemap.xml":
                return httpx.Response(
                    200, headers={"content-type": "application/xml"}, text=self.SITEMAP
                )
            return httpx.Response(404)

        registry = tmp_path / "registry.json"
        entry = {"name": "Uni", "country": "Testland", "city": "T", "homepage": f"https://{HOST}/"}
        registry.write_text(json.dumps([entry]), encoding="utf-8")
        profile.context.intended_fields = ["computer science"]
        profile.context.level = "bachelor"
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            adapter = LiveDiscoveryAdapter(fetcher, registry)
            await adapter.discover(profile)
        return adapter.traces[0], fetcher

    async def test_on_discovery_is_charged_and_the_trace_carries_the_ledger(
        self, tmp_path: Any, profile: Any, wire: list[str], ledger_on: None
    ) -> None:
        trace, fetcher = await self._discover(tmp_path, profile)
        ledger = fetcher.ledger_for(HOST)
        assert trace.read_ledger is ledger
        assert ledger.spent == len(wire) > 0
        assert set(ledger.by_phase) == {"discovery"}
        # robots.txt (policy), robots.txt (page) and sitemap.xml are sitemap reads.
        assert ledger.by_kind["sitemap"] == 3
        assert trace.as_dict()["read_ledger"]["spent"] == ledger.spent

    async def test_off_the_trace_has_no_ledger(
        self, tmp_path: Any, profile: Any, wire: list[str]
    ) -> None:
        trace, fetcher = await self._discover(tmp_path, profile)
        assert trace.read_ledger is None
        assert "read_ledger" not in trace.as_dict()
        assert fetcher.ledgers == {}


BACKEND = Path(__file__).resolve().parents[1]


def test_harness_exposes_and_forwards_the_flag_and_stops_gracefully() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--case-read-ledger" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "ledger_module.CASE_READ_LEDGER = True" in source
    assert '*(["--case-read-ledger"] if args.case_read_ledger else [])' in source
    block = source[source.index("elif network_reads >= max_pages:") :]
    graceful = block.index("if fetching.CASE_READ_LEDGER:")
    assert block.index('raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")') > graceful


def test_the_runner_charges_verify_and_funding_to_each_institution(
    settings: Any, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The demo run with RL-1 on: every candidate's verify and funding reads go
    through ``charging`` under its own domain (fixture reads stay free)."""
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker

    from app.models import ApplicantProfileRow, Base, ResearchRun
    from app.pipeline import runner as runner_module
    from app.pipeline.runner import ResearchRunner
    from app.pipeline.state import RunState
    from tests.conftest import TEST_ORGANIZATION_ID

    monkeypatch.setattr(fetching, "CASE_READ_LEDGER", True)
    scopes: list[tuple[str, str]] = []
    original = fetching.charging

    def spy(fetcher: object, institution: str, phase: str) -> Any:
        scopes.append((institution, phase))
        return original(fetcher, institution, phase)

    monkeypatch.setattr(runner_module.fetching, "charging", spy)
    engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        row = ApplicantProfileRow(
            organization_id=TEST_ORGANIZATION_ID,
            display_name="t",
            payload=profile.model_dump(mode="json"),
        )
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id,
            stage="queued",
            demo_mode=True,
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        runner = ResearchRunner(session, run, profile, settings)
        asyncio.run(runner.run_to_decision())
        domains = {c.domain for c in runner._candidates}
    finally:
        session.close()
        engine.dispose()
    assert {phase for _institution, phase in scopes} == {"verify", "funding"}
    assert {institution for institution, _phase in scopes} <= domains
    verified = {institution for institution, phase in scopes if phase == "verify"}
    funded = {institution for institution, phase in scopes if phase == "funding"}
    assert funded and funded <= verified
