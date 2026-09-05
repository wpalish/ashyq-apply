"""diagnostics that are unknowns, kept apart from failures

Revision ID: b8d2f6c103ae
Revises: a7c4e1f80b52
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8d2f6c103ae"
down_revision: str | None = "a7c4e1f80b52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("research_runs") as batch:
        # Existing runs keep everything under `errors`; re-classifying old rows
        # would be inventing a judgement about diagnostics nobody re-read.
        batch.add_column(
            sa.Column("unknowns", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )


def downgrade() -> None:
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("unknowns")
