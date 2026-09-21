"""Announcements with role-scoped targeting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import pagination_params, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.comms import Announcement
from app.models.user import User
from app.schemas import AnnouncementCreate, AnnouncementOut, AnnouncementUpdate
from app.schemas.common import paginated
from app.services import announcement_service, upload_service
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def _announcement_out(a: Announcement) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "content": a.content,
        "summary": a.summary,
        "target_type": a.target_type,
        "department_id": a.department_id,
        "course_id": a.course_id,
        "semester_id": a.semester_id,
        "section": a.section,
        "priority": a.priority,
        "published_by": a.published_by,
        "attachment_path": a.attachment_path,
        "attachment_name": a.attachment_name,
        "published_at": a.published_at,
        "expiry_at": a.expiry_at,
        "is_pinned": a.is_pinned,
        "author_name": a.author.name if a.author else None,
        "author_role": str(a.author.role) if a.author else None,
    }


@router.get("", response_model=dict)
def list_announcements(
    priority: str | None = None,
    pinned_only: bool = False,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = announcement_service.visible_announcements_query(db, current_user)
    if priority:
        q = q.filter(Announcement.priority == priority)
    if pinned_only:
        q = q.filter(Announcement.is_pinned.is_(True))
    if page_params["q"]:
        q = q.filter(Announcement.title.ilike(f"%{page_params['q']}%") | Announcement.content.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = (
        q.order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        .offset(page_params["offset"])
        .limit(page_params["page_size"])
        .all()
    )
    return paginated([_announcement_out(a) for a in rows], page_params["page"], page_params["page_size"], total)


@router.post("", response_model=AnnouncementOut, status_code=201)
def create_announcement(
    payload: AnnouncementCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PUBLISH_ANNOUNCEMENTS)),
):
    ann = announcement_service.publish(db, announcement_in=payload.model_dump(), author=current_user)
    log_from_request(db, request, current_user, "announcement.publish", "announcement", resource_id=ann.id,
                     details={"target": ann.target_type, "priority": ann.priority})
    return _announcement_out(ann)


@router.get("/{announcement_id}", response_model=AnnouncementOut)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise NotFoundError("Announcement not found.")
    visible = announcement_service.visible_announcements_query(db, current_user).filter(Announcement.id == announcement_id).first()
    if not visible and current_user.role != "admin":
        raise ForbiddenError("This announcement is not visible to you.")
    return _announcement_out(a)


@router.put("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PUBLISH_ANNOUNCEMENTS)),
):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise NotFoundError("Announcement not found.")
    if current_user.role != "admin" and a.published_by != current_user.id:
        raise ForbiddenError("You can only edit announcements you published.")
    data = payload.model_dump(exclude_unset=True)
    # Re-targeting is allowed, but must still respect the publisher's scope
    # (e.g. a HOD may not retarget an announcement to another department).
    if any(k in data for k in ("target_type", "department_id", "course_id", "semester_id", "section")):
        announcement_service.validate_publish_scope(db, current_user, {
            "target_type": data.get("target_type", a.target_type),
            "department_id": data.get("department_id", a.department_id),
            "course_id": data.get("course_id", a.course_id),
            "semester_id": data.get("semester_id", a.semester_id),
            "section": data.get("section", a.section),
        })
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    log_from_request(db, request, current_user, "announcement.update", "announcement", resource_id=a.id)
    return _announcement_out(a)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PUBLISH_ANNOUNCEMENTS)),
):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise NotFoundError("Announcement not found.")
    if current_user.role != "admin" and a.published_by != current_user.id:
        raise ForbiddenError("You can only delete announcements you published.")
    upload_service.delete_upload(a.attachment_path)
    log_from_request(db, request, current_user, "announcement.delete", "announcement", resource_id=a.id)
    db.delete(a)
    db.commit()
    return {"success": True, "message": "Announcement deleted."}


@router.post("/{announcement_id}/attachment", response_model=AnnouncementOut)
def upload_announcement_attachment(
    announcement_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PUBLISH_ANNOUNCEMENTS)),
):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise NotFoundError("Announcement not found.")
    if current_user.role != "admin" and a.published_by != current_user.id:
        raise ForbiddenError("You can only edit announcements you published.")
    path, original = upload_service.save_upload(file, subfolder="announcements")
    upload_service.delete_upload(a.attachment_path)
    a.attachment_path, a.attachment_name = path, original
    db.commit()
    db.refresh(a)
    return _announcement_out(a)


@router.get("/targets/allowed", response_model=dict)
def allowed_targets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    """Which audiences the current user may publish to (drives the UI)."""
    if current_user.role == "admin":
        targets = ["everyone", "department", "course", "semester", "section", "faculty"]
        from app.models.people import Student
        sections = [s[0] for s in db.query(Student.section).distinct().all()]
    elif current_user.role == "hod":
        targets = ["department", "course", "semester", "section", "faculty"]
        sections = []
    elif current_user.role == "faculty":
        targets = ["section", "semester", "faculty"]
        from app.models.subject import SubjectAssignment

        sections = [s[0] for s in db.query(SubjectAssignment.section)
                    .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id).distinct().all()]
    else:
        targets = []
        sections = []
    return {"targets": targets, "sections": sections}
