"""when a run's evidence next ages out

Revision ID: f13b9c5d2a44
Revises: e2f7a41c9b83
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f13b9c5d2a44"
down_revision: str | None = "e2f7a41c9b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("research_runs") as batch:
        batch.add_column(sa.Column("next_recheck_at", sa.DateTime(timezone=True), nullable=True))
    # Existing runs get theirs when the recheck job next runs; backfilling a
    # date here would claim evidence was checked on a day it was not.
    op.create_index(
        "ix_runs_next_recheck", "research_runs", ["next_recheck_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_runs_next_recheck", table_name="research_runs")
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("next_recheck_at")
