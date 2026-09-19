"""Timetable management, conflict detection and automatic generation."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.timetable import TimetableEntry
from app.models.user import User
from app.schemas import (
    TimetableEntryCreate,
    TimetableEntryOut,
    TimetableEntryUpdate,
    TimetableGenerateRequest,
    TimetableGenerateResult,
)
from app.schemas.common import paginated
from app.services import timetable_service
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/timetable", tags=["Timetable"])


def _entry_out(e: TimetableEntry) -> dict:
    return {
        "id": e.id,
        "day": str(e.day),
        "period": e.period,
        "start_time": e.start_time,
        "end_time": e.end_time,
        "subject_id": e.subject_id,
        "faculty_id": e.faculty_id,
        "classroom_id": e.classroom_id,
        "section": e.section,
        "semester_id": e.semester_id,
        "subject_name": e.subject.name if e.subject else None,
        "subject_code": e.subject.code if e.subject else None,
        "faculty_name": e.faculty.user.name if e.faculty and e.faculty.user else None,
        "room_number": e.classroom.room_number if e.classroom else None,
    }


@router.get("", response_model=dict)
def list_timetable(
    section: str | None = None,
    faculty_id: int | None = None,
    day: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(TimetableEntry)
    if current_user.role == Role.FACULTY and current_user.faculty_profile and not section and not faculty_id:
        q = q.filter(TimetableEntry.faculty_id == current_user.faculty_profile.id)
    if current_user.role in (Role.STUDENT, Role.CR) and current_user.student_profile and not section:
        q = q.filter(TimetableEntry.section == current_user.student_profile.section)
    if current_user.role == Role.HOD and current_user.faculty_profile and not section and not faculty_id:
        from app.models.people import Faculty as FacultyModel
        from app.models.subject import SubjectAssignment

        dept_sections = (
            db.query(SubjectAssignment.section)
            .join(FacultyModel, FacultyModel.id == SubjectAssignment.faculty_id)
            .filter(FacultyModel.department_id == current_user.faculty_profile.department_id)
            .distinct()
        )
        q = q.filter(TimetableEntry.section.in_([s[0] for s in dept_sections]))
    if section:
        q = q.filter(TimetableEntry.section == section)
    if faculty_id:
        q = q.filter(TimetableEntry.faculty_id == faculty_id)
    if day:
        q = q.filter(TimetableEntry.day == day)
    total = q.count()
    rows = q.order_by(TimetableEntry.day, TimetableEntry.period).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_entry_out(e) for e in rows], page_params["page"], page_params["page_size"], total)


@router.get("/section/{section}", response_model=list[TimetableEntryOut])
def section_timetable(
    section: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    if current_user.role == Role.CR and current_user.student_profile and current_user.student_profile.section != section:
        raise ForbiddenError("You can only view your own section's timetable.")
    if current_user.role == Role.STUDENT and current_user.student_profile and current_user.student_profile.section != section:
        raise ForbiddenError("You can only view your own section's timetable.")
    return [_entry_out(e) for e in timetable_service.section_timetable(db, section)]


@router.get("/my", response_model=list[TimetableEntryOut])
def my_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    if current_user.student_profile:
        return [_entry_out(e) for e in timetable_service.section_timetable(db, current_user.student_profile.section)]
    if current_user.faculty_profile:
        return [_entry_out(e) for e in timetable_service.faculty_timetable(db, current_user.faculty_profile.id)]
    raise ForbiddenError("No student or faculty profile is linked to your account.")


@router.post("", response_model=TimetableEntryOut, status_code=201)
def create_entry(
    payload: TimetableEntryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_TIMETABLE)),
):
    entry = timetable_service.add_entry(db, entry_in=payload.model_dump(), actor_id=current_user.id)
    log_from_request(
        db, request, current_user, "timetable.create", "timetable", resource_id=entry.id,
        details={"section": payload.section, "day": str(payload.day), "period": payload.period},
    )
    return _entry_out(entry)


@router.put("/{entry_id}", response_model=TimetableEntryOut)
def update_entry(
    entry_id: int,
    payload: TimetableEntryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_TIMETABLE)),
):
    entry = db.get(TimetableEntry, entry_id)
    if not entry:
        raise NotFoundError("Timetable entry not found.")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(entry, k, v)
    # Re-validate conflicts for the modified row.
    conflicts = timetable_service.check_conflicts(
        db,
        day=str(entry.day),
        period=entry.period,
        section=entry.section,
        faculty_id=entry.faculty_id,
        classroom_id=entry.classroom_id,
        academic_session_id=entry.academic_session_id,
        exclude_entry_id=entry.id,
    )
    if conflicts:
        from app.core.exceptions import TimetableConflictError

        raise TimetableConflictError(conflicts[0]["message"], details={"conflicts": conflicts})
    db.commit()
    db.refresh(entry)
    log_from_request(db, request, current_user, "timetable.update", "timetable", resource_id=entry.id)
    return _entry_out(entry)


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_TIMETABLE)),
):
    entry = db.get(TimetableEntry, entry_id)
    if not entry:
        raise NotFoundError("Timetable entry not found.")
    log_from_request(db, request, current_user, "timetable.delete", "timetable", resource_id=entry.id)
    db.delete(entry)
    db.commit()
    return {"success": True, "message": "Timetable entry removed."}


@router.post("/check-conflict", response_model=list)
def check_conflict(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    """Preview conflicts for a prospective entry before saving."""
    return timetable_service.check_conflicts(
        db,
        day=payload["day"],
        period=int(payload["period"]),
        section=payload["section"],
        faculty_id=int(payload["faculty_id"]),
        classroom_id=payload.get("classroom_id"),
    )


@router.post("/generate", response_model=TimetableGenerateResult)
def generate(
    payload: TimetableGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_TIMETABLE)),
):
    result = timetable_service.generate_timetable(
        db,
        sections=payload.sections,
        periods_per_day=payload.periods_per_day,
        working_days=[str(d) for d in payload.working_days] or None,
        prefer_room_capacity=payload.prefer_room_capacity,
    )
    log_from_request(
        db, request, current_user, "timetable.generate", "timetable",
        details={"sections": payload.sections, "entries": result["entries_created"]},
    )
    return result
