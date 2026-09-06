"""School subscriptions, and the retirement of the org-wide entitlement.

Revision ID: e7c1a4d90b52
Revises: d4b2c8f17a90
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7c1a4d90b52"
down_revision = "d4b2c8f17a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(32),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_quota", sa.Integer(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("invoice_note", sa.String(200), nullable=False),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_org_status", "subscriptions", ["organization_id", "status"])

    op.add_column("entitlements", sa.Column("subscription_id", sa.String(32), nullable=True))
    op.create_index("ix_entitlements_subscription_id", "entitlements", ["subscription_id"])

    # Phase 1 reserved an org-wide entitlement for a subscription that granted
    # blanket access. A quota grants the right to spend instead, so the shape
    # and its guard come out rather than sit there to be misread.
    op.drop_index("uq_entitlements_org", table_name="entitlements")


def downgrade() -> None:
    op.create_index(
        "uq_entitlements_org",
        "entitlements",
        ["organization_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NULL"),
        sqlite_where=sa.text("profile_id IS NULL"),
    )
    op.drop_index("ix_entitlements_subscription_id", table_name="entitlements")
    op.drop_column("entitlements", "subscription_id")
    op.drop_table("subscriptions")
