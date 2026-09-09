"""
Kanban board endpoint — groups applications by pipeline stage
for drag-and-drop status management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.connection import get_db
from models.models import Application, Job, Company, User
from utils.auth import get_current_user

router = APIRouter(prefix="/api/kanban", tags=["kanban"])


PIPELINE_STAGES = ["saved", "applied", "screening", "interview", "offer", "rejected"]


@router.get("")
def get_kanban_board(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all applications grouped by pipeline stage for kanban view."""
    apps = db.query(Application).filter(Application.user_id == user.id).all()

    columns = {stage: [] for stage in PIPELINE_STAGES}

    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        company = db.query(Company).filter(Company.id == job.company_id).first() if job else None

        card = {
            "id": app.id,
            "job_id": app.job_id,
            "status": app.status,
            "notes": app.notes or "",
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "interview_date": app.interview_date.isoformat() if app.interview_date else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "job_title": job.title if job else "Unknown Job",
            "company_name": company.name if company else "Unknown Company",
            "company_logo": company.logo_url if company else "",
            "location": job.location if job else "",
            "salary_min": job.salary_min if job else 0,
            "salary_max": job.salary_max if job else 0,
            "match_score": app.match_score or 0,
        }

        status = app.status if app.status in PIPELINE_STAGES else "saved"
        columns[status].append(card)

    # Sort each column by date (newest first)
    for stage in columns:
        columns[stage].sort(
            key=lambda c: c.get("applied_at") or "1970-01-01",
            reverse=True,
        )

    # Pipeline stats
    stats = {stage: len(columns[stage]) for stage in PIPELINE_STAGES}

    return {
        "columns": columns,
        "stats": stats,
        "stages": PIPELINE_STAGES,
        "total": len(apps),
    }


class MoveCardRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    interview_date: Optional[str] = None


@router.put("/{app_id}/move")
def move_card(
    app_id: int,
    data: MoveCardRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move an application to a different pipeline stage."""
    if data.status not in PIPELINE_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = app.status
    app.status = data.status
    app.updated_at = datetime.utcnow()

    if data.notes is not None:
        app.notes = data.notes
    if data.interview_date:
        app.interview_date = datetime.fromisoformat(data.interview_date)

    db.commit()

    return {
        "message": f"Moved from {old_status} to {data.status}",
        "id": app.id,
        "status": app.status,
    }
