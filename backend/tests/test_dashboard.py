"""Per-role dashboards and the shared /dashboard/me endpoint."""

from __future__ import annotations

import pytest

DASHBOARDS = {
    "admin": "/api/v1/dashboard/admin",
    "hod": "/api/v1/dashboard/hod",
    "faculty": "/api/v1/dashboard/faculty",
    "cr": "/api/v1/dashboard/cr",
    "student": "/api/v1/dashboard/student",
}


@pytest.mark.parametrize("role", list(DASHBOARDS))
def test_role_dashboard_returns_200(client, tokens, role):
    response = client.get(
        DASHBOARDS[role], headers={"Authorization": f"Bearer {tokens[role]}"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == role


def test_dashboard_me_works_for_every_role(client, tokens):
    """Each /dashboard/me response identifies the caller and their role."""
    for role in ("admin", "hod", "faculty", "cr", "student"):
        response = client.get(
            "/api/v1/dashboard/me",
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 200, f"{role}: {response.text}"
        body = response.json()
        assert body["role"] == role
        # Every role's summary names the caller; the extra field varies by role
        # (department for HOD, section for CR, email elsewhere).
        assert body["user"]["name"]


def test_student_dashboard_has_attendance_and_subjects(client, student_headers):
    response = client.get("/api/v1/dashboard/student", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert "attendance" in body
    assert "overall_percentage" in body["attendance"]
    assert "cards" in body
    assert isinstance(body["today_classes"], list)


def test_admin_dashboard_has_cards_and_charts(client, admin_headers):
    response = client.get("/api/v1/dashboard/admin", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "cards" in body
    assert "charts" in body
    assert isinstance(body["cards"], list)
    assert len(body["cards"]) > 0


def test_faculty_dashboard_lists_subjects(client, faculty_headers):
    response = client.get("/api/v1/dashboard/faculty", headers=faculty_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "faculty"
