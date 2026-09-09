"""Tests for search history and analytics endpoints."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _login(client, email="histuser@test.com", password="securepass123"):
    """Register + login helper returning CSRF token from cookies."""
    client.post("/api/auth/register", json={
        "email": email, "password": password, "name": "History User",
    })
    # CSRF cookie is set on register response
    csrf = client.cookies.get("rolio_csrf")
    return csrf


class TestSearchHistory:
    def test_save_and_list_search(self, test_client):
        csrf = _login(test_client)
        resp = test_client.post(
            "/api/search/history?query=internship&location=bangalore&results_count=12",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Search saved"

        resp = test_client.get("/api/search/history?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["query"] == "internship"
        assert data[0]["location"] == "bangalore"
        assert data[0]["results_count"] == 12

    def test_save_requires_auth(self, test_client):
        resp = test_client.post("/api/search/history?query=test")
        assert resp.status_code in (401, 403)

    def test_save_requires_csrf(self, test_client):
        _login(test_client)
        resp = test_client.post("/api/search/history?query=test")
        assert resp.status_code == 403

    def test_duplicate_search_updates_timestamp(self, test_client):
        csrf = _login(test_client)
        test_client.post(
            "/api/search/history?query=python&results_count=5",
            headers={"X-CSRF-Token": csrf},
        )
        test_client.post(
            "/api/search/history?query=python&results_count=9",
            headers={"X-CSRF-Token": csrf},
        )
        resp = test_client.get("/api/search/history")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["results_count"] == 9  # updated, not duplicated

    def test_delete_single_entry(self, test_client):
        csrf = _login(test_client)
        resp = test_client.post(
            "/api/search/history?query=react&results_count=3",
            headers={"X-CSRF-Token": csrf},
        )
        entry_id = resp.json()["id"]

        # No CSRF -> forbidden
        resp = test_client.delete(f"/api/search/history/{entry_id}")
        assert resp.status_code == 403

        # With CSRF -> deleted
        resp = test_client.delete(
            f"/api/search/history/{entry_id}",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        assert test_client.get("/api/search/history").json() == []

    def test_delete_other_users_entry_forbidden(self, test_client):
        csrf_a = _login(test_client, email="usera@test.com")
        resp = test_client.post(
            "/api/search/history?query=aws",
            headers={"X-CSRF-Token": csrf_a},
        )
        entry_id = resp.json()["id"]

        # Second user
        _login(test_client, email="userb@test.com")
        csrf_b = test_client.cookies.get("rolio_csrf")
        resp = test_client.delete(
            f"/api/search/history/{entry_id}",
            headers={"X-CSRF-Token": csrf_b},
        )
        assert resp.status_code == 404  # not visible to other user

    def test_clear_all_history(self, test_client):
        csrf = _login(test_client)
        test_client.post(
            "/api/search/history?query=one",
            headers={"X-CSRF-Token": csrf},
        )
        test_client.post(
            "/api/search/history?query=two",
            headers={"X-CSRF-Token": csrf},
        )
        resp = test_client.delete(
            "/api/search/history",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        assert test_client.get("/api/search/history").json() == []


class TestAnalytics:
    def test_dashboard_requires_auth(self, test_client):
        resp = test_client.get("/api/analytics/dashboard")
        assert resp.status_code in (401, 403)

    def test_dashboard_empty_state(self, test_client):
        _login(test_client)
        resp = test_client.get("/api/analytics/dashboard?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_applications"] == 0
        assert data["match_scores"]["average"] == 0
        assert data["applications_over_time"] != []
        assert "status_distribution" in data
        assert "company_distribution" in data
        assert "recent_activity" in data

    def test_dashboard_days_bounds(self, test_client):
        _login(test_client)
        # Below minimum -> 422
        assert test_client.get("/api/analytics/dashboard?days=1").status_code == 422
        # Above maximum -> 422
        assert test_client.get("/api/analytics/dashboard?days=999").status_code == 422