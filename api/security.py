"""Transport-level security middleware for the Episcopio API.

Two concerns live here:

* :class:`SecurityHeadersMiddleware` sets the response headers that keep the
  dashboard from being framed, sniffed or downgraded.
* :class:`RateLimitMiddleware` implements a small in-process token budget so a
  single client cannot hammer the public read endpoints or the unauthenticated
  survey/pipeline write endpoints.

The rate limiter is intentionally per-process: with more than one worker the
effective budget is ``limit * workers``. That is fine as a floor for abuse
control; a shared Redis counter is the natural upgrade and is called out in the
deployment docs.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Dash needs inline scripts/styles, so 'unsafe-inline' cannot be dropped
# without vendoring its assets. Everything else is locked to same-origin.
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response."""

    def __init__(self, app, *, https_only: bool = False, csp: str = DEFAULT_CSP):
        super().__init__(app)
        self.https_only = https_only
        self.csp = csp

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Content-Security-Policy", self.csp)
        headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        # Credentials are session-scoped and must never be cached by a proxy.
        if request.url.path.startswith("/api/v1/session"):
            headers["Cache-Control"] = "no-store"
        if self.https_only:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-IP rate limiter.

    Only the public API surface is metered. Dash drives the dashboard through
    its own ``/_dash-update-component`` endpoint, and every user interaction is
    a POST there — counting those against the API's write budget would rate-limit
    the UI against itself after a handful of clicks.

    Args:
        read_limit: requests per minute allowed for safe methods.
        write_limit: requests per minute allowed for state-changing methods.
        scope_prefixes: only paths under these prefixes are metered.
        exempt_paths: prefixes that bypass the limiter entirely (health probes).
    """

    # Live instances, so operators (and tests) can clear the counters without
    # digging through Starlette's middleware stack.
    _instances: "List[RateLimitMiddleware]" = []

    def __init__(
        self,
        app,
        *,
        read_limit: int = 60,
        write_limit: int = 10,
        window_seconds: int = 60,
        scope_prefixes: Iterable[str] = ("/api/v1",),
        exempt_paths: Iterable[str] = ("/api/v1/health",),
    ):
        super().__init__(app)
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.window_seconds = window_seconds
        self.scope_prefixes = tuple(scope_prefixes)
        self.exempt_paths = tuple(exempt_paths)
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        RateLimitMiddleware._instances.append(self)

    def reset(self) -> None:
        """Drop every counter."""
        with self._lock:
            self._hits.clear()

    @classmethod
    def reset_all(cls) -> None:
        """Drop the counters of every live limiter in this process."""
        for instance in cls._instances:
            instance.reset()

    @staticmethod
    def _client_key(request: Request) -> str:
        """Identify the caller.

        ``X-Forwarded-For`` is only honoured for the left-most entry, and only
        as a best-effort bucket key — it is spoofable, so it is never used for
        an authorization decision.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _prune(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(self.scope_prefixes) or path.startswith(self.exempt_paths):
            return await call_next(request)

        limit = self.write_limit if request.method in WRITE_METHODS else self.read_limit
        key = f"{self._client_key(request)}:{'w' if request.method in WRITE_METHODS else 'r'}"
        now = time.monotonic()

        with self._lock:
            bucket = self._hits[key]
            self._prune(bucket, now)
            if len(bucket) >= limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Demasiadas solicitudes. Intente de nuevo más tarde.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
            remaining = limit - len(bucket)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
