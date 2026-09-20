"""Rate limiting tests.

These prove the configured limits are *actually enforced*: the first ``limit``
requests succeed and the very next one is rejected with the documented 429 /
``RATE_LIMIT_EXCEEDED`` body.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.rate_limiter import parse_rate_limit, rate_limiter
from tests.conftest import DEMO_CREDENTIALS


def _login(client: TestClient, email: str, password: str, headers: dict | None = None):
    return client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
        headers=headers,
    )


def test_configured_limits_match_intent():
    """The intended login (10/min) and AI (30/min) limits come from settings."""
    assert parse_rate_limit(settings.rate_limit_login) == (10, 60)
    assert parse_rate_limit(settings.rate_limit_ai) == (30, 60)


def test_login_rate_limiting(client):
    """Login allows 10 requests/minute and blocks the 11th."""
    limit, _window = parse_rate_limit(settings.rate_limit_login)
    email, password = DEMO_CREDENTIALS["student"]

    for i in range(limit):
        response = _login(client, email, password)
        assert response.status_code == 200, f"Request {i + 1}/{limit} should succeed"

    # The very next login in the same window must be blocked.
    response = _login(client, email, password)
    assert response.status_code == 429
    assert response.json()["detail"] == "RATE_LIMIT_EXCEEDED"
    assert int(response.headers["Retry-After"]) >= 1


def test_login_limit_is_per_client_ip(client):
    """Exhausting the limit as one caller does not block a different caller."""
    limit, _window = parse_rate_limit(settings.rate_limit_login)
    email, password = DEMO_CREDENTIALS["student"]

    for _ in range(limit):
        assert _login(client, email, password).status_code == 200
    assert _login(client, email, password).status_code == 429

    # A different forwarded client IP gets its own fresh bucket.
    other = _login(client, email, password, headers={"X-Forwarded-For": "10.0.0.99"})
    assert other.status_code == 200


def test_ai_chat_rate_limiting(client, student_headers):
    """AI chat allows 30 requests/minute and blocks the 31st."""
    limit, _window = parse_rate_limit(settings.rate_limit_ai)

    for i in range(limit):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello", "history": []},
            headers=student_headers,
        )
        assert response.status_code == 200, f"Request {i + 1}/{limit} should succeed"

    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hello", "history": []},
        headers=student_headers,
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "RATE_LIMIT_EXCEEDED"


def test_rate_limit_does_not_block_other_endpoints(client, student_headers):
    """Only login/AI are limited; unrelated routes keep working after exhaustion."""
    limit, _window = parse_rate_limit(settings.rate_limit_login)
    email, password = DEMO_CREDENTIALS["student"]

    for _ in range(limit + 3):
        _login(client, email, password)

    # An already-issued token still works on a non-limited route.
    response = client.get("/api/v1/auth/me", headers=student_headers)
    assert response.status_code == 200


def test_rate_limiter_reset_restores_access(client):
    """Resetting the store clears the window (used for test isolation)."""
    limit, _window = parse_rate_limit(settings.rate_limit_login)
    email, password = DEMO_CREDENTIALS["student"]

    for _ in range(limit):
        assert _login(client, email, password).status_code == 200
    assert _login(client, email, password).status_code == 429

    rate_limiter.reset()
    assert _login(client, email, password).status_code == 200


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("10/minute", (10, 60)),
        ("30/minute", (30, 60)),
        ("120/minute", (120, 60)),
        ("5/second", (5, 1)),
        ("2/hour", (2, 3600)),
        ("100 per minute", (100, 60)),
    ],
)
def test_parse_rate_limit_formats(spec, expected):
    assert parse_rate_limit(spec) == expected


def test_parse_rate_limit_rejects_garbage():
    with pytest.raises(ValueError):
        parse_rate_limit("not-a-limit")
