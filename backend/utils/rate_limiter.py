"""
Rate limiting utility with Redis backend (fallback to in-memory).
"""
import time
import logging

logger = logging.getLogger("rolio.rate_limiter")

# In-memory fallback for development
_memory_store: dict[str, list[float]] = {}


class RateLimiter:
    """Rate limiter using Redis with in-memory fallback.

    The fallback store is MODULE-LEVEL, shared by every instance: without
    it, each get_rate_limiter() call started from an empty bucket and
    limiting silently did nothing in Redis-less deployments.
    """

    def __init__(self, redis=None):
        self.redis = redis

    def _store(self) -> dict[str, list[float]]:
        return _memory_store
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        return f"ratelimit:{prefix}:{identifier}"
    
    def _memory_check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check rate limit using the shared in-memory store."""
        store = self._store()
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean old entries
        if key in store:
            store[key] = [
                ts for ts in store[key] if ts > cutoff
            ]
        else:
            store[key] = []
        
        if len(store[key]) >= limit:
            return False
        
        store[key].append(now)
        return True
    
    def _redis_check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check rate limit using Redis sliding window."""
        if not self.redis:
            return self._memory_check(key, limit, window_seconds)
        
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_start = now - window_seconds
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {f"{now}": now})
            
            # Set expiry
            pipe.expire(key, window_seconds)
            
            results = pipe.execute()
            current_count = results[1]
            
            return current_count < limit
        except Exception as e:
            logger.warning(f"Redis rate limit check failed, falling back to memory: {e}")
            return self._memory_check(key, limit, window_seconds)
    
    def check(self, prefix: str, identifier: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            prefix: Rate limit category (e.g., "login", "jsearch")
            identifier: User/IP identifier
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if request is allowed, False if rate limited
        """
        key = self._get_key(prefix, identifier)
        
        if self.redis:
            return self._redis_check(key, limit, window_seconds)
        else:
            return self._memory_check(key, limit, window_seconds)
    
    def get_remaining(self, prefix: str, identifier: str, limit: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        key = self._get_key(prefix, identifier)
        now = time.time()
        cutoff = now - window_seconds
        
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                results = pipe.execute()
                return max(0, limit - results[1])
            except Exception:
                pass
        
        # Fallback to memory
        store = self._store()
        if key in store:
            store[key] = [
                ts for ts in store[key] if ts > cutoff
            ]
            return max(0, limit - len(store[key]))
        return limit


_limiter_singleton: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the shared rate limiter (singleton). Redis when available,
    otherwise the module-level in-memory store shared across instances."""
    global _limiter_singleton
    if _limiter_singleton is not None:
        return _limiter_singleton
    try:
        from database.connection import get_redis
        redis = get_redis()
        _limiter_singleton = RateLimiter(redis=redis)
    except Exception:
        logger.info("Redis not available, using in-memory rate limiter")
        _limiter_singleton = RateLimiter(redis=None)
    return _limiter_singleton
