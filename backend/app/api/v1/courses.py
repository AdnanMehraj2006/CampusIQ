"""Course and semester management (admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.academic import AcademicSession, Course, Semester
from app.models.people import Student
from app.models.user import User
from app.schemas import (
    AcademicSessionCreate,
    AcademicSessionOut,
    AcademicSessionUpdate,
    CourseCreate,
    CourseOut,
    CourseUpdate,
    SemesterCreate,
    SemesterOut,
)
from app.schemas.common import paginated
from app.services.audit_service import log_from_request

router = APIRouter(tags=["Academic Structure"])


# ---------------- Courses ----------------


def _course_out(c: Course, db: Session) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "code": c.code,
        "department_id": c.department_id,
        "duration_years": c.duration_years,
        "description": c.description,
        "department_name": c.department.name if c.department else None,
        "student_count": db.query(Student).filter(Student.course_id == c.id).count(),
    }


@router.get("/courses", response_model=dict)
def list_courses(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Course)
    if department_id:
        q = q.filter(Course.department_id == department_id)
    if page_params["q"]:
        q = q.filter(Course.name.ilike(f"%{page_params['q']}%") | Course.code.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Course.id).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_course_out(c, db) for c in rows], page_params["page"], page_params["page_size"], total)


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(
    payload: CourseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COURSES)),
):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise ConflictError("Course code already exists.")
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    log_from_request(db, request, current_user, "course.create", "course", resource_id=course.id)
    return _course_out(course, db)


@router.put("/courses/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COURSES)),
):
    course = db.get(Course, course_id)
    if not course:
        raise NotFoundError("Course not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    db.commit()
    db.refresh(course)
    log_from_request(db, request, current_user, "course.update", "course", resource_id=course.id)
    return _course_out(course, db)


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COURSES)),
):
    course = db.get(Course, course_id)
    if not course:
        raise NotFoundError("Course not found.")
    log_from_request(db, request, current_user, "course.delete", "course", resource_id=course.id)
    db.delete(course)
    db.commit()
    return {"success": True, "message": "Course deleted."}


# ---------------- Academic sessions ----------------


@router.get("/academic-sessions", response_model=list)
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS))):
    return [dict(id=s.id, name=s.name, start_date=s.start_date, end_date=s.end_date, is_active=s.is_active)
            for s in db.query(AcademicSession).order_by(AcademicSession.id.desc()).all()]


@router.post("/academic-sessions", response_model=AcademicSessionOut, status_code=201)
def create_session(
    payload: AcademicSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ACADEMIC_SESSIONS)),
):
    if payload.is_active:
        db.query(AcademicSession).filter(AcademicSession.is_active.is_(True)).update({AcademicSession.is_active: False})
    session = AcademicSession(**payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    log_from_request(db, request, current_user, "session.create", "academic_session", resource_id=session.id)
    return session


@router.put("/academic-sessions/{session_id}", response_model=AcademicSessionOut)
def update_session(
    session_id: int,
    payload: AcademicSessionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ACADEMIC_SESSIONS)),
):
    session = db.get(AcademicSession, session_id)
    if not session:
        raise NotFoundError("Academic session not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_active"):
        db.query(AcademicSession).filter(AcademicSession.id != session_id, AcademicSession.is_active.is_(True)).update(
            {AcademicSession.is_active: False}
        )
    for k, v in data.items():
        setattr(session, k, v)
    db.commit()
    db.refresh(session)
    log_from_request(db, request, current_user, "session.update", "academic_session", resource_id=session.id)
    return session


# ---------------- Semesters ----------------


@router.get("/semesters", response_model=list)
def list_semesters(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Semester)
    if course_id:
        q = q.filter(Semester.course_id == course_id)
    return [{"id": s.id, "semester_number": s.semester_number,
             "academic_session_id": s.academic_session_id, "course_id": s.course_id}
            for s in q.order_by(Semester.semester_number).all()]


@router.post("/semesters", response_model=SemesterOut, status_code=201)
def create_semester(
    payload: SemesterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ACADEMIC_SESSIONS)),
):
    existing = db.query(Semester).filter(
        Semester.semester_number == payload.semester_number,
        ((Semester.course_id == payload.course_id) if payload.course_id else Semester.course_id.is_(None)),
    ).first()
    if existing:
        raise ConflictError("This semester already exists for the selected course.")
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    return semester
