"""
Deterministic natural-language search parser.

Turns queries like "backend internships in Bangalore using Python" into
structured filters the search engine already understands. No LLM, no cost,
fully testable — covers the most common phrasings:

  - work type:   internship / part time / full time / contract / freelance
  - seniority:   fresher / entry level / junior / senior / lead / intern
  - remote:      remote / wfh / work from home / hybrid
  - location:    "in X" / "near X" / known Indian cities
  - keywords:    whatever remains is the search query (role/skills)

Deterministic and idempotent: parse("...") always yields the same result,
so it is safe to run on both the local search path and the external (paid)
leg without cache-key instability.
"""

import re
from typing import Optional

# ── Known Indian cities (most common search targets for this product) ──
_CITIES = [
    "bangalore", "bengaluru", "mumbai", "delhi", "new delhi", "noida",
    "gurgaon", "gurugram", "hyderabad", "pune", "chennai", "kolkata",
    "ahmedabad", "jaipur", "indore", "chandigarh", "kochi", "coimbatore",
    "bhubaneswar", "lucknow", "nagpur", "surat", "vadodara", "bhopal",
    "thiruvananthapuram", "visakhapatnam", "mangalore", "mysore",
    "dehradun", "guwahati", "raipur", "ranchi", "patna", "goa", "remote",
]

# Words that map to structured filters (removed from the keyword query)
_WORK_TYPE_PATTERNS = [
    (r"\binternships?\b|\bintern\s", "internship"),
    (r"\bpart[- ]?time\b", "part-time"),
    (r"\bfull[- ]?time\b", "full-time"),
    (r"\bcontract(ual)?\b", "contract"),
    (r"\bfreelance\b", "contract"),
]

_SENIORITY_PATTERNS = [
    (r"\bfreshers?\b|\bentry[- ]level\b|\bgraduate\b", "entry"),
    (r"\bjuniors?\b", "junior"),
    (r"\bseniors?\b", "senior"),
    (r"\bleads?\b|\blead\b", "lead"),
    (r"\bmanagers?\b", "lead"),
]

_REMOTE_PATTERN = r"\bremote\b|\bwfh\b|\bwork from home\b|\bhybrid\b"


def parse_query(query: str) -> dict:
    """Parse a natural-language job search query into structured filters.

    Returns a dict with keys: location, work_type, experience_level,
    remote, keywords, parsed (list of human-readable what-was-extracted).
    """
    text = (query or "").strip()
    if not text:
        return {"location": "", "work_type": None, "experience_level": None,
                "remote": False, "keywords": "", "parsed": []}

    original = text
    parsed: list = []
    lowered = text.lower()

    # ── Location: "in X", "near X", "X city" or bare known city ──
    location = ""
    # "in bangalore", "near pune", "jobs in new delhi"
    m = re.search(
        r"\b(?:in|near|at|around)\s+([a-z][a-z\s]{2,30}?)(?=\b(?:using|with|for|that|remote|internships?\b|jobs?\b|$))",
        lowered,
    )
    if m:
        candidate = m.group(1).strip()
        if candidate in _CITIES:
            location = candidate
    if not location:
        # bare city mention: "bangalore python jobs"
        for city in _CITIES:
            if re.search(rf"\b{re.escape(city)}\b", lowered):
                location = city
                break
    if location:
        parsed.append(("location", location.title()))
        # remove the location phrase from the keyword query
        if m and m.group(1).strip() == location:
            text = re.sub(
                rf"\b(?:in|near|at|around)\s+{re.escape(location)}\b",
                " ", text, flags=re.IGNORECASE)
        text = re.sub(rf"\b{re.escape(location)}\b", " ", text, flags=re.IGNORECASE)

    # ── Remote ──
    remote = False
    if re.search(_REMOTE_PATTERN, lowered):
        remote = True
        parsed.append(("remote", "yes"))
        if not location or location == "remote":
            location = "remote" if "remote" in lowered else location
        text = re.sub(_REMOTE_PATTERN, " ", text, flags=re.IGNORECASE)

    # ── Work type ──
    work_type: Optional[str] = None
    for pat, wt in _WORK_TYPE_PATTERNS:
        if re.search(pat, lowered):
            work_type = wt
            parsed.append(("work type", wt))
            text = re.sub(pat, " ", text, flags=re.IGNORECASE)
            break

    # ── Seniority ──
    experience_level: Optional[str] = None
    for pat, lvl in _SENIORITY_PATTERNS:
        if re.search(pat, lowered):
            experience_level = lvl
            parsed.append(("experience", lvl))
            text = re.sub(pat, " ", text, flags=re.IGNORECASE)
            break

    # ── Keywords: collapse leftover whitespace ──
    keywords = re.sub(r"\s+", " ", text).strip(" ,.-")

    return {
        "location": location,
        "work_type": work_type,
        "experience_level": experience_level,
        "remote": remote,
        "keywords": keywords,
        "parsed": parsed,
        "original": original,
    }


def merged_query_location(query: str, explicit_location: str) -> str:
    """Effective location: explicit filter wins over NL-extracted location."""
    return (explicit_location or "").strip() or parse_query(query).get("location", "")
