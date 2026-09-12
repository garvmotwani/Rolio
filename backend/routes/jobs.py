import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database.connection import get_db
from models.models import Job, Company, SavedJob, Application, User, Profile

from schemas.schemas import JobResponse, JobListResponse, JobSearchRequest
from utils.auth import get_current_user, get_optional_user
from services.matching_service import calculate_match_score
from services.jsearch_service import get_job_details as jsearch_get_details
from services.free_job_boards import get_free_board_job

router = APIRouter(prefix="/api", tags=["jobs"])


def job_to_response(job: Job, user_id: int = None, db: Session = None) -> JobResponse:
    company = db.query(Company).filter(Company.id == job.company_id).first() if db else None
    is_saved = False
    is_applied = False
    match_score = 0.0

    if db and user_id:
        is_saved = db.query(SavedJob).filter(
            SavedJob.user_id == user_id, SavedJob.job_id == job.id
        ).first() is not None
        is_applied = db.query(Application).filter(
            Application.user_id == user_id, Application.job_id == job.id
        ).first() is not None

    return JobResponse(
        id=job.id,
        company_id=job.company_id,
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        responsibilities=job.responsibilities,
        preferred_qualifications=job.preferred_qualifications,
        skills_required=job.skills_required,
        skills_preferred=job.skills_preferred,
        location=job.location,
        work_type=job.work_type,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        experience_level=job.experience_level,
        employment_type=job.employment_type,
        application_url=job.application_url,
        is_active=job.is_active,
        posted_at=job.posted_at,
        company_name=company.name if company else "",
        company_logo=company.logo_url if company else "",
        company_industry=company.industry if company else "",
        match_score=match_score,
        is_saved=is_saved,
        is_applied=is_applied,
    )


@router.get("/jobs", response_model=JobListResponse)
def search_jobs(
    query: str = "",
    location: str = "",
    work_type: str = None,
    experience_level: str = None,
    salary_min: int = None,
    salary_max: int = None,
    employment_type: str = None,
    sort_by: str = "best_match",
    page: int = 1,
    per_page: int = 20,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    # Validate pagination bounds
    page = max(1, min(page, 1000))
    per_page = max(1, min(per_page, 50))
    query = (query or "")[:200]  # Cap query length
    location = (location or "")[:100]

    VALID_SORT = {"best_match", "most_recent", "salary"}
    if sort_by not in VALID_SORT:
        sort_by = "best_match"

    user_id = user.id if user else None
    q = db.query(Job).filter(Job.is_active == True)

    if query:
        search_term = f"%{query}%"
        q = q.filter(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
                Job.skills_required.ilike(search_term),
                Job.requirements.ilike(search_term),
            )
        )

    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))

    if work_type:
        q = q.filter(Job.work_type == work_type)

    if experience_level:
        q = q.filter(Job.experience_level == experience_level)

    if employment_type:
        q = q.filter(Job.employment_type == employment_type)

    if salary_min:
        q = q.filter(Job.salary_max >= salary_min)

    if salary_max:
        q = q.filter(Job.salary_min <= salary_max)

    total = q.count()

    if sort_by == "most_recent":
        q = q.order_by(Job.posted_at.desc())
    elif sort_by == "salary":
        q = q.order_by(Job.salary_max.desc())
    else:
        q = q.order_by(Job.posted_at.desc())

    jobs = q.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate match scores — cache profile skills to avoid N+1 queries
    profile = None
    cached_profile_skills = None
    if user_id:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if profile:
            from models.models import Skill
            skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
            cached_profile_skills = [s.name for s in skills]

    job_responses = []
    for job in jobs:
        resp = job_to_response(job, user_id, db)
        if profile:
            resp.match_score = calculate_match_score(profile, job, db, cached_skills=cached_profile_skills)
        job_responses.append(resp)

    # Sort by match score if best_match
    if sort_by == "best_match":
        job_responses.sort(key=lambda x: x.match_score, reverse=True)

    return JobListResponse(jobs=job_responses, total=total, page=page, per_page=per_page)


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get job detail — handles local DB IDs (int) and external IDs
    (jsearch_* / remotive_* / jobicy_* prefixes)."""
    # ── Free-board job (remotive_/jobicy_ prefixed ID) ──
    if isinstance(job_id, str) and (
        job_id.startswith("remotive_") or job_id.startswith("jobicy_")
    ):
        detail = await get_free_board_job(job_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Job not found — listing may have expired from the source board")
        # Compute match score if user has a profile
        if user and user.profile:
            from services.matching_service import compute_quick_match
            detail["match_score"] = compute_quick_match(user.profile, detail)
        return detail

    # ── JSearch job (prefixed ID) ────────────────────────
    if isinstance(job_id, str) and job_id.startswith("jsearch_"):
        js_real_id = job_id.removeprefix("jsearch_")
        detail = await jsearch_get_details(js_real_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Job not found")

        # Compute match score if user has a profile
        match_score = 0.0
        if user and user.profile:
            # Create a lightweight match from available data
            from services.matching_service import compute_quick_match
            match_score = compute_quick_match(user.profile, detail)

        return {
            "id": job_id,
            "company_id": 0,
            "title": detail.get("title", ""),
            "description": detail.get("description", ""),
            "requirements": "\n".join(detail.get("qualifications", [])) if detail.get("qualifications") else "",
            "responsibilities": "\n".join(detail.get("responsibilities", [])) if detail.get("responsibilities") else "",
            "preferred_qualifications": "",
            "skills_required": json.dumps(detail.get("skills", [])),
            "skills_preferred": "",
            "location": detail.get("location", ""),
            "work_type": detail.get("work_type", "hybrid"),
            "salary_min": detail.get("salary_min") or 0,
            "salary_max": detail.get("salary_max") or 0,
            "experience_level": detail.get("experience_level", "mid"),
            "employment_type": detail.get("employment_type", "full-time"),
            "application_url": detail.get("apply_link", ""),
            "posted_at": detail.get("posted_at", ""),
            "company_name": detail.get("company_name", ""),
            "company_logo": detail.get("company_logo", ""),
            "company_industry": detail.get("employer_company_type", ""),
            "match_score": match_score,
            "is_saved": False,
            "is_applied": False,
            "source": "jsearch",
            "google_link": detail.get("google_link", ""),
            "publisher": detail.get("publisher", ""),
            "benefits": detail.get("benefits", []),
        }

    # ── Local database job (numeric ID) ───────────────────
    try:
        numeric_id = int(job_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Job not found")

    job = db.query(Job).filter(Job.id == numeric_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    user_id = user.id if user else None
    resp = job_to_response(job, user_id, db)

    if user and user.profile:
        resp.match_score = calculate_match_score(user.profile, job, db)

    return resp


EXTERNAL_PREFIXES = ("jsearch_", "remotive_", "jobicy_")


async def _resolve_external_detail(job_id: str) -> Optional[dict]:
    """Fetch full job detail for any prefixed external ID."""
    if job_id.startswith("jsearch_"):
        return await jsearch_get_details(job_id.removeprefix("jsearch_"))
    return await get_free_board_job(job_id)


async def _import_external_job(job_id: str, db: Session) -> Optional[Job]:
    """Find or import an external job into the DB. Idempotent via external_id."""
    # Already imported?
    existing_job = db.query(Job).filter(Job.external_id == job_id).first()
    if existing_job:
        return existing_job

    # Legacy jsearch rows stored before external_id existed — match the old
    # fragile way (URL substring) and backfill external_id.
    if job_id.startswith("jsearch_"):
        js_real_id = job_id.removeprefix("jsearch_")
        legacy = db.query(Job).filter(
            Job.source == "jsearch", Job.application_url.ilike(f"%{js_real_id}%")
        ).first()
        if legacy:
            legacy.external_id = job_id
            db.flush()
            return legacy

    detail = await _resolve_external_detail(job_id)
    if not detail:
        return None

    # Find or create company
    company_name = detail.get("company_name", "")
    company = db.query(Company).filter(Company.name == company_name).first() if company_name else None
    if not company and company_name:
        company = Company(
            name=company_name,
            logo_url=detail.get("company_logo", ""),
            website=detail.get("company_website", ""),
        )
        db.add(company)
        db.flush()

    source = job_id.split("_", 1)[0]
    job = Job(
        company_id=company.id if company else 0,
        title=detail.get("title", ""),
        description=detail.get("description", ""),
        requirements="\n".join(detail.get("qualifications", [])),
        responsibilities="\n".join(detail.get("responsibilities", [])),
        skills_required=detail.get("skills_required") or json.dumps(detail.get("skills", [])),
        location=detail.get("location", ""),
        work_type=detail.get("work_type", "hybrid"),
        salary_min=detail.get("salary_min") or 0,
        salary_max=detail.get("salary_max") or 0,
        experience_level=detail.get("experience_level", "mid"),
        employment_type=detail.get("employment_type", "full-time"),
        application_url=detail.get("application_url") or detail.get("apply_link", ""),
        source=source,
        external_id=job_id,
    )
    db.add(job)
    db.flush()
    return job


@router.post("/jobs/{job_id}/save")
async def save_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a job — handles local DB IDs and external prefixed IDs
    (jsearch_/remotive_/jobicy_; external jobs are imported to DB first)."""
    # ── External job: fetch details and store in DB ─────
    if isinstance(job_id, str) and job_id.startswith(EXTERNAL_PREFIXES):
        job = await _import_external_job(job_id, db)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Check if already saved
        already = db.query(SavedJob).filter(
            SavedJob.user_id == user.id, SavedJob.job_id == job.id
        ).first()
        if already:
            return {"message": "Already saved"}

        saved = SavedJob(user_id=user.id, job_id=job.id)
        db.add(saved)
        db.commit()
        return {"message": "Job saved"}

    # ── Local job ────────────────────────────────────────
    try:
        numeric_id = int(job_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    existing = db.query(SavedJob).filter(
        SavedJob.user_id == user.id, SavedJob.job_id == numeric_id
    ).first()
    if existing:
        return {"message": "Already saved"}

    saved = SavedJob(user_id=user.id, job_id=numeric_id)
    db.add(saved)
    db.commit()
    return {"message": "Job saved"}


@router.delete("/jobs/{job_id}/save")
async def unsave_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):    
    """Unsave a job — handles local and external prefixed IDs."""
    if isinstance(job_id, str) and job_id.startswith(EXTERNAL_PREFIXES):
        existing_job = db.query(Job).filter(Job.external_id == job_id).first()
        if existing_job:
            db.query(SavedJob).filter(
                SavedJob.user_id == user.id, SavedJob.job_id == existing_job.id
            ).delete()
            db.commit()
        return {"message": "Job unsaved"}

    try:
        numeric_id = int(job_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    db.query(SavedJob).filter(
        SavedJob.user_id == user.id, SavedJob.job_id == numeric_id
    ).delete()
    db.commit()
    return {"message": "Job unsaved"}


@router.get("/saved-jobs")
def get_saved_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = db.query(SavedJob).filter(SavedJob.user_id == user.id).order_by(SavedJob.saved_at.desc()).all()
    results = []
    profile = db.query(Profile).filter(Profile.user_id == user.id).first() if user else None

    for s in saved:
        job = db.query(Job).filter(Job.id == s.job_id).first()
        if not job:
            continue
        company = db.query(Company).filter(Company.id == job.company_id).first()
        is_applied = db.query(Application).filter(
            Application.user_id == user.id, Application.job_id == job.id
        ).first() is not None

        match_score = 0.0
        if profile:
            match_score = calculate_match_score(profile, job, db)

        results.append({
            "id": s.id,
            "job_id": s.job_id,
            "saved_at": s.saved_at.isoformat(),
            "job_title": job.title,
            "company_name": company.name if company else "",
            "company_logo": company.logo_url if company else "",
            "job_location": job.location,
            "job_work_type": job.work_type,
            "job_salary_min": job.salary_min,
            "job_salary_max": job.salary_max,
            "skills_required": job.skills_required,
            "match_score": match_score,
            "is_applied": is_applied,
        })

    return results


@router.get("/companies/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    jobs = db.query(Job).filter(Job.company_id == company.id, Job.is_active == True).all()

    return {
        "id": company.id,
        "name": company.name,
        "logo_url": company.logo_url,
        "industry": company.industry,
        "location": company.location,
        "website": company.website,
        "description": company.description,
        "size": company.size,
        "founded": company.founded,
        "open_jobs_count": len(jobs),
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "location": j.location,
                "work_type": j.work_type,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "experience_level": j.experience_level,
                "posted_at": j.posted_at.isoformat(),
            }
            for j in jobs
        ],
    }
