"""Academic-structure schemas: departments, courses, sessions, semesters,
subjects, classrooms."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ---- Departments ----
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    hod_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    hod_id: Optional[int] = None


class DepartmentOut(ORMModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    hod_id: Optional[int] = None
    hod_name: Optional[str] = None
    student_count: Optional[int] = None
    faculty_count: Optional[int] = None


# ---- Courses ----
class CourseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)
    department_id: int
    duration_years: int = Field(4, ge=1, le=8)
    description: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    duration_years: Optional[int] = Field(None, ge=1, le=8)
    description: Optional[str] = None


class CourseOut(ORMModel):
    id: int
    name: str
    code: str
    department_id: int
    duration_years: int
    description: Optional[str] = None
    department_name: Optional[str] = None
    student_count: Optional[int] = None


# ---- Academic sessions ----
class AcademicSessionBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True


class AcademicSessionCreate(AcademicSessionBase):
    pass


class AcademicSessionUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class AcademicSessionOut(ORMModel):
    id: int
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool


# ---- Semesters ----
class SemesterBase(BaseModel):
    semester_number: int = Field(..., ge=1, le=12)
    academic_session_id: Optional[int] = None
    course_id: Optional[int] = None


class SemesterCreate(SemesterBase):
    pass


class SemesterOut(ORMModel):
    id: int
    semester_number: int
    academic_session_id: Optional[int] = None
    course_id: Optional[int] = None


# ---- Sections ----
class SectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=200)


class SectionCreate(SectionBase):
    is_active: bool = True


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class SectionOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    student_count: Optional[int] = None


# ---- Subjects ----
class SubjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)
    credits: int = Field(4, ge=1, le=10)
    semester_id: Optional[int] = None
    department_id: int
    weekly_periods: int = Field(3, ge=1, le=10)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = Field(None, ge=1, le=10)
    semester_id: Optional[int] = None
    weekly_periods: Optional[int] = Field(None, ge=1, le=10)


class SubjectOut(ORMModel):
    id: int
    name: str
    code: str
    credits: int
    semester_id: Optional[int] = None
    department_id: int
    weekly_periods: int
    department_name: Optional[str] = None
    semester_number: Optional[int] = None


# ---- Subject assignments ----
class SubjectAssignmentCreate(BaseModel):
    subject_id: int
    faculty_id: int
    section: str = Field("A", max_length=10)
    semester_id: Optional[int] = None


class SubjectAssignmentOut(ORMModel):
    id: int
    subject_id: int
    faculty_id: int
    section: str
    semester_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    faculty_name: Optional[str] = None


# ---- Class teachers ----
class ClassTeacherCreate(BaseModel):
    faculty_id: int
    section: str = Field("A", max_length=10)
    semester_id: Optional[int] = None


class ClassTeacherOut(ORMModel):
    id: int
    faculty_id: int
    section: str
    semester_id: Optional[int] = None
    faculty_name: Optional[str] = None


# ---- Classrooms ----
class ClassroomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    building: str = Field("Main Block", max_length=100)
    capacity: int = Field(60, ge=1, le=1000)
    room_type: str = Field("Lecture Hall", max_length=50)


class ClassroomCreate(ClassroomBase):
    pass


class ClassroomUpdate(BaseModel):
    room_number: Optional[str] = None
    building: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1, le=1000)
    room_type: Optional[str] = None


class ClassroomOut(ORMModel):
    id: int
    room_number: str
    building: str
    capacity: int
    room_type: str
