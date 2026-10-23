"""Reference-only shared preparation current/history, without legacy backfill.

Revision ID: c3e71d902023
Revises: b5c81d9e2022
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "c3e71d902023"
down_revision = "b5c81d9e2022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "shared_route_current",
        sa.Column("profile_id", sa.String(32), sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("snapshot", document, nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_shared_route_current_revision"),
        sa.CheckConstraint("schema_version = 'shared-route-v1'", name="ck_shared_route_current_schema"),
    )
    op.create_table(
        "shared_route_history",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_id", sa.String(32), sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("client_write_uuid", sa.String(36), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("receipt", document, nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_shared_route_history_revision"),
        sa.UniqueConstraint("profile_id", "revision", name="uq_shared_route_history_profile_revision"),
        sa.UniqueConstraint("profile_id", "client_write_uuid", name="uq_shared_route_history_profile_uuid"),
    )
    op.create_index("ix_shared_route_history_profile_accepted", "shared_route_history", ["profile_id", "accepted_at"])


def downgrade() -> None:
    op.drop_table("shared_route_history")
    op.drop_table("shared_route_current")
