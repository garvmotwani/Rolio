"""
Unified AI provider — Nemotron 3 Super/Nano via NVIDIA NIM.
Token-efficient: thinking disabled, compact prompts, caching, model routing, retry.

Token budget per use case:
  Chat:         ~150 in + 350 out = ~500 total
  Match:        ~120 in + 250 out = ~370 total
  Career advice: ~100 in + 300 out = ~400 total
  Resume:       ~300 in + 800 out = ~1100 total
  App tips:     ~80 in + 200 out = ~280 total
  Improve text:  ~40 in + 60 out  = ~100 total
"""

import time
import asyncio
import hashlib
import logging
from typing import Optional
from config import (
    NEMOTRON_API_KEY, GEMINI_API_KEY,
    NEMOTRON_MODEL, NEMOTRON_NANO_MODEL, GEMINI_MODEL,
)

logger = logging.getLogger("rolio.ai")

# ─── Model routing ──────────────────────────────────────────────────
MODEL_MAP = {
    "super": NEMOTRON_MODEL,      # nvidia/nemotron-3-super-120b-a12b
    "nano": NEMOTRON_NANO_MODEL,  # nvidia/nemotron-3-nano-30b-a3b
}

# ─── Cache ──────────────────────────────────────────────────────────
_cache: dict[str, tuple[float, str]] = {}
CACHE_TTL = 600  # 10 min


def _cache_key(prompt: str, system: str, provider: str) -> str:
    raw = f"{provider}:{system[:100]}:{prompt[:200]}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[str]:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None


def _set_cache(key: str, val: str):
    if len(_cache) > 200:
        oldest = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest]
    _cache[key] = (time.time(), val)


# ─── Per-user rate limiting ──────────────────────────────────────
_ai_rate_limits: dict[int, list[float]] = {}
AI_RATE_LIMIT = 20  # max AI requests per hour per user
AI_RATE_WINDOW = 3600


def _check_ai_rate_limit(user_id: int) -> bool:
    """Returns True if user is within AI rate limit."""
    now = time.time()
    if user_id not in _ai_rate_limits:
        _ai_rate_limits[user_id] = []
    _ai_rate_limits[user_id] = [
        t for t in _ai_rate_limits[user_id] if now - t < AI_RATE_WINDOW
    ]
    if len(_ai_rate_limits[user_id]) >= AI_RATE_LIMIT:
        return False
    _ai_rate_limits[user_id].append(now)
    return True


# Prompt size cap (tokens, approximate: 1 token ≈ 4 chars)
PROMPT_MAX_CHARS = 4000  # ~1000 tokens

def _truncate_prompt(prompt: str) -> str:
    """Cap prompt length to prevent token waste."""
    if len(prompt) > PROMPT_MAX_CHARS:
        logger.warning("Prompt truncated from %d to %d chars", len(prompt), PROMPT_MAX_CHARS)
        return prompt[:PROMPT_MAX_CHARS]
    return prompt


# ─── Nemotron (NVIDIA NIM) ──────────────────────────────────────────
async def _call_nemotron(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
    tier: str = "super",
    retries: int = 2,
    user_id: int = 0,
) -> str:
    """
    Call Nemotron 3 via NVIDIA NIM with retry logic.
    tier: "super" for complex tasks, "nano" for fast/simple tasks.
    Thinking is disabled to save tokens.
    """
    if not NEMOTRON_API_KEY:
        return ""

    # Per-user rate limit
    if user_id and not _check_ai_rate_limit(user_id):
        logger.warning("AI rate limit exceeded for user %d", user_id)
        return "AI rate limit exceeded. Please try again later."

    model = MODEL_MAP.get(tier, NEMOTRON_MODEL)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    for attempt in range(retries + 1):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {NEMOTRON_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=45.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    if usage:
                        pt = usage.get("prompt_tokens", "?")
                        ct = usage.get("completion_tokens", "?")
                        logger.info("[Nemotron %s] %s in / %s out", tier, pt, ct)
                    content = _strip_thinking(content)
                    return content.strip()
                elif resp.status_code in (503, 429, 502):
                    # Rate limited or overloaded — retry with backoff
                    if attempt < retries:
                        wait = (attempt + 1) * 2  # 2s, 4s
                        logger.warning("Nemotron %d, retry in %ds...", resp.status_code, wait)
                        await asyncio.sleep(wait)
                        continue
                    logger.error("Nemotron %d after %d retries", resp.status_code, retries)
                    return ""
                else:
                    logger.error("Nemotron %d: %s", resp.status_code, resp.text[:200])
                    return ""
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep((attempt + 1) * 2)
                continue
            logger.error("Nemotron error: %s", str(e)[:200])
    return ""


def _strip_thinking(text: str) -> str:
    """Remove any <think>...</think> tags if the model outputs them anyway."""
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


# ─── Gemini (fallback) ──────────────────────────────────────────────
async def _call_gemini(prompt: str, system: str = "", max_tokens: int = 500) -> str:
    """Call Gemini API. Fallback when Nemotron unavailable."""
    if not GEMINI_API_KEY:
        return ""

    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": system}]})
        contents.append({"role": "model", "parts": [{"text": "OK"}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": max_tokens,
                        "topP": 0.9,
                    },
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts).strip()
            else:
                logger.error("Gemini %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Gemini error: %s", str(e)[:200])
    return ""


# ─── Unified interface ──────────────────────────────────────────────

async def call_ai(
    prompt: str,
    system: str = "",
    provider: str = "nemotron",
    max_tokens: int = 500,
    use_cache: bool = True,
    tier: str = "auto",
    user_id: int = 0,
) -> str:
    """
    Unified AI call with routing, caching, retry, and token limits.

    provider: "nemotron" | "gemini" | "auto"
    tier: "super" | "nano" | "auto" (auto picks based on max_tokens)
    """
    # Truncate inputs to prevent token waste
    prompt = _truncate_prompt(prompt)
    system = system[:600]  # System prompts are controlled by us, shorter cap

    # Auto-tier
    if tier == "auto":
        tier = "super" if max_tokens > 300 else "nano"

    if use_cache:
        key = _cache_key(prompt, system, provider)
        cached = _get_cached(key)
        if cached:
            return cached

    result = ""

    # Try requested provider first
    if provider in ("nemotron", "auto"):
        result = await _call_nemotron(prompt, system, max_tokens, tier=tier, user_id=user_id)

    if not result and provider in ("gemini", "auto"):
        result = await _call_gemini(prompt, system, max_tokens)

    # Fallback: try the other provider
    if not result and provider == "nemotron":
        result = await _call_gemini(prompt, system, max_tokens)
    if not result and provider == "gemini":
        result = await _call_nemotron(prompt, system, max_tokens, tier=tier, user_id=user_id)

    logger.info("AI call: provider=%s tier=%s prompt_len=%d cached=%s", provider, tier, len(prompt), "hit" if use_cache else "skip")

    if result and use_cache:
        _set_cache(_cache_key(prompt, system, provider), result)

    return result


# ─── Ultra-compact prompt builders ───────────────────────────────────

def build_match_prompt(profile_data: dict, job_data: dict, breakdown: dict) -> str:
    """Match analysis — ~120 tokens."""
    skills = profile_data.get('skills', [])[:8]
    job_skills = job_data.get('skills', [])[:6]
    return (
        f"Job match. 3 sentences.\n"
        f"Candidate: {profile_data.get('title', '?')} | {', '.join(skills)} | {profile_data.get('years', '?')}y\n"
        f"Job: {job_data['title']} at {job_data['company']} | {', '.join(job_skills)} | {job_data.get('level', 'mid')}\n"
        f"Score: {breakdown['overall']}% (skills={breakdown['skills']}%, exp={breakdown['experience']}%)\n"
        f"Match: {', '.join(breakdown.get('strong_matches', [])[:4])}\n"
        f"Gap: {', '.join(breakdown.get('missing_skills', [])[:4])}\n"
        f"-> 1) Fit 2) Strengths 3) Gap 4) Apply?"
    )


def build_chat_system(profile_data: dict, app_stats: dict, top_matches: list) -> str:
    """Chat system — ~100 tokens."""
    skills = ', '.join(profile_data.get('skills', [])[:10])
    matches = "; ".join(
        f"{m['title']}@{m['company']}({m['score']}%)" for m in top_matches[:3]
    ) if top_matches else "none"
    return (
        f"Rolio career AI. {profile_data.get('name','?')}, {profile_data.get('title','?')}. "
        f"Skills: {skills or 'none'}. "
        f"Apps: {app_stats.get('applied',0)}a/{app_stats.get('interviews',0)}i/{app_stats.get('saved',0)}s. "
        f"Matches: {matches}. "
        f"Be specific & actionable. Max 2 paragraphs."
    )


def build_resume_prompt(profile_data: dict, job_data: Optional[dict] = None) -> str:
    """Resume generation — ~450 tokens in, structured ATS resume out.

    Includes the user's REAL experience entries (company/title/dates/theirs
    bullets) so the AI rewrites actual history instead of inventing one,
    and pins an exact JSON schema the frontend can render.
    """
    exp_lines = []
    for e in profile_data.get("experience", [])[:4]:
        bullets = (e.get("description") or "").replace("\n", "; ")[:220]
        exp_lines.append(
            f"- {e.get('title','?')} at {e.get('company','?')} ({e.get('start','?')}–{e.get('end','Present')}): {bullets or 'no details'}"
        )
    exp_ctx = "\n".join(exp_lines) if exp_lines else "(no experience listed)"

    edu_lines = [
        f"- {ed.get('degree','?')}{' in ' + ed['field'] if ed.get('field') else ''}, {ed.get('institution','?')}"
        for ed in profile_data.get("education", [])[:3]
    ]
    edu_ctx = "\n".join(edu_lines) if edu_lines else "(none listed)"

    job_ctx = ""
    if job_data:
        job_ctx = (
            f"\nTARGET JOB: {job_data['title']} at {job_data['company']}. "
            f"Key skills: {', '.join(job_data.get('skills', [])[:6])}. "
            "Prioritize and phrase the candidate's real experience around these skills."
        )

    return (
        f"Write an ATS-friendly resume for {profile_data.get('name', 'Candidate')}"
        f" ({profile_data.get('title', 'Professional')}, {profile_data.get('location', '')}).\n"
        f"Skills: {', '.join(profile_data.get('skills', [])[:15]) or 'none'}\n"
        f"REAL experience (rewrite into strong bullets — do NOT invent employers/dates):\n{exp_ctx}\n"
        f"Education:\n{edu_ctx}"
        f"{job_ctx}\n\n"
        "Rules: bullets start with action verbs, include metrics where the source hints at any, max 22 words each, 2-4 bullets per role.\n"
        'Output ONLY JSON: {"summary":"2-3 sentences","contact":{"location":"..."},'
        '"experience":[{"title":"...","company":"...","start":"2023","end":"Present","bullets":["..."]}],'
        '"education":[{"degree":"...","field":"...","institution":"..."}],"skills":["top 10"]}'
    )


def build_career_advice_prompt(profile_data: dict, question: str) -> str:
    """Career advice — ~100 tokens."""
    return (
        f"Career advice for {profile_data.get('name', '?')} ({profile_data.get('title', '?')}). "
        f"Skills: {', '.join(profile_data.get('skills', [])[:8])}. "
        f"Q: {question[:200]} "
        f"-> Specific actionable advice. Reference their skills."
    )


def build_section_prompt(section: str, profile_data: dict, job_data: Optional[dict] = None) -> str:
    """Single resume section — ~150 tokens (saves ~600 vs full)."""
    job_hint = ""
    if job_data:
        job_hint = f" Tailor for {job_data['title']}. Key: {', '.join(job_data.get('skills', [])[:4])}."
    if section == "summary":
        return f"2-sentence summary for {profile_data.get('name','?')}, {profile_data.get('title','?')}. Skills: {', '.join(profile_data.get('skills',[])[:8])}.{job_hint}"
    elif section == "experience":
        exps = profile_data.get('experience', [])
        if not exps:
            return f"3 bullets for {profile_data.get('title','?')}.{job_hint}"
        return f"Rewrite bullets (1 line each):\n{str(exps)[:400]}{job_hint}"
    elif section == "skills":
        return f"Rank skills for {profile_data.get('title','?')}: {', '.join(profile_data.get('skills',[]))}. JSON array top 10."
    return f"Generate {section}.{job_hint}"
