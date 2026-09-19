"""Authentication: login for all five roles, /auth/me, token handling."""

from __future__ import annotations


def _login(client, email: str, password: str):
    return client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": password}
    )


def test_login_all_five_roles(client):
    roles = {
        "admin@campusiq.edu": "Admin@123",
        "hod.cse@campusiq.edu": "Hod@12345",
        "faculty@campusiq.edu": "Faculty@123",
        "cr@campusiq.edu": "Cr@12345",
        "adnan@campusiq.edu": "Student@123",
    }
    for email, password in roles.items():
        response = _login(client, email, password)
        assert response.status_code == 200, f"{email}: {response.text}"
        body = response.json()
        assert body["token_type"] == "Bearer"
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["user"]["email"] == email


def test_login_with_college_id_identifier(client):
    """Login accepts an email OR a college_id."""
    response = _login(client, "ADMIN001", "Admin@123")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@campusiq.edu"


def test_login_wrong_password_is_unauthorized(client):
    response = _login(client, "adnan@campusiq.edu", "wrong-password")
    assert response.status_code == 401


def test_login_unknown_user_is_unauthorized(client):
    response = _login(client, "nobody@campusiq.edu", "whatever")
    assert response.status_code == 401


def test_auth_me_all_five_roles(client, tokens):
    expected = {
        "admin": "admin@campusiq.edu",
        "hod": "hod.cse@campusiq.edu",
        "faculty": "faculty@campusiq.edu",
        "cr": "cr@campusiq.edu",
        "student": "adnan@campusiq.edu",
    }
    for role, email in expected.items():
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 200, f"{role}: {response.text}"
        user = response.json()
        assert user["email"] == email
        assert user["role"] == role
        assert "password_hash" not in response.text


def test_auth_me_returns_iso_datetime_for_last_login(client, student_headers):
    """last_login_at must serialise without a ResponseValidationError."""
    response = client.get("/api/v1/auth/me", headers=student_headers)
    assert response.status_code == 200
    # Login recorded a timestamp, so it must be present and ISO-8601 shaped.
    last_login = response.json()["last_login_at"]
    assert last_login is not None
    assert "T" in last_login


def test_auth_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_auth_me_rejects_garbage_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert response.status_code == 401


def test_refresh_token_flow(client):
    login_response = _login(client, "adnan@campusiq.edu", "Student@123")
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_refresh_token_rejects_revoked_token(client):
    login_response = _login(client, "adnan@campusiq.edu", "Student@123")
    refresh_token = login_response.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 401


def test_change_password(client):
    login_response = _login(client, "faculty3@campusiq.edu", "Faculty@123")
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Faculty@123", "new_password": "NewPass42"},
    )
    assert response.status_code == 200, response.text

    # Old password no longer works, the new one does.
    assert _login(client, "faculty3@campusiq.edu", "Faculty@123").status_code == 401
    assert _login(client, "faculty3@campusiq.edu", "NewPass42").status_code == 200
