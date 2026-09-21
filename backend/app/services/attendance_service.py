"""Attendance business logic: marking, scoping, analytics and prediction.

Percentages use this convention:
    classes_conducted = records with status in (present, late, absent)
    classes_attended = records with status in (present, late)
    excused           = excluded from both (student was legitimately excused)

Attendance % = classes_attended / classes_conducted * 100
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    AttendanceConflictError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
)
from app.models.people import Student
from app.models.subject import Subject
from app.models.timetable import (
    Attendance,
    AttendanceStatus,
    TimetableEntry,
)
from app.models.user import User

PRESENT_LIKE = (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
COUNTED = (AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.ABSENT)


# ---------------------------------------------------------------------------
# Scoping helpers
# ---------------------------------------------------------------------------


def students_in_section(
    db: Session,
    section: str,
    subject_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester_id: Optional[int] = None,
) -> list[Student]:
    """Students in a section, optionally restricted to the subject's semester.

    ``department_id``/``semester_id`` narrow the class context (used to keep a
    CR's view within their own Department + Semester + Section).
    """
    q = db.query(Student).join(User, User.id == Student.user_id).filter(
        Student.section == section,
        User.status == "active",
    )
    if department_id is not None:
        q = q.filter(Student.department_id == department_id)
    if semester_id is not None:
        q = q.filter(Student.semester_id == semester_id)
    if subject_id is not None:
        subject = db.get(Subject, subject_id)
        if subject is None:
            raise NotFoundError("Subject not found.")
        if subject.semester_id is not None:
            q = q.filter(Student.semester_id == subject.semester_id)
    return q.order_by(User.name).all()


def faculty_subjects(db: Session, faculty_id: int) -> list[Subject]:
    from app.models.subject import SubjectAssignment

    return (
        db.query(Subject)
        .join(SubjectAssignment, SubjectAssignment.subject_id == Subject.id)
        .filter(SubjectAssignment.faculty_id == faculty_id)
        .distinct()
        .all()
    )


def assert_faculty_owns_subject(db: Session, faculty_id: int, subject_id: int, section: Optional[str] = None) -> None:
    """Faculty may only mark attendance for subjects/sections assigned to them."""
    from app.models.subject import SubjectAssignment

    q = db.query(SubjectAssignment).filter(
        SubjectAssignment.faculty_id == faculty_id,
        SubjectAssignment.subject_id == subject_id,
    )
    if section:
        q = q.filter(SubjectAssignment.section == section)
    if not q.first():
        raise ForbiddenError(
            "You can only manage attendance for subjects and sections assigned to you."
        )


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------


def zone_for(percentage: float) -> str:
    if percentage >= settings.attendance_threshold:
        return "safe"
    if percentage >= settings.attendance_warning_min:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# Marking
# ---------------------------------------------------------------------------


def mark_attendance(
    db: Session,
    *,
    subject_id: int,
    section: str,
    on_date: date,
    marks: dict[int, str],
    marked_by: User,
) -> list[Attendance]:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Subject not found.")

    if marked_by.role not in ("admin",):
        assert_faculty_owns_subject(db, marked_by.faculty_profile.id if marked_by.faculty_profile else 0, subject_id, section)

    roster = students_in_section(db, section, subject_id)
    if not roster:
        raise BadRequestError(f"No active students found in section {section} for this subject.")

    roster_ids = {s.id for s in roster}
    unknown = set(marks.keys()) - roster_ids
    if unknown:
        raise BadRequestError("Some marked students do not belong to this section.")

    existing = (
        db.query(Attendance)
        .filter(
            Attendance.subject_id == subject_id,
            Attendance.date == on_date,
            Attendance.student_id.in_(roster_ids),
        )
        .all()
    )
    if existing:
        raise AttendanceConflictError(
            "Attendance has already been marked for this subject on this date. "
            "Use the edit endpoint to update it."
        )

    records: list[Attendance] = []
    for student in roster:
        status = marks.get(student.id, AttendanceStatus.PRESENT)
        records.append(
            Attendance(
                student_id=student.id,
                subject_id=subject_id,
                date=on_date,
                status=AttendanceStatus(status),
                marked_by=marked_by.id,
            )
        )
    db.add_all(records)
    db.commit()

    # Notify students in the critical/warning bands after this marking.
    try:
        from app.services.notification_service import notify_students
        from app.models.comms import NotificationType

        summary = subject_summary_for_students(db, [s.id for s in roster], subject_id)
        warn_ids = [
            sid for sid, summ in summary.items()
            if summ["percentage"] < settings.attendance_threshold
        ]
        if warn_ids:
            notify_students(
                db,
                student_ids=warn_ids,
                type_=NotificationType.ATTENDANCE_WARNING,
                title="Attendance update",
                message=(
                    f"Attendance for {subject.name} ({subject.code}) was marked. "
                    "Check your current attendance percentage."
                ),
                resource_type="subject",
                resource_id=subject.id,
                commit=False,
            )
            db.commit()
    except Exception:
        pass

    return records


def update_attendance(
    db: Session,
    record_id: int,
    *,
    status: str,
    note: Optional[str],
    actor: User,
) -> Attendance:
    record = db.get(Attendance, record_id)
    if record is None:
        raise NotFoundError("Attendance record not found.")

    # Faculty scope: must be the subject's assigned faculty.
    if actor.role != "admin":
        from app.models.subject import SubjectAssignment

        assigned = (
            db.query(SubjectAssignment)
            .filter(
                SubjectAssignment.subject_id == record.subject_id,
                SubjectAssignment.faculty_id == actor.faculty_profile.id if actor.faculty_profile else 0,
            )
            .first()
        )
        if not assigned:
            raise ForbiddenError("You can only edit attendance for your own subjects.")

        age = datetime.now(record.created_at.tzinfo) - record.created_at if record.created_at else timedelta(0)
        if age > timedelta(hours=settings.attendance_edit_window_hours):
            raise ForbiddenError(
                f"Attendance can only be edited within {settings.attendance_edit_window_hours} hours of marking."
            )

    record.status = AttendanceStatus(status)
    if note is not None:
        record.note = note
    db.commit()
    return record


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def _student_subject_stats(db: Session, student_id: int) -> dict[int, dict]:
    """{subject_id: {conducted, attended, percentage}}"""
    rows = (
        db.query(
            Attendance.subject_id,
            Attendance.status,
            func.count(Attendance.id),
        )
        .filter(Attendance.student_id == student_id)
        .group_by(Attendance.subject_id, Attendance.status)
        .all()
    )
    agg: dict[int, dict] = defaultdict(lambda: {"conducted": 0, "attended": 0})
    for subject_id, status, cnt in rows:
        if status in COUNTED:
            agg[subject_id]["conducted"] += cnt
        if status in PRESENT_LIKE:
            agg[subject_id]["attended"] += cnt
    out = {}
    for subject_id, v in agg.items():
        pct = round((v["attended"] / v["conducted"] * 100.0), 2) if v["conducted"] else 0.0
        out[subject_id] = {
            "conducted": v["conducted"],
            "attended": v["attended"],
            "percentage": pct,
            "zone": zone_for(pct),
        }
    return out


def subject_summary_for_students(db: Session, student_ids: Iterable[int], subject_id: int) -> dict[int, dict]:
    rows = (
        db.query(
            Attendance.student_id,
            Attendance.status,
            func.count(Attendance.id),
        )
        .filter(
            Attendance.student_id.in_(list(student_ids)),
            Attendance.subject_id == subject_id,
        )
        .group_by(Attendance.student_id, Attendance.status)
        .all()
    )
    agg: dict[int, dict] = defaultdict(lambda: {"conducted": 0, "attended": 0})
    for sid, status, cnt in rows:
        if status in COUNTED:
            agg[sid]["conducted"] += cnt
        if status in PRESENT_LIKE:
            agg[sid]["attended"] += cnt
    out = {}
    for sid, v in agg.items():
        pct = round(v["attended"] / v["conducted"] * 100.0, 2) if v["conducted"] else 0.0
        out[sid] = {"conducted": v["conducted"], "attended": v["attended"], "percentage": pct}
    for sid in student_ids:
        out.setdefault(sid, {"conducted": 0, "attended": 0, "percentage": 0.0})
    return out


def student_analytics(db: Session, student_id: int) -> dict:
    stats = _student_subject_stats(db, student_id)
    subject_ids = list(stats.keys())
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    subject_map = {s.id: s for s in subjects}

    conducted = sum(v["conducted"] for v in stats.values())
    attended = sum(v["attended"] for v in stats.values())
    overall = round(attended / conducted * 100.0, 2) if conducted else 0.0

    by_subject = [
        {
            "subject_id": sid,
            "subject_name": subject_map[sid].name if sid in subject_map else f"Subject {sid}",
            "subject_code": subject_map[sid].code if sid in subject_map else "—",
            "classes_attended": v["attended"],
            "classes_conducted": v["conducted"],
            "percentage": v["percentage"],
            "zone": v["zone"],
        }
        for sid, v in sorted(stats.items())
    ]

    return {
        "total_classes": conducted,
        "attended": attended,
        "absent": conducted - attended,
        "late": 0,
        "excused": 0,
        "overall_percentage": overall,
        "classes_attended": attended,
        "classes_conducted": conducted,
        "classes_missed": conducted - attended,
        "required_percentage": settings.attendance_threshold,
        "zone": zone_for(overall),
        "subject_wise": by_subject,
        "trend": monthly_trend(db, student_id),
    }


def monthly_trend(db: Session, student_id: int, subject_id: Optional[int] = None, months: int = 8) -> list[dict]:
    """Per-month attendance percentage for charts."""
    q = db.query(Attendance).filter(Attendance.student_id == student_id)
    if subject_id:
        q = q.filter(Attendance.subject_id == subject_id)
    rows = q.all()

    buckets: dict[str, dict] = defaultdict(lambda: {"conducted": 0, "attended": 0})
    for r in rows:
        key = r.date.strftime("%Y-%m")
        if r.status in COUNTED:
            buckets[key]["conducted"] += 1
        if r.status in PRESENT_LIKE:
            buckets[key]["attended"] += 1

    out = []
    today = date.today()
    for i in range(months - 1, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 30)
        # align to month start
        key = d.strftime("%Y-%m")
        b = buckets.get(key, {"conducted": 0, "attended": 0})
        pct = round(b["attended"] / b["conducted"] * 100.0, 2) if b["conducted"] else None
        out.append({"date": key, "percentage": pct, "conducted": b["conducted"], "attended": b["attended"]})
    return out


# ---------------------------------------------------------------------------
# Prediction calculator
# ---------------------------------------------------------------------------


def predict_attendance(
    db: Session,
    student_id: int,
    required_percentage: Optional[float] = None,
) -> dict:
    """Minimum future classes to attend / maximum classes missable."""
    required = required_percentage or settings.attendance_threshold
    if not (0 < required < 100):
        raise BadRequestError("Required percentage must be between 1 and 99.")

    stats = _student_subject_stats(db, student_id)
    attended = sum(v["attended"] for v in stats.values())
    conducted = sum(v["conducted"] for v in stats.values())

    current = round(attended / conducted * 100.0, 2) if conducted else 0.0
    r = required / 100.0

    # n: future classes the student must attend (assuming all future classes held)
    #   (attended + n) / (conducted + n) >= r
    if current >= required:
        needed = 0
        will_reach = True
    else:
        needed = (r * conducted - attended) / (1.0 - r)
        needed = max(1, int(needed) if needed == int(needed) else int(needed) + 1)
        will_reach = True  # always reachable while r < 100

    # m: classes the student can still miss (and stay >= r)
    #   attended / (conducted + m) >= r  ->  m <= attended/r - conducted
    if r > 0 and attended / r - conducted > 0:
        can_miss = max(0, int((attended / r) - conducted))
    else:
        can_miss = 0
    if current < required:
        can_miss = 0

    projected = round((attended + needed) / (conducted + needed) * 100.0, 2) if (conducted + needed) else 0.0

    if current >= required:
        msg = (
            f"Your attendance is {current}%, which is above the required {required:g}%. "
            f"You can miss up to {can_miss} more class(es) and still stay above the threshold."
        )
    else:
        msg = (
            f"Your attendance is {current}% ({attended}/{conducted} classes). "
            f"You need to attend the next {needed} consecutive class(es) to reach {required:g}%."
        )

    return {
        "current_percentage": current,
        "required_percentage": required,
        "classes_attended": attended,
        "classes_conducted": conducted,
        "classes_needed": needed,
        "will_reach": will_reach,
        "projected_percentage": projected,
        "classes_can_miss": can_miss,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# Class-level analytics (faculty / CR / HOD)
# ---------------------------------------------------------------------------


def class_attendance_overview(
    db: Session,
    section: str,
    subject_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester_id: Optional[int] = None,
) -> dict:
    """Aggregate attendance for a section, per subject.

    When ``department_id``/``semester_id`` are given the roster is restricted to
    that single class context (Department + Semester + Section).
    """
    roster = students_in_section(db, section, department_id=department_id, semester_id=semester_id)
    if not roster:
        return {"section": section, "subjects": [], "overall": 0.0, "students": []}

    subject_ids = [s.id for s in faculty_subjects_by_section(db, section)] if not subject_id else [subject_id]
    subjects_q = db.query(Subject).filter(Subject.id.in_(subject_ids)) if subject_ids else None
    if subjects_q is not None and department_id is not None:
        # Keep the CR's view inside their own department's subjects.
        subjects_q = subjects_q.filter(Subject.department_id == department_id)
    subjects = subjects_q.all() if subjects_q is not None else []

    rows = (
        db.query(
            Attendance.student_id,
            Attendance.subject_id,
            Attendance.status,
            func.count(Attendance.id),
        )
        .filter(
            Attendance.student_id.in_([s.id for s in roster]),
            Attendance.subject_id.in_(subject_ids) if subject_ids else Attendance.subject_id.is_(False),
        )
        .group_by(Attendance.student_id, Attendance.subject_id, Attendance.status)
        .all()
    )
    per_student_subject: dict[tuple, dict] = defaultdict(lambda: {"conducted": 0, "attended": 0})
    for sid, sub_id, status, cnt in rows:
        if status in COUNTED:
            per_student_subject[(sid, sub_id)]["conducted"] += cnt
        if status in PRESENT_LIKE:
            per_student_subject[(sid, sub_id)]["attended"] += cnt

    students_out = []
    total_attended = total_conducted = 0
    for st in roster:
        s_attended = s_conducted = 0
        subjects_detail = []
        for sub in subjects:
            v = per_student_subject.get((st.id, sub.id), {"conducted": 0, "attended": 0})
            pct = round(v["attended"] / v["conducted"] * 100, 2) if v["conducted"] else None
            subjects_detail.append({"subject_id": sub.id, "subject_name": sub.name, "percentage": pct})
            s_attended += v["attended"]
            s_conducted += v["conducted"]
        overall = round(s_attended / s_conducted * 100, 2) if s_conducted else 0.0
        total_attended += s_attended
        total_conducted += s_conducted
        students_out.append(
            {
                "student_id": st.id,
                "name": st.user.name,
                "enrollment_number": st.enrollment_number,
                "overall_percentage": overall,
                "zone": zone_for(overall),
                "subjects": subjects_detail,
            }
        )
    students_out.sort(key=lambda x: x["overall_percentage"])
    overall = round(total_attended / total_conducted * 100, 2) if total_conducted else 0.0

    subject_agg = []
    for sub in subjects:
        att = sum(per_student_subject.get((st.id, sub.id), {"attended": 0})["attended"] for st in roster)
        con = sum(per_student_subject.get((st.id, sub.id), {"conducted": 0})["conducted"] for st in roster)
        subject_agg.append(
            {
                "subject_id": sub.id,
                "subject_name": sub.name,
                "subject_code": sub.code,
                "percentage": round(att / con * 100, 2) if con else 0.0,
                "conducted": con,
            }
        )
    return {
        "section": section,
        "overall": overall,
        "subjects": subject_agg,
        "students": students_out,
    }


def faculty_subjects_by_section(db: Session, section: str) -> list[Subject]:
    from app.models.subject import SubjectAssignment

    return (
        db.query(Subject)
        .join(SubjectAssignment, SubjectAssignment.subject_id == Subject.id)
        .filter(SubjectAssignment.section == section)
        .distinct()
        .all()
    )
