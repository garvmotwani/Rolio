"""Tests for the unified explainable match engine (services/matching_service.py).

Covers:
- skill normalization (aliases: JS↔JavaScript, ReactJS↔React, Postgres↔PostgreSQL)
- gap classification (required vs preferred weighting)
- factor breakdown shape and data-awareness (unknown factors excluded)
- external (dict-shaped) job scoring parity with ORM jobs
- /api/ai/match accepting prefixed external job IDs
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from services.skill_normalizer import normalize_skill_list, canonical
from services.matching_service import (
    analyze_match,
    analyze_job_like,
    score_job_like,
    EXTERNAL_PREFIXES,
)



def _factor(b: dict, name: str) -> dict:
    """Find a factor entry in the breakdown's factor list."""
    return next(f for f in b["factors"] if f["factor"] == name)

def _equiv(a: str, b: str) -> bool:
    """Two raw skill strings are equivalent when they canonicalize the same."""
    return canonical(a) == canonical(b) and bool(canonical(a))


# ── Skill normalization ──────────────────────────────────────────────────

class TestSkillNormalization:
    def test_js_alias(self):
        assert _equiv("JS", "JavaScript")

    def test_reactjs_alias(self):
        assert _equiv("ReactJS", "React")

    def test_postgres_alias(self):
        assert _equiv("Postgres", "PostgreSQL")

    def test_case_insensitive_exact(self):
        assert _equiv("python", "Python")

    def test_different_skills_not_equivalent(self):
        assert not _equiv("Python", "Java")

    def test_normalize_list_dedupes_aliases(self):
        out = normalize_skill_list(["JS", "JavaScript", "ReactJS", "React"])
        assert out == ["javascript", "react"]

    def test_normalize_list_preserves_order(self):
        out = normalize_skill_list(["React", "Python", "Go"])
        assert out == ["react", "python", "go"]


# ── Factor breakdown shape ───────────────────────────────────────────────

def _make_profile(monkeypatch, skills, title="Backend Developer",
                  experience_level="entry", location_pref="Bengaluru",
                  work_type_pref="hybrid", salary_min=None):
    """Build a duck-typed profile + patch the ORM helpers the engine uses."""
    class P:
        pass

    p = P()
    p.user_id = 1
    p.title = title
    p.experience_level = experience_level
    p.location_preference = location_pref
    p.work_type_preference = work_type_pref
    p.salary_min = salary_min
    p.salary_max = None
    p._skills = list(skills)

    import services.matching_service as ms

    monkeypatch.setattr(ms, "_profile_skills", lambda prof, db: list(prof._skills))
    return p


def _make_job(**overrides):
    class J:
        pass

    j = J()
    j.id = 42
    j.title = "Backend Developer"
    j.description = ""
    j.skills_required = '["Python", "FastAPI"]'
    j.skills_preferred = '["Docker", "AWS"]'
    j.location = "Bengaluru"
    j.work_type = "hybrid"
    j.experience_level = "entry"
    j.salary_min = 0
    j.salary_max = 0
    for k, v in overrides.items():
        setattr(j, k, v)
    return j


class TestAnalyzeMatch:
    def test_breakdown_has_required_keys(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python", "FastAPI"])
        job = _make_job()
        b = analyze_match(profile, job, db=None)
        for key in ("overall", "factors", "matched_skills", "missing_skill_details",
                    "missing_skills", "data_confidence"):
            assert key in b, f"missing key: {key}"

    def test_perfect_skill_match_scores_high(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python", "FastAPI", "Docker", "AWS"])
        job = _make_job()
        b = analyze_match(profile, job, db=None)
        assert _factor(b, "skills")["score"] >= 99

    def test_missing_required_hurts_more_than_missing_preferred(self, monkeypatch):
        # Same number of missing skills, but required-missing should score lower.
        p_full = _make_profile(monkeypatch, ["Python", "FastAPI", "Docker", "AWS"])
        p_miss_required = _make_profile(monkeypatch, ["Docker", "AWS"])  # missing Python+FastAPI
        p_miss_preferred = _make_profile(monkeypatch, ["Python", "FastAPI"])  # missing Docker+AWS
        job = _make_job()
        b_req = analyze_match(p_miss_required, job, db=None)
        b_pref = analyze_match(p_miss_preferred, job, db=None)
        assert _factor(b_req, "skills")["score"] < _factor(b_pref, "skills")["score"]

    def test_missing_skills_are_classified(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python"])
        job = _make_job()
        b = analyze_match(profile, job, db=None)
        missing = b["missing_skill_details"]
        assert missing, "expected classified gaps"
        # Classification is data-driven: required skills -> critical,
        # preferred skills -> nice_to_have.
        for m in missing:
            assert m["importance"] in ("critical", "nice_to_have")
        skills = {m["skill"] for m in missing}
        assert "fastapi" in skills
        fastapi = next(m for m in missing if m["skill"] == "fastapi")
        assert fastapi["importance"] == "critical"

    def test_matched_skills_canonicalized(self, monkeypatch):
        # Profile has "JS" — job asks for "JavaScript". Should still match.
        profile = _make_profile(monkeypatch, ["JS", "Node.js"])
        job = _make_job(skills_required='["JavaScript"]', skills_preferred='[]')
        b = analyze_match(profile, job, db=None)
        assert "javascript" in b["matched_skills"]

    def test_unknown_factors_excluded_not_faked(self, monkeypatch):
        # No salary data on job → salary factor marked unknown, not scored 0.
        profile = _make_profile(monkeypatch, ["Python"])
        job = _make_job(salary_min=0, salary_max=0)
        b = analyze_match(profile, job, db=None)
        assert _factor(b, "salary")["known"] is False

    def test_overall_in_known_range(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python", "FastAPI"])
        job = _make_job()
        b = analyze_match(profile, job, db=None)
        assert 0 <= b["overall"] <= 100


# ── External (dict) jobs ─────────────────────────────────────────────────

class TestExternalJobScoring:
    def test_score_job_like_basic(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python", "FastAPI"])
        job_dict = {
            "title": "Backend Developer",
            "skills": ["Python", "FastAPI", "Redis"],
            "experience_level": "entry",
            "location": "Bengaluru",
            "work_type": "hybrid",
            "salary_min": 0,
            "salary_max": 0,
        }
        score = score_job_like(profile, job_dict, db=None)
        assert 0 <= score <= 100

    def test_analyze_job_like_classifies_gaps(self, monkeypatch):
        profile = _make_profile(monkeypatch, ["Python"])
        job_dict = {"skills_required": ["Python", "AWS"], "skills_preferred": []}
        b = analyze_job_like(profile, job_dict, db=None)
        assert "aws" in b["missing_skills"]
        aws = next(m for m in b["missing_skill_details"] if m["skill"] == "aws")
        assert aws["importance"] == "critical"

    def test_orc_and_dict_paths_agree(self, monkeypatch):
        """The same candidate/skills should produce the same score whether the
        job came from the DB (ORM) or an external provider (dict)."""
        profile = _make_profile(monkeypatch, ["Python", "FastAPI"])
        orm_job = _make_job()
        dict_job = {
            "title": "Backend Developer",
            "skills_required": ["Python", "FastAPI"],
            "skills_preferred": ["Docker", "AWS"],
            "location": "Bengaluru",
            "work_type": "hybrid",
            "experience_level": "entry",
            "salary_min": 0,
            "salary_max": 0,
        }
        b_orm = analyze_match(profile, orm_job, db=None)
        b_ext = analyze_job_like(profile, dict_job, db=None)
        assert b_orm["overall"] == b_ext["overall"]


def test_external_prefixes_exported():
    assert "jsearch_" in EXTERNAL_PREFIXES


# ── /api/ai/match external resolution ────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_match_target_rejects_garbage():
    from routes.ai import _resolve_match_target
    from database.connection import SessionLocal

    class FakeUser:
        id = 999999

    db = SessionLocal()
    try:
        with pytest.raises(Exception):
            await _resolve_match_target("not-a-real-id!", FakeUser(), db)
    finally:
        db.close()
