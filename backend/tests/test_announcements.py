"""Announcements: listing, detail retrieval and targeting visibility."""

from __future__ import annotations

from app.models.comms import Announcement


def _any_announcement(db) -> Announcement:
    ann = db.query(Announcement).order_by(Announcement.id).first()
    assert ann is not None, "Seed data should contain announcements."
    return ann


def test_every_role_can_list_announcements(client, tokens):
    for role in ("admin", "hod", "faculty", "cr", "student"):
        response = client.get(
            "/api/v1/announcements", headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 200, f"{role}: {response.text}"


def test_announcement_detail(client, student_headers, db):
    ann = _any_announcement(db)
    response = client.get(
        f"/api/v1/announcements/{ann.id}", headers=student_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == ann.id


def test_announcement_list_has_expected_shape(client, student_headers):
    response = client.get("/api/v1/announcements", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    items = body.get("items", body.get("data", []))
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "title" in first
        assert "priority" in first
        assert "published_at" in first


def test_student_sees_everyone_targeted_announcement(client, student_headers, db):
    """An 'everyone' announcement must be visible to a student."""
    ann = (
        db.query(Announcement)
        .filter(Announcement.target_type == "everyone")
        .order_by(Announcement.id)
        .first()
    )
    assert ann is not None
    response = client.get(
        f"/api/v1/announcements/{ann.id}", headers=student_headers
    )
    assert response.status_code == 200


def test_announcement_targets_endpoint(client, faculty_headers):
    response = client.get(
        "/api/v1/announcements/targets/allowed", headers=faculty_headers
    )
    assert response.status_code == 200, response.text
    assert "targets" in response.json()


def test_student_cannot_publish_announcements(client, student_headers):
    response = client.post(
        "/api/v1/announcements",
        headers=student_headers,
        json={"title": "Nope", "content": "Should be blocked.", "target_type": "section", "section": "A"},
    )
    assert response.status_code == 403, response.text


def test_faculty_can_publish_section_announcement(client, faculty_headers, db):
    from app.models.subject import SubjectAssignment
    from app.models.user import User

    user = db.query(User).filter(User.email == "faculty@campusiq.edu").first()
    sa = (
        db.query(SubjectAssignment)
        .filter(SubjectAssignment.faculty_id == user.faculty_profile.id)
        .order_by(SubjectAssignment.id)
        .first()
    )
    response = client.post(
        "/api/v1/announcements",
        headers=faculty_headers,
        json={
            "title": "Test notice",
            "content": "Room change for tomorrow's lab.",
            "target_type": "section",
            "section": sa.section,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Test notice"
