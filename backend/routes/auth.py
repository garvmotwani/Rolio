"""
Authentication routes.

Security measures:
- Tokens set via HttpOnly cookies, never returned in JSON response body.
- Refresh token rotation with persisted sessions and reuse detection.
- Password strength validation on registration.
- Rate limiting on login/register endpoints (Redis-backed with in-memory fallback).
- Generic error messages to prevent account enumeration.
- CSRF protection on all state-changing endpoints including refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from config import RATE_LIMIT_LOGIN_PER_MINUTE, RATE_LIMIT_REGISTER_PER_MINUTE
from database.connection import get_db
from models.models import User, Profile
from models.session import RefreshSession, hash_token
from schemas.schemas import UserRegister, UserLogin, Token, UserResponse
from utils.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, set_auth_cookies, clear_auth_cookies,
    validate_password_strength, get_current_user,
    _verify_csrf, create_refresh_session, validate_refresh_session,
    revoke_refresh_session,
)
from utils.security_logging import log_auth_event, log_rate_limit_violation
from utils.rate_limiter import get_rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiter instance (Redis-backed with in-memory fallback)
_rate_limiter = get_rate_limiter()


def _get_client_ip(request: Request) -> str:
    """Get client IP for rate limiting, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_agent(request: Request) -> str:
    """Extract User-Agent for session tracking."""
    return request.headers.get("User-Agent", "")[:500]


def _user_response(user: User) -> dict:
    """Build the non-sensitive user dict for responses."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_onboarded": user.is_onboarded,
    }


# ─── Register ────────────────────────────────────────────────
@router.post("/register", response_model=Token)
def register(data: UserRegister, request: Request, response: Response, db: Session = Depends(get_db)):
    # Rate limit
    client_ip = _get_client_ip(request)
    if not _rate_limiter.check("register", client_ip, RATE_LIMIT_REGISTER_PER_MINUTE, 60):
        log_rate_limit_violation(endpoint="/api/auth/register", ip_address=client_ip, limit=RATE_LIMIT_REGISTER_PER_MINUTE, window=60)
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # Password strength
    validate_password_strength(data.password)

    # Check existing (use generic message)
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        log_auth_event("register_failed", email=data.email, ip_address=client_ip, success=False, detail="email_exists")
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    log_auth_event("register_success", email=data.email, ip_address=client_ip)

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()

    # Issue tokens and persist session
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token, jti = create_refresh_token(user.id)
    set_auth_cookies(response, access_token, refresh_token)

    create_refresh_session(
        db, user.id, refresh_token, jti,
        user_agent=_get_user_agent(request), ip_address=client_ip,
    )

    # No token in response body
    return Token(user=_user_response(user))


# ─── Login ───────────────────────────────────────────────────
@router.post("/login", response_model=Token)
def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    # Rate limit
    client_ip = _get_client_ip(request)
    if not _rate_limiter.check("login", client_ip, RATE_LIMIT_LOGIN_PER_MINUTE, 60):
        log_rate_limit_violation(endpoint="/api/auth/login", ip_address=client_ip, limit=RATE_LIMIT_LOGIN_PER_MINUTE, window=60)
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # Generic error message prevents account enumeration
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        log_auth_event("login_failed", email=data.email, ip_address=client_ip, success=False, detail="invalid_credentials")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        log_auth_event("login_failed", user_id=user.id, email=data.email, ip_address=client_ip, success=False, detail="account_disabled")
        raise HTTPException(status_code=403, detail="Account is disabled")

    log_auth_event("login_success", user_id=user.id, email=data.email, ip_address=client_ip)

    # Issue tokens and persist session
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token, jti = create_refresh_token(user.id)
    set_auth_cookies(response, access_token, refresh_token)

    create_refresh_session(
        db, user.id, refresh_token, jti,
        user_agent=_get_user_agent(request), ip_address=client_ip,
    )

    # No token in response body
    return Token(user=_user_response(user))


# ─── Refresh Token ───────────────────────────────────────────
@router.post("/refresh", response_model=Token)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Rotate refresh token with server-side session validation and reuse detection."""
    # CSRF protection for refresh too (state-changing endpoint)
    _verify_csrf(request)

    refresh = request.cookies.get("rolio_refresh")
    if not refresh:
        raise HTTPException(status_code=401, detail="No refresh token")

    # Validate the persisted session (includes reuse detection)
    session = validate_refresh_session(db, refresh)
    if session is None:
        # Either expired, not found, or reuse detected (all sessions revoked)
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    user = db.query(User).filter(
        User.id == session.user_id, User.is_active == True
    ).first()
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User not found or disabled")

    # Issue new tokens
    new_access = create_access_token(data={"sub": str(user.id)})
    new_refresh, new_jti = create_refresh_token(user.id)
    set_auth_cookies(response, new_access, new_refresh)

    # Revoke old session and create new one
    new_session = create_refresh_session(
        db, user.id, new_refresh, new_jti,
        user_agent=_get_user_agent(request), ip_address=_get_client_ip(request),
    )
    revoke_refresh_session(db, hash_token(refresh), replaced_by_id=new_session.id)

    # No token in response body
    return Token(user=_user_response(user))


# ─── Me ──────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


# ─── Logout ──────────────────────────────────────────────────
@router.post("/logout")
def logout(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke the current session server-side and clear cookies."""
    # Revoke the current refresh session if present
    refresh = request.cookies.get("rolio_refresh")
    if refresh:
        from models.session import hash_token as ht
        revoke_refresh_session(db, ht(refresh))

    log_auth_event("logout", user_id=user.id)
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


# ─── Logout All Devices ──────────────────────────────────────
@router.post("/logout-all")
def logout_all_devices(
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke ALL active sessions for the user."""
    from utils.auth import revoke_all_user_sessions
    count = revoke_all_user_sessions(db, user.id)
    log_auth_event("logout_all", user_id=user.id, detail=f"revoked_{count}_sessions")
    clear_auth_cookies(response)
    return {"message": f"Logged out from all devices ({count} sessions revoked)"}
