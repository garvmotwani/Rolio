"""add search history table

Revision ID: 7c2e9f1a4b5d
Revises: 0219e6bcb03a
Create Date: 2026-09-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = '7c2e9f1a4b5d'
down_revision: Union[str, Sequence[str], None] = '0219e6bcb03a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the search_history table if it doesn't already exist.

    On a fresh database the initial migration creates it from model metadata,
    so we only create it here when upgrading an existing deployment.
    """
    bind = op.get_bind()
    if 'search_history' in sa_inspect(bind).get_table_names():
        return

    op.create_table(
        'search_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=200), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('work_type', sa.String(length=20), nullable=True),
        sa.Column('experience_level', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_search_history_user_created', 'search_history', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_search_history_user_id'), 'search_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_search_history_id'), 'search_history', ['id'], unique=False)


def downgrade() -> None:
    """Drop the search_history table if present."""
    bind = op.get_bind()
    if 'search_history' not in sa_inspect(bind).get_table_names():
        return
    op.drop_index(op.f('ix_search_history_id'), table_name='search_history')
    op.drop_index(op.f('ix_search_history_user_id'), table_name='search_history')
    op.drop_index('idx_search_history_user_created', table_name='search_history')
    op.drop_table('search_history')