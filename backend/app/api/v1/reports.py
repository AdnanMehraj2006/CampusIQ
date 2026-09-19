"""Report generation: attendance, performance, workload, project progress.

Exports are CSV (for spreadsheets) and PDF (for printing). All data is scoped
by the same rules as the corresponding list endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.academic import Department
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.marks import Mark
from app.models.people import Faculty, Student
from app.models.project import Project
from app.models.subject import Subject, SubjectAssignment
from app.models.timetable import Attendance, TimetableEntry
from app.models.user import User
from app.services import attendance_service, report_service

router = APIRouter(prefix="/reports", tags=["Reports"])

_CSV_HEADERS = {
    "Content-Type": "text/csv",
    "Content-Disposition": 'attachment; filename="{name}.csv"',
}
_PDF_HEADERS = {
    "Content-Type": "application/pdf",
    "Content-Disposition": 'attachment; filename="{name}.pdf"',
}


def _scope_students(db: Session, current_user: User) -> list[Student]:
    q = db.query(Student).join(User, User.id == Student.user_id).filter(User.status == "active")
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Student.department_id == current_user.faculty_profile.department_id)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        sections = [s[0] for s in db.query(SubjectAssignment.section)
                    .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id).distinct().all()]
        q = q.filter(Student.section.in_(sections) if sections else False)
    if current_user.role == Role.CR and current_user.student_profile:
        q = q.filter(Student.section == current_user.student_profile.section)
    if current_user.role == Role.STUDENT and current_user.student_profile:
        q = q.filter(Student.id == current_user.student_profile.id)
    return q.order_by(User.name).all()


def _check_scope(current_user: User) -> None:
    if current_user.role not in (Role.ADMIN, Role.HOD, Role.FACULTY):
        raise ForbiddenError("Only academic staff can generate reports.")


@router.get("/attendance")
def attendance_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    section: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    _check_scope(current_user)
    students = _scope_students(db, current_user)
    if section:
        students = [s for s in students if s.section == section]
    if not students:
        raise NotFoundError("No students match the report scope.")

    rows = []
    for s in students:
        a = attendance_service.student_analytics(db, s.id)
        rows.append(
            {
                "name": s.user.name,
                "enrollment": s.enrollment_number,
                "section": s.section,
                "department": s.department.name if s.department else "",
                "attended": a["classes_attended"],
                "conducted": a["classes_conducted"],
                "percentage": a["overall_percentage"],
                "zone": a["zone"],
            }
        )
    title = "Attendance Report"
    subtitle = f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC - {len(rows)} student(s)"
    if format == "csv":
        data = report_service.build_csv(rows)
        return Response(content=data, headers={k: v.format(name="attendance_report") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        title,
        subtitle,
        [
            {
                "heading": "Student Attendance",
                "columns": ["Name", "Enrollment", "Section", "Attended", "Conducted", "%", "Zone"],
                "rows": [[r["name"], r["enrollment"], r["section"], r["attended"], r["conducted"], r["percentage"], r["zone"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="attendance_report") for k, v in _PDF_HEADERS.items()})


@router.get("/performance")
def performance_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    _check_scope(current_user)
    students = _scope_students(db, current_user)
    rows = []
    for s in students:
        marks = db.query(Mark).filter(Mark.student_id == s.id).all()
        if not marks:
            continue
        total = sum(float(m.marks) for m in marks)
        mx = sum(float(m.max_marks) for m in marks)
        rows.append(
            {
                "name": s.user.name,
                "enrollment": s.enrollment_number,
                "section": s.section,
                "assessments": len(marks),
                "total": total,
                "max": mx,
                "percentage": round(total / mx * 100, 2) if mx else 0.0,
            }
        )
    if not rows:
        raise NotFoundError("No marks records match the report scope.")
    if format == "csv":
        data = report_service.build_csv(rows)
        return Response(content=data, headers={k: v.format(name="performance_report") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        "Student Performance Report",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        [
            {
                "heading": "Performance Summary",
                "columns": ["Name", "Enrollment", "Section", "Assessments", "Total", "Max", "%"],
                "rows": [[r["name"], r["enrollment"], r["section"], r["assessments"], r["total"], r["max"], r["percentage"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="performance_report") for k, v in _PDF_HEADERS.items()})


@router.get("/faculty-workload")
def faculty_workload_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    if current_user.role not in (Role.ADMIN, Role.HOD):
        raise ForbiddenError("Only admin or HOD can generate faculty workload reports.")
    q = db.query(Faculty)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Faculty.department_id == current_user.faculty_profile.department_id)
    rows = []
    for f in q.all():
        rows.append(
            {
                "name": f.name,
                "department": f.department.name if f.department else "",
                "designation": f.designation,
                "subjects": db.query(SubjectAssignment).filter(SubjectAssignment.faculty_id == f.id).count(),
                "weekly_periods": db.query(TimetableEntry).filter(TimetableEntry.faculty_id == f.id).count(),
            }
        )
    if format == "csv":
        return Response(content=report_service.build_csv(rows),
                        headers={k: v.format(name="faculty_workload") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        "Faculty Workload Report",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        [
            {
                "heading": "Faculty Workload",
                "columns": ["Name", "Department", "Designation", "Subjects", "Periods/week"],
                "rows": [[r["name"], r["department"], r["designation"], r["subjects"], r["weekly_periods"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="faculty_workload") for k, v in _PDF_HEADERS.items()})


@router.get("/project-progress")
def project_progress_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    _check_scope(current_user)
    q = db.query(Project)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Project.department_id == current_user.faculty_profile.department_id)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        q = q.filter(Project.supervisor_id == current_user.faculty_profile.id)

    rows = []
    for p in q.all():
        total = len(p.milestones)
        done = sum(1 for m in p.milestones if m.status == "completed")
        rows.append(
            {
                "title": p.title,
                "supervisor": p.supervisor.user.name if p.supervisor and p.supervisor.user else "",
                "status": p.status,
                "groups": len(p.groups),
                "milestones": total,
                "completed": done,
                "progress": round(done / total * 100, 1) if total else 0.0,
                "deadline": p.deadline.strftime("%Y-%m-%d") if p.deadline else "",
            }
        )
    if not rows:
        raise NotFoundError("No projects match the report scope.")
    if format == "csv":
        return Response(content=report_service.build_csv(rows),
                        headers={k: v.format(name="project_progress") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        "Project Progress Report",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        [
            {
                "heading": "Project Progress",
                "columns": ["Title", "Supervisor", "Status", "Groups", "Milestones", "Completed", "%", "Deadline"],
                "rows": [[r["title"], r["supervisor"], r["status"], r["groups"], r["milestones"], r["completed"], r["progress"], r["deadline"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="project_progress") for k, v in _PDF_HEADERS.items()})


@router.get("/assignment-submissions")
def assignment_submission_report(
    assignment_id: int,
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        if a.faculty_id != current_user.faculty_profile.id:
            raise ForbiddenError("You can only report on your own assignments.")
    if current_user.role == Role.HOD and current_user.faculty_profile:
        if a.faculty.department_id != current_user.faculty_profile.department_id:
            raise ForbiddenError("This assignment belongs to another department.")

    roster = attendance_service.students_in_section(db, a.section or "", a.subject_id) if a.section else []
    if not roster:
        roster = (
            db.query(Student).join(User, User.id == Student.user_id)
            .filter(Student.semester_id == a.subject.semester_id if a.subject and a.subject.semester_id else None)
            .all()
        )
    subs = {s.student_id: s for s in db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == a.id).all()}

    rows = []
    for s in roster:
        sub = subs.get(s.id)
        rows.append(
            {
                "name": s.user.name,
                "enrollment": s.enrollment_number,
                "section": s.section,
                "submitted": "yes" if sub else "no",
                "late": "yes" if (sub and sub.is_late) else "no",
                "grade": sub.grade if sub and sub.grade is not None else "",
            }
        )
    if format == "csv":
        return Response(content=report_service.build_csv(rows),
                        headers={k: v.format(name="assignment_submissions") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        f"Submissions: {a.title}",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        [
            {
                "heading": f"{a.subject.name if a.subject else ''} - {a.title}",
                "columns": ["Name", "Enrollment", "Section", "Submitted", "Late", "Grade"],
                "rows": [[r["name"], r["enrollment"], r["section"], r["submitted"], r["late"], r["grade"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="assignment_submissions") for k, v in _PDF_HEADERS.items()})


@router.get("/department")
def department_report(
    department_id: int | None = None,
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    if current_user.role == Role.HOD and current_user.faculty_profile:
        department_id = current_user.faculty_profile.department_id
    if current_user.role == Role.FACULTY:
        raise ForbiddenError("Faculty cannot generate department-wide reports.")
    q = db.query(Department)
    if department_id:
        q = q.filter(Department.id == department_id)
    rows = []
    for d in q.all():
        students = db.query(Student).join(User, User.id == Student.user_id).filter(
            Student.department_id == d.id, User.status == "active"
        ).all()
        att = con = 0
        for s in students:
            stats = attendance_service._student_subject_stats(db, s.id)
            att += sum(v["attended"] for v in stats.values())
            con += sum(v["conducted"] for v in stats.values())
        rows.append(
            {
                "department": d.name,
                "code": d.code,
                "students": len(students),
                "faculty": db.query(Faculty).filter(Faculty.department_id == d.id).count(),
                "subjects": db.query(Subject).filter(Subject.department_id == d.id).count(),
                "attendance": round(att / con * 100, 2) if con else 0.0,
            }
        )
    if not rows:
        raise NotFoundError("No departments match the report scope.")
    if format == "csv":
        return Response(content=report_service.build_csv(rows),
                        headers={k: v.format(name="department_report") for k, v in _CSV_HEADERS.items()})
    pdf = report_service.build_pdf(
        "Department Performance Report",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        [
            {
                "heading": "Departments",
                "columns": ["Department", "Code", "Students", "Faculty", "Subjects", "Attendance %"],
                "rows": [[r["department"], r["code"], r["students"], r["faculty"], r["subjects"], r["attendance"]] for r in rows],
            }
        ],
    )
    return Response(content=pdf, headers={k: v.format(name="department_report") for k, v in _PDF_HEADERS.items()})
