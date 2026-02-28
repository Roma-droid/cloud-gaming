"""Rate limiting middleware using Redis sliding window."""

from __future__ import annotations

import time

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.utils.logging import get_logger
from backend.utils.redis import get_redis

logger = get_logger(__name__)

# Rate limits: (requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/auth/login": (10, 60),      # 10 requests per minute
    "/api/auth/register": (5, 60),    # 5 per minute
    "default": (100, 60),             # 100 per minute
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Find matching rate limit
        limit_config = RATE_LIMITS.get(path, RATE_LIMITS["default"])
        max_requests, window = limit_config

        key = f"ratelimit:{client_ip}:{path}"

        try:
            redis = await get_redis()
            now = time.time()
            window_start = now - window

            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            request_count = results[2]

            if request_count > max_requests:
                logger.warning("rate_limit_exceeded", ip=client_ip, path=path, count=request_count)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(window)},
                )
        except HTTPException:
            raise
        except Exception:
            # If Redis is unavailable, allow the request
            pass

        response = await call_next(request)
        return response
