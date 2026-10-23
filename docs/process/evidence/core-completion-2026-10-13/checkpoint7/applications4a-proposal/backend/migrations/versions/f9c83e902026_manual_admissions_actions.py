"""Admit explicit G3 V2 manual applications without rewriting accepted V1 rows.

Revision ID: f9c83e902026
Revises: e8b72e902025
Rollback refuses when any V2 row exists; no lossy automatic conversion.
"""

import sqlalchemy as sa
from alembic import op

revision = "f9c83e902026"
down_revision = "e8b72e902025"
branch_labels = None
depends_on = None


def _schema_check(table: str, condition: str) -> None:
    name = f"ck_{table}_schema"
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, condition)


def upgrade() -> None:
    for table in ("admissions_actions_current", "admissions_actions_events"):
        _schema_check(
            table,
            "schema_version IN ('admissions-actions-v1', 'admissions-actions-v2')",
        )


def downgrade() -> None:
    connection = op.get_bind()
    for table in ("admissions_actions_current", "admissions_actions_events"):
        found = connection.execute(
            sa.text(
                f"SELECT 1 FROM {table} WHERE schema_version <> 'admissions-actions-v1' LIMIT 1"
            )
        ).first()
        if found is not None:
            raise RuntimeError(
                "G3 V2 records require a compatible application; schema rollback refused"
            )
    for table in ("admissions_actions_current", "admissions_actions_events"):
        _schema_check(table, "schema_version = 'admissions-actions-v1'")
