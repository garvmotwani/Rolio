"""add password_reset_tokens table

Revision ID: f1a9c4d7e2b8
Revises: a3f8c2d1e4b6
Create Date: 2026-09-09 12:30:00.000000

Note: check-first pattern (same as the refresh_sessions migration) so it is
a no-op on databases whose schema was created by create_all and only acts
when upgrading older deployments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = 'f1a9c4d7e2b8'
down_revision: Union[str, Sequence[str], None] = 'a3f8c2d1e4b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = 'password_reset_tokens'


def _table_exists(bind, name: str) -> bool:
    return name in sa_inspect(bind).get_table_names()


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Create the password_reset_tokens table if it doesn't already exist."""
    bind = op.get_bind()
    if _table_exists(bind, TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('request_ip', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_reset_tokens_id', TABLE_NAME, ['id'], unique=False)
    op.create_index('ix_password_reset_tokens_user_id', TABLE_NAME, ['user_id'], unique=False)
    op.create_index('ix_password_reset_tokens_token_hash', TABLE_NAME, ['token_hash'], unique=True)
    op.create_index('idx_pwdreset_user_active', TABLE_NAME, ['user_id', 'used_at'], unique=False)


def downgrade() -> None:
    """Drop the password_reset_tokens table and its indexes if present."""
    bind = op.get_bind()
    if not _table_exists(bind, TABLE_NAME):
        return

    for ix in ('idx_pwdreset_user_active', 'ix_password_reset_tokens_token_hash',
               'ix_password_reset_tokens_user_id', 'ix_password_reset_tokens_id'):
        if _index_exists(bind, TABLE_NAME, ix):
            op.drop_index(ix, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
