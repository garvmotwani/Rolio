"""
Tests for the deterministic natural-language search parser and the
activity-feed endpoint. No external APIs — all parsing is local.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.nl_search import parse_query


class TestNaturalLanguageParsing:
    def test_location_and_work_type(self):
        r = parse_query("backend internships in Bangalore using Python")
        assert r["location"] == "bangalore"
        assert r["work_type"] == "internship"
        assert "backend" in r["keywords"].lower()
        assert "python" in r["keywords"].lower()
        # extracted words must not remain in the keyword query
        assert "bangalore" not in r["keywords"].lower()
        assert "internship" not in r["keywords"].lower()

    def test_remote_detection(self):
        r = parse_query("remote frontend internships using React")
        assert r["remote"] is True
        assert r["work_type"] == "internship"
        assert "frontend" in r["keywords"].lower()

    def test_seniority(self):
        r = parse_query("senior vlsi design jobs")
        assert r["experience_level"] == "senior"
        assert "vlsi" in r["keywords"].lower()
        assert "senior" not in r["keywords"].lower()

    def test_entry_level(self):
        r = parse_query("entry-level software engineering jobs")
        assert r["experience_level"] == "entry"

    def test_full_time(self):
        r = parse_query("full time java jobs in pune")
        assert r["work_type"] == "full-time"
        assert r["location"] == "pune"
        assert "java" in r["keywords"].lower()

    def test_bare_city_mention(self):
        r = parse_query("python jobs bangalore")
        assert r["location"] == "bangalore"

    def test_explicit_wins_over_nl_in_endpoint(self):
        # The endpoint gives explicit filter params priority — parser only
        # fills gaps. (Unit-level: parse never invents values.)
        r = parse_query("react developer")
        assert r["location"] == ""
        assert r["work_type"] is None
        assert r["experience_level"] is None
        assert r["remote"] is False
        assert "react" in r["keywords"].lower()

    def test_empty_and_plain_queries(self):
        r = parse_query("")
        assert r["keywords"] == ""
        r = parse_query("react developer")
        assert r["keywords"] == "react developer"

    def test_deterministic(self):
        q = "remote internships in mumbai using python"
        assert parse_query(q) == parse_query(q)


class TestActivityFeedEndpoint:
    def test_activity_requires_auth(self, test_client):
        resp = test_client.get("/api/analytics/activity")
        assert resp.status_code == 401

    def test_resume_performance_requires_auth(self, test_client):
        resp = test_client.get("/api/analytics/resume-performance")
        assert resp.status_code == 401

    def test_auto_sync_requires_auth(self, test_client):
        # POST without a CSRF token is rejected (403) before auth is checked
        resp = test_client.post("/api/gmail/auto-sync")
        assert resp.status_code in (401, 403)
