import time
import uuid
import logging
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

RATE_LIMIT = 60
WINDOW_SECONDS = 60
CLEANUP_INTERVAL = 300


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID header to every response for debugging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


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

    def _is_rate_limited(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - WINDOW_SECONDS
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        if len(self.requests[ip]) >= RATE_LIMIT:
            oldest = self.requests[ip][0] if self.requests[ip] else now
            retry_after = max(1, int(oldest + WINDOW_SECONDS - now))
            return True, retry_after
        self.requests[ip].append(now)
        return False, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        self._cleanup()

        client_ip = request.client.host if request.client else "unknown"

        limited, retry_after = self._is_rate_limited(client_ip)
        if limited:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )

        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)

        request_id = getattr(request.state, "request_id", "")
        logger.info(f"[{request_id}] {request.method} {request.url.path} {response.status_code} {duration}ms")

        return response
