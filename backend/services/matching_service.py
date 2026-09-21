"""
Unified explainable match engine.

One scoring path for every job source (local DB, JSearch, free boards).
The engine is data-aware: a factor with no reliable data on either side is
EXCLUDED from the score (weight redistributed) instead of being assigned an
arbitrary neutral value — we don't pretend precision we don't have.

Public API:
    score_job(profile, job, db)               -> float (0-100)
    analyze_match(profile, job, db)           -> full explainable breakdown dict
    score_job_like(profile, job_dict, db)     -> float for dict-shaped jobs (external)
    analyze_job_like(profile, job_dict, db)   -> breakdown for dict-shaped jobs

Weights live in MATCH_WEIGHTS and must sum to 1.0.
"""
import json
from datetime import datetime
from typing import Any, Optional

from services.skill_normalizer import normalize_skill_list, overlap_sets

# ── Centralized weights (must sum to 1.0) ─────────────────────────────
MATCH_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.20,
    "role": 0.20,
    "location": 0.10,
    "work_type": 0.075,
    "salary": 0.075,
}

SENIORITY_YEARS = {
    "intern": 0, "entry": 0, "junior": 1, "mid": 3,
    "senior": 5, "lead": 8, "executive": 10,
}


# ── Field extraction: works for ORM Job objects and plain dicts ───────
def _field(job_or_dict: Any, name: str, default=None):
    if job_or_dict is None:
        return default
    if isinstance(job_or_dict, dict):
        return job_or_dict.get(name, default)
    return getattr(job_or_dict, name, default)


def _parse_skills_field(value) -> list:
    """skills_required/skills_preferred arrive as JSON strings, CSVs, or lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(s) for s in value]
    s = str(value).strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [x.strip() for x in s.split(",") if x.strip()]


def _profile_skills(profile, db) -> list:
    if profile is None:
        return []
    skills = getattr(profile, "skills", None)
    if skills is not None:
        try:
            names = [s.name for s in skills]
            if names or skills.__len__() == 0 and not _is_lazy_unloaded(skills):
                return names
        except Exception:
            pass
    # lazy relationship not loaded / detached — hit the DB
    try:
        from models.models import Skill
        rows = db.query(Skill).filter(Skill.profile_id == profile.id).all()
        return [s.name for s in rows]
    except Exception:
        return []


def _is_lazy_unloaded(rel) -> bool:
    state = getattr(rel, "_sa_instance_state", None)
    if state is None:
        return False
    return state.unloaded


def _profile_years(profile) -> Optional[float]:
    """Total experience years from profile experiences; None when unknowable."""
    exps = getattr(profile, "experiences", None)
    if not exps:
        return None
    now_year = datetime.now().year
    total = 0.0
    any_valid = False
    for e in exps:
        start = getattr(e, "start_date", None)
        if not start:
            continue
        try:
            sy = int(str(start)[:4])
            end = getattr(e, "end_date", None)
            if getattr(e, "is_current", False) or not end:
                ey = now_year
            else:
                ey = int(str(end)[:4])
            total += max(0.0, float(ey - sy))
            any_valid = True
        except (ValueError, IndexError):
            continue
    return total if any_valid else None


def _preferred_roles(profile) -> list:
    raw = getattr(profile, "preferred_roles", None) if profile else None
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, list):
            return [str(r) for r in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [r.strip() for r in str(raw).split(",") if r.strip()]


# ── Factor scorers: each returns (score 0-1, known bool, detail str|list) ──
def _skill_factor(profile_skills: list, job_required: list, job_preferred: list):
    required_canon = normalize_skill_list(job_required)
    preferred_canon = normalize_skill_list(job_preferred)
    all_job = list(dict.fromkeys(required_canon + preferred_canon))

    if not all_job:
        return 1.0, False, {"matched": [], "missing": [], "job_skills": []}

    matched, missing_raw, partial = overlap_sets(profile_skills, all_job)

    # Weight: required skills count double — missing a required skill hurts more.
    covered = 0.0
    total = 0.0
    for s in required_canon:
        total += 2.0
        if s in matched:
            covered += 2.0
        elif any(ps in s or s in ps for ps in partial if len(ps) >= 3):
            covered += 1.0
    for s in preferred_canon:
        total += 1.0
        if s in matched:
            covered += 1.0
        elif any(ps in s or s in ps for ps in partial if len(ps) >= 3):
            covered += 0.5

    score = min(1.0, covered / total) if total else 1.0

    # Missing-skill classification driven by the job's own data, not guesses.
    missing = []
    for s in all_job:
        if s in matched:
            continue
        is_partial = any(ps in s or s in ps for ps in partial if len(ps) >= 3)
        if is_partial:
            continue
        importance = "critical" if s in required_canon else "nice_to_have"
        missing.append({"skill": s, "importance": importance})

    matched_list = [s for s in all_job if s in matched]
    return score, True, {
        "matched": matched_list,
        "missing": missing,
        "partial": sorted(partial),
        "job_skills": all_job,
    }


def _experience_factor(profile, job_level: str) -> tuple:
    required_years = SENIORITY_YEARS.get((job_level or "").lower(), None)
    candidate_years = _profile_years(profile)
    if required_years is None and candidate_years is None:
        return 1.0, False, None
    if candidate_years is None:
        # Job wants N years, we don't know the candidate's — factor unknown.
        return 1.0, False, None
    if required_years is None:
        return 1.0, False, None

    if candidate_years >= required_years:
        return 1.0, True, {"years": candidate_years, "required": required_years}
    if required_years == 0:
        return 1.0, True, {"years": candidate_years, "required": 0}
    ratio = candidate_years / required_years
    if ratio >= 0.5:
        return 0.6 + 0.4 * ratio, True, {"years": candidate_years, "required": required_years}
    return max(0.2, ratio), True, {"years": candidate_years, "required": required_years}


def _role_factor(profile, job_title: str) -> tuple:
    roles = _preferred_roles(profile)
    title = (job_title or "").lower().strip()
    if not roles or not title:
        return 1.0, False, None

    title_words = set(title.replace("-", " ").split())
    best = 0.0
    for role in roles:
        rn = role.lower().strip()
        if not rn:
            continue
        if rn in title or title in rn:
            best = max(best, 1.0)
            continue
        role_words = set(rn.replace("-", " ").split())
        overlap = role_words & title_words
        if overlap:
            best = max(best, 0.6 + 0.4 * len(overlap) / max(len(role_words), 1))
    if best == 0.0:
        best = 0.35
    return best, True, {"preferred_roles": roles, "job_title": job_title}


def _location_factor(profile, job_location: str, job_work_type: str) -> tuple:
    loc = getattr(profile, "location", None) if profile else None
    job_loc = (job_location or "").lower().strip()
    if (not loc and not _preferred_locations(profile)) or not job_loc:
        return 1.0, False, None

    if (job_work_type or "").lower() == "remote":
        return 1.0, True, {"reason": "remote"}

    user_loc = (loc or "").lower().strip()
    if user_loc and (user_loc in job_loc or job_loc in user_loc):
        return 1.0, True, {"reason": "same_city"}

    for pref in _preferred_locations(profile):
        p = pref.lower().strip()
        if p and (p in job_loc or job_loc in p):
            return 1.0, True, {"reason": "preferred_location"}

    return 0.4, True, {"reason": "different_location"}


def _preferred_locations(profile) -> list:
    raw = getattr(profile, "preferred_locations", None) if profile else None
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def _work_type_factor(profile, job_work_type: str) -> tuple:
    pref = getattr(profile, "preferred_work_type", None) if profile else None
    if not pref or not job_work_type:
        return 1.0, False, None
    p, j = pref.lower().strip(), job_work_type.lower().strip()
    if p == j:
        return 1.0, True, None
    return 0.5, True, None


def _salary_factor(profile, job_min, job_max) -> tuple:
    p_min = getattr(profile, "salary_expectation_min", 0) if profile else 0
    p_max = getattr(profile, "salary_expectation_max", 0) if profile else 0
    if (not p_min and not p_max) or (not job_min and not job_max):
        return 1.0, False, None

    p_lo, p_hi = float(p_min or 0), float(p_max or 10**12)
    j_lo, j_hi = float(job_min or 0), float(job_max or 10**12)
    if j_hi >= p_lo and j_lo <= p_hi:
        return 1.0, True, None
    if j_lo >= p_lo * 0.8:
        return 0.6, True, None
    return 0.2, True, None


# ── Core engine ────────────────────────────────────────────────────────
def analyze_match(profile, job, db, cached_skills: list = None) -> dict:
    """Full explainable analysis for an ORM Job."""
    factors_data = {
        "skills": _skill_factor(
            cached_skills if cached_skills is not None else _profile_skills(profile, db),
            _parse_skills_field(_field(job, "skills_required")),
            _parse_skills_field(_field(job, "skills_preferred")),
        ),
        "experience": _experience_factor(profile, _field(job, "experience_level", "")),
        "role": _role_factor(profile, _field(job, "title", "")),
        "location": _location_factor(profile, _field(job, "location", ""), _field(job, "work_type", "")),
        "work_type": _work_type_factor(profile, _field(job, "work_type", "")),
        "salary": _salary_factor(profile, _field(job, "salary_min", 0), _field(job, "salary_max", 0)),
    }
    return _build_breakdown(factors_data)


def analyze_job_like(profile, job_dict: dict, db, cached_skills: list = None) -> dict:
    """Full explainable analysis for a dict-shaped (external) job."""
    factors_data = {
        "skills": _skill_factor(
            cached_skills if cached_skills is not None else _profile_skills(profile, db),
            _parse_skills_field(job_dict.get("skills_required") or job_dict.get("skills")),
            _parse_skills_field(job_dict.get("skills_preferred")),
        ),
        "experience": _experience_factor(profile, job_dict.get("experience_level", "")),
        "role": _role_factor(profile, job_dict.get("title", "")),
        "location": _location_factor(profile, job_dict.get("location", ""), job_dict.get("work_type", "")),
        "work_type": _work_type_factor(profile, job_dict.get("work_type", "")),
        "salary": _salary_factor(profile, job_dict.get("salary_min", 0), job_dict.get("salary_max", 0)),
    }
    return _build_breakdown(factors_data)


def _build_breakdown(factors_data: dict) -> dict:
    factors = []
    weighted_total = 0.0
    weight_sum = 0.0

    for name, (score, known, detail) in factors_data.items():
        weight = MATCH_WEIGHTS[name]
        entry: dict = {
            "factor": name,
            "label": name.replace("_", " ").title(),
            "score": round(score * 100, 1),
            "weight": round(weight * 100, 1),
            "known": known,
        }
        if known:
            weighted_total += score * weight
            weight_sum += weight
            entry["contribution"] = round(score * weight / weight_sum_hint(factors_data) * 100, 1)
            if detail is not None:
                entry["details"] = detail
        else:
            entry["contribution"] = None
        factors.append(entry)

    overall = (weighted_total / weight_sum) * 100 if weight_sum else 0.0
    skills_detail = factors_data["skills"][2]

    return {
        "overall": round(overall, 1),
        "factors": factors,
        # legacy flat fields (frontend already renders these)
        "skills": round(factors_data["skills"][0] * 100, 1),
        "experience": round(factors_data["experience"][0] * 100, 1),
        "role": round(factors_data["role"][0] * 100, 1),
        "location": round(factors_data["location"][0] * 100, 1),
        "work_type": round(factors_data["work_type"][0] * 100, 1),
        "salary": round(factors_data["salary"][0] * 100, 1),
        "strong_matches": skills_detail.get("matched", []),
        "partial_matches": skills_detail.get("partial", []),
        "missing_skills": [m["skill"] for m in skills_detail.get("missing", [])],
        "missing_skill_details": skills_detail.get("missing", []),
        "matched_skills": skills_detail.get("matched", []),
        "data_confidence": round(weight_sum / sum(MATCH_WEIGHTS.values()) * 100, 1),
    }


def weight_sum_hint(factors_data: dict) -> float:
    """Known-weight sum for contribution normalization."""
    total = 0.0
    for name, (_s, known, _d) in factors_data.items():
        if known:
            total += MATCH_WEIGHTS[name]
    return total or 1.0


def score_job(profile, job, db, cached_skills: Optional[list] = None) -> float:
    """Single-number score for an ORM Job (same formula as analyze_match)."""
    factors_data = {
        "skills": _skill_factor(
            cached_skills if cached_skills is not None else _profile_skills(profile, db),
            _parse_skills_field(_field(job, "skills_required")),
            _parse_skills_field(_field(job, "skills_preferred")),
        ),
        "experience": _experience_factor(profile, _field(job, "experience_level", "")),
        "role": _role_factor(profile, _field(job, "title", "")),
        "location": _location_factor(profile, _field(job, "location", ""), _field(job, "work_type", "")),
        "work_type": _work_type_factor(profile, _field(job, "work_type", "")),
        "salary": _salary_factor(profile, _field(job, "salary_min", 0), _field(job, "salary_max", 0)),
    }
    weighted = sum(s * MATCH_WEIGHTS[n] for n, (s, known, _d) in factors_data.items() if known)
    wsum = sum(MATCH_WEIGHTS[n] for n, (_s, known, _d) in factors_data.items() if known)
    return round((weighted / wsum if wsum else 0.0) * 100, 1)


def score_job_like(profile, job_dict: dict, db, cached_skills: Optional[list] = None) -> float:
    """Single-number score for a dict-shaped (external) job."""
    factors_data = {
        "skills": _skill_factor(
            cached_skills if cached_skills is not None else _profile_skills(profile, db),
            _parse_skills_field(job_dict.get("skills_required") or job_dict.get("skills")),
            _parse_skills_field(job_dict.get("skills_preferred")),
        ),
        "experience": _experience_factor(profile, job_dict.get("experience_level", "")),
        "role": _role_factor(profile, job_dict.get("title", "")),
        "location": _location_factor(profile, job_dict.get("location", ""), job_dict.get("work_type", "")),
        "work_type": _work_type_factor(profile, job_dict.get("work_type", "")),
        "salary": _salary_factor(profile, job_dict.get("salary_min", 0), job_dict.get("salary_max", 0)),
    }
    weighted = sum(s * MATCH_WEIGHTS[n] for n, (s, known, _d) in factors_data.items() if known)
    wsum = sum(MATCH_WEIGHTS[n] for n, (_s, known, _d) in factors_data.items() if known)
    return round((weighted / wsum if wsum else 0.0) * 100, 1)


# ── Backward-compatible wrappers (existing callers keep working) ──────
def normalize(text: str) -> str:
    return (text or "").lower().strip()


# Prefixed IDs from external providers (jsearch/remotive/jobicy). Exported for
# consumers that need to branch on external vs local job identity.
EXTERNAL_PREFIXES = ("jsearch_", "remotive_", "jobicy_")


def parse_skills_from_string(skills_str: str) -> list:
    """Legacy alias kept for existing importers (ai_service etc.)."""
    return _parse_skills_field(skills_str)


def calculate_match_score(profile, job, db, cached_skills: list = None) -> float:
    return score_job(profile, job, db, cached_skills=cached_skills)


def get_match_breakdown(profile, job, db) -> dict:
    return analyze_match(profile, job, db)


def compute_quick_match(profile, job_detail: dict) -> float:
    return score_job_like(profile, job_detail or {}, None)


def get_recommendations(profile, db, limit: int = 20) -> list:
    from models.models import Application, Job

    applied_job_ids = {
        a.job_id for a in db.query(Application).filter(
            Application.user_id == profile.user_id
        ).all()
    }

    cached_skills = _profile_skills(profile, db)
    jobs = db.query(Job).filter(Job.is_active == True).all()

    scored = []
    for job in jobs:
        if job.id in applied_job_ids:
            continue
        score = score_job(profile, job, db, cached_skills=cached_skills)
        if score >= 30:
            scored.append((job, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
