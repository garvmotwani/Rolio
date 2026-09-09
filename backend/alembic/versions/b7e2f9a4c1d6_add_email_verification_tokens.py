"""add email_verification_tokens table

Revision ID: b7e2f9a4c1d6
Revises: f1a9c4d7e2b8
Create Date: 2026-09-09 14:00:00.000000

Note: check-first pattern (same as the refresh_sessions and
password_reset_tokens migrations) so it is a no-op on databases whose schema
was created by create_all and only acts when upgrading older deployments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = 'b7e2f9a4c1d6'
down_revision: Union[str, Sequence[str], None] = 'f1a9c4d7e2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = 'email_verification_tokens'
COLUMN_NAME = 'email_verified'


def _table_exists(bind, name: str) -> bool:
    return name in sa_inspect(bind).get_table_names()


def _column_exists(bind, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in sa_inspect(bind).get_columns(table)}
    except Exception:
        return False


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Create the email_verification_tokens table + users.email_verified column."""
    bind = op.get_bind()

    # users.email_verified — needed on databases created before the column
    # existed (fresh create_all DBs already have it from the model).
    if not _column_exists(bind, 'users', COLUMN_NAME):
        op.add_column('users', sa.Column(COLUMN_NAME, sa.Boolean(), nullable=False, server_default=sa.false()))

    if _table_exists(bind, TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_verification_tokens_id'), TABLE_NAME, ['id'])
    op.create_index(op.f('ix_email_verification_tokens_user_id'), TABLE_NAME, ['user_id'])
    op.create_index(op.f('ix_email_verification_tokens_token_hash'), TABLE_NAME, ['token_hash'])
    if not _index_exists(bind, TABLE_NAME, 'idx_emailverify_user_active'):
        op.create_index('idx_emailverify_user_active', TABLE_NAME, ['user_id', 'used_at'])


def downgrade() -> None:
    """Drop the email_verification_tokens table and the email_verified column."""
    bind = op.get_bind()
    if _table_exists(bind, TABLE_NAME):
        op.drop_index('idx_emailverify_user_active', table_name=TABLE_NAME)
        op.drop_index(op.f('ix_email_verification_tokens_token_hash'), table_name=TABLE_NAME)
        op.drop_index(op.f('ix_email_verification_tokens_user_id'), table_name=TABLE_NAME)
        op.drop_index(op.f('ix_email_verification_tokens_id'), table_name=TABLE_NAME)
        op.drop_table(TABLE_NAME)
    if _column_exists(bind, 'users', COLUMN_NAME):
        op.drop_column('users', COLUMN_NAME)
