"""
Tests for JSearch abuse protection: input bounds, missing API key handling,
rate limits, and anonymous access behavior.

These tests never call the real RapidAPI — the service layer is mocked.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, AsyncMock


class TestJSearchInputBounds:
    """Test request validation for external search."""

    def test_post_rejects_empty_query(self, test_client):
        resp = test_client.post("/api/jsearch/search", json={"query": "   "})
        assert resp.status_code == 422

    def test_post_rejects_invalid_date_posted(self, test_client):
        resp = test_client.post(
            "/api/jsearch/search",
            json={"query": "developer", "date_posted": "yesterday"},
        )
        assert resp.status_code == 422

    def test_post_accepts_valid_date_posted(self, test_client):
        # Hermetic: never call the real RapidAPI even when a key is configured.
        with patch(
            "routes.jsearch.search_jobs",
            new=AsyncMock(return_value={"data": [], "count": 0, "page": 1,
                                        "num_pages": 1, "query": "dev",
                                        "source": "fallback"}),
        ):
            resp = test_client.post(
                "/api/jsearch/search",
                json={"query": "developer", "date_posted": "week"},
            )
        # 200 (results or unavailable) but never 422
        assert resp.status_code == 200

    def test_post_rejects_invalid_employment_type(self, test_client):
        resp = test_client.post(
            "/api/jsearch/search",
            json={"query": "developer", "employment_type": "GIG"},
        )
        assert resp.status_code == 422

    def test_post_accepts_internship_alias(self, test_client):
        # Hermetic: never call the real RapidAPI even when a key is configured.
        with patch(
            "routes.jsearch.search_jobs",
            new=AsyncMock(return_value={"data": [], "count": 0, "page": 1,
                                        "num_pages": 1, "query": "dev",
                                        "source": "fallback"}),
        ):
            resp = test_client.post(
                "/api/jsearch/search",
                json={"query": "developer", "employment_type": "INTERNSHIP"},
            )
        assert resp.status_code == 200

    def test_get_rejects_overlong_query(self, test_client):
        resp = test_client.get("/api/jsearch/search", params={"q": "a" * 300})
        assert resp.status_code == 422

    def test_get_rejects_page_zero(self, test_client):
        resp = test_client.get("/api/jsearch/search", params={"q": "dev", "page": 0})
        assert resp.status_code == 422

    def test_get_rejects_huge_page(self, test_client):
        resp = test_client.get("/api/jsearch/search", params={"q": "dev", "page": 999})
        assert resp.status_code == 422

    def test_job_detail_rejects_overlong_id(self, test_client):
        resp = test_client.get(f"/api/jsearch/job/{'x' * 300}")
        assert resp.status_code == 400


class TestJSearchMissingKey:
    """Test graceful behavior when JSEARCH_API_KEY is not configured."""

    # Note: JSEARCH_CONFIGURED is patched explicitly in every test in this
    # class so results are identical whether or not the local environment
    # happens to have a real JSEARCH_API_KEY set (CI has none).

    def test_unavailable_response_when_no_key(self, test_client):
        with patch("routes.jsearch.JSEARCH_CONFIGURED", False):
            resp = test_client.post("/api/jsearch/search", json={"query": "developer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "unavailable"
        assert data["count"] == 0
        assert data["external_available"] is False
        assert "unavailable" in data["summary"].lower()

    def test_detail_returns_503_when_no_key(self, test_client):
        with patch("routes.jsearch.JSEARCH_CONFIGURED", False):
            resp = test_client.get("/api/jsearch/job/some-job-id")
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()

    def test_similar_returns_empty_when_no_key(self, test_client):
        with patch("routes.jsearch.JSEARCH_CONFIGURED", False):
            resp = test_client.get("/api/jsearch/similar/some-job-id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["external_available"] is False


class TestJSearchKeyNotExposed:
    """Ensure the RapidAPI key never leaks into responses."""

    def test_response_has_no_api_key_fields(self, test_client):
        with patch(
            "routes.jsearch.search_jobs",
            new=AsyncMock(return_value={"data": [], "count": 0, "page": 1,
                                        "num_pages": 1, "query": "dev",
                                        "source": "fallback"}),
        ):
            resp = test_client.post("/api/jsearch/search", json={"query": "dev"})
        assert resp.status_code == 200
        body = str(resp.json())
        assert "api_key" not in body.lower()
        assert "x-rapidapi" not in body.lower()


class TestJSearchRateLimiting:
    """Anonymous searches are IP-limited; quota must not be endless."""

    def test_anonymous_quota_eventually_blocks(self, test_client):
        from routes.jsearch import ANON_SEARCH_LIMIT_PER_HOUR

        # Patch the service configured-flag so the quota check is reached
        # even in environments without a real JSEARCH_API_KEY (e.g. CI).
        with patch("routes.jsearch.JSEARCH_CONFIGURED", True), patch(
            "routes.jsearch.search_jobs",
            new=AsyncMock(return_value={"data": [], "count": 0, "page": 1,
                                        "num_pages": 1, "query": "dev",
                                        "source": "fallback"}),
        ):
            last_status = None
            for _ in range(ANON_SEARCH_LIMIT_PER_HOUR + 3):
                resp = test_client.post(
                    "/api/jsearch/search",
                    json={"query": "rate limit probe"},
                    headers={"X-Forwarded-For": "203.0.113.99"},
                )
                last_status = resp.status_code
                if last_status == 429:
                    break

        assert last_status == 429, "anonymous quota should block after the limit"


class TestUnifiedSearchProtection:
    """Unified search bounds and anonymous quota on the external leg."""

    def test_per_page_capped(self, test_client):
        resp = test_client.get("/api/search", params={"q": "dev", "per_page": 500})
        assert resp.status_code == 422

    def test_query_length_capped(self, test_client):
        resp = test_client.get("/api/search", params={"q": "a" * 500})
        assert resp.status_code == 422
