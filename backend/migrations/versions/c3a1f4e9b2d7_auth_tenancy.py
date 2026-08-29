"""authentication, organizations and tenant-scoped applicant cases

Revision ID: c3a1f4e9b2d7
Revises: bb9a7d0ed5c3
Create Date: 2026-08-28
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "c3a1f4e9b2d7"
down_revision: str | None = "bb9a7d0ed5c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_ORG_ID = "00000000000000000000000000000001"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_table(
        "organization_memberships",
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "organization_id"),
        sa.UniqueConstraint("user_id", "organization_id"),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_auth_sessions_organization_id", "auth_sessions", ["organization_id"], unique=False
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)
    op.create_index(
        "ix_auth_sessions_user_expires", "auth_sessions", ["user_id", "expires_at"], unique=False
    )

    with op.batch_alter_table("applicant_profiles") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=32), nullable=True))
        batch.create_foreign_key(
            "fk_applicant_profiles_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_applicant_profiles_organization_id", ["organization_id"])
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=32), nullable=True))
        batch.create_foreign_key(
            "fk_audit_events_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_audit_events_organization_id", ["organization_id"])

    now = datetime.now(UTC)
    orgs = sa.table(
        "organizations",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        orgs,
        [
            {
                "id": LEGACY_ORG_ID,
                "name": "Local development workspace",
                "slug": "local-development",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.execute(
        sa.text(
            "UPDATE applicant_profiles SET organization_id = :org WHERE organization_id IS NULL"
        ).bindparams(org=LEGACY_ORG_ID)
    )
    op.execute(
        sa.text(
            "UPDATE audit_events SET organization_id = :org WHERE organization_id IS NULL"
        ).bindparams(org=LEGACY_ORG_ID)
    )

    with op.batch_alter_table("applicant_profiles") as batch:
        batch.alter_column("organization_id", existing_type=sa.String(length=32), nullable=False)
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("organization_id", existing_type=sa.String(length=32), nullable=False)
        batch.create_index(
            "ix_audit_organization_created", ["organization_id", "created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_index("ix_audit_organization_created")
        batch.drop_index("ix_audit_events_organization_id")
        batch.drop_constraint("fk_audit_events_organization_id", type_="foreignkey")
        batch.drop_column("organization_id")
    with op.batch_alter_table("applicant_profiles") as batch:
        batch.drop_index("ix_applicant_profiles_organization_id")
        batch.drop_constraint("fk_applicant_profiles_organization_id", type_="foreignkey")
        batch.drop_column("organization_id")
    op.drop_table("auth_sessions")
    op.drop_table("organization_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
