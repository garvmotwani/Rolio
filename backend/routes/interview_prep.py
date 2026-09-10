"""
Interview Prep — AI-generated interview flashcards tailored to specific jobs.
Each card has a question, expected answer framework, and difficulty level.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database.connection import get_db
from models.models import User, Profile, Skill, Job, Company
from utils.auth import get_current_user
from utils.ai_rate_limit import ai_rate_limit

logger = logging.getLogger("rolio.prep")

router = APIRouter(prefix="/api/interview-prep", tags=["interview-prep"])


class PrepRequest(BaseModel):
    job_id: int
    category: str = "all"  # all, behavioral, technical, system-design
    count: int = 10


def _build_prep_context(job, company, profile, skills):
    """Minimal context for flashcard generation (~150 tokens)."""
    skill_names = ", ".join([s.name for s in skills[:12]]) or "none"
    return (
        f"ROLE: {job.title} at {company.name if company else '?'}\n"
        f"Skills: {skill_names}\n"
        f"Requirements: {(job.requirements or '')[:400]}\n"
        f"Description: {(job.description or '')[:400]}\n"
        f"CANDIDATE: {profile.title or '?'}"
    )


@router.post("/generate")
async def generate_flashcards(
    data: PrepRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    """Generate interview flashcards for a specific job."""
    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    ctx = _build_prep_context(job, company, profile, skills)

    cat_filter = ""
    if data.category == "behavioral":
        cat_filter = " Only behavioral/STAR-method questions."
    elif data.category == "technical":
        cat_filter = " Only technical/coding/architecture questions."
    elif data.category == "system-design":
        cat_filter = " Only system design and architecture questions."

    system = (
        f"Generate {data.count} interview flashcards for this role.{cat_filter}\n"
        f"Return JSON array: [{{\"question\": \"...\", \"answer\": \"...\", "
        f"\"category\": \"behavioral|technical|system-design\", \"difficulty\": \"easy|medium|hard\"}}]\n"
        f"Questions should be specific to the role. Answers should use STAR format for behavioral, "
        f"concise technical explanations for technical. Max 3 sentences per answer."
    )

    prompt = f"Create interview prep flashcards:\n\n{ctx}"

    try:
        import json
        from services.ai_provider import call_ai
        result = await call_ai(prompt, system, provider="nemotron", max_tokens=1200)
        if result:
            # Try to parse JSON from response
            try:
                # Find JSON array in response
                start = result.find('[')
                end = result.rfind(']') + 1
                if start >= 0 and end > start:
                    cards = json.loads(result[start:end])
                    return {"cards": cards, "job_title": job.title, "company": company.name if company else ""}
            except json.JSONDecodeError:
                pass
            # If parsing fails, return as text
            return {"cards": [], "raw": result, "job_title": job.title, "company": company.name if company else ""}
    except Exception as e:
        logger.error("Interview prep AI error: %s", str(e)[:200])

    # Fallback cards
    return {"cards": _fallback_cards(job, data.category), "job_title": job.title, "company": company.name if company else ""}


@router.post("/generate/stream")
async def generate_flashcards_stream(
    data: PrepRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    """Streaming interview prep — yields cards as JSON lines as they're generated."""
    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
    ctx = _build_prep_context(job, company, profile, skills)

    cat_filter = ""
    if data.category == "behavioral":
        cat_filter = " Only behavioral/STAR-method questions."
    elif data.category == "technical":
        cat_filter = " Only technical/coding/architecture questions."
    elif data.category == "system-design":
        cat_filter = " Only system design and architecture questions."

    system = (
        f"Generate {data.count} interview flashcards for this role.{cat_filter}\n"
        f"Return ONLY a JSON array (no markdown, no code fences): [{{\"question\": \"...\", \"answer\": \"...\", "
        f"\"category\": \"behavioral|technical|system-design\", \"difficulty\": \"easy|medium|hard\"}}]\n"
        f"Questions should be specific to the role. Answers should use STAR format for behavioral, "
        f"concise technical explanations for technical. Max 3 sentences per answer."
    )

    prompt = f"Create interview prep flashcards:\n\n{ctx}"

    async def generate():
        try:
            from services.ai_stream import stream_ai
            full_response = []
            async for token in stream_ai(prompt, system, user_id=user.id):
                full_response.append(token)
                # Stream partial text for real-time display
                yield json.dumps({"type": "token", "token": token}) + "\n"

            # Parse the complete response for flashcards
            full_text = "".join(full_response)
            cards = []
            try:
                start = full_text.find('[')
                end = full_text.rfind(']') + 1
                if start >= 0 and end > start:
                    cards = json.loads(full_text[start:end])
            except json.JSONDecodeError:
                pass

            yield json.dumps({
                "type": "done",
                "cards": cards,
                "job_title": job.title,
                "company": company.name if company else "",
            }) + "\n"
        except Exception as e:
            logger.error("Interview prep stream error: %s", str(e)[:200])
            # Return fallback cards
            yield json.dumps({
                "type": "done",
                "cards": _fallback_cards(job, data.category),
                "job_title": job.title,
                "company": company.name if company else "",
            }) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


def _fallback_cards(job, category):
    """Generic but useful fallback flashcards."""
    cards = [
        {"question": "Tell me about yourself.", "answer": "Structure: Current role → key achievements → why this role. Keep it under 2 minutes.", "category": "behavioral", "difficulty": "easy"},
        {"question": "Why do you want to work at this company?", "answer": "Research their mission, recent projects, and culture. Connect to your own values and career goals.", "category": "behavioral", "difficulty": "easy"},
        {"question": "Describe a challenging project you led.", "answer": "Use STAR: Situation, Task, Action, Result. Quantify your impact with specific numbers.", "category": "behavioral", "difficulty": "medium"},
        {"question": "What are your strengths and weaknesses?", "answer": "Strength: pick one relevant to the role with example. Weakness: genuine but show improvement steps.", "category": "behavioral", "difficulty": "easy"},
        {"question": "Where do you see yourself in 5 years?", "answer": "Show ambition aligned with company growth. Mention specific skills you want to develop.", "category": "behavioral", "difficulty": "easy"},
        {"question": "Tell me about a time you disagreed with a teammate.", "answer": "Focus on resolution, not conflict. Show communication skills and compromise.", "category": "behavioral", "difficulty": "medium"},
        {"question": "How do you handle tight deadlines?", "answer": "Give a specific example. Mention prioritization, communication, and trade-off decisions.", "category": "behavioral", "difficulty": "medium"},
        {"question": "Describe your technical process for solving a complex problem.", "answer": "Break down approach: understand → research → plan → implement → test → iterate.", "category": "technical", "difficulty": "medium"},
        {"question": "How do you ensure code quality?", "answer": "Mention testing strategies, code review, linting, CI/CD, and documentation practices.", "category": "technical", "difficulty": "medium"},
        {"question": "Do you have any questions for us?", "answer": "Ask about team structure, tech stack decisions, growth opportunities, and current challenges.", "category": "behavioral", "difficulty": "easy"},
    ]

    if category != "all":
        cards = [c for c in cards if c["category"] == category]

    return cards[:10]
