"""Domain exceptions and standardized API error responses.

Raw stack traces are never leaked to clients - every error is converted into
the standard envelope:

    {"success": false, "message": "...", "error_code": "...", "details": {...}}
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base domain exception mapped to a structured HTTP error response."""

    status_code: int = 400
    error_code: str = "BAD_REQUEST"
    message: str = "Request failed."

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = 400
    error_code = "BAD_REQUEST"
    message = "Invalid request."


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You are not authorized to perform this action."


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"
    message = "The request conflicts with existing data."


class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "The provided data failed validation."


class RateLimitError(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please slow down."


class ServerError(AppException):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An internal server error occurred."


class FileUploadError(AppException):
    status_code = 400
    error_code = "FILE_UPLOAD_ERROR"
    message = "The uploaded file was rejected."


class TimetableConflictError(ConflictError):
    error_code = "TIMETABLE_CONFLICT"
    message = "The timetable entry conflicts with an existing entry."


class AttendanceConflictError(ConflictError):
    error_code = "ATTENDANCE_CONFLICT"
    message = "Attendance has already been marked for this subject/date/section."


def error_envelope(
    message: str,
    error_code: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "success": False,
        "message": message,
        "error_code": error_code,
    }
    if details:
        body["details"] = details
    return body
