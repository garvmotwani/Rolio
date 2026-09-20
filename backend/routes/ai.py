from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import User, Profile, Job, Skill
from schemas.schemas import AIMatchRequest, AICareerAdviceRequest
from utils.auth import get_current_user
from utils.ai_rate_limit import ai_rate_limit
from services.matching_service import (
    get_match_breakdown,
    analyze_match,
    analyze_job_like,
    EXTERNAL_PREFIXES,
)
from services.ai_service import (
    generate_match_explanation,
    generate_career_advice,
    generate_application_advice,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


async def _resolve_match_target(job_id, user: User, db: Session):
    """Resolve a local ORM Job or a dict-shaped external job + its breakdown.

    Returns (job, breakdown, is_external). External IDs (jsearch_/remotive_/
    jobicy_) get a deterministic breakdown from the unified engine; the AI
    narrative layer stays local-only until a detail fetch + cache exists.
    """
    if isinstance(job_id, str) and job_id.startswith(EXTERNAL_PREFIXES):
        detail = None
        if job_id.startswith("jsearch_"):
            from services.jsearch_service import get_job_details
            detail = await get_job_details(job_id.removeprefix("jsearch_"))
        else:
            from routes.jobs import _resolve_external_detail
            detail = await _resolve_external_detail(job_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Job not found or unavailable")
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        breakdown = analyze_job_like(profile, detail, db)
        return detail, breakdown, True

    try:
        numeric_id = int(job_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Job not found")

    job = db.query(Job).filter(Job.id == numeric_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    breakdown = analyze_match(profile, job, db) if profile else None
    return job, breakdown, False


@router.post("/match")
async def explain_match(
    data: AIMatchRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    """Explainable match analysis. Deterministic for all job sources; the AI
    narrative is generated only for local jobs (external narrative TODO once
    a detail cache exists)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    job, breakdown, is_external = await _resolve_match_target(data.job_id, user, db)

    if is_external:
        return {
            "breakdown": breakdown,
            "explanation": None,
            "source": "deterministic",
        }

    result = await generate_match_explanation(profile, job, db)
    return result


@router.post("/explain-job")
async def explain_job(
    data: AIMatchRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await generate_match_explanation(profile, job, db)
    return result


@router.post("/career-advice")
async def career_advice(
    data: AICareerAdviceRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    response = await generate_career_advice(profile, data.question, db)
    return {"response": response}


@router.post("/application-advice")
async def application_advice(
    data: AIMatchRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = await generate_application_advice(profile, job, db)
    return {"response": response}
