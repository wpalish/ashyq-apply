"""Local university catalogue and selected research scope.

Revision ID: d8e412c6a901
Revises: c5d01b7e4f83
"""

import sqlalchemy as sa
from alembic import op

revision = "d8e412c6a901"
down_revision = "c5d01b7e4f83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "universities",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("identity_key", sa.String(400), nullable=False, unique=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(200), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("domain", sa.String(253)),
        sa.Column("domain_status", sa.String(40), nullable=False),
        sa.Column("registry_entry", sa.JSON()),
        sa.Column("seed_snapshot", sa.JSON()),
        sa.Column("seed_version", sa.String(80)),
    )
    op.create_index("ix_universities_country", "universities", ["country"])
    op.create_table(
        "university_observations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "university_id",
            sa.String(32),
            sa.ForeignKey("universities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("seed_version", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("university_id", "fingerprint"),
    )
    op.create_index(
        "ix_university_observations_university_id", "university_observations", ["university_id"]
    )
    with op.batch_alter_table("research_runs") as batch:
        batch.add_column(sa.Column("university_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("university_ids")
    op.drop_table("university_observations")
    op.drop_table("universities")
