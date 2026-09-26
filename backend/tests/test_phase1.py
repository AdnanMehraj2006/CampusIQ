"""Phase 1 tests: user management, CR controls and section management.

Covers:
  * Admin student/faculty creation with a generated password that works at
    login and is never persisted in plaintext.
  * RBAC: non-admins cannot perform admin-only creation.
  * CR assignment: appoint/remove/reassign with the 2-CR-per-class limit and
    HOD department scoping, both enforced server-side.
  * CR attendance scope (Department + Semester + Section, read-only).
  * Section CRUD/management and form validation.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import Course, Department
from app.models.people import Student
from app.models.user import User
from tests.conftest import auth_headers, login


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _dept_id_by_code(db: Session, code: str) -> int:
    dept = db.query(Department).filter(Department.code == code).first()
    assert dept is not None, f"Department {code} missing from seed data"
    return dept.id


def _create_student(
    client: TestClient,
    headers: dict,
    department_id: int,
    db: Session,
    *,
    section: str = "A",
    semester_id: int | None = None,
    is_cr: bool = False,
    password: str | None = None,
):
    suffix = _suffix()
    course = db.query(Course).filter(Course.department_id == department_id).first()
    assert course is not None, f"Course for department {department_id} not found"
    if semester_id is None:
        semester = db.query(Semester).filter(Semester.course_id == course.id).first()
        semester_id = semester.id if semester else None
    payload: dict = {
        "name": f"P1 Student {suffix}",
        "email": f"p1student.{suffix}@campusiq.edu",
        "college_id": f"P1{suffix}",
        "enrollment_number": f"P1ENR{suffix}",
        "department_id": department_id,
        "course_id": course.id,
        "semester_id": semester_id,
        "section": section,
        "admission_year": 2024,
    }
    if is_cr:
        payload["is_cr"] = True
    if password is not None:
        payload["password"] = password
    response = client.post("/api/v1/students", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_faculty(client: TestClient, headers: dict, department_id: int, db: Session, is_hod: bool = False):
    suffix = _suffix()
    course = db.query(Course).filter(Course.department_id == department_id).first()
    assert course is not None, f"Course for department {department_id} not found"
    payload: dict = {
        "name": f"P1 Faculty {suffix}",
        "email": f"p1faculty.{suffix}@campusiq.edu",
        "college_id": f"P1FAC{suffix}",
        "department_id": department_id,
        "course_id": course.id,
        "designation": "Assistant Professor",
    }
    if is_hod:
        payload["is_hod"] = True
    response = client.post("/api/v1/faculty", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# 1. Admin student/faculty creation + generated password
# ---------------------------------------------------------------------------


def test_admin_creates_student_and_generated_password_works(
    client: TestClient, admin_headers: dict, db: Session
):
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, dept_id, db)

    assert created["role"] == "student"
    assert created["name"].startswith("P1 Student")
    # A generated password is returned exactly once.
    assert "initial_password" in created
    plaintext = created["initial_password"]
    assert plaintext
    assert "password" not in created or created.get("password") is None

    # The account can log in immediately with the generated password.
    token_response = login(client, created["email"], plaintext)
    assert token_response["access_token"]

    # Only the hash is persisted - the plaintext is not stored anywhere.
    user = db.query(User).filter(User.email == created["email"]).first()
    assert user is not None
    assert plaintext not in user.password_hash
    assert user.password_hash != plaintext


def test_admin_creates_faculty_and_generated_password_works(
    client: TestClient, admin_headers: dict, db: Session
):
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_faculty(client, admin_headers, dept_id, db)

    assert created["role"] == "faculty"
    assert "initial_password" in created
    plaintext = created["initial_password"]

    login(client, created["email"], plaintext)

    user = db.query(User).filter(User.email == created["email"]).first()
    assert user is not None
    assert plaintext not in user.password_hash


def test_created_student_visible_in_list_after_creation(
    client: TestClient, admin_headers: dict, db: Session
):
    """The newly created record must appear immediately (list refresh flow)."""
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, dept_id, db)
    response = client.get("/api/v1/students", headers=admin_headers)
    assert response.status_code == 200
    ids = [s["id"] for s in response.json()["items"]]
    assert created["id"] in ids


def test_provided_password_is_not_echoed(client: TestClient, admin_headers: dict, db: Session):
    """When the admin supplies a password it is never echoed back."""
    created = _create_student(
        client, admin_headers, 1, db, password="Supplied@12345"
    )
    # No generated password is surfaced for a caller-supplied password.
    assert not created.get("initial_password")


def test_unauthorized_users_cannot_create_students(
    client: TestClient, student_headers: dict, faculty_headers: dict, cr_headers: dict
):
    for headers in (student_headers, faculty_headers, cr_headers):
        response = client.post(
            "/api/v1/students",
            json={
                "name": "Nope",
                "email": f"nope.{_suffix()}@campusiq.edu",
                "college_id": f"NOPE{_suffix()}",
                "enrollment_number": f"NOPE{_suffix()}",
                "department_id": 1,
                "admission_year": 2024,
            },
            headers=headers,
        )
        assert response.status_code == 403, response.text


def test_unauthorized_users_cannot_create_faculty(
    client: TestClient, student_headers: dict, cr_headers: dict
):
    for headers in (student_headers, cr_headers):
        response = client.post(
            "/api/v1/faculty",
            json={
                "name": "Nope",
                "email": f"nofac.{_suffix()}@campusiq.edu",
                "college_id": f"NOFAC{_suffix()}",
                "department_id": 1,
            },
            headers=headers,
        )
        assert response.status_code == 403, response.text


def test_hod_cannot_create_student_outside_own_department(
    client: TestClient, hod_headers: dict, db: Session
):
    it_dept_id = _dept_id_by_code(db, "IT")
    it_course = db.query(Course).filter(Course.department_id == it_dept_id).first()
    assert it_course is not None
    it_semester = db.query(Semester).filter(Semester.course_id == it_course.id).first()
    if it_semester is None:
        it_semester = Semester(semester_number=1, course_id=it_course.id)
        db.add(it_semester)
        db.commit()
        db.refresh(it_semester)
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Out of scope",
            "email": f"oos.{_suffix()}@campusiq.edu",
            "college_id": f"OOS{_suffix()}",
            "enrollment_number": f"OOS{_suffix()}",
            "department_id": it_dept_id,
            "course_id": it_course.id,
            "semester_id": it_semester.id,
            "section": "A",
            "admission_year": 2024,
        },
        headers=hod_headers,
    )
    # hod.cse@campusiq.edu may only touch the CSE department.
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# 2. CR assignment
# ---------------------------------------------------------------------------


def _make_section(client: TestClient, headers: dict, db: Session, semester_id: int | None = None, course_id: int | None = None) -> str:
    """Create a throwaway contextual section so each CR test gets an isolated class quota."""
    name = f"T{_suffix()}"[:10]
    # Get or create a course for this section
    if course_id is None:
        cse_dept_id = _dept_id_by_code(db, "CSE")
        course = db.query(Course).filter(Course.department_id == cse_dept_id).first()
        assert course is not None
        course_id = course.id
    else:
        course = db.get(Course, course_id)
        assert course is not None
    
    # Use provided semester or create a new one
    if semester_id is None:
        semester = Semester(semester_number=99, course_id=course_id)
        db.add(semester)
        db.commit()
        db.refresh(semester)
        semester_id = semester.id
    
    response = client.post(
        "/api/v1/sections",
        json={"name": name, "course_id": course_id, "semester_id": semester_id, "is_active": True},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return name


def test_admin_can_assign_and_remove_cr(client: TestClient, admin_headers: dict, db: Session):
    dept_id = _dept_id_by_code(db, "CSE")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    assert semester is not None

    section = _make_section(client, admin_headers, db, semester.id)
    created = _create_student(
        client, admin_headers, dept_id, db, section=section, semester_id=semester.id
    )
    assert created["role"] == "student"

    assign = client.post(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)
    assert assign.status_code == 200, assign.text
    assert assign.json()["role"] == "cr"

    remove = client.delete(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)
    assert remove.status_code == 200, remove.text
    assert remove.json()["role"] == "student"


def test_cr_list_reflects_assignment(client: TestClient, admin_headers: dict, db: Session):
    dept_id = _dept_id_by_code(db, "CSE")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    section = _make_section(client, admin_headers, db, semester.id)
    created = _create_student(
        client, admin_headers, dept_id, db, section=section, semester_id=semester.id
    )

    client.post(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)

    response = client.get("/api/v1/cr-assignments", headers=admin_headers)
    assert response.status_code == 200
    ids = [s["id"] for s in response.json()["items"]]
    assert created["id"] in ids

    client.delete(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)


def test_max_two_crs_per_department_semester_section(
    client: TestClient, admin_headers: dict, db: Session
):
    dept_id = _dept_id_by_code(db, "CSE")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    section = _make_section(client, admin_headers, db, semester.id)

    a = _create_student(client, admin_headers, dept_id, db, section=section, semester_id=semester.id)
    b = _create_student(client, admin_headers, dept_id, db, section=section, semester_id=semester.id)
    c = _create_student(client, admin_headers, dept_id, db, section=section, semester_id=semester.id)

    first = client.post(f"/api/v1/students/{a['id']}/cr", headers=admin_headers)
    assert first.status_code == 200, first.text

    second = client.post(f"/api/v1/students/{b['id']}/cr", headers=admin_headers)
    assert second.status_code == 200, second.text

    # A third CR for the same Department + Semester + Section must be rejected.
    third = client.post(f"/api/v1/students/{c['id']}/cr", headers=admin_headers)
    assert third.status_code == 409, third.text
    assert "maximum" in third.json()["message"].lower()

    # Removing one frees a slot and allows reassignment.
    remove = client.delete(f"/api/v1/students/{a['id']}/cr", headers=admin_headers)
    assert remove.status_code == 200

    reassign = client.post(f"/api/v1/students/{c['id']}/cr", headers=admin_headers)
    assert reassign.status_code == 200, reassign.text
    assert reassign.json()["role"] == "cr"


def test_third_class_uses_independent_quota(
    client: TestClient, admin_headers: dict, db: Session
):
    """The 2-CR limit is per class: another section gets its own quota."""
    dept_id = _dept_id_by_code(db, "CSE")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()

    section_b = _make_section(client, admin_headers, db, semester.id)
    a = _create_student(client, admin_headers, dept_id, db, section=section_b, semester_id=semester.id)
    b = _create_student(client, admin_headers, dept_id, db, section=section_b, semester_id=semester.id)
    assert client.post(f"/api/v1/students/{a['id']}/cr", headers=admin_headers).status_code == 200
    assert client.post(f"/api/v1/students/{b['id']}/cr", headers=admin_headers).status_code == 200

    # A different section is a different class context: allowed.
    section_c = _make_section(client, admin_headers, db, semester.id)
    other = _create_student(client, admin_headers, dept_id, db, section=section_c, semester_id=semester.id)
    response = client.post(f"/api/v1/students/{other['id']}/cr", headers=admin_headers)
    assert response.status_code == 200, response.text


def test_hod_can_assign_cr_within_own_department(
    client: TestClient, hod_headers: dict, admin_headers: dict, db: Session
):
    cse_dept_id = _dept_id_by_code(db, "CSE")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    section = _make_section(client, admin_headers, db, semester.id)
    created = _create_student(
        client, admin_headers, cse_dept_id, db, section=section, semester_id=semester.id
    )

    response = client.post(f"/api/v1/students/{created['id']}/cr", headers=hod_headers)
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "cr"


def test_hod_cannot_assign_cr_outside_own_department(
    client: TestClient, hod_headers: dict, admin_headers: dict, db: Session
):
    it_dept_id = _dept_id_by_code(db, "IT")
    it_course = db.query(Course).filter(Course.department_id == it_dept_id).first()
    assert it_course is not None
    it_semester = db.query(Semester).filter(Semester.course_id == it_course.id).first()
    if it_semester is None:
        it_semester = Semester(semester_number=1, course_id=it_course.id)
        db.add(it_semester)
        db.commit()
        db.refresh(it_semester)
    section = _make_section(client, admin_headers, db, it_semester.id, it_course.id)
    created = _create_student(
        client, admin_headers, it_dept_id, db, section=section, semester_id=it_semester.id
    )

    response = client.post(f"/api/v1/students/{created['id']}/cr", headers=hod_headers)
    # The HOD (CSE) must not appoint a CR for an IT student.
    assert response.status_code == 403, response.text


def test_student_cannot_assign_cr(client: TestClient, student_headers: dict, db: Session):
    student = db.query(Student).first()
    assert student is not None
    response = client.post(f"/api/v1/students/{student.id}/cr", headers=student_headers)
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# 3. CR attendance scope
# ---------------------------------------------------------------------------


def _cr_account(db: Session) -> Student:
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(User.role == "cr")
        .first()
    )
    assert student is not None, "Seed data should contain a CR"
    return student


def test_cr_can_view_own_attendance(client: TestClient, db: Session):
    """A CR keeps seeing their own attendance exactly like a normal student."""
    cr = _cr_account(db)
    token = login(client, cr.user.email, "Cr@12345")["access_token"]
    headers = auth_headers(token)

    response = client.get("/api/v1/attendance/analytics/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total_classes"] >= 0


def test_cr_attendance_list_is_scoped_to_own_class(
    client: TestClient, db: Session
):
    cr = _cr_account(db)
    token = login(client, cr.user.email, "Cr@12345")["access_token"]
    headers = auth_headers(token)

    response = client.get("/api/v1/attendance", headers=headers)
    assert response.status_code == 200, response.text
    records = response.json()["items"]
    me = cr

    class_ids = {
        s.id
        for s in db.query(Student).filter(
            Student.department_id == me.department_id,
            Student.semester_id == me.semester_id,
            Student.section == me.section,
        ).all()
    }
    for record in records:
        assert record["student_id"] in class_ids, (
            "CR saw attendance for a student outside their class context"
        )


def test_cr_cannot_view_another_section_attendance(client: TestClient, db: Session):
    cr = _cr_account(db)
    token = login(client, cr.user.email, "Cr@12345")["access_token"]
    headers = auth_headers(token)

    other = cr.section == "A" and "B" or "A"
    response = client.get(f"/api/v1/attendance?section={other}", headers=headers)
    assert response.status_code == 403, response.text


def test_cr_cannot_view_another_class_student_details(
    client: TestClient, db: Session
):
    cr = _cr_account(db)
    token = login(client, cr.user.email, "Cr@12345")["access_token"]
    headers = auth_headers(token)

    from sqlalchemy import or_

    outside = (
        db.query(Student)
        .filter(
            Student.id != cr.id,
            or_(
                Student.department_id != cr.department_id,
                Student.semester_id != cr.semester_id,
                Student.section != cr.section,
            ),
        )
        .first()
    )
    assert outside is not None

    response = client.get(f"/api/v1/students/{outside.id}", headers=headers)
    assert response.status_code == 403, response.text


def test_cr_cannot_mark_or_edit_attendance(client: TestClient, db: Session):
    """A CR has read-only class access - no editing permissions at all."""
    cr = _cr_account(db)
    token = login(client, cr.user.email, "Cr@12345")["access_token"]
    headers = auth_headers(token)

    mark = client.post(
        "/api/v1/attendance",
        json={
            "subject_id": 1,
            "section": cr.section,
            "date": "2026-09-22",
            "marks": [{"student_id": cr.id, "status": "present"}],
        },
        headers=headers,
    )
    assert mark.status_code == 403, mark.text

    edit = client.put(
        "/api/v1/attendance/1",
        json={"status": "absent"},
        headers=headers,
    )
    assert edit.status_code == 403, edit.text


# ---------------------------------------------------------------------------
# 4. Section management
# ---------------------------------------------------------------------------


def test_admin_section_crud(client: TestClient, admin_headers: dict, db: Session):
    name = f"Z{_suffix()}"
    cse_dept_id = _dept_id_by_code(db, "CSE")
    course = db.query(Course).filter(Course.department_id == cse_dept_id).first()
    assert course is not None
    semester = Semester(semester_number=98, course_id=course.id)
    db.add(semester)
    db.commit()
    db.refresh(semester)
    created_response = client.post(
        "/api/v1/sections",
        json={"name": name, "description": "Phase 1 test section", "course_id": course.id, "semester_id": semester.id},
        headers=admin_headers,
    )
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    assert created["name"] == name
    assert created["is_active"] is True
    section_id = created["id"]

    # Duplicate name in same context is rejected.
    dup = client.post(
        "/api/v1/sections",
        json={"name": name, "course_id": course.id, "semester_id": semester.id, "is_active": True},
        headers=admin_headers,
    )
    assert dup.status_code == 409, dup.text

    # It shows up in the listing.
    listing = client.get(f"/api/v1/sections?course_id={course.id}&semester_id={semester.id}", headers=admin_headers)
    assert listing.status_code == 200
    assert any(s["id"] == section_id for s in listing.json()["items"])

    # Update.
    updated = client.put(
        f"/api/v1/sections/{section_id}",
        json={"description": "Updated description", "is_active": False},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["is_active"] is False
    assert updated.json()["description"] == "Updated description"

    # Delete works while nothing references the section.
    deleted = client.delete(f"/api/v1/sections/{section_id}", headers=admin_headers)
    assert deleted.status_code == 200, deleted.text
    assert db.get(Section, section_id) is None


def test_section_with_students_cannot_be_deleted(
    client: TestClient, admin_headers: dict, db: Session
):
    """Section A in seed data has students - deletion must be refused."""
    # Get a contextual section A that has students
    sections = client.get("/api/v1/sections", headers=admin_headers).json()["items"]
    # Find a section A with course_id/semester_id that has students
    section_a = next((s for s in sections if s["name"] == "A" and s.get("student_count", 0) > 0), None)
    assert section_a is not None, "Seed data should contain contextual section A with students"

    response = client.delete(f"/api/v1/sections/{section_a['id']}", headers=admin_headers)
    assert response.status_code == 409, response.text
    assert "deactivate" in response.json()["message"].lower()


def test_student_cannot_manage_sections(client: TestClient, student_headers: dict):
    create = client.post("/api/v1/sections", json={"name": "X", "is_active": True}, headers=student_headers)
    assert create.status_code == 403, create.text
    listing = client.get("/api/v1/sections", headers=student_headers)
    assert listing.status_code == 403, listing.text


# ---------------------------------------------------------------------------
# 5. Validation
# ---------------------------------------------------------------------------


def test_student_creation_rejects_invalid_section(
    client: TestClient, admin_headers: dict, db: Session
):
    cse_dept_id = _dept_id_by_code(db, "CSE")
    course = db.query(Course).filter(Course.department_id == cse_dept_id).first()
    assert course is not None
    semester = Semester(semester_number=97, course_id=course.id)
    db.add(semester)
    db.commit()
    db.refresh(semester)
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Section",
            "email": f"badsec.{_suffix()}@campusiq.edu",
            "college_id": f"BADSEC{_suffix()}",
            "enrollment_number": f"BADSEC{_suffix()}",
            "department_id": cse_dept_id,
            "course_id": course.id,
            "semester_id": semester.id,
            "section": "ZZ9",
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert "no active sections" in response.json()["message"].lower()


def test_student_creation_rejects_course_from_another_department(
    client: TestClient, admin_headers: dict, db: Session
):
    it_dept_id = _dept_id_by_code(db, "IT")
    # Find a course that belongs to CSE (not IT).
    from app.models.academic import Course

    cse_course_row = (
        db.query(Course)
        .join(Department, Department.id == Course.department_id)
        .filter(Department.code == "CSE")
        .first()
    )
    assert cse_course_row is not None
    cse_semester = db.query(Semester).filter(Semester.course_id == cse_course_row.id).first()
    assert cse_semester is not None

    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Course",
            "email": f"badcourse.{_suffix()}@campusiq.edu",
            "college_id": f"BADC{_suffix()}",
            "enrollment_number": f"BADC{_suffix()}",
            "department_id": it_dept_id,
            "course_id": cse_course_row.id,
            "semester_id": cse_semester.id,
            "section": "A",
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text


def test_student_creation_rejects_invalid_semester(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Semester",
            "email": f"badsem.{_suffix()}@campusiq.edu",
            "college_id": f"BADS{_suffix()}",
            "enrollment_number": f"BADS{_suffix()}",
            "department_id": 1,
            "course_id": 1,
            "section": "A",
            "admission_year": 2024,
            "semester_id": 999999,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text


def test_student_creation_rejects_non_numeric_admission_year(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Year",
            "email": f"badyear.{_suffix()}@campusiq.edu",
            "college_id": f"BADY{_suffix()}",
            "enrollment_number": f"BADY{_suffix()}",
            "department_id": 1,
            "section": "A",
            "admission_year": "not-a-number",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


def test_duplicate_email_rejected(client: TestClient, admin_headers: dict, db: Session):
    first = _create_student(client, admin_headers, 1, db)
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Dup Email",
            "email": first["email"],
            "college_id": f"DUP{_suffix()}",
            "enrollment_number": f"DUP{_suffix()}",
            "department_id": first["department_id"],
            "course_id": first["course_id"],
            "semester_id": first["semester_id"],
            "section": first["section"],
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 409, response.text




