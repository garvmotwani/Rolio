"""add oauth_states table

Revision ID: 0219e6bcb03a
Revises: b05a93c793ce
Create Date: 2026-09-02 06:39:18.378791

Note: the initial migration (d555c3fbfe92) creates the full schema from model
metadata, including this table. This migration therefore checks first, so it is
a no-op on fresh databases and only acts when upgrading older deployments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = '0219e6bcb03a'
down_revision: Union[str, Sequence[str], None] = 'b05a93c793ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = 'oauth_states'


def _table_exists(bind, name: str) -> bool:
    return name in sa_inspect(bind).get_table_names()


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Create the oauth_states table with indexes if it doesn't already exist."""
    bind = op.get_bind()
    if _table_exists(bind, TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('state_token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_consumed', sa.Boolean(), nullable=True),
        sa.Column('flow_type', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('state_token', name='uq_oauth_state_token'),
    )
    op.create_index('ix_oauth_states_id', TABLE_NAME, ['id'], unique=False)
    op.create_index('ix_oauth_states_user_id', TABLE_NAME, ['user_id'], unique=False)
    op.create_index('ix_oauth_states_state_token', TABLE_NAME, ['state_token'], unique=True)
    op.create_index('idx_oauth_state_lookup', TABLE_NAME, ['state_token', 'is_consumed'], unique=False)


def downgrade() -> None:
    """Drop the oauth_states table if present."""
    bind = op.get_bind()
    if not _table_exists(bind, TABLE_NAME):
        return

    op.drop_index('idx_oauth_state_lookup', table_name=TABLE_NAME)
    op.drop_index('ix_oauth_states_state_token', table_name=TABLE_NAME)
    op.drop_index('ix_oauth_states_user_id', table_name=TABLE_NAME)
    op.drop_index('ix_oauth_states_id', table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
