"""
Pytest configuration and fixtures for Rolio backend tests.

Test isolation:
- Uses a separate SQLite database for tests (not the production Supabase).
- Rate limiters are cleared between tests.
- All test uploads use a temporary directory.
"""
import os
import sys
import tempfile
import pytest

# Force test environment before importing the app
os.environ["ROLIO_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///./test_rolio.db"
# Use a random encryption key for tests
os.environ["TOKEN_ENCRYPTION_KEY"] = ""
# Keep tests hermetic: point Redis at an unreachable endpoint so the rate
# limiter and caches fall back to in-memory storage. Otherwise, when a Redis
# is reachable (e.g. the Docker stack exposes :6379), rate-limit state would
# persist in Redis across tests and cause cross-test 429 pollution.
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Override config before importing app
import config
config.ENV_NAME = "test"
config.IS_PRODUCTION = False
config.DATABASE_URL = "sqlite:///./test_rolio.db"
config.COOKIE_SECURE = False
config.TOKEN_ENCRYPTION_KEY = ""
config.REDIS_URL = "redis://127.0.0.1:1/0"

from fastapi.testclient import TestClient
from database.connection import engine, Base, SessionLocal

# Create all tables in the test database
from models.models import *
from models.session import RefreshSession
from models.email_models import *
from models.oauth_state import OAuthState

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create clean tables for each test and clean up after."""
    # Clear all data between tests
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(table.delete())
            except Exception:
                pass
        conn.commit()
    yield
    # Clean up after
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(table.delete())
            except Exception:
                pass
        conn.commit()


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate-limiter state before and after each test.

    Clears every module-level limiter instance's in-memory store (tests run
    with the in-memory fallback — see REDIS_URL override above).
    """
    def _clear_all():
        try:
            from utils.rate_limiter import _memory_store
            _memory_store.clear()
        except ImportError:
            pass
        # Every routes module holds its own limiter instance
        import sys as _sys
        for mod in list(_sys.modules.values()):
            limiter = getattr(mod, "_rate_limiter", None)
            store = getattr(limiter, "_memory_store", None)
            if store is not None:
                store.clear()

    _clear_all()
    yield
    _clear_all()


@pytest.fixture
def test_client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def demo_user_credentials():
    """Return demo user credentials."""
    return {"email": "demo@rolio.com", "password": "password123"}


@pytest.fixture
def registered_user(test_client):
    """Register a fresh user and return credentials."""
    creds = {"email": "testuser@example.com", "password": "securepassword123", "name": "Test User"}
    resp = test_client.post("/api/auth/register", json=creds)
    assert resp.status_code == 200
    return creds


from main import app  # Import after env override
