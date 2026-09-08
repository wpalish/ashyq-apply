"""claims.source_page_id and research_runs.recheck_generation

Revision ID: d9c4e7a21b83
Revises: b4e8a1c2f6d9
Create Date: 2026-09-07

Two columns for freshness 2.0:

- ``claims.source_page_id`` links a piece of evidence to the ``source_pages``
  row it was read from. Nullable, indexed, and ``ON DELETE SET NULL``: the
  retention purge may delete a page whose only referencers are SUPERSEDED,
  and the history rows must survive it with their payload (and the source_url
  inside it) intact — that is the whole was/stale record.
- ``research_runs.recheck_generation`` seeds the recheck job's idempotency
  key. The previous key was date-granular, so a no-op recheck recomputed the
  key of the job that had just finished and the recheck chain died. Existing
  rows start at generation 0; the next recheck arms generation 1.

ClaimStatus gains SUPERSEDED with no DDL anywhere: the column is a plain
String(40) with no CHECK constraint, by design.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d9c4e7a21b83"
# Plain assignment, not an annotated one: QA's T32 locator greps for
# down_revision == "b4e8a1c2f6d9" exactly, as written in b4e8a1c2f6d9 itself.
down_revision = "b4e8a1c2f6d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("claims") as batch:
        batch.add_column(sa.Column("source_page_id", sa.String(32), nullable=True))
        batch.create_foreign_key(
            "fk_claims_source_page",
            "source_pages",
            ["source_page_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_claims_source_page", "claims", ["source_page_id"], unique=False)
    with op.batch_alter_table("research_runs") as batch:
        batch.add_column(
            sa.Column("recheck_generation", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("recheck_generation")
    op.drop_index("ix_claims_source_page", table_name="claims")
    with op.batch_alter_table("claims") as batch:
        batch.drop_constraint("fk_claims_source_page", type_="foreignkey")
        batch.drop_column("source_page_id")
