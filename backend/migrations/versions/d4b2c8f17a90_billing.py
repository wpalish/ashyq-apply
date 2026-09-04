"""Orders, payment events, entitlements, and the tier a run was allowed.

Revision ID: d4b2c8f17a90
Revises: c3a1f4e9b2d7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4b2c8f17a90"
down_revision = "c3a1f4e9b2d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(32),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            sa.String(32),
            sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("amount_kzt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_invoice_id", sa.String(80), nullable=True),
        sa.Column("external_order_id", sa.String(80), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("phone_masked", sa.String(20), nullable=False),
        sa.Column("qr_payload", sa.Text(), nullable=False),
        sa.Column("qr_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(60), nullable=False),
    )
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_profile_id", "orders", ["profile_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_org_profile", "orders", ["organization_id", "profile_id"])
    op.create_index("ix_orders_provider_invoice", "orders", ["provider_invoice_id"])
    op.create_index("ix_orders_external_order_id", "orders", ["external_order_id"], unique=True)

    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(32),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("provider_status", sa.String(30), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])
    op.create_index("ix_payment_events_order", "payment_events", ["order_id", "received_at"])

    op.create_table(
        "entitlements",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(32),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_id", sa.String(32), nullable=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("order_id", sa.String(32), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_entitlements_organization_id", "entitlements", ["organization_id"])
    op.create_index("ix_entitlements_profile_id", "entitlements", ["profile_id"])
    # Two partial indexes, not one constraint: a plain UNIQUE treats every NULL
    # profile_id as distinct, which would let an organization accumulate
    # unlimited subscriptions.
    op.create_index(
        "uq_entitlements_case",
        "entitlements",
        ["organization_id", "profile_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NOT NULL"),
        sqlite_where=sa.text("profile_id IS NOT NULL"),
    )
    op.create_index(
        "uq_entitlements_org",
        "entitlements",
        ["organization_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NULL"),
        sqlite_where=sa.text("profile_id IS NULL"),
    )

    op.add_column(
        "research_runs",
        sa.Column("access_tier", sa.String(10), nullable=False, server_default="full"),
    )
    op.create_index("ix_research_runs_access_tier", "research_runs", ["access_tier"])


def downgrade() -> None:
    op.drop_index("ix_research_runs_access_tier", table_name="research_runs")
    op.drop_column("research_runs", "access_tier")
    op.drop_table("entitlements")
    op.drop_table("payment_events")
    op.drop_table("orders")
