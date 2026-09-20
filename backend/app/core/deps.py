"""Shared FastAPI dependencies: current user, RBAC enforcement, scoping helpers.

These are the *only* place authorization is decided. Every protected router
depends on ``get_current_user`` and, where needed, ``require_permission`` or
one of the resource-scoping helpers (``get_current_student``, ``get_current_faculty``).
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    UnauthorizedError,
)
from app.core.permissions import Permission, Role, role_has_permission
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import RefreshToken, User, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    authorization: Optional[str],
) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise UnauthorizedError("Missing or malformed Authorization header.")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> User:
    """Resolve the user backing a valid access token. 401 otherwise."""
    import jwt

    from app.core.security import decode_access_token

    token = _extract_token(credentials, authorization)
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Your session has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid authentication token.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise UnauthorizedError("User account no longer exists.")
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("Your account has been suspended. Contact the administrator.")

    # Attach request-scoped context for audit logging middleware.
    request.state.current_user = user
    return user


def require_permission(permission: Permission | str) -> Callable:
    """Dependency factory: allows the route only if the role grants ``permission``."""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(current_user.role, permission):
            raise ForbiddenError(
                f"Your role ({current_user.role}) is not allowed to perform this action."
            )
        return current_user

    return _checker


def require_roles(*roles: Role | str) -> Callable:
    """Dependency factory: allows the route only for the listed roles."""

    allowed = {str(r) for r in roles}

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if str(current_user.role) not in allowed:
            raise ForbiddenError("Your role is not allowed to access this resource.")
        return current_user

    return _checker


def get_current_student(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the Student profile of the authenticated user (student or CR)."""
    from app.models.people import Student

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise ForbiddenError("Your account is not linked to a student profile.")
    return student


def get_current_faculty(current_user: User = Depends(get_current_user)):
    """Return the Faculty profile of the authenticated faculty/HOD user."""
    if current_user.faculty_profile is None:
        raise ForbiddenError("Your account is not linked to a faculty profile.")
    return current_user.faculty_profile


def check_department_scope(current_user: User, department_id: int | None) -> None:
    """HODs may only touch their own department; admins are unrestricted."""
    if current_user.role == Role.ADMIN:
        return
    if current_user.role == Role.HOD and current_user.faculty_profile is not None:
        if department_id is not None and current_user.faculty_profile.department_id != department_id:
            raise ForbiddenError("You can only access resources within your own department.")
        return
    raise ForbiddenError("You are not allowed to access department-scoped resources.")


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def pagination_params(
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
) -> dict:
    if page < 1:
        raise BadRequestError("page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise BadRequestError("page_size must be between 1 and 100")
    return {"page": page, "page_size": page_size, "q": (q or "").strip(), "offset": (page - 1) * page_size}
