"""google sign-in: users.google_sub, users.hashed_password nullable, oauth_states.session_id

Revision ID: a3f8c2d1e4b6
Revises: 7c2e9f1a4b5d
Create Date: 2026-09-07 06:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = 'a3f8c2d1e4b6'
down_revision: Union[str, Sequence[str], None] = '7c2e9f1a4b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_OAUTH = 'oauth_states'
TABLE_USERS = 'users'


def _table_exists(bind, name: str) -> bool:
    return name in sa_inspect(bind).get_table_names()


def _column_exists(bind, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa_inspect(bind).get_columns(table)}


def _index_exists(bind, table: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Add Google sign-in columns.

    - users.google_sub: nullable, unique Google identity.
    - users.hashed_password: made nullable (SQLite can't alter nullability,
      so the ALTER only runs on Postgres; SQLite tolerates writing NULL into
      a non-null declared column via SQLAlchemy, and fresh DBs get the new
      model default anyway).
    - oauth_states.user_id: nullable for sign-in flows.
    - oauth_states.session_id: new column for sign-in flow binding.
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # ── users.google_sub ────────────────────────────────────
    if _column_exists(bind, TABLE_USERS, "google_sub"):
        pass  # already migrated
    else:
        op.add_column(TABLE_USERS, sa.Column('google_sub', sa.String(), nullable=True))
    if not _index_exists(bind, TABLE_USERS, 'ix_users_google_sub'):
        op.create_index('ix_users_google_sub', TABLE_USERS, ['google_sub'], unique=True)

    # ── users.hashed_password nullable (Postgres only) ─────
    if not is_sqlite:
        op.alter_column(TABLE_USERS, 'hashed_password', existing_type=sa.String(),
                        nullable=True)

    # ── oauth_states.user_id nullable ──────────────────────
    if not is_sqlite:
        op.alter_column(TABLE_OAUTH, 'user_id', existing_type=sa.Integer(),
                        nullable=True)

    # ── oauth_states.session_id ────────────────────────────
    if not _column_exists(bind, TABLE_OAUTH, 'session_id'):
        op.add_column(TABLE_OAUTH, sa.Column('session_id', sa.String(64), nullable=True))
        op.create_index('ix_oauth_states_session_id', TABLE_OAUTH, ['session_id'], unique=False)


def downgrade() -> None:
    """Remove Google sign-in columns."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if _column_exists(bind, TABLE_OAUTH, 'session_id'):
        op.drop_index('ix_oauth_states_session_id', table_name=TABLE_OAUTH)
        op.drop_column(TABLE_OAUTH, 'session_id')

    if not is_sqlite:
        # Refuse to make password non-nullable if OAuth-only users exist
        op.alter_column(TABLE_OAUTH, 'user_id', existing_type=sa.Integer(), nullable=False)
        op.alter_column(TABLE_USERS, 'hashed_password', existing_type=sa.String(),
                        nullable=False)

    if _column_exists(bind, TABLE_USERS, 'google_sub'):
        op.drop_index('ix_users_google_sub', table_name=TABLE_USERS)
        op.drop_column(TABLE_USERS, 'google_sub')
