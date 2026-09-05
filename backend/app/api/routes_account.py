"""Account management: password change and reset, workspaces, deletion.

Separate from routes_auth, which is about getting in and out. These are the
flows a person needs *after* they have an account, and every one of them was
missing: there was no way to change a password, no way back in after losing
one, no way to leave, and no way to reach a second workspace.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import PrincipalView, _view
from app.config import get_settings
from app.db import get_session
from app.mail import Message, get_sender
from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    AuthSession,
    Organization,
    OrganizationMembership,
    PasswordResetToken,
    User,
)
from app.models.base import ensure_utc
from app.security import (
    Principal,
    clear_session_cookie,
    create_session,
    get_principal,
    hash_password,
    normalize_email,
    token_hash,
    verify_password,
)

log = logging.getLogger("unimatch.account")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordResetRequestIn(BaseModel):
    email: str = Field(max_length=320)


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=12, max_length=128)


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    #: Required once the account owns applicant data. A session cookie is not
    #: consent to destroy someone's research.
    confirm_delete_data: bool = False


class OrganizationView(BaseModel):
    id: str
    name: str
    role: str
    current: bool


class SwitchOrganizationIn(BaseModel):
    organization_id: str


def _limiter_allows(key: str, limit: int) -> bool:
    # Imported at call time: app.main imports this module, and the tests
    # replace the limiter instance wholesale.
    from app.main import _limiter

    return _limiter.allow(key, limit, monotonic())


def _client_address(request: Request) -> str:
    from app.main import client_address

    return client_address(request)


@router.post("/password", response_model=PrincipalView)
def change_password(
    payload: PasswordChangeIn,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PrincipalView:
    """Change the password, then revoke every other session.

    People change a password when they think someone else has it. Leaving the
    other sessions alive would defeat the point of the exercise.
    """
    user = session.get(User, principal.user_id)
    if user is None or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "The current password is not correct.")
    try:
        user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    raw = request.cookies.get(get_settings().session_cookie_name)
    kept = token_hash(raw) if raw else ""
    revoked = (
        session.query(AuthSession)
        .filter(AuthSession.user_id == user.id, AuthSession.token_hash != kept)
        .delete(synchronize_session=False)
    )
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="password_changed",
            entity_type="user",
            entity_id=user.id,
            detail={"sessions_revoked": revoked},
        )
    )
    session.commit()
    return _view(session, principal)


@router.post("/password/reset-request", status_code=202)
def request_password_reset(
    payload: PasswordResetRequestIn,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Start a reset. The answer never reveals whether the account exists.

    Outside production the response carries the link, because the console
    sender only writes it to a log; in production that field is never present.
    """
    settings = get_settings()
    address = _client_address(request)
    if not _limiter_allows(f"reset:{address}", settings.auth_rate_limit_per_minute):
        raise HTTPException(429, "Too many reset requests. Try again in a minute.")

    answer: dict = {"detail": "If that email has an account, a reset link is on its way."}
    try:
        email = normalize_email(payload.email)
    except ValueError:
        return answer  # an address that cannot exist has no account either

    if not _limiter_allows(f"reset:email:{email}", settings.auth_rate_limit_per_minute):
        raise HTTPException(429, "Too many reset requests for this account.")

    user = session.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return answer

    raw = secrets.token_urlsafe(32)
    # One live token per account: requesting a new link invalidates the old.
    session.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).delete(synchronize_session=False)
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.password_reset_ttl_minutes),
            requested_ip=address[:64],
        )
    )
    link = f"{settings.public_base_url.rstrip('/')}/#/reset?token={raw}"
    get_sender(settings).send(
        Message(
            to=user.email,
            subject="Reset your ASHYQ Apply password",
            body=(
                "Someone asked to reset the password for this account.\n\n"
                f"{link}\n\n"
                f"The link works once and expires in {settings.password_reset_ttl_minutes} "
                "minutes. If it was not you, nothing has changed and you can ignore this."
            ),
        )
    )
    session.add(
        AuditEvent(
            organization_id=_first_organization(session, user.id) or "",
            actor="system",
            action="password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            detail={},
        )
    )
    session.commit()
    if not settings.is_production:
        answer["reset_link"] = link
    return answer


@router.post("/password/reset", response_model=PrincipalView)
def confirm_password_reset(
    payload: PasswordResetConfirmIn,
    response: Response,
    session: Session = Depends(get_session),
) -> PrincipalView:
    """Redeem a reset token exactly once, and sign the person back in."""
    now = datetime.now(UTC)
    token = (
        session.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash(payload.token))
        .first()
    )
    expires_at = ensure_utc(token.expires_at) if token is not None else None
    expired = expires_at is None or expires_at < now
    if token is None or token.used_at is not None or expired:
        # One message for every failure: expired, spent, or never existed.
        raise HTTPException(400, "This reset link is no longer valid. Request a new one.")

    user = session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(400, "This reset link is no longer valid. Request a new one.")
    try:
        user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    token.used_at = now
    # Every existing session dies with the old password: whoever forced the
    # reset must not keep a cookie from before it.
    session.query(AuthSession).filter(AuthSession.user_id == user.id).delete(
        synchronize_session=False
    )
    organization_id = _first_organization(session, user.id)
    if organization_id is None:
        raise HTTPException(403, "This account has no active workspace.")
    membership = session.get(OrganizationMembership, (user.id, organization_id))
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor="system",
            action="password_reset_completed",
            entity_type="user",
            entity_id=user.id,
            detail={},
        )
    )
    session.commit()
    create_session(session, user, organization_id, response)
    return _view(
        session,
        Principal(
            user_id=user.id,
            organization_id=organization_id,
            email=user.email,
            display_name=user.display_name,
            role=membership.role if membership else "owner",
        ),
    )


@router.get("/organizations", response_model=list[OrganizationView])
def list_organizations(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[OrganizationView]:
    rows = (
        session.query(OrganizationMembership, Organization)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .filter(OrganizationMembership.user_id == principal.user_id)
        .order_by(OrganizationMembership.created_at)
        .all()
    )
    return [
        OrganizationView(
            id=org.id,
            name=org.name,
            role=membership.role,
            current=org.id == principal.organization_id,
        )
        for membership, org in rows
    ]


@router.post("/session/organization", response_model=PrincipalView)
def switch_organization(
    payload: SwitchOrganizationIn,
    request: Request,
    response: Response,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PrincipalView:
    """Point this session at another workspace the user belongs to.

    The organization lives on the session row, so switching reissues the
    session. The membership is checked first: an organization id from the
    client is never taken on trust, which is what keeps tenant scoping honest.
    """
    membership = session.get(OrganizationMembership, (principal.user_id, payload.organization_id))
    if membership is None:
        # 404, not 403: do not confirm that a workspace this user is not in
        # even exists.
        raise HTTPException(404, "Workspace not found.")

    user = session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(401, "Authentication required.")

    raw = request.cookies.get(get_settings().session_cookie_name)
    if raw:
        session.query(AuthSession).filter(AuthSession.token_hash == token_hash(raw)).delete(
            synchronize_session=False
        )
    session.commit()
    create_session(session, user, payload.organization_id, response)
    return _view(
        session,
        Principal(
            user_id=user.id,
            organization_id=payload.organization_id,
            email=user.email,
            display_name=user.display_name,
            role=membership.role,
        ),
    )


@router.post("/me/delete", status_code=204)
def delete_account(
    payload: DeleteAccountIn,
    response: Response,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Erase the account and the workspaces only this person belongs to.

    Confirmed by password. Workspaces with another member survive; the ones
    this user alone holds are removed with their applicant cases, runs and
    claims - which is what the deletion promise in the product actually means.

    POST rather than DELETE because a body is required and several HTTP
    clients drop the body of a DELETE.
    """
    user = session.get(User, principal.user_id)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(400, "The password is not correct.")

    sole_owner_orgs = [
        membership.organization_id
        for membership in session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .all()
        if session.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == membership.organization_id,
            OrganizationMembership.user_id != user.id,
        )
        .count()
        == 0
    ]
    profiles = (
        session.query(ApplicantProfileRow)
        .filter(ApplicantProfileRow.organization_id.in_(sole_owner_orgs))
        .count()
        if sole_owner_orgs
        else 0
    )
    if profiles and not payload.confirm_delete_data:
        raise HTTPException(
            409,
            f"This account is the only member of a workspace holding {profiles} applicant "
            f"case(s). Send confirm_delete_data=true to erase them with the account.",
        )

    # Audited before the deletion: afterwards there is no organization left to
    # attach the record to.
    for organization_id in sole_owner_orgs:
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor=f"user:{user.id[:8]}",
                action="account_deleted",
                entity_type="user",
                entity_id=user.id,
                detail={"profiles_removed": profiles},
            )
        )
    session.commit()

    session.delete(user)
    for organization_id in sole_owner_orgs:
        # The ORM deletes the cases one by one rather than trusting the
        # database cascade: SQLite's foreign_keys pragma is per-connection and
        # easy to lose, and "the applicant's data is gone" is a promise, not a
        # best effort. Each profile takes its runs, results and claims with it.
        for profile in (
            session.query(ApplicantProfileRow)
            .filter(ApplicantProfileRow.organization_id == organization_id)
            .all()
        ):
            session.delete(profile)
        org = session.get(Organization, organization_id)
        if org is not None:
            session.delete(org)
    session.commit()

    clear_session_cookie(response)
    response.status_code = 204
    return response


def _first_organization(session: Session, user_id: str) -> str | None:
    membership = (
        session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user_id)
        .order_by(OrganizationMembership.created_at)
        .first()
    )
    return membership.organization_id if membership else None
