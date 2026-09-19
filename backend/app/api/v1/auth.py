"""Authentication endpoints: login, refresh, logout, password flows, invite."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import client_ip, get_current_user, require_permission
from app.core.exceptions import NotFoundError  # noqa: F401
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteUserRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login with email **or** College ID + password."""
    ip = client_ip(request)
    user = auth_service.authenticate(db, payload.identifier, payload.password, ip=ip)
    tokens = auth_service.issue_tokens(db, user, ip=ip, user_agent=request.headers.get("user-agent"))
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    return auth_service.refresh_session(db, payload.refresh_token, ip=client_ip(request))


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    auth_service.logout(db, payload.refresh_token)
    return {"success": True, "message": "Logged out successfully."}


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_service.change_password(db, current_user, payload.current_password, payload.new_password)
    return {"success": True, "message": "Password changed. Please log in again."}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Demo mode returns the reset token directly so the flow is testable
    without an email server. In production this would be emailed."""
    result = auth_service.create_password_reset_token(db, payload.identifier)
    if not result:
        # Do not reveal whether the account exists.
        return {
            "success": True,
            "message": "If an account exists for that identifier, a reset link has been issued.",
        }
    user, token = result
    if settings.is_production:
        return {
            "success": True,
            "message": f"If an account exists for {payload.identifier}, a reset link has been emailed.",
        }
    return {
        "success": True,
        "message": "Reset token issued (demo mode - no email server configured).",
        "data": {"token": token, "expires_in_minutes": 60},
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = auth_service.reset_password(db, payload.token, payload.new_password)
    return {"success": True, "message": f"Password reset for {user.email}. You can now log in."}


@router.post("/invite", response_model=UserPublic)
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Admin/HOD invitation: creates a ready-to-use account."""
    from app.services.audit_service import log_action

    user, plaintext = auth_service.create_user_account(
        db,
        name=payload.name,
        email=payload.email,
        college_id=payload.college_id,
        role=payload.role,
        password=payload.password,
        phone=payload.phone,
    )
    log_action(
        db,
        user_id=current_user.id,
        user_name=current_user.name,
        role=str(current_user.role),
        action="user.invited",
        resource="user",
        resource_id=user.id,
        details={"invited_role": str(payload.role)},
        ip_address=None,
    )
    return JSONResponse(
        status_code=201,
        content={
            **user.to_public_dict(),
            "initial_password": plaintext if not settings.is_production else None,
        },
    )
