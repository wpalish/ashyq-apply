"""Regressions for false positives observed in a live run.

Each test here corresponds to a claim the system made that no official source
supported. They are written from the *shape* of the real pages that produced
them (see tests/fixtures/live_shapes/), so the defect cannot reappear.

Precision over recall: an honest UNKNOWN is always preferred to one false
confirmation. Every assertion below encodes that trade.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import html_to_text
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.enums import ClaimType

SHAPES = Path(__file__).parent / "fixtures" / "live_shapes"

#: Claims from the most recent _find_awards call, so excerpt provenance can be
#: asserted without threading a return value through every caller.
_last_award_claims: list = []


def shape(name: str) -> str:
    return (SHAPES / name).read_text()


def claims_by_type(claims) -> dict:
    out: dict = {}
    for c in claims:
        out.setdefault(c.claim_type, []).append(c)
    return out


# ---------------------------------------------------------------------------
# FP-1  A general admissions page does not prove a programme exists
# ---------------------------------------------------------------------------


class TestProgramExistence:
    """Observed: `PROGRAM_EXISTS: computer science (bachelor)` from a page
    titled "Check admission requirements | BSc Dutch diploma"."""

    def test_a_general_admissions_page_is_classified_as_such(self):
        page = classify_page(
            url="https://www.tudelft.nl/en/education/admission-and-application/bsc-dutch-diploma",
            html=shape("general_admissions_dutch_diploma.html"),
        )
        assert page.page_type is PageType.GENERAL_ADMISSIONS

    def test_a_programme_catalogue_is_not_a_programme_page(self):
        page = classify_page(url="https://uni.edu/bachelors", html=shape("program_catalog.html"))
        assert page.page_type is PageType.PROGRAM_CATALOG

    def test_a_careers_page_is_irrelevant_to_admissions(self):
        page = classify_page(
            url="https://careers.univie.ac.at/en/how-to-apply", html=shape("careers_page.html")
        )
        assert page.page_type in (PageType.IRRELEVANT, PageType.NAVIGATION)

    @pytest.mark.asyncio
    async def test_no_program_exists_claim_from_a_general_admissions_page(
        self, settings, tmp_path, monkeypatch
    ):
        result = await _verify_against(
            monkeypatch, settings, tmp_path,
            page_html=shape("general_admissions_dutch_diploma.html"),
            program_name="computer science (bachelor)",
            url="https://www.tudelft.nl/en/education/admission-and-application/bsc-dutch-diploma",
        )
        assert ClaimType.PROGRAM_EXISTS not in claims_by_type(result.claims)

    @pytest.mark.asyncio
    async def test_a_real_programme_page_does_produce_the_claim(
        self, settings, tmp_path, monkeypatch
    ):
        """The guard must not simply suppress everything."""
        result = await _verify_against(
            monkeypatch, settings, tmp_path,
            page_html=shape("program_detail_cse.html"),
            program_name="BSc Computer Science and Engineering",
            url="https://www.tudelft.nl/en/education/programmes/bachelors/cse",
        )
        assert ClaimType.PROGRAM_EXISTS in claims_by_type(result.claims)

    @pytest.mark.asyncio
    async def test_a_degree_level_mismatch_blocks_the_claim(
        self, settings, tmp_path, monkeypatch
    ):
        """A master's page does not confirm a bachelor's programme."""
        result = await _verify_against(
            monkeypatch, settings, tmp_path,
            page_html=shape("scholarship_award_msc_only.html"),
            program_name="BSc Computer Science",
            url="https://www.tudelft.nl/en/education/programmes/masters/cs",
        )
        assert ClaimType.PROGRAM_EXISTS not in claims_by_type(result.claims)


# ---------------------------------------------------------------------------
# FP-2  Absence of "closed" is not evidence of "open"
# ---------------------------------------------------------------------------


class TestIntakeAvailability:
    @pytest.mark.asyncio
    async def test_a_page_that_says_nothing_about_the_cycle_yields_no_open_claim(
        self, settings, tmp_path, monkeypatch
    ):
        result = await _verify_against(
            monkeypatch, settings, tmp_path,
            page_html=shape("general_admissions_dutch_diploma.html"),
            program_name="computer science (bachelor)",
            url="https://www.tudelft.nl/en/education/admission-and-application/bsc-dutch-diploma",
        )
        intake = claims_by_type(result.claims).get(ClaimType.INTAKE_OPEN, [])
        assert not [c for c in intake if c.normalized_value is True]

    @pytest.mark.asyncio
    async def test_an_explicit_application_window_does_produce_an_open_claim(
        self, settings, tmp_path, monkeypatch
    ):
        result = await _verify_against(
            monkeypatch, settings, tmp_path,
            page_html=shape("program_detail_cse.html"),
            program_name="BSc Computer Science and Engineering",
            url="https://www.tudelft.nl/en/education/programmes/bachelors/cse",
            intake="fall 2027",
        )
        intake = claims_by_type(result.claims).get(ClaimType.INTAKE_OPEN, [])
        assert [c for c in intake if c.normalized_value is True], (
            "a page stating the window opens 1 October 2026 and closes 15 January 2027 "
            "for 2027/2028 is genuine evidence"
        )


# ---------------------------------------------------------------------------
# FP-3  Every excerpt must be quoted from the page
# ---------------------------------------------------------------------------


class TestExcerptsAreRealQuotes:
    """Observed: the evidence panel showed `"Page describes entry for the fall
    2027 intake."` — a sentence the extractor wrote, not the page."""

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(text.split()).lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("fixture,program", [
        ("program_detail_cse.html", "BSc Computer Science and Engineering"),
        ("general_admissions_dutch_diploma.html", "computer science (bachelor)"),
        ("news_page.html", "computer science (bachelor)"),
    ])
    async def test_every_excerpt_appears_verbatim_in_the_page(
        self, settings, tmp_path, monkeypatch, fixture, program
    ):
        html = shape(fixture)
        result = await _verify_against(
            monkeypatch, settings, tmp_path, page_html=html,
            program_name=program, url="https://uni.edu/page",
        )
        page_text = self._normalise(html_to_text(html))
        for claim in result.claims:
            if not claim.original_text_excerpt:
                continue
            excerpt = self._normalise(claim.original_text_excerpt)
            assert excerpt in page_text, (
                f"{claim.claim_type} carries an excerpt that is not on the page: "
                f"{claim.original_text_excerpt!r}"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("fixture", [
        "scholarship_award_msc_only.html",
        "scholarship_award_no_deadline.html",
    ])
    async def test_award_claims_quote_the_award_page(
        self, settings, tmp_path, monkeypatch, fixture
    ):
        """The same guarantee for the scholarship adapter.

        "Award page: <title>" and "the page describes the award for master
        only" were both sentences the extractor wrote, shown as evidence.
        """
        html = shape(fixture)
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/x": html},
            index_html='<a href="https://uni.edu/scholarships/x">Award Scholarship</a>',
        )
        assert awards
        page_text = self._normalise(html_to_text(html))
        from app.adapters.fetching import Fetcher as _F  # noqa: F401  (import kept local)

        for claim in _last_award_claims:
            if not claim.original_text_excerpt:
                continue
            assert self._normalise(claim.original_text_excerpt) in page_text, (
                f"{claim.claim_type} excerpt is not on the page: "
                f"{claim.original_text_excerpt!r}"
            )


# ---------------------------------------------------------------------------
# FP-4  An index or FAQ page is not an award
# ---------------------------------------------------------------------------


class TestScholarshipPageClassification:
    def test_an_index_page_is_an_index(self):
        page = classify_page(url="https://uni.edu/scholarships", html=shape("scholarship_index.html"))
        assert page.page_type is PageType.SCHOLARSHIP_INDEX

    def test_a_faq_is_a_faq(self):
        page = classify_page(
            url="https://uni.edu/scholarships/faq", html=shape("scholarship_faq.html")
        )
        assert page.page_type is PageType.SCHOLARSHIP_FAQ

    def test_an_award_page_is_an_award(self):
        page = classify_page(
            url="https://uni.edu/scholarships/van-effen",
            html=shape("scholarship_award_msc_only.html"),
        )
        assert page.page_type is PageType.SCHOLARSHIP_AWARD

    @pytest.mark.asyncio
    @pytest.mark.parametrize("fixture", ["scholarship_index.html", "scholarship_faq.html"])
    async def test_no_award_is_created_from_an_index_or_faq(
        self, settings, tmp_path, monkeypatch, fixture
    ):
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/x": shape(fixture)},
            index_html='<a href="https://uni.edu/scholarships/x">Scholarship information</a>',
        )
        assert awards == []

    @pytest.mark.asyncio
    async def test_an_award_page_still_produces_an_award(
        self, settings, tmp_path, monkeypatch
    ):
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/merit": shape("scholarship_award_no_deadline.html")},
            index_html='<a href="https://uni.edu/scholarships/merit">Faculty Merit Award</a>',
        )
        assert len(awards) == 1
        assert awards[0].name == "Faculty Merit Award"


# ---------------------------------------------------------------------------
# FP-5  A generic mention of international students is not eligibility evidence
# ---------------------------------------------------------------------------


class TestInternationalEligibility:
    @pytest.mark.asyncio
    async def test_a_generic_mention_does_not_confirm_eligibility(
        self, settings, tmp_path, monkeypatch
    ):
        """"few external scholarships are offered to international students" is
        not an affirmative eligibility clause."""
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/merit": shape("scholarship_award_no_deadline.html")},
            index_html='<a href="https://uni.edu/scholarships/merit">Faculty Merit Award</a>',
        )
        assert awards[0].international_eligible == "unknown"

    @pytest.mark.asyncio
    async def test_an_affirmative_clause_does_confirm_eligibility(
        self, settings, tmp_path, monkeypatch
    ):
        html = shape("scholarship_award_no_deadline.html").replace(
            "<h2>Eligibility</h2><p>Open to admitted bachelor's students in the Faculty of Science.</p>",
            "<h2>Eligibility</h2><p>International applicants are eligible to apply.</p>",
        )
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/merit": html},
            index_html='<a href="https://uni.edu/scholarships/merit">Faculty Merit Award</a>',
        )
        assert awards[0].international_eligible == "yes"


# ---------------------------------------------------------------------------
# FP-6  A master's award is not an opportunity for a bachelor's applicant
# ---------------------------------------------------------------------------


class TestDegreeApplicability:
    @pytest.mark.asyncio
    async def test_an_msc_award_is_not_applicable_to_a_bachelor_applicant(
        self, settings, tmp_path, monkeypatch
    ):
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/van-effen": shape("scholarship_award_msc_only.html")},
            index_html='<a href="https://uni.edu/scholarships/van-effen">van Effen Scholarship</a>',
            degree="bachelor",
        )
        assert len(awards) == 1
        assert awards[0].degree_applicability == "no", (
            "the page says the scholarship is not available for bachelor's programmes"
        )

    @pytest.mark.asyncio
    async def test_the_same_award_is_applicable_to_a_master_applicant(
        self, settings, tmp_path, monkeypatch
    ):
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/van-effen": shape("scholarship_award_msc_only.html")},
            index_html='<a href="https://uni.edu/scholarships/van-effen">van Effen Scholarship</a>',
            degree="master",
        )
        assert awards[0].degree_applicability == "yes"

    @pytest.mark.asyncio
    async def test_an_award_silent_on_degree_is_unknown_not_eligible(
        self, settings, tmp_path, monkeypatch
    ):
        html = shape("scholarship_award_no_deadline.html").replace(
            "for outstanding bachelor's students", "for outstanding students"
        ).replace("Open to admitted bachelor's students in the Faculty of Science.",
                  "Open to admitted students in the Faculty of Science.")
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/merit": html},
            index_html='<a href="https://uni.edu/scholarships/merit">Faculty Merit Award</a>',
            degree="bachelor",
        )
        assert awards[0].degree_applicability == "unknown"


# ---------------------------------------------------------------------------
# FP-7  No deadline is not availability
# ---------------------------------------------------------------------------


class TestAvailabilityStates:
    @pytest.mark.asyncio
    async def test_an_award_with_no_published_deadline_is_not_available_yes(
        self, settings, tmp_path, monkeypatch
    ):
        awards = await _find_awards(
            monkeypatch, settings, tmp_path,
            pages={"https://uni.edu/scholarships/merit": shape("scholarship_award_no_deadline.html")},
            index_html='<a href="https://uni.edu/scholarships/merit">Faculty Merit Award</a>',
        )
        award = awards[0]
        assert award.deadline is None
        assert award.deadline_known is False
        assert award.available_this_intake == "unknown"

    def test_availability_states_are_separate_fields(self):
        """They must not be collapsed into one flag."""
        from app.schemas.result import Scholarship

        fields = set(Scholarship.model_fields)
        for name in (
            "opportunity_exists", "currently_available", "applicant_eligible",
            "application_window_open", "deadline_known", "deadline_passed",
            "award_current_for_intake", "degree_applicability",
        ):
            assert name in fields, f"Scholarship is missing the {name!r} state"


# ---------------------------------------------------------------------------
# Shared harness
# ---------------------------------------------------------------------------


async def _verify_against(
    monkeypatch, settings, tmp_path, *, page_html: str, program_name: str,
    url: str, intake: str = "fall 2027",
):
    """Run the requirements adapter against one in-memory page."""
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {url: page_html})
        candidate = Candidate(name="Test University", country="Netherlands", city="Delft",
                              domain="uni.edu")
        program = CandidateProgram(name=program_name, field="computer science",
                                   degree="bachelor", url=url)
        return await WebRequirementsAdapter(fetcher, "2026/27").verify(candidate, program, intake)


async def _find_awards(
    monkeypatch, settings, tmp_path, *, pages: dict[str, str], index_html: str,
    degree: str = "bachelor",
):
    index_url = "https://uni.edu/scholarships"
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {index_url: _wrap_index(index_html), **pages})
        candidate = Candidate(name="Test University", country="Netherlands", city="Delft",
                              domain="uni.edu", scholarships_url=index_url)
        program = CandidateProgram(name="BSc Computer Science", field="computer science",
                                   degree=degree, url="https://uni.edu/bsc/cs")
        awards, result = await WebScholarshipAdapter(fetcher, "2026/27").find(
            candidate, program, None
        )
        _last_award_claims.clear()
        _last_award_claims.extend(result.claims)
        return awards


def _wrap_index(body: str) -> str:
    return f"<!doctype html><html><head><title>Scholarships</title></head><body><main>{body}</main></body></html>"


def _serve(monkeypatch, fetcher: Fetcher, pages: dict[str, str]) -> None:
    """Serve fixed HTML for fixed URLs through the real Fetcher interface."""
    from datetime import UTC, datetime

    from app.adapters.fetching import FetchResult
    from app.domain.enums import FetchOutcome

    async def fake_get(url: str, *, use_cache: bool = True) -> FetchResult:
        html = pages.get(url) or pages.get(url.rstrip("/"))
        if html is None:
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404,
                               error="not in this test's page set", final_url=url)
        body = html.encode()
        return FetchResult(
            url=url, outcome=FetchOutcome.OK, status_code=200, content=body, text=html,
            content_type="text/html; charset=utf-8", fetched_at=datetime.now(UTC), final_url=url,
        )

    monkeypatch.setattr(fetcher, "get", fake_get)


# ---------------------------------------------------------------------------
# FP-8  candidate_limit was accepted and ignored
# ---------------------------------------------------------------------------


class TestCandidateLimit:
    @pytest.mark.asyncio
    async def test_a_limit_of_one_produces_at_most_one_candidate(self, settings, profile):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.models import ApplicantProfileRow, Base, ResearchRun
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            run = ResearchRun(
                profile_id=row.id, stage="queued", demo_mode=True,
                candidate_limit=1, verify_limit=1, stage_state=RunState.load(None).dump(),
            )
            session.add(run)
            session.flush()

            runner = ResearchRunner(session, run, profile, settings)
            assert runner.candidate_limit == 1
            await runner.run_to_decision()

            assert run.candidates_found <= 1, "the requested limit was not applied"
            assert run.settings_snapshot["candidate_limit"] == 1
            assert run.settings_snapshot["candidate_limit_source"] == "run"
        finally:
            session.close()

    def test_verify_limit_can_never_exceed_candidate_limit(self, settings, profile):
        from app.models import ResearchRun
        from app.pipeline.runner import ResearchRunner

        run = ResearchRun(profile_id="p", stage="queued", demo_mode=True,
                          candidate_limit=3, verify_limit=50, stage_state={})
        runner = ResearchRunner(None, run, profile, settings)  # type: ignore[arg-type]
        assert runner.verify_limit == 3

    def test_the_server_default_applies_when_the_run_does_not_override(self, settings, profile):
        from app.models import ResearchRun
        from app.pipeline.runner import ResearchRunner

        run = ResearchRun(profile_id="p", stage="queued", demo_mode=True, stage_state={})
        runner = ResearchRunner(None, run, profile, settings)  # type: ignore[arg-type]
        assert runner.candidate_limit == settings.candidate_limit


# ---------------------------------------------------------------------------
# FP-9  The browser tier was constructed on every run and never invoked
# ---------------------------------------------------------------------------


class TestBrowserTierIsReallyUsed:
    @pytest.mark.asyncio
    async def test_an_empty_shell_page_escalates_to_the_renderer(self, tmp_path):
        """A 200 with no extractable text must reach the browser tier."""
        from datetime import UTC, datetime

        from app.adapters.fetching import FetchResult
        from app.domain.enums import FetchOutcome

        rendered_urls: list[str] = []

        class RecordingRenderer:
            async def render(self, url: str) -> FetchResult:
                rendered_urls.append(url)
                html = "<html><body><main><p>" + ("Real content. " * 60) + "</p></main></body></html>"
                return FetchResult(
                    url=url, outcome=FetchOutcome.OK, status_code=200,
                    content=html.encode(), text=html, content_type="text/html",
                    fetched_at=datetime.now(UTC), final_url=url,
                )

        async with Fetcher(tmp_path / "cache", delay_seconds=0.0) as fetcher:
            fetcher.attach_renderer(RecordingRenderer())
            shell = '<html><body><div id="root"></div></body></html>'
            fetcher._client = _StubClient({"https://uni.edu/js-page": shell})  # type: ignore[assignment]
            fetcher.robots.enabled = False
            result = await fetcher.get("https://uni.edu/js-page")

        assert rendered_urls == ["https://uni.edu/js-page"]
        assert result.fetch_tier == "browser"
        assert "Real content" in result.text
        assert fetcher.tier_counts["browser"] == 1

    @pytest.mark.asyncio
    async def test_a_page_with_real_content_is_not_escalated(self, tmp_path):
        """Escalation is an exception, not the default: a browser is expensive."""
        rendered: list[str] = []

        class RecordingRenderer:
            async def render(self, url):  # pragma: no cover - must not run
                rendered.append(url)
                raise AssertionError("should not escalate a page that already has content")

        html = "<html><body><main><p>" + ("Plenty of readable prose. " * 40) + "</p></main></body></html>"
        async with Fetcher(tmp_path / "cache", delay_seconds=0.0) as fetcher:
            fetcher.attach_renderer(RecordingRenderer())
            fetcher._client = _StubClient({"https://uni.edu/static": html})  # type: ignore[assignment]
            fetcher.robots.enabled = False
            result = await fetcher.get("https://uni.edu/static")

        assert rendered == []
        assert result.fetch_tier == "http"

    def test_the_runner_attaches_the_renderer_to_the_fetcher(self):
        """The defect was a browser that existed but was never wired in."""
        import inspect

        from app.pipeline.runner import ResearchRunner

        source = inspect.getsource(ResearchRunner.run_to_decision)
        assert "attach_renderer" in source


class _StubClient:
    """Minimal httpx.AsyncClient stand-in returning fixed HTML."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    async def get(self, url: str, **_kwargs):
        from types import SimpleNamespace

        html = self.pages[url]
        return SimpleNamespace(
            status_code=200, content=html.encode(), text=html, encoding="utf-8",
            headers={"content-type": "text/html; charset=utf-8"}, url=url,
        )

    async def aclose(self) -> None:
        return None


# ---------------------------------------------------------------------------
# A database created before a column existed must fail loudly at startup
# ---------------------------------------------------------------------------


class TestSchemaDrift:
    """A database the code does not match must fail at startup, not at request time.

    This surfaced as `table research_runs has no column named candidate_limit`
    on an unrelated request. The check is now against the Alembic revision,
    which catches every kind of drift rather than only missing columns.
    """

    def test_a_database_that_was_never_migrated_is_reported(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine

        import app.db as db_module

        engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}",
                               connect_args={"check_same_thread": False})
        monkeypatch.setattr(db_module, "engine", engine)
        with pytest.raises(db_module.SchemaOutOfDate) as exc:
            db_module.assert_at_head()
        assert "never been migrated" in str(exc.value)
        assert "alembic upgrade head" in str(exc.value)

    def test_a_database_behind_head_names_both_revisions(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine, text

        import app.db as db_module

        url = f"sqlite:///{tmp_path / 'behind.db'}"
        db_module.migrate_to_head(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = 'oldrev'"))
        monkeypatch.setattr(db_module, "engine", engine)

        with pytest.raises(db_module.SchemaOutOfDate) as exc:
            db_module.assert_at_head()
        assert "oldrev" in str(exc.value)
        assert db_module.head_revision() in str(exc.value)

    def test_a_migrated_database_passes(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine

        import app.db as db_module

        url = f"sqlite:///{tmp_path / 'fresh.db'}"
        db_module.migrate_to_head(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        monkeypatch.setattr(db_module, "engine", engine)
        db_module.assert_at_head()

    def test_create_all_is_not_used_as_a_migration_mechanism(self):
        """It creates missing tables and silently ignores changed columns."""
        import inspect

        import app.db as db_module

        source = inspect.getsource(db_module.init_db)
        assert "create_all" not in source
        assert "migrate_to_head" in source


# ---------------------------------------------------------------------------
# Crash / restart: a run must never sit "running" with no worker behind it
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    """A worker that dies mid-stage used to leave the run claiming to be
    running, and the UI polled it forever."""

    @staticmethod
    def _session(settings):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head

        migrate_to_head(settings.database_url)
        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
        return engine, sessionmaker(bind=engine)()

    def test_a_fresh_heartbeat_is_not_treated_as_abandoned(self):
        from datetime import UTC, datetime, timedelta

        from app.pipeline.state import is_lease_expired

        assert not is_lease_expired(
            "funding_discovery", datetime.now(UTC) - timedelta(seconds=5)
        )

    def test_a_silent_worker_expires_its_lease(self):
        from datetime import UTC, datetime, timedelta

        from app.pipeline.state import is_lease_expired

        assert is_lease_expired(
            "funding_discovery", datetime.now(UTC) - timedelta(seconds=600)
        )

    def test_a_run_awaiting_a_decision_is_never_abandoned(self):
        """Waiting for the user is not work, however long it lasts."""
        from datetime import UTC, datetime, timedelta

        from app.pipeline.state import is_lease_expired

        assert not is_lease_expired(
            "awaiting_user_decision", datetime.now(UTC) - timedelta(days=30)
        )

    def test_a_queued_run_that_never_started_is_not_abandoned(self):
        from app.pipeline.state import is_lease_expired

        assert not is_lease_expired("queued", None)

    @pytest.mark.asyncio
    async def test_a_completed_run_releases_its_lease(self, settings, profile):
        from app.models import ApplicantProfileRow, ResearchRun
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        engine, session = self._session(settings)
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            run = ResearchRun(profile_id=row.id, stage="queued", demo_mode=True,
                              candidate_limit=2, verify_limit=2,
                              stage_state=RunState.load(None).dump())
            session.add(run)
            session.flush()
            await ResearchRunner(session, run, profile, settings).run_to_decision()

            assert run.stage == "awaiting_user_decision"
            assert run.worker_id is None, "a run waiting on the user holds no lease"
        finally:
            session.close()
            engine.dispose()

    def test_startup_reconciliation_recovers_a_stranded_run(self, settings, profile, monkeypatch):
        """A run mid-pipeline with no queued or running job is stranded."""
        import app.db as db_module
        from app.jobs.worker import reconcile_startup
        from app.models import ApplicantProfileRow, ResearchRun

        engine, session = self._session(settings)
        from sqlalchemy.orm import sessionmaker

        monkeypatch.setattr(db_module, "engine", engine)
        monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=engine, future=True))
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            run = ResearchRun(profile_id=row.id, stage="funding_discovery", demo_mode=True,
                              worker_id="host:9999", stage_state={})
            session.add(run)
            session.commit()
            run_id = run.id

            summary = reconcile_startup()
            assert summary["runs_recovered"] == 1

            session.expire_all()
            refreshed = session.get(ResearchRun, run_id)
            assert refreshed.stage == "retryable_failed"
            assert refreshed.worker_id is None
            assert refreshed.recovery_count == 1
            assert any("recovered at startup" in e for e in refreshed.errors)
        finally:
            session.close()
            engine.dispose()

    def test_reconciliation_leaves_a_run_with_a_live_job_alone(
        self, settings, profile, monkeypatch
    ):
        import app.db as db_module
        from app.jobs.store import JobStore
        from app.jobs.worker import reconcile_startup
        from app.models import ApplicantProfileRow, ResearchRun

        engine, session = self._session(settings)
        from sqlalchemy.orm import sessionmaker

        monkeypatch.setattr(db_module, "engine", engine)
        monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=engine, future=True))
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            live = ResearchRun(profile_id=row.id, stage="funding_discovery", demo_mode=True,
                               stage_state={})
            done = ResearchRun(profile_id=row.id, stage="completed", demo_mode=True,
                               stage_state={}, finished_at=datetime.now(UTC))
            session.add_all([live, done])
            session.flush()
            JobStore(session).enqueue("research", run_id=live.id)
            session.commit()

            assert reconcile_startup()["runs_recovered"] == 0
            session.expire_all()
            assert session.get(ResearchRun, live.id).stage == "funding_discovery"
            assert session.get(ResearchRun, done.id).stage == "completed"
        finally:
            session.close()
            engine.dispose()

    def test_the_api_reports_a_stale_run_as_not_running(self, settings, profile, monkeypatch):
        """The UI must not poll a run whose worker is gone."""
        from datetime import UTC, datetime, timedelta

        import app.db as db_module
        from app.api.routes_research import _view
        from app.models import ApplicantProfileRow, ResearchRun

        engine, session = self._session(settings)
        monkeypatch.setattr(db_module, "engine", engine)
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            run = ResearchRun(
                profile_id=row.id, stage="program_verification", demo_mode=True,
                worker_id="host:dead", stage_state={},
                heartbeat_at=datetime.now(UTC) - timedelta(seconds=600),
            )
            session.add(run)
            session.commit()

            view = _view(session, run)
            assert view.stale is True
            assert view.job_running is False
        finally:
            session.close()
            engine.dispose()


# ---------------------------------------------------------------------------
# Site chrome must not be read as page content
# ---------------------------------------------------------------------------


class TestSiteChromeIsIgnored:
    """Every page on a university site carries the same global menu.

    Counting its links classified a single award page as an index (six award
    links, all from the menu) and an admissions page as a catalogue (twelve
    programme links, all from the menu). Observed on tudelft.nl and rug.nl.
    """

    NAV = """
      <header><a href="/">Home</a></header>
      <nav class="main-menu">
        <a href="/en/education/programmes/bachelors/cs">Computer Science</a>
        <a href="/en/education/programmes/bachelors/ae">Aerospace Engineering</a>
        <a href="/en/education/programmes/masters/cs">MSc Computer Science</a>
        <a href="/en/education/programmes/bachelors/ap">Applied Physics</a>
        <a href="/en/education/programmes/masters/ae">MSc Aerospace</a>
        <a href="/en/education/programmes/bachelors/me">Mechanical Engineering</a>
        <a href="/scholarships/van-effen">van Effen Scholarship</a>
        <a href="/scholarships/holland">Holland Scholarship</a>
        <a href="/scholarships/faq">Scholarship FAQ</a>
        <a href="/scholarships/other">Scholarships from other providers</a>
      </nav>
    """
    FOOTER = '<footer><a href="/scholarships">Scholarships</a><a href="/privacy">Privacy</a></footer>'

    def _page(self, title: str, body: str) -> str:
        return (
            f"<!doctype html><html><head><title>{title}</title></head><body>"
            f"{self.NAV}<main>{body}</main>{self.FOOTER}</body></html>"
        )

    def test_an_award_page_wrapped_in_a_menu_is_still_an_award(self):
        html = self._page(
            "Justus & Louise van Effen Excellence Scholarship",
            "<h1>Justus &amp; Louise van Effen Excellence Scholarship</h1>"
            "<p>The scholarship covers tuition and housing for students enrolling in an "
            "MSc programme.</p><h2>Who can apply</h2><p>You are eligible if you are enrolling "
            "in a two-year MSc programme.</p><h2>How to apply</h2>"
            "<p>Candidates are nominated by the faculty.</p>",
        )
        page = classify_page(url="https://uni.edu/scholarships/van-effen", html=html)
        assert page.page_type is PageType.SCHOLARSHIP_AWARD
        assert page.subject and "van Effen" in page.subject

    def test_an_admissions_page_wrapped_in_a_menu_is_not_a_catalogue(self):
        html = self._page(
            "Check admission requirements",
            "<h1>Check admission requirements</h1>"
            "<p>These pages explain the admission requirements for applicants holding a Dutch "
            "secondary school diploma.</p>",
        )
        page = classify_page(url="https://uni.edu/admission/check", html=html)
        assert page.page_type is not PageType.PROGRAM_CATALOG

    def test_the_page_identity_comes_from_the_content_not_the_menu(self):
        html = self._page(
            "Faculty Merit Award",
            "<h1>Faculty Merit Award</h1><p>The award is worth EUR 5,000 per year. "
            "Open to admitted students. No separate application is required.</p>",
        )
        page = classify_page(url="https://uni.edu/scholarships/merit", html=html)
        assert page.subject == "Faculty Merit Award"

    def test_main_content_drops_navigation_and_keeps_the_page(self):
        from bs4 import BeautifulSoup

        from app.adapters.page_classifier import main_content

        html = self._page("X", "<h1>Real heading</h1><p>" + "Real content. " * 30 + "</p>")
        content = main_content(BeautifulSoup(html, "lxml"))
        text = content.get_text(" ", strip=True)
        assert "Real heading" in text
        assert "Aerospace Engineering" not in text
        assert "Privacy" not in text


class TestCostVocabulary:
    """`\\btuition fee\\b` does not match "tuition fees"; a fees page was
    therefore classified as general admissions and its costs never read."""

    @pytest.mark.parametrize("heading", [
        "Application, registration and tuition fees",
        "Tuition fee",
        "Cost of attendance",
        "Tuition fees and funding",
        "Living costs",
    ])
    def test_cost_headings_are_recognised_in_singular_and_plural(self, heading):
        html = f"<!doctype html><html><head><title>{heading}</title></head><body><main>" \
               f"<h1>{heading}</h1><p>Details of what studying here costs.</p></main></body></html>"
        page = classify_page(url="https://uni.edu/fees", html=html)
        assert page.page_type is PageType.COSTS


# ---------------------------------------------------------------------------
# Degree applicability on the shapes real award pages actually use
# ---------------------------------------------------------------------------


class TestDegreeApplicabilityOnRealShapes:
    """Both cases below were found by the live canary against tudelft.nl.

    Text is paraphrased from the real pages; the sentence *structure* is what
    the extractor has to cope with.
    """

    #: Mirrors the real page's structure: an eligibility sentence stating the
    #: level, then a separate "not eligible if" list. The exclusion sits 75
    #: characters after "not eligible", past the window the first
    #: implementation used, and its clause ends in a colon.
    EXCLUSION_PAGE = (
        "Justus & Louise van Effen Excellence Scholarships. The foundation supports "
        "excellent international MSc students. You are eligible if you are an "
        "international applicant applying for a 2-year regular MSc programme. "
        "You are not eligible for the Justus & Louise van Effen Excellence Scholarships "
        "if: You are a university bachelor's student, even if you have obtained your "
        "bachelor's degree at a Dutch university."
    )

    #: No exclusion at all; the level is settled by a positive statement about a
    #: *different* level, and the applicant's own bachelor's appears only as a
    #: prior qualification.
    OTHER_LEVEL_PAGE = (
        "Innovation Programme Scholarship. Up to five scholarships are provided annually "
        "to students who have completed undergraduate studies in Greece, and hold either "
        "a Greek passport or Greek residence. The scholarships are available to students "
        "entering the academic year 2026 for one of the following specific Master of "
        "Science Programmes: MSc Environmental Engineering; MSc Geomatics. Applicants "
        "must submit an Undergraduate Degree Transcript with GPA."
    )

    def test_an_exclusion_far_from_its_negation_is_still_found(self):
        from app.adapters.applicability import assess_degree_applicability

        verdict = assess_degree_applicability(self.EXCLUSION_PAGE, "bachelor")
        assert verdict.verdict == "no"
        assert "bachelor" in verdict.evidence.lower()

    def test_the_same_page_applies_to_a_master_applicant(self):
        from app.adapters.applicability import assess_degree_applicability

        assert assess_degree_applicability(self.EXCLUSION_PAGE, "master").verdict == "yes"

    def test_a_degree_held_is_not_the_degree_awarded(self):
        """"obtained your bachelor's degree" must not read as "for bachelors"."""
        from app.adapters.applicability import assess_degree_applicability

        assert assess_degree_applicability(self.EXCLUSION_PAGE, "bachelor").verdict != "yes"

    def test_a_positive_mention_inside_an_exclusion_clause_does_not_count(self):
        """A level named only inside "you are not eligible if" is not included."""
        from app.adapters.applicability import assess_degree_applicability

        collapsed = (
            "Excellence Scholarship. You are not eligible if: you are a bachelor's "
            "student, even if you are applying for an MSc programme."
        )
        assert assess_degree_applicability(collapsed, "master").verdict != "yes"

    def test_a_positive_statement_about_another_level_excludes_this_one(self):
        from app.adapters.applicability import assess_degree_applicability

        verdict = assess_degree_applicability(self.OTHER_LEVEL_PAGE, "bachelor")
        assert verdict.verdict == "no"
        assert "master" in verdict.reason.lower()

    def test_that_page_applies_to_a_master_applicant(self):
        from app.adapters.applicability import assess_degree_applicability

        assert assess_degree_applicability(self.OTHER_LEVEL_PAGE, "master").verdict == "yes"

    def test_a_prior_undergraduate_requirement_is_not_an_award_level(self):
        from app.adapters.applicability import assess_degree_applicability

        verdict = assess_degree_applicability(self.OTHER_LEVEL_PAGE, "bachelor")
        assert verdict.verdict != "yes", (
            "'completed undergraduate studies' is an entry requirement, not the award's level"
        )

    def test_a_page_naming_no_level_stays_unknown(self):
        from app.adapters.applicability import assess_degree_applicability

        neutral = (
            "Faculty Merit Award. The award is worth EUR 5,000 per year and is open to "
            "admitted students in the Faculty of Science. No separate application is required."
        )
        assert assess_degree_applicability(neutral, "bachelor").verdict == "unknown"
