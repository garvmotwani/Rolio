import logging
import sys
import uuid
from datetime import datetime
from contextvars import ContextVar

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from config import (
    ENV_NAME, IS_PRODUCTION, FRONTEND_ORIGINS, BACKEND_PUBLIC_ORIGIN,
    UPLOAD_DIR, MAX_UPLOAD_SIZE_BYTES, FORCE_HTTPS, TRUSTED_PROXIES,
)
from database.connection import engine, Base, get_db, get_redis
from models.models import (
    User, Profile, Skill, Company, Job, SavedJob, Application, Notification,
)
from models.session import RefreshSession
from routes import (
    auth, users, jobs, applications, recommendations, resumes, ai, gmail,
    ai_chat, resume_builder, jsearch, unified_search, kanban,
    cover_letter, interview_prep, salary_analytics, export, analytics,
    google_auth,
)
from utils.auth import get_current_user
from seed import seed_database

# ─── Structured Logging ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("rolio")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# ─── Application ─────────────────────────────────────────────
app = FastAPI(
    title="Rolio API",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url=None,
)


# ─── Middleware ───────────────────────────────────────────────
def _client_ip(request: Request) -> str:
    """Best-effort client IP (proxy headers are trusted via ProxyHeadersMiddleware)."""
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def force_https_middleware(request: Request, call_next):
    """Redirect plain-HTTP requests to HTTPS in production.

    Only honours X-Forwarded-Proto from trusted proxies (uvicorn's
    ProxyHeadersMiddleware rewrites request.url.scheme accordingly).
    Health check stays on HTTP so load-balancer probes over plain HTTP
    don't get 307s.
    """
    if (
        FORCE_HTTPS
        and request.url.scheme == "http"
        and not request.url.path.startswith("/api/health")
    ):
        https_url = str(request.url.replace(scheme="https"))
        return RedirectResponse(https_url, status_code=308)  # permanent, preserves method
    return await call_next(request)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self' https://fonts.gstatic.com",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    if "server" in response.headers:
        del response.headers["server"]
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)

# Honour X-Forwarded-Proto / X-Forwarded-For only from trusted proxies, so
# request.url.scheme reflects the outer TLS scheme and the HTTPS redirect and
# rate limiting see the real client. Uvicorn also applies its own
# ProxyHeadersMiddleware at the server layer; passing --forwarded-allow-ips
# (or FORWARDED_ALLOW_IPS env) there keeps them consistent. Inside ASGI we
# use uvicorn's middleware directly so the app behaves the same under any
# ASGI server. With no TRUSTED_PROXIES configured nothing is trusted and
# direct connection info is used as-is.
if TRUSTED_PROXIES:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    if TRUSTED_PROXIES == ["*"]:
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    else:
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=TRUSTED_PROXIES)

# Compress large JSON responses (job lists, analytics)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    detail = "Internal server error" if IS_PRODUCTION else str(exc)
    return JSONResponse(status_code=500, content={"detail": detail})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_SIZE_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB."},
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
    return await call_next(request)


# ─── Routers ─────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(recommendations.router)
app.include_router(resumes.router)
app.include_router(ai.router)
app.include_router(gmail.router)
app.include_router(ai_chat.router)
app.include_router(resume_builder.router)
app.include_router(jsearch.router)
app.include_router(unified_search.router)
app.include_router(kanban.router)
app.include_router(cover_letter.router)
app.include_router(interview_prep.router)
app.include_router(salary_analytics.router)
app.include_router(export.router)
app.include_router(analytics.router)


# ─── Startup ─────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    logger.info(f"Starting Rolio API in {ENV_NAME} mode")
    if IS_PRODUCTION:
        logger.info("Production mode: skipping create_all() and seed. Use 'alembic upgrade head'.")
    else:
        Base.metadata.create_all(bind=engine)
        seed_database()
    import os
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except OSError as e:
        # config.py already guarantees a writable UPLOAD_DIR; this is a
        # defensive guard so a filesystem oddity can never kill startup.
        logger.warning("Could not create upload dir %r: %s", UPLOAD_DIR, e)
    try:
        redis = get_redis()
        if redis:
            redis.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Using in-memory rate limiting.")


# ─── Root ────────────────────────────────────────────────────
@app.get("/")
def root():
    """Friendly index so visiting the API root doesn't look broken."""
    return {
        "name": "Rolio API",
        "version": "1.0.0",
        "status": "ok",
        "health": "/api/health",
        "docs": "/docs" if not IS_PRODUCTION else "disabled in production",
    }


# ─── Health Check ────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    try:
        from database.connection import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    try:
        redis = get_redis()
        if redis:
            redis.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unavailable"

    overall = "ok" if db_status == "healthy" else "degraded"
    return {
        "status": overall,
        "environment": ENV_NAME,
        "version": "1.0.0",
        "database": db_status,
        "redis": redis_status,
    }


# ─── Dashboard (N+1 optimized) ──────────────────────────────
@app.get("/api/dashboard")
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    applications_list = db.query(Application).filter(Application.user_id == user.id).all()
    saved = db.query(SavedJob).filter(SavedJob.user_id == user.id).all()

    # Pre-compute saved/applied sets for O(1) lookup
    saved_job_ids = {s.job_id for s in saved}
    applied_job_ids = {a.job_id for a in applications_list}

    from services.matching_service import get_recommendations
    strong_matches = 0
    recommended = []

    # Batch-load all companies needed
    if profile:
        recs = get_recommendations(profile, db, limit=6)
        strong_matches = len([r for r in recs if r[1] >= 70])

        # Collect all company IDs needed
        rec_job_ids = [job.id for job, _ in recs]
        rec_company_ids = set()
        for job, _ in recs:
            if job.company_id:
                rec_company_ids.add(job.company_id)

        # Also collect company IDs from recent apps
        recent_app_job_ids = [a.job_id for a in applications_list[:5]]
        for jid in recent_app_job_ids:
            job = db.query(Job).filter(Job.id == jid).first()
            if job and job.company_id:
                rec_company_ids.add(job.company_id)

        # Batch-load all companies in one query
        companies = db.query(Company).filter(Company.id.in_(rec_company_ids)).all() if rec_company_ids else []
        company_map = {c.id: c for c in companies}

        for job, score in recs:
            company = company_map.get(job.company_id)
            recommended.append({
                "id": job.id, "company_id": job.company_id, "title": job.title,
                "description": job.description, "requirements": job.requirements,
                "responsibilities": job.responsibilities,
                "preferred_qualifications": job.preferred_qualifications,
                "skills_required": job.skills_required, "skills_preferred": job.skills_preferred,
                "location": job.location, "work_type": job.work_type,
                "salary_min": job.salary_min, "salary_max": job.salary_max,
                "experience_level": job.experience_level, "employment_type": job.employment_type,
                "application_url": job.application_url, "is_active": job.is_active,
                "posted_at": job.posted_at.isoformat(),
                "company_name": company.name if company else "",
                "company_logo": company.logo_url if company else "",
                "company_industry": company.industry if company else "",
                "match_score": score,
                "is_saved": job.id in saved_job_ids,
                "is_applied": job.id in applied_job_ids,
            })

    interview_count = len([a for a in applications_list if a.status == "interview"])

    # Batch-load jobs for recent apps
    recent_app_job_ids = [a.job_id for a in applications_list[:5]]
    recent_jobs = db.query(Job).filter(Job.id.in_(recent_app_job_ids)).all() if recent_app_job_ids else []
    recent_job_map = {j.id: j for j in recent_jobs}

    recent_apps = []
    for app_item in applications_list[:5]:
        job = recent_job_map.get(app_item.job_id)
        company = company_map.get(job.company_id) if job and job.company_id in company_map else (
            db.query(Company).filter(Company.id == job.company_id).first() if job and job.company_id else None
        )
        recent_apps.append({
            "id": app_item.id, "user_id": app_item.user_id, "job_id": app_item.job_id,
            "status": app_item.status, "notes": app_item.notes,
            "applied_at": app_item.applied_at.isoformat(),
            "interview_date": app_item.interview_date.isoformat() if app_item.interview_date else None,
            "external_url": app_item.external_url, "match_score": app_item.match_score,
            "job_title": job.title if job else "",
            "company_name": company.name if company else "",
            "company_logo": company.logo_url if company else "",
            "job_location": job.location if job else "",
            "job_work_type": job.work_type if job else "",
            "job_salary_min": job.salary_min if job else 0,
            "job_salary_max": job.salary_max if job else 0,
            "skills_required": job.skills_required if job else "",
        })

    tips = []
    if profile:
        if len(skills) < 5:
            tips.append("Add more skills to improve your match rate")
        if not profile.title:
            tips.append("Add a professional title to your profile")
        if not profile.preferred_roles:
            tips.append("Specify your preferred roles for better recommendations")
        if not profile.bio:
            tips.append("Add a bio to make your profile stand out")
        if profile.completeness_score < 60:
            tips.append("Complete more profile sections for stronger matches")
        if len(applications_list) == 0:
            tips.append("Start applying to jobs you're matched with")
        if strong_matches > 0 and len(applications_list) < 3:
            tips.append(f"You have {strong_matches} strong matches waiting — apply today!")

    unread_notifications = db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False
    ).count()

    hour = datetime.utcnow().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return {
        "greeting": greeting, "name": user.name,
        "strong_matches": strong_matches, "total_applications": len(applications_list),
        "interviews": interview_count, "saved_jobs": len(saved),
        "profile_strength": profile.completeness_score if profile else 0,
        "recommended_jobs": recommended, "recent_applications": recent_apps,
        "profile_tips": tips, "unread_notifications": unread_notifications,
    }


@app.get("/api/notifications")
def get_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return [
        {
            "id": n.id, "title": n.title, "message": n.message,
            "type": n.type, "is_read": n.is_read, "link": n.link,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@app.put("/api/notifications/read-all")
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@app.get("/api/stats")
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from services.matching_service import get_recommendations
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    total_jobs = db.query(Job).filter(Job.is_active == True).count()
    total_companies = db.query(Company).count()
    recs_count = 0
    if profile:
        recs = get_recommendations(profile, db, limit=100)
        recs_count = len(recs)
    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "personalized_matches": recs_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
