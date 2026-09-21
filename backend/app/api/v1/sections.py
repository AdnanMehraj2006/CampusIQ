"""Section management API.

Sections are the canonical source for class-grouping values (they are *never*
hardcoded in the UI). Admins manage them; other roles read them for selectors.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.academic import Section
from app.models.people import Student
from app.schemas import SectionCreate, SectionOut, SectionUpdate
from app.schemas.common import paginated
from app.services.audit_service import log_from_request

router = APIRouter(tags=["Sections"])


def _section_out(db: Session, s: Section) -> dict:
    student_count = db.query(Student).filter(Student.section == s.name).count()
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "is_active": s.is_active,
        "student_count": student_count,
    }


def _assert_not_refered(db: Session, section: Section) -> None:
    """Block hard deletion while academic records still use this section.

    Deactivating (``is_active = False``) is the safe alternative: it hides the
    section from new selectors without touching existing rows.
    """
    name = section.name
    reasons: list[str] = []

    student_count = db.query(Student).filter(Student.section == name).count()
    if student_count:
        reasons.append(f"{student_count} student(s)")

    from app.models.subject import SubjectAssignment
    from app.models.academic import ClassTeacher
    from app.models.timetable import TimetableEntry
    from app.models.assignment import Assignment
    from app.models.comms import Announcement, Feedback

    if db.query(SubjectAssignment).filter(SubjectAssignment.section == name).count():
        reasons.append("subject assignments")
    if db.query(ClassTeacher).filter(ClassTeacher.section == name).count():
        reasons.append("class teachers")
    if db.query(TimetableEntry).filter(TimetableEntry.section == name).count():
        reasons.append("timetable entries")
    if db.query(Assignment).filter(Assignment.section == name).count():
        reasons.append("assignments")
    if db.query(Announcement).filter(Announcement.section == name).count():
        reasons.append("announcements")
    if db.query(Feedback).filter(Feedback.section == name).count():
        reasons.append("feedback")

    if reasons:
        raise ConflictError(
            f"Section '{name}' is still referenced by {', '.join(reasons)}. "
            "Deactivate it instead of deleting it."
        )


@router.get("/sections", response_model=dict)
def list_sections(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user=Depends(require_permission(Permission.VIEW_SECTIONS)),
):
    q = db.query(Section)
    if is_active is not None:
        q = q.filter(Section.is_active == is_active)
    if page_params["q"]:
        q = q.filter(Section.name.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Section.name).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_section_out(db, s) for s in rows], page_params["page"], page_params["page_size"], total)


@router.get("/sections/all", response_model=list[dict])
def list_all_sections(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permission.VIEW_SECTIONS)),
):
    """All active sections, for dropdowns/selectors."""
    sections = db.query(Section).filter(Section.is_active.is_(True)).order_by(Section.name).all()
    return [_section_out(db, s) for s in sections]


@router.get("/sections/{section_id}", response_model=dict)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permission.VIEW_SECTIONS)),
):
    section = db.get(Section, section_id)
    if not section:
        raise NotFoundError("Section not found.")
    return _section_out(db, section)


@router.post("/sections", response_model=dict, status_code=201)
def create_section(
    payload: SectionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permission.MANAGE_SECTIONS)),
):
    name = payload.name.strip()
    if not name:
        raise BadRequestError("Section name is required.")
    if db.query(Section).filter(Section.name == name).first():
        raise ConflictError(f"A section named '{name}' already exists.")

    section = Section(
        name=name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    log_from_request(db, request, current_user, "section.create", "section", resource_id=section.id)
    return _section_out(db, section)


@router.put("/sections/{section_id}", response_model=dict)
def update_section(
    section_id: int,
    payload: SectionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permission.MANAGE_SECTIONS)),
):
    section = db.get(Section, section_id)
    if not section:
        raise NotFoundError("Section not found.")

    data = payload.model_dump(exclude_unset=True)
    name = (data.get("name") or "").strip() if "name" in data else None
    if name:
        if name != section.name and db.query(Section).filter(Section.name == name).first():
            raise ConflictError(f"A section named '{name}' already exists.")
        if db.query(Student).filter(Student.section == section.name).count():
            raise BadRequestError(
                "Rename is not allowed while students are still assigned to this section."
            )
        section.name = name
    if "description" in data:
        section.description = data["description"]
    if "is_active" in data:
        section.is_active = data["is_active"]

    db.commit()
    db.refresh(section)
    log_from_request(db, request, current_user, "section.update", "section", resource_id=section.id)
    return _section_out(db, section)


@router.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permission.MANAGE_SECTIONS)),
):
    section = db.get(Section, section_id)
    if not section:
        raise NotFoundError("Section not found.")
    _assert_not_refered(db, section)
    log_from_request(db, request, current_user, "section.delete", "section", resource_id=section.id)
    db.delete(section)
    db.commit()
    return {"success": True, "message": f"Section '{section.name}' removed."}
