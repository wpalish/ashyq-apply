"""blocking, and a queue for what a person reports

Purely additive: two tables, nothing altered, nothing backfilled.

Revision ID: a4d61c8e73b2
Revises: f2a8c17d9e04
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d61c8e73b2"
down_revision: str | None = "f2a8c17d9e04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Kept in step with `app.domain.social`, and asserted equal in the tests.
REPORT_NOTE_MAX_CHARS = 500


def upgrade() -> None:
    op.create_table(
        "social_blocks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("blocker_id", sa.String(length=32), nullable=False),
        sa.Column("blocked_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("blocker_id <> blocked_id", name="ck_blocks_not_self"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
    )
    op.create_index("ix_social_blocks_blocker_id", "social_blocks", ["blocker_id"], unique=False)
    op.create_index("ix_social_blocks_blocked_id", "social_blocks", ["blocked_id"], unique=False)

    op.create_table(
        "content_reports",
        sa.Column("reporter_id", sa.String(length=32), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        # Not a foreign key on purpose: a report has to outlive the thing it is
        # about, both to keep the queue's history and so that "removed" is a
        # state the queue can show rather than a row that vanished.
        sa.Column("subject_id", sa.String(length=32), nullable=False),
        sa.Column("subject_author_id", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("note", sa.String(length=REPORT_NOTE_MAX_CHARS), nullable=False),
        sa.Column("excerpt", sa.String(length=600), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_by", sa.String(length=320), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.String(length=REPORT_NOTE_MAX_CHARS), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reporter_id", "subject_type", "subject_id", name="uq_report_once_per_person"
        ),
    )
    op.create_index("ix_reports_reporter_id", "content_reports", ["reporter_id"], unique=False)
    op.create_index("ix_reports_reason", "content_reports", ["reason"], unique=False)
    op.create_index("ix_reports_status", "content_reports", ["status"], unique=False)
    op.create_index(
        "ix_reports_subject_author_id", "content_reports", ["subject_author_id"], unique=False
    )
    op.create_index(
        "ix_reports_status_created", "content_reports", ["status", "created_at"], unique=False
    )
    op.create_index(
        "ix_reports_subject", "content_reports", ["subject_type", "subject_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("content_reports")
    op.drop_table("social_blocks")
