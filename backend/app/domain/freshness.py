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


def _as_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime, convert an aware one. Pure."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def age_days(accessed_at: datetime, now: datetime | None = None) -> int:
    """Whole days since the evidence was read. Display only.

    The whole-day floor is deliberately kept out of the staleness decision:
    ``is_stale`` compares moments, not floored days, so a claim ages out the
    minute its window closes rather than a day later.
    """
    now = _as_utc(now) if now is not None else datetime.now(UTC)
    return max(0, (now - _as_utc(accessed_at)).days)


def is_stale(claim_type: ClaimType, accessed_at: datetime, now: datetime | None = None) -> bool:
    """Whether the evidence has aged out, at the inclusive boundary.

    Both operands are UTC-normalized, so a naive ``now`` cannot crash the
    subtraction and naive and aware callers get the same answer. A claim is
    stale once ``now - accessed_at`` reaches the window exactly — the previous
    ``age_days(...) > max_age_days`` read a 30-day-old claim as 30 > 30 and
    left it trusted for a whole extra day.
    """
    now_norm = _as_utc(now) if now is not None else datetime.now(UTC)
    return (now_norm - _as_utc(accessed_at)) >= timedelta(days=max_age_days(claim_type))


def apply_freshness(
    status: ClaimStatus, claim_type: ClaimType, accessed_at: datetime, now: datetime | None = None
) -> ClaimStatus:
    """Downgrade a current claim to POSSIBLY_STALE once it ages out.

    Only VERIFIED_CURRENT moves. Every other status passes through untouched —
    in particular SUPERSEDED, which is historical record rather than live
    evidence: however old it gets, freshness must never rewrite it.
    """
    if status == ClaimStatus.VERIFIED_CURRENT and is_stale(claim_type, accessed_at, now):
        return ClaimStatus.POSSIBLY_STALE
    return status


def next_recheck_at(claim_type: ClaimType, accessed_at: datetime) -> datetime:
    return _as_utc(accessed_at) + timedelta(days=max_age_days(claim_type))
