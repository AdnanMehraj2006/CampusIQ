"""Shared fixtures for the CampusIQ backend test suite.

Isolation strategy: a throwaway SQLite database is selected *before* any
application module is imported (the engine/session factory bind at import
time). The schema is rebuilt and seeded once per test session, so the tests
never touch the developer database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --- Configure the test environment BEFORE importing the application. -------
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_PATH = BACKEND_DIR / "test_campusiq.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["AI_PROVIDER"] = "demo"
os.environ["RATE_LIMIT_ENABLED"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.rate_limiter import rate_limiter  # noqa: E402
from seed import seed as seed_database  # noqa: E402

# Demo credentials (see seed.py).
DEMO_CREDENTIALS = {
    "admin": ("admin@campusiq.edu", "Admin@123"),
    "hod": ("hod.cse@campusiq.edu", "Hod@12345"),
    "faculty": ("faculty@campusiq.edu", "Faculty@123"),
    "cr": ("cr@campusiq.edu", "Cr@12345"),
    "student": ("adnan@campusiq.edu", "Student@123"),
}
# Every generated student in the seed data shares this password.
DEFAULT_STUDENT_PASSWORD = "CampusIQ@123"


def login(client: TestClient, email: str, password: str) -> dict:
    """Log in and return the raw token response."""
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
    )
    assert response.status_code == 200, (
        f"Login failed for {email}: {response.status_code} {response.text}"
    )
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Database + client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db():
    """A seeded session against the isolated test database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        # Release every pooled SQLite connection before removing the file,
        # otherwise Windows keeps an open handle on it.
        engine.dispose()
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def client(db) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Rate limiter isolation
# ---------------------------------------------------------------------------
# The limiter is a process-wide singleton keyed by route + client IP, and the
# limits are per-minute. Without a reset, a test that exhausts the login/AI
# budget would leak into every later test using the same client (all TestClient
# requests share one IP), causing spurious 429s. Clear the counters per test.


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# ---------------------------------------------------------------------------
# Tokens / auth headers per role
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tokens(client) -> dict[str, str]:
    """access_token for each of the five demo roles, keyed by role name."""
    return {
        role: login(client, email, password)["access_token"]
        for role, (email, password) in DEMO_CREDENTIALS.items()
    }


def _role_headers_fixture(role: str):
    @pytest.fixture(scope="session")
    def _fixture(tokens):
        return auth_headers(tokens[role])

    return _fixture


admin_headers = _role_headers_fixture("admin")
hod_headers = _role_headers_fixture("hod")
faculty_headers = _role_headers_fixture("faculty")
cr_headers = _role_headers_fixture("cr")
student_headers = _role_headers_fixture("student")


# ---------------------------------------------------------------------------
# Second student (Student B) for cross-student isolation tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def other_student(db):
    """A second *regular student* (never the CR) for cross-student tests."""
    from app.models.people import Student
    from app.models.user import User

    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(User.email != "adnan@campusiq.edu", User.role == "student")
        .order_by(Student.id)
        .first()
    )
    assert student is not None, "Seed data should contain more than one student."
    return student


@pytest.fixture(scope="session")
def other_student_headers(client, other_student) -> dict:
    token = login(client, other_student.user.email, DEFAULT_STUDENT_PASSWORD)[
        "access_token"
    ]
    return auth_headers(token)
