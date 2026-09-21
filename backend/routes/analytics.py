"""
Application analytics routes — provides aggregated data for the analytics dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from typing import Optional

from database.connection import get_db
from models.models import User, Application, SavedJob, Job, Company, Profile, Skill
from utils.auth import get_current_user
from services.matching_service import analyze_match, score_job

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/skill-gaps")
def get_skill_gaps(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated skill-gap analysis over the user's strong local matches.

    Deterministic and data-driven: scans active local jobs the candidate
    scores >= 60 on, collects their missing skills with importance, and
    estimates impact honestly by RE-SCORING each job as if the user had the
    skill (no invented numbers). Sorted by (importance, impact).
    """

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"gaps": [], "jobs_analyzed": 0, "strong_matches": 0}

    profile_skills = [s.name for s in profile.skills]
    jobs = db.query(Job).filter(Job.is_active == True).all()

    # Aggregate missing skills across strong matches
    gap_jobs: dict = {}          # skill -> {count, critical_count, jobs, total_gain, considered}
    strong = 0
    analyzed = 0

    for job in jobs:
        breakdown = analyze_match(profile, job, db, cached_skills=profile_skills)
        overall = breakdown.get("overall", 0)
        if overall < 30:
            continue
        analyzed += 1
        if overall < 60:
            continue
        strong += 1

        for m in breakdown.get("missing_skill_details", []):
            skill = m["skill"]
            importance = m.get("importance", "nice_to_have")
            entry = gap_jobs.setdefault(
                skill,
                {"skill": skill, "critical_count": 0, "job_count": 0, "impact_sum": 0.0, "impact_n": 0},
            )
            entry["job_count"] += 1
            if importance == "critical":
                entry["critical_count"] += 1

            # Honest impact: re-score this job as if the user had the skill.
            patched = profile_skills + [skill]
            new_score = score_job(profile, job, db, cached_skills=patched)
            gain = max(0.0, new_score - overall)
            entry["impact_sum"] += gain
            entry["impact_n"] += 1

    gaps = []
    for entry in gap_jobs.values():
        gaps.append({
            "skill": entry["skill"],
            "jobs_missing": entry["job_count"],
            "critical_jobs": entry["critical_count"],
            "avg_score_gain": round(entry["impact_sum"] / entry["impact_n"], 1) if entry["impact_n"] else 0.0,
            "importance": "critical" if entry["critical_count"] > entry["job_count"] / 2 else "nice_to_have",
        })

    # Sort: critical first, then by job count (breadth of opportunity), then impact
    gaps.sort(key=lambda g: (
        0 if g["importance"] == "critical" else 1,
        -g["jobs_missing"],
        -g["avg_score_gain"],
    ))

    return {
        "gaps": gaps[:12],
        "jobs_analyzed": analyzed,
        "strong_matches": strong,
    }


@router.get("/career-roadmap")
def get_career_roadmap(
    role: str = Query("", max_length=100, description="Target role; defaults to profile title/first preferred role"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Career roadmap for a target role, derived from REAL job listings.

    Readiness = average match score across the target role's active jobs.
    Each skill to learn shows how many target-role jobs require it and the
    average readiness gain from having it (computed by re-scoring, not
    invented). No AI, no generic advice — pure data the user can act on.
    """
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"target_role": role, "has_profile": False, "steps": []}

    # Priority: explicit ?role= > profile.target_role > profile.title > first preferred role
    target = (role or profile.target_role or profile.title or "").strip()
    if not target:
        try:
            import json as _json
            preferred = _json.loads(profile.preferred_roles) if profile.preferred_roles else []
        except Exception:
            preferred = []
        target = preferred[0] if preferred else ""

    if not target:
        return {
            "target_role": "",
            "has_profile": True,
            "message": "Set a target role in your profile to build a roadmap.",
            "readiness": None,
            "steps": [],
        }

    target_lower = target.lower()
    profile_skills = [s.name for s in profile.skills]
    jobs = db.query(Job).filter(Job.is_active == True).all()

    target_jobs = []
    for job in jobs:
        title_l = (job.title or "").lower()
        if target_lower in title_l:
            target_jobs.append(job)

    if not target_jobs:
        return {
            "target_role": target,
            "has_profile": True,
            "message": f"No active {target} jobs in the database yet — check back as listings refresh.",
            "readiness": None,
            "matching_jobs": 0,
            "steps": [],
        }

    from services.matching_service import score_job, analyze_match

    readiness_sum = 0.0
    gap_data: dict = {}
    for job in target_jobs:
        base = score_job(profile, job, db, cached_skills=profile_skills)
        readiness_sum += base
        breakdown = analyze_match(profile, job, db, cached_skills=profile_skills)
        for m in breakdown.get("missing_skill_details", []):
            skill = m["skill"]
            entry = gap_data.setdefault(skill, {"jobs_missing": 0, "gain_sum": 0.0, "gain_n": 0})
            entry["jobs_missing"] += 1
            patched = profile_skills + [skill]
            gain = max(0.0, score_job(profile, job, db, cached_skills=patched) - base)
            entry["gain_sum"] += gain
            entry["gain_n"] += 1

    readiness = round(readiness_sum / len(target_jobs), 1)

    steps = []
    for skill, e in gap_data.items():
        steps.append({
            "skill": skill,
            "jobs_missing": e["jobs_missing"],
            "avg_readiness_gain": round(e["gain_sum"] / e["gain_n"], 1) if e["gain_n"] else 0.0,
            "priority": round(e["jobs_missing"] / len(target_jobs) * 100),
        })
    steps.sort(key=lambda s: (-s["jobs_missing"], -s["avg_readiness_gain"]))

    return {
        "target_role": target,
        "has_profile": True,
        "readiness": readiness,
        "matching_jobs": len(target_jobs),
        "current_skills": profile_skills,
        "steps": steps[:8],
    }


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

    Note: summary stats are lifetime by design; `days` scopes the trend chart.
    """
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


# ════════════════════════════════════════════════════════════════════
# Activity feed — "What changed?" (dashboard question #4)
# Cursor-based: frontend passes ?since=<ISO date> of its last visit.
# ════════════════════════════════════════════════════════════════════

@router.get("/activity")
def get_activity_feed(
    since: Optional[str] = Query(None, max_length=40, description="ISO timestamp of last visit"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Everything new for this user since `since`: application events
    (status changes, email detections, applies), plus new strong matches.
    Ordered newest-first. `since` is clamped to 30 days back max."""
    from models.email_models import ApplicationEvent

    cutoff = None
    if since:
        try:
            cutoff = datetime.fromisoformat(since.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            cutoff = None
    if cutoff is None or cutoff < datetime.utcnow() - timedelta(days=30):
        # No cursor or stale cursor → default to last 7 days (bounded feed)
        cutoff = datetime.utcnow() - timedelta(days=7)

    events = []

    # 1. Application events (applies, status changes, email detections)
    app_events = db.query(ApplicationEvent).filter(
        ApplicationEvent.user_id == user.id,
        ApplicationEvent.created_at >= cutoff,
    ).order_by(ApplicationEvent.created_at.desc()).limit(limit).all()

    app_ids = {e.application_id for e in app_events}
    apps = db.query(Application).filter(Application.id.in_(app_ids)).all() if app_ids else []
    job_ids = {a.job_id for a in apps}
    jobs = db.query(Job).filter(Job.id.in_(job_ids)).all() if job_ids else []
    company_ids = {j.company_id for j in jobs if j.company_id}
    companies = db.query(Company).filter(Company.id.in_(company_ids)).all() if company_ids else []
    job_map = {j.id: j for j in jobs}
    app_map = {a.id: a for a in apps}
    company_map = {c.id: c for c in companies}

    for e in app_events:
        app = app_map.get(e.application_id)
        job = job_map.get(app.job_id) if app else None
        company = company_map.get(job.company_id) if job and job.company_id else None
        kind = e.event_type  # applied | status_change | email_received
        icon = {
            "applied": "applied",
            "status_change": "status",
            "email_received": "email",
        }.get(kind, "info")
        events.append({
            "id": f"ev-{e.id}",
            "type": icon,
            "title": e.title or kind.replace("_", " ").title(),
            "description": e.description or "",
            "detail": e.new_value or "",
            "job_title": job.title if job else "",
            "company_name": company.name if company else "",
            "job_id": job.id if job else None,
            "created_at": e.created_at.isoformat(),
        })

    # 2. New strong matches (score >= 60) — re-scored at read time so the
    #    feed reflects the profile's CURRENT skills, not stale scores.
    try:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if profile and profile.skills:
            profile_skills = [s.name for s in profile.skills]
            candidate_jobs = db.query(Job).filter(Job.is_active == True).order_by(
                Job.posted_at.desc().nullslast()
            ).limit(80).all()
            for job in candidate_jobs:
                if not job.posted_at or job.posted_at < cutoff:
                    continue
                if not job.title:
                    continue
                score = score_job(profile, job, db, cached_skills=profile_skills)
                if score >= 60:
                    events.append({
                        "id": f"job-{job.id}",
                        "type": "match",
                        "title": f"New {int(score)}% match",
                        "description": "",
                        "detail": f"{score:.0f}%",
                        "job_title": job.title,
                        "company_name": "",
                        "job_id": job.id,
                        "created_at": job.posted_at.isoformat(),
                        "score": score,
                    })
    except Exception:
        # Matching failure must never break the feed — events so far still return
        pass

    # Merge by created_at desc, trim to limit
    events.sort(key=lambda x: x["created_at"], reverse=True)
    events = events[:limit]

    return {
        "events": events,
        "cutoff": cutoff.isoformat(),
        "count": len(events),
    }


# ═════════════════════════════════════════════ `since` cursor updates

@router.post("/activity/seen")
def mark_activity_seen(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark "now" as the user's last-seen cursor (server-side, cross-device)."""
    user.last_seen_at = datetime.utcnow()
    db.commit()
    return {"message": "ok"}


# ════════════════════════════════════════════════════════════════════
# Per-resume performance (spec §21): which resume version performs best?
# Descriptive statistics only — never claims causality.
# ════════════════════════════════════════════════════════════════════

@router.get("/resume-performance")
def get_resume_performance(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Applications + outcomes grouped by the resume used. Small-sample
    caveat is included so the UI can label honestly."""
    from models.models import Resume

    rows = db.query(
        Application.resume_id,
        func.count(Application.id).label("total"),
        func.sum(case((Application.status.in_(["screening", "interview", "offer"]), 1), else_=0)).label("responses"),
        func.sum(case((Application.status.in_(["interview", "offer"]), 1), else_=0)).label("interviews"),
        func.sum(case((Application.status == "offer", 1), else_=0)).label("offers"),
    ).filter(
        Application.user_id == user.id,
        Application.resume_id.isnot(None),
    ).group_by(Application.resume_id).all()

    resume_ids = [r[0] for r in rows]
    resumes = db.query(Resume).filter(Resume.id.in_(resume_ids)).all() if resume_ids else []
    resume_map = {r.id: r for r in resumes}

    versions = []
    for r in rows:
        resume = resume_map.get(r.resume_id)
        total = r.total or 0
        responses = r.responses or 0
        interviews = r.interviews or 0
        offers = r.offers or 0
        versions.append({
            "resume_id": r.resume_id,
            "filename": resume.filename if resume else "(deleted)",
            "uploaded_at": resume.uploaded_at.isoformat() if resume and resume.uploaded_at else None,
            "applications": total,
            "responses": responses,
            "interviews": interviews,
            "offers": offers,
            "response_rate": round(responses / total * 100, 1) if total else 0.0,
            "interview_rate": round(interviews / total * 100, 1) if total else 0.0,
        })

    # Sort by application count desc (most-used resume first)
    versions.sort(key=lambda v: v["applications"], reverse=True)

    unattributed = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id,
        Application.resume_id.is_(None),
    ).scalar() or 0

    return {
        "versions": versions,
        "unattributed": unattributed,
        "sample_caveat": "Descriptive only — differences may reflect job mix, not resume quality.",
    }
