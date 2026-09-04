"""What an organization may see, and what a free row withholds.

Deliberately close to pure: one query, and one projection with no side effects.
The rules a customer is paying for should be readable in a single screen.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.billing import Entitlement, EntitlementKind, EntitlementSource
from app.schemas.result import ProgramResult


def has_full_access(session: Session, organization_id: str, profile_id: str) -> bool:
    """True when this organization may see everything about this case.

    With payments disabled the product is exactly what it was before this
    feature existed, so the answer is always yes.
    """
    if not get_settings().payments_enabled:
        return True

    found = session.scalar(
        select(Entitlement.id).where(
            Entitlement.organization_id == organization_id,
            or_(
                # This case, bought outright.
                (Entitlement.kind == EntitlementKind.CASE_FULL.value)
                & (Entitlement.profile_id == profile_id),
                # Or the whole organization, under a subscription (phase 2).
                (Entitlement.kind == EntitlementKind.ORG_SUBSCRIPTION.value)
                & (Entitlement.profile_id.is_(None)),
            ),
        )
    )
    return found is not None


def grant_case_access(
    session: Session,
    *,
    organization_id: str,
    profile_id: str,
    order_id: str | None,
    source: str = EntitlementSource.PURCHASE.value,
) -> Entitlement:
    """Idempotent: granting an entitlement that exists returns the existing one."""
    existing = session.scalar(
        select(Entitlement).where(
            Entitlement.organization_id == organization_id,
            Entitlement.profile_id == profile_id,
            Entitlement.kind == EntitlementKind.CASE_FULL.value,
        )
    )
    if existing is not None:
        return existing

    granted = Entitlement(
        organization_id=organization_id,
        profile_id=profile_id,
        kind=EntitlementKind.CASE_FULL.value,
        source=source,
        order_id=order_id,
    )
    session.add(granted)
    return granted


def free_view(result: ProgramResult) -> ProgramResult:
    """A copy of one row with the paid material removed.

    What survives is enough to know the programme exists and roughly how well
    it fits. Everything that took a fetch to establish is withheld.
    """
    trimmed = result.model_copy(deep=True)
    trimmed.source_urls = []
    trimmed.claims = []
    trimmed.scholarships = []
    trimmed.requirement_checks = []
    trimmed.missing_prerequisites = []
    trimmed.hard_filter_failures = []
    trimmed.conflicts = []
    trimmed.unresolved = []
    trimmed.funding_gap = None
    trimmed.checklist = None
    trimmed.career_notes = ""
    trimmed.post_study_work = ""
    trimmed.work_during_study = ""
    trimmed.admission_deadline_raw = None
    trimmed.verification_completeness = 0.0
    return trimmed


def truncate_shortlist(results: list[ProgramResult], limit: int) -> list[ProgramResult]:
    """The highest-scoring rows only. The list arrives already ordered."""
    return results[:limit]
