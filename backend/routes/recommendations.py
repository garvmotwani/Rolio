from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import User, Profile, Company, SavedJob, Application
from utils.auth import get_current_user
from services.matching_service import get_recommendations, analyze_match

router = APIRouter(prefix="/api", tags=["recommendations"])


@router.get("/recommendations")
def get_user_recommendations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return []

    if not profile.skills or (hasattr(profile.skills, '__len__') and len(profile.skills) == 0):
        if not profile.title:
            return []

    recommendations = get_recommendations(profile, db, limit=15)
    profile_skills = [s.name for s in profile.skills]

    results = []
    for job, score in recommendations:
        company = db.query(Company).filter(Company.id == job.company_id).first()
        is_saved = db.query(SavedJob).filter(
            SavedJob.user_id == user.id, SavedJob.job_id == job.id
        ).first() is not None
        is_applied = db.query(Application).filter(
            Application.user_id == user.id, Application.job_id == job.id
        ).first() is not None

        results.append({
            "id": job.id,
            "company_id": job.company_id,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "responsibilities": job.responsibilities,
            "preferred_qualifications": job.preferred_qualifications,
            "skills_required": job.skills_required,
            "skills_preferred": job.skills_preferred,
            "location": job.location,
            "work_type": job.work_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "experience_level": job.experience_level,
            "employment_type": job.employment_type,
            "application_url": job.application_url,
            "is_active": job.is_active,
            "posted_at": job.posted_at.isoformat(),
            "company_name": company.name if company else "",
            "company_logo": company.logo_url if company else "",
            "company_industry": company.industry if company else "",
            "match_score": score,
            "matched_skills": [],
            "missing_skills": [],
            "is_saved": is_saved,
            "is_applied": is_applied,
        })

    # Explainable card fields (batch-computed after assembly)
    for item, (job, _score) in zip(results, recommendations):
        breakdown = analyze_match(profile, job, db, cached_skills=profile_skills)
        item["matched_skills"] = breakdown.get("matched_skills", [])[:4]
        item["missing_skills"] = [m["skill"] if isinstance(m, dict) else m
                                  for m in breakdown.get("missing_skill_details", [])[:3]]

    return results
