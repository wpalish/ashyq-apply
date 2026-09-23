"""source_snapshots: the versions of a page we have observed

Revision ID: a1f3c8d75e29
Revises: d9c4e7a21b83
Create Date: 2026-09-21

``source_pages`` is one mutable row per URL — the page's current state, which
is what conditional GET needs and all it needs. It cannot answer "what did
this page say when we claimed that?", because the previous hash is gone the
moment the page changes.

``source_snapshots`` is that record: one row per (page, content hash), with
the validators seen alongside it and when that content was first and last
observed. Metadata only, never a body, exactly like the page table.

ON DELETE CASCADE: a snapshot is meaningless without its page, and the page
retention sweep already refuses to purge a page with live claims.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1f3c8d75e29"
down_revision = "d9c4e7a21b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("page_id", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified_header", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["source_pages.id"],
            name="fk_snapshots_source_page",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "uq_snapshots_page_hash",
        "source_snapshots",
        ["page_id", "content_hash"],
        unique=True,
    )
    op.create_index(
        "ix_snapshots_page_last_seen",
        "source_snapshots",
        ["page_id", "last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_page_last_seen", table_name="source_snapshots")
    op.drop_index("uq_snapshots_page_hash", table_name="source_snapshots")
    op.drop_table("source_snapshots")
