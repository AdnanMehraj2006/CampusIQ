"""Project, milestone, announcement and notification schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.comms import AnnouncementTarget, NotificationType, Priority
from app.models.project import MilestoneStatus, ProjectStatus
from app.schemas.common import ORMModel


# ---- Projects ----
class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    department_id: Optional[int] = None
    semester_id: Optional[int] = None
    supervisor_id: int
    deadline: Optional[datetime] = None
    max_group_size: int = Field(4, ge=1, le=10)


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    deadline: Optional[datetime] = None
    supervisor_id: Optional[int] = None


class ProjectOut(ORMModel):
    id: int
    title: str
    description: Optional[str] = None
    project_code: Optional[str] = None
    department_id: Optional[int] = None
    semester_id: Optional[int] = None
    supervisor_id: int
    status: str
    deadline: Optional[datetime] = None
    max_group_size: int
    created_at: Optional[datetime] = None
    supervisor_name: Optional[str] = None
    department_name: Optional[str] = None
    group_count: Optional[int] = None
    member_names: Optional[List[str]] = None
    progress_percentage: Optional[float] = None
    my_group_id: Optional[int] = None


class ProjectGroupCreate(BaseModel):
    project_id: int
    name: Optional[str] = None
    proposal: Optional[str] = None
    member_ids: List[int] = Field(..., min_length=1)


class ProjectGroupOut(ORMModel):
    id: int
    project_id: int
    name: Optional[str] = None
    proposal: Optional[str] = None
    status: str
    approved: bool
    approved_at: Optional[datetime] = None
    project_title: Optional[str] = None
    supervisor_name: Optional[str] = None
    members: Optional[List[dict]] = None


class MilestoneCreate(BaseModel):
    project_id: int
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    deadline: Optional[datetime] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[MilestoneStatus] = None
    feedback: Optional[str] = None


class MilestoneSubmission(BaseModel):
    submission_text: Optional[str] = None


class MilestoneOut(ORMModel):
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    order_index: int
    deadline: Optional[datetime] = None
    status: str
    submission_text: Optional[str] = None
    submitted_at: Optional[datetime] = None
    feedback: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    project_title: Optional[str] = None
    is_overdue: Optional[bool] = None


# ---- Announcements ----
class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    target_type: AnnouncementTarget = AnnouncementTarget.EVERYONE
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: Optional[str] = None
    priority: Priority = Priority.NORMAL
    expiry_at: Optional[datetime] = None
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    target_type: Optional[AnnouncementTarget] = None
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: Optional[str] = None
    priority: Optional[Priority] = None
    expiry_at: Optional[datetime] = None
    is_pinned: Optional[bool] = None


class AnnouncementOut(ORMModel):
    id: int
    title: str
    content: str
    summary: Optional[str] = None
    target_type: str
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    semester_id: Optional[int] = None
    section: Optional[str] = None
    priority: str
    published_by: int
    attachment_name: Optional[str] = None
    published_at: datetime
    expiry_at: Optional[datetime] = None
    is_pinned: bool
    author_name: Optional[str] = None
    author_role: Optional[str] = None


# ---- Notifications ----
class NotificationOut(ORMModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    created_at: Optional[datetime] = None


class NotificationSummary(BaseModel):
    unread_count: int
    total: int
    by_type: dict


# ---- Feedback / CR requests ----
class FeedbackCreate(BaseModel):
    target_type: str = Field("subject", max_length=30)
    subject_id: Optional[int] = None
    department_id: Optional[int] = None
    section: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=5)


class FeedbackOut(ORMModel):
    id: int
    submitted_by: int
    target_type: str
    subject_id: Optional[int] = None
    department_id: Optional[int] = None
    section: Optional[str] = None
    rating: int
    message: str
    status: str
    response: Optional[str] = None
    author_name: Optional[str] = None
    subject_name: Optional[str] = None
    created_at: Optional[datetime] = None


class CRRequestCreate(BaseModel):
    request_type: str = Field("other", max_length=50)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    section: Optional[str] = None
    department_id: Optional[int] = None


class CRRequestOut(ORMModel):
    id: int
    submitted_by: int
    request_type: str
    title: str
    description: str
    status: str
    resolution_note: Optional[str] = None
    section: Optional[str] = None
    author_name: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogOut(ORMModel):
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    role: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[dict] = None
    created_at: Optional[datetime] = None
