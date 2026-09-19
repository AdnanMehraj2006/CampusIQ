"""Classrooms / lecture halls."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.timetable import TimetableEntry


class Classroom(Base, TimestampMixin):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    building: Mapped[str] = mapped_column(String(100), default="Main Block", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    room_type: Mapped[str] = mapped_column(String(50), default="Lecture Hall", nullable=False)

    timetable_entries: Mapped[List["TimetableEntry"]] = relationship(back_populates="classroom")
