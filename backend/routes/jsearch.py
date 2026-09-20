"""
JSearch API routes — real-time job search from Google for Jobs.
Merges JSearch results with local database for unified search experience.

Abuse protection:
- All paid-API-invoking endpoints are rate limited (per-user when authenticated,
  per-IP for anonymous visitors with a tight quota).
- Input bounds: query/location length, page numbers, enum filters.
- When JSEARCH_API_KEY is not configured, endpoints return a clear
  "external search unavailable" response instead of crashing.
- The RapidAPI key is never exposed to the frontend.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, field_validator

from database.connection import get_db
from models.models import User, Profile
from utils.auth import get_optional_user
from utils.rate_limiter import get_rate_limiter
from utils.client_ip import get_client_ip
from services.jsearch_service import (
    search_jobs, get_job_details, search_company_jobs, get_similar_jobs,
    get_search_summary, JSEARCH_CONFIGURED,
)
from services.matching_service import score_job_like, analyze_job_like
from config import RATE_LIMIT_JSEARCH_PER_MINUTE

logger = logging.getLogger("rolio.jsearch")

router = APIRouter(prefix="/api/jsearch", tags=["jsearch"])

_rate_limiter = get_rate_limiter()

# Anonymous visitors get a much tighter quota than authenticated users
# (protects the paid RapidAPI key from abuse).
ANON_SEARCH_LIMIT_PER_HOUR = 10
ANON_DETAIL_LIMIT_PER_HOUR = 20

# Input bounds
MAX_QUERY_LENGTH = 200
MAX_LOCATION_LENGTH = 100
MAX_PAGE = 20
MAX_NUM_PAGES = 5

VALID_DATE_POSTED = {"today", "3days", "week", "month"}
VALID_EMPLOYMENT_TYPES = {"FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN", "INTERNSHIP"}


def _check_search_quota(user: Optional[User], request: Request, *, detail: bool = False) -> None:
    """Enforce per-user (auth) or per-IP (anonymous) quota. Raises 429."""
    if user:
        allowed = _rate_limiter.check(
            "jsearch_detail" if detail else "jsearch_search",
            f"user:{user.id}",
            RATE_LIMIT_JSEARCH_PER_MINUTE * 2,  # per-user hourly-ish allowance
            3600,
        )
    else:
        allowed = _rate_limiter.check(
            "jsearch_detail" if detail else "jsearch_search",
            f"ip:{get_client_ip(request)}",
            ANON_DETAIL_LIMIT_PER_HOUR if detail else ANON_SEARCH_LIMIT_PER_HOUR,
            3600,
        )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again in an hour.",
        )


def _unavailable_response(query: str, page: int) -> dict:
    """Consistent response when the external search API is not configured."""
    return {
        "data": [],
        "count": 0,
        "page": page,
        "num_pages": 1,
        "query": query,
        "source": "unavailable",
        "summary": "External job search is unavailable — no API key configured. Local jobs are still searchable.",
        "external_available": False,
    }


class JSearchRequest(BaseModel):
    query: str
    page: int = 1
    num_pages: int = 1
    location: Optional[str] = None
    remote_only: bool = False
    date_posted: Optional[str] = None  # today, 3days, week, month
    employment_type: Optional[str] = None  # FULLTIME, PARTTIME, CONTRACTOR, INTERN

    @field_validator("query")
    @classmethod
    def query_bounds(cls, v: str) -> str:
        v = (v or "").strip()[:MAX_QUERY_LENGTH]
        if not v:
            raise ValueError("Query is required")
        return v

    @field_validator("location")
    @classmethod
    def location_bounds(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return v.strip()[:MAX_LOCATION_LENGTH]

    @field_validator("date_posted")
    @classmethod
    def date_posted_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in VALID_DATE_POSTED:
            raise ValueError(f"date_posted must be one of {sorted(VALID_DATE_POSTED)}")
        return v

    @field_validator("employment_type")
    @classmethod
    def employment_type_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.upper()
        if v not in VALID_EMPLOYMENT_TYPES:
            raise ValueError(f"employment_type must be one of {sorted(VALID_EMPLOYMENT_TYPES)}")
        return "INTERN" if v == "INTERNSHIP" else v


def _apply_match_scores(results: dict, user: Optional[User], db) -> dict:
    """Attach unified engine match scores for logged-in users (same formula as
    every other job source — see services.matching_service)."""
    if not user or not results.get("data"):
        return results
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return results
    cached_skills = [s.name for s in profile.skills]
    for job in results["data"]:
        job["match_score"] = score_job_like(profile, job, db, cached_skills=cached_skills)
        # Explainable card fields: top matches + classified gaps (required > preferred)
        breakdown = analyze_job_like(profile, job, db, cached_skills=cached_skills)
        job["matched_skills"] = breakdown.get("matched_skills", [])[:4]
        job["missing_skills"] = [m["skill"] if isinstance(m, dict) else m
                                 for m in breakdown.get("missing_skill_details", [])[:3]]
    results["data"].sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return results


@router.post("/search")
async def search_real_jobs(
    data: JSearchRequest,
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
    db=Depends(get_db),
):
    """Search real jobs from Google for Jobs via JSearch API (rate limited)."""
    if not JSEARCH_CONFIGURED:
        return _unavailable_response(data.query, data.page)

    _check_search_quota(user, request)

    data.page = max(1, min(data.page, MAX_PAGE))
    data.num_pages = max(1, min(data.num_pages, MAX_NUM_PAGES))

    results = await search_jobs(
        query=data.query,
        page=data.page,
        num_pages=data.num_pages,
        location=data.location,
        remote_only=data.remote_only,
        date_posted=data.date_posted,
        employment_type=data.employment_type,
    )

    results = _apply_match_scores(results, user, db)
    results["summary"] = get_search_summary(data.query, results)
    results["external_available"] = True
    return results


@router.get("/search")
async def search_real_jobs_get(
    request: Request,
    q: str = Query(..., min_length=1, max_length=MAX_QUERY_LENGTH, description="Search query"),
    page: int = Query(1, ge=1, le=MAX_PAGE),
    location: Optional[str] = Query(None, max_length=MAX_LOCATION_LENGTH),
    remote: bool = False,
    date_posted: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db=Depends(get_db),
):
    """GET endpoint for job search (rate limited per-user or per-IP)."""
    if date_posted and date_posted not in VALID_DATE_POSTED:
        raise HTTPException(status_code=400, detail=f"date_posted must be one of {sorted(VALID_DATE_POSTED)}")
    if employment_type:
        employment_type = employment_type.upper()
        if employment_type not in VALID_EMPLOYMENT_TYPES:
            raise HTTPException(status_code=400, detail=f"employment_type must be one of {sorted(VALID_EMPLOYMENT_TYPES)}")
        employment_type = "INTERN" if employment_type == "INTERNSHIP" else employment_type

    if not JSEARCH_CONFIGURED:
        return _unavailable_response(q, page)

    _check_search_quota(user, request)

    results = await search_jobs(
        query=q,
        page=page,
        location=location,
        remote_only=remote,
        date_posted=date_posted,
        employment_type=employment_type,
    )

    results = _apply_match_scores(results, user, db)
    results["summary"] = get_search_summary(q, results)
    results["external_available"] = True
    return results


@router.get("/job/{job_id}")
async def get_jsearch_job(
    job_id: str,
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
    db=Depends(get_db),
):
    """Get detailed info for a specific JSearch job (rate limited)."""
    if len(job_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid job id")

    if not JSEARCH_CONFIGURED:
        raise HTTPException(status_code=503, detail="External job search is unavailable — no API key configured.")

    _check_search_quota(user, request, detail=True)

    detail = await get_job_details(job_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Job not found or API unavailable")

    detail = _apply_match_scores({"data": [detail]}, user, db)
    result = detail["data"][0]
    # Full explainable breakdown for the job-detail page ("Why this job?" panel)
    if user:
        result["match_breakdown"] = analyze_job_like(
            db.query(Profile).filter(Profile.user_id == user.id).first(), detail, db
        )
    return result


@router.get("/similar/{job_id}")
async def get_similar(
    job_id: str,
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
):
    """Get similar jobs to a given JSearch job (rate limited)."""
    if len(job_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid job id")

    if not JSEARCH_CONFIGURED:
        return {"data": [], "count": 0, "external_available": False}

    _check_search_quota(user, request, detail=True)

    similar = await get_similar_jobs(job_id)
    return {"data": similar, "count": len(similar), "external_available": True}


@router.get("/company/{company_name}")
async def search_company(
    company_name: str,
    request: Request,
    page: int = Query(1, ge=1, le=MAX_PAGE),
    user: Optional[User] = Depends(get_optional_user),
    db=Depends(get_db),
):
    """Search for jobs at a specific company (rate limited)."""
    company_name = company_name.strip()[:MAX_LOCATION_LENGTH]
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name is required")

    if not JSEARCH_CONFIGURED:
        return _unavailable_response(company_name, page)

    _check_search_quota(user, request)

    results = await search_company_jobs(company_name, page=page)
    results = _apply_match_scores(results, user, db)
    results["external_available"] = True
    return results
