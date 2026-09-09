"""
Authentication utilities.

Security design:
- Access tokens are short-lived (default 30 min) and stored in HttpOnly cookies.
- Refresh tokens are longer-lived, rotate on each use, and are persisted as hashed sessions.
- CSRF protection uses a double-submit cookie pattern.
- Passwords are validated for minimum length before hashing.
- Tokens are NEVER exposed to JavaScript or stored in localStorage.
- Cookie Secure flag is environment-aware (False for localhost dev, True for production).
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

# PyJWT (python-jose is unmaintained with unpatched advisories). PyJWTError
# is the base class matching jose's JWTError role for our HS256 usage.
import jwt as pyjwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session as DBSession

from config import (
    SECRET_KEY, CSRF_SECRET, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    IS_PRODUCTION,
)
from database.connection import get_db
from models.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cookie names
ACCESS_COOKIE = "rolio_access"
REFRESH_COOKIE = "rolio_refresh"
CSRF_COOKIE = "rolio_csrf"

# Cookie configuration — environment-aware
COOKIE_SAMESITE = "strict" if IS_PRODUCTION else "lax"
COOKIE_SECURE = IS_PRODUCTION  # Only Secure in production (HTTPS)


# ─── Password Policy ─────────────────────────────────────────
MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> None:
    """Enforce minimum password length. Raises HTTPException on failure."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.",
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ─── Token Creation ──────────────────────────────────────────
def create_access_token(data: dict) -> str:
    """Create a short-lived access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Create a long-lived refresh token. Returns (token, jti)."""
    jti = secrets.token_urlsafe(16)
    to_encode = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": jti,
    }
    token = pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on any failure."""
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ─── CSRF Protection ─────────────────────────────────────────
def generate_csrf_token() -> str:
    """Generate a CSRF token for double-submit cookie pattern."""
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set all auth cookies on the response. Tokens are never accessible to JS."""
    secure = COOKIE_SECURE
    # Access token cookie — short-lived, HttpOnly, SameSite
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=secure,
        path="/",
    )
    # Refresh token cookie — longer-lived, HttpOnly, narrow path
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=secure,
        path="/api/auth/refresh",  # Only sent to refresh endpoint
    )
    # CSRF token cookie — NOT HttpOnly (must be readable by JS to send in header)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,
        samesite=COOKIE_SAMESITE,
        secure=secure,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies on logout."""
    response.delete_cookie(key=ACCESS_COOKIE, path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth/refresh", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    response.delete_cookie(key=CSRF_COOKIE, path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)


def _get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
    """Extract a token from a specific cookie."""
    return request.cookies.get(cookie_name)


def _verify_csrf(request: Request) -> None:
    """
    Verify CSRF token for state-changing requests (POST, PUT, DELETE, PATCH).
    Uses double-submit cookie pattern: the CSRF token must be present in both
    the cookie and the X-CSRF-Token header, and they must match.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return  # Safe methods don't need CSRF

    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch",
        )


# ─── Session Management ─────────────────────────────────────
def create_refresh_session(
    db: DBSession, user_id: int, token: str, jti: str,
    user_agent: str = "", ip_address: str = "",
) -> "RefreshSession":
    """Persist a refresh token session in the database."""
    from models.session import RefreshSession, hash_token
    session = RefreshSession(
        user_id=user_id,
        token_hash=hash_token(token),
        jti=jti,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent[:500],
        ip_address=ip_address[:45],
    )
    db.add(session)
    db.commit()
    return session


def revoke_refresh_session(db: DBSession, token_hash: str, replaced_by_id: int = None) -> bool:
    """Revoke a refresh session. Returns True if a session was revoked."""
    from models.session import RefreshSession
    session = db.query(RefreshSession).filter(
        RefreshSession.token_hash == token_hash,
        RefreshSession.revoked_at.is_(None),
    ).first()
    if not session:
        return False
    session.revoked_at = datetime.utcnow()
    if replaced_by_id:
        session.replaced_by_id = replaced_by_id
    db.commit()
    return True


def revoke_all_user_sessions(db: DBSession, user_id: int) -> int:
    """Revoke all active sessions for a user. Returns count of revoked sessions."""
    from models.session import RefreshSession
    from sqlalchemy import and_
    count = db.query(RefreshSession).filter(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})
    db.commit()
    return count


def validate_refresh_session(db: DBSession, token: str) -> Optional["RefreshSession"]:
    """
    Validate a refresh token against the persisted sessions.
    Returns the session if valid, None if invalid.
    Handles reuse detection: if a revoked token is reused, revokes all sessions.
    """
    from models.session import RefreshSession, hash_token
    token_hash = hash_token(token)
    session = db.query(RefreshSession).filter(
        RefreshSession.token_hash == token_hash,
    ).first()

    if not session:
        return None

    # Token is expired
    if session.is_expired:
        return None

    # Token was revoked — potential reuse attack
    if session.revoked_at is not None:
        # Revoke ALL active sessions for this user (security event)
        revoke_all_user_sessions(db, session.user_id)
        session.is_reused = True
        db.commit()
        return None

    return session


# ─── User Extraction ─────────────────────────────────────────
async def get_current_user(
    request: Request,
    db: DBSession = Depends(get_db),
) -> User:
    """
    Extract the authenticated user from the HttpOnly access cookie.
    Also verifies CSRF on state-changing requests.
    """
    # Verify CSRF on mutating requests
    _verify_csrf(request)

    token = _get_token_from_cookie(request, ACCESS_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return user


async def get_optional_user(
    request: Request,
    db: DBSession = Depends(get_db),
) -> Optional[User]:
    """Extract user if authenticated, return None otherwise. No CSRF check."""
    token = _get_token_from_cookie(request, ACCESS_COOKIE)
    if not token:
        return None

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None
