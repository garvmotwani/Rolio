"""add activity feed, target role, resume tracking

Revision ID: e9f2a4b6c8d1
Revises: d7e1f3a9c5b8
Create Date: 2026-09-21

NOTE: Each operation is conditional because the initial migration uses
Base.metadata.create_all() (documented limitation of this project), which
already creates tables matching the CURRENT models on a fresh database.
On databases created before those model fields existed (e.g. production
Neon), the columns are genuinely missing and get added here.
"""
from alembic import op
import sqlalchemy as sa

revision = "e9f2a4b6c8d1"
down_revision = "d7e1f3a9c5b8"
branch_labels = None
depends_on = None


def _columns_exist(bind, table: str) -> set:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table)}


def _has_index(bind, table: str, index: str) -> bool:
    insp = sa.inspect(bind)
    return index in {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()

    # 1. profiles.target_role — drives career roadmap defaults
    if "target_role" not in _columns_exist(bind, "profiles"):
        op.add_column(
            "profiles",
            sa.Column("target_role", sa.String(), nullable=False, server_default=""),
        )

    # 2. users.last_seen_at — activity feed cursor ("What's new?" only)
    if "last_seen_at" not in _columns_exist(bind, "users"):
        op.add_column("users", sa.Column("last_seen_at", sa.DateTime(), nullable=True))

    # 3. applications.resume_id — per-resume response-rate analytics
    cols = _columns_exist(bind, "applications")
    if "resume_id" not in cols:
        op.add_column("applications", sa.Column("resume_id", sa.Integer(), nullable=True))
    if "fk_application_resume_id" not in {
        fk["name"] for fk in sa.inspect(bind).get_foreign_keys("applications")
    }:
        # batch_alter_table works on both SQLite (copy-and-move) and PostgreSQL
        with op.batch_alter_table("applications") as batch:
            batch.create_foreign_key(
                "fk_application_resume_id", "resumes", ["resume_id"], ["id"]
            )
    if not _has_index(bind, "applications", "idx_application_resume_id"):
        op.create_index("idx_application_resume_id", "applications", ["resume_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "applications", "idx_application_resume_id"):
        op.drop_index("idx_application_resume_id", table_name="applications")
    if "resume_id" in _columns_exist(bind, "applications"):
        # Dropping the column implicitly removes the FK on both SQLite
        # (batch copy-and-move) and PostgreSQL (auto-drops dependent
        # constraints), so no explicit constraint drop is needed.
        with op.batch_alter_table("applications") as batch:
            batch.drop_column("resume_id")
    if "last_seen_at" in _columns_exist(bind, "users"):
        op.drop_column("users", "last_seen_at")
    if "target_role" in _columns_exist(bind, "profiles"):
        op.drop_column("profiles", "target_role")
