"""Import every mapped model so SQLAlchemy/Alembic can discover the metadata."""

from app.models.academic import AcademicSession, ClassTeacher, Course, Department, Semester
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.classroom import Classroom
from app.models.comms import (
    Announcement,
    AnnouncementTarget,
    AuditLog,
    CRRequest,
    Feedback,
    Notification,
    NotificationType,
    Priority,
    SystemSetting,
)
from app.models.marks import AssessmentType, Mark
from app.models.people import Faculty, Student
from app.models.project import (
    MilestoneStatus,
    Project,
    ProjectGroup,
    ProjectGroupMember,
    ProjectMilestone,
    ProjectStatus,
)
from app.models.subject import Subject, SubjectAssignment
from app.models.timetable import (
    Attendance,
    AttendanceStatus,
    DayOfWeek,
    TimetableEntry,
    WORKING_DAYS,
)
from app.models.user import RefreshToken, User, UserStatus
from app.database import Base

__all__ = [
    "Base",
    "AcademicSession",
    "Announcement",
    "ClassTeacher",
    "AnnouncementTarget",
    "AssessmentType",
    "Assignment",
    "AssignmentSubmission",
    "Attendance",
    "AttendanceStatus",
    "AuditLog",
    "Classroom",
    "Course",
    "CRRequest",
    "DayOfWeek",
    "Department",
    "Faculty",
    "Feedback",
    "Mark",
    "MilestoneStatus",
    "Notification",
    "NotificationType",
    "Priority",
    "Project",
    "ProjectGroup",
    "ProjectGroupMember",
    "ProjectMilestone",
    "ProjectStatus",
    "RefreshToken",
    "Semester",
    "Student",
    "Subject",
    "SubjectAssignment",
    "SystemSetting",
    "TimetableEntry",
    "User",
    "UserStatus",
    "WORKING_DAYS",
]
