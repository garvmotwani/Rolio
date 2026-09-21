"""
Export endpoints — CSV download for applications and saved jobs.
"""

import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import User, Application, SavedJob, Job, Company
from utils.auth import get_current_user

router = APIRouter(prefix="/api/export", tags=["export"])


def _safe_str(val) -> str:
    """Convert a value to a clean string for CSV."""
    if val is None:
        return ""
    return str(val).replace("\n", " ").replace("\r", "")


@router.get("/applications")
def export_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all applications as CSV."""
    applications = (
        db.query(Application)
        .filter(Application.user_id == user.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Job Title", "Company", "Status", "Match Score",
        "Applied Date", "Interview Date", "Location", "Work Type",
        "Notes", "External URL",
    ])

    for app in applications:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        company = db.query(Company).filter(Company.id == job.company_id).first() if job else None
        writer.writerow([
            _safe_str(job.title) if job else "Unknown",
            _safe_str(company.name) if company else "Unknown",
            _safe_str(app.status),
            _safe_str(app.match_score),
            _safe_str(app.applied_at.date() if app.applied_at else ""),
            _safe_str(app.interview_date.date() if app.interview_date else ""),
            _safe_str(job.location) if job else "",
            _safe_str(job.work_type) if job else "",
            _safe_str(app.notes),
            _safe_str(app.external_url),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=rolio_applications.csv",
        },
    )


@router.get("/saved-jobs")
def export_saved_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all saved jobs as CSV."""
    saved = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id)
        .order_by(SavedJob.saved_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Job Title", "Company", "Location", "Work Type",
        "Salary Range", "Experience Level", "Employment Type",
        "Skills Required", "Posted Date", "Application URL",
    ])

    for s in saved:
        job = db.query(Job).filter(Job.id == s.job_id).first()
        company = db.query(Company).filter(Company.id == job.company_id).first() if job else None
        salary = ""
        if job and job.salary_min and job.salary_max:
            salary = f"${job.salary_min:,.0f} - ${job.salary_max:,.0f}"
        elif job and job.salary_min:
            salary = f"${job.salary_min:,.0f}+"

        writer.writerow([
            _safe_str(job.title) if job else "Unknown",
            _safe_str(company.name) if company else "Unknown",
            _safe_str(job.location) if job else "",
            _safe_str(job.work_type) if job else "",
            salary,
            _safe_str(job.experience_level) if job else "",
            _safe_str(job.employment_type) if job else "",
            _safe_str(job.skills_required) if job else "",
            _safe_str(job.posted_at.date() if job and job.posted_at else ""),
            _safe_str(job.application_url) if job else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=rolio_saved_jobs.csv",
        },
    )
