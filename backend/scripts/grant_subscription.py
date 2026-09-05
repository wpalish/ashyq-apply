"""Record a school subscription after its invoice is paid.

Money arrives by bank transfer against a contract raised outside the product,
so this is the whole of "billing" for a school: write down what was sold.

A grant always lands ``pending``. Activation belongs to ``consume_for_case``
and nowhere else, so there is one activation path rather than two that have to
agree — the term starts counting when the school opens its first case.

Usage::

    python scripts/grant_subscription.py --org <slug> --cases 50 --days 365 \\
        --invoice "Договор 14/26"
    python scripts/grant_subscription.py --list
    python scripts/grant_subscription.py --list --org <slug>
    python scripts/grant_subscription.py --cancel <subscription-id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Organization
from app.models.subscription import Subscription, SubscriptionStatus


def grant(
    session: Session, *, org_slug: str, cases: int | None, days: int, invoice: str
) -> Subscription:
    """Record a sold subscription. Refuses an organization it cannot find."""
    org = session.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None:
        raise LookupError(f"No organization with slug {org_slug!r}")

    subscription = Subscription(
        organization_id=org.id,
        case_quota=cases,
        duration_days=days,
        status=SubscriptionStatus.PENDING.value,
        invoice_note=invoice,
    )
    session.add(subscription)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=org.id,
            actor="cli",
            action="subscription_granted",
            entity_type="subscription",
            entity_id=subscription.id,
            detail={"cases": cases, "days": days, "invoice": invoice},
        )
    )
    return subscription


def listing(session: Session, org_slug: str | None = None) -> list[str]:
    """One readable line per subscription, oldest first."""
    from app.payments.subscriptions import quota_remaining

    query = select(Subscription, Organization).join(
        Organization, Organization.id == Subscription.organization_id
    )
    if org_slug:
        query = query.where(Organization.slug == org_slug)
    query = query.order_by(Subscription.created_at)

    lines = []
    for subscription, org in session.execute(query):
        remaining = quota_remaining(session, subscription)
        quota = "unlimited" if subscription.case_quota is None else str(subscription.case_quota)
        left = "-" if remaining is None else str(remaining)
        ends = subscription.ends_at.date().isoformat() if subscription.ends_at else "not started"
        lines.append(
            f"{subscription.id}  {org.slug:<20}  {subscription.status:<10}  "
            f"{left}/{quota} left  ends {ends}  {subscription.invoice_note}"
        )
    return lines


def cancel(session: Session, subscription_id: str) -> bool:
    """Cancel a subscription. False when there is no such row."""
    subscription = session.get(Subscription, subscription_id)
    if subscription is None:
        return False
    subscription.status = SubscriptionStatus.CANCELLED.value
    session.add(
        AuditEvent(
            organization_id=subscription.organization_id,
            actor="cli",
            action="subscription_cancelled",
            entity_type="subscription",
            entity_id=subscription.id,
            detail={},
        )
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a paid school subscription.")
    parser.add_argument("--org", help="organization slug")
    parser.add_argument("--cases", type=int, help="cases included; omit for unlimited")
    parser.add_argument("--days", type=int, default=365, help="term length in days")
    parser.add_argument("--invoice", default="", help="contract or invoice number")
    parser.add_argument("--list", action="store_true", help="show subscriptions")
    parser.add_argument("--cancel", help="cancel a subscription by id")
    args = parser.parse_args(argv)

    from app.db import session_scope

    with session_scope() as session:
        if args.cancel:
            if not cancel(session, args.cancel):
                print(f"No subscription {args.cancel}", file=sys.stderr)
                return 1
            print(f"Cancelled {args.cancel}")
            return 0

        if args.list:
            lines = listing(session, args.org)
            print("\n".join(lines) if lines else "No subscriptions.")
            return 0

        if not args.org:
            parser.error("--org is required when granting")
        subscription = grant(
            session,
            org_slug=args.org,
            cases=args.cases,
            days=args.days,
            invoice=args.invoice,
        )
        session.flush()
        quota = "unlimited" if args.cases is None else f"{args.cases} cases"
        print(f"Granted {subscription.id}: {quota} for {args.days} days, pending first use.")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
