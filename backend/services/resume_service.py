import os
import re

# Resource-exhaustion guards: crafted documents with enormous page/paragraph
# counts can burn the entire serverless time budget. These caps bound parsing
# work while comfortably exceeding any legitimate resume.
MAX_PDF_PAGES = 60
MAX_DOCX_PARAGRAPHS = 2000
MAX_EXTRACTED_CHARS = 400_000


def parse_resume_text(text: str) -> dict:
    """Parse resume text and extract structured information."""
    result = {
        "name": "",
        "email": "",
        "phone": "",
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
    }

    # Extract email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    if email_match:
        result["email"] = email_match.group(0)

    # Extract phone
    phone_match = re.search(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{7,}', text)
    if phone_match:
        result["phone"] = phone_match.group(0).strip()

    # Extract name (first meaningful line that isn't a section header)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    section_headers = {
        'education', 'experience', 'skills', 'projects', 'certifications',
        'summary', 'objective', 'contact', 'about', 'work experience',
        'work history', 'professional experience', 'technical skills',
    }
    for line in lines[:10]:
        if line.lower() not in section_headers and len(line) > 2 and len(line) < 50:
            if not any(c in line for c in '@#$%^&*'):
                result["name"] = line
                break

    # Extract skills
    skill_keywords = [
        'python', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'node.js', 'express', 'fastapi', 'django', 'flask', 'spring',
        'java', 'c++', 'c#', 'go', 'rust', 'ruby', 'php',
        'html', 'css', 'sql', 'mongodb', 'postgresql', 'mysql', 'redis',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'git', 'linux', 'bash', 'machine learning', 'deep learning',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
        'graphql', 'rest', 'api', 'microservices', 'ci/cd',
        'figma', 'photoshop', 'sketch',
    ]

    text_lower = text.lower()
    found_skills = []
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill.title())
    result["skills"] = list(set(found_skills))

    # Try to extract sections
    sections = re.split(r'\n(?=[A-Z][A-Za-z\s]+(?:\n|$))', text)
    for section in sections:
        section_lower = section.lower().strip()
        if 'experience' in section_lower or 'employment' in section_lower:
            # Try to extract job entries
            entries = re.split(r'\n(?=[A-Z][a-z]+\s)', section)
            for entry in entries[1:4]:  # Take up to 3
                if len(entry.strip()) > 10:
                    result["experience"].append(entry.strip()[:200])
        elif 'education' in section_lower:
            edu_entries = re.split(r'\n(?=[A-Z])', section)
            for entry in edu_entries[1:3]:
                if len(entry.strip()) > 5:
                    result["education"].append(entry.strip()[:200])
        elif 'project' in section_lower:
            proj_entries = re.split(r'\n(?=[A-Z])', section)
            for entry in proj_entries[1:4]:
                if len(entry.strip()) > 10:
                    result["projects"].append(entry.strip()[:200])

    return result


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file (page-count and size bounded)."""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                return "Error reading PDF: document exceeds maximum page count"
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) > MAX_EXTRACTED_CHARS:
                    break
            return text[:MAX_EXTRACTED_CHARS]
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file (paragraph-count and size bounded)."""
    try:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for i, para in enumerate(doc.paragraphs):
            if i >= MAX_DOCX_PARAGRAPHS or len(text) > MAX_EXTRACTED_CHARS:
                break
            text += para.text + "\n"
        return text[:MAX_EXTRACTED_CHARS]
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"


def process_resume(file_path: str) -> dict:
    """Process a resume file and return parsed data."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext in ('.docx', '.doc'):
        raw_text = extract_text_from_docx(file_path)
    else:
        return {"error": f"Unsupported file format: {ext}"}

    if raw_text.startswith("Error"):
        return {"error": raw_text}

    parsed = parse_resume_text(raw_text)
    parsed["raw_text"] = raw_text

    return parsed
