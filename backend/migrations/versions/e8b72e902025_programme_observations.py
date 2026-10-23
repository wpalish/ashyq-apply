"""Retain early read-only programme observations separately from assessed results.

Revision ID: e8b72e902025
Revises: d7a61e902024
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "e8b72e902025"
down_revision = "d7a61e902024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_runs",
        sa.Column("programme_observations", sa.JSON().with_variant(JSONB(), "postgresql")),
    )


def downgrade() -> None:
    op.drop_column("research_runs", "programme_observations")
