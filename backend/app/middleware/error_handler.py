"""Standardized exception -> HTTP response mapping.

No stack traces or internal messages ever reach the client. In development the
error detail is richer to aid debugging; in production only the envelope.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import AppException, error_envelope

logger = logging.getLogger("campusiq.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.message, exc.error_code, exc.status_code, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
        }
        message = str(exc.detail) if exc.detail else "Request failed."
        if exc.status_code == 404 and message.isdigit():
            message = "The requested resource was not found."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(message, code_map.get(exc.status_code, "HTTP_ERROR"), exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details: Dict[str, Any] = {}
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []) if part not in ("body",))
            details[loc or "body"] = err.get("msg", "Invalid value.")
        return JSONResponse(
            status_code=422,
            content=error_envelope(
                "The provided data failed validation.", "VALIDATION_ERROR", 422, details
            ),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        # Duplicate-key / FK violations are surfaced as 409.
        msg = "The request conflicts with existing data."
        if settings.debug:
            msg = "Database constraint violation."
        logger.warning("IntegrityError on %s: %s", request.url.path, str(exc.orig)[:200])
        return JSONResponse(status_code=409, content=error_envelope(msg, "CONFLICT", 409))

    @app.exception_handler(OperationalError)
    async def operational_handler(request: Request, exc: OperationalError):
        logger.exception("Database operational error on %s", request.url.path)
        return JSONResponse(
            status_code=503,
            content=error_envelope(
                "A database error occurred. Please try again shortly.", "SERVICE_UNAVAILABLE", 503
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        # Never leak the stack trace; log it server-side only.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        message = "An internal server error occurred."
        if settings.debug and isinstance(exc, ValueError):
            message = str(exc)[:200]
        return JSONResponse(
            status_code=500,
            content=error_envelope(message, "INTERNAL_ERROR", 500),
        )
