"""Role-specific dashboards - every card is computed live from the database."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.datetime import as_utc

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_student, require_permission
from app.core.exceptions import ForbiddenError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.academic import AcademicSession, Course, Department
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.comms import Announcement, Notification
from app.models.marks import Mark
from app.models.people import Faculty, Student
from app.models.project import Project, ProjectStatus
from app.models.subject import Subject, SubjectAssignment
from app.models.timetable import Attendance, TimetableEntry
from app.models.user import User
from app.services import attendance_service
from app.services.announcement_service import visible_announcements_query

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


def _today_weekday() -> str:
    return date.today().strftime("%A")


# ---------------------------------------------------------------------------
# Student dashboard
# ---------------------------------------------------------------------------


@router.get("/student", response_model=dict)
def student_dashboard(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    user = student.user
    analytics = attendance_service.student_analytics(db, student.id)

    # Today's classes
    today = _today_weekday()
    today_classes = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.section == student.section, TimetableEntry.day == today)
        .order_by(TimetableEntry.period)
        .all()
    )

    # Upcoming assignments for the student's semester subjects
    subject_ids = [s.id for s in db.query(Subject).filter(Subject.semester_id == student.semester_id).all()]
    now = datetime.now(timezone.utc)
    upcoming_assignments = (
        db.query(Assignment)
        .filter(Assignment.subject_id.in_(subject_ids) if subject_ids else False, Assignment.deadline >= now)
        .order_by(Assignment.deadline.asc())
        .limit(5)
        .all()
    )
    assignment_rows = []
    for a in upcoming_assignments:
        sub = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == a.id, AssignmentSubmission.student_id == student.id
        ).first()
        assignment_rows.append(
            {
                "id": a.id,
                "title": a.title,
                "subject": a.subject.name if a.subject else None,
                "deadline": a.deadline,
                "max_marks": a.max_marks,
                "submitted": sub is not None,
                "days_left": (as_utc(a.deadline) - now).days if a.deadline else None,
            }
        )

    # Recent marks
    recent_marks = (
        db.query(Mark).filter(Mark.student_id == student.id).order_by(Mark.id.desc()).limit(5).all()
    )

    # Projects
    from app.models.project import ProjectGroup, ProjectGroupMember

    my_projects = (
        db.query(Project)
        .join(ProjectGroup, ProjectGroup.project_id == Project.id)
        .join(ProjectGroupMember, ProjectGroupMember.group_id == ProjectGroup.id)
        .filter(ProjectGroupMember.student_id == student.id)
        .distinct()
        .all()
    )
    project_rows = []
    for p in my_projects:
        total = len(p.milestones)
        done = sum(1 for m in p.milestones if m.status == "completed")
        project_rows.append(
            {
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "progress": round(done / total * 100, 1) if total else 0.0,
                "deadline": p.deadline,
            }
        )

    # Announcements
    announcements = (
        visible_announcements_query(db, user).order_by(Announcement.published_at.desc()).limit(5).all()
    )

    unread = db.query(Notification).filter(Notification.recipient_id == user.id, Notification.is_read.is_(False)).count()

    # Performance trend (by assessment type over time)
    perf_rows = (
        db.query(Mark).filter(Mark.student_id == student.id).order_by(Mark.created_at.asc()).limit(30).all()
    )

    return {
        "success": True,
        "role": str(user.role),
        "user": {"name": user.name, "email": user.email, "college_id": user.college_id, "role": str(user.role)},
        "cards": [
            {"label": "Overall Attendance", "value": f"{analytics['overall_percentage']}%",
             "sublabel": f"{analytics['classes_attended']}/{analytics['classes_conducted']} classes", "trend": None},
            {"label": "Attendance Zone", "value": analytics["zone"].upper(),
             "sublabel": f"Required {analytics['required_percentage']:g}%", "trend": None},
            {"label": "Classes Today", "value": len(today_classes), "sublabel": today, "trend": None},
            {"label": "Pending Assignments", "value": sum(1 for a in assignment_rows if not a["submitted"]),
             "sublabel": f"{len(assignment_rows)} upcoming", "trend": None},
            {"label": "Active Projects", "value": len([p for p in project_rows if p["status"] in ("approved", "in_progress")]),
             "sublabel": None, "trend": None},
            {"label": "Unread Notifications", "value": unread, "sublabel": None, "trend": None},
        ],
        "attendance": analytics,
        "today_classes": [
            {
                "period": c.period,
                "subject": c.subject.name if c.subject else None,
                "faculty": c.faculty.user.name if c.faculty and c.faculty.user else None,
                "room": c.classroom.room_number if c.classroom else None,
                "time": f"{c.start_time or ''} - {c.end_time or ''}",
            }
            for c in today_classes
        ],
        "upcoming_assignments": assignment_rows,
        "upcoming_exams": [
            {"id": m.id, "title": m.title, "subject": m.subject.name if m.subject else None,
             "type": m.assessment_type, "max_marks": float(m.max_marks)}
            for m in db.query(Mark).filter(Mark.student_id == student.id,
                                           Mark.assessment_type.in_(["internal_exam", "midterm", "end_semester"]))
            .order_by(Mark.id.desc()).limit(3).all()
        ],
        "projects": project_rows,
        "recent_marks": [
            {"id": m.id, "title": m.title, "subject": m.subject.name if m.subject else None,
             "marks": float(m.marks), "max_marks": float(m.max_marks)}
            for m in recent_marks
        ],
        "announcements": [
            {"id": a.id, "title": a.title, "priority": a.priority, "published_at": a.published_at}
            for a in announcements
        ],
        "performance_trend": [
            {"label": m.title, "percentage": m.percentage, "subject": m.subject.name if m.subject else None}
            for m in perf_rows
        ],
        "section": student.section,
        "semester_number": student.semester.semester_number if student.semester else None,
        "department_name": student.department.name if student.department else None,
    }


# ---------------------------------------------------------------------------
# Faculty dashboard
# ---------------------------------------------------------------------------


@router.get("/faculty", response_model=dict)
def faculty_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MARK_ATTENDANCE)),
):
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    fac = current_user.faculty_profile
    today = _today_weekday()

    subjects = attendance_service.faculty_subjects(db, fac.id)
    subject_ids = [s.id for s in subjects]

    today_classes = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.faculty_id == fac.id, TimetableEntry.day == today)
        .order_by(TimetableEntry.period)
        .all()
    )

    sections = [s[0] for s in db.query(SubjectAssignment.section).filter(SubjectAssignment.faculty_id == fac.id).distinct().all()]

    # Attendance pending: subjects with no record today
    pending = []
    for s in subjects:
        for sec in sections:
            has_today = db.query(Attendance).filter(Attendance.subject_id == s.id, Attendance.date == date.today()).first()
            roster = attendance_service.students_in_section(db, sec, s.id)
            if roster and not has_today:
                pending.append({"subject_id": s.id, "subject": s.name, "section": sec, "students": len(roster)})

    now = datetime.now(timezone.utc)
    assignments = (
        db.query(Assignment)
        .filter(Assignment.faculty_id == fac.id, Assignment.deadline >= now)
        .order_by(Assignment.deadline.asc())
        .limit(5)
        .all()
    )

    submissions_pending = (
        db.query(AssignmentSubmission)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .filter(Assignment.faculty_id == fac.id, AssignmentSubmission.grade.is_(None))
        .count()
    )

    projects = db.query(Project).filter(Project.supervisor_id == fac.id).all()

    announcements = (
        visible_announcements_query(db, current_user).order_by(Announcement.published_at.desc()).limit(5).all()
    )

    # Class performance overview for the first section taught
    class_overview = attendance_service.class_attendance_overview(db, sections[0]) if sections else None

    unread = db.query(Notification).filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False)).count()

    return {
        "success": True,
        "role": str(current_user.role),
        "user": {"name": current_user.name, "email": current_user.email, "designation": fac.designation},
        "cards": [
            {"label": "Assigned Subjects", "value": len(subjects), "sublabel": None, "trend": None},
            {"label": "Classes Today", "value": len(today_classes), "sublabel": today, "trend": None},
            {"label": "Attendance Pending", "value": len(pending), "sublabel": "subjects not marked today", "trend": None},
            {"label": "Submissions to Grade", "value": submissions_pending, "sublabel": None, "trend": None},
            {"label": "Supervised Projects", "value": len(projects), "sublabel": None, "trend": None},
            {"label": "Unread Notifications", "value": unread, "sublabel": None, "trend": None},
        ],
        "subjects": [{"id": s.id, "name": s.name, "code": s.code, "credits": s.credits} for s in subjects],
        "sections": sections,
        "today_classes": [
            {
                "period": c.period,
                "section": c.section,
                "subject": c.subject.name if c.subject else None,
                "room": c.classroom.room_number if c.classroom else None,
                "time": f"{c.start_time or ''} - {c.end_time or ''}",
            }
            for c in today_classes
        ],
        "attendance_pending": pending,
        "assignments": [
            {"id": a.id, "title": a.title, "deadline": a.deadline, "subject": a.subject.name if a.subject else None}
            for a in assignments
        ],
        "projects": [
            {"id": p.id, "title": p.title, "status": p.status, "groups": len(p.groups), "deadline": p.deadline}
            for p in projects
        ],
        "announcements": [
            {"id": a.id, "title": a.title, "priority": a.priority, "published_at": a.published_at} for a in announcements
        ],
        "class_overview": class_overview,
        "quick_actions": [
            {"key": "mark_attendance", "label": "Mark Attendance"},
            {"key": "create_assignment", "label": "Create Assignment"},
            {"key": "enter_marks", "label": "Enter Marks"},
            {"key": "post_announcement", "label": "Post Announcement"},
            {"key": "view_students", "label": "View Students"},
            {"key": "manage_project", "label": "Manage Project"},
        ],
    }


# ---------------------------------------------------------------------------
# HOD dashboard
# ---------------------------------------------------------------------------


@router.get("/hod", response_model=dict)
def hod_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_DEPARTMENT_ANALYTICS)),
):
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    fac = current_user.faculty_profile
    dept_id = fac.department_id
    dept = fac.department

    students = db.query(Student).join(User, User.id == Student.user_id).filter(
        Student.department_id == dept_id, User.status == "active"
    ).all()
    faculty_rows = db.query(Faculty).filter(Faculty.department_id == dept_id).all()
    subjects = db.query(Subject).filter(Subject.department_id == dept_id).all()
    projects = db.query(Project).filter(Project.department_id == dept_id).all()

    # Department attendance
    total_attended = total_conducted = 0
    student_rows = []
    below_threshold = []
    for s in students:
        stats = attendance_service._student_subject_stats(db, s.id)
        att = sum(v["attended"] for v in stats.values())
        con = sum(v["conducted"] for v in stats.values())
        pct = round(att / con * 100, 2) if con else 0.0
        total_attended += att
        total_conducted += con
        student_rows.append({"id": s.id, "name": s.user.name, "percentage": pct, "section": s.section})
        if con > 0 and pct < settings_attendance_threshold():
            below_threshold.append({"id": s.id, "name": s.user.name, "percentage": pct, "section": s.section})

    dept_attendance = round(total_attended / total_conducted * 100, 2) if total_conducted else 0.0
    student_rows.sort(key=lambda x: x["percentage"])

    # Academic attention: students averaging < 50% in marks
    needs_attention = []
    for s in students:
        marks = db.query(Mark).filter(Mark.student_id == s.id).all()
        if marks:
            total = sum(float(m.marks) for m in marks)
            mx = sum(float(m.max_marks) for m in marks)
            if mx:
                p = round(total / mx * 100, 2)
                if p < 50:
                    needs_attention.append({"id": s.id, "name": s.user.name, "percentage": p})

    # Subject performance
    subject_perf = []
    for sub in subjects:
        marks = db.query(Mark).filter(Mark.subject_id == sub.id).all()
        if marks:
            total = sum(float(m.marks) for m in marks)
            mx = sum(float(m.max_marks) for m in marks)
            subject_perf.append(
                {"subject_id": sub.id, "subject": sub.name, "code": sub.code,
                 "average": round(total / mx * 100, 2) if mx else 0.0, "count": len(marks)}
            )
    subject_perf.sort(key=lambda x: x["average"])

    # Faculty workload
    workload = []
    for f in faculty_rows:
        workload.append(
            {
                "id": f.id,
                "name": f.name,
                "designation": f.designation,
                "subjects": db.query(SubjectAssignment).filter(SubjectAssignment.faculty_id == f.id).count(),
                "periods": db.query(TimetableEntry).filter(TimetableEntry.faculty_id == f.id).count(),
            }
        )

    unread = db.query(Notification).filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False)).count()

    return {
        "success": True,
        "role": str(current_user.role),
        "user": {"name": current_user.name, "department": dept.name if dept else None},
        "department": {"id": dept.id, "name": dept.name, "code": dept.code if dept else None},
        "cards": [
            {"label": "Total Students", "value": len(students), "sublabel": None, "trend": None},
            {"label": "Total Faculty", "value": len(faculty_rows), "sublabel": None, "trend": None},
            {"label": "Average Attendance", "value": f"{dept_attendance}%",
             "sublabel": f"{len(below_threshold)} below threshold", "trend": None},
            {"label": "Subjects", "value": len(subjects), "sublabel": None, "trend": None},
            {"label": "Active Projects", "value": len([p for p in projects if p.status in ("approved", "in_progress")]),
             "sublabel": f"{len(projects)} total", "trend": None},
            {"label": "Unread Notifications", "value": unread, "sublabel": None, "trend": None},
        ],
        "charts": {
            "attendance_zones": _zone_breakdown(student_rows),
            "subject_performance": [{"name": s["subject"], "average": s["average"]} for s in subject_perf[-10:]],
            "faculty_workload": [{"name": w["name"], "periods": w["periods"]} for w in workload],
        },
        "students_below_threshold": below_threshold,
        "students_needing_attention": needs_attention,
        "subject_performance": subject_perf,
        "faculty_workload": workload,
        "projects": [
            {"id": p.id, "title": p.title, "status": p.status, "supervisor": p.supervisor.user.name if p.supervisor and p.supervisor.user else None}
            for p in projects
        ],
    }


def settings_attendance_threshold() -> float:
    from app.config import settings

    return settings.attendance_threshold


def _zone_breakdown(student_rows: list[dict]) -> list[dict]:
    zones = {"safe": 0, "warning": 0, "critical": 0, "none": 0}
    for s in student_rows:
        zones[attendance_service.zone_for(s["percentage"])] = zones.get(attendance_service.zone_for(s["percentage"]), 0) + 1
    return [{"name": k.title(), "value": v} for k, v in zones.items() if v or k == "none"]


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------


@router.get("/admin", response_model=dict)
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_SYSTEM_ANALYTICS)),
):
    total_students = db.query(Student).join(User, User.id == Student.user_id).filter(User.status == "active").count()
    total_faculty = db.query(Faculty).count()
    total_departments = db.query(Department).count()
    total_subjects = db.query(Subject).count()
    total_courses = db.query(Course).count()
    active_session = db.query(AcademicSession).filter(AcademicSession.is_active.is_(True)).first()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status.in_([ProjectStatus.APPROVED, ProjectStatus.IN_PROGRESS])).count()
    total_assignments = db.query(Assignment).count()
    total_announcements = db.query(Announcement).count()
    total_classes = db.query(TimetableEntry).count()

    # System-wide attendance
    conducted = db.query(Attendance).count()
    attended = db.query(Attendance).filter(Attendance.status.in_(["present", "late"])).count()
    overall_attendance = round(attended / conducted * 100, 2) if conducted else 0.0

    # Students by department
    by_dept = []
    for d in db.query(Department).all():
        by_dept.append(
            {
                "name": d.name,
                "students": db.query(Student).join(User, User.id == Student.user_id)
                .filter(Student.department_id == d.id, User.status == "active").count(),
                "faculty": db.query(Faculty).filter(Faculty.department_id == d.id).count(),
            }
        )

    unread = db.query(Notification).filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False)).count()
    recent_announcements = (
        db.query(Announcement).order_by(Announcement.published_at.desc()).limit(5).all()
    )

    return {
        "success": True,
        "role": str(current_user.role),
        "user": {"name": current_user.name, "email": current_user.email},
        "cards": [
            {"label": "Total Students", "value": total_students, "sublabel": None, "trend": None},
            {"label": "Total Faculty", "value": total_faculty, "sublabel": None, "trend": None},
            {"label": "Departments", "value": total_departments, "sublabel": f"{total_courses} courses", "trend": None},
            {"label": "Active Users", "value": f"{active_users}/{total_users}", "sublabel": "active accounts", "trend": None},
            {"label": "Subjects", "value": total_subjects, "sublabel": f"{total_classes} timetable slots", "trend": None},
            {"label": "Overall Attendance", "value": f"{overall_attendance}%", "sublabel": f"{conducted} records", "trend": None},
            {"label": "Active Projects", "value": active_projects, "sublabel": f"{total_projects} total", "trend": None},
            {"label": "Announcements", "value": total_announcements, "sublabel": f"{total_assignments} assignments", "trend": None},
        ],
        "active_session": {"id": active_session.id, "name": active_session.name} if active_session else None,
        "charts": {
            "students_by_department": by_dept,
            "attendance_zones": _zone_breakdown(
                [
                    {"percentage": attendance_service.student_analytics(db, s.id)["overall_percentage"]}
                    for s in db.query(Student).join(User, User.id == Student.user_id)
                    .filter(User.status == "active").limit(200).all()
                ]
            ),
        },
        "announcements": [
            {"id": a.id, "title": a.title, "priority": a.priority, "published_at": a.published_at} for a in recent_announcements
        ],
        "unread_notifications": unread,
    }


# ---------------------------------------------------------------------------
# CR dashboard
# ---------------------------------------------------------------------------


@router.get("/cr", response_model=dict)
def cr_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUBMIT_REQUESTS)),
):
    if current_user.student_profile is None:
        raise ForbiddenError("No student profile is linked to your account.")
    st = current_user.student_profile

    overview = attendance_service.class_attendance_overview(db, st.section)
    timetable = (
        db.query(TimetableEntry).filter(TimetableEntry.section == st.section).order_by(TimetableEntry.day, TimetableEntry.period).all()
    )
    announcements = (
        visible_announcements_query(db, current_user).order_by(Announcement.published_at.desc()).limit(5).all()
    )
    from app.models.comms import CRRequest

    my_requests = db.query(CRRequest).filter(CRRequest.submitted_by == current_user.id).order_by(CRRequest.id.desc()).limit(5).all()
    unread = db.query(Notification).filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False)).count()

    return {
        "success": True,
        "role": str(current_user.role),
        "user": {"name": current_user.name, "section": st.section},
        "section": st.section,
        "cards": [
            {"label": "Class Average Attendance", "value": f"{overview['overall']}%", "sublabel": f"Section {st.section}", "trend": None},
            {"label": "Students Below Threshold",
             "value": len([s for s in overview["students"] if s["zone"] != "safe"]),
             "sublabel": f"threshold {settings_attendance_threshold():g}%", "trend": None},
            {"label": "Classes This Week", "value": len(timetable), "sublabel": None, "trend": None},
            {"label": "Open Requests", "value": len([r for r in my_requests if r.status == "open"]), "sublabel": None, "trend": None},
            {"label": "Unread Notifications", "value": unread, "sublabel": None, "trend": None},
        ],
        "class_overview": overview,
        "timetable": [
            {"day": str(e.day), "period": e.period, "subject": e.subject.name if e.subject else None,
             "faculty": e.faculty.user.name if e.faculty and e.faculty.user else None}
            for e in timetable
        ],
        "announcements": [{"id": a.id, "title": a.title, "priority": a.priority, "published_at": a.published_at} for a in announcements],
        "my_requests": [
            {"id": r.id, "title": r.title, "type": r.request_type, "status": r.status, "created_at": r.created_at}
            for r in my_requests
        ],
    }


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


@router.get("/me", response_model=dict)
def my_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    """Redirect-style helper: returns the role-appropriate dashboard summary."""
    role = str(current_user.role)
    if role in ("student", "cr"):
        return student_dashboard(db=db, student=current_user.student_profile)
    if role == "faculty":
        return faculty_dashboard(db=db, current_user=current_user)
    if role == "hod":
        return hod_dashboard(db=db, current_user=current_user)
    if role == "admin":
        return admin_dashboard(db=db, current_user=current_user)
    raise ForbiddenError("No dashboard is available for your role.")
