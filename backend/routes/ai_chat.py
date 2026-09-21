import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from models.models import User, Profile, Skill, Application, Job, Company
from utils.auth import get_current_user
from utils.ai_rate_limit import ai_rate_limit
from services.matching_service import get_match_breakdown

router = APIRouter(prefix="/api/ai", tags=["ai-chat"])


class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("content")
    @classmethod
    def _bounded_content(cls, v):
        if len(v) > 2000:
            raise ValueError("History message too long (max 2000 characters)")
        return v


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

    # Resource-exhaustion bounds: every char here becomes AI-provider tokens
    # (cost/quota abuse). Prompt builder truncates to [:200] anyway — these
    # caps reject absurd payloads before any processing.
    @field_validator("message")
    @classmethod
    def _bounded_message(cls, v):
        if len(v) > 2000:
            raise ValueError("Message too long (max 2000 characters)")
        return v

    @field_validator("history")
    @classmethod
    def _bounded_history(cls, v):
        if v and len(v) > 20:
            raise ValueError("History too long (max 20 messages)")
        return v


class JobQuestionRequest(BaseModel):
    job_id: int
    question: str  # "why_match" | "missing" | "apply_tips" | "tailor_resume" | "prepare"


# Per-question prompts. Each gets a focused instruction + the shared job/user
# context, so answers are short, specific, and different from each other.
JOB_QUESTIONS = {
    "why_match": (
        "Answer: why is this user a good fit?\n"
        "Structure: one verdict sentence, then 2-3 bullet strengths referencing THEIR skills."
    ),
    "missing": (
        "Answer: what skills/experience is the user missing?\n"
        "Structure: 2-3 bullet gaps, each with a one-line how-to-close-it suggestion."
    ),
    "apply_tips": (
        "Answer: how should they apply to maximize success?\n"
        "Structure: 3 short numbered tips (resume focus, cover-letter angle, timing/follow-up)."
    ),
    "tailor_resume": (
        "Answer: how to tailor their resume for THIS job?\n"
        "Structure: 1 intro line, then per-key-skill bullets saying where to surface it."
    ),
    "prepare": (
        "Answer: what to prepare for interviews for THIS job?\n"
        "Structure: 3 likely technical topics from the job skills, 2 likely behavioral questions, 1 smart question they should ask."
    ),
}


def _job_question_context(job: Job, company, profile, profile_skills, breakdown) -> str:
    """Compact shared context for job Q&A (~90 tokens)."""
    try:
        job_skills = json.loads(job.skills_required) if job.skills_required else []
    except (json.JSONDecodeError, TypeError, ValueError):
        job_skills = [s.strip() for s in (job.skills_required or "").split(",") if s.strip()]
    return (
        f"Job: {job.title} at {company.name if company else '?'} | Level: {job.experience_level or 'mid'}\n"
        f"Job skills: {', '.join(job_skills[:8]) or '?'}\n"
        f"User: {profile.title or '?'}, skills: {', '.join(profile_skills[:10]) or 'none'}\n"
        f"Match: {breakdown['overall']}% | Strong: {', '.join(breakdown.get('strong_matches', [])[:4]) or 'none'} | Missing: {', '.join(breakdown.get('missing_skills', [])[:4]) or 'none'}"
    )


def _build_compact_context(user, profile, profile_skills, applications, recs, company_names):
    """Build a minimal context string (~120 tokens) for Nemotron."""
    applied = len([a for a in applications if a.status == "applied"])
    interviews = len([a for a in applications if a.status == "interview"])
    saved = len([a for a in applications if a.status == "saved"])

    top = ""
    for j, s in recs[:3]:
        cn = company_names.get(j.company_id, "?")
        top += f" {j.title}@{cn}({int(s)}%),"

    return (
        f"User: {user.name}, {profile.title or '?'}, {profile.location or '?'}\n"
        f"Skills: {', '.join(profile_skills[:12]) or 'none'}\n"
        f"Apps: {applied} applied, {interviews} interview, {saved} saved\n"
        f"Profile: {profile.completeness_score}%\n"
        f"Matches:{top or ' none'}"
    )


def _get_chat_context(user, profile, db):
    """Shared context building for both streaming and non-streaming."""
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]
    applications = db.query(Application).filter(Application.user_id == user.id).all()

    from services.matching_service import get_recommendations
    recs = get_recommendations(profile, db, limit=5)

    company_names = {}
    for j, _score in recs:
        if j.company_id:
            c = db.query(Company).filter(Company.id == j.company_id).first()
            if c:
                company_names[j.company_id] = c.name

    return profile_skills, applications, recs, company_names


def _build_system_prompt(user, ctx):
    return f"Rolio career AI. {ctx}\nRules: Reference user data. Be specific & actionable. Max 3 paragraphs. No fluff."


def _build_user_prompt(message, history):
    history_parts = []
    for m in (history or [])[-3:]:
        truncated = m.content[:100]
        role_label = "U" if m.role == "user" else "A"
        history_parts.append(f"{role_label}: {truncated}")

    prompt = message[:200]
    if history_parts:
        prompt = "Context:\n" + "\n".join(history_parts) + f"\nU: {message[:200]}"
    return prompt


@router.post("/chat")
async def chat(
    data: ChatRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_skills, applications, recs, company_names = _get_chat_context(user, profile, db)
    ctx = _build_compact_context(user, profile, profile_skills, applications, recs, company_names)

    system = _build_system_prompt(user, ctx)
    prompt = _build_user_prompt(data.message, data.history)

    # Try streaming AI
    try:
        from services.ai_stream import stream_ai
        tokens = []
        async for token in stream_ai(prompt, system, user_id=user.id):
            tokens.append(token)
        full_response = "".join(tokens)
        if full_response and not full_response.startswith("AI provider") and not full_response.startswith("No AI"):
            return {"response": full_response}
    except Exception as e:
        import logging
        logging.getLogger("rolio.ai").error("AI streaming error: %s", str(e)[:200])

    # Fallback: rule-based responses
    msg = data.message.lower()

    if any(w in msg for w in ["hello", "hi", "hey", "help"]):
        return {"response": f"Hey {user.name}! 👋 I'm your AI career assistant. I can see you have {len(applications)} applications and {len(profile_skills)} skills. Ask me about job matches, skills, profile tips, or interview prep!"}

    if any(w in msg for w in ["match", "recommend", "best job", "top job"]):
        if recs:
            lines = "Your top matches:\n\n"
            for j, s in recs[:5]:
                cn = company_names.get(j.company_id, "?")
                emoji = "🎯" if s >= 80 else "✅" if s >= 60 else "👍"
                lines += f"{emoji} **{j.title}** at {cn} — {int(s)}%\n"
            return {"response": lines}
        return {"response": "No recommendations yet. Complete your profile to get matches!"}

    if any(w in msg for w in ["skill", "what skill", "missing"]):
        common = ["Python", "JavaScript", "TypeScript", "React", "Node.js", "SQL", "AWS", "Docker"]
        missing = [s for s in common if s.lower() not in [ps.lower() for ps in profile_skills]]
        if missing:
            return {"response": f"Consider adding:\n\n" + "\n".join(f"• **{s}**" for s in missing[:6]) + "\n\nVisit [Profile](/profile) to add them."}
        return {"response": f"Your {len(profile_skills)} skills look solid!"}

    if any(w in msg for w in ["apply", "should i", "application"]):
        return {"response": f"**Status:** {len([a for a in applications if a.status=='applied'])} applied, {len([a for a in applications if a.status=='interview'])} interviews, {len([a for a in applications if a.status=='saved'])} saved.\n\n**Tips:** Apply to 5-10/day, customize resume per job, follow up after 1 week."}

    if any(w in msg for w in ["profile", "improve", "strength"]):
        tips = []
        if len(profile_skills) < 8: tips.append("Add more skills (aim 8-15)")
        if not profile.title: tips.append("Add professional title")
        if not profile.bio: tips.append("Write a bio")
        if profile.completeness_score < 70: tips.append("Complete more sections")
        if tips:
            return {"response": f"Profile strength: **{profile.completeness_score}%**\n\n" + "\n".join(f"• {t}" for t in tips)}
        return {"response": f"Profile is at **{profile.completeness_score}%** — looking great!"}

    if any(w in msg for w in ["interview", "prep", "question"]):
        return {"response": "**Interview prep:**\n\n• STAR method for behavioral\n• Research company news\n• Prepare 3-5 questions\n• Practice out loud\n\nCommon: Tell me about yourself, Why this company?, Challenge you faced"}

    return {"response": f"Hey {user.name}! I can help with:\n\n• Job matches & recommendations\n• Skills to add\n• Profile improvements\n• Interview prep\n• Application strategy\n\nWhat would you like to know?"}


@router.post("/job-question/stream")
async def job_question_stream(
    data: JobQuestionRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    """Streaming answers for the job-detail AI assistant buttons.

    NDJSON: {"token": "..."} lines, then {"done": true, "full": "..."}.
    Falls back to a deterministic rule-based answer when AI is unavailable,
    so the panel is never a dead end.
    """
    instruction = JOB_QUESTIONS.get(data.question)
    if not instruction:
        raise HTTPException(status_code=400, detail=f"Unknown question: {data.question}")

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]
    breakdown = get_match_breakdown(profile, job, db)

    ctx = _job_question_context(job, company, profile, profile_skills, breakdown)
    system = f"Rolio job-fit assistant. Be specific, reference the actual skills listed. No preamble, no sign-off. Max 120 words.\n{ctx}"
    prompt = instruction

    async def generate():
        import json as _json
        full = []
        try:
            from services.ai_stream import stream_ai
            async for token in stream_ai(prompt, system, max_tokens=260, user_id=user.id):
                full.append(token)
                yield _json.dumps({"token": token}) + "\n"
        except Exception as e:
            import logging
            logging.getLogger("rolio.ai").error("job-question stream error: %s", str(e)[:200])

        text = "".join(full).strip()
        # Detect dead-end AI outputs and replace with a rule-based answer
        bad = (not text or text.startswith(("AI provider", "No AI", "AI rate limit", "AI service")))
        if bad:
            text = _rule_based_job_answer(data.question, job, company, breakdown, profile_skills)
            yield _json.dumps({"token": text}) + "\n"
        yield _json.dumps({"done": True, "full": text}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


def _rule_based_job_answer(question, job, company, breakdown, profile_skills) -> str:
    """Deterministic fallback so the UI always shows something useful."""
    jtitle = job.title
    strong = breakdown.get("strong_matches", [])
    missing = breakdown.get("missing_skills", [])
    pct = breakdown["overall"]
    skill_list = ", ".join(profile_skills[:6]) or "your listed skills"

    if question == "why_match":
        verdict = "strong fit" if pct >= 70 else "reasonable fit" if pct >= 50 else "stretch fit"
        lines = [f"You're a {verdict} for {jtitle} ({pct}% match).", ""]
        if strong:
            lines += [f"• You already have: {', '.join(strong[:4])}"]
        lines.append(f"• Your background in {skill_list} maps to the core requirements.")
        return "\n".join(lines)
    if question == "missing":
        if not missing:
            return f"No significant gaps — your skills cover the listed requirements for {jtitle}. Focus on interview prep next."
        lines = [f"Gaps for {jtitle}:", ""]
        lines += [f"• {m} — build a small project or take a course to close this" for m in missing[:3]]
        return "\n".join(lines)
    if question == "apply_tips":
        return (
            f"Applying to {jtitle}:\n\n"
            f"1. Resume: lead with {', '.join(strong[:2]) or skill_list} — mirror the job's exact wording.\n"
            f"2. Cover letter: one paragraph on a project that proves the top required skill.\n"
            f"3. Apply within 48h of posting, follow up after 5-7 days."
        )
    if question == "tailor_resume":
        return (
            f"Tailoring for {jtitle}:\n\n"
            + "\n".join(f"• Put **{s}** in your summary AND first bullet of your most recent role" for s in (strong[:3] or missing[:3]))
            + "\n• Quantify results (%, $, users, latency) on every bullet"
        )
    # prepare
    return (
        f"Interview prep for {jtitle}:\n\n"
        f"• Technical: expect deep-dives on {', '.join(missing[:2] or strong[:2] or ['the core stack'])}\n"
        f"• Behavioral: prepare STAR stories about shipped projects\n"
        f"• Ask them: how does the team handle code review and deployment cadence?"
    )


@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    user: User = Depends(ai_rate_limit),
    db: Session = Depends(get_db),
):
    """Streaming AI chat — returns NDJSON lines (one per token chunk)."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_skills, applications, recs, company_names = _get_chat_context(user, profile, db)
    ctx = _build_compact_context(user, profile, profile_skills, applications, recs, company_names)

    system = _build_system_prompt(user, ctx)
    prompt = _build_user_prompt(data.message, data.history)

    async def generate():
        import json
        full = []
        try:
            from services.ai_stream import stream_ai
            async for token in stream_ai(prompt, system, user_id=user.id):
                full.append(token)
                yield json.dumps({"token": token, "done": False}) + "\n"
            yield json.dumps({"token": "", "done": True, "full": "".join(full)}) + "\n"
        except Exception as e:
            import logging
            logging.getLogger("rolio.ai").error("Stream error: %s", str(e)[:200])
            yield json.dumps({"token": "", "done": True, "full": "AI service error. Please try again."}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
