"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.permissions import Role


class LoginRequest(BaseModel):
    """Accepts either email or college_id as the identifier."""

    identifier: str = Field(..., min_length=3, description="Email or College ID")
    password: str = Field(..., min_length=1)

    @field_validator("identifier")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip()


class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=128)


class InviteUserRequest(BaseModel):
    """Admin/HOD invitation flow: creates a pending account."""

    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    college_id: str = Field(..., min_length=3, max_length=32)
    role: Role
    phone: Optional[str] = None
    department_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, description="Optional preset password")


class UserPublic(BaseModel):
    id: int
    college_id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str
    avatar_url: Optional[str] = None
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


TokenResponse.model_rebuild()
