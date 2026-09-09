from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import User, Profile, Job, Skill
from schemas.schemas import AIMatchRequest, AICareerAdviceRequest
from utils.auth import get_current_user
from services.matching_service import get_match_breakdown
from services.ai_service import (
    generate_match_explanation,
    generate_career_advice,
    generate_application_advice,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/match")
async def explain_match(
    data: AIMatchRequest,
    user: User = Depends(get_current_user),
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


@router.post("/explain-job")
async def explain_job(
    data: AIMatchRequest,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
