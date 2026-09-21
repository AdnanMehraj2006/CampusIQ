"""CampusIQ - Smart College Management & Analytics Platform.

Application entrypoint. Wires middleware, error handling, CORS, rate limiting
and all versioned routers.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.error_handler import register_error_handlers
from app.middleware.rate_limiter import RateLimitingMiddleware, rate_limiter
from app.models import Base  # noqa: F401  (ensures metadata is importable)

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("campusiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CampusIQ API...")
    yield
    # Shutdown
    logger.info("Shutting down CampusIQ API...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        description=(
            "Smart College Management & Analytics Platform. "
            "Role-based access is enforced on every protected endpoint; "
            "see /docs for the interactive documentation."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add rate limiting middleware FIRST (before CORS)
    app.add_middleware(RateLimitingMiddleware)
    # Expose the limiter's storage so ops/debug tooling can inspect it.
    app.state.rate_limit_storage = rate_limiter.storage

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
        expose_headers=["Content-Disposition"],
    )

    # ---- Security headers ----
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains" if settings.is_production else ""
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
        )
        return response

    # ---- Request logging / latency ----
    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
        return response

    register_error_handlers(app)

    # ---- Routers ----
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["System"])
    def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.app_env,
            "database": "postgresql" if not settings.sqlite_in_use else "sqlite",
            "ai_mode": "demo" if (settings.ai_provider == "demo" or not settings.ai_api_key) else "openai",
            "time": time.time(),
        }

    @app.get("/", tags=["System"])
    def root():
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
