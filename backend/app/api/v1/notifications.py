"""In-app notifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.comms import Notification, NotificationType
from app.models.user import User
from app.schemas import NotificationOut, NotificationSummary
from app.schemas.common import paginated

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=dict)
def list_notifications(
    unread_only: bool = False,
    type: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Notification).filter(Notification.recipient_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    if type:
        q = q.filter(Notification.type == type)
    total = q.count()
    rows = q.order_by(Notification.created_at.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated(
        [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "resource_type": n.resource_type,
                "resource_id": n.resource_id,
                "created_at": n.created_at,
            }
            for n in rows
        ],
        page_params["page"], page_params["page_size"], total,
    )


@router.get("/summary", response_model=NotificationSummary)
def notification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    base = db.query(Notification).filter(Notification.recipient_id == current_user.id)
    unread = base.filter(Notification.is_read.is_(False)).count()
    total = base.count()
    by_type: dict[str, int] = {}
    for n in base.all():
        by_type[n.type] = by_type.get(n.type, 0) + 1
    return {"unread_count": unread, "total": total, "by_type": by_type}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    n = db.get(Notification, notification_id)
    if not n:
        raise NotFoundError("Notification not found.")
    if n.recipient_id != current_user.id:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only manage your own notifications.")
    n.is_read = True
    db.commit()
    return {"success": True, "message": "Notification marked as read."}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    db.query(Notification).filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False)).update(
        {Notification.is_read: True}
    )
    db.commit()
    return {"success": True, "message": "All notifications marked as read."}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    n = db.get(Notification, notification_id)
    if not n:
        raise NotFoundError("Notification not found.")
    if n.recipient_id != current_user.id:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only delete your own notifications.")
    db.delete(n)
    db.commit()
    return {"success": True, "message": "Notification deleted."}
