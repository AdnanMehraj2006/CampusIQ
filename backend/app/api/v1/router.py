"""Versioned API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    announcements,
    assignments,
    attendance,
    audit,
    auth,
    files,
    classrooms,
    courses,
    dashboard,
    departments,
    people,
    projects,
    reports,
    search,
    settings as settings_router,
    subjects,
    timetable,
)

api_router = APIRouter()

api_router.include_router(ai.router)
api_router.include_router(announcements.router)
api_router.include_router(assignments.router)
api_router.include_router(files.router)
api_router.include_router(attendance.router)
api_router.include_router(audit.router)
api_router.include_router(auth.router)
api_router.include_router(classrooms.router)
api_router.include_router(courses.router)
api_router.include_router(dashboard.router)
api_router.include_router(departments.router)
api_router.include_router(people.router)
api_router.include_router(projects.router)
api_router.include_router(reports.router)
api_router.include_router(search.router)
api_router.include_router(settings_router.router)
api_router.include_router(subjects.router)
api_router.include_router(timetable.router)
