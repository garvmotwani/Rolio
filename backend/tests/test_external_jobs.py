"""
Tests for external job flows: prefixed-ID detail resolution, save/import
idempotency, applications for external jobs, and city-alias local search.

All external API calls (RapidAPI, Remotive, Jobicy) are mocked — fully
hermetic, no network access, no API keys required.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, AsyncMock

import pytest

from database.connection import SessionLocal
from models.models import Job, Company, User, Application
from utils.auth import get_password_hash


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_user(db, email="ext@test.com", password="supersecret123"):
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        name="Ext Tester",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_cookies(client, creds):
    """Log in and prepare the client for CSRF-protected requests: copy the
    rolio_csrf cookie value into the X-CSRF-Token header (mirrors the browser
    flow where JS reads the non-HttpOnly cookie)."""
    resp = client.post("/api/auth/login", json=creds)
    assert resp.status_code == 200
    csrf = client.cookies.get("rolio_csrf", "")
    client.headers.update({"X-CSRF-Token": csrf})


# ─── External detail resolution ──────────────────────────────────────────────

@pytest.fixture
def remotive_detail():
    return {
        "id": "remotive_123",
        "company_id": 0,
        "title": "Senior React Developer",
        "description": "Great remote role",
        "requirements": "",
        "responsibilities": "",
        "preferred_qualifications": "",
        "skills_required": json.dumps(["react", "typescript"]),
        "skills_preferred": "",
        "location": "Remote",
        "work_type": "remote",
        "salary_min": 0,
        "salary_max": 0,
        "experience_level": "senior",
        "employment_type": "full-time",
        "application_url": "https://remotive.com/jobs/123",
        "posted_at": "2026-09-01T00:00:00",
        "company_name": "Acme Corp",
        "company_logo": "",
        "company_industry": "",
        "match_score": 0,
        "is_saved": False,
        "is_applied": False,
        "source": "remotive",
        "publisher": "Remotive",
        "benefits": [],
        "salary_currency": "USD",
        "salary_raw": "$80k - $100k",
        "google_link": "",
    }


class TestExternalJobDetail:
    def test_remotive_detail_resolves(self, test_client, remotive_detail):
        with patch(
            "routes.jobs.get_free_board_job",
            new=AsyncMock(return_value=remotive_detail),
        ):
            resp = test_client.get("/api/jobs/remotive_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Senior React Developer"
        assert data["source"] == "remotive"
        assert data["salary_currency"] == "USD"

    def test_unknown_listing_returns_404(self, test_client):
        with patch(
            "routes.jobs.get_free_board_job",
            new=AsyncMock(return_value=None),
        ):
            resp = test_client.get("/api/jobs/remotive_gone")
        assert resp.status_code == 404

    def test_jobicy_detail_resolves(self, test_client, remotive_detail):
        jobicy = dict(remotive_detail, id="jobicy_99", source="jobicy",
                      title="Backend Engineer", publisher="Jobicy")
        with patch(
            "routes.jobs.get_free_board_job",
            new=AsyncMock(return_value=jobicy),
        ):
            resp = test_client.get("/api/jobs/jobicy_99")
        assert resp.status_code == 200
        assert resp.json()["source"] == "jobicy"


# ─── Save + import idempotency ───────────────────────────────────────────────

class TestExternalSaveImport:
    def test_save_imports_job_to_db(self, test_client, registered_user, remotive_detail):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=remotive_detail),
        ):
            resp = test_client.post("/api/jobs/remotive_123/save")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Job saved"

        db = SessionLocal()
        job = db.query(Job).filter(Job.external_id == "remotive_123").first()
        assert job is not None
        assert job.source == "remotive"
        assert job.company_id is not None
        db.close()

    def test_save_is_idempotent(self, test_client, registered_user, remotive_detail):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=remotive_detail),
        ):
            first = test_client.post("/api/jobs/remotive_123/save")
            second = test_client.post("/api/jobs/remotive_123/save")
        assert first.json()["message"] == "Job saved"
        assert second.json()["message"] == "Already saved"

        # Only ONE job row + ONE company row created
        db = SessionLocal()
        assert db.query(Job).filter(Job.external_id == "remotive_123").count() == 1
        assert db.query(Company).filter(Company.name == "Acme Corp").count() == 1
        db.close()

    def test_unsave_removes_saved_row(self, test_client, registered_user, remotive_detail):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=remotive_detail),
        ):
            test_client.post("/api/jobs/remotive_123/save")
            resp = test_client.delete("/api/jobs/remotive_123/save")
        assert resp.json()["message"] == "Job unsaved"

    def test_legacy_jsearch_row_backfills_external_id(self, test_client, registered_user, db=None):
        """Old jsearch rows (pre-external_id) found by URL substring get the
        column backfilled instead of creating a duplicate."""
        _auth_cookies(test_client, registered_user)
        session = SessionLocal()
        legacy = Job(
            company_id=0,
            title="Legacy JS Job",
            application_url="https://example.com/apply?job_id=abc123",
            source="jsearch",
        )
        session.add(legacy)
        session.commit()
        session.close()

        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=None),  # must NOT be called
        ):
            resp = test_client.post("/api/jobs/jsearch_abc123/save")
        assert resp.status_code == 200

        session = SessionLocal()
        row = session.query(Job).filter(Job.title == "Legacy JS Job").first()
        assert row.external_id == "jsearch_abc123"
        # No duplicate created
        assert session.query(Job).filter(Job.source == "jsearch").count() == 1
        session.close()


# ─── Applications for external jobs ─────────────────────────────────────────

class TestExternalApplications:
    def test_apply_with_string_external_id(self, test_client, registered_user, remotive_detail):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=remotive_detail),
        ):
            resp = test_client.post("/api/applications", json={
                "job_id": "remotive_123",
                "external_url": "https://remotive.com/jobs/123",
            })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Application created"

        # The application links to the imported numeric job
        db = SessionLocal()
        job = db.query(Job).filter(Job.external_id == "remotive_123").first()
        assert job is not None
        app = db.query(Application).filter(
            Application.job_id == job.id,
        ).first()
        assert app is not None
        assert app.external_url == "https://remotive.com/jobs/123"
        db.close()

    def test_duplicate_external_apply_rejected(self, test_client, registered_user, remotive_detail):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=remotive_detail),
        ):
            test_client.post("/api/applications", json={"job_id": "remotive_123"})
            resp = test_client.post("/api/applications", json={"job_id": "remotive_123"})
        assert resp.status_code == 400
        assert "Already applied" in resp.json()["detail"]

    def test_unknown_external_job_404(self, test_client, registered_user):
        _auth_cookies(test_client, registered_user)
        with patch(
            "routes.jobs._resolve_external_detail",
            new=AsyncMock(return_value=None),
        ):
            resp = test_client.post("/api/applications", json={"job_id": "remotive_nope"})
        assert resp.status_code == 404


# ─── City aliases ────────────────────────────────────────────────────────────

class TestCityAliases:
    def test_location_variants_bangalore(self):
        from routes.unified_search import _location_variants
        variants = _location_variants("bangalore")
        assert "bengaluru" in variants and "bangalore" in variants

    def test_location_variants_passthrough(self):
        from routes.unified_search import _location_variants
        assert _location_variants("Hyderabad") == ["Hyderabad"]

    def test_local_search_matches_alias(self, test_client):
        """A job stored as 'Bengaluru' is found when searching 'bangalore'."""
        session = SessionLocal()
        company = Company(name="AliasTestCo")
        session.add(company)
        session.flush()
        session.add(Job(
            company_id=company.id,
            title="Backend Engineer",
            location="Bengaluru, Karnataka",
            is_active=True,
        ))
        session.commit()
        session.close()

        resp = test_client.get("/api/search", params={"location": "bangalore"})
        assert resp.status_code == 200
        titles = [j["title"] for j in resp.json()["jobs"]]
        assert "Backend Engineer" in titles

    def test_intern_filter_whole_word(self):
        """'International Tax Manager' must NOT match an intern search."""
        from routes.unified_search import _free_boards_search
        import asyncio

        board_job_intern = {"title": "Data Intern", "skills": [], "job_id": "jobicy_1",
                            "company_name": "X", "location": "Remote", "work_type": "remote",
                            "salary_min": None, "salary_max": None, "currency": "USD",
                            "salary_raw": "", "experience_level": "intern",
                            "employment_type": "full-time", "posted_at": "",
                            "source": "jobicy", "publisher": "Jobicy", "apply_link": ""}
        board_job_international = {"title": "International Tax Manager", "skills": [],
                                   "job_id": "jobicy_2", "company_name": "Y",
                                   "location": "Remote", "work_type": "remote",
                                   "salary_min": None, "salary_max": None,
                                   "currency": "USD", "salary_raw": "",
                                   "experience_level": "mid", "employment_type": "full-time",
                                   "posted_at": "", "source": "jobicy",
                                   "publisher": "Jobicy", "apply_link": ""}

        with patch(
            "routes.unified_search.search_free_boards",
            new=AsyncMock(return_value=[board_job_intern, board_job_international]),
        ):
            results, total = asyncio.run(_free_boards_search("intern", 1))
        titles = [r["title"] for r in results]
        assert "Data Intern" in titles
        assert "International Tax Manager" not in titles
        assert total == 1
