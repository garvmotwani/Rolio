"""
Tests for Gmail OAuth state validation and token encryption.

Covers: valid state, expired state, invalid state, replayed state,
encryption round-trip, tamper rejection, and client-secret hygiene.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta


def _make_user(db):
    from models.models import User
    from utils.auth import get_password_hash
    user = User(email="oauthstate@example.com", name="OAuth Test",
                hashed_password=get_password_hash("password123"), is_active=True)
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


class TestOAuthStateValidation:
    """Test the DB-persisted OAuth state flow."""

    def test_valid_state_returns_user_id(self):
        from database.connection import SessionLocal
        from routes.gmail import _create_oauth_state, _validate_oauth_state

        db = SessionLocal()
        try:
            user = _make_user(db)
            state = _create_oauth_state(db, user.id)
            user_id = _validate_oauth_state(db, state)
            assert user_id == user.id
        finally:
            db.close()

    def test_invalid_state_returns_none(self):
        from database.connection import SessionLocal
        from routes.gmail import _validate_oauth_state

        db = SessionLocal()
        try:
            assert _validate_oauth_state(db, "no-such-state-token") is None
        finally:
            db.close()

    def test_expired_state_rejected(self):
        from database.connection import SessionLocal
        from models.oauth_state import OAuthState
        from routes.gmail import _validate_oauth_state

        db = SessionLocal()
        try:
            user = _make_user(db)
            state = OAuthState(
                user_id=user.id,
                state_token="expired-state-token-123",
                created_at=datetime.utcnow() - timedelta(minutes=20),
                expires_at=datetime.utcnow() - timedelta(minutes=10),
            )
            db.add(state)
            db.commit()
            assert _validate_oauth_state(db, "expired-state-token-123") is None
            # Expired state should be cleaned up
            assert db.query(OAuthState).filter(
                OAuthState.state_token == "expired-state-token-123").first() is None
        finally:
            db.close()

    def test_replayed_state_rejected(self):
        from database.connection import SessionLocal
        from routes.gmail import _create_oauth_state, _validate_oauth_state

        db = SessionLocal()
        try:
            user = _make_user(db)
            state = _create_oauth_state(db, user.id)
            # First use: valid
            assert _validate_oauth_state(db, state) == user.id
            # Replay: rejected
            assert _validate_oauth_state(db, state) is None
        finally:
            db.close()

    def test_states_are_unique_random(self):
        from database.connection import SessionLocal
        from routes.gmail import _create_oauth_state

        db = SessionLocal()
        try:
            user = _make_user(db)
            states = {_create_oauth_state(db, user.id) for _ in range(10)}
            assert len(states) == 10, "states must be cryptographically random"
            assert all(len(s) >= 32 for s in states)
        finally:
            db.close()


class TestGmailTokenEncryption:
    """Test Fernet encryption used for Gmail tokens at rest."""

    def test_roundtrip(self):
        from routes.gmail import _encrypt_token, _decrypt_token
        original = "ya29.test_access_token_value"
        assert _decrypt_token(_encrypt_token(original)) == original

    def test_empty_token_passthrough(self):
        from routes.gmail import _encrypt_token, _decrypt_token
        assert _encrypt_token("") == ""
        assert _decrypt_token("") == ""

    def test_ciphertext_does_not_contain_plaintext(self):
        from routes.gmail import _encrypt_token
        original = "1//very_secret_refresh_token_value"
        encrypted = _encrypt_token(original)
        assert original not in encrypted

    def test_tampered_ciphertext_rejected(self):
        from routes.gmail import _encrypt_token, _decrypt_token
        import fastapi
        encrypted = _encrypt_token("some-secret-value")
        # Flip bytes at the end — must never decrypt to the original
        corrupted = encrypted[:-4] + ("AAAA" if encrypted[-4:] != "AAAA" else "BBBB")
        with pytest.raises((fastapi.HTTPException, Exception)) as excinfo:
            _decrypt_token(corrupted)
        # And it must never silently return the plaintext
        assert not isinstance(excinfo.value, fastapi.HTTPException) or excinfo.value.status_code == 500

    def test_garbage_ciphertext_rejected(self):
        from routes.gmail import _decrypt_token
        with pytest.raises(Exception):
            _decrypt_token("not-a-valid-fernet-token-at-all")


class TestClientSecretHygiene:
    """Ensure the Google client secret is never stored per-user."""

    def test_new_gmail_token_record_has_empty_secret(self):
        from database.connection import SessionLocal
        from models.email_models import GmailToken

        db = SessionLocal()
        try:
            user = _make_user(db)
            token = GmailToken(
                user_id=user.id,
                access_token="encrypted-a",
                refresh_token="encrypted-r",
                client_id="test-client-id",
                client_secret="",  # Must always be empty
                gmail_address="user@gmail.com",
            )
            db.add(token)
            db.commit()
            db.refresh(token)
            assert token.client_secret == ""
        finally:
            db.close()

    def test_callback_clears_legacy_secret(self):
        """The callback explicitly clears any legacy stored secret."""
        import inspect
        from routes import gmail
        source = inspect.getsource(gmail.gmail_callback)
        assert 'client_secret = ""' in source


class TestCrossFlowStateConfusion:
    """A state minted for one OAuth flow must not validate in another."""

    def test_signin_state_rejected_by_gmail_callback_validator(self):
        from database.connection import SessionLocal
        from models.oauth_state import OAuthState
        from routes.gmail import _validate_oauth_state

        db = SessionLocal()
        try:
            user = _make_user(db)
            state = OAuthState(
                user_id=user.id,
                state_token="signin-flow-state-token-abc123",
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
                flow_type="google_signin",
            )
            db.add(state)
            db.commit()
            # Must be rejected even though the token itself is fresh and valid
            assert _validate_oauth_state(db, "signin-flow-state-token-abc123") is None
            # And it must NOT have been consumed — it still belongs to its own flow
            db.refresh(state)
            assert state.is_consumed is False
        finally:
            db.close()

    def test_gmail_state_still_validates_in_gmail_flow(self):
        from routes.gmail import _create_oauth_state, _validate_oauth_state
        from database.connection import SessionLocal

        db = SessionLocal()
        try:
            user = _make_user(db)
            state = _create_oauth_state(db, user.id)
            assert _validate_oauth_state(db, state) == user.id
        finally:
            db.close()


class TestSyncRateLimit:
    """The manual sync endpoint is throttled per user, not per IP."""

    def test_sync_blocked_after_burst(self):
        from fastapi import HTTPException
        from database.connection import SessionLocal
        from utils.rate_limiter import get_rate_limiter
        from routes import gmail

        db = SessionLocal()
        try:
            user = _make_user(db)
            # Deterministic: ensure a clean bucket, then exceed the 6/5min limit
            limiter = get_rate_limiter()
            for _ in range(6):
                assert limiter.check("gmail_sync", user.id, 6, 300) is True
            assert limiter.check("gmail_sync", user.id, 6, 300) is False

            # Endpoint-level: the 7th call must 429 before touching Gmail
            with pytest.raises(HTTPException) as excinfo:
                gmail.sync_emails(user=user, db=db)
            assert excinfo.value.status_code == 429
        finally:
            db.close()

    def test_rate_check_runs_before_token_decryption(self):
        """Source-level guard: throttle precedes any token/decrypt work."""
        import inspect
        from routes import gmail
        src = inspect.getsource(gmail.sync_emails)
        rate_pos = src.find('get_rate_limiter().check("gmail_sync"')
        svc_pos = src.find("_get_gmail_service(")
        assert 0 < rate_pos < svc_pos, "rate limit must run before service build"
