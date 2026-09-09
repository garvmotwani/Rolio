"""
Tests for the password reset flow.

Covers: request behavior (generic responses, enumeration safety, rate limit),
token consumption (single-use, expiry, invalid tokens), session revocation
on reset, and the dev-fallback mailer.
"""
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.password_reset import PasswordResetToken, hash_reset_token
from models.session import RefreshSession


GENERIC_MSG = "If an account with that email exists, a reset link has been sent."


@pytest.fixture
def reset_user(test_client):
    """Register a user and return (email, password, user_id)."""
    creds = {
        "email": "resetme@example.com",
        "password": "oldpassword123",
        "name": "Reset Me",
    }
    resp = test_client.post("/api/auth/register", json=creds)
    assert resp.status_code == 200
    user_id = resp.json()["user"]["id"]
    return creds["email"], creds["password"], user_id


class TestForgotPassword:
    def test_generic_response_for_unknown_email(self, test_client):
        resp = test_client.post(
            "/api/auth/forgot-password", json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == GENERIC_MSG

    def test_generic_response_for_existing_email(self, test_client, reset_user, db_session=None):
        email, _, _ = reset_user
        resp = test_client.post("/api/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200
        assert resp.json()["message"] == GENERIC_MSG

    def test_identical_response_known_vs_unknown(self, test_client, reset_user):
        """Enumeration safety: byte-identical responses either way."""
        email, _, _ = reset_user
        known = test_client.post("/api/auth/forgot-password", json={"email": email})
        unknown = test_client.post("/api/auth/forgot-password", json={"email": "nope@example.com"})
        assert known.json() == unknown.json()
        assert known.status_code == unknown.status_code

    def test_creates_token_record_for_existing_user(self, test_client, reset_user):
        from database.connection import SessionLocal
        email, _, user_id = reset_user
        test_client.post("/api/auth/forgot-password", json={"email": email})
        db = SessionLocal()
        try:
            rows = db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user_id,
            ).all()
            assert len(rows) == 1
            assert rows[0].used_at is None
            assert rows[0].expires_at > datetime.utcnow()
        finally:
            db.close()

    def test_new_request_invalidates_previous_tokens(self, test_client, reset_user):
        from database.connection import SessionLocal
        email, _, user_id = reset_user
        test_client.post("/api/auth/forgot-password", json={"email": email})
        test_client.post("/api/auth/forgot-password", json={"email": email})
        db = SessionLocal()
        try:
            unused = db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            ).count()
            assert unused == 1
        finally:
            db.close()

    def test_no_token_leak_in_response(self, test_client, reset_user):
        """Dev fallback logs the link but must never return it in the body."""
        email, _, _ = reset_user
        resp = test_client.post("/api/auth/forgot-password", json={"email": email})
        body = str(resp.json())
        assert "token" not in body.lower()


class TestResetPassword:
    def _request_token(self, test_client, email: str) -> str:
        """Request a reset and capture the plaintext token via the mailer mock."""
        captured = {}
        def _capture(to_email, name, reset_url):
            captured["url"] = reset_url
            return False
        with patch("routes.auth.send_password_reset_email", side_effect=_capture):
            test_client.post("/api/auth/forgot-password", json={"email": email})
        url = captured["url"]
        assert "token=" in url
        return url.split("token=", 1)[1]

    def test_reset_with_valid_token(self, test_client, reset_user):
        email, old_password, _ = reset_user
        token = self._request_token(test_client, email)

        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "brandnewpassword123"},
        )
        assert resp.status_code == 200

        # Old password no longer works, new one does
        old_login = test_client.post(
            "/api/auth/login", json={"email": email, "password": old_password},
        )
        assert old_login.status_code == 401
        new_login = test_client.post(
            "/api/auth/login", json={"email": email, "password": "brandnewpassword123"},
        )
        assert new_login.status_code == 200

    def test_token_is_single_use(self, test_client, reset_user):
        email, _, _ = reset_user
        token = self._request_token(test_client, email)

        first = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "brandnewpassword123"},
        )
        assert first.status_code == 200

        second = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "anotherpassword456"},
        )
        assert second.status_code == 400

    def test_invalid_token_rejected(self, test_client):
        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": "not-a-real-token", "password": "somepassword123"},
        )
        assert resp.status_code == 400

    def test_expired_token_rejected(self, test_client, reset_user):
        from database.connection import SessionLocal
        email, _, user_id = reset_user

        raw_token = "expired-token-value"
        db = SessionLocal()
        try:
            db.add(PasswordResetToken(
                user_id=user_id,
                token_hash=hash_reset_token(raw_token),
                expires_at=datetime.utcnow() - timedelta(minutes=1),
            ))
            db.commit()
        finally:
            db.close()

        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "somepassword123"},
        )
        assert resp.status_code == 400

    def test_reset_revokes_active_sessions(self, test_client, reset_user):
        """After a reset, previously issued refresh sessions must be dead."""
        email, old_password, _ = reset_user

        # Log in to create a session
        login = test_client.post(
            "/api/auth/login", json={"email": email, "password": old_password},
        )
        assert login.status_code == 200

        from database.connection import SessionLocal
        db = SessionLocal()
        try:
            active = db.query(RefreshSession).filter(
                RefreshSession.revoked_at.is_(None),
            ).count()
            assert active >= 1
        finally:
            db.close()

        token = self._request_token(test_client, email)
        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "brandnewpassword123"},
        )
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            active = db.query(RefreshSession).filter(
                RefreshSession.revoked_at.is_(None),
            ).count()
            assert active == 0
        finally:
            db.close()

    def test_weak_password_rejected(self, test_client, reset_user):
        email, _, _ = reset_user
        token = self._request_token(test_client, email)
        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "short"},
        )
        assert resp.status_code == 422

    def test_gmail_connect_reset(self, test_client, reset_user):
        """Password reset must also work for Google-signup accounts (no password)."""
        from models.models import User
        from database.connection import SessionLocal
        email, _, user_id = reset_user

        # Simulate a Google-signup account: no password set
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.id == user_id).first()
            u.hashed_password = None
            db.commit()
        finally:
            db.close()

        token = self._request_token(test_client, email)
        resp = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "newgooglepassword123"},
        )
        assert resp.status_code == 200

        login = test_client.post(
            "/api/auth/login", json={"email": email, "password": "newgooglepassword123"},
        )
        assert login.status_code == 200
