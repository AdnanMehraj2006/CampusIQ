"""Announcements, notifications, feedback and audit logs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.user import User


class AnnouncementTarget(StrEnum):
    EVERYONE = "everyone"
    DEPARTMENT = "department"
    COURSE = "course"
    SEMESTER = "semester"
    SECTION = "section"
    FACULTY = "faculty"

    @classmethod
    def scoped(cls) -> set["AnnouncementTarget"]:
        return {cls.DEPARTMENT, cls.COURSE, cls.SEMESTER, cls.SECTION}


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    target_type: Mapped[str] = mapped_column(Enum(AnnouncementTarget), default=AnnouncementTarget.EVERYONE, nullable=False, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)

    priority: Mapped[str] = mapped_column(Enum(Priority), default=Priority.NORMAL, nullable=False)
    published_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expiry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)

    author: Mapped[Optional["User"]] = relationship()


class NotificationType(StrEnum):
    ATTENDANCE_WARNING = "attendance_warning"
    ATTENDANCE_MARKED = "attendance_marked"
    ASSIGNMENT = "assignment"
    ASSIGNMENT_GRADED = "assignment_graded"
    PROJECT = "project"
    PROJECT_DEADLINE = "project_deadline"
    MILESTONE = "milestone"
    ANNOUNCEMENT = "announcement"
    MARKS_PUBLISHED = "marks_published"
    TIMETABLE_UPDATE = "timetable_update"
    SYSTEM = "system"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient_read", "recipient_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Enum(NotificationType), default=NotificationType.SYSTEM, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    recipient: Mapped[Optional["User"]] = relationship()


class Feedback(Base, TimestampMixin):
    """Class/subject feedback submitted by students and CRs."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), default="subject", nullable=False, index=True)
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    author: Mapped[Optional["User"]] = relationship()
    subject: Mapped[Optional["Subject"]] = relationship()


class CRRequest(Base, TimestampMixin):
    """Requests raised by class representatives."""

    __tablename__ = "cr_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    request_type: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    author: Mapped[Optional["User"]] = relationship()


class AuditLog(Base):
    """Immutable record of security-sensitive actions.

    There is no update/delete endpoint for this table - it is append-only.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_user_action", "user_id", "action"), Index("ix_audit_resource", "resource", "resource_id"))

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[Optional["User"]] = relationship()


class SystemSetting(Base, TimestampMixin):
    """Key/value store for admin-configurable system settings."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
