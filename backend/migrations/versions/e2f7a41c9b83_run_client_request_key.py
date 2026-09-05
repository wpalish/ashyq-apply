"""client request key on research runs, so a replayed start returns its run

Revision ID: e2f7a41c9b83
Revises: c3a1f4e9b2d7
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f7a41c9b83"
down_revision: str | None = "c3a1f4e9b2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite cannot ALTER a table in place, so the column and its index go
    # through batch mode; on PostgreSQL this compiles to a plain ALTER.
    with op.batch_alter_table("research_runs") as batch:
        batch.add_column(sa.Column("client_request_key", sa.String(length=120), nullable=True))
    # NULL is distinct from NULL in both engines, so every existing run - and
    # every future run started without the header - stays outside this index.
    op.create_index(
        "uq_runs_client_request_key",
        "research_runs",
        ["profile_id", "client_request_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_runs_client_request_key", table_name="research_runs")
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("client_request_key")
