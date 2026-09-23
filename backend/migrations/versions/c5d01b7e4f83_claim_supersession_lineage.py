"""claims.superseded_at and claims.superseded_by_id

Revision ID: c5d01b7e4f83
Revises: a1f3c8d75e29
Create Date: 2026-09-21

Supersession already worked: a re-read page flips its live claims to
SUPERSEDED and the fresh ones are appended beside them. What the history
could not answer is when a value stopped being current and which value took
over — the two questions the phase guide's ClaimVersion exists for.

``superseded_at`` is written in the same transaction as the status flip.
``superseded_by_id`` points at the successor row when there is one; NULL means
the page no longer states this at all, which is a fact, not a missing link.
ON DELETE SET NULL mirrors ``claims.source_page_id``: the retention purge must
never take a history row with it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c5d01b7e4f83"
down_revision = "a1f3c8d75e29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("claims") as batch:
        batch.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("superseded_by_id", sa.String(32), nullable=True))
        batch.create_foreign_key(
            "fk_claims_superseded_by",
            "claims",
            ["superseded_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("claims") as batch:
        batch.drop_constraint("fk_claims_superseded_by", type_="foreignkey")
        batch.drop_column("superseded_by_id")
        batch.drop_column("superseded_at")
