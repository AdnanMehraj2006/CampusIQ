"""Roles and the permission matrix used for RBAC.

Authorization is enforced on the backend for *every* protected endpoint
(see ``app.core.deps``). The frontend only uses roles to decide which UI to
render - it never acts as the authority.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    HOD = "hod"
    FACULTY = "faculty"
    CR = "cr"
    STUDENT = "student"


class Permission(StrEnum):
    # System / users
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_SYSTEM_ANALYTICS = "view_system_analytics"

    # Academic structure
    MANAGE_DEPARTMENTS = "manage_departments"
    MANAGE_COURSES = "manage_courses"
    MANAGE_SECTIONS = "manage_sections"
    VIEW_SECTIONS = "view_sections"
    MANAGE_SUBJECTS = "manage_subjects"
    MANAGE_CLASSROOMS = "manage_classrooms"
    MANAGE_ACADEMIC_SESSIONS = "manage_academic_sessions"
    MANAGE_TIMETABLE = "manage_timetable"
    GENERATE_TIMETABLE = "generate_timetable"

    # People
    MANAGE_STUDENTS = "manage_students"
    MANAGE_FACULTY = "manage_faculty"
    VIEW_STUDENTS = "view_students"
    VIEW_FACULTY = "view_faculty"

    # Attendance
    MARK_ATTENDANCE = "mark_attendance"
    EDIT_ATTENDANCE = "edit_attendance"
    VIEW_ATTENDANCE = "view_attendance"
    VIEW_CLASS_ATTENDANCE = "view_class_attendance"

    # Assignments / marks
    MANAGE_ASSIGNMENTS = "manage_assignments"
    SUBMIT_ASSIGNMENTS = "submit_assignments"
    GRADE_ASSIGNMENTS = "grade_assignments"
    ENTER_MARKS = "enter_marks"
    VIEW_OWN_MARKS = "view_own_marks"
    VIEW_CLASS_MARKS = "view_class_marks"

    # Projects
    MANAGE_PROJECTS = "manage_projects"
    SUPERVISE_PROJECTS = "supervise_projects"
    JOIN_PROJECTS = "join_projects"
    SUBMIT_MILESTONES = "submit_milestones"

    # Comms
    PUBLISH_ANNOUNCEMENTS = "publish_announcements"
    VIEW_ANNOUNCEMENTS = "view_announcements"
    SUBMIT_REQUESTS = "submit_requests"
    SUBMIT_FEEDBACK = "submit_feedback"

    # Analytics & reports
    VIEW_DEPARTMENT_ANALYTICS = "view_department_analytics"
    VIEW_OWN_ANALYTICS = "view_own_analytics"
    GENERATE_REPORTS = "generate_reports"

    # AI
    USE_AI_ASSISTANT = "use_ai_assistant"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.HOD: {
        Permission.VIEW_DEPARTMENT_ANALYTICS,
        Permission.MANAGE_STUDENTS,
        Permission.MANAGE_FACULTY,
        Permission.VIEW_STUDENTS,
        Permission.VIEW_FACULTY,
        Permission.VIEW_ATTENDANCE,
        Permission.VIEW_CLASS_ATTENDANCE,
        Permission.VIEW_CLASS_MARKS,
        Permission.MANAGE_PROJECTS,
        Permission.SUPERVISE_PROJECTS,
        Permission.PUBLISH_ANNOUNCEMENTS,
        Permission.VIEW_ANNOUNCEMENTS,
        Permission.GENERATE_REPORTS,
        Permission.USE_AI_ASSISTANT,
        Permission.SUBMIT_REQUESTS,
        Permission.VIEW_SECTIONS,
    },
    Role.FACULTY: {
        Permission.MARK_ATTENDANCE,
        Permission.EDIT_ATTENDANCE,
        Permission.VIEW_ATTENDANCE,
        Permission.VIEW_CLASS_ATTENDANCE,
        Permission.MANAGE_ASSIGNMENTS,
        Permission.GRADE_ASSIGNMENTS,
        Permission.ENTER_MARKS,
        Permission.VIEW_CLASS_MARKS,
        Permission.VIEW_STUDENTS,
        Permission.SUPERVISE_PROJECTS,
        Permission.MANAGE_PROJECTS,
        Permission.PUBLISH_ANNOUNCEMENTS,
        Permission.VIEW_ANNOUNCEMENTS,
        Permission.GENERATE_REPORTS,
        Permission.USE_AI_ASSISTANT,
        Permission.SUBMIT_FEEDBACK,
        Permission.VIEW_SECTIONS,
    },
    Role.CR: {
        Permission.VIEW_ANNOUNCEMENTS,
        Permission.VIEW_CLASS_ATTENDANCE,
        Permission.VIEW_ATTENDANCE,  # own + own class, scoped in services
        Permission.SUBMIT_REQUESTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.USE_AI_ASSISTANT,
        Permission.VIEW_STUDENTS,
        Permission.VIEW_SECTIONS,
    },
    Role.STUDENT: {
        Permission.VIEW_OWN_MARKS,
        Permission.VIEW_ATTENDANCE,  # own only - scoped in services
        Permission.VIEW_OWN_ANALYTICS,
        Permission.SUBMIT_ASSIGNMENTS,
        Permission.JOIN_PROJECTS,
        Permission.SUBMIT_MILESTONES,
        Permission.VIEW_ANNOUNCEMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.USE_AI_ASSISTANT,
    },
}


def permissions_for_role(role: Role | str) -> set[Permission]:
    """Return the full permission set granted to ``role``."""
    try:
        r = Role(role)
    except (ValueError, TypeError):
        return set()
    return ROLE_PERMISSIONS.get(r, set())


def role_has_permission(role: Role | str, permission: Permission | str) -> bool:
    perm = Permission(permission) if isinstance(permission, str) else permission
    return perm in permissions_for_role(role)
