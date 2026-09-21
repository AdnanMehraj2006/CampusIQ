"""Assignments, submissions and marks entry."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.datetime import as_utc, utcnow

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_student, pagination_params, require_permission
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.marks import Mark
from app.models.people import Student
from app.models.user import User
from app.schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentUpdate,
    MarkCreate,
    MarkOut,
    MarkUpdate,
    SubmissionCreate,
    SubmissionGrade,
    SubmissionOut,
)
from app.schemas.common import paginated
from app.services import upload_service
from app.services.audit_service import log_from_request
from app.services.notification_service import notify, notify_students

router = APIRouter(tags=["Academic"])


def _assignment_out(db: Session, a: Assignment, viewer: User | None = None) -> dict:
    out = {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "instructions": a.instructions,
        "subject_id": a.subject_id,
        "faculty_id": a.faculty_id,
        "section": a.section,
        "semester_id": a.semester_id,
        "deadline": a.deadline,
        "max_marks": a.max_marks,
        "attachment_path": a.attachment_path,
        "attachment_name": a.attachment_name,
        "allow_late": a.allow_late,
        "is_published": a.is_published,
        "created_at": a.created_at,
        "subject_name": a.subject.name if a.subject else None,
        "subject_code": a.subject.code if a.subject else None,
        "faculty_name": a.faculty.user.name if a.faculty and a.faculty.user else None,
        "submission_count": db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == a.id).count(),
        "my_submission": None,
    }
    if viewer is not None and viewer.student_profile is not None:
        sub = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == a.id, AssignmentSubmission.student_id == viewer.student_profile.id)
            .first()
        )
        if sub:
            out["my_submission"] = {
                "id": sub.id,
                "submitted_at": sub.submitted_at,
                "is_late": sub.is_late,
                "grade": sub.grade,
                "feedback": sub.feedback,
                "file_name": sub.file_name,
            }
    return out


def _assert_faculty_owns(db: Session, current_user: User, assignment: Assignment) -> None:
    if current_user.role == Role.ADMIN:
        return
    if current_user.faculty_profile is None or assignment.faculty_id != current_user.faculty_profile.id:
        raise ForbiddenError("You can only manage assignments you created.")


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


@router.get("/assignments", response_model=dict)
def list_assignments(
    subject_id: int | None = None,
    section: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Assignment)
    if current_user.role in (Role.STUDENT, Role.CR) and current_user.student_profile:
        from app.models.subject import Subject

        subject_ids = [
            s.id for s in db.query(Subject).filter(Subject.semester_id == current_user.student_profile.semester_id).all()
        ]
        q = q.filter(Assignment.subject_id.in_(subject_ids) if subject_ids else False)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        q = q.filter(Assignment.faculty_id == current_user.faculty_profile.id)
    if subject_id:
        q = q.filter(Assignment.subject_id == subject_id)
    if section:
        q = q.filter((Assignment.section == section) | Assignment.section.is_(None))
    if page_params["q"]:
        q = q.filter(Assignment.title.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Assignment.deadline.asc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated(
        [_assignment_out(db, a, current_user) for a in rows],
        page_params["page"], page_params["page_size"], total,
    )


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ASSIGNMENTS)),
):
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    assignment = Assignment(
        **payload.model_dump(),
        faculty_id=current_user.faculty_profile.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    log_from_request(db, request, current_user, "assignment.create", "assignment", resource_id=assignment.id)
    try:
        subject = assignment.subject
        roster = db.query(Student).join(User, User.id == Student.user_id).filter(
            Student.semester_id == assignment.subject.semester_id if subject and subject.semester_id else None,
            User.status == "active",
        )
        if assignment.section:
            roster = roster.filter(Student.section == assignment.section)
        notify_students(
            db,
            student_ids=[s.id for s in roster.all()],
            type_="assignment",
            title=f"New assignment: {assignment.title}",
            message=f"{subject.name if subject else ''} - due {assignment.deadline}",
            resource_type="assignment",
            resource_id=assignment.id,
        )
    except Exception:
        pass
    return _assignment_out(db, assignment, current_user)


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    return _assignment_out(db, a, current_user)


@router.put("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ASSIGNMENTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    _assert_faculty_owns(db, current_user, a)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    log_from_request(db, request, current_user, "assignment.update", "assignment", resource_id=a.id)
    return _assignment_out(db, a, current_user)


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ASSIGNMENTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    _assert_faculty_owns(db, current_user, a)
    upload_service.delete_upload(a.attachment_path)
    log_from_request(db, request, current_user, "assignment.delete", "assignment", resource_id=a.id)
    db.delete(a)
    db.commit()
    return {"success": True, "message": "Assignment deleted."}


@router.post("/assignments/{assignment_id}/attachment", response_model=AssignmentOut)
def upload_assignment_attachment(
    assignment_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_ASSIGNMENTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    _assert_faculty_owns(db, current_user, a)
    path, original = upload_service.save_upload(file, subfolder="assignments")
    a.attachment_path, a.attachment_name = path, original
    db.commit()
    db.refresh(a)
    return _assignment_out(db, a, current_user)


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


@router.get("/assignments/{assignment_id}/submissions", response_model=dict)
def list_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.GRADE_ASSIGNMENTS)),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")
    _assert_faculty_owns(db, current_user, a)
    q = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment_id)
    total = q.count()
    rows = q.order_by(AssignmentSubmission.submitted_at.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    items = [
        {
            "id": s.id,
            "assignment_id": s.assignment_id,
            "student_id": s.student_id,
            "file_name": s.file_name,
            "text_submission": s.text_submission,
            "submitted_at": s.submitted_at,
            "is_late": s.is_late,
            "grade": s.grade,
            "feedback": s.feedback,
            "graded_at": s.graded_at,
            "student_name": s.student.user.name if s.student and s.student.user else None,
            "enrollment_number": s.student.enrollment_number if s.student else None,
            "assignment_title": a.title,
            "max_marks": a.max_marks,
        }
        for s in rows
    ]
    return paginated(items, page_params["page"], page_params["page_size"], total)


@router.post("/assignments/{assignment_id}/submit", response_model=SubmissionOut, status_code=201)
async def submit_assignment(
    assignment_id: int,
    request: Request,
    text_submission: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found.")

    now = utcnow()
    is_late = bool(a.deadline and now > as_utc(a.deadline))
    if is_late and not a.allow_late:
        raise BadRequestError("The submission deadline has passed and late submissions are not allowed for this assignment.")

    existing = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == assignment_id, AssignmentSubmission.student_id == student.id)
        .first()
    )
    if existing:
        # Re-submitting replaces the previous upload.
        upload_service.delete_upload(existing.file_path)
        existing.text_submission = text_submission
        existing.submitted_at = now
        existing.is_late = is_late
        if file is not None:
            path, original = await upload_service.save_upload(file, subfolder="submissions")
            existing.file_path, existing.file_name = path, original
        db.commit()
        db.refresh(existing)
        submission = existing
    else:
        path = original = None
        if file is not None:
            path, original = await upload_service.save_upload(file, subfolder="submissions")
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=student.id,
            file_path=path,
            file_name=original,
            text_submission=text_submission,
            submitted_at=now,
            is_late=is_late,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    log_from_request(
        db, request, student.user, "assignment.submit", "assignment_submission",
        resource_id=submission.id, details={"assignment_id": assignment_id, "late": is_late},
    )
    notify(
        db,
        recipient_id=a.faculty.user_id,
        type_="assignment",
        title=f"Submission received: {a.title}",
        message=f"{student.user.name} submitted the assignment ({'late' if is_late else 'on time'}).",
        resource_type="assignment",
        resource_id=a.id,
    )
    return submission


@router.put("/submissions/{submission_id}/grade", response_model=SubmissionOut)
def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GRADE_ASSIGNMENTS)),
):
    s = db.get(AssignmentSubmission, submission_id)
    if not s:
        raise NotFoundError("Submission not found.")
    assignment = s.assignment
    _assert_faculty_owns(db, current_user, assignment)
    if payload.grade > assignment.max_marks:
        raise BadRequestError(f"Grade cannot exceed the maximum marks ({assignment.max_marks}).")
    s.grade = payload.grade
    s.feedback = payload.feedback
    s.graded_by = current_user.id
    s.graded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)
    log_from_request(db, request, current_user, "assignment.grade", "assignment_submission", resource_id=s.id)
    notify(
        db,
        recipient_id=s.student.user_id,
        type_="assignment_graded",
        title=f"Grade published: {assignment.title}",
        message=f"You scored {s.grade}/{assignment.max_marks}.",
        resource_type="assignment",
        resource_id=assignment.id,
    )
    return s


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------


def _mark_out(m: Mark) -> dict:
    return {
        "id": m.id,
        "student_id": m.student_id,
        "subject_id": m.subject_id,
        "assessment_type": m.assessment_type,
        "title": m.title,
        "marks": float(m.marks),
        "max_marks": float(m.max_marks),
        "remarks": m.remarks,
        "percentage": m.percentage,
        "subject_name": m.subject.name if m.subject else None,
        "student_name": m.student.user.name if m.student and m.student.user else None,
        "entered_at": m.created_at,
    }


@router.get("/marks", response_model=dict)
def list_marks(
    student_id: int | None = None,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_OWN_MARKS)),
):
    q = db.query(Mark)
    if current_user.role in (Role.STUDENT, Role.CR) and current_user.student_profile:
        if student_id and student_id != current_user.student_profile.id:
            raise ForbiddenError("You can only view your own marks.")
        q = q.filter(Mark.student_id == current_user.student_profile.id)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        from app.services.attendance_service import faculty_subjects

        ids = [s.id for s in faculty_subjects(db, current_user.faculty_profile.id)]
        q = q.filter(Mark.subject_id.in_(ids) if ids else False)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        from app.models.subject import Subject as SubjectModel

        ids = [s.id for s in db.query(SubjectModel).filter(SubjectModel.department_id == current_user.faculty_profile.department_id).all()]
        q = q.filter(Mark.subject_id.in_(ids) if ids else False)
    if student_id:
        q = q.filter(Mark.student_id == student_id)
    if subject_id:
        q = q.filter(Mark.subject_id == subject_id)
    total = q.count()
    rows = q.order_by(Mark.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_mark_out(m) for m in rows], page_params["page"], page_params["page_size"], total)


@router.post("/marks", response_model=MarkOut, status_code=201)
def create_mark(
    payload: MarkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ENTER_MARKS)),
):
    if payload.marks > payload.max_marks:
        raise BadRequestError("Marks cannot exceed the maximum marks.")
    student = db.get(Student, payload.student_id)
    if not student:
        raise NotFoundError("Student not found.")
    if current_user.role != Role.ADMIN:
        from app.models.subject import SubjectAssignment

        assigned = (
            db.query(SubjectAssignment)
            .filter(SubjectAssignment.subject_id == payload.subject_id, SubjectAssignment.faculty_id == current_user.faculty_profile.id)
            .first()
        )
        if not assigned:
            raise ForbiddenError("You can only enter marks for subjects assigned to you.")

    existing = db.query(Mark).filter(
        Mark.student_id == payload.student_id,
        Mark.subject_id == payload.subject_id,
        Mark.assessment_type == payload.assessment_type,
        Mark.title == payload.title,
    ).first()
    if existing:
        raise BadRequestError("A mark record already exists for this student/subject/assessment. Use PUT to update it.")

    mark = Mark(**payload.model_dump(), entered_by=current_user.id)
    db.add(mark)
    db.commit()
    db.refresh(mark)
    log_from_request(db, request, current_user, "marks.enter", "mark", resource_id=mark.id,
                     details={"student_id": mark.student_id, "subject_id": mark.subject_id, "value": float(mark.marks)})
    notify(
        db,
        recipient_id=student.user_id,
        type_="marks_published",
        title="Marks published",
        message=f"{mark.title} for {mark.subject.name if mark.subject else ''} has been published.",
        resource_type="subject",
        resource_id=mark.subject_id,
    )
    return _mark_out(mark)


@router.put("/marks/{mark_id}", response_model=MarkOut)
def update_mark(
    mark_id: int,
    payload: MarkUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ENTER_MARKS)),
):
    mark = db.get(Mark, mark_id)
    if not mark:
        raise NotFoundError("Mark record not found.")
    if current_user.role != Role.ADMIN:
        from app.models.subject import SubjectAssignment

        assigned = (
            db.query(SubjectAssignment)
            .filter(SubjectAssignment.subject_id == mark.subject_id, SubjectAssignment.faculty_id == current_user.faculty_profile.id)
            .first()
        )
        if not assigned:
            raise ForbiddenError("You can only update marks for subjects assigned to you.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("marks") is not None and data.get("max_marks") is not None and data["marks"] > data["max_marks"]:
        raise BadRequestError("Marks cannot exceed the maximum marks.")
    for k, v in data.items():
        setattr(mark, k, v)
    db.commit()
    db.refresh(mark)
    log_from_request(db, request, current_user, "marks.edit", "mark", resource_id=mark.id)
    return _mark_out(mark)


@router.get("/marks/me", response_model=dict)
def my_marks(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
    page_params: dict = Depends(pagination_params),
):
    q = db.query(Mark).filter(Mark.student_id == student.id)
    total = q.count()
    rows = q.order_by(Mark.subject_id, Mark.assessment_type).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_mark_out(m) for m in rows], page_params["page"], page_params["page_size"], total)
