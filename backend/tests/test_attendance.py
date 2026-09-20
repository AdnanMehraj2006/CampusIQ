"""Attendance: analytics, prediction, marking and section scoping."""

from __future__ import annotations

from app.models.subject import SubjectAssignment
from app.models.user import User


def _faculty_assignment(db) -> SubjectAssignment:
    """The subject/section the demo faculty actually teaches."""
    user = db.query(User).filter(User.email == "faculty@campusiq.edu").first()
    sa = (
        db.query(SubjectAssignment)
        .filter(SubjectAssignment.faculty_id == user.faculty_profile.id)
        .order_by(SubjectAssignment.id)
        .first()
    )
    assert sa is not None, "Demo faculty should have assigned subjects."
    return sa


def test_student_own_analytics(client, student_headers, db):
    user = db.query(User).filter(User.email == "adnan@campusiq.edu").first()
    response = client.get(
        f"/api/v1/attendance/analytics/student/{user.student_profile.id}",
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "overall_percentage" in body
    assert "subject_wise" in body


def test_student_analytics_me(client, student_headers):
    response = client.get(
        "/api/v1/attendance/analytics/me", headers=student_headers
    )
    assert response.status_code == 200, response.text
    assert "overall_percentage" in response.json()


def test_student_predict_me(client, student_headers):
    response = client.get("/api/v1/attendance/predict/me", headers=student_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "current_percentage" in body or "current" in body


def test_student_attendance_listing_is_own_only(client, student_headers, db):
    user = db.query(User).filter(User.email == "adnan@campusiq.edu").first()
    response = client.get("/api/v1/attendance", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    items = body.get("items", body.get("data", []))
    for row in items:
        assert row["student_id"] == user.student_profile.id


def test_faculty_can_view_own_section_analytics(client, faculty_headers, db):
    sa = _faculty_assignment(db)
    response = client.get(
        f"/api/v1/attendance/analytics/section/{sa.section}", headers=faculty_headers
    )
    assert response.status_code == 200, response.text


def test_faculty_can_fetch_roster(client, faculty_headers, db):
    sa = _faculty_assignment(db)
    response = client.get(
        f"/api/v1/attendance/roster/{sa.subject_id}/{sa.section}",
        headers=faculty_headers,
    )
    assert response.status_code == 200, response.text
    assert "students" in response.json()


def test_faculty_can_mark_attendance(client, faculty_headers, db):
    """The happy path must work end-to-end (also covers the audit log write)."""
    sa = _faculty_assignment(db)
    roster = client.get(
        f"/api/v1/attendance/roster/{sa.subject_id}/{sa.section}",
        headers=faculty_headers,
    ).json()["students"]
    student_id = roster[0]["student_id"]

    response = client.post(
        "/api/v1/attendance",
        headers=faculty_headers,
        json={
            "subject_id": sa.subject_id,
            "section": sa.section,
            "date": "2026-09-30",
            "marks": [{"student_id": student_id, "status": "present"}],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()[0]["status"] == "present"


def test_faculty_cannot_mark_unassigned_subject(client, faculty_headers, db):
    """Faculty may not mark attendance for a subject they do not teach."""
    user = db.query(User).filter(User.email == "faculty@campusiq.edu").first()
    other = (
        db.query(SubjectAssignment)
        .filter(SubjectAssignment.faculty_id != user.faculty_profile.id)
        .order_by(SubjectAssignment.id)
        .first()
    )
    response = client.post(
        "/api/v1/attendance",
        headers=faculty_headers,
        json={
            "subject_id": other.subject_id,
            "section": other.section,
            "date": "2026-09-19",
            "marks": [{"student_id": 1, "status": "present"}],
        },
    )
    assert response.status_code == 403, response.text


def test_hod_views_department_attendance(client, hod_headers):
    response = client.get("/api/v1/attendance", headers=hod_headers)
    assert response.status_code == 200, response.text


def test_admin_views_all_attendance(client, admin_headers):
    response = client.get("/api/v1/attendance", headers=admin_headers)
    assert response.status_code == 200, response.text


def test_faculty_can_view_attendance_history(client, faculty_headers, db):
    """Faculty can view attendance they previously submitted."""
    response = client.get("/api/v1/attendance/my", headers=faculty_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body or "data" in body


def test_faculty_history_scoped_to_own_submissions(client, faculty_headers, db):
    """Faculty history contains only records they marked."""
    response = client.get("/api/v1/attendance/my", headers=faculty_headers)
    assert response.status_code == 200
    body = response.json()
    items = body.get("items", body.get("data", []))
    for item in items:
        assert item["marked_by"] == db.query(User).filter(
            User.email == "faculty@campusiq.edu"
        ).first().id


def test_faculty_cannot_access_another_faculty_history(client, faculty_headers, db):
    """Faculty A cannot access Faculty B's attendance history."""
    response = client.get("/api/v1/attendance/my?marked_by=999", headers=faculty_headers)
    # The endpoint should not expose other faculty's data
    assert response.status_code == 200
    body = response.json()
    items = body.get("items", body.get("data", []))
    for item in items:
        assert item["marked_by"] == db.query(User).filter(
            User.email == "faculty@campusiq.edu"
        ).first().id


def test_attendance_history_is_faculty_only(
    client, student_headers, cr_headers, hod_headers, admin_headers
):
    """Only faculty may call GET /attendance/my - every other role is rejected."""
    for role, headers in (
        ("student", student_headers),
        ("cr", cr_headers),
        ("hod", hod_headers),
        ("admin", admin_headers),
    ):
        response = client.get("/api/v1/attendance/my", headers=headers)
        assert response.status_code == 403, f"{role} should not reach /attendance/my"


def test_faculty_history_includes_own_submission_and_section(client, faculty_headers, db):
    """A freshly submitted record appears in the faculty's history with its section."""
    sa = _faculty_assignment(db)
    roster = client.get(
        f"/api/v1/attendance/roster/{sa.subject_id}/{sa.section}",
        headers=faculty_headers,
    ).json()["students"]
    assert roster, "The seeded section should have students."
    student_id = roster[0]["student_id"]

    mark = client.post(
        "/api/v1/attendance",
        headers=faculty_headers,
        json={
            "subject_id": sa.subject_id,
            "section": sa.section,
            "date": "2026-01-05",
            "marks": [{"student_id": student_id, "status": "present"}],
        },
    )
    assert mark.status_code == 201, mark.text

    response = client.get("/api/v1/attendance/my", headers=faculty_headers)
    assert response.status_code == 200, response.text
    items = response.json().get("items", [])
    own = [
        i
        for i in items
        if i["student_id"] == student_id and i["subject_id"] == sa.subject_id
    ]
    assert own, "The history should contain the record just submitted."
    record = own[0]
    assert record["section"] == sa.section
    assert record["marked_by"] == (
        db.query(User).filter(User.email == "faculty@campusiq.edu").first().id
    )
