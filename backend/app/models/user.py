"""User identity, status and refresh-token models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.database import Base

if TYPE_CHECKING:
    from app.models.people import Faculty, Student


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("admin", "hod", "faculty", "cr", "student", name="user_role"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- relationships ---
    student_profile: Mapped[Optional["Student"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    faculty_profile: Mapped[Optional["Faculty"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def to_public_dict(self) -> dict:
        """Never expose password_hash/tokens anywhere."""
        return {
            "id": self.id,
            "college_id": self.college_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "status": self.status,
            "avatar_url": self.avatar_url,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
