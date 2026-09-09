import json
import re
from sqlalchemy.orm import Session
from models.models import Profile, Skill, Experience, Job, Company


def normalize(text: str) -> str:
    return text.lower().strip() if text else ""


def calculate_skill_match(profile_skills: list[str], job_skills: list[str]) -> float:
    if not job_skills:
        return 1.0

    profile_set = set(normalize(s) for s in profile_skills)
    job_set = set(normalize(s) for s in job_skills)

    if not job_set:
        return 1.0

    matches = profile_set & job_set
    # Partial matches: check if any profile skill is a substring of a job skill or vice versa
    partial = set()
    for ps in profile_set:
        for js in job_set:
            if ps != js and (ps in js or js in ps):
                partial.add(ps)

    score = (len(matches) + len(partial) * 0.5) / len(job_set)
    return min(1.0, score)


def calculate_experience_match(profile: Profile, job: Job) -> float:
    experiences = profile.experiences if profile.experiences else []
    total_years = 0

    for exp in experiences:
        start = exp.start_date
        end = exp.end_date if not exp.is_current else "2024-12"
        if start:
            try:
                start_year = int(start[:4])
                end_year = int(end[:4]) if end else 2024
                total_years += max(0, end_year - start_year)
            except (ValueError, IndexError):
                pass

    level_map = {
        "intern": 0,
        "junior": 1,
        "mid": 3,
        "senior": 5,
        "lead": 8,
        "executive": 10,
    }

    required_years = level_map.get(job.experience_level, 3)

    if total_years >= required_years:
        return 1.0
    elif total_years >= required_years * 0.5:
        return 0.7 + (total_years / required_years) * 0.3
    else:
        return max(0.3, total_years / max(1, required_years))


def calculate_location_match(profile: Profile, job: Job) -> float:
    if not job.location or not profile.location:
        return 0.8

    job_loc = normalize(job.location)
    profile_loc = normalize(profile.location)

    if profile_loc in job_loc or job_loc in profile_loc:
        return 1.0

    if job.work_type == "remote":
        return 1.0

    return 0.5


def calculate_work_type_match(profile: Profile, job: Job) -> float:
    if not profile.preferred_work_type:
        return 0.8
    if profile.preferred_work_type == job.work_type:
        return 1.0
    return 0.6


def calculate_salary_match(profile: Profile, job: Job) -> float:
    if not profile.salary_expectation_min and not profile.salary_expectation_max:
        return 0.8

    if not job.salary_min and not job.salary_max:
        return 0.8

    # Check overlap
    p_min = profile.salary_expectation_min or 0
    p_max = profile.salary_expectation_max or float("inf")
    j_min = job.salary_min or 0
    j_max = job.salary_max or float("inf")

    if j_min >= p_min and j_max <= p_max:
        return 1.0
    elif j_max >= p_min and j_min <= p_max:
        return 0.8
    elif j_min >= p_min * 0.8:
        return 0.6
    else:
        return 0.3


def calculate_role_match(profile: Profile, job: Job) -> float:
    if not profile.preferred_roles:
        return 0.7

    try:
        roles = json.loads(profile.preferred_roles) if isinstance(profile.preferred_roles, str) else profile.preferred_roles
    except (json.JSONDecodeError, TypeError):
        roles = [r.strip() for r in profile.preferred_roles.split(",")]

    job_title = normalize(job.title)
    for role in roles:
        role_norm = normalize(str(role))
        if role_norm in job_title or job_title in role_norm:
            return 1.0
        # Check word overlap
        role_words = set(role_norm.split())
        title_words = set(job_title.split())
        overlap = role_words & title_words
        if overlap:
            return 0.7 + 0.3 * len(overlap) / max(len(role_words), 1)

    return 0.5


def get_skill_lists(profile: Profile, db: Session) -> tuple[list, list]:
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    profile_skills = [s.name for s in skills]

    return profile_skills


def parse_skills_from_string(skills_str: str) -> list:
    if not skills_str:
        return []
    try:
        parsed = json.loads(skills_str)
        if isinstance(parsed, list):
            return [str(s) for s in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [s.strip() for s in skills_str.split(",") if s.strip()]


def calculate_match_score(profile: Profile, job: Job, db: Session, cached_skills: list = None) -> float:
    profile_skills = cached_skills if cached_skills is not None else get_skill_lists(profile, db)
    job_required = parse_skills_from_string(job.skills_required)
    job_preferred = parse_skills_from_string(job.skills_preferred)
    all_job_skills = job_required + job_preferred

    skill_score = calculate_skill_match(profile_skills, all_job_skills)
    experience_score = calculate_experience_match(profile, job)
    location_score = calculate_location_match(profile, job)
    work_type_score = calculate_work_type_match(profile, job)
    salary_score = calculate_salary_match(profile, job)
    role_score = calculate_role_match(profile, job)

    # Weighted average
    weights = {
        "skill": 0.30,
        "experience": 0.20,
        "role": 0.20,
        "location": 0.10,
        "work_type": 0.10,
        "salary": 0.10,
    }

    total = (
        skill_score * weights["skill"]
        + experience_score * weights["experience"]
        + role_score * weights["role"]
        + location_score * weights["location"]
        + work_type_score * weights["work_type"]
        + salary_score * weights["salary"]
    )

    return round(total * 100, 1)


def get_match_breakdown(profile: Profile, job: Job, db: Session) -> dict:
    profile_skills = get_skill_lists(profile, db)
    job_required = parse_skills_from_string(job.skills_required)
    job_preferred = parse_skills_from_string(job.skills_preferred)
    all_job_skills = job_required + job_preferred

    skill_score = calculate_skill_match(profile_skills, all_job_skills)
    experience_score = calculate_experience_match(profile, job)
    location_score = calculate_location_match(profile, job)
    work_type_score = calculate_work_type_match(profile, job)
    salary_score = calculate_salary_match(profile, job)
    role_score = calculate_role_match(profile, job)

    profile_set = set(normalize(s) for s in profile_skills)
    job_set = set(normalize(s) for s in all_job_skills)

    strong_matches = list(profile_set & job_set)
    missing_skills = list(job_set - profile_set)

    # Partial matches
    partial = []
    for ps in profile_set:
        for js in job_set:
            if ps != js and ps not in job_set and (ps in js or js in ps):
                partial.append(str(ps))

    total = (
        skill_score * 0.30
        + experience_score * 0.20
        + role_score * 0.20
        + location_score * 0.10
        + work_type_score * 0.10
        + salary_score * 0.10
    )

    return {
        "overall": round(total * 100, 1),
        "skills": round(skill_score * 100, 1),
        "experience": round(experience_score * 100, 1),
        "role": round(role_score * 100, 1),
        "location": round(location_score * 100, 1),
        "work_type": round(work_type_score * 100, 1),
        "salary": round(salary_score * 100, 1),
        "strong_matches": strong_matches,
        "partial_matches": partial,
        "missing_skills": missing_skills,
    }


def compute_quick_match(profile: Profile, job_detail: dict) -> float:
    """Compute a fast match score for a JSearch job (dict, not ORM model)."""
    # Skill match
    profile_skills = []
    if profile.skills:
        profile_skills = [s.name.lower() for s in profile.skills]
    elif profile.preferred_roles:
        try:
            profile_skills = [s.lower() for s in json.loads(profile.preferred_roles)]
        except Exception:
            pass

    job_skills = [s.lower() for s in (job_detail.get("skills") or [])]
    skill_score = calculate_skill_match(profile_skills, job_skills) if job_skills else 0.7

    # Experience match
    exp_level = job_detail.get("experience_level", "mid")
    level_map = {"intern": 0, "junior": 1, "mid": 3, "senior": 5, "lead": 8, "executive": 10}
    required = level_map.get(exp_level, 3)
    # Rough estimate from profile
    total_years = 0
    if profile.experiences:
        for exp in profile.experiences:
            try:
                sy = int(exp.start_date[:4]) if exp.start_date else 2024
                ey = int(exp.end_date[:4]) if exp.end_date and not exp.is_current else 2024
                total_years += max(0, ey - sy)
            except Exception:
                pass
    exp_score = min(1.0, total_years / max(1, required)) if required > 0 else 0.8

    # Role match
    role_score = 0.5
    if profile.preferred_roles:
        try:
            roles = json.loads(profile.preferred_roles) if isinstance(profile.preferred_roles, str) else profile.preferred_roles
        except Exception:
            roles = [r.strip() for r in str(profile.preferred_roles).split(",")]
        title = (job_detail.get("title") or "").lower()
        for r in (roles or []):
            rn = normalize(str(r))
            if rn in title or title in rn:
                role_score = 1.0
                break
            if set(rn.split()) & set(title.split()):
                role_score = 0.7

    total = skill_score * 0.35 + exp_score * 0.25 + role_score * 0.20 + 0.7 * 0.20
    return round(min(1.0, total) * 100, 1)


def get_recommendations(profile: Profile, db: Session, limit: int = 20) -> list:
    from models.models import Application, SavedJob

    applied_job_ids = [a.job_id for a in db.query(Application).filter(
        Application.user_id == profile.user_id
    ).all()]

    jobs = db.query(Job).filter(Job.is_active == True).all()

    scored = []
    for job in jobs:
        if job.id in applied_job_ids:
            continue
        score = calculate_match_score(profile, job, db)
        if score >= 30:
            scored.append((job, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
