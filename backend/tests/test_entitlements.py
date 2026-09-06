"""Who may see what, and exactly what a free row withholds."""

from __future__ import annotations

import pytest

from app.models.billing import Entitlement, EntitlementSource
from app.payments.entitlements import (
    free_view,
    grant_case_access,
    has_full_access,
    truncate_shortlist,
)
from app.schemas.result import ProgramResult


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    """Without this the answer is always yes, and these tests prove nothing."""
    from app.config import Settings, get_settings

    settings = Settings(payments_enabled=True)
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.payments.entitlements.get_settings", lambda: settings)
    yield
    get_settings.cache_clear()


@pytest.fixture
def tenant(pg_session):
    from app.models import ApplicantProfileRow, Organization

    org = Organization(name="Test org", slug="test-org")
    pg_session.add(org)
    pg_session.flush()
    case = ApplicantProfileRow(organization_id=org.id, payload={})
    pg_session.add(case)
    pg_session.flush()
    return {"organization_id": org.id, "profile_id": case.id}


def _result(index: int = 0) -> ProgramResult:
    return ProgramResult(
        id=f"r{index}",
        run_id="run1",
        university="Test University",
        university_id="u1",
        country="Netherlands",
        city="Delft",
        program="Computer Science",
        degree="bachelor",
        intake="fall 2027",
        source_urls=["https://example.edu/a", "https://example.edu/b"],
        career_notes="Strong graduate outcomes.",
    )


def test_no_entitlement_means_no_access(pg_session, tenant) -> None:
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is False


def test_granting_makes_access_true(pg_session, tenant) -> None:
    grant_case_access(
        pg_session,
        organization_id=tenant["organization_id"],
        profile_id=tenant["profile_id"],
        order_id=None,
        source=EntitlementSource.PURCHASE.value,
    )
    pg_session.flush()
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True


def test_granting_twice_grants_once(pg_session, tenant) -> None:
    for _ in range(2):
        grant_case_access(
            pg_session,
            organization_id=tenant["organization_id"],
            profile_id=tenant["profile_id"],
            order_id=None,
            source=EntitlementSource.PURCHASE.value,
        )
        pg_session.flush()
    assert pg_session.query(Entitlement).count() == 1


def test_another_organization_is_not_covered(pg_session, tenant) -> None:
    from app.models import Organization

    grant_case_access(
        pg_session,
        organization_id=tenant["organization_id"],
        profile_id=tenant["profile_id"],
        order_id=None,
        source=EntitlementSource.MANUAL.value,
    )
    other = Organization(name="Other org", slug="other-org")
    pg_session.add(other)
    pg_session.flush()
    assert has_full_access(pg_session, other.id, tenant["profile_id"]) is False


def test_a_subscription_no_longer_grants_blanket_access(pg_session, tenant) -> None:
    """Phase 2 turned the subscription into a right to spend, not access."""
    from app.models.subscription import Subscription

    pg_session.add(
        Subscription(organization_id=tenant["organization_id"], case_quota=50, duration_days=365)
    )
    pg_session.flush()
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is False


def test_a_free_row_keeps_identity_and_drops_evidence() -> None:
    free = free_view(_result())
    assert free.university == "Test University"
    assert free.program == "Computer Science"
    assert free.country == "Netherlands"
    assert free.degree == "bachelor"
    # Everything a buyer is paying for is gone.
    assert free.source_urls == []
    assert free.claims == []
    assert free.scholarships == []
    assert free.requirement_checks == []
    assert free.conflicts == []
    assert free.unresolved == []
    assert free.funding_gap is None
    assert free.career_notes == ""


def test_the_projection_does_not_mutate_its_input() -> None:
    original = _result()
    free_view(original)
    assert original.source_urls == ["https://example.edu/a", "https://example.edu/b"]
    assert original.career_notes == "Strong graduate outcomes."


def test_the_shortlist_is_cut_to_the_free_limit() -> None:
    rows = [_result(i) for i in range(12)]
    assert len(truncate_shortlist(rows, 5)) == 5
    assert truncate_shortlist(rows, 5)[0].id == "r0"


def test_a_shorter_shortlist_is_left_alone() -> None:
    rows = [_result(i) for i in range(3)]
    assert len(truncate_shortlist(rows, 5)) == 3


def test_with_payments_disabled_everything_is_visible(pg_session, tenant, monkeypatch) -> None:
    from app.config import Settings

    off = Settings(payments_enabled=False)
    monkeypatch.setattr("app.payments.entitlements.get_settings", lambda: off)
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True
