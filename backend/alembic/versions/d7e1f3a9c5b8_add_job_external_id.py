"""add external_id to jobs

Revision ID: d7e1f3a9c5b8
Revises: c3d8e2f9a4b7
Create Date: 2026-09-12

Stable external identifier for jobs imported from external sources
(JSearch, Remotive, Jobicy). Enables idempotent save/import without
fragile URL-substring lookups. Indexed for dedup checks.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d7e1f3a9c5b8"
down_revision = "c3d8e2f9a4b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("jobs")}
    if "external_id" not in columns:
        op.add_column(
            "jobs",
            sa.Column("external_id", sa.String(length=512), nullable=True),
        )
        op.create_index("ix_jobs_external_id", "jobs", ["external_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("jobs")}
    if "external_id" in columns:
        op.drop_index("ix_jobs_external_id", table_name="jobs")
        op.drop_column("jobs", "external_id")
