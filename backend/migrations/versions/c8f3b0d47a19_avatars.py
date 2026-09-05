"""avatars, stored and served by us

Also drops `social_profiles.avatar_url`, which was added with the module for
"when an upload path exists". It exists now and does not use it: an avatar is
served from our own origin under `/api/social/avatars/{id}`, because the
content security policy is `img-src 'self' data:` and a third-party URL would
never have rendered. A column nothing reads is not a spare part.

Revision ID: c8f3b0d47a19
Revises: a4d61c8e73b2
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8f3b0d47a19"
down_revision: str | None = "a4d61c8e73b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "social_avatars",
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=30), nullable=False),
        # Bytes in the database rather than on a disk: the deployment is a
        # container with no promised volume, and backups already cover this.
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    with op.batch_alter_table("social_profiles") as batch:
        batch.drop_column("avatar_url")


def downgrade() -> None:
    with op.batch_alter_table("social_profiles") as batch:
        batch.add_column(
            sa.Column("avatar_url", sa.String(length=500), nullable=False, server_default="")
        )
    op.drop_table("social_avatars")
