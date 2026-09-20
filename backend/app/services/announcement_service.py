"""Announcement targeting: who may publish what, and who may read which item."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models.academic import Course, Department, Semester
from app.models.comms import Announcement, AnnouncementTarget, NotificationType, Priority
from app.models.people import Faculty, Student
from app.models.subject import SubjectAssignment
from app.models.user import User
from app.services.notification_service import notify_many


def validate_publish_scope(db: Session, user: User, announcement_in: dict) -> None:
    """Enforce that role X may only publish to audiences it owns."""
    target = AnnouncementTarget(announcement_in.get("target_type", AnnouncementTarget.EVERYONE))

    if user.role == "admin":
        return

    if user.role == "hod":
        dept_id = user.faculty_profile.department_id if user.faculty_profile else None
        if target == AnnouncementTarget.EVERYONE:
            raise ForbiddenError("HODs may only publish announcements to their own department.")
        if target == AnnouncementTarget.FACULTY:
            return  # scoped to their department below
        if announcement_in.get("department_id") not in (None, dept_id):
            raise ForbiddenError("You can only publish to your own department.")
        return

    if user.role == "faculty":
        if target not in (AnnouncementTarget.SECTION, AnnouncementTarget.SEMESTER, AnnouncementTarget.FACULTY):
            raise ForbiddenError(
                "Faculty may only publish announcements to their own sections, semesters or faculty."
            )
        if target == AnnouncementTarget.SECTION:
            section = announcement_in.get("section")
            if not section:
                raise ForbiddenError("A section is required for section-targeted announcements.")
            if not user.faculty_profile:
                raise ForbiddenError("No faculty profile is linked to your account.")
            assigned = (
                db.query(SubjectAssignment.section)
                .filter(SubjectAssignment.faculty_id == user.faculty_profile.id)
                .distinct()
                .all()
            )
            valid_sections = {a[0] for a in assigned}
            if section not in valid_sections:
                raise ForbiddenError("You can only publish to sections you teach.")
        return

    raise ForbiddenError("Your role cannot publish announcements.")


def announcement_recipients(db: Session, announcement: Announcement) -> list[int]:
    """Resolve the user ids that should see (and be notified about) an item."""
    target = AnnouncementTarget(announcement.target_type)

    student_q = db.query(Student).join(User, User.id == Student.user_id).filter(User.status == "active")
    if target == AnnouncementTarget.EVERYONE:
        users = db.query(User.id).filter(User.status == "active").all()
        return [u[0] for u in users]

    if target == AnnouncementTarget.FACULTY:
        q = db.query(User.id).join(Faculty, Faculty.user_id == User.id).filter(User.status == "active")
        if announcement.department_id:
            q = q.filter(Faculty.department_id == announcement.department_id)
        return [u[0] for u in q.all()]

    sq = student_q
    if announcement.department_id:
        sq = sq.filter(Student.department_id == announcement.department_id)
    if announcement.course_id:
        sq = sq.filter(Student.course_id == announcement.course_id)
    if announcement.semester_id:
        sq = sq.filter(Student.semester_id == announcement.semester_id)
    if announcement.section:
        sq = sq.filter(Student.section == announcement.section)
    return [s.user_id for s in sq.all()]


def visible_announcements_query(db: Session, user: User):
    """Base query of announcements visible to ``user`` (callers add paging/order).

    Announcements are published on creation (``published_at`` is non-nullable and
    defaults to now), so there is no draft flag to filter on here; visibility is
    decided purely by the targeting rules below.
    """
    q = db.query(Announcement)

    student = user.student_profile
    faculty = user.faculty_profile

    if user.role == "admin":
        return q

    if student is not None:
        clauses = [Announcement.target_type == AnnouncementTarget.EVERYONE]
        if student.department_id:
            clauses.append(
                and_(
                    Announcement.target_type == AnnouncementTarget.DEPARTMENT,
                    Announcement.department_id == student.department_id,
                )
            )
        if student.course_id:
            clauses.append(
                and_(
                    Announcement.target_type == AnnouncementTarget.COURSE,
                    Announcement.course_id == student.course_id,
                )
            )
        if student.semester_id:
            clauses.append(
                and_(
                    Announcement.target_type == AnnouncementTarget.SEMESTER,
                    Announcement.semester_id == student.semester_id,
                )
            )
        clauses.append(
            and_(
                Announcement.target_type == AnnouncementTarget.SECTION,
                Announcement.section == student.section,
                or_(Announcement.department_id.is_(None), Announcement.department_id == student.department_id),
            )
        )
        return q.filter(or_(*clauses))

    if faculty is not None:
        clauses = [
            Announcement.target_type == AnnouncementTarget.EVERYONE,
            and_(
                Announcement.target_type == AnnouncementTarget.DEPARTMENT,
                Announcement.department_id == faculty.department_id,
            ),
            and_(Announcement.target_type == AnnouncementTarget.FACULTY,
                 or_(Announcement.department_id.is_(None), Announcement.department_id == faculty.department_id)),
        ]
        sections = (
            db.query(SubjectAssignment.section)
            .filter(SubjectAssignment.faculty_id == faculty.id)
            .distinct()
            .all()
        )
        section_list = [s[0] for s in sections]
        if section_list:
            clauses.append(
                and_(
                    Announcement.target_type == AnnouncementTarget.SECTION,
                    Announcement.section.in_(section_list),
                    or_(Announcement.department_id.is_(None), Announcement.department_id == faculty.department_id),
                )
            )
        return q.filter(or_(*clauses))

    return q.filter(Announcement.target_type == AnnouncementTarget.EVERYONE)


def publish(db: Session, *, announcement_in: dict, author: User, commit: bool = True) -> Announcement:
    validate_publish_scope(db, author, announcement_in)
    ann = Announcement(
        title=announcement_in["title"],
        content=announcement_in["content"],
        summary=announcement_in.get("summary"),
        target_type=AnnouncementTarget(announcement_in.get("target_type", AnnouncementTarget.EVERYONE)),
        department_id=announcement_in.get("department_id"),
        course_id=announcement_in.get("course_id"),
        semester_id=announcement_in.get("semester_id"),
        section=announcement_in.get("section"),
        priority=Priority(announcement_in.get("priority", Priority.NORMAL)),
        published_by=author.id,
        expiry_at=announcement_in.get("expiry_at"),
        is_pinned=announcement_in.get("is_pinned", False),
    )
    db.add(ann)
    if commit:
        db.commit()
    else:
        db.flush()

    try:
        notify_many(
            db,
            recipient_ids=announcement_recipients(db, ann),
            type_=NotificationType.ANNOUNCEMENT,
            title=f"New announcement: {ann.title}",
            message=(ann.summary or ann.content)[:240],
            resource_type="announcement",
            resource_id=ann.id,
            commit=False,
        )
        if commit:
            db.commit()
    except Exception:
        pass
    return ann
