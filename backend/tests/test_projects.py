"""Projects: listing, static routes (my/supervised), milestones."""

from __future__ import annotations


def test_every_role_can_list_projects(client, tokens):
    for role in ("admin", "hod", "faculty", "cr", "student"):
        response = client.get(
            "/api/v1/projects", headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 200, f"{role}: {response.text}"


def test_project_detail(client, student_headers):
    """The /projects/{id} dynamic route must still work after reordering."""
    response = client.get("/api/v1/projects/1", headers=student_headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == 1


def test_projects_my_route_resolves(client, student_headers):
    """/projects/my must match the static route, not {project_id}."""
    response = client.get("/api/v1/projects/my", headers=student_headers)
    assert response.status_code == 200, response.text
    assert "items" in response.json() or "data" in response.json()


def test_projects_supervised_route_resolves(client, faculty_headers):
    """/projects/supervised must match the static route, not {project_id}."""
    response = client.get("/api/v1/projects/supervised", headers=faculty_headers)
    assert response.status_code == 200, response.text
    assert "items" in response.json() or "data" in response.json()


def test_project_groups(client, student_headers):
    response = client.get("/api/v1/projects/1/groups", headers=student_headers)
    assert response.status_code == 200, response.text


def test_project_milestones(client, student_headers):
    """Milestone listing must not trip on the timezone mismatch."""
    response = client.get("/api/v1/projects/1/milestones", headers=student_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_student_cannot_create_project(client, student_headers):
    response = client.post(
        "/api/v1/projects",
        headers=student_headers,
        json={"title": "x", "description": "x", "department_id": 1},
    )
    assert response.status_code == 403, response.text


def test_student_cannot_approve_groups(client, student_headers):
    response = client.put(
        "/api/v1/projects/groups/1/approve", headers=student_headers
    )
    assert response.status_code == 403, response.text
