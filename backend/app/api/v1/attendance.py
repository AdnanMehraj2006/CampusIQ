"""Attendance marking, viewing, analytics and prediction."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import (
    get_current_student,
    pagination_params,
    require_permission,
)
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.people import Student
from app.models.subject import Subject
from app.models.timetable import Attendance, AttendanceStatus
from app.models.user import User
from app.schemas import (
    AttendanceAnalytics,
    AttendanceCreateRequest,
    AttendanceOut,
    AttendancePrediction,
    AttendanceUpdateRequest,
)
from app.schemas.common import paginated
from app.services import attendance_service
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _record_out(r: Attendance) -> dict:
    return {
        "id": r.id,
        "student_id": r.student_id,
        "subject_id": r.subject_id,
        "date": r.date.isoformat() if r.date else None,
        "status": r.status,
        "marked_by": r.marked_by,
        "note": r.note,
        "student_name": r.student.user.name if r.student and r.student.user else None,
        "enrollment_number": r.student.enrollment_number if r.student else None,
        "subject_name": r.subject.name if r.subject else None,
    }


@router.get("", response_model=dict)
def list_attendance(
    student_id: int | None = None,
    subject_id: int | None = None,
    section: str | None = None,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ATTENDANCE)),
):
    q = db.query(Attendance)
    viewer = current_user

    if viewer.role == Role.STUDENT or viewer.role == Role.CR:
        me = viewer.student_profile
        if me is None:
            raise ForbiddenError("No student profile is linked to your account.")
        if viewer.role == Role.STUDENT:
            q = q.filter(Attendance.student_id == me.id)
        else:  # CR: view attendance for their own Department + Semester + Section
            if section and section != me.section:
                raise ForbiddenError("You can only view attendance for your own section.")
            q = q.join(Student, Student.id == Attendance.student_id).filter(
                Student.department_id == me.department_id,
                Student.semester_id == me.semester_id,
                Student.section == me.section,
            )
    elif viewer.role == Role.FACULTY:
        if viewer.faculty_profile is None:
            raise ForbiddenError("No faculty profile is linked to your account.")
        from app.models.subject import SubjectAssignment

        subject_ids = [s.id for s in attendance_service.faculty_subjects(db, viewer.faculty_profile.id)]
        if not subject_ids:
            raise ForbiddenError("You have no assigned subjects.")
        q = q.filter(Attendance.subject_id.in_(subject_ids))
        if section:
            q = q.join(Student, Student.id == Attendance.student_id).filter(Student.section == section)
    elif viewer.role == Role.HOD:
        if viewer.faculty_profile is not None:
            q = q.join(Student, Student.id == Attendance.student_id).filter(
                Student.department_id == viewer.faculty_profile.department_id
            )

    if student_id:
        q = q.filter(Attendance.student_id == student_id)
    if subject_id:
        q = q.filter(Attendance.subject_id == subject_id)
    if start_date:
        q = q.filter(Attendance.date >= start_date)
    if end_date:
        q = q.filter(Attendance.date <= end_date)
    if status:
        q = q.filter(Attendance.status == status)

    total = q.count()
    rows = (
        q.order_by(Attendance.date.desc(), Attendance.id.desc())
        .offset(page_params["offset"])
        .limit(page_params["page_size"])
        .all()
    )
    return paginated([_record_out(r) for r in rows], page_params["page"], page_params["page_size"], total)


@router.post("", response_model=list[AttendanceOut], status_code=201)
def mark_attendance(
    payload: AttendanceCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MARK_ATTENDANCE)),
):
    marks = {m.student_id: m.status for m in payload.marks}
    records = attendance_service.mark_attendance(
        db,
        subject_id=payload.subject_id,
        section=payload.section,
        on_date=payload.date,
        marks=marks,
        marked_by=current_user,
    )
    log_from_request(
        db, request, current_user, "attendance.mark", "attendance",
        resource_id=payload.subject_id,
        details={"section": payload.section, "date": payload.date.isoformat(), "count": len(records)},
    )
    return [_record_out(r) for r in records]


@router.put("/{record_id}", response_model=AttendanceOut)
def update_attendance(
    record_id: int,
    payload: AttendanceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EDIT_ATTENDANCE)),
):
    record = attendance_service.update_attendance(
        db, record_id, status=payload.status, note=payload.note, actor=current_user
    )
    log_from_request(
        db, request, current_user, "attendance.edit", "attendance",
        resource_id=record.id, details={"status": payload.status},
    )
    return _record_out(record)


@router.delete("/{record_id}")
def delete_attendance(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EDIT_ATTENDANCE)),
):
    record = db.get(Attendance, record_id)
    if not record:
        raise NotFoundError("Attendance record not found.")
    if current_user.role != "admin":
        if current_user.faculty_profile is None:
            raise ForbiddenError("No faculty profile is linked to your account.")
        from app.models.subject import SubjectAssignment

        assigned = (
            db.query(SubjectAssignment)
            .filter(
                SubjectAssignment.subject_id == record.subject_id,
                SubjectAssignment.faculty_id == current_user.faculty_profile.id,
            )
            .first()
        )
        if not assigned:
            raise ForbiddenError("You can only delete attendance for your own subjects.")
    log_from_request(db, request, current_user, "attendance.delete", "attendance", resource_id=record.id)
    db.delete(record)
    db.commit()
    return {"success": True, "message": "Attendance record deleted."}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics/me", response_model=AttendanceAnalytics)
def my_attendance_analytics(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    return attendance_service.student_analytics(db, student.id)


@router.get("/analytics/student/{student_id}", response_model=AttendanceAnalytics)
def student_attendance_analytics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ATTENDANCE)),
):
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    from app.api.v1.people import _assert_student_scope

    _assert_student_scope(db, current_user, s)
    return attendance_service.student_analytics(db, s.id)


@router.get("/analytics/section/{section}", response_model=dict)
def section_attendance_analytics(
    section: str,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_CLASS_ATTENDANCE)),
):
    if current_user.role == Role.CR:
        me = current_user.student_profile
        if me is None:
            raise ForbiddenError("Your account has no student profile.")
        # A CR may only view their own class context (Department + Semester + Section).
        if me.section != section or me.department_id is None or me.semester_id is None:
            raise ForbiddenError("You can only view analytics for your own class.")
        return attendance_service.class_attendance_overview(
            db, section, subject_id, department_id=me.department_id, semester_id=me.semester_id
        )
    if current_user.role == Role.FACULTY:
        from app.models.subject import SubjectAssignment

        teaches = (
            db.query(SubjectAssignment)
            .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id, SubjectAssignment.section == section)
            .first()
        )
        if not teaches:
            raise ForbiddenError("You can only view analytics for sections you teach.")
    if current_user.role == Role.HOD and current_user.faculty_profile:
        enrolled = (
            db.query(Student).filter(Student.section == section, Student.department_id == current_user.faculty_profile.department_id).count()
        )
        if not enrolled:
            raise ForbiddenError("No such section in your department.")
    return attendance_service.class_attendance_overview(db, section, subject_id)


@router.get("/predict/me", response_model=AttendancePrediction)
def predict_my_attendance(
    required_percentage: float | None = Query(None, ge=1, le=99),
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    return attendance_service.predict_attendance(db, student.id, required_percentage)


@router.get("/predict/student/{student_id}", response_model=AttendancePrediction)
def predict_student_attendance(
    student_id: int,
    required_percentage: float | None = Query(None, ge=1, le=99),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ATTENDANCE)),
):
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    from app.api.v1.people import _assert_student_scope

    _assert_student_scope(db, current_user, s)
    return attendance_service.predict_attendance(db, s.id, required_percentage)


@router.get("/roster/{subject_id}/{section}")
def attendance_roster(
    subject_id: int,
    section: str,
    on_date: date_type | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MARK_ATTENDANCE)),
):
    """Roster with existing statuses for a subject/section/date (marking screen)."""
    if current_user.role not in ("admin",):
        attendance_service.assert_faculty_owns_subject(
            db, current_user.faculty_profile.id if current_user.faculty_profile else 0, subject_id, section
        )
    roster = attendance_service.students_in_section(db, section, subject_id)
    statuses = {}
    if on_date:
        rows = db.query(Attendance).filter(
            Attendance.subject_id == subject_id, Attendance.date == on_date,
            Attendance.student_id.in_([s.id for s in roster]),
        ).all()
        statuses = {r.student_id: r.status for r in rows}
    return {
        "subject_id": subject_id,
        "section": section,
        "date": on_date.isoformat() if on_date else None,
        "already_marked": bool(statuses),
        "students": [
            {
                "student_id": s.id,
                "name": s.user.name,
                "enrollment_number": s.enrollment_number,
                "status": statuses.get(s.id),
            }
            for s in roster
        ],
    }


@router.get("/my", response_model=dict)
def faculty_attendance_history(
    page_params: dict = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MARK_ATTENDANCE)),
):
    """Attendance records submitted by the authenticated faculty member.

    Identity is derived from the authenticated user only; no faculty id is
    accepted from the client, so one faculty member can never read another's
    submissions.
    """
    if current_user.role != Role.FACULTY:
        raise ForbiddenError("Only faculty can view their attendance history.")
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    q = db.query(Attendance).filter(Attendance.marked_by == current_user.id)
    total = q.count()
    rows = (
        q.order_by(Attendance.date.desc(), Attendance.id.desc())
        .offset(page_params["offset"])
        .limit(page_params["page_size"])
        .all()
    )
    out = []
    for r in rows:
        subject = db.get(Subject, r.subject_id)
        student = db.get(Student, r.student_id)
        out.append({
            "id": r.id,
            "date": r.date.isoformat() if r.date else None,
            "subject_id": r.subject_id,
            "subject_name": subject.name if subject else None,
            "subject_code": subject.code if subject else None,
            "student_id": r.student_id,
            "student_name": student.user.name if student and student.user else None,
            "enrollment_number": student.enrollment_number if student else None,
            "section": student.section if student else None,
            "status": r.status,
            "note": r.note,
            "marked_by": r.marked_by,
        })
    return paginated(out, page_params["page"], page_params["page_size"], total)
