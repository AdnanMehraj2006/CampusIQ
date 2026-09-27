"""Classroom management."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.classroom import Classroom
from app.models.user import User
from app.schemas import ClassroomCreate, ClassroomOut, ClassroomUpdate
from app.schemas.common import paginated

router = APIRouter(tags=["Academic"])


@router.get("/classrooms", response_model=dict)
def list_classrooms(
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_FACULTY)),
):
    total = db.query(Classroom).count()
    rows = (
        db.query(Classroom)
        .offset(page_params["offset"])
        .limit(page_params["page_size"])
        .all()
    )
    return paginated(
        [{"id": r.id, "room_number": r.room_number, "building": r.building, "capacity": r.capacity, "type": r.room_type} for r in rows],
        page_params["page"],
        page_params["page_size"],
        total,
    )


@router.post("/classrooms", response_model=ClassroomOut, status_code=201)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    existing = db.query(Classroom).filter(Classroom.room_number == payload.room_number).first()
    if existing:
        raise NotFoundError("Classroom already exists.")
    room = Classroom(
        room_number=payload.room_number,
        building=payload.building,
        capacity=payload.capacity,
        room_type=payload.room_type,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return {"id": room.id, "room_number": room.room_number, "building": room.building, "capacity": room.capacity, "type": room.room_type}


@router.put("/classrooms/{room_id}", response_model=ClassroomOut)
def update_classroom(
    room_id: int,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    room = db.get(Classroom, room_id)
    if not room:
        raise NotFoundError("Classroom not found.")
    if payload.room_number is not None:
        room.room_number = payload.room_number
    if payload.building is not None:
        room.building = payload.building
    if payload.capacity is not None:
        room.capacity = payload.capacity
    if payload.room_type is not None:
        room.room_type = payload.room_type
    db.commit()
    db.refresh(room)
    return {"id": room.id, "room_number": room.room_number, "building": room.building, "capacity": room.capacity, "type": room.room_type}


@router.delete("/classrooms/{room_id}")
def delete_classroom(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    room = db.get(Classroom, room_id)
    if not room:
        raise NotFoundError("Classroom not found.")
    db.delete(room)
    db.commit()
    return {"success": True, "message": "Classroom deleted."}
