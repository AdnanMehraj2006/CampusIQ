"""In-memory fixed-window rate limiting.

Limits are declared in ``app.config`` (e.g. ``RATE_LIMIT_LOGIN=10/minute``) and
enforced per (route, client). The store is a process-local dict guarded by a
lock, which suits the single-process Railway deployment; ``RateLimiter.reset()``
is exposed so the test suite can isolate every test.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.deps import client_ip

logger = logging.getLogger("campusiq.ratelimit")

_SPEC_RE = re.compile(r"^\s*(\d+)\s*(?:/|per\s+)?\s*(second|minute|hour)s?\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600}


def parse_rate_limit(spec: str) -> Tuple[int, int]:
    """Parse a ``"10/minute"`` style spec into ``(limit, window_seconds)``."""
    match = _SPEC_RE.match(spec or "")
    if not match:
        raise ValueError(
            f"Invalid rate-limit spec: {spec!r} (expected '<n>/<second|minute|hour>')"
        )
    return int(match.group(1)), _UNIT_SECONDS[match.group(2).lower()]


class RateLimiter:
    """Thread-safe fixed-window counter keyed by route + client."""

    def __init__(self) -> None:
        self.storage: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def hit(self, key: str, limit: int, window: int) -> Tuple[bool, float]:
        """Record one request for ``key``.

        Returns ``(allowed, retry_after_seconds)``. When the limit is exceeded the
        hit is *not* recorded, so the window is not extended by blocked traffic.
        """
        now = time.time()
        with self._lock:
            hits = [t for t in self.storage[key] if now - t < window]
            if len(hits) >= limit:
                retry_after = max(1.0, window - (now - hits[0]))
                self.storage[key] = hits
                return False, retry_after
            hits.append(now)
            self.storage[key] = hits
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self.storage.clear()


rate_limiter = RateLimiter()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Enforces the configured per-client limits on sensitive routes.

    Routes are matched *after* stripping the API prefix, so they are written as
    they appear in the routers (``/auth/login``, ``/ai/chat``) and stay correct if
    the prefix ever changes.
    """

    skip_paths = ("/health", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app):
        super().__init__(app)
        # Parsed once at startup so a malformed spec fails loudly, not per request.
        self.rules: Dict[str, Tuple[int, int]] = {
            "/auth/login": parse_rate_limit(settings.rate_limit_login),
            "/ai/chat": parse_rate_limit(settings.rate_limit_ai),
        }
        logger.info(
            "Rate limiting enabled for: %s",
            ", ".join(f"{r}={n}/{w}s" for r, (n, w) in self.rules.items()),
        )

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # CORS preflight requests are unauthenticated and cheap; CORS middleware
        # (registered outermost) already answers most of them.
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.skip_paths):
            return await call_next(request)

        route = self._route_for(path)
        if route is None:
            return await call_next(request)

        limit, window = self.rules[route]
        allowed, retry_after = rate_limiter.hit(f"{route}:{client_ip(request)}", limit, window)
        if not allowed:
            logger.warning("Rate limit exceeded for %s on %s", client_ip(request), route)
            return JSONResponse(
                status_code=429,
                content={"detail": "RATE_LIMIT_EXCEEDED"},
                headers={"Retry-After": str(int(retry_after))},
            )
        return await call_next(request)

    def _route_for(self, path: str) -> Optional[str]:
        """Map a full request path to a rate-limited route, or ``None``."""
        prefix = settings.api_v1_prefix
        if prefix and path.startswith(prefix):
            path = path[len(prefix):]
        path = path.rstrip("/") or "/"
        return path if path in self.rules else None
