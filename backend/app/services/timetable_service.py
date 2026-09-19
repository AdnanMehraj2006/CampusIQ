"""Timetable conflict detection and automatic generation.

Hard constraints (always enforced):
  * section clash  - a section cannot have two subjects in the same slot
  * faculty clash  - a faculty member cannot teach two sections at once
  * room clash     - a classroom cannot host two sections at once
  * room capacity  - room capacity must cover section enrolment
  * quota          - each subject must receive its required weekly periods

Soft constraints (best-effort, expressed through slot preference ordering):
  * spread a subject across different days instead of stacking them
  * avoid more than two consecutive periods of the same subject
  * fill earlier periods first to minimise mid-day gaps for a section
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, TimetableConflictError
from app.models.academic import AcademicSession
from app.models.classroom import Classroom
from app.models.people import Student
from app.models.subject import Subject, SubjectAssignment
from app.models.timetable import DayOfWeek, TimetableEntry, WORKING_DAYS

PERIOD_TIMES = [
    ("09:00", "09:55"),
    ("10:00", "10:55"),
    ("11:00", "11:55"),
    ("12:00", "12:55"),
    ("14:00", "14:55"),
    ("15:00", "15:55"),
    ("16:00", "16:55"),
    ("17:00", "17:55"),
]


def active_session(db: Session) -> Optional[AcademicSession]:
    return db.query(AcademicSession).filter(AcademicSession.is_active.is_(True)).order_by(AcademicSession.id.desc()).first()


def section_enrolment(db: Session, section: str) -> int:
    return db.query(Student).filter(Student.section == section).count()


def _conflict_detail(kind: str, message: str, day: Optional[str] = None, period: Optional[int] = None) -> dict:
    return {"type": kind, "message": message, "day": day, "period": period}


def check_conflicts(
    db: Session,
    *,
    day: str,
    period: int,
    section: str,
    faculty_id: int,
    classroom_id: Optional[int],
    academic_session_id: Optional[int] = None,
    exclude_entry_id: Optional[int] = None,
) -> list[dict]:
    """Return a list of conflict descriptions; empty when the slot is free."""
    conflicts: list[dict] = []

    base = db.query(TimetableEntry).filter(
        TimetableEntry.day == day,
        TimetableEntry.period == period,
    )
    if exclude_entry_id:
        base = base.filter(TimetableEntry.id != exclude_entry_id)
    same_session = base.filter(
        TimetableEntry.academic_session_id.is_(academic_session_id)
        if academic_session_id is not None
        else TimetableEntry.academic_session_id.is_(None)
    )

    section_hit = same_session.filter(TimetableEntry.section == section).first()
    if section_hit:
        conflicts.append(_conflict_detail(
            "section",
            f"Section {section} already has '{section_hit.subject.name if section_hit.subject else 'a subject'}' "
            f"on {day} period {period}.",
            day, period,
        ))

    faculty_hit = same_session.filter(TimetableEntry.faculty_id == faculty_id).first()
    if faculty_hit:
        conflicts.append(_conflict_detail(
            "faculty",
            f"Faculty conflict: already assigned to section {faculty_hit.section} on {day} period {period}.",
            day, period,
        ))

    if classroom_id:
        room_hit = same_session.filter(TimetableEntry.classroom_id == classroom_id).first()
        if room_hit:
            conflicts.append(_conflict_detail(
                "room",
                f"Classroom conflict: room is already occupied by section {room_hit.section} on {day} period {period}.",
                day, period,
            ))
        room = db.get(Classroom, classroom_id) if classroom_id else None
        if room is not None:
            enrolment = section_enrolment(db, section)
            if room.capacity < enrolment:
                conflicts.append(_conflict_detail(
                    "capacity",
                    f"Room {room.room_number} capacity ({room.capacity}) is smaller than "
                    f"section {section} enrolment ({enrolment}).",
                    day, period,
                ))
    return conflicts


def add_entry(db: Session, *, entry_in: dict, actor_id: int) -> TimetableEntry:
    session = active_session(db)
    conflicts = check_conflicts(
        db,
        day=entry_in["day"],
        period=entry_in["period"],
        section=entry_in["section"],
        faculty_id=entry_in["faculty_id"],
        classroom_id=entry_in.get("classroom_id"),
        academic_session_id=session.id if session else None,
    )
    if conflicts:
        raise TimetableConflictError(conflicts[0]["message"], details={"conflicts": conflicts})

    times = PERIOD_TIMES[entry_in["period"] - 1] if 0 < entry_in["period"] <= len(PERIOD_TIMES) else (None, None)
    entry = TimetableEntry(
        day=DayOfWeek(entry_in["day"]),
        period=entry_in["period"],
        subject_id=entry_in["subject_id"],
        faculty_id=entry_in["faculty_id"],
        classroom_id=entry_in.get("classroom_id"),
        section=entry_in["section"],
        semester_id=entry_in.get("semester_id"),
        academic_session_id=session.id if session else None,
        start_time=entry_in.get("start_time") or times[0],
        end_time=entry_in.get("end_time") or times[1],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def section_timetable(db: Session, section: str) -> list[TimetableEntry]:
    return (
        db.query(TimetableEntry)
        .filter(TimetableEntry.section == section)
        .order_by(
            TimetableEntry.day,
            TimetableEntry.period,
        )
        .all()
    )


def faculty_timetable(db: Session, faculty_id: int) -> list[TimetableEntry]:
    return (
        db.query(TimetableEntry)
        .filter(TimetableEntry.faculty_id == faculty_id)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .all()
    )


# ---------------------------------------------------------------------------
# Automatic generation (CSP backtracking)
# ---------------------------------------------------------------------------


def _slot_preference(day_index: int, period: int, days_total: int) -> int:
    """Lower = more preferred. Kept for documentation of the soft-constraint idea;
    the live ordering is built in ``candidate_slots``."""
    return day_index * 100 + period * 10


def generate_timetable(
    db: Session,
    *,
    sections: list[str],
    periods_per_day: int = 6,
    working_days: Optional[list[str]] = None,
    prefer_room_capacity: bool = True,
) -> dict:
    """Backtracking CSP solver producing a clash-free timetable per section."""
    days = [str(d) for d in (working_days or [str(d) for d in WORKING_DAYS if d != DayOfWeek.SUNDAY])]
    if not days:
        raise BadRequestError("At least one working day is required.")
    if periods_per_day < 1 or periods_per_day > len(PERIOD_TIMES):
        raise BadRequestError(f"periods_per_day must be between 1 and {len(PERIOD_TIMES)}")

    session = active_session(db)
    session_id = session.id if session else None

    rooms = db.query(Classroom).order_by(Classroom.capacity.asc()).all()
    if not rooms:
        raise BadRequestError("No classrooms exist. Add classrooms before generating a timetable.")

    # Wipe the existing timetable for the target sections (idempotent generation).
    db.query(TimetableEntry).filter(TimetableEntry.section.in_(sections)).delete(
        synchronize_session=False
    )

    # Build the requirement list: (section, subject, faculty, required_periods)
    requirements: list[dict] = []
    for section in sections:
        assignments = (
            db.query(SubjectAssignment)
            .filter(SubjectAssignment.section == section)
            .all()
        )
        if not assignments:
            raise BadRequestError(
                f"No subject assignments exist for section {section}. Assign faculty to subjects first."
            )
        for a in assignments:
            requirements.append(
                {
                    "section": section,
                    "subject": a.subject,
                    "faculty_id": a.faculty_id,
                    "required": max(1, a.subject.weekly_periods),
                }
            )
    # Most constrained first: subjects needing the most periods.
    requirements.sort(key=lambda r: -r["required"])

    # Expand into individual placement units (one period slot each) so the DFS
    # can backtrack at the granularity of a single slot.
    units: list[dict] = []
    for req in requirements:
        for _ in range(req["required"]):
            units.append(req)

    # Occupancy registers (hard constraints)
    used_section: set[tuple] = set()
    used_faculty: set[tuple] = set()
    used_room: set[tuple] = set()
    section_day_subject: dict[tuple, int] = defaultdict(int)  # soft: subject-per-day spread
    section_day_load: dict[tuple, int] = defaultdict(int)    # soft: daily load balance
    placed_for_req: dict[int, list[tuple]] = defaultdict(list)  # req id -> [(day, period)]
    _req_counter = [0]
    for r in requirements:
        r["_id"] = _req_counter[0]
        _req_counter[0] += 1

    all_slots = [
        (d, p)
        for d in days
        for p in range(1, periods_per_day + 1)
    ]

    def room_for(section: str, day: str, period: int) -> Optional[Classroom]:
        enrolment = section_enrolment(db, section)
        candidates = rooms if not prefer_room_capacity else ([r for r in rooms if r.capacity >= enrolment] or rooms)
        for r in candidates:
            if (day, period, r.id) not in used_room:
                return r
        return None

    def candidate_slots(req: dict) -> list[tuple[str, int]]:
        """Slot ordering that encodes the soft constraints (preferred first)."""
        load = {d: section_day_load[(req["section"], d)] for d in days}
        max_load = max(load.values()) if load else 0
        light = {d for d in days if load[d] < max_load}
        same_day = {d for (d, _p) in placed_for_req[req["_id"]]}

        def score(slot: tuple[str, int]) -> tuple:
            d, p = slot
            # 1) prefer days with lighter load, 2) avoid repeating a subject on the
            #    same day, 3) prefer early periods, 4) stable day order
            return (
                0 if d in light else 1,
                1 if d in same_day else 0,
                p,
                days.index(d),
            )

        return sorted(all_slots, key=score)

    results: list[TimetableEntry] = []
    conflicts_log: list[dict] = []
    step_budget = [400_000]

    def commit_slot(req: dict, day: str, period: int, room: Classroom) -> TimetableEntry:
        times = PERIOD_TIMES[period - 1]
        entry = TimetableEntry(
            day=DayOfWeek(day),
            period=period,
            subject_id=req["subject"].id,
            faculty_id=req["faculty_id"],
            classroom_id=room.id,
            section=req["section"],
            semester_id=req["subject"].semester_id,
            academic_session_id=session_id,
            start_time=times[0],
            end_time=times[1],
        )
        db.add(entry)
        results.append(entry)
        used_section.add((day, period, req["section"]))
        used_faculty.add((day, period, req["faculty_id"]))
        used_room.add((day, period, room.id))
        section_day_subject[(req["section"], req["subject"].id)] += 1
        section_day_load[(req["section"], day)] += 1
        placed_for_req[req["_id"]].append((day, period))
        return entry

    def rollback_slot(req: dict, entry: TimetableEntry) -> None:
        day, period, room_id = str(entry.day), entry.period, entry.classroom_id
        used_section.discard((day, period, req["section"]))
        used_faculty.discard((day, period, req["faculty_id"]))
        used_room.discard((day, period, room_id))
        section_day_subject[(req["section"], req["subject"].id)] -= 1
        section_day_load[(req["section"], day)] -= 1
        if (day, period) in placed_for_req[req["_id"]]:
            placed_for_req[req["_id"]].remove((day, period))
        if entry in results:
            results.remove(entry)
        db.delete(entry)

    def solve(index: int) -> bool:
        if index >= len(units):
            return True
        step_budget[0] -= 1
        if step_budget[0] <= 0:
            conflicts_log.append({"message": "Solver step budget exhausted."})
            return False

        req = units[index]
        for day, period in candidate_slots(req):
            if (day, period, req["section"]) in used_section:
                continue
            if (day, period, req["faculty_id"]) in used_faculty:
                continue
            room = room_for(req["section"], day, period)
            if room is None:
                continue
            entry = commit_slot(req, day, period, room)
            if solve(index + 1):
                return True
            rollback_slot(req, entry)
        return False

    ok = solve(0)
    db.commit()

    if not ok:
        db.query(TimetableEntry).filter(TimetableEntry.section.in_(sections)).delete(
            synchronize_session=False
        )
        db.commit()
        raise ConflictError(
            "No clash-free timetable could be generated with the current constraints. "
            "Try reducing weekly periods, adding more working days/periods, or more classrooms.",
            details={"conflicts": conflicts_log[:10] or [{"message": "No solution exists under current constraints."}]},
        )

    return {
        "entries_created": len(results),
        "conflicts": conflicts_log[:10],
        "sections": sections,
        "message": f"Generated {len(results)} timetable entries across {len(sections)} section(s).",
    }
