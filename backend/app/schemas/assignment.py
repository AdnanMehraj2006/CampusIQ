"""Assignment, submission and marks schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.marks import AssessmentType
from app.schemas.common import ORMModel


# ---- Assignments ----
class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    subject_id: int
    section: Optional[str] = None
    semester_id: Optional[int] = None
    deadline: datetime
    max_marks: int = Field(10, ge=1, le=1000)
    allow_late: bool = True


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    deadline: Optional[datetime] = None
    max_marks: Optional[int] = Field(None, ge=1, le=1000)
    allow_late: Optional[bool] = None


class AssignmentOut(ORMModel):
    id: int
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    subject_id: int
    faculty_id: int
    section: Optional[str] = None
    semester_id: Optional[int] = None
    deadline: datetime
    max_marks: int
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None
    allow_late: bool
    is_published: bool
    created_at: Optional[datetime] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    faculty_name: Optional[str] = None
    submission_count: Optional[int] = None
    my_submission: Optional[dict] = None


class SubmissionCreate(BaseModel):
    text_submission: Optional[str] = None


class SubmissionGrade(BaseModel):
    grade: float = Field(..., ge=0)
    feedback: Optional[str] = None


class SubmissionOut(ORMModel):
    id: int
    assignment_id: int
    student_id: int
    file_name: Optional[str] = None
    text_submission: Optional[str] = None
    submitted_at: datetime
    is_late: bool
    grade: Optional[float] = None
    feedback: Optional[str] = None
    graded_at: Optional[datetime] = None
    student_name: Optional[str] = None
    enrollment_number: Optional[str] = None
    assignment_title: Optional[str] = None
    max_marks: Optional[int] = None


# ---- Marks ----
class MarkCreate(BaseModel):
    student_id: int
    subject_id: int
    assessment_type: AssessmentType
    title: str = Field("Internal Assessment", max_length=150)
    marks: float = Field(..., ge=0)
    max_marks: float = Field(100.0, ge=1)
    remarks: Optional[str] = None


class MarkUpdate(BaseModel):
    marks: Optional[float] = Field(None, ge=0)
    max_marks: Optional[float] = Field(None, ge=1)
    remarks: Optional[str] = None


class MarkOut(ORMModel):
    id: int
    student_id: int
    subject_id: int
    assessment_type: str
    title: str
    marks: float
    max_marks: float
    remarks: Optional[str] = None
    percentage: Optional[float] = None
    subject_name: Optional[str] = None
    student_name: Optional[str] = None
    entered_at: Optional[str] = None
