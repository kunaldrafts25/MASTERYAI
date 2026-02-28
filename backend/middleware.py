import time
import logging
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

RATE_LIMIT = 60
WINDOW_SECONDS = 60
CLEANUP_INTERVAL = 300


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup(self):
        now = time.time()
        if now - self.last_cleanup < CLEANUP_INTERVAL:
            return
        self.last_cleanup = now
        cutoff = now - WINDOW_SECONDS
        stale = [ip for ip, timestamps in self.requests.items() if not timestamps or timestamps[-1] < cutoff]
        for ip in stale:
            del self.requests[ip]

    def _is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - WINDOW_SECONDS
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        if len(self.requests[ip]) >= RATE_LIMIT:
            return True
        self.requests[ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        self._cleanup()

        client_ip = request.client.host if request.client else "unknown"

        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})

        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)

        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration}ms")

        return response
