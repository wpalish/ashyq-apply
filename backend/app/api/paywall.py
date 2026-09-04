"""One place that answers: may this request see the paid material?

Routes call ``require_full_access``. Nothing else in the API decides this, so
the rule cannot drift between endpoints.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.tenancy import owned_run
from app.config import get_settings
from app.payments.entitlements import has_full_access
from app.payments.http import PaymentRequired
from app.security import Principal


def access_for_run(session: Session, run_id: str, principal: Principal) -> tuple[str, bool]:
    """The case behind a run, and whether it is unlocked.

    Ownership is checked here too, so a caller cannot skip it by asking about
    access instead of asking for the run.
    """
    run = owned_run(session, run_id, principal)
    return run.profile_id, has_full_access(session, principal.organization_id, run.profile_id)


def require_full_access(session: Session, run_id: str, principal: Principal) -> None:
    profile_id, allowed = access_for_run(session, run_id, principal)
    if not allowed:
        raise PaymentRequired(profile_id, get_settings().case_unlock_price_kzt)
