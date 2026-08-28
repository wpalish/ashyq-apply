"""How old a verified fact may be before it stops being trustworthy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.enums import ClaimStatus, ClaimType

#: Deadlines and prices move every cycle; a policy page moves rarely.
MAX_AGE_DAYS: dict[ClaimType, int] = {
    ClaimType.ADMISSION_DEADLINE: 30,
    ClaimType.SCHOLARSHIP_DEADLINE: 30,
    ClaimType.INTAKE_OPEN: 30,
    ClaimType.TUITION: 120,
    ClaimType.TOTAL_COST_OF_ATTENDANCE: 120,
    ClaimType.HOUSING_COST: 120,
    ClaimType.MEALS_COST: 120,
    ClaimType.SCHOLARSHIP_AMOUNT: 120,
}
DEFAULT_MAX_AGE_DAYS = 180


def max_age_days(claim_type: ClaimType) -> int:
    return MAX_AGE_DAYS.get(claim_type, DEFAULT_MAX_AGE_DAYS)


def age_days(accessed_at: datetime, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    if accessed_at.tzinfo is None:
        accessed_at = accessed_at.replace(tzinfo=UTC)
    return max(0, (now - accessed_at).days)


def is_stale(claim_type: ClaimType, accessed_at: datetime, now: datetime | None = None) -> bool:
    return age_days(accessed_at, now) > max_age_days(claim_type)


def apply_freshness(status: ClaimStatus, claim_type: ClaimType, accessed_at: datetime,
                    now: datetime | None = None) -> ClaimStatus:
    """Downgrade a current claim to POSSIBLY_STALE once it ages out."""
    if status == ClaimStatus.VERIFIED_CURRENT and is_stale(claim_type, accessed_at, now):
        return ClaimStatus.POSSIBLY_STALE
    return status


def next_recheck_at(claim_type: ClaimType, accessed_at: datetime) -> datetime:
    if accessed_at.tzinfo is None:
        accessed_at = accessed_at.replace(tzinfo=UTC)
    return accessed_at + timedelta(days=max_age_days(claim_type))
