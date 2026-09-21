"""Class teacher assignments and classroom management."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.academic import ClassTeacher
from app.models.people import Faculty
from app.models.user import User
from app.schemas import ClassTeacherCreate, ClassTeacherOut
from app.schemas.common import paginated

router = APIRouter(tags=["Academic"])


def _class_teacher_out(db: Session, ct: ClassTeacher) -> dict:
    return {
        "id": ct.id,
        "faculty_id": ct.faculty_id,
        "section": ct.section,
        "semester_id": ct.semester_id,
        "faculty_name": ct.faculty.user.name if ct.faculty and ct.faculty.user else None,
    }


@router.get("/class-teachers", response_model=dict)
def list_class_teachers(
    section: str | None = None,
    semester_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_FACULTY)),
):
    q = db.query(ClassTeacher)
    if section:
        q = q.filter(ClassTeacher.section == section)
    if semester_id:
        q = q.filter(ClassTeacher.semester_id == semester_id)
    total = q.count()
    rows = q.order_by(ClassTeacher.section, ClassTeacher.semester_id).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_class_teacher_out(db, ct) for ct in rows], page_params["page"], page_params["page_size"], total)


@router.post("/class-teachers", response_model=ClassTeacherOut, status_code=201)
def create_class_teacher(
    payload: ClassTeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    faculty = db.get(Faculty, payload.faculty_id)
    if not faculty:
        raise NotFoundError("Faculty member not found.")

    existing = (
        db.query(ClassTeacher)
        .filter(ClassTeacher.faculty_id == payload.faculty_id, ClassTeacher.section == payload.section, ClassTeacher.semester_id == payload.semester_id)
        .first()
    )
    if existing:
        raise BadRequestError("A class teacher already exists for this faculty/section/semester combination.")

    ct = ClassTeacher(
        faculty_id=payload.faculty_id,
        section=payload.section,
        semester_id=payload.semester_id,
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return _class_teacher_out(db, ct)


@router.delete("/class-teachers/{teacher_id}")
def delete_class_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    ct = db.get(ClassTeacher, teacher_id)
    if not ct:
        raise NotFoundError("Class teacher assignment not found.")
    db.delete(ct)
    db.commit()
    return {"success": True, "message": "Class teacher assignment removed."}
