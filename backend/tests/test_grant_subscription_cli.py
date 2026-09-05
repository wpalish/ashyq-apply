"""Granting a subscription after a school pays its invoice."""

from __future__ import annotations

import pytest

from app.models.subscription import Subscription, SubscriptionStatus
from scripts.grant_subscription import cancel, grant, listing


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    """With payments off, has_full_access says yes to everything."""
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def test_a_grant_lands_pending_and_records_the_invoice(pg_session, org) -> None:
    sub = grant(pg_session, org_slug="test-school", cases=50, days=365, invoice="Договор 14/26")
    pg_session.flush()
    assert sub.status == SubscriptionStatus.PENDING.value
    assert sub.case_quota == 50
    assert sub.duration_days == 365
    assert sub.invoice_note == "Договор 14/26"
    assert sub.starts_at is None


def test_omitting_the_case_count_means_unlimited(pg_session, org) -> None:
    sub = grant(pg_session, org_slug="test-school", cases=None, days=365, invoice="")
    pg_session.flush()
    assert sub.case_quota is None


def test_an_unknown_organization_is_refused(pg_session) -> None:
    with pytest.raises(LookupError):
        grant(pg_session, org_slug="no-such-school", cases=10, days=30, invoice="")


def test_a_grant_writes_an_audit_event(pg_session, org) -> None:
    from app.models import AuditEvent

    grant(pg_session, org_slug="test-school", cases=10, days=30, invoice="")
    pg_session.flush()
    actions = [e.action for e in pg_session.query(AuditEvent).all()]
    assert "subscription_granted" in actions


def test_listing_reports_what_a_school_holds(pg_session, org) -> None:
    grant(pg_session, org_slug="test-school", cases=50, days=365, invoice="A")
    pg_session.flush()
    lines = listing(pg_session, org_slug="test-school")
    assert len(lines) == 1
    assert "test-school" in lines[0]
    assert "pending" in lines[0]


def test_cancelling_marks_it_cancelled(pg_session, org) -> None:
    sub = grant(pg_session, org_slug="test-school", cases=50, days=365, invoice="")
    pg_session.flush()
    assert cancel(pg_session, sub.id) is True
    pg_session.flush()
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELLED.value


def test_cancelling_something_that_does_not_exist_reports_it(pg_session) -> None:
    assert cancel(pg_session, "0" * 32) is False


def test_a_cancelled_subscription_is_never_spent(pg_session, org) -> None:
    from app.models import ApplicantProfileRow
    from app.payments.subscriptions import consume_for_case

    sub = grant(pg_session, org_slug="test-school", cases=5, days=365, invoice="")
    pg_session.flush()
    cancel(pg_session, sub.id)
    pg_session.flush()

    case = ApplicantProfileRow(organization_id=org.id, payload={})
    pg_session.add(case)
    pg_session.flush()
    assert consume_for_case(pg_session, organization_id=org.id, profile_id=case.id).granted is False
    assert pg_session.query(Subscription).one().status == SubscriptionStatus.CANCELLED.value
