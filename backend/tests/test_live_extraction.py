"""Extraction dictionary and canary-diagnostic visibility (T18 / L01).

Two defects are pinned here, both found by the planner's canary diagnosis of a
real run that reported "35 pages, 0 claims, 0 failed" and could not explain
itself.

B. The extraction dictionary is narrower than the universities it reads:
   ``_MONEY``/``_CURRENCY_SYMBOLS`` know no KZT and no tenge sign, so a
   Kazakhstani tuition page produces no money claim at all; ``_IELTS_OVERALL``
   only matches when a keyword (overall/minimum/score of/band) sits *between*
   "IELTS" and the number, so "IELTS 6.5 overall (or equivalent)" is missed.

A. The run is blind to its own adapter-level outcomes. Pages that were fetched
   fine but answered nothing (unreadable text, rejected by the classifier, or
   read with no pattern matching) vanish: ``AdapterResult.page_types`` is
   collected and then dropped by the runner, and no diagnostic names the
   outcome. "0 failed" is a fetch-level fact only.

The required behaviour frozen by these tests (T18 acceptance, translated to
the runner path): after a run, the run's persisted diagnostics
(``research_runs.errors`` + ``research_runs.unknowns``, the lines the canary
report is built from) must say, per page URL, which of these happened:

* ``unreadable``          — fetched OK, no readable text could be extracted;
* ``classifier-rejected`` — read, but classified as a page kind that cannot
                            answer the question (the page kind is named);
* ``no-pattern-match``    — read and accepted by an extractor, which matched
                            no pattern at all;
* and every page that *was* read must leave its page classification
  (``AdapterResult.page_types``) on the run instead of being discarded.

Category wording follows the frozen acceptance vocabulary
(fetch-failed / unreadable / classifier-rejected / no-pattern-match).

unknown ≠ zero throughout: a page that says nothing leaves a diagnostic with
a reason and never produces a claim that a requirement is absent.

All pages here are synthetic fixtures (tests/fixtures/qa_t18/) served through
the real adapter interfaces in memory. No test in this module touches the
network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.extraction import (
    ClaimBuilder,
    extract_costs,
    extract_requirements,
    html_to_text,
    parse_money,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import ClaimType, CostCategory, DegreeLevel, FetchOutcome
from app.schemas.profile import ApplicantProfileIn

FIXTURES = Path(__file__).parent / "fixtures" / "qa_t18"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# ---------------------------------------------------------------------------
# Shared harnesses. Pages are served through the real Fetcher interface, so
# the adapters under test run unmodified - nothing here imports a fake.
# ---------------------------------------------------------------------------


def _serve(monkeypatch, fetcher: Fetcher, pages: dict[str, str]) -> None:
    """Serve fixed HTML for fixed URLs through the real Fetcher interface."""

    async def fake_get(url: str, *, use_cache: bool = True) -> FetchResult:
        html = pages.get(url) or pages.get(url.rstrip("/"))
        if html is None:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.HTTP_ERROR,
                status_code=404,
                error="not in this test's page set",
                final_url=url,
            )
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            content=html.encode(),
            text=html,
            content_type="text/html; charset=utf-8",
            fetched_at=datetime.now(UTC),
            final_url=url,
        )

    monkeypatch.setattr(fetcher, "get", fake_get)


def _candidate(**overrides) -> Candidate:
    fields: dict = {
        "name": "QA Fixture University",
        "country": "Kazakhstan",
        "city": "Astana",
        "domain": "qa-fixture.example",
    }
    fields.update(overrides)
    return Candidate(**fields)


def _program(url: str | None) -> CandidateProgram:
    return CandidateProgram(
        name="BSc Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=url,
    )


async def _verify_against(monkeypatch, tmp_path, *, url: str, html: str):
    """Run the requirements adapter against one in-memory page."""
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {url: html})
        return await WebRequirementsAdapter(fetcher, "2026/27").verify(
            _candidate(admissions_url=url), _program(None), "fall 2027"
        )


async def _fetch_costs(monkeypatch, tmp_path, *, url: str, html: str):
    """Run the cost adapter against one in-memory page."""
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {url: html})
        return await WebCostAdapter(fetcher, "2026/27").fetch(_candidate(costs_url=url))


# ---------------------------------------------------------------------------
# A. Canary diagnostics: the run must be able to explain itself, per page.
#    All four tests are RED at baseline 1e9f841: the data is discarded or
#    reported without its category.
# ---------------------------------------------------------------------------

_PROGRAM_URL = "https://alpha-qa.example/programme/bsc-computer-science"
_NAV_URL = "https://alpha-qa.example/menu"
_NOPATTERN_URL = "https://beta-qa.example/how-to-apply"
_UNREADABLE_URL = "https://beta-qa.example/tuition"

#: Two institutions (distinct after key normalisation, which strips
#: "university"/"college") so one run covers all three page outcomes.
_CATALOG = [
    {
        "name": "Alpha QA Fixture University",
        "country": "Kazakhstan",
        "city": "Astana",
        "domain": "alpha-qa.example",
        "programs": [
            {
                "name": "BSc Computer Science",
                "field": "computer science",
                "degree": "bachelor",
                "url": _PROGRAM_URL,
            }
        ],
        "admissions_url": _NAV_URL,
    },
    {
        "name": "Beta QA Fixture College",
        "country": "Kazakhstan",
        "city": "Astana",
        "domain": "beta-qa.example",
        "programs": [
            {
                "name": "BSc Computer Science",
                "field": "computer science",
                "degree": "bachelor",
                "url": "https://beta-qa.example/programme/bsc-computer-science",
            }
        ],
        "admissions_url": _NOPATTERN_URL,
        "costs_url": _UNREADABLE_URL,
    },
]


def _pipeline_pages() -> dict[str, str]:
    return {
        "fixture://catalog.json": json.dumps(_CATALOG),
        _PROGRAM_URL: fixture("program_page_kzt.html"),
        "https://beta-qa.example/programme/bsc-computer-science": fixture("program_page_kzt.html"),
        _NAV_URL: fixture("navigation_shell.html"),
        _NOPATTERN_URL: fixture("admissions_no_patterns.html"),
        _UNREADABLE_URL: fixture("unreadable_js_shell.html"),
    }


async def _run_pipeline(monkeypatch, settings, profile: ApplicantProfileIn) -> dict:
    """Run the real pipeline over the synthetic pages and return the run row.

    The database is the run's own SQLite file; the pages are served in memory
    through the real Fetcher interface. Whatever the runner records on the run
    row is what a canary report could read afterwards. The interesting columns
    are materialised before the session closes.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import ApplicantProfileRow, Base, ResearchRun
    from app.pipeline.runner import ResearchRunner
    from app.pipeline.state import RunState
    from tests.conftest import TEST_ORGANIZATION_ID

    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
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
            candidate_limit=2,
            verify_limit=2,
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()

        fetcher = Fetcher(settings.cache_dir, delay_seconds=0.0, offline=True)
        _serve(monkeypatch, fetcher, _pipeline_pages())
        monkeypatch.setattr(ResearchRunner, "_make_fetcher", lambda self: fetcher)

        await ResearchRunner(session, run, profile, settings).run_to_decision()

        # Read back what was actually persisted, not what the live object
        # happens to carry: a canary in another process sees only the row.
        session.expire_all()
        stored = session.get(ResearchRun, run.id)
        assert stored is not None  # mypy: narrow ResearchRun | None
        return {
            "stage": stored.stage,
            "errors": list(stored.errors or []),
            "unknowns": list(stored.unknowns or []),
            "pages_checked": stored.pages_checked,
            "pages_failed": stored.pages_failed,
            "claims_recorded": stored.claims_recorded,
        }
    finally:
        session.close()
        engine.dispose()


def _persisted_diagnostics(run: dict) -> list[str]:
    return list(run["errors"]) + list(run["unknowns"])


class TestTheRunExplainsItsPages:
    @pytest.mark.asyncio
    async def test_a_read_page_leaves_its_page_type_on_the_run(
        self, monkeypatch, settings, profile
    ):
        """The programme page was read and classified - the run must keep that
        classification instead of dropping ``AdapterResult.page_types``."""
        run = await _run_pipeline(monkeypatch, settings, profile)
        diagnostics = _persisted_diagnostics(run)
        assert any(
            _PROGRAM_URL in d and ("intake_specific_program" in d or "program_detail" in d)
            for d in diagnostics
        ), (
            "the programme page was fetched and classified, but no diagnostic on the run "
            "records its page type; a report built from this run cannot say what the "
            "page was or why it produced what it did"
        )

    @pytest.mark.asyncio
    async def test_an_unreadable_page_is_named_as_unreadable(self, monkeypatch, settings, profile):
        """A 200 response with no extractable text is an adapter-level failure
        and must be reported as such, per page, not left unexplained."""
        run = await _run_pipeline(monkeypatch, settings, profile)
        diagnostics = _persisted_diagnostics(run)
        assert any(_UNREADABLE_URL in d and "unreadable" in d for d in diagnostics), (
            "the costs page returns HTTP 200 but no readable text; the run must record "
            "that page as unreadable (T18 acceptance: the report separates "
            "fetch-failed/unreadable/classifier-rejected/no-pattern-match)"
        )

    @pytest.mark.asyncio
    async def test_a_page_matching_no_pattern_is_reported_as_no_pattern_match(
        self, monkeypatch, settings, profile
    ):
        """A requirements page where no pattern matches must say so. Silence
        is how 35 pages turned into 0 claims with no explanation, and unknown
        must never quietly become zero."""
        run = await _run_pipeline(monkeypatch, settings, profile)
        diagnostics = _persisted_diagnostics(run)
        assert any(_NOPATTERN_URL in d and "no-pattern-match" in d for d in diagnostics), (
            "the admissions page was read and accepted by the requirement extractor "
            "but matched no pattern; the run must record a no-pattern-match outcome "
            "for that page"
        )

    @pytest.mark.asyncio
    async def test_a_classifier_rejected_page_is_named_as_such(
        self, monkeypatch, settings, profile
    ):
        """A link-heavy menu page is NAVIGATION and can answer nothing. The
        run must file it as classifier-rejected with the page kind named, so
        it is counted in the diagnosis instead of disappearing."""
        run = await _run_pipeline(monkeypatch, settings, profile)
        diagnostics = _persisted_diagnostics(run)
        assert any(
            _NAV_URL in d and "classifier-rejected" in d and "navigation" in d for d in diagnostics
        ), (
            "the admissions URL is a navigation shell; the run must record it as "
            "classifier-rejected (navigation) so the report counts pages the "
            "classifier refused, not only pages the fetcher failed on"
        )


# ---------------------------------------------------------------------------
# B1. KZT / tenge tuition figures. RED at baseline: _MONEY and
#     _CURRENCY_SYMBOLS know neither the tenge sign nor the KZT code, so the
#     money never becomes a claim and the page honest-fails with zero.
# ---------------------------------------------------------------------------


class TestKztTuitionVocabulary:
    def test_the_tenge_sign_is_read_as_kzt(self):
        assert parse_money("2 500 000 ₸") == (2500000.0, "KZT")

    def test_the_kzt_code_is_read_as_kzt(self):
        assert parse_money("2,500,000 KZT") == (2500000.0, "KZT")

    def test_a_tuition_line_in_tenge_yields_a_tuition_claim(self):
        builder = ClaimBuilder(source_url="https://qa-fixture.example/tuition")
        claims = extract_costs("Tuition fee: 2 500 000 ₸ в год", builder)
        tuition = [c for c in claims if c.claim_type is ClaimType.TUITION]
        assert tuition, "a stated tuition in tenge must produce a tuition claim"
        assert tuition[0].normalized_value == {"amount": 2500000.0, "currency": "KZT"}
        assert tuition[0].original_text_excerpt

    @pytest.mark.asyncio
    async def test_a_tenge_fees_page_yields_a_tuition_breakdown(self, monkeypatch, tmp_path):
        breakdown, result = await _fetch_costs(
            monkeypatch,
            tmp_path,
            url="https://qa-fixture.example/tuition",
            html=fixture("kzt_tuition_tenge.html"),
        )
        tuition = breakdown.items.get(CostCategory.TUITION)
        assert tuition is not None, (
            f"a page stating 'Tuition fee: 2 500 000 ₸ в год' produced no tuition "
            f"figure; adapter said: {result.errors}"
        )
        assert tuition.amount == 2500000.0
        assert tuition.currency == "KZT"

    @pytest.mark.asyncio
    async def test_a_kzt_code_fees_page_yields_a_tuition_breakdown(self, monkeypatch, tmp_path):
        breakdown, result = await _fetch_costs(
            monkeypatch,
            tmp_path,
            url="https://qa-fixture.example/tuition",
            html=fixture("kzt_tuition_code.html"),
        )
        tuition = breakdown.items.get(CostCategory.TUITION)
        assert tuition is not None, (
            f"a page stating 'Tuition fee: 2,500,000 KZT per year' produced no "
            f"tuition figure; adapter said: {result.errors}"
        )
        assert tuition.amount == 2500000.0
        assert tuition.currency == "KZT"

    def test_the_existing_currency_vocabulary_still_parses(self):
        """Widening the dictionary must not break what already worked."""
        assert parse_money("$20,000") == (20000.0, "USD")
        assert parse_money("€ 5 000") == (5000.0, "EUR")
        assert parse_money("5000 EUR") == (5000.0, "EUR")


# ---------------------------------------------------------------------------
# B2. "IELTS 6.5 overall" - the number may come before the keyword. RED at
#     baseline: _IELTS_OVERALL requires overall/minimum/score of/band between
#     "IELTS" and the number.
# ---------------------------------------------------------------------------


class TestIeltsOverallWordOrder:
    def test_ielts_before_overall_yields_the_band(self):
        builder = ClaimBuilder(source_url="https://qa-fixture.example/programme")
        claims = extract_requirements(
            "Applicants must present IELTS 6.5 overall (or equivalent).", builder
        )
        overall = [c for c in claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
        assert overall, (
            "'IELTS 6.5 overall (or equivalent)' is a stated overall band; it must "
            "produce an IELTS_MIN_OVERALL claim"
        )
        assert overall[0].normalized_value == 6.5
        assert overall[0].original_text_excerpt

    @pytest.mark.asyncio
    async def test_a_programme_page_stating_ielts_6_5_overall_yields_the_claim(
        self, monkeypatch, tmp_path
    ):
        html = fixture("ielts_overall_word_order.html")
        result = await _verify_against(
            monkeypatch,
            tmp_path,
            url="https://qa-fixture.example/programme/bsc-computer-science",
            html=html,
        )
        overall = [
            c
            for c in result.claims
            if c.claim_type is ClaimType.IELTS_MIN_OVERALL and c.normalized_value == 6.5
        ]
        assert overall, (
            "the page states 'IELTS 6.5 overall (or equivalent)'; the run must "
            f"produce an IELTS_MIN_OVERALL claim, got: {result.claims}"
        )
        # Evidence hygiene (same rule as the FP-3 regressions): the excerpt is
        # a real quote from the page, never a sentence the extractor wrote.
        page_text = " ".join(html_to_text(html).split()).lower()
        for claim in overall:
            assert " ".join(claim.original_text_excerpt.split()).lower() in page_text


# ---------------------------------------------------------------------------
# C. Precision guards. GREEN at baseline and required to stay green: widening
#    the dictionary or the diagnostics must not create claims or categories
#    the page does not state. unknown ≠ zero.
# ---------------------------------------------------------------------------


class TestPrecisionGuards:
    def test_a_scholarship_amount_is_not_a_tuition(self):
        builder = ClaimBuilder(source_url="https://qa-fixture.example/aid")
        claims = extract_costs("Scholarship of $500 per semester for admitted students.", builder)
        assert not [c for c in claims if c.claim_type is ClaimType.TUITION], (
            "a scholarship award must never be read as a tuition cost"
        )
        assert parse_money("$500") == (500.0, "USD"), (
            "the money parser may see the figure; the cost extractor must not "
            "attach it to a tuition claim"
        )

    @pytest.mark.asyncio
    async def test_a_page_mentioning_only_a_scholarship_yields_no_cost_items(
        self, monkeypatch, tmp_path
    ):
        breakdown, _ = await _fetch_costs(
            monkeypatch,
            tmp_path,
            url="https://qa-fixture.example/aid",
            html=fixture("scholarship_not_tuition.html"),
        )
        assert breakdown.items == {} and breakdown.total is None

    def test_ielts_without_a_number_yields_no_claim(self):
        builder = ClaimBuilder(source_url="https://qa-fixture.example/programme")
        claims = extract_requirements(
            "The programme accepts IELTS for admission to the bachelor.", builder
        )
        assert not [
            c
            for c in claims
            if c.claim_type in (ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE)
        ], "a mention of IELTS with no band must not invent one"

    @pytest.mark.asyncio
    async def test_a_page_that_states_no_requirement_stays_unresolved_and_never_zero(
        self, monkeypatch, tmp_path
    ):
        """unknown ≠ zero: no invented absence, and a reason on the record."""
        result = await _verify_against(
            monkeypatch,
            tmp_path,
            url="https://qa-fixture.example/how-to-apply",
            html=fixture("admissions_no_patterns.html"),
        )
        english = [
            c
            for c in result.claims
            if c.claim_type
            in (
                ClaimType.IELTS_MIN_OVERALL,
                ClaimType.IELTS_MIN_SUBSCORE,
                ClaimType.TOEFL_MIN_TOTAL,
                ClaimType.DUOLINGO_MIN,
            )
        ]
        assert not english, "nothing on the page states a test score; none may be claimed"
        assert result.errors, (
            "a page that answers nothing must leave a diagnostic with a reason, never a silent zero"
        )
        assert any("how-to-apply" in e for e in result.errors), (
            "the diagnostic must name the page it is about"
        )
