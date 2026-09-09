"""
Tests for Google sign-in (OpenID Connect) flow — all external Google calls
are mocked; no real network or credentials needed.

Covers: state/session binding, expiry, replay, unverified email, account
linking vs creation, password-less users, and missing-configuration behavior.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


def _make_password_user(db, email="linkme@example.com", password="password123"):
    from models.models import User
    from utils.auth import get_password_hash
    user = User(email=email, name="Link Me", hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _db_session():
    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _mock_id_token(sub="google-sub-123", email="newgoogle@example.com", verified=True):
    return {
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "name": "Google User",
        "aud": "test-client-id",
        "iss": "https://accounts.google.com",
        "exp": datetime.utcnow().timestamp() + 3600,
    }


class TestGoogleSignInConfig:
    """Behavior when Google credentials are absent."""

    def test_auth_url_503_when_not_configured(self, test_client):
        with patch("routes.google_auth.GOOGLE_CLIENT_ID", ""), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", ""):
            resp = test_client.get("/api/auth/google/auth-url")
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


class TestGoogleSignInStart:
    """Starting the flow creates state + binding cookie."""

    def test_auth_url_returns_url_and_cookie(self, test_client):
        with patch("routes.google_auth.GOOGLE_CLIENT_ID", "test-client-id"), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", "test-secret"):
            resp = test_client.get("/api/auth/google/auth-url")

        assert resp.status_code == 200
        data = resp.json()
        assert data["auth_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "state=" in data["auth_url"]
        assert "openid" in data["auth_url"]
        # Session binding cookie must be set (HttpOnly)
        assert "rolio_oauth_session" in resp.cookies

    def test_auth_url_creates_db_state(self, test_client):
        from database.connection import SessionLocal
        from models.oauth_state import OAuthState

        with patch("routes.google_auth.GOOGLE_CLIENT_ID", "test-client-id"), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", "test-secret"):
            test_client.get("/api/auth/google/auth-url")

        db = SessionLocal()
        try:
            states = db.query(OAuthState).filter(
                OAuthState.flow_type == "google_signin").all()
            assert len(states) >= 1
            state = states[-1]
            assert state.user_id is None        # sign-in flow: no user yet
            assert state.session_id             # bound to a browser session
            assert not state.is_consumed
        finally:
            db.close()


class TestGoogleSignInCallback:
    """Callback validation: state, binding, expiry, replay, verification."""

    def _start_flow(self, test_client):
        with patch("routes.google_auth.GOOGLE_CLIENT_ID", "test-client-id"), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", "test-secret"):
            resp = test_client.get("/api/auth/google/auth-url")
        state = resp.json()["auth_url"].split("state=")[1].split("&")[0]
        session = resp.cookies.get("rolio_oauth_session")
        return state, session

    def _callback(self, test_client, state, session, sub="google-sub-123",
                  email="newgoogle@example.com", verified=True,
                  mock_verify=None):
        """Invoke callback with mocked token exchange + ID verification."""
        id_payload = mock_verify or _mock_id_token(sub=sub, email=email, verified=verified)

        def fake_verify(token, request, client_id):
            return id_payload

        with patch("routes.google_auth.GOOGLE_CLIENT_ID", "test-client-id"), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", "test-secret"), \
             patch("httpx.post") as mock_post, \
             patch("routes.google_auth.id_token.verify_oauth2_token", side_effect=fake_verify):
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"id_token": "fake-id-token", "access_token": "x"},
            )
            cookies = {"rolio_oauth_session": session} if session else {}
            return test_client.get(
                "/api/auth/google/callback",
                params={"code": "auth-code-123", "state": state},
                cookies=cookies,
                follow_redirects=False,
            )

    def test_successful_new_user_creation(self, test_client):
        state, session = self._start_flow(test_client)
        resp = self._callback(test_client, state, session)

        # Should redirect to onboarding (new user, not onboarded)
        assert resp.status_code in (302, 307)
        assert "/onboarding" in resp.headers["location"]
        # Session cookies must be set (same as password login)
        assert "rolio_access" in resp.cookies
        assert "rolio_refresh" in resp.cookies

        # User created with no password
        from database.connection import SessionLocal
        from models.models import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.google_sub == "google-sub-123").first()
            assert user is not None
            assert user.email == "newgoogle@example.com"
            assert user.hashed_password is None
            assert user.profile is not None
        finally:
            db.close()

    def test_existing_email_account_is_linked(self, test_client):
        from database.connection import SessionLocal
        from models.models import User

        _make_password_user(_db_session().__next__(), "linkme2@example.com") if False else None
        db = SessionLocal()
        try:
            _make_password_user(db, "linkme2@example.com")
        finally:
            db.close()

        state, session = self._start_flow(test_client)
        resp = self._callback(test_client, state, session,
                              email="linkme2@example.com")
        assert resp.status_code in (302, 307)

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "linkme2@example.com").first()
            assert user.google_sub == "google-sub-123"
            # Password preserved — account linking, not replacement
            assert user.hashed_password is not None
        finally:
            db.close()

    def test_missing_state_redirects_error(self, test_client):
        resp = test_client.get(
            "/api/auth/google/callback",
            params={"code": "x"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "google=error" in resp.headers["location"]

    def test_unknown_state_redirects_error(self, test_client):
        resp = test_client.get(
            "/api/auth/google/callback",
            params={"code": "x", "state": "bogus-state"},
            cookies={"rolio_oauth_session": "whatever"},
            follow_redirects=False,
        )
        assert "google=error" in resp.headers["location"]

    def test_session_binding_mismatch_rejected(self, test_client):
        state, session = self._start_flow(test_client)
        # Callback carrying a DIFFERENT session id (state fixation attempt /
        # flow started in another browser)
        resp = self._callback(test_client, state, session="attacker-session-value")
        assert "google=error" in resp.headers["location"]

    def test_expired_state_rejected(self, test_client):
        from database.connection import SessionLocal
        from models.oauth_state import OAuthState

        db = SessionLocal()
        try:
            expired = OAuthState(
                user_id=None, session_id="sess-exp",
                state_token="expired-google-state",
                created_at=datetime.utcnow() - timedelta(minutes=20),
                expires_at=datetime.utcnow() - timedelta(minutes=10),
                flow_type="google_signin",
            )
            db.add(expired)
            db.commit()
        finally:
            db.close()

        resp = self._callback(test_client, "expired-google-state", "sess-exp")
        assert "google=error" in resp.headers["location"]

    def test_replayed_state_rejected(self, test_client):
        state, session = self._start_flow(test_client)
        first = self._callback(test_client, state, session)
        assert "/onboarding" in first.headers["location"]

        # Replay with the same state — rejected even with the right session
        second = self._callback(test_client, state, session)
        assert "google=error" in second.headers["location"]

    def test_unverified_email_rejected(self, test_client):
        state, session = self._start_flow(test_client)
        resp = self._callback(test_client, state, session, verified=False,
                              email="unverified@example.com")
        assert "google=error" in resp.headers["location"]
        # No user must have been created
        from database.connection import SessionLocal
        from models.models import User
        db = SessionLocal()
        try:
            assert db.query(User).filter(
                User.email == "unverified@example.com").first() is None
        finally:
            db.close()

    def test_token_exchange_failure_redirects_error(self, test_client):
        state, session = self._start_flow(test_client)

        with patch("routes.google_auth.GOOGLE_CLIENT_ID", "test-client-id"), \
             patch("routes.google_auth.GOOGLE_CLIENT_SECRET", "test-secret"), \
             patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=400, json=lambda: {})
            resp = test_client.get(
                "/api/auth/google/callback",
                params={"code": "bad-code", "state": state},
                cookies={"rolio_oauth_session": session},
                follow_redirects=False,
            )
        assert "google=error" in resp.headers["location"]


class TestPasswordlessUserSecurity:
    """OAuth-only users must not be loginable via the password endpoint."""

    def test_password_login_rejected_for_oauth_user(self, test_client):
        from database.connection import SessionLocal
        from models.models import User

        db = SessionLocal()
        try:
            user = User(email="oauthonly@example.com", name="OAuth Only",
                        hashed_password=None, google_sub="google-sub-oauth")
            db.add(user)
            db.commit()
        finally:
            db.close()

        resp = test_client.post("/api/auth/login", json={
            "email": "oauthonly@example.com", "password": "anypassword",
        })
        assert resp.status_code == 401
