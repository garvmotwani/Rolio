"""add unique constraints and indexes

Revision ID: 873760469030
Revises: d555c3fbfe92
Create Date: 2026-09-02 05:59:43.161100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = '873760469030'
down_revision: Union[str, Sequence[str], None] = 'd555c3fbfe92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(bind, table: str, index_name: str) -> bool:
    """Check whether an index exists on a table (works for SQLite + Postgres)."""
    try:
        indexes = {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
        if index_name in indexes:
            return True
        # Also check legacy naming ix_<table>_<column>
        return any(
            ix.startswith(index_name) or index_name.startswith(ix)
            for ix in indexes
        )
    except Exception:
        return False


def _constraint_exists(bind, table: str, constraint_name: str) -> bool:
    """Check whether a unique constraint exists on a table."""
    try:
        constraints = sa_inspect(bind).get_unique_constraints(table)
        return any(c["name"] == constraint_name for c in constraints)
    except Exception:
        return False


def upgrade() -> None:
    """Add indexes and constraints if they don't already exist.

    This migration is idempotent: on a fresh database the initial migration
    already created model-defined indexes, so we only add anything missing.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    tables = set(inspector.get_table_names())

    if "application_events" in tables:
        with op.batch_alter_table('application_events', schema=None) as batch_op:
            if not _index_exists(bind, 'application_events', 'idx_event_app_created'):
                batch_op.create_index('idx_event_app_created', ['application_id', 'created_at'], unique=False)
            if not _index_exists(bind, 'application_events', 'ix_application_events_application_id'):
                batch_op.create_index(batch_op.f('ix_application_events_application_id'), ['application_id'], unique=False)
            if not _index_exists(bind, 'application_events', 'ix_application_events_user_id'):
                batch_op.create_index(batch_op.f('ix_application_events_user_id'), ['user_id'], unique=False)

    if "application_reminders" in tables:
        with op.batch_alter_table('application_reminders', schema=None) as batch_op:
            if not _index_exists(bind, 'application_reminders', 'ix_application_reminders_application_id'):
                batch_op.create_index(batch_op.f('ix_application_reminders_application_id'), ['application_id'], unique=False)
            if not _index_exists(bind, 'application_reminders', 'ix_application_reminders_remind_at'):
                batch_op.create_index(batch_op.f('ix_application_reminders_remind_at'), ['remind_at'], unique=False)
            if not _index_exists(bind, 'application_reminders', 'ix_application_reminders_user_id'):
                batch_op.create_index(batch_op.f('ix_application_reminders_user_id'), ['user_id'], unique=False)

    if "applications" in tables:
        with op.batch_alter_table('applications', schema=None) as batch_op:
            if not _index_exists(bind, 'applications', 'idx_application_applied_at'):
                batch_op.create_index('idx_application_applied_at', ['applied_at'], unique=False)
            if not _index_exists(bind, 'applications', 'idx_application_user_status'):
                batch_op.create_index('idx_application_user_status', ['user_id', 'status'], unique=False)
            if not _index_exists(bind, 'applications', 'ix_applications_job_id'):
                batch_op.create_index(batch_op.f('ix_applications_job_id'), ['job_id'], unique=False)
            if not _index_exists(bind, 'applications', 'ix_applications_user_id'):
                batch_op.create_index(batch_op.f('ix_applications_user_id'), ['user_id'], unique=False)
            if not _constraint_exists(bind, 'applications', 'uq_application_user_job'):
                batch_op.create_unique_constraint('uq_application_user_job', ['user_id', 'job_id'])

    if "email_messages" in tables:
        with op.batch_alter_table('email_messages', schema=None) as batch_op:
            if not _index_exists(bind, 'email_messages', 'idx_email_user_received'):
                batch_op.create_index('idx_email_user_received', ['user_id', 'received_at'], unique=False)
            if not _index_exists(bind, 'email_messages', 'ix_email_messages_matched_application_id'):
                batch_op.create_index(batch_op.f('ix_email_messages_matched_application_id'), ['matched_application_id'], unique=False)
            if not _index_exists(bind, 'email_messages', 'ix_email_messages_received_at'):
                batch_op.create_index(batch_op.f('ix_email_messages_received_at'), ['received_at'], unique=False)
            if not _index_exists(bind, 'email_messages', 'ix_email_messages_sender_domain'):
                batch_op.create_index(batch_op.f('ix_email_messages_sender_domain'), ['sender_domain'], unique=False)
            if not _index_exists(bind, 'email_messages', 'ix_email_messages_user_id'):
                batch_op.create_index(batch_op.f('ix_email_messages_user_id'), ['user_id'], unique=False)

    if "email_sync_logs" in tables:
        with op.batch_alter_table('email_sync_logs', schema=None) as batch_op:
            if not _index_exists(bind, 'email_sync_logs', 'ix_email_sync_logs_user_id'):
                batch_op.create_index(batch_op.f('ix_email_sync_logs_user_id'), ['user_id'], unique=False)

    if "gmail_tokens" in tables:
        with op.batch_alter_table('gmail_tokens', schema=None) as batch_op:
            if not _index_exists(bind, 'gmail_tokens', 'ix_gmail_tokens_is_active'):
                batch_op.create_index(batch_op.f('ix_gmail_tokens_is_active'), ['is_active'], unique=False)
            if not _index_exists(bind, 'gmail_tokens', 'ix_gmail_tokens_user_id'):
                batch_op.create_index(batch_op.f('ix_gmail_tokens_user_id'), ['user_id'], unique=True)

    if "saved_jobs" in tables:
        with op.batch_alter_table('saved_jobs', schema=None) as batch_op:
            if not _index_exists(bind, 'saved_jobs', 'idx_saved_user_saved'):
                batch_op.create_index('idx_saved_user_saved', ['user_id', 'saved_at'], unique=False)
            if not _index_exists(bind, 'saved_jobs', 'ix_saved_jobs_job_id'):
                batch_op.create_index(batch_op.f('ix_saved_jobs_job_id'), ['job_id'], unique=False)
            if not _index_exists(bind, 'saved_jobs', 'ix_saved_jobs_user_id'):
                batch_op.create_index(batch_op.f('ix_saved_jobs_user_id'), ['user_id'], unique=False)
            if not _constraint_exists(bind, 'saved_jobs', 'uq_saved_job_user_job'):
                batch_op.create_unique_constraint('uq_saved_job_user_job', ['user_id', 'job_id'])


def downgrade() -> None:
    """Drop the indexes and constraints added in upgrade."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    tables = set(inspector.get_table_names())

    if "saved_jobs" in tables:
        with op.batch_alter_table('saved_jobs', schema=None) as batch_op:
            if _constraint_exists(bind, 'saved_jobs', 'uq_saved_job_user_job'):
                batch_op.drop_constraint('uq_saved_job_user_job', type_='unique')
            if _index_exists(bind, 'saved_jobs', 'ix_saved_jobs_user_id'):
                batch_op.drop_index(batch_op.f('ix_saved_jobs_user_id'))
            if _index_exists(bind, 'saved_jobs', 'ix_saved_jobs_job_id'):
                batch_op.drop_index(batch_op.f('ix_saved_jobs_job_id'))
            if _index_exists(bind, 'saved_jobs', 'idx_saved_user_saved'):
                batch_op.drop_index('idx_saved_user_saved')

    if "applications" in tables:
        with op.batch_alter_table('applications', schema=None) as batch_op:
            if _constraint_exists(bind, 'applications', 'uq_application_user_job'):
                batch_op.drop_constraint('uq_application_user_job', type_='unique')
            if _index_exists(bind, 'applications', 'ix_applications_user_id'):
                batch_op.drop_index(batch_op.f('ix_applications_user_id'))
            if _index_exists(bind, 'applications', 'ix_applications_job_id'):
                batch_op.drop_index(batch_op.f('ix_applications_job_id'))
            if _index_exists(bind, 'applications', 'idx_application_user_status'):
                batch_op.drop_index('idx_application_user_status')
            if _index_exists(bind, 'applications', 'idx_application_applied_at'):
                batch_op.drop_index('idx_application_applied_at')

    if "email_messages" in tables:
        with op.batch_alter_table('email_messages', schema=None) as batch_op:
            if _index_exists(bind, 'email_messages', 'idx_email_user_received'):
                batch_op.drop_index('idx_email_user_received')
            if _index_exists(bind, 'email_messages', 'ix_email_messages_user_id'):
                batch_op.drop_index(batch_op.f('ix_email_messages_user_id'))
            if _index_exists(bind, 'email_messages', 'ix_email_messages_sender_domain'):
                batch_op.drop_index(batch_op.f('ix_email_messages_sender_domain'))
            if _index_exists(bind, 'email_messages', 'ix_email_messages_received_at'):
                batch_op.drop_index(batch_op.f('ix_email_messages_received_at'))
            if _index_exists(bind, 'email_messages', 'ix_email_messages_matched_application_id'):
                batch_op.drop_index(batch_op.f('ix_email_messages_matched_application_id'))

    if "application_reminders" in tables:
        with op.batch_alter_table('application_reminders', schema=None) as batch_op:
            if _index_exists(bind, 'application_reminders', 'ix_application_reminders_user_id'):
                batch_op.drop_index(batch_op.f('ix_application_reminders_user_id'))
            if _index_exists(bind, 'application_reminders', 'ix_application_reminders_remind_at'):
                batch_op.drop_index(batch_op.f('ix_application_reminders_remind_at'))
            if _index_exists(bind, 'application_reminders', 'ix_application_reminders_application_id'):
                batch_op.drop_index(batch_op.f('ix_application_reminders_application_id'))

    if "application_events" in tables:
        with op.batch_alter_table('application_events', schema=None) as batch_op:
            if _index_exists(bind, 'application_events', 'ix_application_events_user_id'):
                batch_op.drop_index(batch_op.f('ix_application_events_user_id'))
            if _index_exists(bind, 'application_events', 'ix_application_events_application_id'):
                batch_op.drop_index(batch_op.f('ix_application_events_application_id'))
            if _index_exists(bind, 'application_events', 'idx_event_app_created'):
                batch_op.drop_index('idx_event_app_created')