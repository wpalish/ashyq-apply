"""Owned deadline preparation calendars.

Revision ID: a9e5c14d2021
Revises: f1a2b3c4d511
"""

import sqlalchemy as sa
from alembic import op

revision = "a9e5c14d2021"
down_revision = "f1a2b3c4d511"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_schedules",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("profile_id", name="uq_study_schedules_profile"),
        sa.CheckConstraint("revision > 0", name="ck_study_schedules_revision"),
    )


def downgrade() -> None:
    op.drop_table("study_schedules")
