"""
Rate limiting utility with Redis backend (fallback to in-memory).
"""
import time
import logging

logger = logging.getLogger("rolio.rate_limiter")

# In-memory fallback for development
_memory_store: dict[str, list[float]] = {}


class RateLimiter:
    """Rate limiter using Redis with in-memory fallback."""
    
    def __init__(self, redis=None):
        self.redis = redis
        self._memory_store: dict[str, list[float]] = {}
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        return f"ratelimit:{prefix}:{identifier}"
    
    def _memory_check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check rate limit using in-memory storage."""
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean old entries
        if key in self._memory_store:
            self._memory_store[key] = [
                ts for ts in self._memory_store[key] if ts > cutoff
            ]
        else:
            self._memory_store[key] = []
        
        if len(self._memory_store[key]) >= limit:
            return False
        
        self._memory_store[key].append(now)
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
        if key in self._memory_store:
            self._memory_store[key] = [
                ts for ts in self._memory_store[key] if ts > cutoff
            ]
            return max(0, limit - len(self._memory_store[key]))
        return limit


def get_rate_limiter() -> RateLimiter:
    """Get a rate limiter instance with Redis if available."""
    try:
        from database.connection import get_redis
        redis = get_redis()
        return RateLimiter(redis=redis)
    except Exception:
        logger.info("Redis not available, using in-memory rate limiter")
        return RateLimiter(redis=None)
