import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._requests: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        bucket = self._requests[client_host]

        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        bucket.append(now)
        return await call_next(request)
