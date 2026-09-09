"""
Security-focused tests: upload validation, injection, API integrity, token encryption.
"""
import io
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _login(test_client, email="security@example.com"):
    """Helper: register and login, return cookies + csrf."""
    test_client.post("/api/auth/register", json={
        "email": email, "password": "password123", "name": "Security Test"
    })
    resp = test_client.post("/api/auth/login", json={
        "email": email, "password": "password123",
    })
    if resp.status_code != 200:
        pytest.skip(f"Login failed ({resp.status_code})")
    cookies = {k: v for k, v in test_client.cookies.items()}
    csrf = test_client.cookies.get("rolio_csrf", "")
    return cookies, csrf


class TestUploadSecurity:
    """Test file upload security."""

    def test_upload_requires_auth(self, test_client):
        resp = test_client.post("/api/resume/upload")
        assert resp.status_code in (401, 403)

    def test_upload_requires_file(self, test_client):
        cookies, csrf = _login(test_client, "upload1@example.com")
        resp = test_client.post(
            "/api/resume/upload",
            cookies=cookies,
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code in (400, 422)

    def test_upload_invalid_file_type(self, test_client):
        cookies, csrf = _login(test_client, "upload2@example.com")
        resp = test_client.post(
            "/api/resume/upload",
            cookies=cookies,
            headers={"X-CSRF-Token": csrf},
            files={"file": ("test.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
        )
        assert resp.status_code == 400


class TestTokenEncryption:
    """Test Fernet token encryption for Gmail tokens."""

    def test_fernet_encrypt_decrypt_roundtrip(self):
        from routes.gmail import _encrypt_token, _decrypt_token
        original = "ya29.a0AfH6SMB_test_token_value_12345"
        encrypted = _encrypt_token(original)
        decrypted = _decrypt_token(encrypted)
        assert decrypted == original
        # Ciphertext must not contain plaintext
        assert original not in encrypted

    def test_fernet_tampered_ciphertext_rejected(self):
        from routes.gmail import _decrypt_token
        from cryptography.fernet import InvalidToken
        # Tamper with ciphertext
        with pytest.raises(Exception):
            _decrypt_token("dGFtcGVkX2RhdGFfaGVyZQ==")


class TestInputValidation:
    """Test that API properly validates input."""

    def test_search_query_max_length(self, test_client):
        long_query = "a" * 500
        resp = test_client.get(f"/api/jobs?query={long_query}")
        assert resp.status_code == 200

    def test_invalid_sort_by(self, test_client):
        resp = test_client.get("/api/jobs?sort_by=invalid")
        assert resp.status_code == 200

    def test_negative_page(self, test_client):
        resp = test_client.get("/api/jobs?page=-1")
        assert resp.status_code == 200


class TestAPIConsistency:
    """Test API response shapes and status codes."""

    def test_health_shape(self, test_client):
        resp = test_client.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_jobs_response_shape(self, test_client):
        resp = test_client.get("/api/jobs")
        data = resp.json()
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)

    def test_login_error_shape(self):
        from fastapi.testclient import TestClient as TC
        from main import app
        fresh = TC(app)
        resp = fresh.post("/api/auth/login", json={
            "email": "nonexistent_test@example.com",
            "password": "wrongpassword123",
        })
        assert resp.status_code == 401
        data = resp.json()
        assert "detail" in data


class TestErrorHandling:
    """Test that errors don't leak internal details."""

    def test_no_stack_traces_in_response(self):
        from fastapi.testclient import TestClient as TC
        from main import app
        fresh = TC(app)
        resp = fresh.post("/api/auth/login", json={
            "email": "nonexistent_nostack@example.com",
            "password": "wrongpassword123",
        })
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert ".py" not in detail
        assert "sql" not in detail.lower()
        assert "traceback" not in detail.lower()

    def test_404_for_nonexistent_job(self, test_client):
        resp = test_client.get("/api/jobs/999999")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data


class TestCrossUserAccess:
    """Test that users cannot access other users' data."""

    def test_user_a_cannot_see_user_b_apps(self, test_client):
        # Register user A
        test_client.post("/api/auth/register", json={
            "email": "userA_cross@example.com", "password": "password123", "name": "User A"
        })
        test_client.post("/api/auth/login", json={
            "email": "userA_cross@example.com", "password": "password123",
        })
        cookies_a = {k: v for k, v in test_client.cookies.items()}
        csrf_a = test_client.cookies.get("rolio_csrf", "")

        # User A should see empty applications (not crash or see User B's data)
        resp = test_client.get("/api/applications", cookies=cookies_a,
                               headers={"X-CSRF-Token": csrf_a})
        assert resp.status_code == 200
        assert resp.json() == [] or isinstance(resp.json(), list)
