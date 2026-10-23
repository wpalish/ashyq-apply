"""Admit explicit V2 personal removal; preserve all accepted prior rows.

Revision ID: a0d94e902027
Revises: f9c83e902026
No backfill. Refuse lossy rollback of any extended current/event body.
"""

import sqlalchemy as sa
from alembic import op

revision = "a0d94e902027"
down_revision = "f9c83e902026"
branch_labels = None
depends_on = None

OLD = "kind IN ('create_application', 'create_personal_task', 'bind_source_task', 'rebind_source_task', 'set_document_self_report', 'set_personal_details', 'set_planning_status', 'declare_submission', 'declare_withdrawal', 'correct_declaration', 'import_legacy_marks', 'select_active_preparation')"
NEW = (
    "("
    + OLD
    + ") OR (schema_version = 'admissions-actions-v2' AND kind = 'remove_personal_action')"
)


def _replace(condition: str) -> None:
    with op.batch_alter_table("admissions_actions_events") as batch:
        batch.drop_constraint("ck_admissions_actions_events_kind", type_="check")
        batch.create_check_constraint("ck_admissions_actions_events_kind", condition)


def upgrade() -> None:
    _replace(NEW)


def downgrade() -> None:
    current = sa.table("admissions_actions_current", sa.column("state", sa.JSON))
    events = sa.table(
        "admissions_actions_events", sa.column("kind", sa.String), sa.column("receipt", sa.JSON)
    )
    connection = op.get_bind()
    has_current = connection.execute(
        sa.select(sa.literal(1))
        .select_from(current)
        .where(current.c.state["head_ref"].as_string().is_not(None))
        .limit(1)
    ).first()
    has_event = connection.execute(
        sa.select(sa.literal(1))
        .select_from(events)
        .where(
            sa.or_(
                events.c.kind == "remove_personal_action",
                events.c.receipt["request"]["operation"]
                .as_string()
                .in_(["document_metadata", "application_context"]),
            )
        )
        .limit(1)
    ).first()
    if has_current is not None or has_event is not None:
        raise RuntimeError(
            "Extended G3 V2 records require compatible readers; schema rollback refused"
        )
    _replace(OLD)
