"""Stamp every durable job with the payload contract it was written against.

A queue outlives the process that filled it, so during a rolling deployment a
worker can be handed a payload written by a build it has never seen. Without a
version on the row there is no way to tell "I cannot read this" from "this
work failed", and the second answer spends the job's attempts and buries it in
the dead-letter state.

Rows written before this column existed were produced by the build that
introduced version 1, so they are backfilled to 1 rather than to 0 or NULL —
they are readable, and marking them unreadable would park real work.

The server defaults are kept on the columns rather than dropped after the
backfill: an older API writing a row during a rolling deployment does not know
about these columns, and a NOT NULL column with no default would reject its
insert outright.

Revision ID: b312b741919d
Revises: c3a1f4e9b2d7
Create Date: 2026-08-30 00:03:20.152032
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b312b741919d"
down_revision: str | None = "c3a1f4e9b2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payload_schema_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "producer_version",
                sa.String(length=40),
                nullable=False,
                server_default="",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("producer_version")
        batch_op.drop_column("payload_schema_version")
