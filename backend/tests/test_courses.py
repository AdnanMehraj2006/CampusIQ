"""Course/semester listing tests."""

from __future__ import annotations


def test_list_semesters_includes_college_wide_for_a_course(client, admin_headers):
    """Semesters with no course are college-wide, so they must appear when
    filtering by course (otherwise the announcement Semester dropdown is empty).
    """
    response = client.get("/api/v1/semesters?course_id=1", headers=admin_headers)
    assert response.status_code == 200, response.text
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1, "course-filtered semester list must not be empty"
    assert all("id" in s and "semester_number" in s for s in items)


def test_list_semesters_without_course(client, admin_headers):
    response = client.get("/api/v1/semesters", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
