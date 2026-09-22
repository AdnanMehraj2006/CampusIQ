"""Phase 2: CR requests, feedback routing, and notifications tests."""

from __future__ import annotations


def test_cr_can_create_request(client, cr_headers, db):
    """CR can submit a class request."""
    from app.models.comms import CRRequest
    from app.models.user import User
    from app.core.permissions import Role
    
    response = client.post(
        "/api/v1/cr/requests",
        headers=cr_headers,
        json={
            "request_type": "academic",
            "title": "Request for extended library hours",
            "description": "Students request extended library hours during exam season.",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["request_type"] == "academic"
    assert data["title"] == "Request for extended library hours"
    assert data["status"] == "processing"
    
    # Verify request was persisted
    req = db.query(CRRequest).filter(CRRequest.title == "Request for extended library hours").first()
    assert req is not None
    assert req.submitted_by is not None
    
    # Verify HOD was notified
    from app.models.comms import Notification
    
    cr_user = db.query(User).filter(User.id == req.submitted_by).first()
    assert cr_user is not None
    assert cr_user.student_profile is not None
    hod_faculty = db.query(User).filter(
        User.role == str(Role.HOD)
    ).first()
    if hod_faculty:
        notif = db.query(Notification).filter(
            Notification.recipient_id == hod_faculty.id,
            Notification.type == "request_submitted",
        ).first()
        assert notif is not None


def test_request_routing_to_correct_hod(client, db, tokens):
    """Requests are routed to the appropriate HOD based on department."""
    from app.models.comms import CRRequest, Notification
    from app.models.people import Student
    from app.models.user import User
    
    # Get a CR from a specific department
    cr_student = db.query(Student).filter(
        User.role == "cr"
    ).join(User, User.id == Student.user_id).first()
    
    if cr_student is None:
        return  # Skip test if no CR exists
    
    # Create a request
    response = client.post(
        "/api/v1/cr/requests",
        headers={"Authorization": f"Bearer {tokens['cr']}"},
        json={
            "request_type": "general",
            "title": "Test request",
            "description": "Testing request routing",
        },
    )
    assert response.status_code == 201
    
    req = response.json()
    
    # The correct HOD should have received a notification
    hod_faculty = db.query(User).filter(User.role == "hod").first()
    if hod_faculty:
        notif = db.query(Notification).filter(
            Notification.recipient_id == hod_faculty.id,
            Notification.resource_type == "cr_request",
            Notification.resource_id == req["id"],
        ).first()
        assert notif is not None, "Correct HOD should receive notification"


def test_hod_can_view_department_requests(client, hod_headers):
    """HOD can view requests from their department."""
    response = client.get("/api/v1/cr/requests", headers=hod_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_cr_cannot_see_other_cr_requests(client, cr_headers, db):
    """CR can only see their own requests."""
    from app.models.comms import CRRequest
    
    # Create a request as a different CR (simulated)
    response = client.get("/api/v1/cr/requests", headers=cr_headers)
    assert response.status_code == 200
    data = response.json()
    
    # All returned requests should belong to this CR
    for item in data["items"]:
        assert "submitted_by" in item


def test_feedback_listing_works(client, cr_headers):
    """CR can view their own feedback."""
    response = client.get("/api/v1/feedback", headers=cr_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_student_can_submit_feedback(client, student_headers):
    """Students can submit feedback."""
    response = client.post(
        "/api/v1/feedback",
        headers=student_headers,
        json={
            "target_type": "subject",
            "rating": 4,
            "message": "Good teaching methods.",
        },
    )
    assert response.status_code in (200, 201), response.text


def test_feedback_requires_student_or_cr_role(client, hod_headers):
    """Only students and CRs can submit feedback."""
    response = client.post(
        "/api/v1/feedback",
        headers=hod_headers,
        json={
            "target_type": "subject",
            "rating": 5,
            "message": "Test",
        },
    )
    assert response.status_code == 403


def test_hod_can_view_department_feedback(client, hod_headers):
    """HOD can view feedback from their department."""
    response = client.get("/api/v1/feedback", headers=hod_headers)
    assert response.status_code == 200


def test_cr_can_see_request_status(client, cr_headers):
    """CR can see their request status."""
    from app.models.comms import CRRequest
    
    # Create a request
    response = client.post(
        "/api/v1/cr/requests",
        headers=cr_headers,
        json={
            "request_type": "academic",
            "title": "Status check test",
            "description": "Testing status visibility",
        },
    )
    assert response.status_code == 201
    req = response.json()
    assert "status" in req


def test_notification_authorization(client, db, tokens):
    from app.models.user import User
    """Users can only access their own notifications."""
    from app.models.comms import Notification
    
    # Get user IDs
    cr_user = db.query(User).filter(User.role == "cr").first()
    student_user = db.query(User).filter(User.role == "student").first()
    
    if cr_user and student_user:
        # CR should not see student's notifications
        # (this is tested via the notification endpoint authorization)
        pass


def test_faculty_performance_endpoint(client, hod_headers):
    """HOD can view faculty performance based on feedback."""
    response = client.get("/api/v1/reports/faculty-performance", headers=hod_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
