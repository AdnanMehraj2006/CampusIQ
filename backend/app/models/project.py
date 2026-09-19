"""Projects, groups and milestone tracking."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import Department, Semester
    from app.models.people import Faculty, Student


class ProjectStatus(StrEnum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class MilestoneStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_code: Mapped[Optional[str]] = mapped_column(String(30), unique=True, nullable=True)

    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.PROPOSED, nullable=False, index=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_group_size: Mapped[int] = mapped_column(default=4, nullable=False)

    department: Mapped[Optional["Department"]] = relationship()
    semester: Mapped[Optional["Semester"]] = relationship()
    supervisor: Mapped["Faculty"] = relationship()
    groups: Mapped[List["ProjectGroup"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    milestones: Mapped[List["ProjectMilestone"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectGroup(Base, TimestampMixin):
    """A team within a project."""

    __tablename__ = "project_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    proposal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.PROPOSED, nullable=False)
    approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="groups")
    members: Mapped[List["ProjectGroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class ProjectGroupMember(Base, TimestampMixin):
    __tablename__ = "project_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_group_member"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)

    group: Mapped["ProjectGroup"] = relationship(back_populates="members")
    student: Mapped["Student"] = relationship(back_populates="project_memberships")


class ProjectMilestone(Base, TimestampMixin):
    __tablename__ = "project_milestones"
    __table_args__ = (Index("ix_milestones_project_order", "project_id", "order_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(Enum(MilestoneStatus), default=MilestoneStatus.PENDING, nullable=False)
    submission_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="milestones")
