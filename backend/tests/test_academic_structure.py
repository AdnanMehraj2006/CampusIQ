"""Academic structure regression tests.

Covers:
- Context-free section creation rejection
- Contextual section creation and filtering
- Same section name across different contexts
- Duplicate section in same context rejection
- Course/semester/section filtering
- Student creation with valid/invalid academic context
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import Course, Department, Section, Semester
from app.models.people import Student
from tests.conftest import auth_headers


def _dept_id_by_code(db: Session, code: str) -> int:
    dept = db.query(Department).filter(Department.code == code).first()
    assert dept is not None
    return dept.id


def _course_by_code(db: Session, code: str) -> Course:
    course = db.query(Course).filter(Course.code == code).first()
    assert course is not None
    return course


def test_context_free_section_rejected(
    client: TestClient, admin_headers: dict, db: Session
):
    """Sections without academic context must be rejected."""
    response = client.post(
        "/api/v1/sections",
        json={"name": "X", "description": "Context free section", "is_active": True},
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert "academic context" in response.json()["message"].lower()


def test_contextual_section_creation_succeeds(
    client: TestClient, admin_headers: dict, db: Session
):
    """Sections with valid course/semester context should be created."""
    cse_dept_id = _dept_id_by_code(db, "CSE")
    cse_course = _course_by_code(db, "BTech-CSE")
    
    # Create a semester for this course
    semester = Semester(semester_number=5, course_id=cse_course.id)
    db.add(semester)
    db.commit()
    db.refresh(semester)
    
    response = client.post(
        "/api/v1/sections",
        json={
            "name": "TEST",
            "description": "Test section",
            "is_active": True,
            "course_id": cse_course.id,
            "semester_id": semester.id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "TEST"
    assert data["course_id"] == cse_course.id
    assert data["semester_id"] == semester.id


def test_same_section_name_across_different_contexts(
    client: TestClient, admin_headers: dict, db: Session
):
    """Section name 'A' should be allowed in different academic contexts."""
    cse_course = _course_by_code(db, "BTech-CSE")
    
    # Create two semesters for the same course
    semester5 = Semester(semester_number=5, course_id=cse_course.id)
    semester6 = Semester(semester_number=6, course_id=cse_course.id)
    db.add(semester5)
    db.add(semester6)
    db.commit()
    db.refresh(semester5)
    db.refresh(semester6)
    
    # Create section A in semester 5
    response1 = client.post(
        "/api/v1/sections",
        json={
            "name": "A",
            "course_id": cse_course.id,
            "semester_id": semester5.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response1.status_code == 201, response1.text
    
    # Create section A in semester 6 (same course, different semester)
    response2 = client.post(
        "/api/v1/sections",
        json={
            "name": "A",
            "course_id": cse_course.id,
            "semester_id": semester6.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response2.status_code == 201, response2.text
    
    # Verify both exist with different IDs
    sections5 = client.get(f"/api/v1/sections?course_id={cse_course.id}&semester_id={semester5.id}", headers=admin_headers).json()["items"]
    sections6 = client.get(f"/api/v1/sections?course_id={cse_course.id}&semester_id={semester6.id}", headers=admin_headers).json()["items"]
    
    assert any(s["name"] == "A" for s in sections5)
    assert any(s["name"] == "A" for s in sections6)


def test_duplicate_section_in_same_context_rejected(
    client: TestClient, admin_headers: dict, db: Session
):
    """Duplicate section name in the same academic context must be rejected."""
    cse_course = _course_by_code(db, "BTech-CSE")
    
    # Create a semester
    semester = Semester(semester_number=5, course_id=cse_course.id)
    db.add(semester)
    db.commit()
    db.refresh(semester)
    
    # First creation succeeds
    response1 = client.post(
        "/api/v1/sections",
        json={
            "name": "DUP",
            "course_id": cse_course.id,
            "semester_id": semester.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response1.status_code == 201, response1.text
    
    # Second creation fails
    response2 = client.post(
        "/api/v1/sections",
        json={
            "name": "DUP",
            "course_id": cse_course.id,
            "semester_id": semester.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response2.status_code == 409, response2.text
    assert "already exists" in response2.json()["message"].lower()


def test_course_filtering_by_department(
    client: TestClient, admin_headers: dict, db: Session
):
    """Course dropdown should only show courses belonging to selected department."""
    cse_dept_id = _dept_id_by_code(db, "CSE")
    it_dept_id = _dept_id_by_code(db, "IT")
    
    # Get CSE courses
    cse_courses = client.get(f"/api/v1/courses?department_id={cse_dept_id}", headers=admin_headers).json()["items"]
    cse_course_ids = [c["id"] for c in cse_courses]
    
    # Get IT courses
    it_courses = client.get(f"/api/v1/courses?department_id={it_dept_id}", headers=admin_headers).json()["items"]
    it_course_ids = [c["id"] for c in it_courses]
    
    # Verify no overlap
    assert len(set(cse_course_ids) & set(it_course_ids)) == 0


def test_semester_filtering_by_course(
    client: TestClient, admin_headers: dict, db: Session
):
    """Semester dropdown should only show semesters belonging to selected course."""
    cse_course = _course_by_code(db, "BTech-CSE")
    it_course = _course_by_code(db, "BTech-IT")
    
    # Get semesters for CSE course
    cse_semesters = client.get(f"/api/v1/semesters?course_id={cse_course.id}", headers=admin_headers).json()
    cse_semester_ids = {s["id"] for s in cse_semesters}
    
    # Get semesters for IT course
    it_semesters = client.get(f"/api/v1/semesters?course_id={it_course.id}", headers=admin_headers).json()
    it_semester_ids = {s["id"] for s in it_semesters}
    
    # Verify context-specific semesters (some may be shared as NULL course_id)
    # but course-specific semesters should be distinct
    assert len(cse_semester_ids) > 0
    assert len(it_semester_ids) > 0


def test_section_filtering_by_course_and_semester(
    client: TestClient, admin_headers: dict, db: Session
):
    """Section dropdown should only show sections for the selected course + semester."""
    cse_course = _course_by_code(db, "BTech-CSE")
    
    # Create two semesters
    semester5 = Semester(semester_number=5, course_id=cse_course.id)
    semester6 = Semester(semester_number=6, course_id=cse_course.id)
    db.add(semester5)
    db.add(semester6)
    db.commit()
    db.refresh(semester5)
    db.refresh(semester6)
    
    # Create sections for semester 5
    client.post(
        "/api/v1/sections",
        json={
            "name": "S5A",
            "course_id": cse_course.id,
            "semester_id": semester5.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    
    # Create sections for semester 6
    client.post(
        "/api/v1/sections",
        json={
            "name": "S6A",
            "course_id": cse_course.id,
            "semester_id": semester6.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    
    # Get sections for semester 5
    sections5 = client.get(
        f"/api/v1/sections?course_id={cse_course.id}&semester_id={semester5.id}",
        headers=admin_headers,
    ).json()["items"]
    
    # Get sections for semester 6
    sections6 = client.get(
        f"/api/v1/sections?course_id={cse_course.id}&semester_id={semester6.id}",
        headers=admin_headers,
    ).json()["items"]
    
    # Verify sections are context-specific
    assert len(sections5) == 1
    assert sections5[0]["name"] == "S5A"
    assert len(sections6) == 1
    assert sections6[0]["name"] == "S6A"


def test_student_creation_with_valid_academic_context(
    client: TestClient, admin_headers: dict, db: Session
):
    """Student creation with valid Department + Course + Semester + Section should succeed."""
    cse_dept_id = _dept_id_by_code(db, "CSE")
    cse_course = _course_by_code(db, "BTech-CSE")
    
    # Create semester and section
    semester = Semester(semester_number=5, course_id=cse_course.id)
    db.add(semester)
    db.commit()
    db.refresh(semester)
    
    section_response = client.post(
        "/api/v1/sections",
        json={
            "name": "VALID",
            "course_id": cse_course.id,
            "semester_id": semester.id,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert section_response.status_code == 201
    section_name = section_response.json()["name"]
    
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Valid Context Student",
            "email": f"validcontext.{cse_dept_id}@campusiq.edu",
            "college_id": "VC123",
            "enrollment_number": "VCENR123",
            "department_id": cse_dept_id,
            "course_id": cse_course.id,
            "semester_id": semester.id,
            "section": section_name,
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["department_id"] == cse_dept_id
    assert data["course_id"] == cse_course.id
    assert data["semester_id"] == semester.id
    assert data["section"] == section_name


def test_student_creation_with_invalid_course_rejected(
    client: TestClient, admin_headers: dict, db: Session
):
    """Student creation with course from different department should be rejected."""
    cse_dept_id = _dept_id_by_code(db, "CSE")
    it_dept_id = _dept_id_by_code(db, "IT")
    it_course = _course_by_code(db, "BTech-IT")
    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Invalid Course Student",
            "email": f"invalidc.{it_dept_id}@campusiq.edu",
            "college_id": "IC123",
            "enrollment_number": "ICENR123",
            "department_id": cse_dept_id,  # CSE
            "course_id": it_course.id,     # IT course
            "semester_id": semester.id,
            "section": "A",
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert "does not belong to" in response.json()["message"].lower()


def test_student_creation_with_invalid_semester_rejected(
    client: TestClient, admin_headers: dict, db: Session
):
    """Student creation with semester from different course should be rejected."""
    cse_dept_id = _dept_id_by_code(db, "CSE")
    cse_course = _course_by_code(db, "BTech-CSE")
    it_course = _course_by_code(db, "BTech-IT")
    
    # Create/find semester for IT course
    it_semester = db.query(Semester).filter(
        Semester.semester_number == 5,
        Semester.course_id == it_course.id,
    ).first()
    if not it_semester:
        it_semester = Semester(semester_number=5, course_id=it_course.id)
        db.add(it_semester)
        db.commit()
    
    response = client.post(
        "/api/v1/students",
        json={
            "name": "Invalid Semester Student",
            "email": f"invalids.{cse_dept_id}@campusiq.edu",
            "college_id": "IS123",
            "enrollment_number": "ISENR123",
            "department_id": cse_dept_id,
            "course_id": cse_course.id,   # CSE course
            "semester_id": it_semester.id,  # IT course semester
            "section": "A",
            "admission_year": 2024,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert "does not belong to" in response.json()["message"].lower()
