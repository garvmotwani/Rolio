"""
Shared per-user rate-limit dependency for expensive AI endpoints (audit fix M3).

Every AI generation route (chat, job questions, cover letters, interview prep,
resume builder, explanations) invokes a paid/inference API. This dependency
caps each authenticated user with a single shared bucket so a user can't
exceed the quota by spreading requests across endpoints.
"""
import logging

from fastapi import Depends, HTTPException, Request

from config import RATE_LIMIT_AI_PER_MINUTE
from utils.auth import get_current_user
from utils.rate_limiter import get_rate_limiter
from utils.security_logging import log_rate_limit_violation

logger = logging.getLogger("rolio.ai")

_rate_limiter = get_rate_limiter()


async def ai_rate_limit(
    request: Request,
    user=Depends(get_current_user),
):
    """FastAPI dependency: per-user shared quota for all AI endpoints.

    Use as:  user=Depends(ai_rate_limit)   (replaces get_current_user)
    The returned user is the authenticated user, so this both authenticates
    AND rate limits in one dependency.
    """
    allowed = _rate_limiter.check(
        "ai_generation",
        f"user:{user.id}",
        RATE_LIMIT_AI_PER_MINUTE,
        60,
    )
    if not allowed:
        log_rate_limit_violation(
            endpoint=str(request.url.path),
            ip_address=request.client.host if request.client else "unknown",
            limit=RATE_LIMIT_AI_PER_MINUTE,
            window=60,
        )
        raise HTTPException(
            status_code=429,
            detail="AI request limit reached. Please wait a minute and try again.",
        )
    return user
