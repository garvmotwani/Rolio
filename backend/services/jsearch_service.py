"""
JSearch API service — fetches real job listings from Google for Jobs via RapidAPI.
Includes caching, rate limiting, and smart deduplication.
"""

import json
import time
import hashlib
import logging
from typing import Optional
from datetime import datetime
from config import JSEARCH_API_KEY

logger = logging.getLogger("rolio.jsearch")

JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com"

# Whether the external paid API is usable. Never exposes the key itself.
JSEARCH_CONFIGURED = bool(JSEARCH_API_KEY)

# In-memory cache (TTL: 30 minutes for search, 24 hours for job details)
_search_cache: dict[str, tuple[float, dict]] = {}
_detail_cache: dict[str, tuple[float, dict]] = {}
SEARCH_CACHE_TTL = 1800  # 30 min
DETAIL_CACHE_TTL = 86400  # 24 hours

# Redis-backed search result cache (bypasses paid JSearch API for identical queries)
# Keys: jsr:{md5_hash} → {data, count, ...}
# TTL: 24 hours — long enough to save API calls, short enough to stay fresh
_JSEARCH_REDIS_TTL = 86400  # 24 hours

try:
    from database.connection import get_redis
    _redis = get_redis()  # eager init — None if Redis unavailable
except Exception:
    _redis = None

logger.info("JSearch Redis cache: %s" % ("enabled" if _redis else "disabled (in-memory fallback)"))

# Per-user rate limiting: max 30 JSearch requests per hour
_user_search_counts: dict[int, list[float]] = {}
JSEARCH_RATE_LIMIT = 30  # per hour
JSEARCH_RATE_WINDOW = 3600  # 1 hour


def _check_rate_limit(user_id: int) -> bool:
    """Returns True if user is within rate limit."""
    now = time.time()
    if user_id not in _user_search_counts:
        _user_search_counts[user_id] = []
    # Prune old entries
    _user_search_counts[user_id] = [
        t for t in _user_search_counts[user_id] if now - t < JSEARCH_RATE_WINDOW
    ]
    if len(_user_search_counts[user_id]) >= JSEARCH_RATE_LIMIT:
        return False
    _user_search_counts[user_id].append(now)
    return True


def _cache_key_search(query: str, page: int, **filters) -> str:
    raw = f"{query}:{page}:{json.dumps(filters, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_key_detail(job_id: str) -> str:
    return hashlib.md5(job_id.encode()).hexdigest()


async def search_jobs(
    query: str,
    page: int = 1,
    num_pages: int = 1,
    location: Optional[str] = None,
    remote_only: bool = False,
    date_posted: Optional[str] = None,
    employment_type: Optional[str] = None,
    min_salary: Optional[int] = None,
    fields: Optional[list[str]] = None,
) -> dict:
    """
    Search for jobs via JSearch API.

    Args:
        query: Search query (job title, skills, keywords)
        page: Page number
        num_pages: Number of pages to return (max 10)
        location: Location filter
        remote_only: Remote jobs only
        date_posted: 'today', '3days', 'week', 'month'
        employment_type: 'FULLTIME', 'PARTTIME', 'CONTRACTOR', 'INTERN'
        min_salary: Minimum salary filter
        fields: Fields to include in response

    Returns:
        dict with 'data' (list of jobs), 'count', 'query'
    """
    if not JSEARCH_API_KEY:
        logger.warning("JSearch API key not configured, returning fallback")
        return _get_fallback_jobs(query, page)

    # Check Redis cache first (long-lived, saves paid API calls)
    cache_key = _cache_key_search(
        query, page, location=location, remote=remote_only,
        date_posted=date_posted, employment_type=employment_type
    )
    if _redis:
        redis_result = _redis.get(f"jsr:{cache_key}")
        if redis_result:
            try:
                data = json.loads(redis_result)
                logger.info("JSearch cache HIT (Redis): %s — %d results", query[:50], data.get("count", 0))
                return data
            except (json.JSONDecodeError, TypeError):
                logger.warning("JSearch Redis cache corrupt, removing key")
                _redis.delete(f"jsr:{cache_key}")

    # Fallback: in-memory cache (30 min TTL)
    if cache_key in _search_cache:
        ts, data = _search_cache[cache_key]
        if time.time() - ts < SEARCH_CACHE_TTL:
            return data

    # Build query params — keep query and location separate for better results
    search_query = query
    if remote_only or (location and location.lower() == "remote"):
        search_query = f"{query} remote"

    params = {
        "query": search_query,
        "page": str(page),
        "num_pages": str(min(num_pages, 10)),
    }

    if date_posted:
        params["date_posted"] = date_posted
    if employment_type:
        params["employment_type"] = employment_type
    # Note: JSearch v2 doesn't have a separate location param,
    # but we can add locality info to the query if location is specified
    # and not already in the query
    if location and location.lower() != "remote" and location.lower() not in search_query.lower():
        # Append location to query for better geo-targeting
        search_query = f"{search_query} {location}"
        params["query"] = search_query

    # Note: v2 API does not support fields param — all fields returned automatically

    try:
        import httpx
        last_error: Optional[Exception] = None
        for attempt in range(2):  # one retry — upstream is intermittently slow
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{JSEARCH_BASE_URL}/search-v2",
                        headers={
                            "X-RapidAPI-Key": JSEARCH_API_KEY,
                            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                        },
                        params=params,
                        timeout=15.0,
                    )

                if resp.status_code == 200:
                    raw = resp.json()
                    result = _normalize_search_results(raw, query)
                    _search_cache[cache_key] = (time.time(), result)

                    # Persist to Redis for 24h — avoids future paid API calls for same query
                    if _redis:
                        try:
                            _redis.setex(f"jsr:{cache_key}", _JSEARCH_REDIS_TTL, json.dumps(result))
                            logger.info("JSearch cache SET (Redis): %s — %d results", query[:50], result.get("count", 0))
                        except Exception as e:
                            logger.warning("JSearch Redis write failed: %s", str(e)[:100])

                    return result
                else:
                    # 4xx won't improve on retry — bail immediately
                    logger.warning("JSearch API error %d for query '%s'", resp.status_code, query[:50])
                    break
            except Exception as e:
                # httpx timeout errors stringify to "" — always log the type name
                last_error = e
                logger.warning("JSearch attempt %d failed: %s: %s",
                               attempt + 1, type(e).__name__, str(e)[:200])
                if attempt == 0:
                    import asyncio as _asyncio
                    await _asyncio.sleep(0.8)
        if last_error:
            logger.error("JSearch request failed after retry: %s: %s",
                         type(last_error).__name__, str(last_error)[:200])
    except Exception as e:
        logger.error("JSearch request failed: %s: %s", type(e).__name__, str(e)[:200])

    return _get_fallback_jobs(query, page)


async def get_job_details(job_id: str) -> Optional[dict]:
    """Get detailed job info by JSearch job_id.

    Resilience: if the paid detail endpoint is slow/failing, fall back to
    the full job dict already returned by (cached) search results — the
    search payload contains everything the detail page renders.
    """
    cache_key = _cache_key_detail(job_id)
    if cache_key in _detail_cache:
        ts, data = _detail_cache[cache_key]
        if time.time() - ts < DETAIL_CACHE_TTL:
            return data

    if JSEARCH_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{JSEARCH_BASE_URL}/job-details",
                    headers={
                        "X-RapidAPI-Key": JSEARCH_API_KEY,
                        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                    },
                    params={"job_id": job_id},
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    raw = resp.json()
                    data_block = raw.get("data", [])
                    # data can be a list or dict with 'jobs' key
                    items = data_block if isinstance(data_block, list) else data_block.get("jobs", []) if isinstance(data_block, dict) else []
                    if items:
                        detail = _normalize_job_detail(items[0])
                        # The details endpoint sometimes omits job_apply_link even
                        # when the search response had it — patch from search cache.
                        if not detail.get("apply_link"):
                            cached = _find_job_in_search_caches(job_id)
                            if cached and cached.get("apply_link"):
                                detail["apply_link"] = cached["apply_link"]
                        _detail_cache[cache_key] = (time.time(), detail)
                        return detail
                else:
                    logger.warning("JSearch detail HTTP %d for job %s...", resp.status_code, job_id[:20])
        except Exception as e:
            # Log the exception TYPE — httpx timeout errors stringify to ""
            logger.error("JSearch detail error: %s: %s", type(e).__name__, str(e)[:200])

    # Fallback: reuse cached search results (24h Redis / 30min memory).
    # Avoids a 404 dead-end for the user and saves a paid retry.
    cached = _find_job_in_search_caches(job_id)
    if cached:
        logger.info("JSearch detail served from search cache for job %s...", job_id[:20])
        _detail_cache[cache_key] = (time.time(), cached)
        return cached

    return None


def _find_job_in_search_caches(job_id: str) -> Optional[dict]:
    """Scan cached search results for a specific job_id."""
    # In-memory search cache
    for _ts, result in list(_search_cache.values()):
        for job in result.get("data", []):
            if job.get("job_id") == job_id:
                return job
    # Redis search cache
    if _redis:
        try:
            for key in _redis.scan_iter("jsr:*"):
                try:
                    result = json.loads(_redis.get(key))
                    for job in result.get("data", []):
                        if job.get("job_id") == job_id:
                            return job
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue
        except Exception as e:
            logger.warning("JSearch cache scan failed: %s: %s", type(e).__name__, str(e)[:100])
    return None


async def search_company_jobs(company: str, page: int = 1) -> dict:
    """Search for jobs at a specific company."""
    return await search_jobs(f"at {company}", page=page)


async def get_similar_jobs(job_id: str) -> list[dict]:
    """Get similar jobs based on a job_id."""
    if not JSEARCH_API_KEY:
        return []

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{JSEARCH_BASE_URL}/job-details",
                headers={
                    "X-RapidAPI-Key": JSEARCH_API_KEY,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
                params={"job_id": job_id},
                timeout=20.0,
            )

            if resp.status_code == 200:
                raw = resp.json()
                data_block = raw.get("data", [])
                items = data_block if isinstance(data_block, list) else data_block.get("jobs", []) if isinstance(data_block, dict) else []
                if items:
                    detail = items[0]
                    title = detail.get("job_title", "")
                    if title:
                        similar = await search_jobs(title, page=1, num_pages=1)
                        return similar.get("data", [])[:5]
    except Exception as e:
        logger.error("JSearch similar jobs error: %s: %s", type(e).__name__, str(e)[:200])

    return []


def _normalize_search_results(raw: dict, query: str) -> dict:
    """Normalize JSearch API v2 response to our format."""
    # v2 wraps jobs in data.jobs; fallback to data as list for compat
    data_block = raw.get("data", {})
    if isinstance(data_block, dict):
        raw_jobs = data_block.get("jobs", [])
        result_count = data_block.get("total_count", len(raw_jobs))
        result_page = data_block.get("page", 1)
        result_pages = data_block.get("num_pages", 1)
    else:
        raw_jobs = data_block if isinstance(data_block, list) else []
        result_count = raw.get("count", len(raw_jobs))
        result_page = raw.get("page", 1)
        result_pages = raw.get("num_pages", 1)

    jobs = [_normalize_job(item) for item in raw_jobs]

    return {
        "data": jobs,
        "count": result_count,
        "page": result_page,
        "num_pages": result_pages,
        "query": query,
        "source": "jsearch",
    }


def _normalize_job(item: dict) -> dict:
    """Normalize a single JSearch job to our format."""
    # Parse skills from description and highlights
    skills = item.get("job_required_skills") or []
    if not skills:
        # Extract from description
        desc = (item.get("job_description") or "").lower()
        common_skills = [
            "python", "javascript", "typescript", "react", "node.js", "node",
            "java", "c++", "c#", "go", "rust", "ruby", "php", "swift",
            "html", "css", "sql", "nosql", "mongodb", "postgresql", "mysql",
            "aws", "gcp", "azure", "docker", "kubernetes", "k8s",
            "git", "ci/cd", "linux", "agile", "scrum",
            "machine learning", "ml", "ai", "data science", "tensorflow", "pytorch",
            "vue", "angular", "svelte", "next.js", "nextjs", "express", "django", "flask", "fastapi",
            "rest api", "graphql", "grpc", "microservices",
            "figma", "sketch", "photoshop", "illustrator",
            "salesforce", "hubspot", "jira", "confluence",
            "communication", "leadership", "teamwork", "problem solving",
        ]
        found = [s for s in common_skills if s in desc]
        skills = found[:8] if found else []

    # Parse salary
    salary_min = item.get("job_min_salary")
    salary_max = item.get("job_max_salary")
    if salary_min:
        salary_min = int(salary_min)
    if salary_max:
        salary_max = int(salary_max)

    # Parse work type
    emp_type = (item.get("job_employment_type") or "").upper()
    work_type = "hybrid"
    desc_lower = (item.get("job_description") or "").lower()
    title_lower = (item.get("job_title") or "").lower()
    if "remote" in title_lower or "remote" in desc_lower[:500]:
        work_type = "remote"
    elif "on-site" in desc_lower[:500] or "onsite" in desc_lower[:500]:
        work_type = "on-site"

    # Parse experience level
    exp_level = "mid"
    title = (item.get("job_title") or "").lower()
    if "senior" in title or "sr." in title or "sr " in title:
        exp_level = "senior"
    elif "junior" in title or "jr." in title or "jr " in title or "entry" in title:
        exp_level = "junior"
    elif "lead" in title or "principal" in title or "staff" in title:
        exp_level = "lead"
    elif "intern" in title:
        exp_level = "intern"
    elif "director" in title or "vp" in title or "head of" in title:
        exp_level = "executive"

    # Parse location
    city = item.get("job_city") or ""
    state = item.get("job_state") or ""
    country = item.get("job_country") or ""
    location = ", ".join(filter(None, [city, state, country])) or "Remote"

    # Employment type mapping
    emp_type_map = {
        "FULLTIME": "full-time",
        "PARTTIME": "part-time",
        "CONTRACTOR": "contract",
        "INTERN": "internship",
    }

    # Highlights (key qualifications, responsibilities)
    highlights = item.get("job_highlights") or {}
    qualifications = highlights.get("Qualifications") or []
    responsibilities = highlights.get("Responsibilities") or []
    benefits = highlights.get("Benefits") or []

    return {
        "job_id": item.get("job_id", ""),
        "title": item.get("job_title", ""),
        "company_name": item.get("employer_name", ""),
        "company_logo": item.get("employer_logo") or "",
        "company_website": item.get("employer_website") or "",
        "publisher": item.get("job_publisher", ""),
        "description": item.get("job_description", ""),
        "location": location,
        "work_type": work_type,
        "employment_type": emp_type_map.get(emp_type, "full-time"),
        "experience_level": exp_level,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_period": item.get("job_salary_period") or "year",
        "skills": skills,
        "qualifications": qualifications,
        "responsibilities": responsibilities,
        "benefits": benefits,
        "apply_link": item.get("job_apply_link") or "",
        "google_link": item.get("job_google_link") or "",
        "posted_at": _parse_timestamp(item.get("job_posting_timestamp")),
        "source": "jsearch",
    }


def _normalize_job_detail(item: dict) -> dict:
    """Normalize detailed job response."""
    job = _normalize_job(item)
    job.update({
        "job_onet_soc": item.get("job_ONET_SOC") or "",
        "job_onet_group": item.get("job_ONET_SOC_group") or "",
        "employer_company_type": item.get("employer_company_type") or "",
        "is_direct_apply": item.get("job_apply_is_direct", False),
        "availability": item.get("job_availability", ""),
    })
    return job


def _parse_timestamp(ts: Optional[str]) -> str:
    """Parse ISO timestamp to ISO format."""
    if not ts:
        return datetime.utcnow().isoformat()
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.isoformat()
    except (ValueError, TypeError):
        return datetime.utcnow().isoformat()


def _get_fallback_jobs(query: str, page: int = 1) -> dict:
    """Fallback jobs when JSearch API is not available."""
    return {
        "data": [],
        "count": 0,
        "page": page,
        "num_pages": 1,
        "query": query,
        "source": "fallback",
    }


def get_search_summary(query: str, results: dict) -> str:
    """Generate a brief summary of search results for display."""
    count = results.get("count", 0)
    source = results.get("source", "database")

    if count == 0:
        return f"No jobs found for '{query}'"
    elif source == "jsearch":
        return f"Found {count} real jobs from Google for Jobs"
    else:
        return f"Found {count} jobs in our database"
