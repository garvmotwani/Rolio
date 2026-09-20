import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import User, Profile, Skill, Experience, Education, Project
from schemas.schemas import ProfileUpdate, ProfileResponse, OnboardingData, SkillResponse, ExperienceResponse, EducationResponse, ProjectResponse
from utils.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/me")
def get_current_user_info(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_onboarded": user.is_onboarded,
        "created_at": user.created_at.isoformat(),
    }


@router.put("/users/me")
def update_user_info(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if "name" in data:
        user.name = data["name"]
    db.commit()
    return {"message": "Updated"}


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profile")
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    # Recalculate completeness
    profile.completeness_score = calculate_completeness(profile, db)
    db.commit()
    db.refresh(profile)
    return {"message": "Profile updated", "completeness_score": profile.completeness_score}


@router.post("/onboarding")
def complete_onboarding(
    data: OnboardingData,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()

    # Update user name
    if data.name:
        user.name = data.name

    # Update profile fields
    if data.title:
        profile.title = data.title
    if data.location:
        profile.location = data.location
    if data.bio:
        profile.bio = data.bio
    if data.preferred_roles:
        profile.preferred_roles = data.preferred_roles
    if data.preferred_locations:
        profile.preferred_locations = data.preferred_locations
    if data.preferred_work_type:
        profile.preferred_work_type = data.preferred_work_type
    if data.target_role:
        profile.target_role = data.target_role
    if data.salary_expectation_min:
        profile.salary_expectation_min = data.salary_expectation_min
    if data.salary_expectation_max:
        profile.salary_expectation_max = data.salary_expectation_max

    # Add skills
    if data.skills:
        db.query(Skill).filter(Skill.profile_id == profile.id).delete()
        for s in data.skills:
            skill = Skill(profile_id=profile.id, name=s.name, level=s.level, category=s.category)
            db.add(skill)

    # Add experience
    if data.experience:
        db.query(Experience).filter(Experience.profile_id == profile.id).delete()
        for e in data.experience:
            exp = Experience(
                profile_id=profile.id,
                company=e.company,
                title=e.title,
                description=e.description,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                is_current=e.is_current,
                achievements=e.achievements,
            )
            db.add(exp)

    # Add education
    if data.education:
        db.query(Education).filter(Education.profile_id == profile.id).delete()
        for ed in data.education:
            edu = Education(
                profile_id=profile.id,
                institution=ed.institution,
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                start_date=ed.start_date,
                end_date=ed.end_date,
                gpa=ed.gpa,
                description=ed.description,
            )
            db.add(edu)

    # Add projects
    if data.projects:
        db.query(Project).filter(Project.profile_id == profile.id).delete()
        for p in data.projects:
            proj = Project(
                profile_id=profile.id,
                name=p.name,
                description=p.description,
                technologies=p.technologies,
                url=p.url,
                github_url=p.github_url,
            )
            db.add(proj)

    profile.completeness_score = calculate_completeness(profile, db)
    user.is_onboarded = True
    db.commit()
    db.refresh(profile)

    return {
        "message": "Onboarding complete",
        "profile": {
            "completeness_score": profile.completeness_score,
            "is_onboarded": True,
        },
    }


def calculate_completeness(profile, db):
    score = 0
    total = 100

    # Skills (25 points)
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).count()
    score += min(25, skills * 5)

    # Experience (25 points)
    exp_count = db.query(Experience).filter(Experience.profile_id == profile.id).count()
    score += min(25, exp_count * 8)

    # Education (15 points)
    edu_count = db.query(Education).filter(Education.profile_id == profile.id).count()
    score += min(15, edu_count * 15)

    # Projects (15 points)
    proj_count = db.query(Project).filter(Project.profile_id == profile.id).count()
    score += min(15, proj_count * 5)

    # Profile info (20 points)
    if profile.title:
        score += 5
    if profile.location:
        score += 5
    if profile.preferred_roles:
        score += 5
    if profile.preferred_work_type:
        score += 5

    return min(100, score)


@router.post("/profile/skills")
def add_skill(
    data: SkillResponse,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    skill = Skill(profile_id=profile.id, name=data.name, level=data.level, category=data.category)
    db.add(skill)
    db.commit()
    return {"message": "Skill added"}


@router.delete("/profile/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    db.query(Skill).filter(Skill.id == skill_id, Skill.profile_id == profile.id).delete()
    db.commit()
    return {"message": "Skill removed"}


@router.post("/profile/experiences")
def add_experience(
    data: ExperienceResponse,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    exp = Experience(
        profile_id=profile.id,
        company=data.company,
        title=data.title,
        description=data.description,
        location=data.location,
        start_date=data.start_date,
        end_date=data.end_date,
        is_current=data.is_current,
        achievements=data.achievements,
    )
    db.add(exp)
    db.commit()
    return {"message": "Experience added"}


@router.post("/profile/educations")
def add_education(
    data: EducationResponse,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    edu = Education(
        profile_id=profile.id,
        institution=data.institution,
        degree=data.degree,
        field_of_study=data.field_of_study,
        start_date=data.start_date,
        end_date=data.end_date,
        gpa=data.gpa,
        description=data.description,
    )
    db.add(edu)
    db.commit()
    return {"message": "Education added"}


@router.post("/profile/projects")
def add_project(
    data: ProjectResponse,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    proj = Project(
        profile_id=profile.id,
        name=data.name,
        description=data.description,
        technologies=data.technologies,
        url=data.url,
        github_url=data.github_url,
    )
    db.add(proj)
    db.commit()
    return {"message": "Project added"}
