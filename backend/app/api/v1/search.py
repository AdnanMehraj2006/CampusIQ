"""Global search across searchable entities (permission-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.academic import Department
from app.models.assignment import Assignment
from app.models.comms import Announcement
from app.models.people import Faculty, Student
from app.models.project import Project
from app.models.subject import Subject
from app.models.user import User
from app.schemas import SearchResponse, SearchResultItem
from app.schemas.common import paginated
from app.services import announcement_service

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=dict)
def global_search(
    q: str,
    kind: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    """Debounced client-side; the backend enforces scoping on every entity."""
    term = (q or "").strip()
    if len(term) < 2:
        return paginated([], page_params["page"], page_params["page_size"], 0)

    items: list[dict] = []
    limit = page_params["page_size"]

    def add(type_, id_, title, subtitle, meta=None) -> None:
        items.append({"type": type_, "id": id_, "title": title, "subtitle": subtitle, "meta": meta or {}})

    is_staff = current_user.role in (Role.ADMIN, Role.HOD, Role.FACULTY)

    # ---- Students (staff only; CR sees own section) ----
    if kind in (None, "student") and (is_staff or current_user.role == Role.CR):
        qst = db.query(Student).join(User, User.id == Student.user_id).filter(
            or_(User.name.ilike(f"%{term}%"), User.email.ilike(f"%{term}%"), Student.enrollment_number.ilike(f"%{term}%"))
        )
        if current_user.role == Role.HOD and current_user.faculty_profile:
            qst = qst.filter(Student.department_id == current_user.faculty_profile.department_id)
        elif current_user.role == Role.FACULTY and current_user.faculty_profile:
            from app.models.subject import SubjectAssignment

            sections = [s[0] for s in db.query(SubjectAssignment.section)
                        .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id).distinct().all()]
            qst = qst.filter(Student.section.in_(sections) if sections else False)
        elif current_user.role == Role.CR and current_user.student_profile:
            qst = qst.filter(Student.section == current_user.student_profile.section)
        for s in qst.limit(limit).all():
            add("student", s.id, s.user.name, f"{s.enrollment_number} - Section {s.section}",
                {"section": s.section, "department_id": s.department_id})

    # ---- Faculty (staff only) ----
    if kind in (None, "faculty") and is_staff:
        qf = db.query(Faculty).join(User, User.id == Faculty.user_id).filter(
            or_(User.name.ilike(f"%{term}%"), User.email.ilike(f"%{term}%"))
        )
        if current_user.role == Role.HOD and current_user.faculty_profile:
            qf = qf.filter(Faculty.department_id == current_user.faculty_profile.department_id)
        for f in qf.limit(limit).all():
            add("faculty", f.id, f.name, f"{f.designation} - {f.email}", {"department_id": f.department_id})

    # ---- Subjects ----
    if kind in (None, "subject"):
        qs = db.query(Subject).filter(or_(Subject.name.ilike(f"%{term}%"), Subject.code.ilike(f"%{term}%")))
        if current_user.role == Role.HOD and current_user.faculty_profile:
            qs = qs.filter(Subject.department_id == current_user.faculty_profile.department_id)
        for s in qs.limit(limit).all():
            add("subject", s.id, f"{s.code} - {s.name}", f"{s.credits} credits", {"department_id": s.department_id})

    # ---- Departments (staff) ----
    if kind in (None, "department") and is_staff:
        for d in db.query(Department).filter(or_(Department.name.ilike(f"%{term}%"), Department.code.ilike(f"%{term}%"))).limit(limit).all():
            add("department", d.id, d.name, d.code, {})

    # ---- Assignments ----
    if kind in (None, "assignment"):
        qa = db.query(Assignment).filter(Assignment.title.ilike(f"%{term}%"))
        if current_user.role == Role.FACULTY and current_user.faculty_profile:
            qa = qa.filter(Assignment.faculty_id == current_user.faculty_profile.id)
        if current_user.role in (Role.STUDENT, Role.CR) and current_user.student_profile:
            from app.models.subject import Subject as SubjectModel

            ids = [s.id for s in db.query(SubjectModel).filter(SubjectModel.semester_id == current_user.student_profile.semester_id).all()]
            qa = qa.filter(Assignment.subject_id.in_(ids) if ids else False)
        for a in qa.limit(limit).all():
            add("assignment", a.id, a.title, f"{a.subject.name if a.subject else ''} - due {a.deadline}", {})

    # ---- Projects ----
    if kind in (None, "project"):
        qp = db.query(Project).filter(Project.title.ilike(f"%{term}%"))
        if current_user.role == Role.HOD and current_user.faculty_profile:
            qp = qp.filter(Project.department_id == current_user.faculty_profile.department_id)
        if current_user.role == Role.FACULTY and current_user.faculty_profile:
            qp = qp.filter((Project.supervisor_id == current_user.faculty_profile.id) | Project.supervisor_id.is_(None))
        for p in qp.limit(limit).all():
            add("project", p.id, p.title, f"{p.status} - {p.supervisor.user.name if p.supervisor and p.supervisor.user else ''}", {})

    # ---- Announcements (respect targeting) ----
    if kind in (None, "announcement"):
        qan = announcement_service.visible_announcements_query(db, current_user).filter(
            Announcement.title.ilike(f"%{term}%")
        )
        for a in qan.limit(limit).all():
            add("announcement", a.id, a.title, f"{a.priority} - {a.published_at}", {})

    total = len(items)
    return paginated(items[: page_params["page_size"]], page_params["page"], page_params["page_size"], total)
