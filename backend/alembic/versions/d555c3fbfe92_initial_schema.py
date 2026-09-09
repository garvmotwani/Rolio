"""initial schema

Revision ID: d555c3fbfe92
Revises:
Create Date: 2026-09-02 05:57:45.163945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd555c3fbfe92'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the complete schema from the SQLAlchemy model metadata.

    This is the canonical initial schema. All tables (core models, refresh
    sessions, OAuth states, Gmail/email models) are created from the model
    definitions in one step so a fresh deployment works end-to-end.
    Subsequent migrations only alter the schema incrementally.
    """
    from database.connection import Base
    # Import every model module so all tables are registered on Base.metadata
    from models.models import (  # noqa: F401
        User, Profile, Skill, Experience, Education, Project, Resume,
        Company, Job, SavedJob, Application, Notification, SearchHistory,
    )
    from models.session import RefreshSession  # noqa: F401
    from models.email_models import (  # noqa: F401
        GmailToken, EmailMessage, EmailSyncLog, ApplicationEvent,
        ApplicationReminder,
    )
    from models.oauth_state import OAuthState  # noqa: F401

    # create_all is idempotent (checkfirst=True) — safe on both fresh and
    # partially-initialized databases.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    from database.connection import Base
    from models.models import (  # noqa: F401
        User, Profile, Skill, Experience, Education, Project, Resume,
        Company, Job, SavedJob, Application, Notification, SearchHistory,
    )
    from models.session import RefreshSession  # noqa: F401
    from models.email_models import (  # noqa: F401
        GmailToken, EmailMessage, EmailSyncLog, ApplicationEvent,
        ApplicationReminder,
    )
    from models.oauth_state import OAuthState  # noqa: F401

    Base.metadata.drop_all(bind=op.get_bind())