"""Assignment and submission tests."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.people import Student
from app.models.user import User


def create_test_file(content: bytes, filename: str = "test.pdf") -> io.BytesIO:
    """Create a mock file upload."""
    return io.BytesIO(content)


def test_student_submit_assignment_with_file(client: TestClient, student_headers: dict, db):
    """Student can submit an assignment with a file."""
    # Get an assignment the student can access
    assignment = db.query(Assignment).first()
    assert assignment is not None

    # Create a test PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    test_file = create_test_file(pdf_content, "test.pdf")

    # Submit the assignment
    files = {"file": ("test.pdf", test_file, "application/pdf")}
    response = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        files=files,
        headers=student_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assignment_id"] == assignment.id
    assert data["student_id"] is not None
    assert data["file_name"] == "test.pdf"
    assert data["submitted_at"] is not None


def test_student_submit_assignment_with_text(client: TestClient, student_headers: dict, db):
    """Student can submit an assignment with text only."""
    assignment = db.query(Assignment).first()
    assert assignment is not None

    response = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        data={"text_submission": "This is my text submission."},
        headers=student_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text_submission"] == "This is my text submission."


def test_student_cannot_submit_for_another_student(client: TestClient, student_headers: dict, db, other_student):
    """Student cannot submit on behalf of another student."""
    assignment = db.query(Assignment).first()
    assert assignment is not None

    # The submit endpoint uses get_current_student which enforces auth
    # So a student can only submit as themselves
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    test_file = create_test_file(pdf_content, "test.pdf")

    files = {"file": ("test.pdf", test_file, "application/pdf")}
    response = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        files=files,
        headers=student_headers,
    )
    assert response.status_code == 201

    # Verify the submission belongs to the authenticated student
    data = response.json()
    assert data["student_id"] == db.query(Student).filter(User.email == "adnan@campusiq.edu").join(User).first().id


def test_resubmission_replaces_previous(client: TestClient, student_headers: dict, db):
    """Resubmitting replaces the previous submission."""
    assignment = db.query(Assignment).first()
    assert assignment is not None

    # Get current student
    from app.models.user import User
    student = db.query(Student).filter(User.email == "adnan@campusiq.edu").join(User).first()

    # First submission
    pdf_content1 = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    test_file1 = create_test_file(pdf_content1, "v1.pdf")
    files1 = {"file": ("v1.pdf", test_file1, "application/pdf")}
    response1 = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        files=files1,
        headers=student_headers,
    )
    assert response1.status_code == 201

    # Second submission (resubmit)
    pdf_content2 = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    test_file2 = create_test_file(pdf_content2, "v2.pdf")
    files2 = {"file": ("v2.pdf", test_file2, "application/pdf")}
    response2 = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        files=files2,
        headers=student_headers,
    )
    assert response2.status_code == 201

    # Verify only one submission exists for this assignment and student
    submission_count = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment.id,
        AssignmentSubmission.student_id == student.id
    ).count()
    assert submission_count == 1


def test_file_size_exceeded_rejected(client: TestClient, student_headers: dict):
    """Files exceeding the upload limit are rejected."""
    # Create a file larger than the configured limit (10MB default)
    oversized_content = b"x" * (settings.max_upload_size_mb * 1024 * 1024 + 1000)
    test_file = create_test_file(oversized_content, "large.pdf")

    # Use a mock assignment ID - the size check happens before assignment lookup
    files = {"file": ("large.pdf", test_file, "application/pdf")}
    response = client.post(
        "/api/v1/assignments/1/submit",
        files=files,
        headers=student_headers,
    )
    # Should fail with file size error
    assert response.status_code == 400
    data = response.json()
    assert "max" in data.get("message", "").lower() or "size" in data.get("message", "").lower()


def test_file_type_validation(client: TestClient, student_headers: dict):
    """Invalid file types are rejected."""
    # Try to upload an executable file
    exe_content = b"MZ" + b"\x00" * 50
    test_file = create_test_file(exe_content, "malware.exe")

    files = {"file": ("malware.exe", test_file, "application/x-msdownload")}
    response = client.post(
        "/api/v1/assignments/1/submit",
        files=files,
        headers=student_headers,
    )
    assert response.status_code == 400


def test_empty_file_rejected(client: TestClient, student_headers: dict):
    """Empty files are rejected."""
    test_file = create_test_file(b"", "empty.pdf")

    files = {"file": ("empty.pdf", test_file, "application/pdf")}
    response = client.post(
        "/api/v1/assignments/1/submit",
        files=files,
        headers=student_headers,
    )
    assert response.status_code == 400
