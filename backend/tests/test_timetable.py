"""Timetable: listing, per-user views and faculty name resolution."""

from __future__ import annotations

from app.models.timetable import TimetableEntry


def test_every_role_can_list_timetable(client, tokens):
    for role in ("admin", "hod", "faculty", "cr", "student"):
        response = client.get(
            "/api/v1/timetable", headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 200, f"{role}: {response.text}"


def test_timetable_entry_resolves_names(client, student_headers):
    """faculty_name must resolve via the TimetableEntry.faculty relationship."""
    response = client.get("/api/v1/timetable?section=A", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    items = body.get("items", body.get("data", []))
    assert items, "Section A should have timetable entries"
    for entry in items:
        assert entry["subject_name"] is not None
        # faculty_name is the field that previously raised AttributeError.
        assert entry["faculty_name"] is not None


def test_student_own_timetable(client, student_headers):
    response = client.get("/api/v1/timetable/my", headers=student_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_faculty_own_timetable(client, faculty_headers):
    response = client.get("/api/v1/timetable/my", headers=faculty_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_section_timetable(client, faculty_headers):
    response = client.get("/api/v1/timetable/section/A", headers=faculty_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_admin_can_view_any_section(client, admin_headers):
    response = client.get("/api/v1/timetable/section/A", headers=admin_headers)
    assert response.status_code == 200, response.text


def test_student_cannot_create_timetable_entry(client, student_headers):
    response = client.post(
        "/api/v1/timetable",
        headers=student_headers,
        json={
            "day": "Monday",
            "period": 7,
            "subject_id": 1,
            "faculty_id": 1,
            "classroom_id": 1,
            "section": "A",
        },
    )
    assert response.status_code == 403, response.text


def test_seeded_timetable_exists(db):
    count = db.query(TimetableEntry).filter(TimetableEntry.section == "A").count()
    assert count > 0, "Seed data should populate section A's timetable."
