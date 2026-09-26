"""Every production adapter hands the verifier its context (adversarial review, 2026-09-25).

A ``ClaimBuilder`` evaluates only the checks whose context it was given, so an
adapter that passed no page text skipped the verbatim check for every claim
without a word. These tests record what each adapter passes.
"""

from __future__ import annotations

import pytest

from app.adapters import extraction
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.extraction import verification_domains
from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import DegreeLevel

_CANDIDATE = Candidate(
    name="Delft University of Technology",
    country="Netherlands",
    city="Delft",
    domain="tudelft.nl",
    admissions_url="fixture://tu-delft/admissions.html",
)
_PROGRAM = CandidateProgram(
    name="BSc CSE",
    field="cs",
    degree=DegreeLevel.BACHELOR,
    url="fixture://tu-delft/program-0.html",
)


@pytest.fixture
def builders(monkeypatch):
    seen: list[extraction.ClaimBuilder] = []
    original = extraction.ClaimBuilder.__init__

    def init(self, **kwargs):
        original(self, **kwargs)
        seen.append(self)

    monkeypatch.setattr(extraction.ClaimBuilder, "__init__", init)
    return seen


def test_verification_domains():
    assert verification_domains("https://www.tudelft.nl/x", "tudelft.nl") == ("tudelft.nl",)
    assert verification_domains("fixture://tu-delft/x", "tudelft.nl") == ()
    assert verification_domains("https://www.tudelft.nl/x", None) == ()


@pytest.mark.asyncio
async def test_requirements_builders_carry_page_text_and_type(settings, corpus_dir, builders):
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
        await WebRequirementsAdapter(f, "2026/27").verify(_CANDIDATE, _PROGRAM, "fall 2027")
    assert builders
    assert all(b.page_text for b in builders)
    assert all(b.page_type for b in builders)


@pytest.mark.asyncio
async def test_cost_builders_carry_page_text(settings, corpus_dir, builders):
    candidate = Candidate(
        name="EPFL", country="Switzerland", city="Lausanne", costs_url="fixture://epfl/costs.html"
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
        await WebCostAdapter(f, "2026/27").fetch(candidate)
    assert builders
    assert all(b.page_text for b in builders)


def test_a_claim_not_on_its_page_is_now_rejected():
    builder = extraction.ClaimBuilder(
        source_url="https://www.tudelft.nl/x",
        official_domain=True,
        page_text="IELTS overall 6.5",
        allowed_domains=("tudelft.nl",),
    )
    assert builder.add(extraction.ClaimType.IELTS_MIN_OVERALL, 7.0, "IELTS overall 7.0") is None
    assert builder.rejected


def test_a_row_degree_overrides_the_page_scope_degree():
    """Run 76: HKU's undergraduate page was scoped 'master' from a stray mention."""
    from app.domain.claim_scope import ClaimScope

    builder = extraction.ClaimBuilder(
        source_url="https://www.hku.hk/x", scope=ClaimScope(degree="master")
    )
    claim = builder.add(
        extraction.ClaimType.PROGRAM_EXISTS, {"program": "BEng CS"}, "BEng CS", degree="bachelor"
    )
    assert claim is not None and claim.scope.degree == "bachelor"
    assert builder.meta["scope"].degree == "master"
