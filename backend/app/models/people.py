"""Student and faculty profile models.

A user account holds identity + auth; these profiles hold academic linkage.
CRs are students whose ``User.role == 'cr'``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.database import Base

if TYPE_CHECKING:
    from app.models.academic import Course, Department, Semester
    from app.models.marks import Mark
    from app.models.project import ProjectGroupMember
    from app.models.timetable import Attendance
    from app.models.user import User


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    enrollment_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True)
    section: Mapped[str] = mapped_column(String(10), default="A", nullable=False, index=True)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    guardian_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    department: Mapped["Department"] = relationship(back_populates="students")
    course: Mapped[Optional["Course"]] = relationship(back_populates="students")
    semester: Mapped[Optional["Semester"]] = relationship()

    attendance: Mapped[List["Attendance"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    marks: Mapped[List["Mark"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    project_memberships: Mapped[List["ProjectGroupMember"]] = relationship(back_populates="student", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        return self.user.name if self.user else ""


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(100), default="Assistant Professor", nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="faculty_profile")
    department: Mapped["Department"] = relationship(back_populates="faculty", foreign_keys=[department_id])

    @property
    def name(self) -> str:
        return self.user.name if self.user else ""

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""
