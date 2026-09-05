"""which portfolio bucket a result landed in

Revision ID: a4d1c7e58b92
Revises: e7c4a91b6f20
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d1c7e58b92"
down_revision: str | None = "e7c4a91b6f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("program_results") as batch:
        batch.add_column(
            sa.Column("bucket", sa.String(length=40), nullable=False, server_default="")
        )
    # Rows assessed under v1 keep an empty bucket rather than a guessed one:
    # the bucket comes from axes those rows were never scored on.
    op.create_index("ix_results_bucket", "program_results", ["bucket"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_results_bucket", table_name="program_results")
    with op.batch_alter_table("program_results") as batch:
        batch.drop_column("bucket")
