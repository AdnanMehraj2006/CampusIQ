"""Attendance and timetable schemas."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.timetable import AttendanceStatus, DayOfWeek
from app.schemas.common import ORMModel


# ---- Attendance ----
class AttendanceMark(BaseModel):
    student_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT


class AttendanceCreateRequest(BaseModel):
    subject_id: int
    section: str = Field(..., max_length=10)
    date: date
    marks: List[AttendanceMark] = Field(..., min_length=1)
    note: Optional[str] = None


class AttendanceUpdateRequest(BaseModel):
    status: AttendanceStatus
    note: Optional[str] = None


class AttendanceOut(ORMModel):
    id: int
    student_id: int
    subject_id: int
    date: date
    status: str
    marked_by: int
    note: Optional[str] = None
    student_name: Optional[str] = None
    enrollment_number: Optional[str] = None
    subject_name: Optional[str] = None


class AttendanceSummaryItem(BaseModel):
    subject_id: int
    subject_name: str
    subject_code: str
    classes_attended: int
    classes_conducted: int
    percentage: float
    zone: str


class AttendanceAnalytics(BaseModel):
    total_classes: int
    attended: int
    absent: int
    late: int
    excused: int
    overall_percentage: float
    classes_attended: int
    classes_conducted: int
    classes_missed: int
    required_percentage: float
    zone: str
    subject_wise: List[AttendanceSummaryItem]
    trend: List[dict]


class AttendancePrediction(BaseModel):
    current_percentage: float
    required_percentage: float
    classes_attended: int
    classes_conducted: int
    classes_needed: int
    will_reach: bool
    projected_percentage: Optional[float] = None
    classes_can_miss: int
    message: str


# ---- Timetable ----
class TimetableEntryCreate(BaseModel):
    day: DayOfWeek
    period: int = Field(..., ge=1, le=12)
    subject_id: int
    faculty_id: int
    classroom_id: Optional[int] = None
    section: str = Field(..., max_length=10)
    semester_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class TimetableEntryUpdate(BaseModel):
    subject_id: Optional[int] = None
    faculty_id: Optional[int] = None
    classroom_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class TimetableEntryOut(ORMModel):
    id: int
    day: str
    period: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    subject_id: int
    faculty_id: int
    classroom_id: Optional[int] = None
    section: str
    semester_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    faculty_name: Optional[str] = None
    room_number: Optional[str] = None


class TimetableGenerateRequest(BaseModel):
    sections: List[str] = Field(..., min_length=1)
    periods_per_day: int = Field(6, ge=1, le=12)
    working_days: List[DayOfWeek] = Field(default_factory=list)
    prefer_room_capacity: bool = True


class TimetableGenerateResult(BaseModel):
    success: bool
    entries_created: int
    conflicts: List[dict]
    sections: List[str]
    message: str


class TimetableConflict(BaseModel):
    type: str
    message: str
    day: Optional[str] = None
    period: Optional[int] = None
