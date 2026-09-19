"""Subject and subject-assignment management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import check_department_scope, pagination_params, require_permission
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.academic import Department, Semester
from app.models.subject import Subject, SubjectAssignment
from app.models.user import User
from app.schemas import (
    SubjectAssignmentCreate,
    SubjectAssignmentOut,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
)
from app.schemas.common import paginated
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/subjects", tags=["Subjects"])


def _subject_out(s: Subject) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "code": s.code,
        "credits": s.credits,
        "semester_id": s.semester_id,
        "department_id": s.department_id,
        "weekly_periods": s.weekly_periods,
        "department_name": s.department.name if s.department else None,
        "semester_number": s.semester.semester_number if s.semester else None,
    }


@router.get("", response_model=dict)
def list_subjects(
    department_id: int | None = None,
    semester_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Subject)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Subject.department_id == current_user.faculty_profile.department_id)
    if department_id:
        q = q.filter(Subject.department_id == department_id)
    if semester_id:
        q = q.filter(Subject.semester_id == semester_id)
    if page_params["q"]:
        q = q.filter(Subject.name.ilike(f"%{page_params['q']}%") | Subject.code.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Subject.code).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_subject_out(s) for s in rows], page_params["page"], page_params["page_size"], total)


@router.get("/all", response_model=list)
def list_all_subjects(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Subject)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Subject.department_id == current_user.faculty_profile.department_id)
    if department_id:
        q = q.filter(Subject.department_id == department_id)
    return [{"id": s.id, "name": s.name, "code": s.code, "department_id": s.department_id} for s in q.order_by(Subject.code).all()]


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SUBJECTS)),
):
    if current_user.role == Role.HOD:
        check_department_scope(current_user, payload.department_id)
    if db.query(Subject).filter(Subject.code == payload.code, Subject.department_id == payload.department_id).first():
        raise ConflictError("A subject with this code already exists in this department.")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    log_from_request(db, request, current_user, "subject.create", "subject", resource_id=subject.id)
    return _subject_out(subject)


@router.put("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SUBJECTS)),
):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, subject.department_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(subject, k, v)
    db.commit()
    db.refresh(subject)
    log_from_request(db, request, current_user, "subject.update", "subject", resource_id=subject.id)
    return _subject_out(subject)


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SUBJECTS)),
):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, subject.department_id)
    log_from_request(db, request, current_user, "subject.delete", "subject", resource_id=subject.id)
    db.delete(subject)
    db.commit()
    return {"success": True, "message": "Subject deleted."}


# ---------------- Faculty-subject assignments ----------------


@router.get("/assignments", response_model=dict)
def list_assignments(
    faculty_id: int | None = None,
    section: str | None = None,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(SubjectAssignment)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        q = q.filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(SubjectAssignment.faculty.has(department_id=current_user.faculty_profile.department_id))
    if faculty_id:
        q = q.filter(SubjectAssignment.faculty_id == faculty_id)
    if section:
        q = q.filter(SubjectAssignment.section == section)
    if subject_id:
        q = q.filter(SubjectAssignment.subject_id == subject_id)
    total = q.count()
    rows = q.order_by(SubjectAssignment.id).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    items = [
        {
            "id": a.id,
            "subject_id": a.subject_id,
            "faculty_id": a.faculty_id,
            "section": a.section,
            "semester_id": a.semester_id,
            "subject_name": a.subject.name if a.subject else None,
            "subject_code": a.subject.code if a.subject else None,
            "faculty_name": a.faculty.user.name if a.faculty and a.faculty.user else None,
        }
        for a in rows
    ]
    return paginated(items, page_params["page"], page_params["page_size"], total)


@router.post("/assignments", response_model=SubjectAssignmentOut, status_code=201)
def create_assignment(
    payload: SubjectAssignmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SUBJECTS)),
):
    subject = db.get(Subject, payload.subject_id)
    if not subject:
        raise NotFoundError("Subject not found.")
    from app.models.people import Faculty

    faculty = db.get(Faculty, payload.faculty_id)
    if not faculty:
        raise NotFoundError("Faculty member not found.")

    if current_user.role == Role.HOD:
        check_department_scope(current_user, subject.department_id)
        check_department_scope(current_user, faculty.department_id)

    if (
        db.query(SubjectAssignment)
        .filter(
            SubjectAssignment.subject_id == payload.subject_id,
            SubjectAssignment.faculty_id == payload.faculty_id,
            SubjectAssignment.section == payload.section,
        )
        .first()
    ):
        raise ConflictError("This faculty member is already assigned to this subject and section.")

    assignment = SubjectAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    log_from_request(
        db, request, current_user, "subject.assign", "subject_assignment", resource_id=assignment.id,
        details={"subject_id": payload.subject_id, "faculty_id": payload.faculty_id, "section": payload.section},
    )
    return assignment


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SUBJECTS)),
):
    assignment = db.get(SubjectAssignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment not found.")
    if current_user.role == Role.HOD and assignment.faculty:
        check_department_scope(current_user, assignment.faculty.department_id)
    log_from_request(db, request, current_user, "subject.unassign", "subject_assignment", resource_id=assignment.id)
    db.delete(assignment)
    db.commit()
    return {"success": True, "message": "Assignment removed."}


@router.get("/my", response_model=list)
def my_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MARK_ATTENDANCE)),
):
    """Subjects taught by the authenticated faculty member."""
    from app.services.attendance_service import faculty_subjects

    if not current_user.faculty_profile:
        raise ForbiddenError("No faculty profile is linked to your account.")
    return [
        {
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "credits": s.credits,
            "weekly_periods": s.weekly_periods,
            "department_id": s.department_id,
        }
        for s in faculty_subjects(db, current_user.faculty_profile.id)
    ]
