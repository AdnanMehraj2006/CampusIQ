"""Classroom management (admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.classroom import Classroom
from app.models.user import User
from app.schemas import ClassroomCreate, ClassroomOut, ClassroomUpdate
from app.schemas.common import paginated
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/classrooms", tags=["Classrooms"])


@router.get("", response_model=dict)
def list_classrooms(
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Classroom)
    if page_params["q"]:
        q = q.filter(
            Classroom.room_number.ilike(f"%{page_params['q']}%")
            | Classroom.building.ilike(f"%{page_params['q']}%")
        )
    total = q.count()
    rows = q.order_by(Classroom.building, Classroom.room_number).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    items = [
        {
            "id": r.id,
            "room_number": r.room_number,
            "building": r.building,
            "capacity": r.capacity,
            "room_type": r.room_type,
        }
        for r in rows
    ]
    return paginated(items, page_params["page"], page_params["page_size"], total)


@router.post("", response_model=ClassroomOut, status_code=201)
def create_classroom(
    payload: ClassroomCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_CLASSROOMS)),
):
    if db.query(Classroom).filter(Classroom.room_number == payload.room_number).first():
        raise ConflictError("A classroom with this room number already exists.")
    room = Classroom(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    log_from_request(db, request, current_user, "classroom.create", "classroom", resource_id=room.id)
    return room


@router.put("/{classroom_id}", response_model=ClassroomOut)
def update_classroom(
    classroom_id: int,
    payload: ClassroomUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_CLASSROOMS)),
):
    room = db.get(Classroom, classroom_id)
    if not room:
        raise NotFoundError("Classroom not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    log_from_request(db, request, current_user, "classroom.update", "classroom", resource_id=room.id)
    return room


@router.delete("/{classroom_id}")
def delete_classroom(
    classroom_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_CLASSROOMS)),
):
    room = db.get(Classroom, classroom_id)
    if not room:
        raise NotFoundError("Classroom not found.")
    log_from_request(db, request, current_user, "classroom.delete", "classroom", resource_id=room.id)
    db.delete(room)
    db.commit()
    return {"success": True, "message": "Classroom deleted."}
