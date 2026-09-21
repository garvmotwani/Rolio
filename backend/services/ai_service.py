"""
AI service — match analysis, career advice, application tips.
All calls use Nemotron with token-efficient prompts.
"""

import json
from models.models import Profile, Job, Skill
from services.matching_service import get_match_breakdown, parse_skills_from_string
from services.ai_provider import call_ai, build_match_prompt, build_career_advice_prompt


async def generate_match_explanation(profile: Profile, job: Job, db) -> dict:
    """Match explanation — Nemotron, ~300 tokens total (input+output)."""
    breakdown = get_match_breakdown(profile, job, db)

    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]

    try:
        job_skills = json.loads(job.skills_required) if job.skills_required else []
    except (json.JSONDecodeError, TypeError):
        job_skills = parse_skills_from_string(job.skills_required)

    from models.models import Company
    company = db.query(Company).filter(Company.id == job.company_id).first() if job.company_id else None

    prompt = build_match_prompt(
        {'title': profile.title or '?', 'skills': profile_skills, 'years': _estimate_years(profile, db)},
        {'title': job.title, 'company': company.name if company else '?', 'skills': job_skills[:8], 'level': job.experience_level or 'mid'},
        breakdown,
    )

    ai_response = await call_ai(prompt, "Concise job match analysis. 3 sentences max.", provider="nemotron", max_tokens=250)

    if not ai_response:
        ai_response = _rule_based_match(profile, job, breakdown, db)

    return {"breakdown": breakdown, "explanation": ai_response}


def _estimate_years(profile: Profile, db) -> int:
    try:
        from models.models import Experience
        exps = db.query(Experience).filter(Experience.profile_id == profile.id).all()
        total = 0
        for e in exps:
            if e.start_date:
                start = int(e.start_date[:4])
                end = int(e.end_date[:4]) if e.end_date else 2026
                total += max(0, end - start)
        return total
    except Exception:
        return 0


def _rule_based_match(profile, job, breakdown, db) -> str:
    lines = []
    pct = breakdown['overall']
    if pct >= 80: lines.append(f"**Strong match** ({pct}%)")
    elif pct >= 60: lines.append(f"**Moderate match** ({pct}%)")
    else: lines.append(f"**Partial match** ({pct}%)")
    if breakdown['strong_matches']:
        lines.append(f"Matching: {', '.join(breakdown['strong_matches'][:4])}")
    if breakdown['missing_skills']:
        lines.append(f"Gap: {', '.join(breakdown['missing_skills'][:3])}")
    if pct >= 70: lines.append("→ Apply.")
    elif pct >= 50: lines.append("→ Worth applying. Highlight relevant skills.")
    else: lines.append("→ Consider developing missing skills first.")
    return "\n".join(lines)


async def generate_career_advice(profile: Profile, question: str, db) -> str:
    """Career advice — Nemotron, ~300 tokens total."""
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]

    prompt = build_career_advice_prompt(
        {'name': profile.user.name if hasattr(profile, 'user') else 'User', 'title': profile.title or '?', 'skills': profile_skills},
        question,
    )

    ai_response = await call_ai(prompt, "Rolio career AI. Be specific & actionable. Reference user skills.", provider="nemotron", max_tokens=300)

    if not ai_response:
        ai_response = _fallback_advice(profile, question, profile_skills)

    return ai_response


def _fallback_advice(profile, question, profile_skills):
    q = question.lower()
    if "frontend" in q:
        fe = {"react", "vue", "javascript", "typescript", "css", "html"}
        have = fe & set(ps.lower() for ps in profile_skills)
        miss = fe - set(ps.lower() for ps in profile_skills)
        r = "Frontend tips:\n"
        if have: r += f"Strong: {', '.join(have)}\n"
        if miss: r += f"Add: {', '.join(list(miss)[:3])}\n"
        return r
    if "resume" in q or "improve" in q:
        tips = []
        if len(profile_skills) < 8: tips.append("Add more skills (aim 8-15)")
        if not profile.title: tips.append("Add professional title")
        if not profile.bio: tips.append("Write a bio")
        return "Profile tips:\n" + "\n".join(f"• {t}" for t in tips) if tips else "Profile looks good!"
    return "Ask about skills, resume tips, interview prep, or application strategy."


async def generate_application_advice(profile: Profile, job: Job, db) -> str:
    """Application tips — Nemotron, ~200 tokens total."""
    breakdown = get_match_breakdown(profile, job, db)
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]

    prompt = (
        f"Apply tips for {job.title}. Skills: {', '.join(profile_skills[:8])}. "
        f"Missing: {', '.join(breakdown['missing_skills'][:3])}. Match: {breakdown['overall']}%. "
        f"→ 3 tips: resume, cover letter, interview."
    )

    ai_response = await call_ai(prompt, "3 concise application tips. Reference their skills.", provider="nemotron", max_tokens=200)

    if not ai_response:
        ai_response = f"Tips for {job.title}:\n"
        if breakdown['strong_matches']:
            ai_response += f"Highlight: {', '.join(breakdown['strong_matches'][:3])}\n"
        if breakdown['missing_skills']:
            ai_response += f"Address: {', '.join(breakdown['missing_skills'][:3])}\n"
        ai_response += f"Match: {breakdown['overall']}% — {'apply with confidence' if breakdown['overall'] >= 70 else 'emphasize transferable skills'}"

    return ai_response
