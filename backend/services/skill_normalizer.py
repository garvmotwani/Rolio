"""
Skill normalization — canonical names for fuzzy skill matching.

Job boards write the same skill many ways ("React.js", "ReactJS", "react.js").
The match engine must treat those as one skill. This module maps raw strings
to canonical names before any set comparison happens.
"""

from typing import Dict, List, Set

# alias → canonical form (all keys/values lowercase)
ALIASES: Dict[str, str] = {
    # JavaScript family
    "js": "javascript", "javascript": "javascript", "ecmascript": "javascript",
    "es6": "javascript", "es2015": "javascript", "vanilla js": "javascript",
    "javascript es6": "javascript",
    # TypeScript
    "ts": "typescript",
    # React family
    "react": "react", "react.js": "react", "reactjs": "react", "react js": "react",
    "react.js (next.js)": "react",
    # Next
    "next": "next.js", "nextjs": "next.js", "next.js": "next.js", "next js": "next.js",
    # Vue / Angular
    "vue": "vue.js", "vue.js": "vue.js", "vuejs": "vue.js",
    "angular": "angular", "angularjs": "angular", "angular.js": "angular",
    # Node family
    "node": "node.js", "node.js": "node.js", "nodejs": "node.js", "node js": "node.js",
    # Python web
    "fastapi": "fastapi", "fast api": "fastapi",
    "flask": "flask", "django": "django", "django rest framework": "django",
    "drf": "django",
    # Databases
    "postgres": "postgresql", "postgresql": "postgresql", "psql": "postgresql",
    "postgre": "postgresql",
    "mysql": "mysql", "mariadb": "mysql",
    "mongo": "mongodb", "mongodb": "mongodb", "mongoose": "mongodb",
    "sqlite": "sqlite", "sqlite3": "sqlite",
    "redis": "redis",
    "mssql": "sql server", "sql server": "sql server",
    "oracle db": "oracle", "oracle": "oracle",
    # SQL general
    "sql": "sql",
    # Cloud
    "aws": "aws", "amazon web services": "aws",
    "gcp": "google cloud", "google cloud platform": "google cloud",
    "google cloud": "google cloud",
    "azure": "azure", "microsoft azure": "azure",
    # DevOps
    "k8s": "kubernetes", "kubernetes": "kubernetes",
    "docker": "docker", "containerization": "docker",
    "ci/cd": "ci/cd", "cicd": "ci/cd", "ci cd": "ci/cd",
    "jenkins": "jenkins", "github actions": "github actions",
    "terraform": "terraform", "ansible": "ansible",
    "linux": "linux", "unix": "linux", "bash": "bash", "shell scripting": "bash",
    # Python ecosystem
    "python": "python", "python3": "python",
    "pandas": "pandas", "numpy": "numpy", "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "pytorch": "pytorch", "tensorflow": "tensorflow", "tf": "tensorflow",
    "keras": "tensorflow",
    "ml": "machine learning", "machine learning": "machine learning",
    "machine-learning": "machine learning",
    "ai": "artificial intelligence", "artificial intelligence": "artificial intelligence",
    "deep learning": "deep learning", "dl": "deep learning",
    "nlp": "natural language processing", "natural language processing": "natural language processing",
    "llm": "llm", "llms": "llm", "genai": "generative ai", "generative ai": "generative ai",
    "data science": "data science", "datascience": "data science",
    "data analysis": "data analysis", "data analytics": "data analysis",
    "data visualization": "data visualization",
    "power bi": "power bi", "powerbi": "power bi",
    "tableau": "tableau",
    "excel": "excel", "advanced excel": "excel",
    # Web general
    "html": "html", "html5": "html",
    "css": "css", "css3": "css",
    "scss": "sass", "sass": "sass",
    "tailwind": "tailwind css", "tailwindcss": "tailwind css", "tailwind css": "tailwind css",
    "bootstrap": "bootstrap", "material ui": "material ui", "mui": "material ui",
    # APIs & tools
    "rest": "rest apis", "rest api": "rest apis", "rest apis": "rest apis",
    "restful api": "rest apis", "restful apis": "rest apis", "api development": "rest apis",
    "graphql": "graphql",
    "grpc": "grpc",
    "git": "git", "github": "git", "gitlab": "git", "version control": "git",
    "gitlab ci": "gitlab",
    "jira": "jira",
    "postman": "postman",
    # Languages
    "java": "java",
    "c": "c", "c++": "c++", "cpp": "c++", "c plus plus": "c++",
    "c#": "c#", "csharp": "c#", "cs": "c#",
    ".net": ".net", "dotnet": ".net", "asp.net": ".net",
    "php": "php", "laravel": "laravel",
    "ruby": "ruby", "ruby on rails": "ruby on rails", "rails": "ruby on rails",
    "go": "go", "golang": "go",
    "rust": "rust",
    "kotlin": "kotlin", "swift": "swift",
    "scala": "scala",
    "r": "r", "r language": "r",
    "matlab": "matlab",
    "dart": "dart", "flutter": "flutter",
    # Mobile
    "android": "android", "android dev": "android",
    "ios": "ios", "swiftui": "swift",
    "react native": "react native", "react-native": "react native",
    # Concepts
    "oop": "object-oriented programming", "object oriented programming": "object-oriented programming",
    "dsa": "data structures", "data structures": "data structures",
    "data structures and algorithms": "data structures",
    "algorithms": "data structures",
    "dbms": "databases", "database management": "databases", "databases": "databases",
    "os": "operating systems", "operating systems": "operating systems",
    "computer networks": "networking", "networking": "networking", "networks": "networking",
    "cn": "networking",
    "microservices": "microservices",
    "system design": "system design",
    "agile": "agile", "scrum": "agile", "agile/scrum": "agile",
    "unit testing": "testing", "testing": "testing", "pytest": "testing",
    "jest": "testing", "junit": "testing", "selenium": "testing",
    "debugging": "debugging",
    "problem solving": "problem solving",
    "communication": "communication",
    "teamwork": "teamwork", "team collaboration": "teamwork",
    "leadership": "leadership",
    "time management": "time management",
    # VLSI / ECE
    "verilog": "verilog", "systemverilog": "systemverilog", "system verilog": "systemverilog",
    "vhdl": "vhdl",
    "vlsi": "vlsi", "vlsi design": "vlsi",
    "rtl": "rtl design", "rtl design": "rtl design",
    "fpga": "fpga",
    "cadence": "cadence", "synopsys": "synopsys", "vivado": "vivado",
    "xilinx": "vivado",
    "embedded": "embedded systems", "embedded c": "embedded systems",
    "embedded systems": "embedded systems", "embedded systems programming": "embedded systems",
    "iot": "iot", "internet of things": "iot",
    # Design
    "figma": "figma", "adobe xd": "figma",
    "ui/ux": "ui/ux design", "ui ux": "ui/ux design", "ux design": "ui/ux design",
    "ui design": "ui/ux design", "ui/ux design": "ui/ux design",
    "graphic design": "graphic design",
    "photoshop": "photoshop", "illustrator": "illustrator",
    "canva": "canva",
    # Business / other
    "seo": "seo", "digital marketing": "digital marketing",
    "content writing": "content writing", "copywriting": "content writing",
    "marketing": "marketing",
    "financial modeling": "financial modeling",
    "accounting": "accounting",
    "hr": "human resources", "human resources": "human resources",
    "recruitment": "recruitment",
    "sales": "sales", "business development": "business development",
    "project management": "project management", "product management": "product management",
    "supply chain": "supply chain", "operations": "operations",
}

# Extra tokens stripped before lookup (e.g. "python (pandas)" → "python")
_STRIP_CHARS = "().,/·-–—:;|!"


def canonical(raw: str) -> str:
    """Map a raw skill string to its canonical lowercase name."""
    if not raw:
        return ""
    s = raw.strip().lower()
    # try full string first, then progressively simpler variants
    if s in ALIASES:
        return ALIASES[s]
    # strip punctuation wrappers: "react.js" already handled, but "c++ (11)" etc.
    cleaned = s.strip(_STRIP_CHARS).strip()
    if cleaned in ALIASES:
        return ALIASES[cleaned]
    # try without common suffixes
    for suffix in (" programming", " development", " engineer", " skills"):
        if cleaned.endswith(suffix) and cleaned[: -len(suffix)] in ALIASES:
            return ALIASES[cleaned[: -len(suffix)]]
    return cleaned or s


def normalize_skill_list(raw_skills) -> List[str]:
    """Canonicalize a list of skills, preserving order, deduplicating."""
    seen: Set[str] = set()
    out: List[str] = []
    for s in raw_skills or []:
        c = canonical(str(s))
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def overlap_sets(profile_skills, job_skills) -> tuple:
    """Return (matched, missing, partial) canonical sets plus partial profile skills."""
    p = normalize_skill_list(profile_skills)
    j = normalize_skill_list(job_skills)
    p_set, j_set = set(p), set(j)

    matched = j_set & p_set
    missing = j_set - p_set

    partial = set()
    matched_p = set()
    for ps in p_set:
        for js in j_set:
            if ps == js:
                matched_p.add(ps)
            elif (ps in js or js in ps) and len(ps) >= 3 and len(js) >= 3:
                partial.add(ps)
    partial -= matched_p
    return matched, missing, partial
