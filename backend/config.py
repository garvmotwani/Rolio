"""
Rolio application configuration.

All secrets and environment-specific values are loaded from environment variables.
In production, required settings are validated at startup — the app refuses to start
if critical secrets are missing or use insecure defaults.
"""
import os
import sys
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("rolio.config")


def _require_env(key: str, default: str | None = None, allow_empty: bool = False) -> str:
    """Read an environment variable. In production, fail fast if missing."""
    value = os.getenv(key, default)
    env_name = os.getenv("ROLIO_ENV", "development")
    if env_name == "production" and (value is None or (not allow_empty and value == "")):
        logger.critical(f"Required environment variable {key} is not set. Exiting.")
        sys.exit(1)
    if value is None:
        value = default or ""
    return value


# ─── Environment ─────────────────────────────────────────────
ENV_NAME = os.getenv("ROLIO_ENV", "development")
IS_PRODUCTION = ENV_NAME == "production"

# ─── Security ────────────────────────────────────────────────
# JWT signing secret — MUST be set in production. The default here is
# a random value for development only; production deployments must
# provide a strong, unique secret via ROLIO_SECRET_KEY.
_secret_key = os.getenv("ROLIO_SECRET_KEY", "")
if not _secret_key:
    if IS_PRODUCTION:
        logger.critical("ROLIO_SECRET_KEY must be set in production.")
        sys.exit(1)
    else:
        _secret_key = secrets.token_urlsafe(48)
        logger.warning(
            "No ROLIO_SECRET_KEY set — using a random development key. "
            "Sessions will not persist across restarts."
        )
SECRET_KEY = _secret_key
ALGORITHM = "HS256"

# Token lifetimes (minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# CSRF — used for cookie-based auth state protection
CSRF_SECRET = os.getenv("CSRF_SECRET", secrets.token_urlsafe(32) if not IS_PRODUCTION else "")
if IS_PRODUCTION and not CSRF_SECRET:
    logger.critical("CSRF_SECRET must be set in production.")
    sys.exit(1)

# Encryption key for external OAuth tokens at rest (Fernet-compatible 32-byte urlsafe base64).
# Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")

# Validate the encryption key ONCE at configuration load.
# - Production: fail fast if the key is missing or not a valid Fernet key.
# - Development: fall back to an ephemeral key — encrypted Gmail tokens will NOT
#   survive a restart (documented limitation, re-connect Gmail after restart).
TOKEN_ENCRYPTION_KEY_VALID = False
if TOKEN_ENCRYPTION_KEY:
    try:
        from cryptography.fernet import Fernet as _Fernet
        _Fernet(TOKEN_ENCRYPTION_KEY.encode())
        TOKEN_ENCRYPTION_KEY_VALID = True
    except Exception:
        TOKEN_ENCRYPTION_KEY_VALID = False
        if IS_PRODUCTION:
            logger.critical("TOKEN_ENCRYPTION_KEY is set but is not a valid Fernet key. Exiting.")
            sys.exit(1)
        logger.warning("TOKEN_ENCRYPTION_KEY is invalid — an ephemeral key will be used. "
                       "Encrypted Gmail tokens will NOT survive a restart.")
else:
    if IS_PRODUCTION:
        logger.critical("TOKEN_ENCRYPTION_KEY must be set in production (Gmail token encryption). Exiting.")
        sys.exit(1)
    logger.warning("TOKEN_ENCRYPTION_KEY not set — using an ephemeral dev key. "
                   "Encrypted Gmail tokens will NOT survive a restart. "
                   "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")

# ─── Database ────────────────────────────────────────────────
DATABASE_URL = _require_env("DATABASE_URL", default="sqlite:///./rolio.db")

# ─── HTTPS enforcement ───────────────────────────────────────
# Production deployments MUST serve traffic over HTTPS. When FORCE_HTTPS is
# true (auto-enabled in production), every plain-HTTP request except the
# health check is redirected to https:// with the same path/query.
#
# The app is expected to sit behind a TLS-terminating reverse proxy (nginx,
# Caddy, cloud load balancer). Trust of X-Forwarded-Proto is controlled by
# TRUSTED_PROXIES so a direct client cannot spoof the scheme and bypass the
# redirect.
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "true" if IS_PRODUCTION else "false").lower() in ("1", "true", "yes")
# Comma-separated list of proxy IPs/networks allowed to set X-Forwarded-*.
# "*" trusts every hop (ONLY appropriate when the app is not directly
# reachable, e.g. bound to a private Docker network behind one proxy).
TRUSTED_PROXIES = [
    p.strip() for p in os.getenv("TRUSTED_PROXIES", "").split(",") if p.strip()
]

# ─── Frontend / CORS ─────────────────────────────────────────
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
BACKEND_PUBLIC_ORIGIN = os.getenv("BACKEND_PUBLIC_ORIGIN", "http://localhost:8001")
APP_PUBLIC_URL = os.getenv("APP_PUBLIC_URL", "http://localhost:3000")

# ─── Google OAuth ────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", f"{BACKEND_PUBLIC_ORIGIN}/api/gmail/callback")

# ─── AI Services ─────────────────────────────────────────────
NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-super-120b-a12b")
NEMOTRON_NANO_MODEL = os.getenv("NEMOTRON_NANO_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")

# ─── Job Search ──────────────────────────────────────────────
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")
JOB_API_KEY = os.getenv("JOB_API_KEY", "")

# ─── Uploads ─────────────────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx"}

# ─── Rate Limiting ───────────────────────────────────────────
RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
RATE_LIMIT_REGISTER_PER_MINUTE = int(os.getenv("RATE_LIMIT_REGISTER_PER_MINUTE", "5"))
RATE_LIMIT_AI_PER_MINUTE = int(os.getenv("RATE_LIMIT_AI_PER_MINUTE", "20"))
RATE_LIMIT_JSEARCH_PER_MINUTE = int(os.getenv("RATE_LIMIT_JSEARCH_PER_MINUTE", "30"))
RATE_LIMIT_UPLOAD_PER_HOUR = int(os.getenv("RATE_LIMIT_UPLOAD_PER_HOUR", "10"))
