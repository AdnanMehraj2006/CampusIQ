"""Department and academic structure models."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.database import Base

if TYPE_CHECKING:
    from app.models.people import Faculty, Student
    from app.models.subject import Subject


class ClassTeacher(Base, TimestampMixin):
    """Faculty responsibility for class oversight."""

    __tablename__ = "class_teachers"
    __table_args__ = (
        UniqueConstraint("faculty_id", "section", name="uq_class_teacher"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    faculty: Mapped["Faculty"] = relationship()


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    hod_id: Mapped[Optional[int]] = mapped_column(ForeignKey("faculty.id", use_alter=True, ondelete="SET NULL"), nullable=True)

    hod: Mapped[Optional["Faculty"]] = relationship(foreign_keys=[hod_id], post_update=True)
    courses: Mapped[List["Course"]] = relationship(back_populates="department", cascade="all, delete-orphan")
    subjects: Mapped[List["Subject"]] = relationship(back_populates="department")
    students: Mapped[List["Student"]] = relationship(back_populates="department")
    faculty: Mapped[List["Faculty"]] = relationship(back_populates="department", foreign_keys="Faculty.department_id")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    duration_years: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    department: Mapped["Department"] = relationship(back_populates="courses")
    students: Mapped[List["Student"]] = relationship(back_populates="course")


class AcademicSession(Base, TimestampMixin):
    """e.g. "2025-2026 Odd Semester" / an academic year+term container."""

    __tablename__ = "academic_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    semesters: Mapped[List["Semester"]] = relationship(back_populates="academic_session", cascade="all, delete-orphan")



