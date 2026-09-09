from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database.connection import Base


class WorkType(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "on-site"


class ExperienceLevel(str, enum.Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Nullable for OAuth-only users (Google sign-in). Null means no password login.
    hashed_password = Column(String, nullable=True)
    name = Column(String, nullable=False)
    # Google identity (OpenID Connect `sub` claim). Unique — one Google account
    # maps to at most one Rolio user. NULL for password-registered users.
    google_sub = Column(String, nullable=True, unique=True, index=True)
    # Email verification: True for Google sign-in users (Google verifies the
    # address) and for anyone who clicked a verification link. Password
    # registrations start False.
    email_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True)
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)
    resume = relationship("Resume", back_populates="user", uselist=False)
    saved_jobs = relationship("SavedJob", back_populates="user")
    applications = relationship("Application", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    title = Column(String, default="")
    location = Column(String, default="")
    bio = Column(Text, default="")
    linkedin_url = Column(String, default="")
    github_url = Column(String, default="")
    portfolio_url = Column(String, default="")
    preferred_roles = Column(Text, default="")  # JSON array
    preferred_locations = Column(Text, default="")  # JSON array
    preferred_work_type = Column(String, default="hybrid")
    salary_expectation_min = Column(Integer, default=0)
    salary_expectation_max = Column(Integer, default=0)
    completeness_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")
    skills = relationship("Skill", back_populates="profile", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="profile", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="profile", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="profile", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    name = Column(String, nullable=False)
    level = Column(String, default="intermediate")  # beginner, intermediate, advanced, expert
    category = Column(String, default="technical")  # technical, soft, tool

    profile = relationship("Profile", back_populates="skills")


class Experience(Base):
    __tablename__ = "experiences"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    location = Column(String, default="")
    start_date = Column(String, default="")
    end_date = Column(String, default="")
    is_current = Column(Boolean, default=False)
    achievements = Column(Text, default="")  # JSON array

    profile = relationship("Profile", back_populates="experiences")


class Education(Base):
    __tablename__ = "educations"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String, default="")
    start_date = Column(String, default="")
    end_date = Column(String, default="")
    gpa = Column(String, default="")
    description = Column(Text, default="")

    profile = relationship("Profile", back_populates="educations")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    technologies = Column(Text, default="")  # JSON array
    url = Column(String, default="")
    github_url = Column(String, default="")

    profile = relationship("Profile", back_populates="projects")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    raw_text = Column(Text, default="")
    parsed_name = Column(String, default="")
    parsed_email = Column(String, default="")
    parsed_phone = Column(String, default="")
    parsed_education = Column(Text, default="")  # JSON
    parsed_experience = Column(Text, default="")  # JSON
    parsed_skills = Column(Text, default="")  # JSON
    parsed_projects = Column(Text, default="")  # JSON
    parsed_certifications = Column(Text, default="")  # JSON
    ai_analysis = Column(Text, default="")  # JSON
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resume")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    logo_url = Column(String, default="")
    industry = Column(String, default="")
    location = Column(String, default="")
    website = Column(String, default="")
    description = Column(Text, default="")
    size = Column(String, default="")  # 1-10, 11-50, 51-200, etc.
    founded = Column(String, default="")

    jobs = relationship("Job", back_populates="company")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    responsibilities = Column(Text, default="")
    preferred_qualifications = Column(Text, default="")
    skills_required = Column(Text, default="")  # JSON array
    skills_preferred = Column(Text, default="")  # JSON array
    location = Column(String, default="")
    work_type = Column(String, default="hybrid")
    salary_min = Column(Integer, default=0)
    salary_max = Column(Integer, default=0)
    experience_level = Column(String, default="mid")
    employment_type = Column(String, default="full-time")
    application_url = Column(String, default="")
    source = Column(String, default="internal")
    is_active = Column(Boolean, default=True)
    posted_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="jobs")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    saved_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_saved_job_user_job"),
        Index("idx_saved_user_saved", "user_id", "saved_at"),
    )

    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job")


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    status = Column(String, default="applied")
    notes = Column(Text, default="")
    applied_at = Column(DateTime, default=datetime.utcnow)
    interview_date = Column(DateTime, nullable=True)
    external_url = Column(String, default="")
    match_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
        Index("idx_application_user_status", "user_id", "status"),
        Index("idx_application_applied_at", "applied_at"),
    )

    user = relationship("User", back_populates="applications")
    job = relationship("Job")


class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query = Column(String(200), default="")
    location = Column(String(100), default="")
    work_type = Column(String(20), default="")
    experience_level = Column(String(20), default="")
    source = Column(String(20), default="all")
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_search_history_user_created", "user_id", "created_at"),
    )

    user = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(Text, default="")
    type = Column(String, default="info")  # info, success, warning
    is_read = Column(Boolean, default=False)
    link = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
