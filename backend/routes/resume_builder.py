"""
AI Resume Builder — Nemotron-powered, section-by-section for token efficiency.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json

from database.connection import get_db
from models.models import User, Profile, Skill, Experience, Education
from utils.auth import get_current_user
from utils.ai_rate_limit import ai_rate_limit
from services.ai_provider import call_ai, build_resume_prompt, build_section_prompt

router = APIRouter(prefix="/api/resume-builder", tags=["resume-builder"])


class ResumeRequest(BaseModel):
    job_id: Optional[int] = None


class ResumeSectionRequest(BaseModel):
    section: str  # "summary", "experience", "skills", "education", "full"
    job_id: Optional[int] = None


def _profile_to_dict(profile, skills, experiences, educations, user):
    return {
        "name": user.name,
        "title": profile.title or "",
        "location": profile.location or "",
        "bio": profile.bio or "",
        "skills": [s.name for s in skills],
        # Full description (the AI rewrites it into bullets; truncation made
        # resumes generic). Still capped to keep prompts token-efficient.
        "experience": [
            {"company": e.company, "title": e.title, "description": (e.description or "")[:600],
             "start": e.start_date, "end": e.end_date or "Present"}
            for e in experiences[:5]
        ],
        "education": [
            {"institution": ed.institution, "degree": ed.degree, "field": ed.field_of_study, "gpa": ed.gpa or ""}
            for ed in educations[:3]
        ],
    }


@router.post("/generate")
async def generate_resume(data: ResumeRequest, user: User = Depends(ai_rate_limit), db: Session = Depends(get_db)):
    """Generate complete resume — Nemotron, ~800 tokens total."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    experiences = db.query(Experience).filter(Experience.profile_id == profile.id).all()
    educations = db.query(Education).filter(Education.profile_id == profile.id).all()
    profile_data = _profile_to_dict(profile, skills, experiences, educations, user)

    job_data = None
    if data.job_id:
        from models.models import Job, Company
        job = db.query(Job).filter(Job.id == data.job_id).first()
        if job:
            company = db.query(Company).filter(Company.id == job.company_id).first()
            try:
                job_skills = json.loads(job.skills_required) if job.skills_required else []
            except (json.JSONDecodeError, TypeError):
                job_skills = [s.strip() for s in (job.skills_required or "").split(",")]
            job_data = {"title": job.title, "company": company.name if company else "?", "skills": job_skills}

    prompt = build_resume_prompt(profile_data, job_data)
    result = await call_ai(prompt, "Output JSON only. ATS-friendly. No markdown.", provider="nemotron", max_tokens=900)

    if not result:
        return {"resume": _build_fallback_resume(profile_data, job_data), "tailored_for": job_data["title"] if job_data else None, "provider": "fallback"}

    try:
        resume = json.loads(result)
    except json.JSONDecodeError:
        try:
            start = result.index("{")
            end = result.rindex("}") + 1
            resume = json.loads(result[start:end])
        except (ValueError, json.JSONDecodeError):
            resume = _build_fallback_resume(profile_data, job_data)

    resume = _normalize_resume(resume, profile_data)

    return {"resume": resume, "tailored_for": job_data["title"] if job_data else None, "provider": "nemotron"}


def _normalize_resume(resume: dict, profile_data: dict) -> dict:
    """Coerce any AI JSON shape into the schema the frontend renders."""
    if not isinstance(resume, dict):
        return _build_fallback_resume(profile_data)

    normalized = {
        "summary": str(resume.get("summary") or "").strip(),
        "contact": resume.get("contact") if isinstance(resume.get("contact"), dict) else {},
        "skills": [str(s).strip() for s in (resume.get("skills") or []) if str(s).strip()][:12],
        "experience": [],
        "education": [],
    }

    for e in resume.get("experience") or []:
        if not isinstance(e, dict):
            continue
        bullets = [str(b).strip().lstrip("•- ") for b in (e.get("bullets") or []) if str(b).strip()]
        normalized["experience"].append({
            "title": str(e.get("title") or "").strip(),
            "company": str(e.get("company") or "").strip(),
            "start": str(e.get("start") or "").strip(),
            "end": str(e.get("end") or "Present").strip() or "Present",
            "bullets": bullets[:4],
        })

    for ed in resume.get("education") or []:
        if not isinstance(ed, dict):
            continue
        normalized["education"].append({
            "degree": str(ed.get("degree") or "").strip(),
            "field": str(ed.get("field") or "").strip(),
            "institution": str(ed.get("institution") or ed.get("school") or "").strip(),
            "year": str(ed.get("year") or "").strip(),
        })

    # Never return an empty resume silently
    if not normalized["experience"] and not normalized["summary"]:
        return _build_fallback_resume(profile_data)
    return normalized


@router.post("/section")
async def generate_section(data: ResumeSectionRequest, user: User = Depends(ai_rate_limit), db: Session = Depends(get_db)):
    """Generate single section — saves ~600 tokens vs full resume."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    experiences = db.query(Experience).filter(Experience.profile_id == profile.id).all()
    educations = db.query(Education).filter(Education.profile_id == profile.id).all()
    profile_data = _profile_to_dict(profile, skills, experiences, educations, user)

    job_data = None
    if data.job_id:
        from models.models import Job, Company
        job = db.query(Job).filter(Job.id == data.job_id).first()
        if job:
            company = db.query(Company).filter(Company.id == job.company_id).first()
            try:
                job_skills = json.loads(job.skills_required) if job.skills_required else []
            except (json.JSONDecodeError, TypeError):
                job_skills = [s.strip() for s in (job.skills_required or "").split(",")]
            job_data = {"title": job.title, "company": company.name if company else "?", "skills": job_skills}

    section = data.section.lower()
    if section not in ("summary", "experience", "skills", "education", "full"):
        raise HTTPException(status_code=400, detail=f"Invalid section: {section}")

    if section == "full":
        return await generate_resume(ResumeRequest(job_id=data.job_id), user, db)

    prompt = build_section_prompt(section, profile_data, job_data)
    result = await call_ai(prompt, "JSON only. No markdown.", provider="nemotron", max_tokens=300)

    if not result:
        return {"section": section, "content": {}, "provider": "fallback"}

    try:
        content = json.loads(result)
    except json.JSONDecodeError:
        try:
            start = result.index("{")
            end = result.rindex("}") + 1
            content = json.loads(result[start:end])
        except (ValueError, json.JSONDecodeError):
            content = {"text": result}

    return {"section": section, "content": content, "provider": "nemotron"}


@router.post("/improve")
async def improve_text(text: str, context: str = "resume bullet point", user: User = Depends(ai_rate_limit), db: Session = Depends(get_db)):
    """Improve one bullet — ~60 tokens per call."""
    prompt = (
        f"Improve this {context} to be ATS-friendly:\n"
        f"Original: {text}\n"
        f"Rules: Action verb start, metrics, under 25 words. Output ONLY improved text."
    )
    result = await call_ai(prompt, "", provider="nemotron", max_tokens=60)
    return {"improved": result or text, "original": text}


def _build_fallback_resume(profile, job=None):
    summary_parts = []
    if profile.get("title"): summary_parts.append(profile["title"])
    if profile.get("location"): summary_parts.append(f"based in {profile['location']}")
    if profile.get("skills"): summary_parts.append(f"skilled in {', '.join(profile['skills'][:5])}")
    summary = "Experienced " + " ".join(summary_parts) + "." if summary_parts else "Professional candidate."

    experience = []
    for exp in profile.get("experience", [])[:4]:
        bullets = [b.strip() for b in (exp.get("description") or "").split("\n") if b.strip()][:3]
        if not bullets: bullets = [f"Worked as {exp.get('title', 'Professional')} at {exp.get('company', 'Company')}"]
        experience.append({"company": exp.get("company", ""), "title": exp.get("title", ""), "bullets": bullets})

    skills = profile.get("skills", [])[:15]
    if job and job.get("skills"):
        job_skills = set(s.lower() for s in job["skills"])
        prioritized = [s for s in skills if s.lower() in job_skills]
        remaining = [s for s in skills if s.lower() not in job_skills]
        skills = (prioritized + remaining)[:15]

    return {
        "summary": summary,
        "experience": experience,
        "education": [{"institution": ed.get("institution", ""), "degree": ed.get("degree", ""), "field": ed.get("field", ""), "year": ed.get("year", "")} for ed in profile.get("education", [])],
        "skills": skills,
    }
