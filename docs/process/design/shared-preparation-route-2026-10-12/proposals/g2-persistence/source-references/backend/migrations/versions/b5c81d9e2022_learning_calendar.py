"""Optional learning path sidecar; original calendars and attempt receipts unchanged.

Revision ID: b5c81d9e2022
Revises: a9e5c14d2021
"""

import sqlalchemy as sa
from alembic import op

revision = "b5c81d9e2022"
down_revision = "a9e5c14d2021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("study_schedules", sa.Column("learning_path", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("study_schedules", "learning_path")
