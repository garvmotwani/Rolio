"""
Unified search — merges local database jobs with JSearch real-time results.
Single endpoint for the frontend to search everything.

Fixes:
- Parallel execution of local DB + JSearch (was sequential, causing 15s+ delays)
- Better location handling for JSearch
- Proper internship/employment type detection from query keywords
- Post-filter JSearch results by experience level
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from database.connection import get_db
from models.models import User, Job, Company, SavedJob, Application, Profile, SearchHistory
from utils.auth import get_optional_user, get_current_user
from utils.rate_limiter import get_rate_limiter
from services.matching_service import calculate_match_score
from services.jsearch_service import search_jobs as jsearch_search, get_search_summary, JSEARCH_CONFIGURED
from services.free_job_boards import search_free_boards, normalize_for_unified

router = APIRouter(prefix="/api/search", tags=["unified-search"])

# Anonymous visitors get a tight quota on the paid external search leg
_UNIFIED_ANON_LIMIT_PER_HOUR = 15
_unified_limiter = get_rate_limiter()

# Keywords that indicate internship intent
INTERNSHIP_KEYWORDS = {"intern", "internship", "interns", "trainee", "apprentice", "co-op", "coop"}


def _detect_employment_type(query: str, experience_level: Optional[str]) -> Optional[str]:
    """Detect employment type from query text and experience level filter."""
    q_lower = query.lower()

    # Explicit experience level filter
    if experience_level == "intern":
        return "INTERN"

    # Detect from query keywords
    if any(kw in q_lower for kw in INTERNSHIP_KEYWORDS):
        return "INTERN"

    return None


def _detect_internship_from_query(query: str) -> bool:
    """Check if the query is looking for internships."""
    return any(kw in query.lower() for kw in INTERNSHIP_KEYWORDS)


def _build_jsearch_query(query: str, location: Optional[str], is_internship: bool) -> str:
    """Build a clean JSearch query string."""
    parts = [query.strip()]

    # Add "intern" to query if it's an internship search but not already in query
    if is_internship and "intern" not in query.lower():
        parts.append("intern")

    # Don't append location to query — JSearch handles location poorly with "in" syntax
    # Instead, let the caller pass location separately if the API supports it
    return " ".join(parts)


# Indian city aliases — users type "bangalore", job data says "Bengaluru".
# Maps input → all acceptable spellings for local ILIKE matching.
CITY_ALIASES: dict[str, list[str]] = {
    "bangalore": ["bengaluru", "bangalore"],
    "bengaluru": ["bengaluru", "bangalore"],
    "bombay": ["mumbai", "bombay"],
    "mumbai": ["mumbai", "bombay"],
    "madras": ["chennai", "madras"],
    "chennai": ["chennai", "madras"],
    "calcutta": ["kolkata", "calcutta"],
    "kolkata": ["kolkata", "calcutta"],
    "gurgaon": ["gurugram", "gurgaon"],
    "gurugram": ["gurugram", "gurgaon"],
    "bangalore/bengaluru": ["bengaluru", "bangalore"],
}


def _location_variants(location: str) -> list[str]:
    """All spellings to match for a location input (alias-aware)."""
    loc = location.strip()
    if not loc:
        return []
    key = loc.lower()
    variants = CITY_ALIASES.get(key)
    if variants:
        return variants
    # Multi-word input like "bangalore, india" — check the first token too
    first = key.split(",")[0].strip()
    if first != key and first in CITY_ALIASES:
        return CITY_ALIASES[first] + [loc]
    return [loc]


def _local_search(
    q: str, location: str, work_type: Optional[str], experience_level: Optional[str],
    salary_min: Optional[int], salary_max: Optional[int],
    page: int, per_page: int, user_id: Optional[int], profile,
    db: Session,
) -> tuple[list[dict], int]:
    """Run local database search. Returns (results, total_count)."""
    q_db = db.query(Job).filter(Job.is_active == True)

    if q:
        search_term = f"%{q}%"
        q_db = q_db.filter(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
                Job.skills_required.ilike(search_term),
                Job.requirements.ilike(search_term),
            )
        )

    if location:
        # Alias-aware: "bangalore" matches "Bengaluru" and vice versa
        q_db = q_db.filter(
            or_(*[Job.location.ilike(f"%{v}%") for v in _location_variants(location)])
        )

    if work_type:
        q_db = q_db.filter(Job.work_type == work_type)

    # For internships, also match "intern" in title
    if experience_level == "intern":
        q_db = q_db.filter(
            or_(
                Job.experience_level == "intern",
                Job.title.ilike("%intern%"),
            )
        )
    elif experience_level:
        q_db = q_db.filter(Job.experience_level == experience_level)

    if salary_min:
        q_db = q_db.filter(Job.salary_max >= salary_min)
    if salary_max:
        q_db = q_db.filter(Job.salary_min <= salary_max)

    total = q_db.count()
    jobs = q_db.offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for job in jobs:
        company = db.query(Company).filter(Company.id == job.company_id).first()
        is_saved = False
        is_applied = False
        if user_id:
            is_saved = db.query(SavedJob).filter(
                SavedJob.user_id == user_id, SavedJob.job_id == job.id
            ).first() is not None
            is_applied = db.query(Application).filter(
                Application.user_id == user_id, Application.job_id == job.id
            ).first() is not None

        match_score = 0.0
        matched = []
        missing = []
        if profile:
            match_score = calculate_match_score(profile, job, db)
            from services.matching_service import analyze_match
            breakdown = analyze_match(profile, job, db)
            matched = breakdown.get("matched_skills", [])[:4]
            missing = [m["skill"] if isinstance(m, dict) else m
                       for m in breakdown.get("missing_skill_details", [])[:3]]

        try:
            import json
            skills = json.loads(job.skills_required) if job.skills_required else []
        except Exception:
            skills = []

        results.append({
            "id": job.id,
            "title": job.title,
            "company_name": company.name if company else "",
            "company_logo": company.logo_url if company else "",
            "location": job.location,
            "work_type": job.work_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "experience_level": job.experience_level,
            "employment_type": job.employment_type,
            "skills": skills,
            "match_score": match_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "posted_at": job.posted_at.isoformat(),
            "is_saved": is_saved,
            "is_applied": is_applied,
            "source": "local",
            "apply_link": job.application_url or "",
        })

    return results, total


async def _jsearch_search(
    q: str, location: Optional[str], work_type: Optional[str],
    experience_level: Optional[str], date_posted: Optional[str],
    page: int, user_id: Optional[int], profile, db: Session,
) -> tuple[list[dict], int]:
    """Run JSearch real-time search. Returns (results, total_count)."""
    is_internship = _detect_internship_from_query(q) or experience_level == "intern"
    emp_type = _detect_employment_type(q, experience_level)

    # Build a clean query
    search_query = _build_jsearch_query(q, location, is_internship)
    # City alias: JSearch knows "Bangalore" but not always "Bengaluru"
    loc_lower = (location or "").lower()
    if loc_lower in ("bengaluru", "bengaluru, india"):
        location = "bangalore"

    remote_flag = work_type == "remote" if work_type else False

    try:
        js_results = await jsearch_search(
            query=search_query,
            page=page,
            num_pages=1,
            location=location if location else None,
            remote_only=remote_flag,
            date_posted=date_posted,
            employment_type=emp_type,
        )
    except Exception:
        return [], 0

    total = js_results.get("count", 0)
    jsearch_raw = js_results.get("data", [])

    results = []
    for job in jsearch_raw:
        # Post-filter: skip jobs that don't match the experience level
        if experience_level and experience_level != "intern":
            job_exp = job.get("experience_level", "mid")
            if job_exp != experience_level:
                continue
        elif is_internship:
            # For internships, prefer jobs tagged as intern but don't filter strictly
            # since JSearch may not always tag them correctly
            pass

        # Check for duplicates with local DB
        existing = db.query(Job).filter(
            Job.title.ilike(job.get("title", "")),
            Job.is_active == True,
        ).first()
        if existing:
            continue

        js_id = job.get("job_id", "")
        prefixed_id = f"jsearch_{js_id}" if js_id else None

        results.append({
            "id": prefixed_id,
            "jsearch_id": js_id,
            "title": job.get("title", ""),
            "company_name": job.get("company_name", ""),
            "company_logo": job.get("company_logo", ""),
            "location": job.get("location", ""),
            "work_type": job.get("work_type", "hybrid"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "experience_level": job.get("experience_level", "mid"),
            "employment_type": job.get("employment_type", "full-time"),
            "skills": job.get("skills", []),
            "match_score": job.get("match_score", 0),
            "posted_at": job.get("posted_at", ""),
            "is_saved": False,
            "is_applied": False,
            "source": "jsearch",
            "apply_link": job.get("apply_link", ""),
            "google_link": job.get("google_link", ""),
            "publisher": job.get("publisher", ""),
        })

    return results, total


async def _free_boards_search(
    q: str, page: int,
) -> tuple[list[dict], int]:
    """Query free boards (Remotive + Jobicy) as a third results leg.

    These boards are remote-only, so they only meaningfully contribute when
    the query fits (any query — they're keyword-searched) — always included
    but ranked after local/JSearch via the sort below. Page 1 only: the
    boards don't paginate, deeper pages would just repeat page-1 results.
    """
    if page > 1:
        return [], 0
    try:
        raw = await search_free_boards(q, limit_per_source=15)
    except Exception:
        return [], 0

    # Relevance post-filter: the boards' search APIs are fuzzy (Jobicy matches
    # tags/geo loosely), so require at least one meaningful query term in the
    # title or skills. Keeps "intern" searches free of "International Tax" noise.
    import re as _re
    stop = {"and", "the", "for", "with", "job", "jobs"}
    terms = [t for t in q.lower().split() if len(t) >= 3 and t not in stop]
    if not terms:
        terms = [w for w in q.lower().split() if len(w) >= 3]
    intern_mode = any(t.startswith("intern") for t in q.lower().split())
    # "intern" must be a whole word (or internship/interns) — "international"
    # also contains the substring and would otherwise pollute results.
    intern_re = _re.compile(r"\bintern(ship|s)?\b")
    filtered = []
    for j in raw:
        hay = (j.get("title", "") + " " + " ".join(j.get("skills", []))).lower()
        if intern_mode:
            if intern_re.search(hay):
                filtered.append(j)
            continue
        if terms and any(t in hay for t in terms):
            filtered.append(j)

    return [normalize_for_unified(j) for j in filtered], len(filtered)


@router.get("")
async def unified_search(
    request: Request,
    q: str = Query("", max_length=200, description="Search query"),
    location: str = Query("", max_length=100, description="Location filter"),
    work_type: Optional[str] = Query(None, max_length=20),
    experience_level: Optional[str] = Query(None, max_length=20),
    salary_min: Optional[int] = Query(None, ge=0),
    salary_max: Optional[int] = Query(None, ge=0),
    date_posted: Optional[str] = Query(None),
    remote: bool = Query(False),
    source: str = Query("all", description="all, local, jsearch"),
    page: int = Query(1, ge=1, le=20),
    per_page: int = Query(20, ge=1, le=50),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Unified job search across local database and JSearch (Google for Jobs).
    Local DB + JSearch run in PARALLEL for fast results.

    The paid JSearch leg is protected: input bounds + an IP-based quota for
    anonymous visitors (per-user quotas apply on the dedicated /api/jsearch
    endpoints). When no API key is configured, local results are returned.
    """
    user_id = user.id if user else None
    profile = None
    if user_id:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    # External legs run when there's a query OR a location (e.g. "bangalore"
    # with the keyword box empty should still find real jobs there).
    external_trigger = bool((q or location) and source in ("all", "jsearch"))

    # ─── Guard the paid external search leg ───────────────
    if external_trigger and JSEARCH_CONFIGURED and not user:
        client_ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                     or (request.client.host if request.client else "unknown"))
        if not _unified_limiter.check("unified_search", f"ip:{client_ip}", _UNIFIED_ANON_LIMIT_PER_HOUR, 3600):
            raise HTTPException(status_code=429, detail="Search rate limit exceeded. Sign in for a higher quota.")
    local_task = asyncio.to_thread(
        _local_search, q, location, work_type, experience_level,
        salary_min, salary_max, page, per_page, user_id, profile, db,
    )

    jsearch_task = asyncio.create_task(
        _jsearch_search(q or location, location, work_type, experience_level,
                        date_posted, page, user_id, profile, db)
    ) if (external_trigger and q) else None

    free_task = asyncio.create_task(
        _free_boards_search(q or location, page)
    ) if (source == "all" and (q or location)) else None

    # Await all legs in parallel
    local_results, total_local = await local_task
    jsearch_results, total_jsearch = await jsearch_task if jsearch_task else ([], 0)
    free_results, total_free = await free_task if free_task else ([], 0)

    # ─── Merge and sort ────────────────────────────────────
    # Dedupe external results by (title-lower, company-lower) — the boards and
    # JSearch both draw from overlapping aggregator pools.
    seen = set()
    deduped_external = []
    for j in jsearch_results + free_results:
        key = (j.get("title", "").lower().strip(), j.get("company_name", "").lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped_external.append(j)

    all_results = local_results + deduped_external

    if profile:
        all_results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    else:
        all_results.sort(key=lambda x: x.get("posted_at", ""), reverse=True)

    total = total_local + len(deduped_external)

    return {
        "jobs": all_results,
        "total": total,
        "total_local": total_local,
        "total_jsearch": total_jsearch,
        "page": page,
        "per_page": per_page,
        "source": source,
        "query": q,
        "total_free": total_free,
        "summary": (
            f"Found {total_local} local + {total_jsearch} real-time + {total_free} remote-board jobs"
            if q else f"{total_local} jobs in database"
        ),
    }


@router.get("/suggest")
async def search_suggestions(
    q: str = Query("", min_length=2),
):
    """Get search suggestions for autocomplete."""
    suggestions = []
    q_lower = q.lower()

    titles = [
        "Software Engineer", "Frontend Developer", "Backend Developer",
        "Full Stack Developer", "Data Scientist", "ML Engineer",
        "DevOps Engineer", "Product Manager", "UX Designer",
        "iOS Developer", "Android Developer", "Cloud Engineer",
        "Data Engineer", "Security Engineer", "SRE",
        "Technical Writer", "Solutions Architect", "Engineering Manager",
        "Intern", "Internship",
    ]

    skills = [
        "Python", "JavaScript", "TypeScript", "React", "Node.js",
        "Java", "Go", "Rust", "C++", "SQL", "AWS", "Docker",
        "Kubernetes", "TensorFlow", "PyTorch", "GraphQL",
    ]

    locations = [
        "Bengaluru", "Bangalore", "Mumbai", "Delhi", "Hyderabad",
        "Pune", "Chennai", "Gurugram", "Noida", "Kolkata",
        "Remote",
    ]

    for t in titles:
        if q_lower in t.lower():
            suggestions.append({"text": t, "type": "title"})

    for s in skills:
        if q_lower in s.lower():
            suggestions.append({"text": f"{s} jobs", "type": "skill"})

    for l in locations:
        if q_lower in l.lower():
            suggestions.append({"text": l, "type": "location"})

    return {"suggestions": suggestions[:8]}


# ─── Search History ──────────────────────────────────────────


@router.get("/history")
def get_search_history(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's recent searches (most recent first)."""
    entries = db.query(SearchHistory).filter(
        SearchHistory.user_id == user.id
    ).order_by(SearchHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "query": e.query,
            "location": e.location,
            "work_type": e.work_type,
            "experience_level": e.experience_level,
            "source": e.source,
            "results_count": e.results_count,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.post("/history")
def save_search(
    query: str = Query("", max_length=200),
    location: str = Query("", max_length=100),
    work_type: Optional[str] = Query(None, max_length=20),
    experience_level: Optional[str] = Query(None, max_length=20),
    source: str = Query("all", max_length=20),
    results_count: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a search. Identical searches bump the timestamp instead of duplicating."""
    existing = db.query(SearchHistory).filter(
        SearchHistory.user_id == user.id,
        SearchHistory.query == query,
        SearchHistory.location == location,
        SearchHistory.work_type == (work_type or ""),
        SearchHistory.experience_level == (experience_level or ""),
    ).first()

    if existing:
        existing.created_at = datetime.utcnow()
        existing.results_count = results_count
        existing.source = source
        db.commit()
        return {"message": "Search updated", "id": existing.id}

    entry = SearchHistory(
        user_id=user.id,
        query=query,
        location=location,
        work_type=work_type or "",
        experience_level=experience_level or "",
        source=source,
        results_count=results_count,
    )
    db.add(entry)
    db.commit()

    # Keep only the latest 30 searches per user
    old = db.query(SearchHistory).filter(
        SearchHistory.user_id == user.id
    ).order_by(SearchHistory.created_at.desc()).offset(30).all()
    for o in old:
        db.delete(o)
    db.commit()

    return {"message": "Search saved", "id": entry.id}


@router.delete("/history/{entry_id}")
def delete_search_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single search history entry (owner only)."""
    entry = db.query(SearchHistory).filter(
        SearchHistory.id == entry_id, SearchHistory.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Search entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Search deleted"}


@router.delete("/history")
def clear_search_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all search history for the user."""
    db.query(SearchHistory).filter(SearchHistory.user_id == user.id).delete()
    db.commit()
    return {"message": "Search history cleared"}
