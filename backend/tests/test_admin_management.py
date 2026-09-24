"""Admin management tests: students, faculty, class teachers."""

from fastapi.testclient import TestClient


def test_admin_can_create_student(client: TestClient, admin_headers: dict, db):
    """Admin can create a new student."""
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Test Student",
            "email": "test.student@campusiq.edu",
            "college_id": "TEST001",
            "enrollment_number": "ENR2026TEST001",
            "department_id": 1,
            "course_id": 1,
            "semester_id": 1,
            "section": "A",
            "admission_year": 2026,
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Student"
    assert data["email"] == "test.student@campusiq.edu"
    assert data["enrollment_number"] == "ENR2026TEST001"
    assert data["role"] == "student"


def test_admin_cannot_create_duplicate_enrollment(client: TestClient, admin_headers: dict, db):
    """Cannot create two students with same enrollment number."""
    # First student creation
    response1 = client.post(
        "/api/v1/students",
        json={
            "name": "Student One",
            "email": "one@campusiq.edu",
            "college_id": "ONE001",
            "enrollment_number": "ENR2026001",
            "department_id": 1,
            "course_id": 1,
            "semester_id": 1,
            "section": "A",
            "admission_year": 2026,
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    assert response1.status_code == 201

    # Second student with same enrollment
    response2 = client.post(
        "/api/v1/students",
        json={
            "name": "Student Two",
            "email": "two@campusiq.edu",
            "college_id": "TWO001",
            "enrollment_number": "ENR2026001",
            "department_id": 1,
            "course_id": 1,
            "semester_id": 1,
            "section": "A",
            "admission_year": 2026,
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["message"].lower()


def test_hod_can_create_student(client: TestClient, hod_headers: dict, db):
    """HOD can create students within their department."""
    response = client.post(
        "/api/v1/students",
        json={
            "name": "HOD Student",
            "email": "hodstudent@campusiq.edu",
            "college_id": "HOD001",
            "enrollment_number": "ENR2026HOD001",
            "department_id": 1,
            "course_id": 1,
            "semester_id": 1,
            "section": "A",
            "admission_year": 2026,
            "password": "Test@123",
        },
        headers=hod_headers,
    )
    assert response.status_code == 201


def test_student_cannot_create_student(client: TestClient, student_headers: dict):
    """Regular student cannot create other students."""
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Unauthorized Student",
            "email": "unauth@campusiq.edu",
            "college_id": "UN001",
            "enrollment_number": "ENR2026UN001",
            "department_id": 1,
            "admission_year": 2026,
            "password": "Test@123",
        },
        headers=student_headers,
    )
    assert response.status_code == 403


def test_admin_can_create_faculty(client: TestClient, admin_headers: dict):
    """Admin can create a new faculty member."""
    response = client.post(
        "/api/v1/faculty",
        json={
            "name": "Test Faculty",
            "email": "test.faculty@campusiq.edu",
            "college_id": "FACULTY001",
            "department_id": 1,
            "designation": "Assistant Professor",
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Faculty"
    assert data["role"] == "faculty"


def test_admin_can_create_hod(client: TestClient, admin_headers: dict):
    """Admin can create a faculty with HOD role."""
    response = client.post(
        "/api/v1/faculty",
        json={
            "name": "New HOD",
            "email": "newhod@campusiq.edu",
            "college_id": "HOD002",
            "department_id": 1,
            "is_hod": True,
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "hod"
    assert data["is_hod"] is True


def test_admin_can_create_class_teacher(client: TestClient, admin_headers: dict):
    """Admin can assign a class teacher."""
    # First get a faculty
    faculty_response = client.post(
        "/api/v1/faculty",
        json={
            "name": "CT Faculty",
            "email": "ct.faculty@campusiq.edu",
            "college_id": "CTFAC001",
            "department_id": 1,
            "password": "Test@123",
        },
        headers=admin_headers,
    )
    faculty_id = faculty_response.json()["id"]

    # Create class teacher assignment
    response = client.post(
        "/api/v1/class-teachers",
        json={
            "faculty_id": faculty_id,
            "section": "A",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["faculty_id"] == faculty_id
    assert data["section"] == "A"
    assert data["faculty_name"] == "CT Faculty"


def test_cannot_create_duplicate_class_teacher(client: TestClient, admin_headers: dict, db):
    """Cannot create duplicate class teacher assignment."""
    from app.models.people import Faculty

    faculty = db.query(Faculty).first()
    assert faculty is not None

    # First assignment
    response1 = client.post(
        "/api/v1/class-teachers",
        json={
            "faculty_id": faculty.id,
            "section": "A",
        },
        headers=admin_headers,
    )
    assert response1.status_code == 201

    # Duplicate assignment
    response2 = client.post(
        "/api/v1/class-teachers",
        json={
            "faculty_id": faculty.id,
            "section": "A",
        },
        headers=admin_headers,
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["message"].lower()


def test_admin_can_delete_class_teacher(client: TestClient, admin_headers: dict, db):
    """Admin can delete a class teacher assignment."""
    from app.models.people import Faculty
    from app.models.academic import ClassTeacher

    # Get faculty with unique identifier
    faculty = db.query(Faculty).filter(Faculty.id > 100).first()
    if faculty is None:
        # Create a faculty first
        faculty_response = client.post(
            "/api/v1/faculty",
            json={
                "name": "Delete Test Faculty",
                "email": "delete.faculty@campusiq.edu",
                "college_id": "DELETEFAC001",
                "department_id": 1,
                "password": "Test@123",
            },
            headers=admin_headers,
        )
        faculty = db.query(Faculty).filter(Faculty.id == faculty_response.json()["id"]).first()

    assert faculty is not None

    # Create class teacher for a unique section
    create_response = client.post(
        "/api/v1/class-teachers",
        json={
            "faculty_id": faculty.id,
            "section": "TEST",
        },
        headers=admin_headers,
    )
    teacher_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/v1/class-teachers/{teacher_id}", headers=admin_headers)
    assert response.status_code == 200

    # Verify it's gone
    deleted = db.query(ClassTeacher).filter(ClassTeacher.id == teacher_id).first()
    assert deleted is None


def test_student_cannot_create_class_teacher(client: TestClient, student_headers: dict):
    """Student cannot create class teacher assignments."""
    response = client.post(
        "/api/v1/class-teachers",
        json={
            "faculty_id": 1,
            "section": "A",
        },
        headers=student_headers,
    )
    assert response.status_code == 403
