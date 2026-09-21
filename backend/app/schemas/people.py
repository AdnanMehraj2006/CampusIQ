"""Student and faculty profile schemas + user management."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.core.permissions import Role
from app.schemas.auth import UserPublic
from app.schemas.common import ORMModel


class StudentCreate(BaseModel):
    """Admin creates a student profile (and its user account if needed)."""

    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    college_id: str = Field(..., min_length=3, max_length=32)
    enrollment_number: str = Field(..., min_length=3, max_length=32)
    department_id: int
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: str = Field("A", max_length=10)
    admission_year: int = Field(..., ge=2000, le=2100)
    phone: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    is_cr: bool = False
    password: Optional[str] = Field(None, min_length=6, description="If omitted, a secure random password is generated")


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    is_cr: Optional[bool] = None


class StudentOut(ORMModel):
    id: int
    user_id: int
    enrollment_number: str
    department_id: int
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: str
    admission_year: int
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    # joined
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str
    college_id: str
    department_name: Optional[str] = None
    course_name: Optional[str] = None
    semester_number: Optional[int] = None
    attendance_percentage: Optional[float] = None
    # Surfaced exactly once when the account is created with a server-generated
    # password; never persisted (only the hash is).
    initial_password: Optional[str] = None


class FacultyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    college_id: str = Field(..., min_length=3, max_length=32)
    department_id: int
    designation: str = Field("Assistant Professor", max_length=100)
    specialization: Optional[str] = None
    phone: Optional[str] = None
    is_hod: bool = False
    password: Optional[str] = Field(None, min_length=6)


class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    specialization: Optional[str] = None
    is_hod: Optional[bool] = None


class FacultyOut(ORMModel):
    id: int
    user_id: int
    department_id: int
    designation: str
    specialization: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str
    college_id: str
    department_name: Optional[str] = None
    subject_count: Optional[int] = None
    is_hod: Optional[bool] = None
    initial_password: Optional[str] = None


class UserUpdateAdmin(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[Role] = None
    status: Optional[str] = None


class UserOutAdmin(UserPublic):
    created_at: Optional[str] = None
    must_change_password: Optional[bool] = None
