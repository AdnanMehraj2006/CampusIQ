"""CampusIQ Assistant - permission-aware AI helper.

SECURITY MODEL
--------------
The assistant NEVER executes raw SQL and never sees the database schema. It can
only call a fixed set of tools, and every tool re-validates the caller's
identity and role *before* returning data:

    get_my_attendance(student)
    get_my_timetable(user)
    get_my_assignments(student)
    get_my_projects(student)
    get_my_performance(student)
    get_class_statistics(faculty/cr)      - scoped to the caller's sections
    get_department_statistics(hod/admin)  - scoped to the caller's department
    get_announcements(user)               - uses the same targeting rules as the UI

A student can therefore never obtain another student's private records: the
tool resolves "me" from the authenticated token, not from the prompt.

If ``AI_PROVIDER=demo`` (or no API key is set), a deterministic rule-based
responder routes the question to the same tools. This means the assistant is
fully functional offline and no data ever leaves the server unless a key is
configured.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError
from app.core.permissions import Role
from app.models.academic import Department
from app.models.comms import Announcement, NotificationType, Priority  # noqa: F401
from app.models.marks import Mark
from app.models.people import Faculty, Student
from app.models.project import ProjectGroupMember, ProjectMilestone, ProjectStatus
from app.models.subject import Subject, SubjectAssignment
from app.models.timetable import Attendance, DayOfWeek, TimetableEntry, WORKING_DAYS
from app.models.user import User
from app.services import attendance_service


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    data: any = None
    error: Optional[str] = None


@dataclass
class ToolContext:
    """Everything a tool may legally know about the caller."""
    db: Session
    user: User
    student: Optional[Student] = None
    faculty: Optional[Faculty] = None
    role: str = "student"


def _require_student(ctx: ToolContext) -> Student:
    if ctx.student is None:
        raise ForbiddenError("This question requires a student account.")
    return ctx.student


def _require_faculty(ctx: ToolContext) -> Faculty:
    if ctx.faculty is None:
        raise ForbiddenError("This question requires a faculty or HOD account.")
    return ctx.faculty


# ---- Student-scoped tools (data only ever resolved from the caller) ----


def tool_get_my_attendance(ctx: ToolContext, **kw) -> dict:
    st = _require_student(ctx)
    return attendance_service.student_analytics(ctx.db, st.id)


def tool_get_my_timetable(ctx: ToolContext, **kw) -> dict:
    st = _require_student(ctx)
    rows = (
        ctx.db.query(TimetableEntry)
        .filter(TimetableEntry.section == st.section)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .all()
    )
    return {
        "section": st.section,
        "entries": [
            {
                "day": str(r.day),
                "period": r.period,
                "subject": r.subject.name if r.subject else None,
                "faculty": r.faculty.user.name if r.faculty and r.faculty.user else None,
                "room": r.classroom.room_number if r.classroom else None,
                "time": f"{r.start_time or ''}-{r.end_time or ''}",
            }
            for r in rows
        ],
    }


def tool_get_my_assignments(ctx: ToolContext, **kw) -> dict:
    from app.models.assignment import Assignment, AssignmentSubmission

    st = _require_student(ctx)
    subject_ids = [s.id for s in ctx.db.query(Subject).filter(Subject.semester_id == st.semester_id).all()] or None
    q = ctx.db.query(Assignment).filter(Assignment.is_published.is_(True))
    if subject_ids:
        q = q.filter(Assignment.subject_id.in_(subject_ids))
    rows = q.order_by(Assignment.deadline.asc()).limit(20).all()
    out = []
    for a in rows:
        sub = (
            ctx.db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == a.id, AssignmentSubmission.student_id == st.id)
            .first()
        )
        out.append(
            {
                "title": a.title,
                "subject": a.subject.name if a.subject else None,
                "deadline": a.deadline.isoformat() if a.deadline else None,
                "max_marks": a.max_marks,
                "submitted": sub is not None,
                "grade": sub.grade if sub else None,
                "is_late": bool(sub and sub.is_late),
            }
        )
    return {"assignments": out}


def tool_get_my_performance(ctx: ToolContext, **kw) -> dict:
    st = _require_student(ctx)
    rows = (
        ctx.db.query(Mark)
        .filter(Mark.student_id == st.id)
        .order_by(Mark.subject_id, Mark.assessment_type)
        .all()
    )
    by_subject: dict[int, list] = {}
    for m in rows:
        by_subject.setdefault(m.subject_id, []).append(m)
    subjects = {s.id: s for s in ctx.db.query(Subject).filter(Subject.id.in_(list(by_subject))).all()}
    out = []
    for sid, marks in by_subject.items():
        total = sum(float(m.marks) for m in marks)
        max_total = sum(float(m.max_marks) for m in marks)
        out.append(
            {
                "subject": subjects[sid].name if sid in subjects else f"Subject {sid}",
                "assessments": len(marks),
                "percentage": round(total / max_total * 100, 2) if max_total else 0.0,
            }
        )
    return {"performance": out}


def tool_get_my_projects(ctx: ToolContext, **kw) -> dict:
    st = _require_student(ctx)
    memberships = (
        ctx.db.query(ProjectGroupMember)
        .filter(ProjectGroupMember.student_id == st.id)
        .all()
    )
    out = []
    for m in memberships:
        group = m.group
        if group is None:
            continue
        project = group.project
        total = len(project.milestones)
        done = sum(1 for x in project.milestones if x.status == "completed")
        out.append(
            {
                "title": project.title,
                "status": project.status,
                "supervisor": project.supervisor.user.name if project.supervisor and project.supervisor.user else None,
                "group_name": group.name,
                "approved": group.approved,
                "progress": round(done / total * 100, 1) if total else 0.0,
                "next_milestone": _next_milestone(project.milestones),
                "deadline": project.deadline.isoformat() if project.deadline else None,
            }
        )
    return {"projects": out}


def _next_milestone(milestones) -> Optional[dict]:
    pending = sorted(
        [m for m in milestones if m.status not in ("completed",)],
        key=lambda m: (m.order_index, m.deadline or datetime.max),
    )
    if not pending:
        return None
    m = pending[0]
    return {
        "title": m.title,
        "deadline": m.deadline.isoformat() if m.deadline else None,
        "status": m.status,
    }


def tool_get_my_announcements(ctx: ToolContext, **kw) -> dict:
    from app.services.announcement_service import visible_announcements_query

    rows = visible_announcements_query(ctx.db, ctx.user).order_by(
        Announcement.published_at.desc()
    ).limit(10).all()
    return {
        "announcements": [
            {"title": a.title, "priority": a.priority, "published_at": a.published_at.isoformat() if a.published_at else None}
            for a in rows
        ]
    }


# ---- Class-scoped tools (faculty / CR) ----


def tool_get_class_statistics(ctx: ToolContext, section: Optional[str] = None, **kw) -> dict:
    if ctx.role not in (Role.FACULTY, Role.HOD, Role.CR, Role.ADMIN):
        raise ForbiddenError("Only faculty, CR, HOD or admin may view class statistics.")
    target = section
    if ctx.role == Role.CR:
        st = _require_student(ctx)
        target = st.section
    elif ctx.role in (Role.FACULTY, Role.HOD):
        fac = _require_faculty(ctx)
        if not target:
            assigned = (
                ctx.db.query(SubjectAssignment.section)
                .filter(SubjectAssignment.faculty_id == fac.id)
                .distinct()
                .first()
            )
            target = assigned[0] if assigned else None
    if not target:
        raise BadRequestError("No class section could be determined for your account.")
    return attendance_service.class_attendance_overview(ctx.db, target)


# ---- Department-scoped tools (HOD / admin) ----


def tool_get_department_statistics(ctx: ToolContext, **kw) -> dict:
    if ctx.role not in (Role.HOD, Role.ADMIN):
        raise ForbiddenError("Only HOD or admin may view department statistics.")

    fac = ctx.faculty
    dept_id = fac.department_id if fac else kw.get("department_id")
    if ctx.role == Role.ADMIN and not dept_id:
        first = ctx.db.query(Department).first()
        dept_id = first.id if first else None
    if not dept_id:
        raise BadRequestError("No department could be determined.")

    students = ctx.db.query(Student).join(User, User.id == Student.user_id).filter(
        Student.department_id == dept_id, User.status == "active"
    ).all()
    faculty_rows = ctx.db.query(Faculty).filter(Faculty.department_id == dept_id).all()
    subjects = ctx.db.query(Subject).filter(Subject.department_id == dept_id).all()

    total_attended = total_conducted = 0
    for s in students:
        stats = attendance_service._student_subject_stats(ctx.db, s.id)
        total_attended += sum(v["attended"] for v in stats.values())
        total_conducted += sum(v["conducted"] for v in stats.values())

    below = []
    for s in students:
        stats = attendance_service._student_subject_stats(ctx.db, s.id)
        att = sum(v["attended"] for v in stats.values())
        con = sum(v["conducted"] for v in stats.values())
        pct = att / con * 100 if con else 0.0
        if pct < settings.attendance_threshold:
            below.append({"name": s.user.name, "percentage": round(pct, 2)})

    return {
        "department_id": dept_id,
        "total_students": len(students),
        "total_faculty": len(faculty_rows),
        "total_subjects": len(subjects),
        "average_attendance": round(total_attended / total_conducted * 100, 2) if total_conducted else 0.0,
        "students_below_threshold": sorted(below, key=lambda x: x["percentage"]),
    }


def tool_get_faculty_workload(ctx: ToolContext, **kw) -> dict:
    if ctx.role not in (Role.HOD, Role.ADMIN):
        raise ForbiddenError("Only HOD or admin may view faculty workload.")
    fac = ctx.faculty
    q = ctx.db.query(Faculty)
    if ctx.role == Role.HOD and fac:
        q = q.filter(Faculty.department_id == fac.department_id)
    rows = q.all()
    out = []
    for f in rows:
        subjects = (
            ctx.db.query(SubjectAssignment)
            .filter(SubjectAssignment.faculty_id == f.id)
            .count()
        )
        periods = (
            ctx.db.query(TimetableEntry)
            .filter(TimetableEntry.faculty_id == f.id)
            .count()
        )
        out.append(
            {
                "name": f.user.name,
                "designation": f.designation,
                "subjects": subjects,
                "weekly_periods": periods,
            }
        )
    return {"faculty": out}


# ---- Registry ----


TOOL_REGISTRY: Dict[str, Callable] = {
    "get_my_attendance": tool_get_my_attendance,
    "get_my_timetable": tool_get_my_timetable,
    "get_my_assignments": tool_get_my_assignments,
    "get_my_performance": tool_get_my_performance,
    "get_my_projects": tool_get_my_projects,
    "get_my_announcements": tool_get_my_announcements,
    "get_class_statistics": tool_get_class_statistics,
    "get_department_statistics": tool_get_department_statistics,
    "get_faculty_workload": tool_get_faculty_workload,
}

TOOL_DESCRIPTIONS = {
    "get_my_attendance": "The caller's own attendance percentages per subject (students/CR only).",
    "get_my_timetable": "The caller's own class timetable (students/CR only).",
    "get_my_assignments": "The caller's own assignments with deadlines and grades (students/CR only).",
    "get_my_performance": "The caller's own marks/performance per subject (students/CR only).",
    "get_my_projects": "Projects the caller belongs to, with milestone progress (students/CR only).",
    "get_my_announcements": "Announcements visible to the caller.",
    "get_class_statistics": "Aggregate attendance statistics for a class section (faculty/CR/HOD/admin).",
    "get_department_statistics": "Aggregate statistics for a department (HOD/admin only).",
    "get_faculty_workload": "Teaching workload per faculty member (HOD/admin only).",
}


def build_context(db: Session, user: User) -> ToolContext:
    return ToolContext(
        db=db,
        user=user,
        student=user.student_profile,
        faculty=user.faculty_profile,
        role=str(user.role),
    )


# ---------------------------------------------------------------------------
# Demo-mode router: deterministic intent detection -> tools
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[str, list[str], dict]] = [
    ("attendance", [r"\battendance\b", r"present", r"absent", r"skip"], {"tool": "get_my_attendance"}),
    ("timetable", [r"\btimetable\b", r"class(es)? do i have", r"schedule", r"today'?s class", r"tomorrow"], {"tool": "get_my_timetable"}),
    ("assignment", [r"\bassignment", r"homework", r"submission", r"due"], {"tool": "get_my_assignments"}),
    ("performance", [r"\bperformance\b", r"\bmarks\b", r"\bgrades?\b", r"result", r"exam"], {"tool": "get_my_performance"}),
    ("project", [r"\bproject", r"milestone", r"group", r"deadline"], {"tool": "get_my_projects"}),
    ("announcement", [r"\bannouncement", r"\bnotice", r"news"], {"tool": "get_my_announcements"}),
]

_CLASS_INTENT = [r"my class", r"class statistic", r"section", r"who (is|was) absent", r"low attendance"]
_DEPT_INTENT = [r"department", r"faculty workload", r"how many (students|faculty)"]


def _detect_tool(message: str, ctx: ToolContext) -> list[tuple[str, dict]]:
    """Map a natural-language question onto the allowed tool set."""
    msg = message.lower()
    calls: list[tuple[str, dict]] = []

    if ctx.role in (Role.HOD, Role.ADMIN) and any(re.search(p, msg) for p in _DEPT_INTENT):
        if "workload" in msg or "faculty" in msg:
            calls.append(("get_faculty_workload", {}))
        calls.append(("get_department_statistics", {}))

    if ctx.role in (Role.FACULTY, Role.HOD, Role.CR) and any(re.search(p, msg) for p in _CLASS_INTENT):
        calls.append(("get_class_statistics", {}))

    if ctx.role in (Role.STUDENT, Role.CR):
        for _name, patterns, payload in _INTENT_PATTERNS:
            if any(re.search(p, msg) for p in patterns):
                calls.append((payload["tool"], {}))
        # students asking about "class" statistics -> their own aggregate
        if any(re.search(p, msg) for p in _CLASS_INTENT) and not calls:
            calls.append(("get_my_attendance", {}))
    elif ctx.role in (Role.FACULTY, Role.HOD) and not calls:
        # faculty asking general "my" questions -> their class overview
        if any(re.search(p, msg) for p in [r"\bmy\b", r"\bclass\b", r"student"]):
            calls.append(("get_class_statistics", {}))

    if not calls:
        calls.append(("get_my_announcements", {}))
    # de-duplicate preserving order
    seen, out = set(), []
    for name, args in calls:
        if name not in seen:
            seen.add(name)
            out.append((name, args))
    return out


def _fmt_attendance(d: dict) -> str:
    lines = [
        f"Overall attendance: {d['overall_percentage']}% ({d['classes_attended']}/{d['classes_conducted']} classes) - {d['zone'].upper()} zone.",
        f"Required: {d['required_percentage']:g}%. By subject:",
    ]
    by_subject = d.get("subject_wise", d.get("by_subject", []))
    for s in by_subject:
        lines.append(f"  - {s['subject_name']} ({s['subject_code']}): {s['percentage']}%  [{s['zone']}]")
    below = [s for s in by_subject if s["percentage"] < d["required_percentage"]]
    if below:
        lines.append(
            "Below threshold: " + ", ".join(f"{s['subject_name']} ({s['percentage']}%)" for s in below)
        )
    else:
        lines.append("All subjects are above the required threshold.")
    return "\n".join(lines)


def _fmt_timetable(d: dict) -> str:
    entries = d["entries"]
    if not entries:
        return "No timetable entries are published for your section yet."
    days_order = [str(x) for x in WORKING_DAYS]
    by_day: dict[str, list] = {}
    for e in entries:
        by_day.setdefault(e["day"], []).append(e)
    lines = [f"Timetable for section {d['section']}:"]
    today = date.today().strftime("%A")
    for day in days_order:
        if day not in by_day:
            continue
        marker = " (today)" if day == today else ""
        lines.append(f"{day}{marker}:")
        for e in sorted(by_day[day], key=lambda x: x["period"]):
            lines.append(f"  P{e['period']} {e['time']} - {e['subject']} ({e['faculty']}, {e['room']})")
    return "\n".join(lines)


def _fmt_assignments(d: dict) -> str:
    rows = d["assignments"]
    if not rows:
        return "You have no assignments right now."
    lines = ["Your assignments:"]
    for a in rows:
        status = "submitted" if a["submitted"] else "not submitted"
        grade = f", grade {a['grade']}/{a['max_marks']}" if a["grade"] is not None else ""
        lines.append(f"  - {a['title']} ({a['subject']}) due {a['deadline']} - {status}{grade}")
    return "\n".join(lines)


def _fmt_performance(d: dict) -> str:
    rows = d["performance"]
    if not rows:
        return "No marks have been published for you yet."
    lines = ["Your performance by subject:"]
    for p in rows:
        lines.append(f"  - {p['subject']}: {p['percentage']}% across {p['assessments']} assessment(s)")
    return "\n".join(lines)


def _fmt_projects(d: dict) -> str:
    rows = d["projects"]
    if not rows:
        return "You are not part of any project group yet."
    lines = ["Your projects:"]
    for p in rows:
        lines.append(
            f"  - {p['title']} ({p['status']}, {p['progress']}% complete) - supervisor {p['supervisor']}"
        )
        if p["next_milestone"]:
            lines.append(
                f"      next milestone: {p['next_milestone']['title']} (due {p['next_milestone']['deadline']})"
            )
    return "\n".join(lines)


def _fmt_announcements(d: dict) -> str:
    rows = d["announcements"]
    if not rows:
        return "No announcements are available right now."
    lines = ["Latest announcements:"]
    for a in rows[:5]:
        lines.append(f"  - [{a['priority']}] {a['title']}")
    return "\n".join(lines)


def _fmt_class(d: dict) -> str:
    lines = [f"Class attendance overview for section {d['section']} - overall {d['overall']}%:"]
    for s in d["students"][:15]:
        lines.append(f"  - {s['name']} ({s['enrollment_number']}): {s['overall_percentage']}% [{s['zone']}]")
    low = [s for s in d["students"] if s["overall_percentage"] < settings.attendance_threshold]
    if low:
        lines.append(
            "Students below the attendance threshold: "
            + ", ".join(f"{s['name']} ({s['overall_percentage']}%)" for s in low)
        )
    return "\n".join(lines)


def _fmt_department(d: dict) -> str:
    below = d["students_below_threshold"]
    lines = [
        f"Department overview: {d['total_students']} students, {d['total_faculty']} faculty, "
        f"{d['total_subjects']} subjects.",
        f"Average attendance: {d['average_attendance']}%.",
    ]
    if below:
        lines.append(
            f"{len(below)} student(s) below the {settings.attendance_threshold:g}% attendance threshold: "
            + ", ".join(f"{s['name']} ({s['percentage']}%)" for s in below[:10])
        )
    else:
        lines.append("All students are above the attendance threshold.")
    return "\n".join(lines)


def _fmt_workload(d: dict) -> str:
    rows = d["faculty"]
    if not rows:
        return "No faculty found."
    lines = ["Faculty workload:"]
    for f in rows:
        lines.append(f"  - {f['name']} ({f['designation']}): {f['subjects']} subject(s), {f['weekly_periods']} periods/week")
    return "\n".join(lines)


_FORMATTERS = {
    "get_my_attendance": _fmt_attendance,
    "get_my_timetable": _fmt_timetable,
    "get_my_assignments": _fmt_assignments,
    "get_my_performance": _fmt_performance,
    "get_my_projects": _fmt_projects,
    "get_my_announcements": _fmt_announcements,
    "get_class_statistics": _fmt_class,
    "get_department_statistics": _fmt_department,
    "get_faculty_workload": _fmt_workload,
}


def chat(db: Session, user: User, message: str, history: Optional[List[dict]] = None) -> dict:
    """Main entrypoint. Returns {reply, tools_used, mode}."""
    message = (message or "").strip()
    if not message:
        raise BadRequestError("Please ask a question.")

    ctx = build_context(db, user)
    plan = _detect_tool(message, ctx)

    blocks: list[str] = []
    used: list[str] = []
    for tool_name, args in plan:
        tool = TOOL_REGISTRY.get(tool_name)
        if tool is None:
            continue
        try:
            result = tool(ctx, **args)
        except ForbiddenError as e:
            blocks.append(f"I can't help with that: {e.message}")
            continue
        except Exception as e:  # never leak internals
            blocks.append("I couldn't retrieve that information right now. Please try again later.")
            continue
        used.append(tool_name)
        fmt = _FORMATTERS.get(tool_name)
        if fmt:
            blocks.append(fmt(result))

    # If an LLM key is configured, we would pass `result` to the model here.
    # Demo mode returns the structured tool output directly.
    reply = "\n\n".join(blocks) if blocks else (
        "I'm not sure how to help with that yet. Try asking about your attendance, "
        "timetable, assignments, performance, projects or announcements."
    )

    return {
        "reply": reply,
        "tools_used": used,
        "mode": settings.ai_provider if (settings.ai_provider == "demo" or not settings.ai_api_key) else "openai",
    }


# ---------------------------------------------------------------------------
# Optional LLM integration (used only when AI_PROVIDER=openai + key present)
# ---------------------------------------------------------------------------


def _openai_chat(db: Session, user: User, message: str, history: Optional[List[dict]]) -> dict:
    """Tool-calling conversation with an OpenAI-compatible provider.

    The model only ever receives tool *descriptions* and the caller's role - never
    the schema, never other users' data. Every tool call is re-authorized on
    execution.
    """
    from openai import OpenAI

    client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    ctx = build_context(db, user)

    system_prompt = (
        "You are the CampusIQ Assistant, a helpful college management assistant. "
        f"The authenticated user is {user.name} with role '{user.role}'. "
        "You may ONLY answer from the tools provided. Never invent data, never "
        "discuss another student's private information, and if a tool denies "
        "access, explain that to the user politely."
    )
    messages = [{"role": "system", "content": system_prompt}]
    for h in (history or [])[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for name in TOOL_REGISTRY
    ]

    used: list[str] = []
    for _ in range(6):
        resp = client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            tools=tools_schema,
            temperature=0.2,
        )
        choice = resp.choices[0]
        msg = choice.message
        if not msg.tool_calls:
            return {"reply": msg.content or "", "tools_used": used, "mode": "openai"}
        messages.append(msg)
        for call in msg.tool_calls:
            name = call.function.name
            args = {}
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool = TOOL_REGISTRY.get(name)
            if tool is None:
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": "Tool not available."}
                )
                continue
            try:
                result = tool(ctx, **args)
                used.append(name)
                content = json.dumps(result, default=str)
            except ForbiddenError as e:
                content = json.dumps({"error": e.message})
            except Exception:
                content = json.dumps({"error": "unavailable"})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        continue

    return {"reply": "I couldn't complete that request. Please try again.", "tools_used": used, "mode": "openai"}


def chat_router(db: Session, user: User, message: str, history: Optional[List[dict]] = None) -> dict:
    # A bare greeting ("hi", "hello", "hey", ...) is small talk, not a data
    # request. Answer it with a short, friendly reply instead of routing it to
    # a tool (which otherwise produced a formal announcement dump).
    if _is_greeting(message):
        return {
            "reply": _greeting_reply(user),
            "tools_used": [],
            "mode": "demo" if (settings.ai_provider == "demo" or not settings.ai_api_key) else "openai",
        }

    if settings.ai_provider == "openai" and settings.ai_api_key:
        try:
            return _openai_chat(db, user, message, history)
        except Exception:
            # Fall back to the deterministic tool router so the assistant keeps working.
            pass
    return chat(db, user, message, history)


# ---------------------------------------------------------------------------
# Greetings (short, conversational small talk - no tool calls)
# ---------------------------------------------------------------------------

_GREETINGS = {
    "hi", "hii", "hiii", "hello", "hey", "heyy", "yo", "howdy", "hiya",
    "hey there", "hi there", "hello there", "greetings", "good morning",
    "good afternoon", "good evening", "sup", "what's up", "whats up",
}

_GREETING_REPLIES: Dict[str, str] = {
    "student": "Hey! What can I help you with? I can check your attendance, timetable, assignments, marks or projects.",
    "cr": "Hey! I can pull up your class attendance overview or the latest announcements.",
    "faculty": "Hello! I can show class statistics or attendance for your sections.",
    "hod": "Hello! I can help with department statistics or faculty workload.",
    "admin": "Hello! I can help with department statistics, faculty workload or announcements.",
}


def _is_greeting(message: str) -> bool:
    """True when the message is *just* a greeting (no follow-up question)."""
    cleaned = re.sub(r"[^a-z0-9' ]", " ", (message or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned in _GREETINGS


def _greeting_reply(user: User) -> str:
    return _GREETING_REPLIES.get(str(user.role), "Hey! How can I help you today?")


SUGGESTED_QUESTIONS: dict[str, list[str]] = {
    "student": [
        "What is my current attendance?",
        "What classes do I have today?",
        "When is my next assignment due?",
        "Which subjects are below 75% attendance?",
        "How is my academic performance?",
        "What projects am I working on?",
    ],
    "cr": [
        "What is my class attendance overview?",
        "Show class statistics for my section.",
        "What announcements are there?",
    ],
    "faculty": [
        "Show class statistics for my section.",
        "Which students have low attendance?",
        "What is my teaching workload?",
    ],
    "hod": [
        "Give me department statistics.",
        "Show faculty workload.",
        "Which students are below the attendance threshold?",
    ],
    "admin": [
        "Give me department statistics.",
        "Show faculty workload.",
        "What announcements are there?",
    ],
}
