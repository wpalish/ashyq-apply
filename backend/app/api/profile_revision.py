"""Owned profile writes with an atomic revision precondition on both databases."""

from __future__ import annotations

from typing import cast

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.api.preparation_transactions import (
    begin_fresh_preparation_write,
    lock_owned_preparation_profile,
)
from app.models import ApplicantProfileRow, Organization
from app.models.base import utcnow
from app.schemas.profile import ApplicantProfileIn
from app.security import Principal


def begin_profile_write(
    session: Session, profile_id: str, principal: Principal, expected_revision: int | None
) -> ApplicantProfileRow:
    """Organization before profile; never insert an audit FK under a late lock."""
    begin_fresh_preparation_write(session)
    organization = (
        session.query(Organization.id)
        .filter(Organization.id == principal.organization_id)
        .with_for_update(read=True, key_share=True)
        .first()
    )
    if organization is None:
        session.rollback()
        raise HTTPException(401, "Authentication required.")
    row = lock_owned_preparation_profile(session, profile_id, principal)
    if expected_revision is None:
        session.rollback()
        raise HTTPException(428, "Reload the current profile before saving its changes.")
    if row.revision != expected_revision:
        revision = row.revision
        session.rollback()
        raise HTTPException(
            409,
            {
                "code": "profile_revision_conflict",
                "message": "This profile changed in another window. Keep your edits and compare the saved profile.",
                "current_revision": revision,
            },
        )
    return row


def store_profile_revision(
    session: Session, row: ApplicantProfileRow, profile: ApplicantProfileIn, expected_revision: int
) -> None:
    """One accepted name/payload/revision; a stale snapshot never overwrites it."""
    changed = cast(
        CursorResult,
        session.execute(
            update(ApplicantProfileRow)
            .where(
                ApplicantProfileRow.id == row.id,
                ApplicantProfileRow.organization_id == row.organization_id,
                ApplicantProfileRow.revision == expected_revision,
            )
            .values(
                payload=profile.model_dump(mode="json"),
                display_name=profile.display_name,
                revision=expected_revision + 1,
                updated_at=utcnow(),
            )
        ),
    )
    if changed.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "The saved profile changed. Keep your edits and reload it.")
    session.expire(row)
    session.refresh(row)
