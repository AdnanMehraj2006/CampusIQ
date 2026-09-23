"""Student, faculty and user management with role-scoped access."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import (
    check_department_scope,
    get_current_student,
    pagination_params,
    require_permission,
)
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role, permissions_for_role
from app.database import get_db
from app.models.academic import Course, Department, Semester
from app.models.people import Faculty, Student
from app.models.user import User, UserStatus
from app.schemas import (
    FacultyCreate,
    FacultyOut,
    FacultyUpdate,
    StudentCreate,
    StudentOut,
    StudentUpdate,
    UserOutAdmin,
    UserUpdateAdmin,
)
from app.schemas.common import paginated
from app.services import auth_service
from app.services.audit_service import log_from_request
from app.services.attendance_service import student_analytics

router = APIRouter(tags=["People"])


def _student_out(db: Session, s: Student) -> dict:
    user = s.user
    dept = s.department.name if s.department else None
    course = s.course.name if s.course else None
    sem = s.semester.semester_number if s.semester else None
    analytics = student_analytics(db, s.id)
    return {
        "id": s.id,
        "user_id": s.user_id,
        "enrollment_number": s.enrollment_number,
        "department_id": s.department_id,
        "course_id": s.course_id,
        "semester_id": s.semester_id,
        "section": s.section,
        "admission_year": s.admission_year,
        "guardian_name": s.guardian_name,
        "guardian_phone": s.guardian_phone,
        "name": user.name if user else "",
        "email": user.email if user else "",
        "phone": user.phone if user else None,
        "role": str(user.role) if user else "student",
        "status": str(user.status) if user else "active",
        "college_id": user.college_id if user else None,
        "department_name": dept,
        "course_name": course,
        "semester_number": sem,
        "attendance_percentage": analytics["overall_percentage"],
    }


def _faculty_out(db: Session, f: Faculty) -> dict:
    user = f.user
    from app.models.subject import SubjectAssignment

    subject_count = db.query(SubjectAssignment).filter(SubjectAssignment.faculty_id == f.id).count()
    return {
        "id": f.id,
        "user_id": f.user_id,
        "department_id": f.department_id,
        "designation": f.designation,
        "specialization": f.specialization,
        "name": f.name,
        "email": f.email,
        "phone": user.phone if user else None,
        "role": str(user.role) if user else "faculty",
        "status": str(user.status) if user else "active",
        "college_id": user.college_id if user else None,
        "department_name": f.department.name if f.department else None,
        "subject_count": subject_count,
        "is_hod": bool(f.department and f.department.hod_id == f.id),
    }


# ---------------------------------------------------------------------------
# Shared business rules
# ---------------------------------------------------------------------------

#: At most two Class Representatives per Department + Semester + Section.
MAX_CRS_PER_CLASS = 2


def _validate_academic_context(db: Session, payload: object) -> None:
    """Authoritative backend validation of create/update academic fields.

    Frontend selects constrain choices for convenience, but this is the
    authority: an invalid section/course/semester is rejected here.
    """
    from app.models.academic import Section

    course_id = getattr(payload, "course_id", None)
    semester_id = getattr(payload, "semester_id", None)
    section_name = getattr(payload, "section", None)
    dept_id = getattr(payload, "department_id", None)

    # Validate course exists and belongs to selected department
    if course_id:
        course = db.get(Course, course_id)
        if not course:
            raise BadRequestError("Course does not exist.")
        if dept_id and course.department_id != dept_id:
            raise BadRequestError("Selected course does not belong to the chosen department.")

    # Validate semester exists and belongs to selected course
    if semester_id:
        semester = db.get(Semester, semester_id)
        if not semester:
            raise BadRequestError("Semester does not exist.")
        if course_id and semester.course_id is not None and semester.course_id != course_id:
            raise BadRequestError("Selected semester does not belong to the chosen course.")

    # Validate section exists - backward compatible:
    # - Contextual sections (course_id/semester_id) must match exactly
    # - Context-free sections (no course_id/semester_id) are available to all
    if section_name:
        active_sections = (
            db.query(Section)
            .filter(Section.is_active.is_(True))
            .all()
        )
        if not active_sections:
            # Bootstrap-friendly: allow any section name until sections exist
            return
        
        # Check if section name exists with matching context
        # A section without course_id/semester_id is context-free and available to all
        context_matched = any(
            s.name == section_name and
            (course_id is None or s.course_id is None or s.course_id == course_id) and
            (semester_id is None or s.semester_id is None or s.semester_id == semester_id)
            for s in active_sections
        )
        
        if not context_matched:
            raise BadRequestError(
                f"Section '{section_name}' does not exist. Create it under Sections first."
            )


def _cr_count_in_class(
    db: Session,
    department_id: int | None,
    semester_id: int | None,
    section: str,
    exclude_student_id: int | None = None,
) -> int:
    """Count existing CRs for the same Department + Semester + Section."""
    q = (
        db.query(Student.id)
        .join(User, User.id == Student.user_id)
        .filter(User.role == str(Role.CR))
        .filter(Student.department_id == department_id)
        .filter(Student.semester_id == semester_id)
        .filter(Student.section == section)
    )
    if exclude_student_id is not None:
        q = q.filter(Student.id != exclude_student_id)
    return q.count()


def _assert_can_assign_cr(db: Session, current_user: User, student: Student) -> None:
    """Authorize a CR appointment and enforce the server-side 2-CR limit.

    A CR assignment is bound to the student's Department + Semester + Section.
    Only admins (institution-wide) and HODs (own department only) may appoint.
    """
    if current_user.role == Role.HOD:
        check_department_scope(current_user, student.department_id)
    elif current_user.role != Role.ADMIN:
        raise ForbiddenError("Only administrators and heads of department can appoint CRs.")
    if student.user is None:
        raise BadRequestError("This student has no linked user account.")
    if student.user.role == Role.CR:
        return  # already a CR - idempotent re-assignment
    existing = _cr_count_in_class(db, student.department_id, student.semester_id, student.section)
    if existing >= MAX_CRS_PER_CLASS:
        raise ConflictError(
            f"This class already has the maximum of {MAX_CRS_PER_CLASS} CRs "
            "for the same Department + Semester + Section. "
            "Remove or reassign an existing CR first."
        )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------


@router.get("/students", response_model=dict)
def list_students(
    department_id: int | None = None,
    section: str | None = None,
    semester_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_STUDENTS)),
):
    q = db.query(Student).join(User, User.id == Student.user_id)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Student.department_id == current_user.faculty_profile.department_id)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        from app.models.subject import SubjectAssignment

        sections = (
            db.query(SubjectAssignment.section)
            .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id)
            .distinct()
            .all()
        )
        q = q.filter(Student.section.in_([s[0] for s in sections]))
    if current_user.role == Role.CR:
        q = q.filter(Student.section == current_user.student_profile.section) if current_user.student_profile else q.filter(False)
    if department_id:
        q = q.filter(Student.department_id == department_id)
    if section:
        q = q.filter(Student.section == section)
    if semester_id:
        q = q.filter(Student.semester_id == semester_id)
    if page_params["q"]:
        q = q.filter(
            User.name.ilike(f"%{page_params['q']}%")
            | User.email.ilike(f"%{page_params['q']}%")
            | Student.enrollment_number.ilike(f"%{page_params['q']}%")
        )
    total = q.count()
    rows = q.order_by(User.name).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_student_out(db, s) for s in rows], page_params["page"], page_params["page_size"], total)


@router.get("/students/me", response_model=StudentOut)
def get_my_student_record(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    """A student reading their own profile."""
    return _student_out(db, student)


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_STUDENTS)),
):
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    _assert_student_scope(db, current_user, s)
    return _student_out(db, s)


def _assert_student_scope(db: Session, current_user: User, student: Student) -> None:
    if current_user.role == Role.ADMIN:
        return
    if current_user.role == Role.STUDENT:
        if current_user.student_profile is None or current_user.student_profile.id != student.id:
            raise ForbiddenError("You can only access your own information.")
        return
    if current_user.role == Role.CR:
        me = current_user.student_profile
        if me is None:
            raise ForbiddenError("Your account has no student profile.")
        # A CR may only see students within their own class context.
        if (
            me.department_id != student.department_id
            or me.semester_id != student.semester_id
            or me.section != student.section
        ):
            raise ForbiddenError(
                "You can only view students in your own class "
                "(department, semester and section)."
            )
        return
    if current_user.role == Role.HOD:
        check_department_scope(current_user, student.department_id)
        return
    if current_user.role == Role.FACULTY:
        from app.models.subject import SubjectAssignment

        teaches = (
            db.query(SubjectAssignment.section)
            .filter(SubjectAssignment.faculty_id == current_user.faculty_profile.id)
            .filter(SubjectAssignment.section == student.section)
            .first()
        )
        if not teaches:
            raise ForbiddenError("You can only view students in sections you teach.")
        return
    raise ForbiddenError("Access denied.")


@router.post("/students", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    if current_user.role == Role.HOD:
        check_department_scope(current_user, payload.department_id)

    dept = db.get(Department, payload.department_id)
    if not dept:
        raise BadRequestError("Department does not exist.")

    _validate_academic_context(db, payload)

    if db.query(Student).filter(Student.enrollment_number == payload.enrollment_number).first():
        raise ConflictError("A student with this enrollment number already exists.")

    # CR is a Student account with extra functionality; the role is granted
    # below only if the class quota allows it.
    user, plaintext = auth_service.create_user_account(
        db,
        name=payload.name,
        email=payload.email,
        college_id=payload.college_id,
        role=Role.STUDENT,
        password=payload.password,
        phone=payload.phone,
    )
    student = Student(
        user_id=user.id,
        enrollment_number=payload.enrollment_number,
        department_id=payload.department_id,
        course_id=payload.course_id,
        semester_id=payload.semester_id,
        section=payload.section,
        admission_year=payload.admission_year,
        guardian_name=payload.guardian_name,
        guardian_phone=payload.guardian_phone,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    if payload.is_cr:
        _assert_can_assign_cr(db, current_user, student)
        user.role = Role.CR
        db.commit()
        db.refresh(student)
    log_from_request(db, request, current_user, "student.create", "student", resource_id=student.id)
    result = _student_out(db, student)
    # Surface an auto-generated password exactly once so the admin can share it
    # securely. Only the hash is stored; this is the only time it is exposed.
    if not payload.password:
        result["initial_password"] = plaintext
    return result


@router.put("/students/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, s.department_id)

    _validate_academic_context(db, payload)

    data = payload.model_dump(exclude_unset=True)
    is_cr = data.pop("is_cr", None)
    for k, v in data.items():
        if k in ("name", "email", "phone"):
            setattr(s.user, k, v)
        else:
            setattr(s, k, v)
    if is_cr is not None:
        if is_cr:
            # Enforce the same quota/scoping rules as the dedicated CR endpoint.
            _assert_can_assign_cr(db, current_user, s)
            s.user.role = Role.CR
        else:
            s.user.role = Role.STUDENT
    db.commit()
    db.refresh(s)
    log_from_request(db, request, current_user, "student.update", "student", resource_id=s.id)
    return _student_out(db, s)


@router.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, s.department_id)
    log_from_request(db, request, current_user, "student.delete", "student", resource_id=s.id)
    user = s.user
    db.delete(s)
    if user:
        db.delete(user)
    db.commit()
    return {"success": True, "message": "Student removed."}


# ---------------------------------------------------------------------------
# Class Representative (CR) assignment
# ---------------------------------------------------------------------------
# A CR is a normal Student account whose ``User.role == 'cr'``. The assignment
# is bound to the student's Department + Semester + Section and at most
# ``MAX_CRS_PER_CLASS`` CRs are allowed per class. GR is *not* a separate role:
# it is informal shorthand for a female CR and is not modelled anywhere.


@router.post("/students/{student_id}/cr", response_model=StudentOut)
def assign_cr(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    """Appoint a student as CR for their Department + Semester + Section."""
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    _assert_can_assign_cr(db, current_user, s)
    if s.user is not None and s.user.role != Role.CR:
        s.user.role = Role.CR
        db.commit()
        db.refresh(s)
    log_from_request(db, request, current_user, "cr.assign", "student", resource_id=s.id)
    return _student_out(db, s)


@router.delete("/students/{student_id}/cr", response_model=StudentOut)
def remove_cr(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    """Remove CR status; the account keeps working as a normal Student."""
    s = db.get(Student, student_id)
    if not s:
        raise NotFoundError("Student not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, s.department_id)
    elif current_user.role != Role.ADMIN:
        raise ForbiddenError("Only administrators and heads of department can remove CRs.")
    if s.user is not None and s.user.role == Role.CR:
        s.user.role = Role.STUDENT
        db.commit()
        db.refresh(s)
    log_from_request(db, request, current_user, "cr.remove", "student", resource_id=s.id)
    return _student_out(db, s)


@router.get("/cr-assignments", response_model=dict)
def list_cr_assignments(
    department_id: int | None = None,
    semester_id: int | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_STUDENTS)),
):
    """List current CRs. HODs only see their own department; admins see all."""
    q = db.query(Student).join(User, User.id == Student.user_id).filter(User.role == str(Role.CR))
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Student.department_id == current_user.faculty_profile.department_id)
    if department_id:
        q = q.filter(Student.department_id == department_id)
    if semester_id is not None:
        q = q.filter(Student.semester_id == semester_id)
    if section:
        q = q.filter(Student.section == section)
    if page_params["q"]:
        q = q.filter(
            User.name.ilike(f"%{page_params['q']}%")
            | User.email.ilike(f"%{page_params['q']}%")
            | Student.enrollment_number.ilike(f"%{page_params['q']}%")
        )
    total = q.count()
    rows = q.order_by(User.name).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_student_out(db, s) for s in rows], page_params["page"], page_params["page_size"], total)


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------


@router.get("/faculty", response_model=dict)
def list_faculty(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_FACULTY)),
):
    from app.models.subject import SubjectAssignment

    q = db.query(Faculty).join(User, User.id == Faculty.user_id)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Faculty.department_id == current_user.faculty_profile.department_id)
    if department_id:
        q = q.filter(Faculty.department_id == department_id)
    if page_params["q"]:
        q = q.filter(User.name.ilike(f"%{page_params['q']}%") | User.email.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(User.name).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    items = []
    for f in rows:
        subject_count = db.query(SubjectAssignment).filter(SubjectAssignment.faculty_id == f.id).count()
        items.append(
            {
                "id": f.id,
                "user_id": f.user_id,
                "department_id": f.department_id,
                "designation": f.designation,
                "specialization": f.specialization,
                "name": f.name,
                "email": f.email,
                "phone": f.user.phone if f.user else None,
                "role": str(f.user.role) if f.user else "faculty",
                "status": str(f.user.status) if f.user else "active",
                "college_id": f.user.college_id if f.user else None,
                "department_name": f.department.name if f.department else None,
                "subject_count": subject_count,
                "is_hod": f.department and f.department.hod_id == f.id,
            }
        )
    return paginated(items, page_params["page"], page_params["page_size"], total)


@router.post("/faculty", response_model=FacultyOut, status_code=201)
def create_faculty(
    payload: FacultyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    if current_user.role == Role.HOD:
        check_department_scope(current_user, payload.department_id)
    dept = db.get(Department, payload.department_id)
    if not dept:
        raise BadRequestError("Department does not exist.")

    role = Role.HOD if payload.is_hod else Role.FACULTY
    user, plaintext = auth_service.create_user_account(
        db,
        name=payload.name,
        email=payload.email,
        college_id=payload.college_id,
        role=role,
        password=payload.password,
        phone=payload.phone,
    )
    faculty = Faculty(
        user_id=user.id,
        department_id=payload.department_id,
        designation=payload.designation,
        specialization=payload.specialization,
    )
    db.add(faculty)
    if payload.is_hod:
        dept.hod_id = None  # resolved below after flush
    db.commit()
    db.refresh(faculty)
    if payload.is_hod:
        dept.hod_id = faculty.id
        db.commit()
        db.refresh(dept)
    log_from_request(db, request, current_user, "faculty.create", "faculty", resource_id=faculty.id)
    result = _faculty_out(db, faculty)
    # Surface an auto-generated password exactly once so the admin can share it
    # securely. Only the hash is stored; this is the only time it is exposed.
    if not payload.password:
        result["initial_password"] = plaintext
    return result


@router.put("/faculty/{faculty_id}", response_model=FacultyOut)
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    f = db.get(Faculty, faculty_id)
    if not f:
        raise NotFoundError("Faculty member not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, f.department_id)
    data = payload.model_dump(exclude_unset=True)
    is_hod = data.pop("is_hod", None)
    for k, v in data.items():
        if k in ("name", "email", "phone"):
            setattr(f.user, k, v)
        else:
            setattr(f, k, v)
    if is_hod is not None:
        if is_hod:
            f.department.hod_id = f.id
            f.user.role = Role.HOD
        else:
            if f.department and f.department.hod_id == f.id:
                f.department.hod_id = None
            if f.user.role == Role.HOD:
                f.user.role = Role.FACULTY
    db.commit()
    db.refresh(f)
    log_from_request(db, request, current_user, "faculty.update", "faculty", resource_id=f.id)
    return _faculty_out(db, f)


@router.delete("/faculty/{faculty_id}")
def delete_faculty(
    faculty_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_FACULTY)),
):
    f = db.get(Faculty, faculty_id)
    if not f:
        raise NotFoundError("Faculty member not found.")
    if current_user.role == Role.HOD:
        check_department_scope(current_user, f.department_id)
    log_from_request(db, request, current_user, "faculty.delete", "faculty", resource_id=f.id)
    user = f.user
    db.delete(f)
    if user:
        db.delete(user)
    db.commit()
    return {"success": True, "message": "Faculty member removed."}


# ---------------------------------------------------------------------------
# User administration
# ---------------------------------------------------------------------------


@router.get("/users", response_model=dict)
def list_users(
    role: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    if page_params["q"]:
        q = q.filter(User.name.ilike(f"%{page_params['q']}%") | User.email.ilike(f"%{page_params['q']}%") | User.college_id.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(User.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    items = [
        {
            **u.to_public_dict(),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "must_change_password": u.must_change_password,
        }
        for u in rows
    ]
    return paginated(items, page_params["page"], page_params["page_size"], total)


@router.put("/users/{user_id}", response_model=UserOutAdmin)
def update_user(
    user_id: int,
    payload: UserUpdateAdmin,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("role") and data["role"] != user.role:
        try:
            Role(data["role"])
        except ValueError:
            raise BadRequestError("Invalid role.")
        log_from_request(
            db, request, current_user, "user.role_change", "user", resource_id=user.id,
            details={"from": user.role, "to": data["role"]},
        )
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    log_from_request(db, request, current_user, "user.update", "user", resource_id=user.id)
    return user


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.")
    if user.id == current_user.id:
        raise BadRequestError("You cannot suspend your own account.")
    user.status = UserStatus.SUSPENDED
    auth_service.revoke_all_sessions(db, user.id)
    db.commit()
    log_from_request(db, request, current_user, "user.suspend", "user", resource_id=user.id)
    return {"success": True, "message": f"User {user.email} suspended and all sessions revoked."}


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.")
    user.status = UserStatus.ACTIVE
    db.commit()
    log_from_request(db, request, current_user, "user.activate", "user", resource_id=user.id)
    return {"success": True, "message": f"User {user.email} reactivated."}


@router.get("/users/permissions")
def list_permissions_for_role(role: str, current_user: User = Depends(require_permission(Permission.MANAGE_USERS))):
    try:
        r = Role(role)
    except ValueError:
        raise BadRequestError("Invalid role.")
    return {"role": str(r), "permissions": sorted(p.value for p in permissions_for_role(r))}
