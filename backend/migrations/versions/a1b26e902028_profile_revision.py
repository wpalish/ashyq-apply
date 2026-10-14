"""Add atomic applicant profile revision.

Revision ID: a1b26e902028
Revises: a0d94e902027
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b26e902028"
down_revision = "a0d94e902027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applicant_profiles",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM applicant_profiles WHERE revision <> 1"))
        .scalar_one()
    ):
        raise RuntimeError(
            "Cannot discard accepted profile revisions; restore a compatible backup."
        )
    with op.batch_alter_table("applicant_profiles") as batch:
        batch.drop_column("revision")
