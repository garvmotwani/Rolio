import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.connection import Base
from config import DATABASE_URL

# Import all models so Alembic knows about them — these are side-effect
# imports: they register tables on Base.metadata for create_all/autogenerate.
import models.models  # noqa: F401
import models.email_models  # noqa: F401
import models.session  # noqa: F401
import models.oauth_state  # noqa: F401
import models.password_reset  # noqa: F401
import models.email_verification  # noqa: F401
# Alembic Config object
config = context.config

# Set the database URL from our config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Our models' metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
