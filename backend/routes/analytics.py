"""
Application analytics routes — provides aggregated data for the analytics dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract
from datetime import datetime, timedelta
from typing import Optional

from database.connection import get_db
from models.models import User, Application, SavedJob, Job, Company, Profile, Skill
from utils.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def get_dashboard_analytics(
    days: int = Query(90, ge=7, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full analytics dashboard data for the current user.
    Returns: summary stats, status distribution, match score stats,
    applications over time, top skills, and recent activity.
    """
    since = datetime.utcnow() - timedelta(days=days)

    # ── Summary Stats ──
    total_applications = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id
    ).scalar() or 0

    active_applications = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id,
        Application.status.in_(["applied", "screening", "interview"])
    ).scalar() or 0

    offers = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id,
        Application.status == "offer"
    ).scalar() or 0

    rejected = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id,
        Application.status == "rejected"
    ).scalar() or 0

    saved_count = db.query(func.count(SavedJob.id)).filter(
        SavedJob.user_id == user.id
    ).scalar() or 0

    # Response rate (applied / total viewed — use saved + applied as proxy)
    total_viewed = saved_count + total_applications
    response_rate = round(
        (active_applications + offers) / max(total_viewed, 1) * 100, 1
    )

    interview_rate = round(
        active_applications / max(total_applications, 1) * 100, 1
    ) if total_applications > 0 else 0

    offer_rate = round(
        offers / max(total_applications, 1) * 100, 1
    ) if total_applications > 0 else 0

    # ── Status Distribution ──
    status_rows = db.query(
        Application.status,
        func.count(Application.id)
    ).filter(
        Application.user_id == user.id
    ).group_by(Application.status).all()

    status_distribution = {row[0]: row[1] for row in status_rows}

    # ── Match Score Stats ──
    score_stats = db.query(
        func.avg(Application.match_score),
        func.min(Application.match_score),
        func.max(Application.match_score),
    ).filter(
        Application.user_id == user.id,
        Application.match_score > 0
    ).first()

    avg_score = round(score_stats[0] or 0, 1)
    min_score = round(score_stats[1] or 0, 1)
    max_score = round(score_stats[2] or 0, 1)

    # Score distribution buckets
    score_buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    apps_with_scores = db.query(Application.match_score).filter(
        Application.user_id == user.id,
        Application.match_score > 0
    ).all()

    for (score,) in apps_with_scores:
        if score < 20:
            score_buckets["0-20"] += 1
        elif score < 40:
            score_buckets["20-40"] += 1
        elif score < 60:
            score_buckets["40-60"] += 1
        elif score < 80:
            score_buckets["60-80"] += 1
        else:
            score_buckets["80-100"] += 1

    # ── Applications Over Time (weekly buckets) ──
    weekly_apps = []
    for i in range(min(days // 7, 13), 0, -1):
        week_start = datetime.utcnow() - timedelta(weeks=i)
        week_end = datetime.utcnow() - timedelta(weeks=i - 1)
        count = db.query(func.count(Application.id)).filter(
            Application.user_id == user.id,
            Application.applied_at >= week_start,
            Application.applied_at < week_end
        ).scalar() or 0
        weekly_apps.append({
            "week": week_start.strftime("%b %d"),
            "count": count
        })

    # ── Top Skills from Applications ──
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_skills = []
    if profile:
        skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
        profile_skills = [{"name": s.name, "level": s.level} for s in skills]

    # ── Company Distribution (top companies applied to) ──
    company_apps = db.query(
        Company.name,
        func.count(Application.id).label("count")
    ).join(
        Job, Application.job_id == Job.id
    ).join(
        Company, Job.company_id == Company.id
    ).filter(
        Application.user_id == user.id
    ).group_by(
        Company.name
    ).order_by(
        func.count(Application.id).desc()
    ).limit(10).all()

    company_distribution = [
        {"company": row[0] or "Unknown", "count": row[1]}
        for row in company_apps
    ]

    # ── Recent Activity (last 10 application updates) ──
    recent = db.query(Application).filter(
        Application.user_id == user.id
    ).order_by(Application.updated_at.desc()).limit(10).all()

    # Batch-load jobs and companies to avoid N+1 queries
    recent_job_ids = [app.job_id for app in recent]
    recent_jobs = db.query(Job).filter(Job.id.in_(recent_job_ids)).all() if recent_job_ids else []
    job_map = {j.id: j for j in recent_jobs}
    company_ids = {j.company_id for j in recent_jobs if j.company_id}
    companies = db.query(Company).filter(Company.id.in_(company_ids)).all() if company_ids else []
    company_map = {c.id: c for c in companies}

    recent_activity = []
    for app in recent:
        job = job_map.get(app.job_id)
        company = company_map.get(job.company_id) if job and job.company_id else None
        recent_activity.append({
            "id": app.id,
            "status": app.status,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "job_title": job.title if job else "Unknown",
            "company_name": company.name if company else "Unknown",
        })

    return {
        "summary": {
            "total_applications": total_applications,
            "active_applications": active_applications,
            "offers": offers,
            "rejected": rejected,
            "saved_jobs": saved_count,
            "response_rate": response_rate,
            "interview_rate": interview_rate,
            "offer_rate": offer_rate,
        },
        "status_distribution": status_distribution,
        "match_scores": {
            "average": avg_score,
            "min": min_score,
            "max": max_score,
            "buckets": score_buckets,
        },
        "applications_over_time": weekly_apps,
        "profile_skills": profile_skills,
        "company_distribution": company_distribution,
        "recent_activity": recent_activity,
    }
