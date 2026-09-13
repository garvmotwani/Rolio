"""
Resume upload and parsing routes — SECURED.

Security measures:
- Maximum upload size enforced (configurable via env).
- File extension and magic-byte validation (PDF/DOCX only).
- Generated server-side filenames prevent path traversal.
- Uploads stored outside public serving paths.
- Previous resume replaced safely on new upload.
- Content is streamed to disk, not held entirely in memory for large files.
"""
import os
import json
import uuid
import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config import UPLOAD_DIR, MAX_UPLOAD_SIZE_BYTES, ALLOWED_UPLOAD_EXTENSIONS
from database.connection import get_db
from models.models import User, Resume, Skill, Experience, Education, Project, Profile
from utils.auth import get_current_user
from services.resume_service import process_resume
from utils.security_logging import log_upload_event

router = APIRouter(prefix="/api", tags=["resumes"])

# File magic bytes for validation
MAGIC_BYTES = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",  # ZIP-based format (Office Open XML)
}


def _validate_file_content(file_path: str, expected_ext: str) -> bool:
    """Validate file content matches expected type via magic bytes.

    DOCX gets an extra structural check beyond the ZIP magic bytes: a genuine
    Word document is a ZIP whose central directory lists word/document.xml.
    A renamed generic ZIP (or an XLSX/PPTX) passes the magic-byte check but
    fails this one.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        expected = MAGIC_BYTES.get(expected_ext)
        if expected and not header.startswith(expected):
            return False
        if expected_ext == ".docx":
            import zipfile
            with zipfile.ZipFile(file_path) as zf:
                names = set(zf.namelist())
            if "word/document.xml" not in names:
                return False
        return True
    except Exception:
        return False


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(ALLOWED_UPLOAD_EXTENSIONS)} files are supported",
        )

    # Stream upload to disk with size limit
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    original_name = file.filename

    total_size = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    f.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Validate content via magic bytes (+ DOCX structural check)
    if not _validate_file_content(file_path, ext):
        os.remove(file_path)
        log_upload_event(user.id, original_name, total_size, success=False, detail="invalid_content")
        raise HTTPException(
            status_code=400,
            detail="File content does not match expected format",
        )

    # Process resume
    try:
        parsed = process_resume(file_path)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="Failed to parse resume")

    if "error" in parsed:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=parsed["error"])

    # The physical file is a processing artifact: everything of value was
    # extracted into the database above/below. Serverless /tmp is ephemeral
    # and nothing ever reads the file again, so delete it immediately.
    try:
        os.remove(file_path)
    except OSError:
        pass

    # Delete previous resume file if replacing
    existing = db.query(Resume).filter(Resume.user_id == user.id).first()
    if existing:
        old_path = os.path.join(UPLOAD_DIR, existing.filename)
        if os.path.exists(old_path) and old_path != file_path:
            try:
                os.remove(old_path)
            except Exception:
                pass  # Best effort cleanup

        existing.filename = safe_filename
        existing.raw_text = parsed.get("raw_text", "")
        existing.parsed_name = parsed.get("name", "")
        existing.parsed_email = parsed.get("email", "")
        existing.parsed_phone = parsed.get("phone", "")
        existing.parsed_education = json.dumps(parsed.get("education", []))
        existing.parsed_experience = json.dumps(parsed.get("experience", []))
        existing.parsed_skills = json.dumps(parsed.get("skills", []))
        existing.parsed_projects = json.dumps(parsed.get("projects", []))
        existing.parsed_certifications = json.dumps(parsed.get("certifications", []))
        resume = existing
    else:
        resume = Resume(
            user_id=user.id,
            filename=safe_filename,
            raw_text=parsed.get("raw_text", ""),
            parsed_name=parsed.get("name", ""),
            parsed_email=parsed.get("email", ""),
            parsed_phone=parsed.get("phone", ""),
            parsed_education=json.dumps(parsed.get("education", [])),
            parsed_experience=json.dumps(parsed.get("experience", [])),
            parsed_skills=json.dumps(parsed.get("skills", [])),
            parsed_projects=json.dumps(parsed.get("projects", [])),
            parsed_certifications=json.dumps(parsed.get("certifications", [])),
        )
        db.add(resume)

    db.commit()
    db.refresh(resume)

    # Auto-populate profile skills
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile and parsed.get("skills"):
        for skill_name in parsed["skills"][:20]:
            existing_skill = db.query(Skill).filter(
                Skill.profile_id == profile.id,
                Skill.name.ilike(skill_name)
            ).first()
            if not existing_skill:
                db.add(Skill(profile_id=profile.id, name=skill_name, level="intermediate", category="technical"))
    db.commit()

    return {
        "message": "Resume uploaded and parsed successfully",
        "resume": {
            "id": resume.id,
            "filename": resume.filename,
            "parsed_name": resume.parsed_name,
            "parsed_email": resume.parsed_email,
            "parsed_phone": resume.parsed_phone,
            "parsed_skills": json.loads(resume.parsed_skills) if resume.parsed_skills else [],
            "parsed_education": json.loads(resume.parsed_education) if resume.parsed_education else [],
            "parsed_experience": json.loads(resume.parsed_experience) if resume.parsed_experience else [],
            "parsed_projects": json.loads(resume.parsed_projects) if resume.parsed_projects else [],
            "parsed_certifications": json.loads(resume.parsed_certifications) if resume.parsed_certifications else [],
        },
    }


@router.get("/resume")
def get_resume(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if not resume:
        return {"resume": None}

    return {
        "resume": {
            "id": resume.id,
            "filename": resume.filename,
            "parsed_name": resume.parsed_name,
            "parsed_email": resume.parsed_email,
            "parsed_phone": resume.parsed_phone,
            "parsed_skills": json.loads(resume.parsed_skills) if resume.parsed_skills else [],
            "parsed_education": json.loads(resume.parsed_education) if resume.parsed_education else [],
            "parsed_experience": json.loads(resume.parsed_experience) if resume.parsed_experience else [],
            "parsed_projects": json.loads(resume.parsed_projects) if resume.parsed_projects else [],
            "parsed_certifications": json.loads(resume.parsed_certifications) if resume.parsed_certifications else [],
            "uploaded_at": resume.uploaded_at.isoformat(),
        }
    }


@router.delete("/resume")
def delete_resume(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user's resume and uploaded file."""
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")

    # Delete file from disk
    file_path = os.path.join(UPLOAD_DIR, resume.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted"}
