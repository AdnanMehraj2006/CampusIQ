"""Phase 1 tests: user management and CR controls.

Covers:
  * Admin student/faculty creation with a generated password that works at
    login and is never persisted in plaintext.
  * RBAC: non-admins cannot perform admin-only creation.
  * CR assignment: appoint/reassign with department-scoped access.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import Course, Department
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
    password: str | None = None,
):
    suffix = _suffix()
    course = db.query(Course).filter(Course.department_id == department_id).first()
    assert course is not None, f"Course for department {department_id} not found"
    payload: dict = {
        "name": f"P1 Student {suffix}",
        "email": f"p1student.{suffix}@campusiq.edu",
        "college_id": f"P1{suffix}",
        "enrollment_number": f"P1ENR{suffix}",
        "department_id": department_id,
        "course_id": course.id,
        "admission_year": 2024,
    }
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
    assert "initial_password" in created
    plaintext = created["initial_password"]
    assert plaintext
    assert "password" not in created or created.get("password") is None

    token_response = login(client, created["email"], plaintext)
    assert token_response["access_token"]

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
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, dept_id, db)
    response = client.get("/api/v1/students", headers=admin_headers)
    assert response.status_code == 200
    ids = [s["id"] for s in response.json()["items"]]
    assert created["id"] in ids


def test_provided_password_is_not_echoed(client: TestClient, admin_headers: dict, db: Session):
    created = _create_student(
        client, admin_headers, 1, db, password="Supplied@12345"
    )
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
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Out of scope",
            "email": f"oos.{_suffix()}@campusiq.edu",
            "college_id": f"OOS{_suffix()}",
            "enrollment_number": f"OOS{_suffix()}",
            "department_id": it_dept_id,
            "course_id": it_course.id,
            "admission_year": 2024,
        },
        headers=hod_headers,
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# 2. CR assignment
# ---------------------------------------------------------------------------


def test_admin_can_assign_and_remove_cr(client: TestClient, admin_headers: dict, db: Session):
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, dept_id, db)
    assert created["role"] == "student"

    assign = client.post(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)
    assert assign.status_code == 200, assign.text
    assert assign.json()["role"] == "cr"

    remove = client.delete(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)
    assert remove.status_code == 200, remove.text
    assert remove.json()["role"] == "student"


def test_cr_list_reflects_assignment(client: TestClient, admin_headers: dict, db: Session):
    dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, dept_id, db)

    client.post(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)

    response = client.get("/api/v1/cr-assignments", headers=admin_headers)
    assert response.status_code == 200
    ids = [s["id"] for s in response.json()["items"]]
    assert created["id"] in ids

    client.delete(f"/api/v1/students/{created['id']}/cr", headers=admin_headers)


def test_hod_can_assign_cr_within_own_department(
    client: TestClient, hod_headers: dict, admin_headers: dict, db: Session
):
    cse_dept_id = _dept_id_by_code(db, "CSE")
    created = _create_student(client, admin_headers, cse_dept_id, db)

    response = client.post(f"/api/v1/students/{created['id']}/cr", headers=hod_headers)
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "cr"


def test_hod_cannot_assign_cr_outside_own_department(
    client: TestClient, hod_headers: dict, admin_headers: dict, db: Session
):
    it_dept_id = _dept_id_by_code(db, "IT")
    created = _create_student(client, admin_headers, it_dept_id, db)

    response = client.post(f"/api/v1/students/{created['id']}/cr", headers=hod_headers)
    assert response.status_code == 403, response.text


def test_student_cannot_assign_cr(client: TestClient, student_headers: dict, db: Session):
    from app.models.people import Student
    student = db.query(Student).first()
    assert student is not None
    response = client.post(f"/api/v1/students/{student.id}/cr", headers=student_headers)
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# 3. Validation
# ---------------------------------------------------------------------------


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
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 409, response.text


def test_student_creation_rejects_invalid_course(
    client: TestClient, admin_headers: dict, db: Session
):
    it_dept_id = _dept_id_by_code(db, "IT")
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Course",
            "email": f"badcourse.{_suffix()}@campusiq.edu",
            "college_id": f"BADC{_suffix()}",
            "enrollment_number": f"BADC{_suffix()}",
            "department_id": it_dept_id,
            "course_id": 999999,
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text


def test_student_creation_rejects_invalid_department(
    client: TestClient, admin_headers: dict, db: Session
):
    course = db.query(Course).filter(Course.department_id == 1).first()
    assert course is not None
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Bad Dept",
            "email": f"baddept.{_suffix()}@campusiq.edu",
            "college_id": f"BAD{_suffix()}",
            "enrollment_number": f"BAD{_suffix()}",
            "department_id": 999999,
            "course_id": course.id,
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text


# ---------------------------------------------------------------------------
# 4. Import User
# ---------------------------------------------------------------------------

from app.models.user import User


def test_admin_cannot_create_duplicate_email(
    client: TestClient, admin_headers: dict, db: Session
):
    first = _create_student(client, admin_headers, 1, db)
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Duplicate",
            "email": first["email"],
            "college_id": f"DUP{_suffix()}",
            "enrollment_number": f"DUPENR{_suffix()}",
            "department_id": 2,
            "course_id": 2,
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 409, response.text


def test_student_can_update_profile(
    client: TestClient, admin_headers: dict, db: Session
):
    from app.models.people import Student
    student = db.query(Student).first()
    assert student is not None

    response = client.put(
        f"/api/v1/students/{student.id}",
        json={"guardian_name": "New Guardian"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text


def test_admin_can_update_student(
    client: TestClient, admin_headers: dict, db: Session
):
    dept_id = _dept_id_by_code(db, "CSE")
    student = _create_student(client, admin_headers, dept_id, db)

    response = client.put(
        f"/api/v1/students/{student['id']}",
        json={"guardian_name": "Updated Guardian"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["guardian_name"] == "Updated Guardian"
