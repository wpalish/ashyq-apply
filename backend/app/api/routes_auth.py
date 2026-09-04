"""Account and organization session endpoints."""

from __future__ import annotations

import re
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import AuthSession, Organization, OrganizationMembership, User
from app.security import (
    Principal,
    clear_session_cookie,
    create_session,
    get_optional_principal,
    get_principal,
    hash_password,
    normalize_email,
    token_hash,
    verify_password,
)

#: A real scrypt hash of a value nobody holds. Verifying against it costs the
#: same as verifying a genuine one, which is the point: an unknown email must
#: not answer faster than a known one.
DUMMY_PASSWORD_HASH = hash_password("no account holds this password value")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    organization_name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class PrincipalView(BaseModel):
    user_id: str
    email: str
    display_name: str
    organization_id: str
    organization_name: str
    role: str
    local_development: bool


def _slug(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:50] or "workspace"
    from app.models.base import new_id

    return f"{base}-{new_id()[:8]}"


def _view(session: Session, principal: Principal) -> PrincipalView:
    org = session.get(Organization, principal.organization_id)
    return PrincipalView(**vars(principal), organization_name=org.name if org else "Workspace")


@router.get("/status")
def auth_status(
    principal: Principal | None = Depends(get_optional_principal),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    return {
        "enabled": settings.auth_enabled,
        "registration_enabled": settings.auth_registration_enabled,
        "authenticated": principal is not None,
        "principal": _view(session, principal).model_dump() if principal else None,
    }


@router.post("/register", response_model=PrincipalView, status_code=201)
def register(
    payload: RegisterIn,
    response: Response,
    session: Session = Depends(get_session),
) -> PrincipalView:
    settings = get_settings()
    if not settings.auth_enabled or not settings.auth_registration_enabled:
        raise HTTPException(403, "Registration is disabled.")
    # These validators raise ValueError, and their messages are written for the
    # person typing. Converting here, rather than through a global handler,
    # keeps an unexpected ValueError elsewhere a 500 where it belongs.
    try:
        email = normalize_email(payload.email)
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if session.query(User.id).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists.")
    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=password_hash,
    )
    org = Organization(
        name=payload.organization_name.strip(), slug=_slug(payload.organization_name)
    )
    session.add_all([user, org])
    session.flush()
    session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role="owner"))
    session.commit()
    create_session(session, user, org.id, response)
    return PrincipalView(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        organization_id=org.id,
        organization_name=org.name,
        role="owner",
        local_development=False,
    )


@router.post("/login", response_model=PrincipalView)
def login(
    payload: LoginIn,
    response: Response,
    session: Session = Depends(get_session),
) -> PrincipalView:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(403, "Authentication is disabled in local development mode.")
    try:
        email = normalize_email(payload.email)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Per-address limiting is in the middleware, but an attacker rotating
    # addresses walks straight past it while pounding one account. The account
    # itself therefore carries a budget too. In-memory and per-process: it
    # slows credential stuffing, it is not a distributed quota.
    from app.main import _limiter

    if not _limiter.allow(f"auth:email:{email}", settings.auth_rate_limit_per_minute, monotonic()):
        raise HTTPException(
            429, "Too many sign-in attempts for this account. Try again in a minute."
        )

    user = session.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        # Hash something anyway. Returning early for an unknown address makes
        # the response measurably faster, which turns login into an oracle for
        # which emails hold an account.
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(401, "Invalid email or password.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    membership = (
        session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .order_by(OrganizationMembership.created_at)
        .first()
    )
    if membership is None:
        raise HTTPException(403, "This account has no active workspace.")
    create_session(session, user, membership.organization_id, response)
    principal = Principal(
        user_id=user.id,
        organization_id=membership.organization_id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )
    return _view(session, principal)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> Response:
    raw = request.cookies.get(get_settings().session_cookie_name)
    if raw:
        auth_session = (
            session.query(AuthSession).filter(AuthSession.token_hash == token_hash(raw)).first()
        )
        if auth_session:
            session.delete(auth_session)
            session.commit()
    clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=PrincipalView)
def me(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PrincipalView:
    return _view(session, principal)
