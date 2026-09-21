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
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from config import (
    RATE_LIMIT_LOGIN_PER_MINUTE, RATE_LIMIT_REGISTER_PER_MINUTE, APP_PUBLIC_URL,
)
from database.connection import get_db
from models.models import User, Profile
from models.session import hash_token
from models.password_reset import PasswordResetToken, hash_reset_token
from models.email_verification import EmailVerificationToken, hash_verification_token
from schemas.schemas import (
    UserRegister, UserLogin, Token, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
)
from utils.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, set_auth_cookies, clear_auth_cookies,
    validate_password_strength, get_current_user,
    _verify_csrf, create_refresh_session, validate_refresh_session,
    revoke_refresh_session, revoke_all_user_sessions,
)
from utils.security_logging import log_auth_event, log_rate_limit_violation
from utils.rate_limiter import get_rate_limiter
from utils.client_ip import get_client_ip as _get_client_ip
from utils.mailer import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiter instance (Redis-backed with in-memory fallback)
_rate_limiter = get_rate_limiter()
# Client IP extraction is shared and trusted-proxy-aware (see utils/client_ip.py)


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
        "email_verified": bool(getattr(user, "email_verified", False)),
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
        email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()

    _issue_email_verification(db, user, client_ip)

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


# ─── Forgot Password ─────────────────────────────────────────
RESET_TOKEN_TTL_MINUTES = 30


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Request a password reset link.

    Always returns a generic 200 response — the response is identical whether
    or not the email exists, preventing account enumeration. Rate limited
    aggressively since each hit can trigger an outbound email.
    """
    client_ip = _get_client_ip(request)
    # Tight per-IP limit: email sending is a valuable side effect to abuse
    if not _rate_limiter.check("forgot_password", client_ip, 5, 3600):
        log_rate_limit_violation(
            endpoint="/api/auth/forgot-password", ip_address=client_ip, limit=5, window=3600,
        )
        # Identical body to the success case — no information leak
        return {"message": "If an account with that email exists, a reset link has been sent."}

    user = db.query(User).filter(User.email == data.email).first()
    if user:
        # Invalidate all previously issued, still-unused tokens for this user:
        # only the newest link ever works.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": datetime.utcnow()})

        raw_token = secrets.token_urlsafe(32)
        record = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
            request_ip=(client_ip or "unknown")[:45],
        )
        db.add(record)
        db.commit()

        reset_url = f"{APP_PUBLIC_URL}/reset-password?token={raw_token}"
        sent = send_password_reset_email(user.email, user.name, reset_url)
        log_auth_event(
            "password_reset_requested", user_id=user.id, ip_address=client_ip,
            success=True, detail="email_sent" if sent else "dev_fallback_logged",
        )

    # Identical response in every branch
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Consume a reset token and set a new password.

    - Token must exist, be unused, and be unexpired (single-use).
    - On success, revokes every active login session for the user.
    - Generic error messages — no hints about token state beyond what is
      necessary for UX (invalid/expired share one message).
    """
    client_ip = _get_client_ip(request)
    if not _rate_limiter.check("reset_password", client_ip, 10, 3600):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    if not data.token or len(data.token) > 128:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    token_hash = hash_reset_token(data.token)
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
    ).first()

    # Same generic error for unknown, used, and expired tokens
    if not record or record.is_used or record.is_expired:
        log_auth_event(
            "password_reset_failed", ip_address=client_ip, success=False,
            detail="invalid_token",
        )
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    user.hashed_password = get_password_hash(data.password)
    record.used_at = datetime.utcnow()

    # Security: a completed reset kills every active session everywhere
    revoked = revoke_all_user_sessions(db, user.id)
    db.commit()

    log_auth_event(
        "password_reset_completed", user_id=user.id, ip_address=client_ip,
        success=True, detail=f"revoked_{revoked}_sessions",
    )
    return {"message": "Password updated. You can now sign in with your new password."}


# ─── Email Verification ──────────────────────────────────
VERIFICATION_TOKEN_TTL_HOURS = 24


def _issue_email_verification(db: Session, user: User, ip_address: str = "") -> bool:
    """
    Create and (attempt to) send a verification email for a user.
    Invalidates all previously issued, still-unused tokens first — only the
    newest link ever works. Returns True when the email was actually sent.
    No-op for already-verified users or users without an email.
    """
    if getattr(user, "email_verified", False):
        return False

    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None),
    ).update({"used_at": datetime.utcnow()})

    raw_token = secrets.token_urlsafe(32)
    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS),
    )
    db.add(record)
    db.commit()

    verify_url = f"{APP_PUBLIC_URL}/verify-email?token={raw_token}"
    sent = send_verification_email(user.email, user.name, verify_url)
    log_auth_event(
        "email_verification_sent", user_id=user.id, ip_address=ip_address,
        success=True, detail="email_sent" if sent else "dev_fallback_logged",
    )
    return sent


@router.post("/send-verification")
def send_verification(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    (Re)send the verification email for the logged-in user.

    Always returns a generic 200 — identical body whether the user is already
    verified, unknown, or a fresh email went out — so the endpoint cannot be
    used to probe account state. Rate limited per-IP (email side effect).
    """
    client_ip = _get_client_ip(request)
    if not _rate_limiter.check("send_verification", client_ip, 5, 3600):
        log_rate_limit_violation(
            endpoint="/api/auth/send-verification", ip_address=client_ip, limit=5, window=3600,
        )
        return {"message": "If your email is not yet verified, a verification link has been sent."}

    if not getattr(user, "email_verified", False):
        _issue_email_verification(db, user, client_ip)

    return {"message": "If your email is not yet verified, a verification link has been sent."}


@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    """
    Consume a verification token and mark the user's email verified.

    Token must exist, be unused, and be unexpired (single-use). Generic error
    message for unknown/used/expired tokens — no state hints. Success logs the
    user out of the token-checking sense only; their session (if any) stays
    valid since verification never changes credentials.
    """
    client_ip = _get_client_ip(request)
    if not _rate_limiter.check("verify_email", client_ip, 20, 3600):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    if not data.token or len(data.token) > 128:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    token_hash = hash_verification_token(data.token)
    record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash,
    ).first()

    # Same generic error for unknown, used, and expired tokens
    if not record or record.is_used or record.is_expired:
        log_auth_event("email_verification_failed", ip_address=client_ip, success=False, detail="invalid_token")
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    user = db.query(User).filter(User.id == record.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    user.email_verified = True
    record.used_at = datetime.utcnow()
    db.commit()

    log_auth_event("email_verification_completed", user_id=user.id, ip_address=client_ip, success=True)
    return {"message": "Email verified successfully.", "email": user.email}


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
