"""Profile command acceptance reuses append-only audit identity, never profile copies.

The audit PK is a globally unique canonical UUID. Its immutable detail binds the
entire normalized request and exact actor/workspace. A replay returns metadata
plus the *current* owned profile, so an old ACK cannot restore historical PII.
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.preparation_transactions import begin_fresh_preparation_write
from app.models import ApplicantProfileRow, AuditEvent, Organization, OrganizationMembership, User
from app.schemas.profile import ApplicantProfile, ProfileWriteReceipt
from app.security import Principal


def begin_profile_creation(session: Session, principal: Principal) -> None:
    begin_fresh_preparation_write(session)
    org = (
        session.query(Organization.id)
        .filter(Organization.id == principal.organization_id)
        .with_for_update(read=True, key_share=True)
        .first()
    )
    actor = (
        session.query(User.id)
        .filter(User.id == principal.user_id, User.is_active.is_(True))
        .first()
    )
    membership = (
        session.query(OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.user_id == principal.user_id,
            OrganizationMembership.organization_id == principal.organization_id,
        )
        .first()
    )
    if org is None or actor is None or membership is None:
        session.rollback()
        raise HTTPException(401, "Authentication required.")


def command_binding(
    kind: str,
    body: dict,
    *,
    target: str | None,
    expected_revision: int | None,
    creation_identity: str | None = None,
) -> str:
    canonical = json.dumps(
        {
            "v": 1,
            "kind": kind,
            "body": body,
            "target": target,
            "expected_revision": expected_revision,
            "creation_identity": creation_identity,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def accepted_command(
    session: Session, key: UUID | None, principal: Principal, digest: str
) -> AuditEvent | None:
    if key is None:
        return None  # bounded legacy compatibility, no replay promise
    event = session.get(AuditEvent, key.hex)
    if event is None:
        return None
    detail = event.detail
    if (
        event.organization_id != principal.organization_id
        or detail.get("profile_command_version") != 1
        or detail.get("actor_id") != principal.user_id
        or detail.get("digest") != digest
    ):
        session.rollback()
        raise HTTPException(409, "This command identity is already bound to a different request.")
    return event


def command_event(
    principal: Principal,
    key: UUID | None,
    kind: str,
    profile_id: str,
    digest: str,
    expected_revision: int | None,
    accepted_revision: int,
    *,
    run_id: str | None = None,
    outcome: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=principal.organization_id,
        actor=f"user:{principal.user_id[:8]}",
        action={
            "create": "profile_created",
            "update": "profile_updated",
            "persisted_rerank": "results_reranked",
        }[kind],
        entity_type="run" if run_id else "profile",
        entity_id=run_id or profile_id,
        detail={}
        if key is None
        else {
            "profile_command_version": 1,
            "command_id": str(key),
            "kind": kind,
            "actor_id": principal.user_id,
            "profile_id": profile_id,
            "digest": digest,
            "expected_revision": expected_revision,
            "accepted_revision": accepted_revision,
            "outcome": outcome or {},
        },
    )
    if key is not None:
        event.id = key.hex
    return event


def receipt(event: AuditEvent | None) -> ProfileWriteReceipt | None:
    if event is None or event.detail.get("profile_command_version") != 1:
        return None
    return ProfileWriteReceipt.model_validate(
        {
            key: event.detail[key]
            for key in (
                "command_id",
                "kind",
                "profile_id",
                "expected_revision",
                "accepted_revision",
            )
        }
    )


def profile_out(row: ApplicantProfileRow, event: AuditEvent | None = None) -> ApplicantProfile:
    return ApplicantProfile(
        **row.payload,
        id=row.id,
        revision=row.revision,
        write_receipt=receipt(event),
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def replay_profile(session: Session, event: AuditEvent, principal: Principal) -> ApplicantProfile:
    row = (
        session.query(ApplicantProfileRow)
        .filter(
            ApplicantProfileRow.id == event.detail["profile_id"],
            ApplicantProfileRow.organization_id == principal.organization_id,
        )
        .populate_existing()
        .first()
    )
    if row is None:
        session.rollback()
        raise HTTPException(
            410, "This accepted command belongs to a deleted case. It cannot recreate it."
        )
    return profile_out(row, event)
