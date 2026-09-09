"""
Cover Letter Generator — AI-powered cover letters tailored to specific jobs.
Uses Nemotron with compact prompts for token efficiency.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.connection import get_db
from models.models import User, Profile, Skill, Job, Company, Experience
from utils.auth import get_current_user

router = APIRouter(prefix="/api/cover-letter", tags=["cover-letter"])


class CoverLetterRequest(BaseModel):
    job_id: int
    tone: str = "professional"  # professional, enthusiastic, casual
    length: str = "medium"  # short, medium, long


def _build_job_context(job, company, profile, skills, experiences):
    """Build minimal context string for the AI (~200 tokens)."""
    skill_names = ", ".join([s.name for s in skills[:10]]) or "none"
    exp_lines = []
    for e in experiences[:3]:
        exp_lines.append(f"{e.title} at {e.company} ({e.start_date}-{e.end_date or 'present'})")
    exp_str = "; ".join(exp_lines) or "no experience listed"

    return (
        f"JOB: {job.title} at {company.name if company else '?'}\n"
        f"Location: {job.location}\n"
        f"Requirements: {job.requirements[:300] if job.requirements else 'not specified'}\n"
        f"---\n"
        f"CANDIDATE: {profile.title or '?'}\n"
        f"Skills: {skill_names}\n"
        f"Experience: {exp_str}\n"
        f"Bio: {(profile.bio or '')[:200]}"
    )


LENGTH_INSTRUCTIONS = {
    "short": "150-200 words, 3 paragraphs",
    "medium": "250-350 words, 4 paragraphs",
    "long": "400-500 words, 5 paragraphs",
}

TONE_INSTRUCTIONS = {
    "professional": "Formal, confident, corporate",
    "enthusiastic": "Energetic, passionate, eager",
    "casual": "Conversational, friendly, relaxed",
}


@router.post("/generate")
async def generate_cover_letter(
    data: CoverLetterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a tailored cover letter for a specific job."""
    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    experiences = db.query(Experience).filter(Experience.profile_id == profile.id).all()

    ctx = _build_job_context(job, company, profile, skills, experiences)

    length_inst = LENGTH_INSTRUCTIONS.get(data.length, LENGTH_INSTRUCTIONS["medium"])
    tone_inst = TONE_INSTRUCTIONS.get(data.tone, TONE_INSTRUCTIONS["professional"])

    system = (
        f"You are a cover letter writer. Write a {data.tone} cover letter.\n"
        f"Length: {length_inst}. Tone: {tone_inst}.\n"
        f"Format: greeting, 2-3 body paragraphs, closing. Use the candidate's specific skills and experience.\n"
        f"Reference the actual company and role. No generic phrases."
    )

    prompt = f"Write a cover letter for this job application:\n\n{ctx}"

    try:
        from services.ai_provider import call_ai
        result = await call_ai(prompt, system, provider="nemotron", max_tokens=800)
        if result:
            return {
                "letter": result,
                "job_title": job.title,
                "company": company.name if company else "",
                "tone": data.tone,
                "length": data.length,
            }
    except Exception as e:
        logging.getLogger("rolio.cover_letter").error("AI error: %s", str(e)[:200])

    # Fallback
    return {
        "letter": _fallback_letter(job, company, profile, skills, data.tone),
        "job_title": job.title,
        "company": company.name if company else "",
        "tone": data.tone,
        "length": data.length,
    }


@router.post("/generate/stream")
async def generate_cover_letter_stream(
    data: CoverLetterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Streaming cover letter generation — yields tokens via NDJSON."""
    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    experiences = db.query(Experience).filter(Experience.profile_id == profile.id).all()

    ctx = _build_job_context(job, company, profile, skills, experiences)

    length_inst = LENGTH_INSTRUCTIONS.get(data.length, LENGTH_INSTRUCTIONS["medium"])
    tone_inst = TONE_INSTRUCTIONS.get(data.tone, TONE_INSTRUCTIONS["professional"])

    system = (
        f"You are a cover letter writer. Write a {data.tone} cover letter.\n"
        f"Length: {length_inst}. Tone: {tone_inst}.\n"
        f"Format: greeting, 2-3 body paragraphs, closing. Use the candidate's specific skills and experience.\n"
        f"Reference the actual company and role. No generic phrases."
    )

    prompt = f"Write a cover letter for this job application:\n\n{ctx}"

    async def generate():
        import json as _json
        full_response = []
        try:
            from services.ai_stream import stream_ai
            async for token in stream_ai(prompt, system, user_id=user.id):
                full_response.append(token)
                yield _json.dumps({"type": "token", "token": token}) + "\n"

            yield _json.dumps({
                "type": "done",
                "letter": "".join(full_response),
                "job_title": job.title,
                "company": company.name if company else "",
                "tone": data.tone,
                "length": data.length,
            }) + "\n"
        except Exception as e:
            logging.getLogger("rolio.cover_letter").error("Stream error: %s", str(e)[:200])
            fallback = _fallback_letter(job, company, profile, skills, data.tone)
            yield _json.dumps({
                "type": "done",
                "letter": fallback,
                "job_title": job.title,
                "company": company.name if company else "",
                "tone": data.tone,
                "length": data.length,
            }) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


def _fallback_letter(job, company, profile, skills, tone):
    company_name = company.name if company else "your team"
    skill_list = ", ".join([s.name for s in skills[:5]]) or "my relevant skills"
    title = profile.title or "professional"

    if tone == "enthusiastic":
        opener = f"I'm thrilled to apply for the {job.title} position at {company_name}. This opportunity excites me because it aligns perfectly with my passion and experience as a {title}."
    elif tone == "casual":
        opener = f"Hi! I'm reaching out about the {job.title} role at {company_name}. It looks like a great fit for my background as a {title}."
    else:
        opener = f"I am writing to express my interest in the {job.title} position at {company_name}. With my experience as a {title}, I believe I am well-suited for this role."

    return (
        f"{opener}\n\n"
        f"My experience in {skill_list} has prepared me to contribute meaningfully to your team. "
        f"I am confident that my skills and dedication would make me a valuable addition to {company_name}.\n\n"
        f"I would welcome the opportunity to discuss how my background aligns with your needs. "
        f"Thank you for considering my application.\n\n"
        f"Best regards,\n{user_name(profile)}"
    )


def user_name(profile):
    return profile.user.name if hasattr(profile, 'user') and profile.user else "Applicant"
