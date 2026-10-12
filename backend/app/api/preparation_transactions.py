"""Fresh bounded write fences for owned preparation and coordinated erasure.

No legacy DML, placeholder child, parent timestamp, late Organization/User lock,
audit FK or global mutex. Read routes and previews never use this fence.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.applicant import ApplicantProfileRow
from app.models.auth import OrganizationMembership, User
from app.models.study_schedule import StudyScheduleRow
from app.security import Principal

_UNAVAILABLE = "Preparation write could not be confirmed. Keep the original request and retry."


def begin_fresh_preparation_write(session: Session) -> None:
    """Discard only clean dependency reads, then reserve a fresh command view."""
    if session.new or session.dirty or session.deleted or session.in_nested_transaction():
        # Never commit or silently discard unrelated/auth pending mutations.
        raise HTTPException(503, "Preparation write requires a clean request session.")
    try:
        if session.in_transaction():
            session.rollback()
        dialect = session.get_bind().dialect.name
        if dialect == "sqlite":
            # SQLAlchemy's logical autobegin emits no SQLite SQL here. This is
            # the first actual guarded statement, before any owner/UUID read.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        elif dialect == "postgresql":
            connection = session.connection(execution_options={"isolation_level": "READ COMMITTED"})
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            if (
                connection.execute(text("SHOW transaction_isolation")).scalar_one()
                != "read committed"
            ):
                session.rollback()
                raise HTTPException(503, "Preparation write isolation is unavailable.")
        else:
            session.rollback()
            raise HTTPException(503, "Preparation write database is unsupported.")
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, _UNAVAILABLE) from exc


def lock_owned_preparation_profile(
    session: Session, profile_id: str, principal: Principal
) -> ApplicantProfileRow:
    """Strong owned parent, current actor authority, then existing legacy child."""
    if not session.in_transaction():
        raise HTTPException(503, "Preparation write requires a fresh transaction.")
    try:
        with session.no_autoflush:
            profile = (
                session.query(ApplicantProfileRow)
                .filter(
                    ApplicantProfileRow.id == profile_id,
                    ApplicantProfileRow.organization_id == principal.organization_id,
                )
                .with_for_update()
                .populate_existing()
                .first()
            )
            if profile is None:
                session.rollback()
                raise HTTPException(404, "Applicant case not found")
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
            if actor is None or membership is None:
                session.rollback()
                raise HTTPException(401, "Authentication required.")
            (
                # Lock only the existing child's ID. Even JSON decoding of its
                # settings/sidecar must wait until after an accepted UUID replay.
                session.query(StudyScheduleRow.id)
                .filter(StudyScheduleRow.profile_id == profile_id)
                .with_for_update()
                .first()
            )
            return profile
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, _UNAVAILABLE) from exc


def begin_owned_preparation_write(
    session: Session, profile_id: str, principal: Principal
) -> ApplicantProfileRow:
    begin_fresh_preparation_write(session)
    return lock_owned_preparation_profile(session, profile_id, principal)
