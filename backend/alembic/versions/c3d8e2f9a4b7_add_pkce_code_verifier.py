"""add pkce code_verifier to oauth_states

Revision ID: c3d8e2f9a4b7
Revises: b7e2f9a4c1d6
Create Date: 2026-09-11

Adds the PKCE code_verifier column (RFC 7636) used by the Google sign-in
flow. Nullable so existing in-flight states remain valid.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c3d8e2f9a4b7"
down_revision = "b7e2f9a4c1d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("oauth_states")}
    if "code_verifier" not in columns:
        op.add_column(
            "oauth_states",
            sa.Column("code_verifier", sa.String(length=128), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("oauth_states")}
    if "code_verifier" in columns:
        op.drop_column("oauth_states", "code_verifier")
