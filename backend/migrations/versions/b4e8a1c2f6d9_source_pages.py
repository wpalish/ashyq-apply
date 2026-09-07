"""Source pages: the crawler's conditional-GET memory, and its retention.

Revision ID: b4e8a1c2f6d9
Revises: e7c1a4d90b52

One metadata-only row per fetched page (never a body): the HTTP validators
and content hash let the next visit ask "has this changed?" instead of
re-downloading, and ``active_claims`` lets the claim system keep a page alive.

Retention policy: metadata-only rows (never bodies); purgeable when
active_claims=0 AND fetched_at < now()-RETENTION_DAYS, or fetched_at IS NULL
AND created_at < now()-RETENTION_DAYS; active_claims>0 never purged;
RETENTION_DAYS=180 (owner may override 90); purge execution is T32's job.
A migration must not import the application, so the policy's constant is
written down here as SOURCE_PAGE_RETENTION_DAYS; the tests pin it equal to
RETENTION_DAYS in app.models.source_page.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b4e8a1c2f6d9"
down_revision = "e7c1a4d90b52"
branch_labels = None
depends_on = None

#: Days a page's metadata is kept after its last fetch. Must stay equal to
#: RETENTION_DAYS in app.models.source_page.
SOURCE_PAGE_RETENTION_DAYS = 180


def upgrade() -> None:
    op.create_table(
        "source_pages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("registrable_domain", sa.String(255), nullable=False),
        sa.Column("institution_key", sa.String(120), nullable=True),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified_header", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("lastmod_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("page_type", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("active_claims", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("uq_source_pages_url", "source_pages", ["url"], unique=True)
    op.create_index("ix_source_pages_domain", "source_pages", ["registrable_domain"])
    op.create_index("ix_source_pages_institution", "source_pages", ["institution_key"])
    op.create_index("ix_source_pages_retention", "source_pages", ["active_claims", "fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_source_pages_retention", table_name="source_pages")
    op.drop_index("ix_source_pages_institution", table_name="source_pages")
    op.drop_index("ix_source_pages_domain", table_name="source_pages")
    op.drop_index("uq_source_pages_url", table_name="source_pages")
    op.drop_table("source_pages")
