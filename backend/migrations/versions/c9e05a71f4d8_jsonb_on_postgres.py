"""JSON columns become JSONB on PostgreSQL

Revision ID: c9e05a71f4d8
Revises: b8d2f6c103ae
Create Date: 2026-09-03

`json` stores the document as text and reparses it on every read; `jsonb`
stores it parsed and can be indexed. Every column here is read on every list
and export, and `program_results.payload` is the largest document the product
holds. SQLite has one JSON representation and needs no change, so this
migration is deliberately dialect-dependent rather than pretending both
databases have the same types.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c9e05a71f4d8"
down_revision: str | None = "b8d2f6c103ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (table, column) for every JSON column in the schema.
JSON_COLUMNS: tuple[tuple[str, str], ...] = (
    ("jobs", "payload"),
    ("applicant_profiles", "payload"),
    ("audit_events", "detail"),
    ("research_runs", "stage_state"),
    ("research_runs", "fetch_tiers"),
    ("research_runs", "errors"),
    ("research_runs", "unknowns"),
    ("research_runs", "retry_urls"),
    ("research_runs", "settings_snapshot"),
    ("claims", "payload"),
    ("conflicts", "payload"),
    ("program_results", "payload"),
    ("program_results", "checklist"),
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, column in JSON_COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f'TYPE jsonb USING "{column}"::jsonb'
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, column in JSON_COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f'TYPE json USING "{column}"::json'
        )
