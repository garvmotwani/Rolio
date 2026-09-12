from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

    def model_post_init(self, __context):
        from utils.auth import validate_password_strength
        validate_password_strength(self.password)
        if len(self.name.strip()) < 1:
            raise ValueError("Name is required")
        if len(self.name) > 100:
            raise ValueError("Name is too long")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    def model_post_init(self, __context):
        from utils.auth import validate_password_strength
        validate_password_strength(self.password)

class VerifyEmailRequest(BaseModel):
    token: str

class Token(BaseModel):
    """Response after login/register/refresh. No token in body — tokens are in HttpOnly cookies."""
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_onboarded: bool
    email_verified: bool = False
    created_at: datetime
    class Config:
        from_attributes = True


# Profile schemas
class SkillCreate(BaseModel):
    name: str
    level: str = "intermediate"
    category: str = "technical"

class SkillResponse(BaseModel):
    id: int
    name: str
    level: str
    category: str
    class Config:
        from_attributes = True

class ExperienceCreate(BaseModel):
    company: str
    title: str
    description: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    achievements: str = ""

class ExperienceResponse(BaseModel):
    id: int
    company: str
    title: str
    description: str
    location: str
    start_date: str
    end_date: str
    is_current: bool
    achievements: str
    class Config:
        from_attributes = True

class EducationCreate(BaseModel):
    institution: str
    degree: str
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    description: str = ""

class EducationResponse(BaseModel):
    id: int
    institution: str
    degree: str
    field_of_study: str
    start_date: str
    end_date: str
    gpa: str
    description: str
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    technologies: str = ""
    url: str = ""
    github_url: str = ""

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    technologies: str
    url: str
    github_url: str
    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    preferred_roles: Optional[str] = None
    preferred_locations: Optional[str] = None
    preferred_work_type: Optional[str] = None
    salary_expectation_min: Optional[int] = None
    salary_expectation_max: Optional[int] = None

    def model_post_init(self, __context):
        # Enforce max lengths
        for field in ['title', 'location', 'linkedin_url', 'github_url', 'portfolio_url']:
            val = getattr(self, field, None)
            if val and len(val) > 500:
                setattr(self, field, val[:500])
        if self.bio and len(self.bio) > 5000:
            self.bio = self.bio[:5000]
        if self.preferred_roles and len(self.preferred_roles) > 1000:
            self.preferred_roles = self.preferred_roles[:1000]
        if self.preferred_locations and len(self.preferred_locations) > 1000:
            self.preferred_locations = self.preferred_locations[:1000]
        if self.salary_expectation_min is not None and (self.salary_expectation_min < 0 or self.salary_expectation_min > 10000000):
            self.salary_expectation_min = None
        if self.salary_expectation_max is not None and (self.salary_expectation_max < 0 or self.salary_expectation_max > 10000000):
            self.salary_expectation_max = None

class OnboardingData(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    education: Optional[List[EducationCreate]] = None
    experience: Optional[List[ExperienceCreate]] = None
    skills: Optional[List[SkillCreate]] = None
    projects: Optional[List[ProjectCreate]] = None
    preferred_roles: Optional[str] = None
    preferred_locations: Optional[str] = None
    preferred_work_type: Optional[str] = None
    salary_expectation_min: Optional[int] = None
    salary_expectation_max: Optional[int] = None
    bio: Optional[str] = None

class ProfileResponse(BaseModel):
    id: int
    user_id: int
    title: str
    location: str
    bio: str
    linkedin_url: str
    github_url: str
    portfolio_url: str
    preferred_roles: str
    preferred_locations: str
    preferred_work_type: str
    salary_expectation_min: int
    salary_expectation_max: int
    completeness_score: float
    skills: List[SkillResponse] = []
    experiences: List[ExperienceResponse] = []
    educations: List[EducationResponse] = []
    projects: List[ProjectResponse] = []
    class Config:
        from_attributes = True


# Job schemas
class JobResponse(BaseModel):
    id: int
    company_id: int
    title: str
    description: str
    requirements: str
    responsibilities: str
    preferred_qualifications: str
    skills_required: str
    skills_preferred: str
    location: str
    work_type: str
    salary_min: int
    salary_max: int
    experience_level: str
    employment_type: str
    application_url: str
    is_active: bool
    posted_at: datetime
    company_name: str = ""
    company_logo: str = ""
    company_industry: str = ""
    match_score: float = 0.0
    is_saved: bool = False
    is_applied: bool = False
    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int

class JobSearchRequest(BaseModel):
    query: str = ""
    location: str = ""
    work_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    employment_type: Optional[str] = None
    sort_by: str = "best_match"
    page: int = 1
    per_page: int = 20


# Application schemas
class ApplicationCreate(BaseModel):
    # int for local DB jobs; str (jsearch_/remotive_/jobicy_ prefixed) for
    # external jobs — the route imports those into the DB before applying.
    job_id: int | str
    notes: str = ""
    external_url: str = ""

    def model_post_init(self, __context):
        if self.notes and len(self.notes) > 5000:
            self.notes = self.notes[:5000]
        if self.external_url and len(self.external_url) > 2000:
            self.external_url = self.external_url[:2000]

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    interview_date: Optional[str] = None
    external_url: Optional[str] = None

    def model_post_init(self, __context):
        ALLOWED_STATUSES = {"saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"}
        if self.status and self.status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}")
        if self.notes and len(self.notes) > 5000:
            self.notes = self.notes[:5000]
        if self.external_url and len(self.external_url) > 2000:
            self.external_url = self.external_url[:2000]
        # Validate interview_date format
        if self.interview_date:
            from datetime import datetime as dt
            try:
                dt.fromisoformat(self.interview_date)
            except (ValueError, TypeError):
                raise ValueError("Invalid interview_date format")

class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    status: str
    notes: str
    applied_at: datetime
    interview_date: Optional[datetime]
    external_url: str
    match_score: float
    job_title: str = ""
    company_name: str = ""
    company_logo: str = ""
    job_location: str = ""
    job_work_type: str = ""
    job_salary_min: int = 0
    job_salary_max: int = 0
    skills_required: str = ""
    class Config:
        from_attributes = True


# Saved job schemas
class SavedJobResponse(BaseModel):
    id: int
    job_id: int
    saved_at: datetime
    job_title: str = ""
    company_name: str = ""
    company_logo: str = ""
    job_location: str = ""
    job_work_type: str = ""
    job_salary_min: int = 0
    job_salary_max: int = 0
    skills_required: str = ""
    match_score: float = 0.0
    is_applied: bool = False


# Notification schemas
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    link: str
    created_at: datetime
    class Config:
        from_attributes = True


# AI schemas
class AIMatchRequest(BaseModel):
    job_id: int

class AIResponse(BaseModel):
    response: str
    data: Optional[dict] = None

class AICareerAdviceRequest(BaseModel):
    question: str

class AIResumeAnalysisResponse(BaseModel):
    skills: List[str] = []
    experience_summary: str = ""
    education_summary: str = ""
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    completeness: float = 0.0


# Dashboard schemas
class DashboardResponse(BaseModel):
    strong_matches: int = 0
    total_applications: int = 0
    interviews: int = 0
    saved_jobs: int = 0
    profile_strength: float = 0.0
    recommended_jobs: List[JobResponse] = []
    recent_applications: List[ApplicationResponse] = []
    profile_tips: List[str] = []


# Company schemas
class CompanyResponse(BaseModel):
    id: int
    name: str
    logo_url: str
    industry: str
    location: str
    website: str
    description: str
    size: str
    founded: str
    open_jobs_count: int = 0
    class Config:
        from_attributes = True
