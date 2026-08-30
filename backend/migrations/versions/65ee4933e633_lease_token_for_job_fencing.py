"""Give every claim a token, so only its holder can write.

`heartbeat`, `complete`, `fail` and `mark_cancelled` matched on job id and
RUNNING status alone. A worker that stalled long enough for its lease to expire
— a long GC pause, a suspended container, a wedged event loop — could wake after
another worker had reclaimed the job and extend that worker's lease, mark its
job succeeded, or fail work it had already finished. Two writers on one job is
the corruption a durable queue exists to prevent, and the crash tests could not
see it because they SIGKILL the first worker, and a dead process writes nothing.

Nullable, and left null for rows that already exist: they were claimed before
tokens existed, and inventing one would assert an ownership nobody recorded. A
null token matches nothing, so such a row cannot be written to by a stale
holder either — it has to be reclaimed first, which is what the reaper is for.

Revision ID: 65ee4933e633
Revises: b312b741919d
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "65ee4933e633"
down_revision: str | None = "b312b741919d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("lease_token", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("lease_token")
