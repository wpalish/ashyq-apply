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
    server = pgserver.get_server(str(directory))
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


#: The secret the payment fixtures sign webhooks with. Tests that forge a
#: signature must use this exact value.
WEBHOOK_SECRET = "whsec-test"


@pytest.fixture
def paid_client(tmp_path, monkeypatch, corpus_dir):
    """An API client with payments switched on, behind the fake provider.

    Payments are configured through the environment, not by patching
    ``app.config.get_settings``. Modules bind that name at import time, so a
    patch reaches only modules imported after it — which made the outcome
    depend on which test module ran first. The environment reaches all of them.
    """
    from fastapi.testclient import TestClient

    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("UNIMATCH_PAYMENTS_PROVIDER", "fake")
    monkeypatch.setenv("UNIMATCH_APIPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'payments.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=True,
        payments_provider="fake",
        apipay_webhook_secret=WEBHOOK_SECRET,
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    reset_shared_fake()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from app.main import app

    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.fixture
def case_id(paid_client) -> str:
    """One applicant case owned by the paid client's tenant."""
    from app.corpus.demo_profile import DEMO_PROFILE

    return paid_client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()["id"]


def sign_webhook(body: bytes) -> str:
    """The signature ApiPay would send for this body."""
    import hashlib
    import hmac

    return "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
