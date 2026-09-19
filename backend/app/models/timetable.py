"""Timetable entries and attendance records."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.classroom import Classroom
    from app.models.people import Faculty
    from app.models.subject import Subject, SubjectAssignment


class DayOfWeek(StrEnum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


WORKING_DAYS: list[DayOfWeek] = [
    DayOfWeek.MONDAY,
    DayOfWeek.TUESDAY,
    DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY,
    DayOfWeek.FRIDAY,
    DayOfWeek.SATURDAY,
]


class TimetableEntry(Base, TimestampMixin):
    """One (day, period) slot for a section.

    ``subject_id``/``faculty_id``/``classroom_id`` are denormalised copies of the
    SubjectAssignment so conflict detection stays simple and history is stable.
    """

    __tablename__ = "timetable"
    __table_args__ = (
        UniqueConstraint("day", "period", "section", "academic_session_id", name="uq_tt_section_slot"),
        UniqueConstraint("day", "period", "faculty_id", "academic_session_id", name="uq_tt_faculty_slot"),
        UniqueConstraint("day", "period", "classroom_id", "academic_session_id", name="uq_tt_room_slot"),
        Index("ix_timetable_section_day_period", "section", "day", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    day: Mapped[str] = mapped_column(Enum(DayOfWeek), nullable=False, index=True)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    classroom_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True, index=True)
    section: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True)
    assignment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subject_assignments.id", ondelete="SET NULL"), nullable=True)
    academic_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)

    subject: Mapped["Subject"] = relationship()
    faculty: Mapped["Faculty"] = relationship()
    assignment: Mapped[Optional["SubjectAssignment"]] = relationship(back_populates="timetable_entries")
    classroom: Mapped[Optional["Classroom"]] = relationship(back_populates="timetable_entries")


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


ATTENDANCE_STATUS_ORDER = {
    AttendanceStatus.PRESENT: 0,
    AttendanceStatus.LATE: 1,
    AttendanceStatus.EXCUSED: 2,
    AttendanceStatus.ABSENT: 3,
}


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "date", name="uq_attendance_student_subject_date"),
        Index("ix_attendance_subject_date", "subject_id", "date"),
        Index("ix_attendance_student_subject", "student_id", "subject_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    marked_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="attendance")
    subject: Mapped["Subject"] = relationship()

    @property
    def counts_as_present(self) -> bool:
        return self.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
