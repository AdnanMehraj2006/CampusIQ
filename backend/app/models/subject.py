"""Subjects and subject-faculty-section assignments."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import Department, Semester
    from app.models.timetable import TimetableEntry


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("code", "department_id", name="uq_subject_code_dept"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    credits: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    weekly_periods: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False,
        doc="Required periods per week for timetable generation",
    )

    semester: Mapped[Optional["Semester"]] = relationship(back_populates="subjects")
    department: Mapped["Department"] = relationship(back_populates="subjects")
    assignments: Mapped[List["SubjectAssignment"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class SubjectAssignment(Base, TimestampMixin):
    """Binds a faculty member to a subject for a specific section/semester."""

    __tablename__ = "subject_assignments"
    __table_args__ = (
        UniqueConstraint("subject_id", "faculty_id", "section", "semester_id", name="uq_subject_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True)

    subject: Mapped["Subject"] = relationship(back_populates="assignments")
    faculty: Mapped["Faculty"] = relationship()
    timetable_entries: Mapped[List["TimetableEntry"]] = relationship(back_populates="assignment")
