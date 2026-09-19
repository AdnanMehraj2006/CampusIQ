"""Assignments and student submissions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.people import Faculty, Student
    from app.models.subject import Subject


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)

    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    max_marks: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    allow_late: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subject: Mapped["Subject"] = relationship()
    faculty: Mapped["Faculty"] = relationship()
    submissions: Mapped[List["AssignmentSubmission"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(Base, TimestampMixin):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_submission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_submission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    grade: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    student: Mapped["Student"] = relationship()

    @property
    def is_graded(self) -> bool:
        return self.grade is not None
