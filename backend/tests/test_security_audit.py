"""
Security test suite — attack-path regression tests.

Covers the vulnerability classes audited in the security review:
  - Stored XSS via URL fields (javascript:/data: scheme injection)
  - IDOR / cross-user access (two-user isolation)
  - CSRF enforcement on state-changing endpoints
  - Unbounded AI input rejection (resource exhaustion)
  - Authentication guards
  - Mass-assignment protection (allowlisted update fields)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
import pytest

from main import app
from database.connection import SessionLocal
from models.models import User, Job, Company


@pytest.fixture
def client():
    return TestClient(app)


def _register(client: TestClient, email: str) -> dict:
    """Register + return cookie jar context."""
    resp = client.post("/api/auth/register", json={
        "email": email, "password": "SecurePass123x", "name": "Sec Test",
    })
    assert resp.status_code == 200, resp.text
    return resp


def _seed_job() -> int:
    """Create one active local job directly in the test DB; return its id."""
    session = SessionLocal()
    try:
        company = Company(name="SecurityTestCo")
        session.add(company)
        session.flush()
        job = Job(company_id=company.id, title="Security Test Engineer",
                  location="Remote", is_active=True)
        session.add(job)
        session.commit()
        return job.id
    finally:
        session.close()


# ═══════════════════ URL-scheme XSS (stored) ═══════════════════

class TestUrlSchemeValidation:
    def test_javascript_url_rejected_in_url_validator(self):
        from utils.url_validation import is_safe_url
        assert not is_safe_url("javascript:alert(document.domain)")
        assert not is_safe_url("JAVASCRIPT:alert(1)")
        # newline-obfuscated scheme
        assert not is_safe_url("java\nscript:alert(1)")
        assert not is_safe_url("data:text/html,<script>alert(1)</script>")
        assert not is_safe_url("vbscript:msgbox(1)")
        assert not is_safe_url("file:///etc/passwd")
        # scheme-relative
        assert not is_safe_url("//evil.com/back")
        # embedded credentials
        assert not is_safe_url("https://user:pass@evil.com")
        # control chars
        assert not is_safe_url("https://ok.com/\x01x")
        # oversized
        assert not is_safe_url("https://ok.com/" + "a" * 3000)
        # safe values pass
        assert is_safe_url("https://careers.google.com/jobs/123")
        assert is_safe_url("http://example.com")
        assert is_safe_url(None)
        assert is_safe_url("")

    def test_application_create_rejects_javascript_url(self, client):
        _register(client, "urlxss1@sec.example.com")
        job_id = _seed_job()
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.post("/api/applications", json={
            "job_id": job_id,
            "external_url": "javascript:alert(document.domain)",
        }, headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"

    def test_application_create_accepts_https_url(self, client):
        _register(client, "urlxss2@sec.example.com")
        job_id = _seed_job()
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.post("/api/applications", json={
            "job_id": job_id,
            "external_url": "https://example.com/apply/123",
        }, headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200, resp.text
        # cleanup
        app_id = resp.json()["id"]
        csrf = client.cookies.get("rolio_csrf", "")
        client.delete(f"/api/applications/{app_id}", headers={"X-CSRF-Token": csrf})

    def test_profile_rejects_javascript_link(self, client):
        _register(client, "urlxss3@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.put("/api/profile", json={
            "portfolio_url": "javascript:alert(1)",
        }, headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422, resp.text


# ═══════════════════ CSRF enforcement ═══════════════════

class TestCsrfEnforcement:
    def test_post_without_csrf_rejected(self, client):
        _register(client, "csrf1@sec.example.com")
        job_id = _seed_job()
        resp = client.post("/api/applications", json={"job_id": job_id})
        assert resp.status_code == 403

    def test_csrf_with_wrong_token_rejected(self, client):
        _register(client, "csrf2@sec.example.com")
        job_id = _seed_job()
        resp = client.post(
            "/api/applications",
            json={"job_id": job_id},
            headers={"X-CSRF-Token": "wrong-token-value"},
        )
        assert resp.status_code == 403


# ═══════════════════ AI input bounds (resource exhaustion) ═══════════════════

class TestAiInputBounds:
    def test_oversized_chat_message_rejected(self, client):
        _register(client, "aibounds1@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.post(
            "/api/ai/chat",
            json={"message": "x" * 3000},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 422, f"got {resp.status_code}"

    def test_oversized_history_rejected(self, client):
        _register(client, "aibounds2@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        big_history = [{"role": "user", "content": "y" * 50} for _ in range(25)]
        resp = client.post(
            "/api/ai/chat",
            json={"message": "hi", "history": big_history},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 422, f"got {resp.status_code}"

    def test_normal_chat_message_accepted_shape(self, client):
        _register(client, "aibounds3@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.post(
            "/api/ai/chat",
            json={"message": "What jobs fit me?"},
            headers={"X-CSRF-Token": csrf},
        )
        # Should not be a validation error (422). May be 200 (AI) or a
        # graceful provider-failure response — both are acceptable.
        assert resp.status_code != 422, resp.text


# ═══════════════════ IDOR / cross-user isolation ═══════════════════

class TestCrossUserIsolation:
    def test_user_cannot_update_others_application(self, client):
        # User A creates an application
        _register(client, "idorA@sec.example.com")
        job_id = _seed_job()
        csrf = client.cookies.get("rolio_csrf", "")
        created = client.post(
            "/api/applications",
            json={"job_id": job_id},
            headers={"X-CSRF-Token": csrf},
        ).json()
        app_id = created["id"]

        # User B (different browser context) attempts to modify it
        other = TestClient(app)
        _register(other, "idorB@sec.example.com")
        csrf_b = other.cookies.get("rolio_csrf", "")
        resp = other.put(
            f"/api/applications/{app_id}",
            json={"status": "offer"},
            headers={"X-CSRF-Token": csrf_b},
        )
        assert resp.status_code == 404, f"expected 404 (ownership-filtered), got {resp.status_code}"

        # Verify A's application unchanged
        apps_a = client.get("/api/applications").json()
        statuses = {a["id"]: a["status"] for a in apps_a if isinstance(apps_a, list)}
        if app_id in statuses:
            assert statuses[app_id] != "offer"

    def test_user_cannot_delete_others_application(self, client):
        _register(client, "idorC@sec.example.com")
        job_id = _seed_job()
        csrf = client.cookies.get("rolio_csrf", "")
        created = client.post(
            "/api/applications",
            json={"job_id": job_id},
            headers={"X-CSRF-Token": csrf},
        ).json()
        app_id = created["id"]

        other = TestClient(app)
        _register(other, "idorD@sec.example.com")
        csrf_b = other.cookies.get("rolio_csrf", "")
        resp = other.delete(
            f"/api/applications/{app_id}",
            headers={"X-CSRF-Token": csrf_b},
        )
        assert resp.status_code == 404

        # A's application still exists
        apps_a = client.get("/api/applications").json()
        ids = {a["id"] for a in apps_a} if isinstance(apps_a, list) else set()
        assert app_id in ids

    def test_gmail_match_rejects_foreign_ids(self, client):
        """Email-application linking requires both resources to be owned."""
        _register(client, "idorE@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        resp = client.post(
            "/api/gmail/match/999999/999999",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 404


# ═══════════════════ Auth guards ═══════════════════

class TestAuthGuards:
    def test_applications_require_auth(self, client):
        assert client.get("/api/applications").status_code == 401

    def test_activity_requires_auth(self, client):
        assert client.get("/api/analytics/activity").status_code == 401

    def test_resume_performance_requires_auth(self, client):
        assert client.get("/api/analytics/resume-performance").status_code == 401

    def test_export_requires_auth(self, client):
        assert client.get("/api/export/applications").status_code == 401

    def test_profile_requires_auth(self, client):
        assert client.get("/api/profile").status_code == 401

    def test_tampered_session_cookie_rejected(self, client):
        client.cookies.set("rolio_access", "forged.token.value")
        resp = client.get("/api/users/me")
        assert resp.status_code == 401


# ═══════════════════ Mass assignment ═══════════════════

class TestMassAssignment:
    def test_user_update_ignores_protected_fields(self, client):
        _register(client, "mass1@sec.example.com")
        csrf = client.cookies.get("rolio_csrf", "")
        # Attempt to escalate via arbitrary fields in PUT /users/me
        resp = client.put(
            "/api/users/me",
            json={"name": "New Name", "is_admin": True, "email_verified": True},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        # Verify fields were NOT persisted
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "mass1@sec.example.com").first()
            assert user is not None
            assert not getattr(user, "is_admin", False) or user.is_admin in (None, False)
        finally:
            db.close()


# ═══════════════════ Query-injection smoke (non-destructive) ═══════════════════

class TestInjectionSmoke:
    def test_search_handles_injection_payloads(self, client):
        for payload in ["' OR 1=1 --", '"; DROP TABLE users; --', "%27%29%3B--"]:
            resp = client.get("/api/jobs", params={"q": payload})
            assert resp.status_code in (200, 422), f"{payload!r}: {resp.status_code}"
