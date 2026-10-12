"""Profile-owned admissions action aggregate and immutable event history.

Revision ID: d7a61e902024
Revises: c3e71d902023
No native backfill, source foreign key, independent event ID or timestamp default.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "d7a61e902024"
down_revision = "c3e71d902023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "admissions_actions_current",
        sa.Column(
            "profile_id",
            sa.String(32),
            sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("state", document, nullable=False),
        sa.Column("state_digest", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision >= 1 AND revision <= 2147483647",
            name="ck_admissions_actions_current_revision",
        ),
        sa.CheckConstraint(
            "schema_version = 'admissions-actions-v1'",
            name="ck_admissions_actions_current_schema",
        ),
    )
    op.create_table(
        "admissions_actions_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(32),
            sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("client_write_uuid", sa.String(36), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("receipt_digest", sa.String(64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_refs", document, nullable=False),
        sa.Column("receipt", document, nullable=False),
        sa.CheckConstraint(
            "revision >= 1 AND revision <= 2147483647",
            name="ck_admissions_actions_events_revision",
        ),
        sa.CheckConstraint(
            "schema_version = 'admissions-actions-v1'",
            name="ck_admissions_actions_events_schema",
        ),
        sa.CheckConstraint(
            "kind IN ('create_application', 'create_personal_task', 'bind_source_task', "
            "'rebind_source_task', 'set_document_self_report', 'set_personal_details', "
            "'set_planning_status', 'declare_submission', 'declare_withdrawal', "
            "'correct_declaration', 'import_legacy_marks', 'select_active_preparation')",
            name="ck_admissions_actions_events_kind",
        ),
        sa.UniqueConstraint(
            "profile_id", "revision", name="uq_admissions_actions_events_profile_revision"
        ),
        sa.UniqueConstraint(
            "profile_id", "client_write_uuid", name="uq_admissions_actions_events_profile_uuid"
        ),
    )


def downgrade() -> None:
    op.drop_table("admissions_actions_events")
    op.drop_table("admissions_actions_current")
