"""Shared fixtures.

Every test runs against a temporary database and the bundled corpus, so no test
touches the network or the developer's working database.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from collections.abc import Iterator
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
def postgres_url() -> Iterator[str]:
    """A real PostgreSQL for the session.

    Provisioned in-process by `pgserver`, so nothing has to be installed. The
    schema work, the queue's SKIP LOCKED claim and the cascade constraints are
    all PostgreSQL-specific and are asserted against the real thing rather than
    against SQLite standing in for it.
    """
    pgserver = pytest.importorskip(
        "pgserver", reason="pgserver provides the local PostgreSQL used by these tests"
    )
    directory = Path(tempfile.mkdtemp(prefix="unimatch-pg-"))
    try:
        server = pgserver.get_server(str(directory))
    except Exception as exc:  # initdb refused: no cluster, so nothing to test against
        # The wheel installs on Windows but its initdb.exe does not run there.
        # That is an unavailable environment, not a failing product: skip, so a
        # developer's local suite is honest, while CI on Linux still provisions
        # a real PostgreSQL and asserts the SKIP LOCKED claim and the cascades.
        shutil.rmtree(directory, ignore_errors=True)
        pytest.skip(f"pgserver could not start a local PostgreSQL: {exc}")
    try:
        yield server.get_uri().replace("postgresql://", "postgresql+psycopg://")
    finally:
        server.cleanup()
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def pg_engine(postgres_url: str):
    """A migrated PostgreSQL database, isolated per test."""
    import sqlalchemy as sa

    from app.db import migrate_to_head

    name = f"t{uuid.uuid4().hex[:12]}"
    admin = sa.create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    admin.dispose()

    url = _swap_database(postgres_url, name)
    migrate_to_head(url)
    engine = sa.create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def _swap_database(url: str, name: str) -> str:
    """Point a libpq URL at a different database, keeping its query string."""
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{name}", parts.query, parts.fragment))


@pytest.fixture
def pg_session(pg_engine):
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=pg_engine, future=True)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Give every test its own abuse budget.

    The limiter is a per-process object keyed on the caller's address, and in
    the suite every test is the same caller. Without this, the twenty-first
    run started anywhere in the session gets a 429 and some unrelated test
    fails with a KeyError on a response body it never expected.
    """
    import app.main as main_module

    main_module._limiter.hits.clear()
    yield
    main_module._limiter.hits.clear()


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


#: The tenant test fixtures write into. Explicit, because the column no longer
#: carries a default: a caller that forgets the organization must fail loudly
#: rather than quietly writing into someone else's workspace.
TEST_ORGANIZATION_ID = "00000000000000000000000000000001"


def profile_row(session, profile, display_name: str = "t"):
    """An ApplicantProfileRow in a real organization, created if missing."""
    from app.models import ApplicantProfileRow, Organization

    if session.get(Organization, TEST_ORGANIZATION_ID) is None:
        session.add(
            Organization(id=TEST_ORGANIZATION_ID, name="Test workspace", slug="test-workspace")
        )
        session.flush()
    payload = profile if isinstance(profile, dict) else profile.model_dump(mode="json")
    row = ApplicantProfileRow(
        organization_id=TEST_ORGANIZATION_ID, display_name=display_name, payload=payload
    )
    session.add(row)
    session.flush()
    return row
