"""Settings, feedback and CR requests."""

from __future__ import annotations


def test_admin_can_read_settings(client, admin_headers):
    response = client.get("/api/v1/settings", headers=admin_headers)
    assert response.status_code == 200, response.text


def test_student_cannot_read_system_settings(client, student_headers):
    response = client.get("/api/v1/settings", headers=student_headers)
    assert response.status_code == 403, response.text


def test_feedback_listing_works_for_authorized_roles(client, tokens):
    for role in ("admin", "hod", "faculty", "cr", "student"):
        response = client.get(
            "/api/v1/feedback", headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 200, f"{role}: {response.text}"


def test_feedback_resolves_subject_name(client, student_headers, db):
    """The Feedback.subject relationship must resolve without AttributeError."""
    from app.models.comms import Feedback

    has_subject = db.query(Feedback).filter(Feedback.subject_id.isnot(None)).first()
    if has_subject is None:
        # Nothing seeded with a subject; create feedback targeted at one.
        from app.models.subject import Subject

        subject = db.query(Subject).order_by(Subject.id).first()
        user = db.query(Feedback).order_by(Feedback.id).first()
        if subject is not None and user is not None:
            user.subject_id = subject.id
            db.commit()
            db.refresh(user)
            has_subject = user
    if has_subject is not None:
        response = client.get("/api/v1/feedback", headers=student_headers)
        assert response.status_code == 200
        body = response.json()
        items = body.get("items", body.get("data", []))
        assert isinstance(items, list)


def test_student_can_submit_feedback(client, student_headers):
    response = client.post(
        "/api/v1/feedback",
        headers=student_headers,
        json={
            "target_type": "subject",
            "subject_id": 1,
            "rating": 5,
            "message": "Great classes.",
        },
    )
    assert response.status_code in (200, 201), response.text


def test_cr_can_list_own_requests(client, cr_headers):
    response = client.get("/api/v1/cr/requests", headers=cr_headers)
    assert response.status_code == 200, response.text


def test_student_cannot_view_cr_requests(client, student_headers):
    response = client.get("/api/v1/cr/requests", headers=student_headers)
    assert response.status_code == 403, response.text


def test_admin_permissions_endpoint(client, admin_headers):
    response = client.get(
        "/api/v1/users/permissions?role=hod", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "hod"
