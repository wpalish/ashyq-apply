"""Case-owned starter practice submissions.

Revision ID: f1a2b3c4d511
Revises: d8e412c6a901
"""

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d511"
down_revision = "d8e412c6a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_attempts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "profile_id",
            sa.String(32),
            sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_attempt_id", sa.String(36), nullable=False),
        sa.Column("lesson_id", sa.String(80), nullable=False),
        sa.Column("content_version", sa.String(40), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.CheckConstraint("total > 0 AND total <= 20", name="ck_study_attempts_total"),
        sa.CheckConstraint("correct >= 0 AND correct <= total", name="ck_study_attempts_correct"),
    )
    op.create_index(
        "uq_study_attempts_profile_client",
        "study_attempts",
        ["profile_id", "client_attempt_id"],
        unique=True,
    )
    op.create_index(
        "ix_study_attempts_profile_created", "study_attempts", ["profile_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("study_attempts")
