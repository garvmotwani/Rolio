from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database.connection import get_db
from models.models import Application, Job, Company, User
from schemas.schemas import ApplicationCreate, ApplicationUpdate
from utils.auth import get_current_user

router = APIRouter(prefix="/api", tags=["applications"])


@router.get("/applications")
def get_applications(
    status: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Application).filter(Application.user_id == user.id)

    if status:
        if status == "all":
            pass
        else:
            q = q.filter(Application.status == status)

    apps = q.order_by(Application.applied_at.desc()).all()
    results = []

    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        company = db.query(Company).filter(Company.id == job.company_id).first() if job else None

        results.append({
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "status": app.status,
            "notes": app.notes,
            "applied_at": app.applied_at.isoformat(),
            "interview_date": app.interview_date.isoformat() if app.interview_date else None,
            "external_url": app.external_url,
            "match_score": app.match_score,
            "job_title": job.title if job else "",
            "company_name": company.name if company else "",
            "company_logo": company.logo_url if company else "",
            "job_location": job.location if job else "",
            "job_work_type": job.work_type if job else "",
            "job_salary_min": job.salary_min if job else 0,
            "job_salary_max": job.salary_max if job else 0,
            "skills_required": job.skills_required if job else "",
        })

    return results


EXTERNAL_JOB_PREFIXES = ("jsearch_", "remotive_", "jobicy_")


@router.post("/applications")
async def create_application(
    data: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── External job: import to DB first (idempotent) ─────
    job_id = data.job_id
    if isinstance(job_id, str) and job_id.startswith(EXTERNAL_JOB_PREFIXES):
        from routes.jobs import _import_external_job
        job_row = await _import_external_job(job_id, db)
        if not job_row:
            raise HTTPException(status_code=404, detail="Job not found")
        data = data.model_copy(update={"job_id": job_row.id})

    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(Application).filter(
        Application.user_id == user.id, Application.job_id == data.job_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this job")

    app = Application(
        user_id=user.id,
        job_id=data.job_id,
        status="applied",
        notes=data.notes,
        external_url=data.external_url,
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {"message": "Application created", "id": app.id}


@router.put("/applications/{app_id}")
def update_application(
    app_id: int,
    data: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if data.status:
        app.status = data.status
    if data.notes is not None:
        app.notes = data.notes
    if data.interview_date:
        app.interview_date = datetime.fromisoformat(data.interview_date)
    if data.external_url is not None:
        app.external_url = data.external_url

    app.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Application updated"}


@router.delete("/applications/{app_id}")
def delete_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(app)
    db.commit()
    return {"message": "Application deleted"}
