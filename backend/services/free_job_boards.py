"""
Free supplemental job-board APIs — add results alongside JSearch.

Why: JSearch (paid, per-request) is flaky under load, rate-limited, and has
thin coverage for some queries (internships, niche hardware roles, India).
Remotive and Jobicy are free community job boards with no key and no quota,
so they can fill gaps at zero cost. Both require attribution in the UI
("via Remotive" / "via Jobicy") and link back to the original listing.

Design:
- httpx with timeout + one retry (the JSearch empty-error lesson applied)
- 24h Redis cache (falls back to in-memory) — these boards update ~daily
- Normalized to the same shape as jsearch_service._normalize_job so the
  rest of the app (cards, detail, save) treats all sources identically
- Salaries from these boards are almost always USD annual; tagged with
  currency so the frontend renders $ correctly instead of ₹
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("rolio.external_jobs")

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
HTTP_TIMEOUT = 10.0
RETRIES = 1  # one retry on failure (JSearch upstream is flaky; these can be too)

CACHE_TTL = 86400  # 24h — these boards update ~daily; zero cost to cache long

_redis = None
try:
    from database.connection import get_redis
    _redis = get_redis()
except Exception:
    _redis = None

_memory_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_key(prefix: str, raw: str) -> str:
    return f"{prefix}:{hashlib.md5(raw.lower().encode()).hexdigest()}"


def _cache_get(key: str) -> Optional[list[dict]]:
    if _redis:
        try:
            raw = _redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    entry = _memory_cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, jobs: list[dict]) -> None:
    if _redis:
        try:
            _redis.setex(key, CACHE_TTL, json.dumps(jobs))
            return
        except Exception:
            pass
    _memory_cache[key] = (time.time(), jobs)


async def _fetch_json(url: str, params: dict) -> Optional[dict]:
    """GET JSON with timeout + one retry. Returns None on failure."""
    import httpx
    for attempt in range(1 + RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("%s returned HTTP %d", url.split("/")[2], resp.status_code)
            return None  # 4xx won't improve on retry
        except Exception as e:
            # Log type — httpx timeout errors stringify to "" (JSearch lesson)
            logger.warning("%s attempt %d failed: %s: %s",
                           url.split("/")[2], attempt + 1, type(e).__name__, str(e)[:120])
            if attempt < RETRIES:
                await asyncio.sleep(0.5)
    return None


# ─── Remotive ────────────────────────────────────────────────────────────────

def _norm_remotive(job: dict) -> dict:
    import re
    desc = job.get("description") or ""
    # Remotive descriptions are HTML — strip tags for display safety
    text = re.sub(r"<[^>]+>", " ", desc)
    text = re.sub(r"\s+", " ", text).strip()
    # Detect experience level from title
    title_l = (job.get("title") or "").lower()
    exp = "mid"
    if "intern" in title_l:
        exp = "intern"
    elif any(w in title_l for w in ("senior", "sr.", "sr ")):
        exp = "senior"
    elif any(w in title_l for w in ("junior", "jr.", "entry", "graduate")):
        exp = "junior"
    elif any(w in title_l for w in ("lead", "principal", "staff", "head of")):
        exp = "lead"
    return {
        "job_id": f"remotive_{job.get('id')}",
        "title": job.get("title", ""),
        "company_name": job.get("company_name", ""),
        "company_logo": job.get("company_logo", ""),
        "company_website": job.get("url", ""),  # listing URL doubles as site link
        "description": text[:4000],
        "location": "Remote",
        "work_type": "remote",
        "employment_type": "full-time",
        "experience_level": exp,
        # Remotive rarely exposes structured salary; salary_raw is a display string
        "salary_min": None,
        "salary_max": None,
        "salary_period": "year",
        "salary_raw": (job.get("salary") or "").strip(),
        "currency": "USD",
        "skills": [t.get("name", "") for t in (job.get("tags") or []) if isinstance(t, dict)][:8],
        "qualifications": [],
        "responsibilities": [],
        "benefits": [],
        "apply_link": job.get("url", ""),
        "posted_at": (job.get("publication_date") or "").replace(" ", "T") or None,
        "source": "remotive",
        "publisher": "Remotive",
    }


async def search_remotive(query: str, limit: int = 10) -> list[dict]:
    """Search Remotive's free remote-jobs API. Returns [] on any failure."""
    key = _cache_key("rmt", f"{query}:{limit}")
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = await _fetch_json(REMOTIVE_URL, {"search": query, "limit": min(limit, 20)})
    if not data:
        return []
    jobs = [_norm_remotive(j) for j in (data.get("jobs") or [])]
    _cache_set(key, jobs)
    logger.info("Remotive: %d results for '%s'", len(jobs), query[:50])
    return jobs


# ─── Jobicy ──────────────────────────────────────────────────────────────────

def _norm_jobicy(job: dict) -> dict:
    import re
    desc = job.get("content") or job.get("excerpt", "") or ""
    text = re.sub(r"<[^>]+>", " ", desc)
    text = re.sub(r"\s+", " ", text).strip()
    title_l = (job.get("jobTitle") or "").lower()
    exp = "mid"
    if "intern" in title_l:
        exp = "intern"
    elif any(w in title_l for w in ("senior", "sr.", "sr ")):
        exp = "senior"
    elif any(w in title_l for w in ("junior", "jr.", "entry", "graduate")):
        exp = "junior"
    elif any(w in title_l for w in ("lead", "principal", "staff", "head of")):
        exp = "lead"
    return {
        "job_id": f"jobicy_{job.get('id')}",
        "title": job.get("jobTitle", ""),
        "company_name": job.get("companyName", ""),
        "company_logo": job.get("companyLogo", ""),
        "company_website": job.get("url", ""),
        "description": text[:4000],
        "location": job.get("jobGeo", "") or "Remote",
        "work_type": "remote",
        "employment_type": "full-time",
        "experience_level": exp,
        "salary_min": None,
        "salary_max": None,
        "salary_period": "year",
        "currency": "USD",
        "skills": [],
        "qualifications": [],
        "responsibilities": [],
        "benefits": [],
        "apply_link": job.get("url", ""),
        "posted_at": (job.get("pubDate") or "") or None,
        "source": "jobicy",
        "publisher": "Jobicy",
    }


async def search_jobicy(query: str, limit: int = 10) -> list[dict]:
    """Search Jobicy's free remote-jobs API. Returns [] on any failure."""
    key = _cache_key("jbc", f"{query}:{limit}")
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = await _fetch_json(JOBICY_URL, {
        "count": min(limit, 50),
        "tag": query,
    })
    if not data:
        return []
    jobs = [_norm_jobicy(j) for j in (data.get("jobs") or [])]
    _cache_set(key, jobs)
    logger.info("Jobicy: %d results for '%s'", len(jobs), query[:50])
    return jobs


# ─── Combined entry point ────────────────────────────────────────────────────

async def search_free_boards(query: str, limit_per_source: int = 8) -> list[dict]:
    """Query both free boards in parallel. Never raises; [] if both fail."""
    if not query or not query.strip():
        return []
    results = await asyncio.gather(
        search_remotive(query, limit_per_source),
        search_jobicy(query, limit_per_source),
        return_exceptions=True,
    )
    jobs: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Free board failed: %s: %s", type(r).__name__, str(r)[:120])
        elif r:
            jobs.extend(r)
    return jobs


def _norm_to_detail(job: dict) -> dict:
    """Map a free-board job into the /api/jobs/{id} detail-response shape
    (same keys the JSearch detail branch returns)."""
    return {
        "id": job.get("job_id", ""),
        "company_id": 0,
        "title": job.get("title", ""),
        "description": job.get("description", ""),
        "requirements": "\n".join(job.get("qualifications", [])),
        "responsibilities": "\n".join(job.get("responsibilities", [])),
        "preferred_qualifications": "",
        "skills_required": json.dumps(job.get("skills", [])),
        "skills_preferred": "",
        "location": job.get("location", "Remote"),
        "work_type": job.get("work_type", "remote"),
        "salary_min": job.get("salary_min") or 0,
        "salary_max": job.get("salary_max") or 0,
        "experience_level": job.get("experience_level", "mid"),
        "employment_type": job.get("employment_type", "full-time"),
        "application_url": job.get("apply_link", ""),
        "posted_at": job.get("posted_at") or "",
        "company_name": job.get("company_name", ""),
        "company_logo": job.get("company_logo", ""),
        "company_industry": "",
        "match_score": 0,
        "is_saved": False,
        "is_applied": False,
        "source": job.get("source", ""),
        "publisher": job.get("publisher", ""),
        "benefits": job.get("benefits", []),
        "salary_currency": job.get("currency", "USD"),
        "salary_raw": job.get("salary_raw") or None,
        "google_link": "",
    }


async def get_free_board_job(job_id: str) -> Optional[dict]:
    """Resolve a remotive_/jobicy_ prefixed ID to a detail dict.

    Tries: (1) any cache (search caches hold full job dicts), then
    (2) a direct re-fetch of the board's API for that listing.
    Returns None if the listing can't be found (expired from board).
    """
    source, _, raw_id = job_id.partition("_")
    if source not in ("remotive", "jobicy") or not raw_id:
        return None

    # 1) Scan caches — search responses already contain the full job
    for prefix in ("rmt:", "jbc:"):
        keys = []
        if _redis:
            try:
                keys = [k.decode() if isinstance(k, bytes) else k
                        for k in _redis.scan_iter(f"{prefix}*")]
            except Exception:
                keys = []
        keys.extend(k for k in _memory_cache if k.startswith(prefix))
        for key in keys:
            jobs = _cache_get(key)
            if not jobs:
                continue
            for job in jobs:
                if job.get("job_id") == job_id:
                    return _norm_to_detail(job)

    # 2) Direct re-fetch — Remotive supports ?id=; Jobicy doesn't, so its
    #    fallback is a broad fetch scanned client-side.
    if source == "remotive":
        data = await _fetch_json(REMOTIVE_URL, {"id": raw_id})
        jobs = (data or {}).get("jobs") or []
        for job in jobs:
            if str(job.get("id")) == raw_id:
                return _norm_to_detail(_norm_remotive(job))
    else:  # jobicy
        data = await _fetch_json(JOBICY_URL, {"count": 50})
        for job in (data or {}).get("jobs") or []:
            if str(job.get("id")) == raw_id:
                return _norm_to_detail(_norm_jobicy(job))
    return None


def normalize_for_unified(job: dict) -> dict:
    """Map a free-board job into the unified-search result shape."""
    return {
        "id": job.get("job_id", ""),
        "jsearch_id": None,
        "title": job.get("title", ""),
        "company_name": job.get("company_name", ""),
        "company_logo": job.get("company_logo", ""),
        "location": job.get("location", "Remote"),
        "work_type": job.get("work_type", "remote"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("currency", "USD"),
        "salary_raw": job.get("salary_raw") or None,
        "experience_level": job.get("experience_level", "mid"),
        "employment_type": job.get("employment_type", "full-time"),
        "skills": job.get("skills", []),
        "match_score": 0,
        "posted_at": job.get("posted_at") or "",
        "is_saved": False,
        "is_applied": False,
        "source": job.get("source", ""),
        "publisher": job.get("publisher", ""),
        "apply_link": job.get("apply_link", ""),
        "google_link": "",
    }
