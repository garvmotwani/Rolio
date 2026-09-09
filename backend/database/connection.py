import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL, ENV_NAME, IS_PRODUCTION

logger = logging.getLogger("rolio.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Test connectivity — in development only, fall back to SQLite if the primary
# database is unreachable (e.g. Docker not running). In production we FAIL FAST:
# silently switching to SQLite would cause data loss and wrong behavior.
try:
    _test_engine = create_engine(DATABASE_URL)
    with _test_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Primary database connected")
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
except Exception as e:
    if IS_PRODUCTION or ENV_NAME == "production":
        logger.critical(
            "Primary database unreachable in production mode. Refusing to start: %s",
            str(e)[:150],
        )
        raise
    logger.warning("Primary DB unreachable (%s), using SQLite fallback", str(e)[:100])
    fallback_url = "sqlite:///./rolio_fallback.db"
    engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
    logger.info("Using SQLite fallback: %s", fallback_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis URL — lazy import to avoid hard dependency in tests
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis():
    """Get Redis client for rate limiting and caching. Returns None if unavailable."""
    try:
        from redis import Redis
        r = Redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()