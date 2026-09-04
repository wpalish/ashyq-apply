"""social module: applicant profiles, posts, tags and threads

Purely additive. No existing table is altered and no existing row is touched,
so this migration is safe to apply to a live database and safe to reverse.

Revision ID: e7c4a91b6f20
Revises: c3a1f4e9b2d7
Create Date: 2026-09-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7c4a91b6f20"
down_revision: str | None = "c3a1f4e9b2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Kept in step with `app.domain.social`. A migration must not import the
#: application, so the numbers are repeated here and asserted equal in
#: `tests/test_social_models.py`.
POST_MAX_CHARS = 500
REPLY_MAX_CHARS = 500
BIO_MAX_CHARS = 280


def upgrade() -> None:
    op.create_table(
        "social_profiles",
        sa.Column("user_id", sa.String(length=32), nullable=False),
        # Null means "not stated". There is no default: the product does not
        # put a status on someone's profile that they did not choose.
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("target_city", sa.String(length=120), nullable=False),
        sa.Column("target_city_key", sa.String(length=120), nullable=False),
        sa.Column("target_major", sa.String(length=120), nullable=False),
        sa.Column("target_major_key", sa.String(length=120), nullable=False),
        sa.Column("bio", sa.String(length=BIO_MAX_CHARS), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_social_profiles_status", "social_profiles", ["status"], unique=False)
    op.create_index(
        "ix_social_profiles_target_city_key", "social_profiles", ["target_city_key"], unique=False
    )
    op.create_index(
        "ix_social_profiles_target_major_key",
        "social_profiles",
        ["target_major_key"],
        unique=False,
    )

    op.create_table(
        "social_profile_universities",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("profile_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("name_key", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["social_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "name_key", name="uq_profile_university"),
    )
    op.create_index(
        "ix_social_profile_universities_profile_id",
        "social_profile_universities",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_social_profile_universities_name_key",
        "social_profile_universities",
        ["name_key"],
        unique=False,
    )

    op.create_table(
        "posts",
        sa.Column("author_id", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"length(body) <= {POST_MAX_CHARS}", name="ck_posts_body_max_length"),
        sa.CheckConstraint("length(trim(body)) > 0", name="ck_posts_body_not_blank"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_posts_author_id", "posts", ["author_id"], unique=False)
    op.create_index("ix_posts_author_created", "posts", ["author_id", "created_at"], unique=False)
    # The feed is newest-first and paginates on (created_at, id), so the index
    # carries both columns: two posts written in the same millisecond still get
    # a stable order and a cursor that cannot skip one.
    op.create_index("ix_posts_created_at_id", "posts", ["created_at", "id"], unique=False)

    op.create_table(
        "post_tags",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("post_id", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "key", name="uq_post_tag"),
    )
    op.create_index("ix_post_tags_post_id", "post_tags", ["post_id"], unique=False)
    op.create_index("ix_post_tags_key", "post_tags", ["key"], unique=False)

    op.create_table(
        "post_replies",
        sa.Column("post_id", sa.String(length=32), nullable=False),
        sa.Column("author_id", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"length(body) <= {REPLY_MAX_CHARS}", name="ck_post_replies_body_max_length"
        ),
        sa.CheckConstraint("length(trim(body)) > 0", name="ck_post_replies_body_not_blank"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_post_replies_post_id", "post_replies", ["post_id"], unique=False)
    op.create_index("ix_post_replies_author_id", "post_replies", ["author_id"], unique=False)
    op.create_index(
        "ix_post_replies_post_created", "post_replies", ["post_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_table("post_replies")
    op.drop_table("post_tags")
    op.drop_table("posts")
    op.drop_table("social_profile_universities")
    op.drop_table("social_profiles")
