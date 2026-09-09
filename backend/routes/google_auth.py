"""
Google sign-in (OpenID Connect) — one-click registration/login.

Security design:
- Standard server-side OAuth flow with a DB-persisted one-time state
  (10-minute expiry, replay-resistant), reusing the OAuthState model.
- Sign-in states carry a random session_id (stored in a cookie on the
  backend origin) so the callback can only complete in the browser that
  started the flow. user_id is NULL for sign-in states.
- The returned ID token is verified against Google's public keys: signature
  (via google.oauth2.id_token), audience (client_id), issuer, and expiry.
- Users are created on first sign-in with a NULL password (OAuth-only);
  existing email matches are linked by setting google_sub. Password-less
  accounts can never be logged into via the password endpoint (verify
  handles None safely).
- Sessions are issued exactly like password login: HttpOnly access cookie +
  rotating refresh session. No token ever reaches the browser's JS.
- The browser is redirected to a clean frontend URL — no tokens in URLs.
  Onboarding intent is passed via the path (/onboarding vs /dashboard).
"""
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleAuthRequest

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APP_PUBLIC_URL, BACKEND_PUBLIC_ORIGIN
from database.connection import get_db
from models.models import User, Profile
from models.oauth_state import OAuthState
from utils.auth import (
    create_access_token, create_refresh_token, set_auth_cookies,
    create_refresh_session,
)
from config import IS_PRODUCTION
from utils.security_logging import log_auth_event
from utils.rate_limiter import get_rate_limiter

logger = logging.getLogger("rolio.google_auth")

router = APIRouter(prefix="/api/auth/google", tags=["google-signin"])

_rate_limiter = get_rate_limiter()

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

SIGNIN_STATE_COOKIE = "rolio_oauth_session"
# Cookie lifetime just needs to cover the OAuth round-trip
STATE_COOKIE_MAX_AGE = 600


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/auth-url")
def get_google_auth_url(request: Request, db: Session = Depends(get_db)):
    """
    Start the Google sign-in flow. Anonymous — this IS the login endpoint.

    Creates a one-time state bound to a random session id, returns the
    Google consent URL, and sets a short-lived cookie carrying the session
    id so only the initiating browser can complete the flow.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server.")

    client_ip = _client_ip(request)
    if not _rate_limiter.check("google_signin_start", client_ip, 20, 60):
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

    session_id = secrets.token_urlsafe(32)
    state_token = secrets.token_urlsafe(32)

    oauth_state = OAuthState(
        user_id=None,  # sign-in flow: no user yet
        session_id=session_id,
        state_token=state_token,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        flow_type="google_signin",
    )
    db.add(oauth_state)
    db.commit()

    params = (
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={BACKEND_PUBLIC_ORIGIN}/api/auth/google/callback"
        f"&response_type=code"
        f"&scope={'openid email profile'.replace(' ', '%20')}"
        f"&state={state_token}"
        f"&prompt=select_account"
    )
    auth_url = AUTH_URI + params

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"auth_url": auth_url})
    response.set_cookie(
        key=SIGNIN_STATE_COOKIE,
        value=session_id,
        max_age=STATE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=IS_PRODUCTION,  # Secure only over HTTPS/production
    )
    return response


@router.get("/callback")
def google_signin_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """
    Google redirect target. Validates state + session binding, verifies the
    ID token against Google's public keys, then links or creates the user
    and issues the same HttpOnly session cookies as password login.
    """
    redirect_base = APP_PUBLIC_URL

    # ── 1. Basic parameter validation ──────────────────────
    if error or not code or not state:
        logger.warning("Google sign-in callback missing code/state or user denied: %s", error or "missing params")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # ── 2. Consume the state (one-time, expiry-checked) ────
    oauth_state = db.query(OAuthState).filter(
        OAuthState.state_token == state,
        OAuthState.flow_type == "google_signin",
    ).first()

    if not oauth_state:
        logger.warning("Google sign-in callback: unknown state")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    if oauth_state.is_consumed:
        logger.warning("Google sign-in state replay detected")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    if datetime.utcnow() > oauth_state.expires_at:
        db.delete(oauth_state)
        db.commit()
        logger.warning("Google sign-in state expired")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # ── 3. Session binding: same browser that started the flow ──
    cookie_session = request.cookies.get(SIGNIN_STATE_COOKIE)
    if not oauth_state.session_id or not cookie_session or cookie_session != oauth_state.session_id:
        logger.warning("Google sign-in session binding mismatch")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # Consume atomically before any external call
    oauth_state.is_consumed = True
    db.commit()

    # ── 4. Exchange the code (server-side only) ────────────
    try:
        import httpx
        redirect_uri = f"{_backend_origin(request)}/api/auth/google/callback"
        token_resp = httpx.post(
            TOKEN_URI,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %d", token_resp.status_code)
            return RedirectResponse(url=f"{redirect_base}/login?google=error")
        tokens = token_resp.json()
        id_token_value = tokens.get("id_token")
        if not id_token_value:
            logger.error("Google token exchange returned no id_token")
            return RedirectResponse(url=f"{redirect_base}/login?google=error")
    except Exception as e:
        logger.error("Google token exchange error: %s", type(e).__name__)
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # ── 5. Verify the ID token against Google's public keys ──
    try:
        userinfo = id_token.verify_oauth2_token(
            id_token_value,
            GoogleAuthRequest(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        logger.error("Google ID token verification failed: %s", type(e).__name__)
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    google_sub = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower().strip()
    email_verified = userinfo.get("email_verified", False)
    name = (userinfo.get("name") or email.split("@")[0] or "User").strip()[:100]

    if not google_sub or not email:
        logger.error("Google ID token missing sub/email")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")
    if not email_verified:
        # Google marks unverified emails; refuse to bind an account to them
        logger.warning("Google sign-in with unverified email attempted")
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # ── 6. Link or create the user ─────────────────────────
    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        # Link by verified email if the account exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_sub = google_sub
            log_auth_event("google_link", user_id=user.id, email=email, ip_address=_client_ip(request))
        else:
            user = User(email=email, name=name, google_sub=google_sub, hashed_password=None)
            db.add(user)
            db.flush()  # get user.id before creating profile
            db.add(Profile(user_id=user.id))
            log_auth_event("google_register", user_id=user.id, email=email, ip_address=_client_ip(request))
        db.commit()
        db.refresh(user)
    else:
        log_auth_event("google_login", user_id=user.id, email=email, ip_address=_client_ip(request))

    if not user.is_active:
        return RedirectResponse(url=f"{redirect_base}/login?google=error")

    # ── 7. Issue sessions exactly like password login ──────
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token, jti = create_refresh_token(user.id)

    # New users go to onboarding ("add details later"); existing skip it
    dest = "/onboarding" if not user.is_onboarded else "/dashboard"
    redirect = RedirectResponse(url=f"{redirect_base}{dest}")

    # Cookies must be set directly on the returned redirect response
    # (the injected Response parameter is discarded for custom returns).
    set_auth_cookies(redirect, access_token, refresh_token)
    redirect.delete_cookie(SIGNIN_STATE_COOKIE, path="/")

    create_refresh_session(
        db, user.id, refresh_token, jti,
        user_agent=request.headers.get("User-Agent", "")[:500],
        ip_address=_client_ip(request),
    )

    return redirect


def _backend_origin(request: Request) -> str:
    """Public origin of this backend (used as the OAuth redirect_uri)."""
    return BACKEND_PUBLIC_ORIGIN
