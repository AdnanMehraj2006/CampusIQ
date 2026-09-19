"""Timezone-safety regression tests.

SQLite returns ``DateTime(timezone=True)`` values as naive datetimes while the
application compares them against timezone-aware ``datetime.now(timezone.utc)``.
These tests pin the behaviour that previously raised::

    TypeError: can't compare offset-naive and offset-aware datetimes
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.datetime import as_utc, utcnow


# ---------------------------------------------------------------------------
# Unit tests for the normaliser itself
# ---------------------------------------------------------------------------


def test_as_utc_attaches_offset_to_naive_input():
    naive = datetime(2026, 9, 19, 12, 0, 0)
    result = as_utc(naive)
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)
    # Wall-clock value is preserved.
    assert result.replace(tzinfo=None) == naive


def test_as_utc_converts_aware_input_to_utc():
    aware = datetime(2026, 9, 19, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    result = as_utc(aware)
    assert result.tzinfo == timezone.utc
    assert result.hour == 12  # 14:00 +02:00 == 12:00 UTC


def test_as_utc_passes_none_through():
    assert as_utc(None) is None


def test_as_utc_is_idempotent():
    dt = datetime(2026, 9, 19, 12, 0, 0)
    assert as_utc(as_utc(dt)) == as_utc(dt)


def test_utcnow_is_aware():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_naive_db_value_compares_against_aware_now(db):
    """The exact operation that used to raise TypeError must now work."""
    from app.models.assignment import Assignment

    assignment = db.query(Assignment).order_by(Assignment.id).first()
    if assignment is None:
        return  # nothing to compare against

    left = as_utc(assignment.deadline)
    right = utcnow()
    # Naive on SQLite, aware in Postgres - both must compare and subtract
    # without raising TypeError.
    assert isinstance(left < right, bool)
    assert isinstance(left > right, bool)
    assert isinstance((left - right).days, int)


# ---------------------------------------------------------------------------
# Integration: endpoints that perform datetime arithmetic/comparison
# ---------------------------------------------------------------------------


def test_student_dashboard_computes_days_left(client, student_headers):
    """dashboard.py subtracts a loaded deadline from an aware 'now'."""
    response = client.get("/api/v1/dashboard/student", headers=student_headers)
    assert response.status_code == 200, response.text


def test_faculty_dashboard_deadline_filter(client, faculty_headers):
    """The faculty dashboard filters assignments by deadline >= now."""
    response = client.get("/api/v1/dashboard/faculty", headers=faculty_headers)
    assert response.status_code == 200, response.text


def test_hod_dashboard_deadline_filter(client, hod_headers):
    response = client.get("/api/v1/dashboard/hod", headers=hod_headers)
    assert response.status_code == 200, response.text


def test_project_milestones_overdue_flag(client, faculty_headers):
    """projects.py compares m.deadline against an aware 'now' for overdue."""
    response = client.get("/api/v1/projects/1/milestones", headers=faculty_headers)
    assert response.status_code == 200, response.text


def test_supervised_projects(client, faculty_headers):
    response = client.get("/api/v1/projects/supervised", headers=faculty_headers)
    assert response.status_code == 200, response.text


def test_refresh_token_expiry_check(client):
    """auth_service compares the stored (naive-on-SQLite) expiry to aware now."""
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "adnan@campusiq.edu", "password": "Student@123"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    # The refresh flow runs record.expires_at < utcnow(); it must not raise.
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200, response.text


def test_password_reset_token_expiry_check(client):
    """The reset flow also compares a stored expiry to an aware 'now'."""
    forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "faculty2@campusiq.edu"},
    )
    assert forgot.status_code == 200
    token = forgot.json().get("data", {}).get("token")
    if not token:  # production mode hides the token; nothing to assert then
        return

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "ResetPass42"},
    )
    assert response.status_code == 200, response.text


def test_assignment_submission_deadline_comparison(client, student_headers, db):
    """Submitting runs `now > as_utc(a.deadline)`; must not raise TypeError."""
    from app.models.assignment import Assignment

    assignment = db.query(Assignment).order_by(Assignment.deadline.desc()).first()
    if assignment is None:
        return

    response = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        headers=student_headers,
        json={"text_submission": "Submitted via the timezone regression test."},
    )
    # 200/201 = accepted; 400 = legitimately past deadline (allow_late False).
    assert response.status_code in (200, 201, 400), response.text
    assert response.status_code != 500
