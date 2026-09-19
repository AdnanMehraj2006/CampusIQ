"""Internal marks / academic performance records."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.people import Student
    from app.models.subject import Subject


class AssessmentType(StrEnum):
    INTERNAL_EXAM = "internal_exam"
    MIDTERM = "midterm"
    ASSIGNMENT = "assignment"
    PRACTICAL = "practical"
    QUIZ = "quiz"
    END_SEMESTER = "end_semester"
    PROJECT = "project"


class Mark(Base, TimestampMixin):
    __tablename__ = "marks"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "assessment_type", "title", name="uq_mark_record"),
        Index("ix_marks_student_subject", "student_id", "subject_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type: Mapped[str] = mapped_column(Enum(AssessmentType), nullable=False)
    title: Mapped[str] = mapped_column(String(150), default="Internal Assessment", nullable=False)
    marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=100.0, nullable=False)
    entered_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="marks")
    subject: Mapped["Subject"] = relationship()

    @property
    def percentage(self) -> float:
        if not self.max_marks:
            return 0.0
        return round((float(self.marks) / float(self.max_marks)) * 100.0, 2)
