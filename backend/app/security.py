"""Authentication, tenant principals and request-level security controls."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import AuthSession, Organization, OrganizationMembership, User
from app.models.base import ensure_utc

DEV_ORGANIZATION_ID = "00000000000000000000000000000001"
DEV_USER_ID = "00000000000000000000000000000002"
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_cookie_scheme = APIKeyCookie(name="unimatch_session", auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: str
    organization_id: str
    email: str
    display_name: str
    role: str
    local_development: bool = False


def normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if len(email) > 320 or not _EMAIL.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    return email


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if len(password) > 128:
        raise ValueError("Password must contain at most 128 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_development_principal(session: Session) -> Principal:
    """Create the explicit single local tenant used only when auth is disabled."""
    org = session.get(Organization, DEV_ORGANIZATION_ID)
    if org is None:
        org = Organization(
            id=DEV_ORGANIZATION_ID, name="Local development workspace", slug="local-development"
        )
        session.add(org)
    user = session.get(User, DEV_USER_ID)
    if user is None:
        user = User(
            id=DEV_USER_ID,
            email="local@unimatch.invalid",
            display_name="Local user",
            password_hash="disabled",
        )
        session.add(user)
    membership = session.get(OrganizationMembership, (DEV_USER_ID, DEV_ORGANIZATION_ID))
    if membership is None:
        session.add(
            OrganizationMembership(
                user_id=DEV_USER_ID, organization_id=DEV_ORGANIZATION_ID, role="owner"
            )
        )
    session.commit()
    return Principal(
        user_id=DEV_USER_ID,
        organization_id=DEV_ORGANIZATION_ID,
        email=user.email,
        display_name=user.display_name,
        role="owner",
        local_development=True,
    )


def create_session(session: Session, user: User, organization_id: str, response: Response) -> None:
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    session.add(
        AuthSession(
            user_id=user.id,
            organization_id=organization_id,
            token_hash=token_hash(raw),
            expires_at=expires,
        )
    )
    session.commit()
    response.set_cookie(
        settings.session_cookie_name,
        raw,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def get_optional_principal(
    request: Request,
    raw_cookie: str | None = Security(_cookie_scheme),
    session: Session = Depends(get_session),
) -> Principal | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return ensure_development_principal(session)
    raw = (
        raw_cookie
        if settings.session_cookie_name == "unimatch_session"
        else request.cookies.get(settings.session_cookie_name)
    )
    if not raw:
        return None
    auth_session = (
        session.query(AuthSession).filter(AuthSession.token_hash == token_hash(raw)).first()
    )
    now = datetime.now(UTC)
    if auth_session is None or (ensure_utc(auth_session.expires_at) or now) <= now:
        if auth_session is not None:
            session.delete(auth_session)
            session.commit()
        return None
    user = session.get(User, auth_session.user_id)
    membership = session.get(
        OrganizationMembership, (auth_session.user_id, auth_session.organization_id)
    )
    if user is None or not user.is_active or membership is None:
        return None
    if (now - (ensure_utc(auth_session.last_seen_at) or now)) > timedelta(minutes=15):
        auth_session.last_seen_at = now
        session.commit()
    return Principal(
        user_id=user.id,
        organization_id=auth_session.organization_id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )


def get_principal(principal: Principal | None = Depends(get_optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return principal
