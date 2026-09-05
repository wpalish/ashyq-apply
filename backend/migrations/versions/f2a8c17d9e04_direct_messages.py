"""private conversations, and who may start one

Additive apart from one column on `social_profiles`, which is backfilled with
the narrow policy rather than the permissive one: an inbox opened to strangers
is a decision each person makes, and a migration must not make it for them.

Revision ID: f2a8c17d9e04
Revises: e7c4a91b6f20
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a8c17d9e04"
down_revision: str | None = "e7c4a91b6f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Kept in step with `app.domain.social`, and asserted equal in the tests.
MESSAGE_MAX_CHARS = 2000
DEFAULT_DM_POLICY = "threads"


def upgrade() -> None:
    with op.batch_alter_table("social_profiles") as batch:
        batch.add_column(sa.Column("dm_policy", sa.String(length=20), nullable=True))
    op.execute(
        sa.text("UPDATE social_profiles SET dm_policy = :policy WHERE dm_policy IS NULL")
        .bindparams(policy=DEFAULT_DM_POLICY)
    )
    with op.batch_alter_table("social_profiles") as batch:
        batch.alter_column("dm_policy", existing_type=sa.String(length=20), nullable=False)

    op.create_table(
        "conversations",
        sa.Column("lower_id", sa.String(length=32), nullable=False),
        sa.Column("higher_id", sa.String(length=32), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lower_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("higher_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # The ordered pair is what makes the unique constraint enough: without
        # it, A→B and B→A are two different rows for one conversation.
        sa.CheckConstraint("lower_id < higher_id", name="ck_conversations_ordered_pair"),
        sa.ForeignKeyConstraint(["lower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["higher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lower_id", "higher_id", name="uq_conversation_pair"),
    )
    op.create_index("ix_conversations_lower_id", "conversations", ["lower_id"], unique=False)
    op.create_index("ix_conversations_higher_id", "conversations", ["higher_id"], unique=False)
    op.create_index(
        "ix_conversations_lower_activity", "conversations", ["lower_id", "last_message_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_higher_activity", "conversations", ["higher_id", "last_message_at"],
        unique=False,
    )

    op.create_table(
        "direct_messages",
        sa.Column("conversation_id", sa.String(length=32), nullable=False),
        sa.Column("sender_id", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"length(body) <= {MESSAGE_MAX_CHARS}", name="ck_direct_messages_body_max_length"
        ),
        sa.CheckConstraint("length(trim(body)) > 0", name="ck_direct_messages_body_not_blank"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_direct_messages_conversation_id", "direct_messages", ["conversation_id"], unique=False
    )
    op.create_index("ix_direct_messages_sender_id", "direct_messages", ["sender_id"], unique=False)
    op.create_index(
        "ix_direct_messages_conversation_created",
        "direct_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("direct_messages")
    op.drop_table("conversations")
    with op.batch_alter_table("social_profiles") as batch:
        batch.drop_column("dm_policy")
