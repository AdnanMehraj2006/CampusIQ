"""In-app notification creation helpers."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.comms import Notification, NotificationType
from app.models.user import User


def notify(
    db: Session,
    *,
    recipient_id: int,
    type_: NotificationType | str,
    title: str,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    commit: bool = True,
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        type=str(type_),
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(n)
    if commit:
        db.commit()
    else:
        db.flush()
    return n


def notify_many(
    db: Session,
    *,
    recipient_ids: Iterable[int],
    type_: NotificationType | str,
    title: str,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    commit: bool = True,
) -> int:
    created = 0
    for rid in dict.fromkeys(recipient_ids):  # de-dupe, preserve order
        notify(
            db,
            recipient_id=rid,
            type_=type_,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            commit=False,
        )
        created += 1
    if commit and created:
        db.commit()
    return created


def notify_students(
    db: Session,
    *,
    student_ids: Iterable[int],
    type_: NotificationType | str,
    title: str,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    commit: bool = True,
) -> int:
    """Resolve student ids -> user ids, then notify."""
    from app.models.people import Student

    ids = list(dict.fromkeys(student_ids))
    if not ids:
        return 0
    users = db.query(User.id).join(Student, Student.user_id == User.id).filter(Student.id.in_(ids)).all()
    return notify_many(
        db,
        recipient_ids=[u[0] for u in users],
        type_=type_,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
        commit=commit,
    )
