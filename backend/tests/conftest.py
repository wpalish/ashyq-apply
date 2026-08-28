"""Shared fixtures.

Every test runs against a temporary database and the bundled corpus, so no test
touches the network or the developer's working database.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.schemas.claim import Claim
from app.schemas.profile import (
    AcademicRecord,
    ApplicantProfileIn,
    ApplicationContext,
    FundingNeeds,
    GradeValue,
    IeltsScore,
    Preferences,
    SatScore,
)

CORPUS = Path(__file__).resolve().parent.parent / "app" / "corpus" / "pages"


@pytest.fixture(scope="session")
def corpus_dir() -> Path:
    if not CORPUS.exists():
        from app.corpus.build import build

        build()
    return CORPUS


@pytest.fixture
def settings(tmp_path: Path, corpus_dir: Path) -> Settings:
    return Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        candidate_limit=40,
        verify_limit=20,
        academic_year="2026/27",
        target_currency="USD",
        enable_browser_tier=False,
    )


@pytest.fixture
def profile() -> ApplicantProfileIn:
    """The synthetic applicant. Sits on the interesting boundaries by design."""
    return ApplicantProfileIn(
        display_name="Test Applicant (synthetic)",
        context=ApplicationContext(
            level="bachelor",
            intended_fields=["computer science"],
            intake_term="fall",
            intake_year=2027,
            citizenship="Kazakhstan",
            country_of_residence="Kazakhstan",
            education_country="Kazakhstan",
            education_system="KZ national secondary",
            graduation_date="2027-05-25",
        ),
        academics=AcademicRecord(
            gpa=GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            # Overall clears most minimums; writing does not clear a 6.5 per-band rule.
            ielts=IeltsScore(overall=7.0, listening=7.5, reading=7.5, writing=6.0, speaking=7.0),
            sat=SatScore(total=1400, math=760, reading_writing=640),
        ),
        preferences=Preferences(preferred_countries=["Netherlands", "Canada"]),
        funding=FundingNeeds(max_annual_budget=6000, max_acceptable_gap=6000),
    )


def make_claim(
    claim_type: str,
    value: object,
    *,
    specificity: str = "program_intake",
    status: str = "VERIFIED_CURRENT",
    url: str = "https://example.edu/programme",
    program: str | None = None,
    subject_key: str | None = None,
    accessed_at: datetime | None = None,
    confidence: float = 0.8,
) -> Claim:
    return Claim(
        claim_type=ClaimType(claim_type),
        normalized_value=value,
        source_url=url,
        accessed_at=accessed_at or datetime.now(UTC),
        status=ClaimStatus(status),
        source_specificity=SourceSpecificity(specificity),
        program=program,
        subject_key=subject_key,
        confidence=confidence,
    )


@pytest.fixture
def claim_factory():
    return make_claim


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
