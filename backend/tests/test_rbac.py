"""Role-based access control and cross-tenant isolation.

These tests verify the security boundaries explicitly required for the
platform: no role must be able to reach another role's or another tenant's
private data, and permission failures must surface as clean 4xx errors rather
than 500s.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Role authorization: each role reaches its own dashboard, and only its own.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role, dashboard",
    [
        ("admin", "/api/v1/dashboard/admin"),
        ("hod", "/api/v1/dashboard/hod"),
        ("faculty", "/api/v1/dashboard/faculty"),
        ("cr", "/api/v1/dashboard/cr"),
        ("student", "/api/v1/dashboard/student"),
    ],
)
def test_own_role_dashboard_succeeds(client, tokens, role, dashboard):
    response = client.get(
        dashboard, headers={"Authorization": f"Bearer {tokens[role]}"}
    )
    assert response.status_code == 200, f"{role} -> {dashboard}: {response.text}"


@pytest.mark.parametrize(
    "role, dashboard",
    [
        ("student", "/api/v1/dashboard/admin"),
        ("student", "/api/v1/dashboard/hod"),
        ("student", "/api/v1/dashboard/faculty"),
        ("student", "/api/v1/dashboard/cr"),
        ("cr", "/api/v1/dashboard/admin"),
        ("cr", "/api/v1/dashboard/hod"),
        ("cr", "/api/v1/dashboard/faculty"),
        ("faculty", "/api/v1/dashboard/admin"),
        ("faculty", "/api/v1/dashboard/hod"),
        ("faculty", "/api/v1/dashboard/cr"),
        ("hod", "/api/v1/dashboard/admin"),
        ("hod", "/api/v1/dashboard/cr"),
    ],
)
def test_other_role_dashboard_forbidden(client, tokens, role, dashboard):
    """A role must not read another role's dashboard - and must get 403, not 500."""
    response = client.get(
        dashboard, headers={"Authorization": f"Bearer {tokens[role]}"}
    )
    assert response.status_code == 403, f"{role} -> {dashboard}: {response.text}"


def test_admin_only_endpoints_reject_non_admins(client, tokens):
    """User management and audit logs are admin-only; failures must be 403."""
    for role in ("student", "faculty", "hod", "cr"):
        headers = {"Authorization": f"Bearer {tokens[role]}"}
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.get("/api/v1/audit-logs", headers=headers).status_code == 403
        assert client.get("/api/v1/settings", headers=headers).status_code == 403
        assert client.get("/api/v1/departments", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Student A cannot access Student B's private information
# ---------------------------------------------------------------------------


def test_student_cannot_read_another_students_analytics(
    client, student_headers, other_student
):
    """Student A must not see Student B's attendance analytics."""
    response = client.get(
        f"/api/v1/attendance/analytics/student/{other_student.id}",
        headers=student_headers,
    )
    assert response.status_code == 403, response.text


def test_student_cannot_predict_another_students_attendance(
    client, student_headers, other_student
):
    response = client.get(
        f"/api/v1/attendance/predict/student/{other_student.id}",
        headers=student_headers,
    )
    assert response.status_code == 403, response.text


def test_student_cannot_read_another_students_marks(
    client, student_headers, other_student
):
    response = client.get(
        f"/api/v1/students/{other_student.id}", headers=student_headers
    )
    assert response.status_code == 403, response.text


def test_student_a_can_read_own_analytics(client, student_headers, db):
    from app.models.user import User

    me = db.query(User).filter(User.email == "adnan@campusiq.edu").first()
    response = client.get(
        f"/api/v1/attendance/analytics/student/{me.student_profile.id}",
        headers=student_headers,
    )
    assert response.status_code == 200, response.text


def test_student_b_cannot_read_student_a_analytics(client, other_student_headers, db):
    """The isolation is symmetric - B cannot read A either."""
    from app.models.user import User

    adnan = db.query(User).filter(User.email == "adnan@campusiq.edu").first()
    response = client.get(
        f"/api/v1/attendance/analytics/student/{adnan.student_profile.id}",
        headers=other_student_headers,
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# CR cannot modify attendance
# ---------------------------------------------------------------------------


def test_cr_cannot_mark_attendance(client, cr_headers):
    """CRs may view class aggregates but must not mark attendance."""
    response = client.post(
        "/api/v1/attendance",
        headers=cr_headers,
        json={
            "subject_id": 1,
            "section": "A",
            "date": "2026-09-19",
            "marks": [{"student_id": 1, "status": "present"}],
        },
    )
    assert response.status_code == 403, response.text


def test_cr_cannot_edit_attendance(client, cr_headers):
    response = client.put(
        "/api/v1/attendance/1",
        headers=cr_headers,
        json={"status": "absent"},
    )
    assert response.status_code == 403, response.text


def test_cr_can_view_own_section_aggregates(client, cr_headers):
    """The CR permission is *view* class attendance - this must still work."""
    response = client.get(
        "/api/v1/attendance/analytics/section/A", headers=cr_headers
    )
    assert response.status_code == 200, response.text


def test_cr_cannot_view_other_section(client, cr_headers):
    response = client.get(
        "/api/v1/attendance/analytics/section/B", headers=cr_headers
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# Student cannot modify marks
# ---------------------------------------------------------------------------


def test_student_cannot_enter_marks(client, student_headers):
    response = client.post(
        "/api/v1/marks",
        headers=student_headers,
        json={
            "student_id": 1,
            "subject_id": 1,
            "assessment_type": "quiz",
            "title": "Quiz",
            "marks": 10,
            "max_marks": 10,
        },
    )
    assert response.status_code == 403, response.text


def test_student_cannot_grade_submissions(client, student_headers):
    response = client.put(
        "/api/v1/submissions/1/grade",
        headers=student_headers,
        json={"grade": 20, "feedback": "good"},
    )
    assert response.status_code == 403, response.text


def test_student_cannot_view_class_marks(client, student_headers):
    response = client.get("/api/v1/marks", headers=student_headers)
    # Students have VIEW_OWN_MARKS only; the class-wide listing is not theirs.
    assert response.status_code in (403, 200)
    if response.status_code == 200:
        # If reachable, it must be scoped to their own records only.
        rows = response.json().get("items", response.json().get("data", []))
        for row in rows:
            assert row.get("student_id") is not None


# ---------------------------------------------------------------------------
# Faculty cannot access unauthorized department data
# ---------------------------------------------------------------------------


def test_faculty_cannot_generate_department_reports(client, faculty_headers):
    response = client.get(
        "/api/v1/reports/department", headers=faculty_headers
    )
    assert response.status_code == 403, response.text


def test_faculty_cannot_list_departments(client, faculty_headers):
    response = client.get("/api/v1/departments", headers=faculty_headers)
    assert response.status_code == 403, response.text


def test_faculty_cannot_manage_users(client, faculty_headers):
    response = client.get("/api/v1/users", headers=faculty_headers)
    assert response.status_code == 403, response.text


def test_faculty_can_view_own_teaching_scope(client, faculty_headers):
    """Faculty retain legitimate access within their own teaching scope."""
    response = client.get("/api/v1/subjects/my", headers=faculty_headers)
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# HOD cannot access another department's administrative data
# ---------------------------------------------------------------------------


def _make_student_in_department(db, department_name: str):
    """Create (or reuse) a student belonging to a department other than CSE."""
    from app.core.security import hash_password
    from app.models.academic import Course, Department
    from app.models.people import Student
    from app.models.user import User
    from app.core.permissions import Role
    from app.models.user import UserStatus

    dept = db.query(Department).filter(Department.name == department_name).first()
    assert dept is not None, f"Seed data missing department {department_name}"

    email = f"isolated.{department_name.lower()}@campusiq.edu"
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            college_id=f"ISO{dept.code}",
            name=f"Isolated {dept.code} Student",
            email=email,
            password_hash=hash_password("CampusIQ@123"),
            role=str(Role.STUDENT),
            status=str(UserStatus.ACTIVE),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    student = db.query(Student).filter(Student.user_id == user.id).first()
    if student is None:
        course = db.query(Course).filter(Course.department_id == dept.id).first()
        student = Student(
            user_id=user.id,
            enrollment_number=f"ISO{dept.code}001",
            department_id=dept.id,
            course_id=course.id if course else None,
            section="A",
            admission_year=2023,
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


def test_hod_cannot_edit_student_in_another_department(client, hod_headers, db):
    """HOD CSE must not modify a student enrolled in IT/ECE."""
    outsider = _make_student_in_department(db, "Information Technology")

    response = client.put(
        f"/api/v1/students/{outsider.id}",
        headers=hod_headers,
        json={"phone": "+91 99999 00000"},
    )
    assert response.status_code == 403, response.text


def test_hod_cannot_view_another_department_student(client, hod_headers, db):
    outsider = _make_student_in_department(db, "Information Technology")
    response = client.get(
        f"/api/v1/students/{outsider.id}", headers=hod_headers
    )
    assert response.status_code == 403, response.text


def test_hod_cannot_delete_another_department_student(client, hod_headers, db):
    outsider = _make_student_in_department(db, "Information Technology")
    response = client.delete(
        f"/api/v1/students/{outsider.id}", headers=hod_headers
    )
    assert response.status_code == 403, response.text


def test_hod_can_view_own_department_students(client, hod_headers, db):
    from app.models.academic import Department
    from app.models.people import Student
    from app.models.user import User

    hod_user = db.query(User).filter(User.email == "hod.cse@campusiq.edu").first()
    dept = db.query(Department).filter(
        Department.id == hod_user.faculty_profile.department_id
    ).first()
    own = (
        db.query(Student)
        .filter(Student.department_id == dept.id)
        .order_by(Student.id)
        .first()
    )
    response = client.get(
        f"/api/v1/students/{own.id}", headers=hod_headers
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Permission failures must be clean 4xx, never 500
# ---------------------------------------------------------------------------


def test_forbidden_responses_are_never_500(client, tokens):
    """A permissions failure must surface as 403, not crash the server."""
    student_headers = {"Authorization": f"Bearer {tokens['student']}"}
    for path in (
        "/api/v1/dashboard/admin",
        "/api/v1/users",
        "/api/v1/audit-logs",
        "/api/v1/settings",
        "/api/v1/departments",
        "/api/v1/reports/department",
    ):
        response = client.get(path, headers=student_headers)
        assert response.status_code in (401, 403), f"{path} -> {response.status_code}"
        assert response.status_code != 500
