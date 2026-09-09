"""add refresh_sessions table

Revision ID: b05a93c793ce
Revises: 873760469030
Create Date: 2026-09-02 06:36:03.310901

Note: the initial migration (d555c3fbfe92) creates the full schema from model
metadata, including this table. This migration therefore checks first, so it is
a no-op on fresh databases and only acts when upgrading older deployments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = 'b05a93c793ce'
down_revision: Union[str, Sequence[str], None] = '873760469030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = 'refresh_sessions'


def _table_exists(bind, name: str) -> bool:
    return name in sa_inspect(bind).get_table_names()


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Create the refresh_sessions table if it doesn't already exist.

    Index names match the model exactly (ix_refresh_sessions_* via SQLAlchemy
    naming, plus idx_refresh_user_active from __table_args__) so a table
    created by create_all and one created here are identical.
    """
    bind = op.get_bind()
    if _table_exists(bind, TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('replaced_by_id', sa.Integer(), nullable=True),
        sa.Column('is_reused', sa.Boolean(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['replaced_by_id'], [f'{TABLE_NAME}.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_sessions_id', TABLE_NAME, ['id'], unique=False)
    op.create_index('ix_refresh_sessions_user_id', TABLE_NAME, ['user_id'], unique=False)
    op.create_index('ix_refresh_sessions_token_hash', TABLE_NAME, ['token_hash'], unique=True)
    op.create_index('ix_refresh_sessions_jti', TABLE_NAME, ['jti'], unique=False)
    op.create_index('idx_refresh_user_active', TABLE_NAME, ['user_id', 'revoked_at'], unique=False)


def downgrade() -> None:
    """Drop the refresh_sessions table and its indexes if present."""
    bind = op.get_bind()
    if not _table_exists(bind, TABLE_NAME):
        return

    # Drop only indexes that actually exist (fresh DBs get create_all-named ones)
    for ix in ('idx_refresh_user_active', 'ix_refresh_sessions_jti',
               'ix_refresh_sessions_token_hash', 'ix_refresh_sessions_user_id',
               'ix_refresh_sessions_id'):
        if _index_exists(bind, TABLE_NAME, ix):
            op.drop_index(ix, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
